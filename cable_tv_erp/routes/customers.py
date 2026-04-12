from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import login_required_session
from routes.decorators import admin_required, permission_required
from rag.sync import sync_customer, remove_customer
import logging

customers_bp = Blueprint('customers', __name__)


@customers_bp.route('/customers')
@login_required_session
def list_customers():
    try:
        search = request.args.get('q', '').strip()
        sql = """
            SELECT c.customerId, c.firstName, c.lastName, c.accountStatus,
                   COUNT(DISTINCT s.subscriptionId) AS activeSubs,
                   COUNT(DISTINCT t.ticketId) AS openTickets
            FROM Customer c
            LEFT JOIN Subscription s ON c.customerId = s.customerId AND s.status = 'active'
            LEFT JOIN Ticket t ON c.customerId = t.customerId AND t.status = 'open'
        """
        args = ()
        if search:
            sql += " WHERE c.firstName LIKE %s OR c.lastName LIKE %s OR CONCAT(c.firstName,' ',c.lastName) LIKE %s"
            like = f'%{search}%'
            args = (like, like, like)
        sql += " GROUP BY c.customerId, c.firstName, c.lastName, c.accountStatus ORDER BY c.lastName, c.firstName"
        customers = query_db(sql, args)
        return render_template('customers/list.html', customers=customers, search=search)
    except Exception as e:
        logging.error(f"Customer list error: {e}")
        flash('Something went wrong loading customers.', 'error')
        return render_template('customers/list.html', customers=[], search='')


@customers_bp.route('/customers/<int:cid>')
@login_required_session
def detail(cid):
    try:
        customer = query_db(
            "SELECT c.* FROM Customer c WHERE c.customerId = %s",
            (cid,), one=True
        )
        if not customer:
            abort(404)

        subscriptions = query_db(
            """SELECT s.*, p.packageName, p.monthlyPrice FROM Subscription s
               JOIN Package p ON s.packageId = p.packageId
               WHERE s.customerId = %s ORDER BY s.startDate DESC""",
            (cid,)
        )

        invoices = query_db(
            """SELECT i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                      i.issueDate, i.dueDate,
                      COALESCE(SUM(pa.allocatedAmount), 0) AS totalPaid,
                      (i.totalAmount - COALESCE(SUM(pa.allocatedAmount), 0)) AS balance
               FROM Invoice i
               LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
               WHERE i.customerId = %s
               GROUP BY i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus, i.issueDate, i.dueDate
               ORDER BY i.issueDate DESC""",
            (cid,)
        )

        devices = query_db(
            """SELECT da.assignmentId, da.assignedDate, da.returnedDate,
                      d.deviceId, d.cardNumber, d.serialNumber, d.status AS deviceStatus,
                      it.itemName
               FROM DeviceAssignment da
               JOIN Device d ON da.deviceId = d.deviceId
               JOIN Item it ON d.itemId = it.itemId
               WHERE da.customerId = %s ORDER BY da.assignedDate DESC""",
            (cid,)
        )

        tickets = query_db(
            """SELECT t.ticketId, t.priority, t.status, t.createdAt,
                      u.userName AS employeeName
               FROM Ticket t
               LEFT JOIN User u ON t.handledBy = u.userId
               WHERE t.customerId = %s ORDER BY t.createdAt DESC""",
            (cid,)
        )

        return render_template('customers/detail.html',
                               customer=customer,
                               subscriptions=subscriptions,
                               invoices=invoices,
                               devices=devices,
                               tickets=tickets)
    except Exception as e:
        logging.error(f"Customer detail error: {e}")
        flash('Something went wrong.', 'error')
        return redirect(url_for('customers.list_customers'))


@customers_bp.route('/customers/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_CUSTOMERS')
def new_customer():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('account_status', 'active')

        errors = []
        if not first_name: errors.append('First name is required.')
        if not last_name: errors.append('Last name is required.')
        if not address: errors.append('Address is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('customers/form.html', action='new', form=request.form)

        try:
            new_id = query_db(
                "INSERT INTO Customer (firstName, lastName, address, accountStatus) VALUES (%s, %s, %s, %s)",
                (first_name, last_name, address, status), commit=True
            )
            sync_customer(new_id)
            flash(f'Customer {first_name} {last_name} created successfully.', 'success')
            return redirect(url_for('customers.detail', cid=new_id))
        except Exception as e:
            logging.error(f"Create customer error: {e}")
            flash('Something went wrong creating the customer.', 'error')
            return render_template('customers/form.html', action='new', form=request.form)

    return render_template('customers/form.html', action='new', form={})


@customers_bp.route('/customers/<int:cid>/edit', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_CUSTOMERS')
def edit_customer(cid):
    customer = query_db(
        "SELECT c.* FROM Customer c WHERE c.customerId = %s",
        (cid,), one=True
    )
    if not customer:
        abort(404)

    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        address = request.form.get('address', '').strip()
        status = request.form.get('account_status', 'active')

        errors = []
        if not first_name: errors.append('First name is required.')
        if not last_name: errors.append('Last name is required.')
        if not address: errors.append('Address is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('customers/form.html', action='edit', customer=customer, form=request.form)

        try:
            query_db(
                "UPDATE Customer SET firstName=%s, lastName=%s, address=%s, accountStatus=%s WHERE customerId=%s",
                (first_name, last_name, address, status, cid), commit=True
            )
            sync_customer(cid)
            flash('Customer updated successfully.', 'success')
            return redirect(url_for('customers.detail', cid=cid))
        except Exception as e:
            logging.error(f"Edit customer error: {e}")
            flash('Something went wrong updating the customer.', 'error')

    return render_template('customers/form.html', action='edit', customer=customer, form=customer)


@customers_bp.route('/customers/<int:cid>/delete', methods=['POST'])
@admin_required
def delete_customer(cid):
    try:
        customer = query_db("SELECT * FROM Customer WHERE customerId = %s", (cid,), one=True)
        if not customer:
            abort(404)
        remove_customer(cid)
        query_db("DELETE FROM Customer WHERE customerId = %s", (cid,), commit=True)
        flash('Customer deleted successfully.', 'success')
    except Exception as e:
        logging.error(f"Delete customer error: {e}")
        flash('Something went wrong deleting the customer.', 'error')
    return redirect(url_for('customers.list_customers'))
