from flask import Blueprint, render_template, request, jsonify, flash
from db import query_db
from routes.auth import admin_required
import logging

permissions_bp = Blueprint('permissions', __name__)


@permissions_bp.route('/permissions')
@admin_required
def manage():
    try:
        # All users who are admin or employee
        users = query_db(
            """SELECT u.userId, u.userName,
                      CASE WHEN a.userId IS NOT NULL THEN 'admin' ELSE 'employee' END AS role
               FROM User u
               LEFT JOIN Admin a ON u.userId = a.userId
               LEFT JOIN Employee e ON u.userId = e.userId
               WHERE a.userId IS NOT NULL OR e.userId IS NOT NULL
               ORDER BY role, u.userName"""
        )

        permissions = query_db("SELECT permissionCode FROM Permission ORDER BY permissionCode")

        # Build a set of (userId, permissionCode) for fast lookup
        assigned = query_db("SELECT userId, permissionCode FROM RoleHasPermission")
        assigned_set = {(r['userId'], r['permissionCode']) for r in assigned}

        return render_template('permissions/manage.html',
                               users=users,
                               permissions=permissions,
                               assigned_set=assigned_set)
    except Exception as e:
        logging.error(f"Permissions manage error: {e}")
        flash('Something went wrong loading permissions.', 'error')
        return render_template('permissions/manage.html', users=[], permissions=[], assigned_set=set())


@permissions_bp.route('/permissions/grant', methods=['POST'])
@admin_required
def grant():
    try:
        data = request.get_json()
        user_id = data.get('userId')
        perm_code = data.get('permissionCode')

        if not user_id or not perm_code:
            return jsonify({'success': False, 'error': 'Missing userId or permissionCode'}), 400

        existing = query_db(
            "SELECT * FROM RoleHasPermission WHERE userId=%s AND permissionCode=%s",
            (user_id, perm_code), one=True
        )
        if not existing:
            query_db(
                "INSERT INTO RoleHasPermission (userId, permissionCode) VALUES (%s, %s)",
                (user_id, perm_code), commit=True
            )
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Grant permission error: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500


@permissions_bp.route('/permissions/revoke', methods=['POST'])
@admin_required
def revoke():
    try:
        data = request.get_json()
        user_id = data.get('userId')
        perm_code = data.get('permissionCode')

        if not user_id or not perm_code:
            return jsonify({'success': False, 'error': 'Missing userId or permissionCode'}), 400

        query_db(
            "DELETE FROM RoleHasPermission WHERE userId=%s AND permissionCode=%s",
            (user_id, perm_code), commit=True
        )
        return jsonify({'success': True})
    except Exception as e:
        logging.error(f"Revoke permission error: {e}")
        return jsonify({'success': False, 'error': 'Database error'}), 500
