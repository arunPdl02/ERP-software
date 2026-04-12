from flask import Blueprint, render_template
from db import query_db
from routes.auth import login_required_session
import logging

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
@login_required_session
def index():
    try:
        active_customers = query_db(
            "SELECT COUNT(*) AS cnt FROM Customer WHERE accountStatus = 'active'",
            one=True
        )['cnt']

        active_subs = query_db(
            "SELECT COUNT(*) AS cnt FROM Subscription WHERE status = 'active'",
            one=True
        )['cnt']

        overdue_invoices_count = query_db(
            "SELECT COUNT(*) AS cnt FROM Invoice WHERE invoiceStatus = 'overdue'",
            one=True
        )['cnt']

        monthly_revenue_row = query_db(
            """SELECT COALESCE(SUM(amount), 0) AS rev FROM Payment
               WHERE DATE_FORMAT(paymentDate, '%Y-%m') = DATE_FORMAT(
                   (SELECT MAX(paymentDate) FROM Payment), '%Y-%m')""",
            one=True
        )
        monthly_revenue = monthly_revenue_row['rev'] if monthly_revenue_row else 0

        inventory_items = query_db(
            "SELECT COUNT(*) AS cnt FROM Item",
            one=True
        )['cnt']

        open_tickets = query_db(
            "SELECT COUNT(*) AS cnt FROM Ticket WHERE status = 'open'",
            one=True
        )['cnt']

        recent_tickets = query_db(
            """SELECT t.ticketId, c.firstName, c.lastName, t.priority, t.status,
                      t.createdAt, u.userName AS employeeName
               FROM Ticket t
               JOIN Customer c ON t.customerId = c.customerId
               LEFT JOIN User u ON t.handledBy = u.userId
               ORDER BY t.createdAt DESC LIMIT 5"""
        )

        overdue_invoices = query_db(
            """SELECT i.invoiceId, c.firstName, c.lastName,
                      i.totalAmount, i.dueDate, i.billingPeriod
               FROM Invoice i
               JOIN Customer c ON i.customerId = c.customerId
               WHERE i.invoiceStatus = 'overdue'
               ORDER BY i.dueDate ASC"""
        )

        return render_template('dashboard.html',
                               active_customers=active_customers,
                               active_subs=active_subs,
                               overdue_invoices_count=overdue_invoices_count,
                               monthly_revenue=monthly_revenue,
                               inventory_items=inventory_items,
                               open_tickets=open_tickets,
                               recent_tickets=recent_tickets,
                               overdue_invoices=overdue_invoices)
    except Exception as e:
        logging.error(f"Dashboard error: {e}")
        return render_template('dashboard.html',
                               active_customers=0, active_subs=0,
                               overdue_invoices_count=0, monthly_revenue=0,
                               inventory_items=0, open_tickets=0,
                               recent_tickets=[], overdue_invoices=[])
