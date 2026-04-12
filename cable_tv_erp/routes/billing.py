from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import login_required_session
from routes.decorators import permission_required
from rag.sync import sync_invoice, sync_payment
from datetime import date
import logging

billing_bp = Blueprint('billing', __name__)


# ---- Invoices ----

@billing_bp.route('/billing/invoices')
@login_required_session
def invoices():
    try:
        status_filter = request.args.get('status', '')
        sql = """
            SELECT i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                   i.issueDate, i.dueDate,
                   c.firstName, c.lastName, c.customerId
            FROM Invoice i
            JOIN Customer c ON i.customerId = c.customerId
        """
        args = ()
        if status_filter:
            sql += " WHERE i.invoiceStatus = %s"
            args = (status_filter,)
        sql += " ORDER BY i.issueDate DESC"
        invoices_list = query_db(sql, args)
        return render_template('billing/invoices.html',
                               invoices=invoices_list,
                               status_filter=status_filter)
    except Exception as e:
        logging.error(f"Invoice list error: {e}")
        flash('Something went wrong loading invoices.', 'error')
        return render_template('billing/invoices.html', invoices=[], status_filter='')


@billing_bp.route('/billing/invoices/<int:iid>')
@login_required_session
def invoice_detail(iid):
    try:
        invoice = query_db(
            """SELECT i.*, c.firstName, c.lastName
               FROM Invoice i JOIN Customer c ON i.customerId = c.customerId
               WHERE i.invoiceId = %s""",
            (iid,), one=True
        )
        if not invoice:
            abort(404)

        line_items = query_db(
            """SELECT il.*, s.status AS subStatus FROM InvoiceLineItem il
               JOIN Subscription s ON il.subscriptionId = s.subscriptionId
               WHERE il.invoiceId = %s ORDER BY il.lineNumber""",
            (iid,)
        )

        allocations = query_db(
            """SELECT pa.allocatedAmount, pa.paymentId,
                      p.paymentDate, p.method, p.amount AS paymentTotal
               FROM PaymentAllocation pa
               JOIN Payment p ON pa.paymentId = p.paymentId
               WHERE pa.invoiceId = %s""",
            (iid,)
        )

        return render_template('billing/invoice_detail.html',
                               invoice=invoice,
                               line_items=line_items,
                               allocations=allocations)
    except Exception as e:
        logging.error(f"Invoice detail error: {e}")
        flash('Something went wrong.', 'error')
        return redirect(url_for('billing.invoices'))


@billing_bp.route('/billing/invoices/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_BILLING')
def new_invoice():
    customers = query_db(
        "SELECT customerId, firstName, lastName FROM Customer ORDER BY lastName"
    )
    subscriptions = query_db(
        """SELECT s.subscriptionId, s.customerId, p.packageName, p.monthlyPrice
           FROM Subscription s JOIN Package p ON s.packageId = p.packageId
           WHERE s.status = 'active' ORDER BY p.packageName"""
    )

    if request.method == 'POST':
        customer_id = request.form.get('customerId')
        subscription_id = request.form.get('subscriptionId')
        billing_period = request.form.get('billingPeriod', '').strip()
        due_date = request.form.get('dueDate', '').strip()
        description = request.form.get('description', '').strip()

        errors = []
        if not customer_id: errors.append('Customer is required.')
        if not subscription_id: errors.append('Subscription is required.')
        if not billing_period: errors.append('Billing period is required.')
        if not due_date: errors.append('Due date is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('billing/new_invoice.html',
                                   customers=customers, subscriptions=subscriptions,
                                   form=request.form)

        try:
            sub = query_db(
                "SELECT s.*, p.monthlyPrice, p.packageName FROM Subscription s JOIN Package p ON s.packageId = p.packageId WHERE s.subscriptionId = %s",
                (subscription_id,), one=True
            )
            if not sub:
                flash('Subscription not found.', 'error')
                return redirect(url_for('billing.new_invoice'))

            amount = sub['monthlyPrice']
            issue_date = date.today().isoformat()
            desc = description if description else f"{sub['packageName']} - {billing_period}"

            inv_id = query_db(
                "INSERT INTO Invoice (customerId, totalAmount, issueDate, dueDate, billingPeriod, invoiceStatus) VALUES (%s, %s, %s, %s, %s, 'unpaid')",
                (customer_id, amount, issue_date, due_date, billing_period), commit=True
            )

            next_line = query_db(
                "SELECT COALESCE(MAX(lineNumber), 0) + 1 AS nl FROM InvoiceLineItem WHERE invoiceId = %s",
                (inv_id,), one=True
            )['nl']

            query_db(
                "INSERT INTO InvoiceLineItem (invoiceId, lineNumber, subscriptionId, description, unitPrice, unitCount) VALUES (%s, %s, %s, %s, %s, 1)",
                (inv_id, next_line, subscription_id, desc, amount), commit=True
            )

            sync_invoice(inv_id)
            flash(f'Invoice #{inv_id} created successfully.', 'success')
            return redirect(url_for('billing.invoice_detail', iid=inv_id))
        except Exception as e:
            logging.error(f"Create invoice error: {e}")
            flash('Something went wrong creating the invoice.', 'error')

    return render_template('billing/new_invoice.html',
                           customers=customers, subscriptions=subscriptions, form={})


@billing_bp.route('/billing/invoices/<int:iid>/mark-paid', methods=['POST'])
@login_required_session
@permission_required('MANAGE_BILLING')
def mark_paid(iid):
    try:
        query_db(
            "UPDATE Invoice SET invoiceStatus='paid' WHERE invoiceId=%s",
            (iid,), commit=True
        )
        sync_invoice(iid)
        flash('Invoice marked as paid.', 'success')
    except Exception as e:
        logging.error(f"Mark paid error: {e}")
        flash('Something went wrong.', 'error')
    return redirect(url_for('billing.invoice_detail', iid=iid))


# ---- Payments ----

@billing_bp.route('/billing/payments')
@login_required_session
def payments():
    try:
        pay_list = query_db(
            """SELECT p.paymentId, p.amount, p.paymentDate, p.method,
                      c.firstName, c.lastName, c.customerId
               FROM Payment p
               JOIN Customer c ON p.customerId = c.customerId
               ORDER BY p.paymentDate DESC"""
        )
        return render_template('billing/payments.html', payments=pay_list)
    except Exception as e:
        logging.error(f"Payments list error: {e}")
        flash('Something went wrong loading payments.', 'error')
        return render_template('billing/payments.html', payments=[])


@billing_bp.route('/billing/payments/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_BILLING')
def new_payment():
    customers = query_db(
        "SELECT customerId, firstName, lastName FROM Customer ORDER BY lastName"
    )

    if request.method == 'POST':
        customer_id = request.form.get('customerId')
        amount = request.form.get('amount', '').strip()
        payment_date = request.form.get('paymentDate', '').strip()
        method = request.form.get('method', '').strip()

        errors = []
        if not customer_id: errors.append('Customer is required.')
        if not amount:
            errors.append('Amount is required.')
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append('Amount must be greater than 0.')
            except ValueError:
                errors.append('Amount must be a valid number.')
        if not payment_date: errors.append('Payment date is required.')
        if not method: errors.append('Payment method is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('billing/new_payment.html', customers=customers, form=request.form)

        try:
            pay_id = query_db(
                "INSERT INTO Payment (customerId, amount, paymentDate, method) VALUES (%s, %s, %s, %s)",
                (customer_id, amount, payment_date, method), commit=True
            )
            sync_payment(pay_id)
            flash(f'Payment #{pay_id} recorded successfully.', 'success')
            return redirect(url_for('billing.payments'))
        except Exception as e:
            logging.error(f"Create payment error: {e}")
            flash('Something went wrong recording the payment.', 'error')

    return render_template('billing/new_payment.html', customers=customers, form={})


# ---- Allocations ----

@billing_bp.route('/billing/allocations')
@login_required_session
def allocations():
    try:
        alloc_list = query_db(
            """SELECT pa.paymentId, pa.invoiceId, pa.allocatedAmount,
                      p.paymentDate, p.method, p.amount AS paymentTotal,
                      c.firstName, c.lastName,
                      i.billingPeriod, i.invoiceStatus
               FROM PaymentAllocation pa
               JOIN Payment p ON pa.paymentId = p.paymentId
               JOIN Customer c ON p.customerId = c.customerId
               JOIN Invoice i ON pa.invoiceId = i.invoiceId
               ORDER BY pa.paymentId DESC"""
        )
        return render_template('billing/allocations.html', allocations=alloc_list)
    except Exception as e:
        logging.error(f"Allocations list error: {e}")
        flash('Something went wrong loading allocations.', 'error')
        return render_template('billing/allocations.html', allocations=[])


@billing_bp.route('/billing/allocations/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_BILLING')
def new_allocation():
    payments = query_db(
        """SELECT p.paymentId, p.amount, p.paymentDate, p.method,
                  c.firstName, c.lastName,
                  COALESCE(SUM(pa.allocatedAmount), 0) AS allocated
           FROM Payment p
           JOIN Customer c ON p.customerId = c.customerId
           LEFT JOIN PaymentAllocation pa ON p.paymentId = pa.paymentId
           GROUP BY p.paymentId, p.amount, p.paymentDate, p.method, c.firstName, c.lastName
           HAVING (p.amount - COALESCE(SUM(pa.allocatedAmount), 0)) > 0
           ORDER BY p.paymentDate DESC"""
    )
    invoices = query_db(
        """SELECT i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                  c.firstName, c.lastName,
                  COALESCE(SUM(pa.allocatedAmount), 0) AS paid
           FROM Invoice i
           JOIN Customer c ON i.customerId = c.customerId
           LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
           WHERE i.invoiceStatus != 'paid'
           GROUP BY i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus, c.firstName, c.lastName
           ORDER BY i.dueDate ASC"""
    )

    if request.method == 'POST':
        payment_id = request.form.get('paymentId')
        invoice_id = request.form.get('invoiceId')
        amount = request.form.get('allocatedAmount', '').strip()

        errors = []
        if not payment_id: errors.append('Payment is required.')
        if not invoice_id: errors.append('Invoice is required.')
        if not amount:
            errors.append('Amount is required.')
        else:
            try:
                amount = float(amount)
                if amount <= 0:
                    errors.append('Amount must be greater than 0.')
            except ValueError:
                errors.append('Amount must be a valid number.')

        if not errors:
            try:
                # Validate payment remaining
                payment = query_db(
                    """SELECT p.amount, COALESCE(SUM(pa.allocatedAmount), 0) AS allocated
                       FROM Payment p
                       LEFT JOIN PaymentAllocation pa ON p.paymentId = pa.paymentId
                       WHERE p.paymentId = %s
                       GROUP BY p.paymentId, p.amount""",
                    (payment_id,), one=True
                )
                if not payment:
                    errors.append('Payment not found.')
                else:
                    remaining = float(payment['amount']) - float(payment['allocated'])
                    if amount > remaining:
                        errors.append(f'Amount exceeds remaining payment balance ({remaining:.2f}).')

                # Validate invoice remaining
                invoice = query_db(
                    """SELECT i.totalAmount, COALESCE(SUM(pa.allocatedAmount), 0) AS paid
                       FROM Invoice i
                       LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
                       WHERE i.invoiceId = %s
                       GROUP BY i.invoiceId, i.totalAmount""",
                    (invoice_id,), one=True
                )
                if not invoice:
                    errors.append('Invoice not found.')
                else:
                    balance = float(invoice['totalAmount']) - float(invoice['paid'])
                    if amount > balance:
                        errors.append(f'Amount exceeds invoice balance ({balance:.2f}).')

                # Check duplicate allocation
                existing_alloc = query_db(
                    "SELECT * FROM PaymentAllocation WHERE paymentId=%s AND invoiceId=%s",
                    (payment_id, invoice_id), one=True
                )
                if existing_alloc:
                    errors.append('An allocation already exists for this payment/invoice pair.')

            except Exception as e:
                logging.error(f"Allocation validation error: {e}")
                errors.append('Something went wrong validating the allocation.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('billing/new_allocation.html',
                                   payments=payments, invoices=invoices, form=request.form)

        try:
            query_db(
                "INSERT INTO PaymentAllocation (paymentId, invoiceId, allocatedAmount) VALUES (%s, %s, %s)",
                (payment_id, invoice_id, amount), commit=True
            )
            # Auto-update invoice status if fully paid
            inv_check = query_db(
                """SELECT i.totalAmount, COALESCE(SUM(pa.allocatedAmount), 0) AS paid
                   FROM Invoice i
                   LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
                   WHERE i.invoiceId = %s
                   GROUP BY i.invoiceId, i.totalAmount""",
                (invoice_id,), one=True
            )
            if inv_check and float(inv_check['paid']) >= float(inv_check['totalAmount']):
                query_db(
                    "UPDATE Invoice SET invoiceStatus='paid' WHERE invoiceId=%s",
                    (invoice_id,), commit=True
                )
            sync_invoice(int(invoice_id))
            flash('Allocation created successfully.', 'success')
            return redirect(url_for('billing.allocations'))
        except Exception as e:
            logging.error(f"Create allocation error: {e}")
            flash('Something went wrong creating the allocation.', 'error')

    return render_template('billing/new_allocation.html',
                           payments=payments, invoices=invoices, form={})
