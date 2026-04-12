from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import login_required_session, admin_required
import logging

packages_bp = Blueprint('packages', __name__)


@packages_bp.route('/packages')
@login_required_session
def list_packages():
    try:
        packages = query_db(
            """SELECT p.packageId, p.packageName, p.monthlyPrice,
                      COUNT(s.subscriptionId) AS activeSubs
               FROM Package p
               LEFT JOIN Subscription s ON p.packageId = s.packageId AND s.status = 'active'
               GROUP BY p.packageId, p.packageName, p.monthlyPrice
               ORDER BY p.monthlyPrice ASC"""
        )
        return render_template('packages/list.html', packages=packages)
    except Exception as e:
        logging.error(f"Package list error: {e}")
        flash('Something went wrong loading packages.', 'error')
        return render_template('packages/list.html', packages=[])


@packages_bp.route('/packages/new', methods=['GET', 'POST'])
@admin_required
def new_package():
    if request.method == 'POST':
        name = request.form.get('packageName', '').strip()
        price = request.form.get('monthlyPrice', '').strip()

        errors = []
        if not name: errors.append('Package name is required.')
        if not price:
            errors.append('Monthly price is required.')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Price must be greater than 0.')
            except ValueError:
                errors.append('Price must be a valid number.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('packages/form.html', action='new', form=request.form)

        try:
            existing = query_db("SELECT packageId FROM Package WHERE packageName = %s", (name,), one=True)
            if existing:
                flash('A package with that name already exists.', 'error')
                return render_template('packages/form.html', action='new', form=request.form)

            query_db(
                "INSERT INTO Package (packageName, monthlyPrice) VALUES (%s, %s)",
                (name, price), commit=True
            )
            flash(f'Package "{name}" created successfully.', 'success')
            return redirect(url_for('packages.list_packages'))
        except Exception as e:
            logging.error(f"Create package error: {e}")
            flash('Something went wrong creating the package.', 'error')
            return render_template('packages/form.html', action='new', form=request.form)

    return render_template('packages/form.html', action='new', form={})


@packages_bp.route('/packages/<int:pid>/edit', methods=['GET', 'POST'])
@admin_required
def edit_package(pid):
    package = query_db("SELECT * FROM Package WHERE packageId = %s", (pid,), one=True)
    if not package:
        abort(404)

    if request.method == 'POST':
        name = request.form.get('packageName', '').strip()
        price = request.form.get('monthlyPrice', '').strip()

        errors = []
        if not name: errors.append('Package name is required.')
        if not price:
            errors.append('Monthly price is required.')
        else:
            try:
                price = float(price)
                if price <= 0:
                    errors.append('Price must be greater than 0.')
            except ValueError:
                errors.append('Price must be a valid number.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('packages/form.html', action='edit', package=package, form=request.form)

        try:
            existing = query_db(
                "SELECT packageId FROM Package WHERE packageName = %s AND packageId != %s",
                (name, pid), one=True
            )
            if existing:
                flash('A package with that name already exists.', 'error')
                return render_template('packages/form.html', action='edit', package=package, form=request.form)

            query_db(
                "UPDATE Package SET packageName=%s, monthlyPrice=%s WHERE packageId=%s",
                (name, price, pid), commit=True
            )
            flash('Package updated successfully.', 'success')
            return redirect(url_for('packages.list_packages'))
        except Exception as e:
            logging.error(f"Edit package error: {e}")
            flash('Something went wrong updating the package.', 'error')

    return render_template('packages/form.html', action='edit', package=package, form=package)


@packages_bp.route('/packages/<int:pid>/delete', methods=['POST'])
@admin_required
def delete_package(pid):
    try:
        active_subs = query_db(
            "SELECT COUNT(*) AS cnt FROM Subscription WHERE packageId = %s AND status = 'active'",
            (pid,), one=True
        )['cnt']
        if active_subs > 0:
            flash(f'Cannot delete: {active_subs} active subscription(s) reference this package.', 'error')
            return redirect(url_for('packages.list_packages'))

        query_db("DELETE FROM Package WHERE packageId = %s", (pid,), commit=True)
        flash('Package deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Delete package error: {e}")
        flash('Something went wrong deleting the package.', 'error')
    return redirect(url_for('packages.list_packages'))
