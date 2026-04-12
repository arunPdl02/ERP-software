from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import login_required_session
from routes.decorators import permission_required
from rag.sync import sync_subscription
from datetime import date
import logging

subscriptions_bp = Blueprint('subscriptions', __name__)


@subscriptions_bp.route('/subscriptions')
@login_required_session
def list_subscriptions():
    try:
        status_filter = request.args.get('status', '')
        sql = """
            SELECT s.subscriptionId, s.startDate, s.endDate, s.status,
                   c.firstName, c.lastName, c.customerId,
                   p.packageName, p.monthlyPrice
            FROM Subscription s
            JOIN Customer c ON s.customerId = c.customerId
            JOIN Package p ON s.packageId = p.packageId
        """
        args = ()
        if status_filter:
            sql += " WHERE s.status = %s"
            args = (status_filter,)
        sql += " ORDER BY s.startDate DESC"
        subscriptions = query_db(sql, args)
        return render_template('subscriptions/list.html',
                               subscriptions=subscriptions,
                               status_filter=status_filter)
    except Exception as e:
        logging.error(f"Subscription list error: {e}")
        flash('Something went wrong loading subscriptions.', 'error')
        return render_template('subscriptions/list.html', subscriptions=[], status_filter='')


@subscriptions_bp.route('/subscriptions/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_CUSTOMERS')
def new_subscription():
    customers = query_db(
        "SELECT customerId, firstName, lastName FROM Customer WHERE accountStatus='active' ORDER BY lastName"
    )
    packages = query_db("SELECT packageId, packageName, monthlyPrice FROM Package ORDER BY monthlyPrice")

    if request.method == 'POST':
        customer_id = request.form.get('customerId')
        package_id = request.form.get('packageId')
        start_date = request.form.get('startDate')

        errors = []
        if not customer_id: errors.append('Customer is required.')
        if not package_id: errors.append('Package is required.')
        if not start_date: errors.append('Start date is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('subscriptions/form.html',
                                   customers=customers, packages=packages, form=request.form)
        try:
            new_id = query_db(
                "INSERT INTO Subscription (customerId, packageId, startDate, status) VALUES (%s, %s, %s, 'active')",
                (customer_id, package_id, start_date), commit=True
            )
            sync_subscription(new_id)
            flash('Subscription created successfully.', 'success')
            return redirect(url_for('subscriptions.list_subscriptions'))
        except Exception as e:
            logging.error(f"Create subscription error: {e}")
            flash('Something went wrong creating the subscription.', 'error')

    return render_template('subscriptions/form.html',
                           customers=customers, packages=packages, form={})


@subscriptions_bp.route('/subscriptions/<int:sid>/cancel', methods=['POST'])
@login_required_session
@permission_required('MANAGE_CUSTOMERS')
def cancel_subscription(sid):
    try:
        sub = query_db("SELECT * FROM Subscription WHERE subscriptionId = %s", (sid,), one=True)
        if not sub:
            abort(404)
        today = date.today().isoformat()
        query_db(
            "UPDATE Subscription SET status='cancelled', endDate=%s WHERE subscriptionId=%s",
            (today, sid), commit=True
        )
        sync_subscription(sid)
        flash('Subscription cancelled successfully.', 'success')
    except Exception as e:
        logging.error(f"Cancel subscription error: {e}")
        flash('Something went wrong cancelling the subscription.', 'error')
    return redirect(url_for('subscriptions.list_subscriptions'))
