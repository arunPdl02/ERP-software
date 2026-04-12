from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_db
from routes.auth import login_required_session
from routes.decorators import admin_required, permission_required
import logging

reports_bp = Blueprint('reports', __name__)

REPORT_SQL = {
    1: {
        'title': 'Active Customer Subscriptions by Monthly Price',
        'description': 'Selection + Projection + Multi-table Join + ORDER BY',
        'sql': """SELECT c.customerId, c.firstName, c.lastName,
       p.packageName, p.monthlyPrice, s.startDate, s.status
FROM Customer c
JOIN Subscription s ON c.customerId = s.customerId
JOIN Package p ON s.packageId = p.packageId
WHERE s.status = 'active'
ORDER BY p.monthlyPrice DESC"""
    },
    2: {
        'title': 'Monthly Revenue Summary',
        'description': 'Aggregation',
        'sql': """SELECT DATE_FORMAT(paymentDate, '%Y-%m') AS month,
       COUNT(*) AS paymentCount,
       SUM(amount) AS totalRevenue
FROM Payment
GROUP BY DATE_FORMAT(paymentDate, '%Y-%m')
ORDER BY month DESC"""
    },
    3: {
        'title': 'Customers with Outstanding Balances (Overdue Invoices)',
        'description': 'Nested subquery',
        'sql': """SELECT c.customerId, c.firstName, c.lastName, c.accountStatus
FROM Customer c
WHERE c.customerId IN (
    SELECT i.customerId
    FROM Invoice i
    WHERE i.invoiceStatus = 'overdue'
)"""
    },
    4: {
        'title': 'Employees Who Have Not Handled Any Ticket',
        'description': 'NOT EXISTS (Division-like)',
        'sql': """SELECT u.userId, u.userName
FROM User u
JOIN Employee e ON u.userId = e.userId
WHERE NOT EXISTS (
    SELECT 1 FROM Ticket t WHERE t.handledBy = u.userId
)"""
    },
    5: {
        'title': 'Customers Subscribed to Every Available Package',
        'description': 'Division using NOT EXISTS double-negation',
        'sql': """SELECT c.customerId, c.firstName, c.lastName
FROM Customer c
WHERE NOT EXISTS (
    SELECT p.packageId FROM Package p
    WHERE NOT EXISTS (
        SELECT s.subscriptionId FROM Subscription s
        WHERE s.customerId = c.customerId AND s.packageId = p.packageId
    )
)"""
    },
    6: {
        'title': 'Invoice Payment Completion Status',
        'description': 'Left join with aggregation showing balance remaining',
        'sql': """SELECT i.invoiceId, c.firstName, c.lastName, i.billingPeriod,
       i.totalAmount, COALESCE(SUM(pa.allocatedAmount),0) AS paid,
       (i.totalAmount - COALESCE(SUM(pa.allocatedAmount),0)) AS balance,
       i.invoiceStatus
FROM Invoice i
JOIN Customer c ON i.customerId = c.customerId
LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
GROUP BY i.invoiceId, c.firstName, c.lastName,
         i.billingPeriod, i.totalAmount, i.invoiceStatus
ORDER BY balance DESC"""
    },
    7: {
        'title': 'Current Device Assignment Status',
        'description': 'Join across four tables',
        'sql': """SELECT d.deviceId, it.itemName, d.cardNumber, d.serialNumber, d.status,
       c.firstName, c.lastName, da.assignedDate, da.returnedDate
FROM Device d
JOIN Item it ON d.itemId = it.itemId
LEFT JOIN DeviceAssignment da ON d.deviceId = da.deviceId AND da.returnedDate IS NULL
LEFT JOIN Customer c ON da.customerId = c.customerId
ORDER BY d.status, it.itemName"""
    },
    8: {
        'title': 'Inventory Stock Level per Item',
        'description': 'Conditional aggregation (inbound vs outbound)',
        'sql': """SELECT i.itemId, i.itemName, i.category,
       COALESCE(SUM(CASE WHEN it2.transactionType='inbound' THEN tl.quantity ELSE 0 END),0)
         AS totalIn,
       COALESCE(SUM(CASE WHEN it2.transactionType='outbound' THEN tl.quantity ELSE 0 END),0)
         AS totalOut,
       COALESCE(SUM(CASE WHEN it2.transactionType='inbound' THEN tl.quantity ELSE 0 END),0)
         - COALESCE(SUM(CASE WHEN it2.transactionType='outbound' THEN tl.quantity ELSE 0 END),0)
         AS stockLevel
FROM Item i
LEFT JOIN TransactionLine tl ON i.itemId = tl.itemId
LEFT JOIN InventoryTransaction it2 ON tl.transactionID = it2.transactionID
GROUP BY i.itemId, i.itemName, i.category"""
    },
    9: {
        'title': 'Ticket Resolution Rate by Employee',
        'description': 'Aggregation with CASE',
        'sql': """SELECT u.userId, u.userName,
       COUNT(t.ticketId) AS totalTickets,
       SUM(CASE WHEN t.status = 'resolved' THEN 1 ELSE 0 END) AS resolvedTickets,
       ROUND(100.0 * SUM(CASE WHEN t.status = 'resolved' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(t.ticketId),0), 1) AS resolutionRate
FROM User u
JOIN Employee e ON u.userId = e.userId
LEFT JOIN Ticket t ON u.userId = t.handledBy
GROUP BY u.userId, u.userName"""
    },
    10: {
        'title': 'Admin Permission Summary',
        'description': 'Customers with overdue invoice counts. Includes "Reactivate Eligible Accounts" action.',
        'sql': """SELECT c.customerId, c.firstName, c.lastName, c.accountStatus,
       COUNT(i.invoiceId) AS overdueCount
FROM Customer c
LEFT JOIN Invoice i ON c.customerId = i.customerId AND i.invoiceStatus = 'overdue'
GROUP BY c.customerId, c.firstName, c.lastName, c.accountStatus
ORDER BY overdueCount DESC"""
    }
}


@reports_bp.route('/reports')
@login_required_session
@permission_required('VIEW_REPORTS')
def index():
    results = {}
    errors = {}

    for num, report in REPORT_SQL.items():
        try:
            rows = query_db(report['sql'])
            results[num] = rows
        except Exception as e:
            logging.error(f"Report {num} error: {e}")
            errors[num] = str(e)
            results[num] = []

    return render_template('reports/index.html',
                           reports=REPORT_SQL,
                           results=results,
                           errors=errors)


@reports_bp.route('/reports/reactivate', methods=['POST'])
@login_required_session
@admin_required
def reactivate_accounts():
    try:
        rows_updated = query_db(
            """UPDATE Customer
               SET accountStatus = 'active'
               WHERE accountStatus = 'suspended'
               AND customerId NOT IN (
                   SELECT customerId FROM Invoice WHERE invoiceStatus = 'overdue'
               )""",
            commit=True
        )
        flash(f'{rows_updated} account(s) reactivated successfully.', 'success')
    except Exception as e:
        logging.error(f"Reactivate accounts error: {e}")
        flash('Something went wrong reactivating accounts.', 'error')
    return redirect(url_for('reports.index') + '#report-10')
