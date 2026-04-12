from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import admin_required
import logging

employees_bp = Blueprint('employees', __name__)


@employees_bp.route('/employees')
@admin_required
def list_employees():
    try:
        employees = query_db(
            """SELECT u.userId, u.userName, u.status,
                      GROUP_CONCAT(rhp.permissionCode ORDER BY rhp.permissionCode SEPARATOR ', ') AS permissions
               FROM User u
               JOIN Employee e ON u.userId = e.userId
               LEFT JOIN RoleHasPermission rhp ON u.userId = rhp.userId
               GROUP BY u.userId, u.userName, u.status
               ORDER BY u.userName"""
        )
        return render_template('employees/list.html', employees=employees)
    except Exception as e:
        logging.error(f"Employee list error: {e}")
        flash('Something went wrong loading employees.', 'error')
        return render_template('employees/list.html', employees=[])


@employees_bp.route('/employees/new', methods=['GET', 'POST'])
@admin_required
def new_employee():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        errors = []
        if not username: errors.append('Username is required.')
        if not password: errors.append('Password is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('employees/form.html', action='new', form=request.form)

        try:
            existing = query_db("SELECT userId FROM User WHERE userName = %s", (username,), one=True)
            if existing:
                flash('Username already exists.', 'error')
                return render_template('employees/form.html', action='new', form=request.form)

            from flask import current_app
            bcrypt_inst = current_app.extensions.get('bcrypt')
            pw_hash = bcrypt_inst.generate_password_hash(password).decode('utf-8') if bcrypt_inst else password

            user_id = query_db(
                "INSERT INTO User (userName, passwordHash, status) VALUES (%s, %s, 'active')",
                (username, pw_hash), commit=True
            )
            query_db("INSERT INTO Employee (userId) VALUES (%s)", (user_id,), commit=True)
            flash(f'Employee {username} created successfully.', 'success')
            return redirect(url_for('employees.list_employees'))
        except Exception as e:
            logging.error(f"Create employee error: {e}")
            flash('Something went wrong creating the employee.', 'error')
            return render_template('employees/form.html', action='new', form=request.form)

    return render_template('employees/form.html', action='new', form={})


@employees_bp.route('/employees/<int:uid>/delete', methods=['POST'])
@admin_required
def delete_employee(uid):
    try:
        emp = query_db("SELECT userId FROM Employee WHERE userId = %s", (uid,), one=True)
        if not emp:
            abort(404)
        query_db("DELETE FROM User WHERE userId = %s", (uid,), commit=True)
        flash('Employee deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Delete employee error: {e}")
        flash('Something went wrong deleting the employee.', 'error')
    return redirect(url_for('employees.list_employees'))
