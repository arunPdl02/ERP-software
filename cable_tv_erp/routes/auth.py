from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, abort
from db import query_db
import logging

# Import bcrypt instance directly from app to avoid extensions lookup issues
def _get_bcrypt():
    from app import bcrypt
    return bcrypt

auth_bp = Blueprint('auth', __name__)


def login_required_session(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated


def get_user_role(user_id):
    if query_db("SELECT userId FROM Admin WHERE userId = %s", (user_id,), one=True):
        return 'admin'
    if query_db("SELECT userId FROM Employee WHERE userId = %s", (user_id,), one=True):
        return 'employee'
    if query_db("SELECT customerId FROM Customer WHERE customerId = %s", (user_id,), one=True):
        return 'customer'
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Please enter both username and password.', 'error')
            return render_template('login.html')

        try:
            user = query_db(
                "SELECT userId, userName, passwordHash, status FROM User WHERE userName = %s",
                (username,), one=True
            )

            if not user:
                flash('Invalid username or password.', 'error')
                return render_template('login.html')

            if user['status'] != 'active':
                flash('Your account is inactive. Contact support.', 'error')
                return render_template('login.html')

            try:
                bcrypt_inst = _get_bcrypt()
                valid = bcrypt_inst.check_password_hash(user['passwordHash'], password)
            except Exception as ex:
                logging.error(f"bcrypt check failed: {ex}")
                valid = False

            if valid:
                # Only allow Admins and Employees — ERP is staff-only
                is_admin = query_db("SELECT userId FROM Admin WHERE userId = %s", (user['userId'],), one=True)
                is_employee = query_db("SELECT userId FROM Employee WHERE userId = %s", (user['userId'],), one=True)

                if not is_admin and not is_employee:
                    flash('Access denied. This system is for staff only.', 'error')
                    return render_template('login.html')

                session['user_id'] = user['userId']
                session['user_name'] = user['userName']
                session['role'] = 'admin' if is_admin else 'employee'
                flash(f'Welcome back, {user["userName"]}!', 'success')
                return redirect(url_for('dashboard.index'))
            else:
                flash('Invalid username or password.', 'error')
        except Exception as e:
            logging.error(f"Login error: {e}")
            flash('Something went wrong. Please try again.', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
