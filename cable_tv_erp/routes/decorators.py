"""
routes/decorators.py — Role and permission decorators for ERP routes.
"""
from functools import wraps
from flask import session, redirect, url_for, flash
from db import query_db


def admin_required(f):
    """Blocks anyone who is not an admin. Shows a flash message and redirects to dashboard."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'admin':
            flash('This action requires admin privileges.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


def permission_required(permission_code):
    """
    Admins always pass.
    Employees pass only if they have the given permissionCode in RoleHasPermission.
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login'))
            if session.get('role') == 'admin':
                return f(*args, **kwargs)
            result = query_db(
                "SELECT 1 FROM RoleHasPermission WHERE userId = %s AND permissionCode = %s",
                (session.get('user_id'), permission_code),
                one=True
            )
            if not result:
                flash(f'You need the {permission_code} permission to perform this action.', 'error')
                return redirect(url_for('dashboard.index'))
            return f(*args, **kwargs)
        return decorated
    return decorator
