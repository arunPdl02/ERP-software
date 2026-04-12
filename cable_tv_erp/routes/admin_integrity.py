"""
routes/admin_integrity.py — Data integrity check page (admin only).

GET  /admin/integrity       → render the integrity check UI
POST /admin/integrity/run   → run all 12 assertions, return JSON
"""

import sys
import os
import logging
from datetime import datetime

from flask import Blueprint, render_template, jsonify
from db import query_db
from routes.decorators import admin_required
from routes.auth import login_required_session

integrity_bp = Blueprint('integrity', __name__)

# ── Assertion definitions (mirrors scripts/run_assertions.py) ──────────────

ASSERTIONS = [
    {
        'id': 'A01',
        'name': 'Orphaned Device Status',
        'description': 'Is any device marked assigned but has no active assignment record?',
        'severity': 'HIGH',
        'sql': """
            SELECT d.deviceId, d.cardNumber, d.serialNumber, d.status
            FROM Device d
            WHERE d.status = 'assigned'
            AND d.deviceId NOT IN (
                SELECT da.deviceId
                FROM DeviceAssignment da
                WHERE da.returnedDate IS NULL
            )
        """,
    },
    {
        'id': 'A02',
        'name': 'Available Device Has Open Assignment',
        'description': 'Is any device marked available but still has an open assignment?',
        'severity': 'HIGH',
        'sql': """
            SELECT d.deviceId, d.cardNumber, d.status,
                   da.customerId, da.assignedDate
            FROM Device d
            JOIN DeviceAssignment da ON d.deviceId = da.deviceId
            WHERE d.status = 'available'
            AND da.returnedDate IS NULL
        """,
    },
    {
        'id': 'A03',
        'name': 'Invoice Overpayment',
        'description': 'Has any invoice been allocated more money than its total amount?',
        'severity': 'HIGH',
        'sql': """
            SELECT i.invoiceId, i.totalAmount,
                   SUM(pa.allocatedAmount) AS totalAllocated,
                   SUM(pa.allocatedAmount) - i.totalAmount AS overAmount
            FROM Invoice i
            JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
            GROUP BY i.invoiceId, i.totalAmount
            HAVING SUM(pa.allocatedAmount) > i.totalAmount
        """,
    },
    {
        'id': 'A04',
        'name': 'Active Subscription With No Invoice',
        'description': 'Is any active subscriber being missed by the billing system?',
        'severity': 'MEDIUM',
        'sql': """
            SELECT s.subscriptionId, s.customerId, s.packageId, s.startDate
            FROM Subscription s
            WHERE s.status = 'active'
            AND s.subscriptionId NOT IN (
                SELECT DISTINCT ili.subscriptionId
                FROM InvoiceLineItem ili
            )
        """,
    },
    {
        'id': 'A05',
        'name': 'Payment Not Allocated to Any Invoice',
        'description': 'Is any recorded payment floating with no invoice allocation?',
        'severity': 'MEDIUM',
        'sql': """
            SELECT p.paymentId, p.customerId, p.amount, p.paymentDate, p.method
            FROM Payment p
            WHERE p.paymentId NOT IN (
                SELECT DISTINCT pa.paymentId
                FROM PaymentAllocation pa
            )
        """,
    },
    {
        'id': 'A06',
        'name': 'Invoice Line Item Total Mismatch',
        'description': 'Does the sum of line items on an invoice match the invoice total?',
        'severity': 'HIGH',
        'sql': """
            SELECT i.invoiceId, i.totalAmount AS invoiceTotal,
                   SUM(ili.unitPrice * ili.unitCount) AS lineItemTotal,
                   ABS(i.totalAmount - SUM(ili.unitPrice * ili.unitCount)) AS discrepancy
            FROM Invoice i
            JOIN InvoiceLineItem ili ON i.invoiceId = ili.invoiceId
            GROUP BY i.invoiceId, i.totalAmount
            HAVING ABS(i.totalAmount - SUM(ili.unitPrice * ili.unitCount)) > 0.01
        """,
    },
    {
        'id': 'A07',
        'name': 'Expired Subscription Still Billed',
        'description': 'Is any expired or cancelled subscription tied to an open invoice?',
        'severity': 'MEDIUM',
        'sql': """
            SELECT s.subscriptionId, s.status AS subStatus,
                   i.invoiceId, i.invoiceStatus, i.billingPeriod
            FROM Subscription s
            JOIN InvoiceLineItem ili ON s.subscriptionId = ili.subscriptionId
            JOIN Invoice i ON ili.invoiceId = i.invoiceId
            WHERE s.status IN ('expired', 'cancelled')
            AND i.invoiceStatus IN ('unpaid', 'overdue')
        """,
    },
    {
        'id': 'A08',
        'name': 'Ticket Assigned to Non-Employee',
        'description': 'Is any ticket assigned to a userId not in the Employee table?',
        'severity': 'HIGH',
        'sql': """
            SELECT t.ticketId, t.handledBy, t.status
            FROM Ticket t
            WHERE t.handledBy IS NOT NULL
            AND t.handledBy NOT IN (
                SELECT userId FROM Employee
            )
        """,
    },
    {
        'id': 'A09',
        'name': 'Duplicate Active Subscription',
        'description': 'Is any customer subscribed to the same package more than once simultaneously?',
        'severity': 'HIGH',
        'sql': """
            SELECT customerId, packageId, COUNT(*) AS activeCount
            FROM Subscription
            WHERE status = 'active'
            GROUP BY customerId, packageId
            HAVING COUNT(*) > 1
        """,
    },
    {
        'id': 'A10',
        'name': 'Suspended Customer With Active Subscription',
        'description': 'Is any suspended customer still on an active subscription?',
        'severity': 'MEDIUM',
        'sql': """
            SELECT c.customerId, c.firstName, c.lastName, c.accountStatus,
                   s.subscriptionId, s.packageId, s.status AS subStatus
            FROM Customer c
            JOIN Subscription s ON c.customerId = s.customerId
            WHERE c.accountStatus = 'suspended'
            AND s.status = 'active'
        """,
    },
    {
        'id': 'A11',
        'name': 'Inventory Stock Gone Negative',
        'description': 'Has more stock gone out than ever came in for any item?',
        'severity': 'HIGH',
        'sql': """
            SELECT i.itemId, i.itemName, i.category,
                   COALESCE(SUM(CASE WHEN it.transactionType = 'inbound'
                                THEN tl.quantity ELSE 0 END), 0) AS totalIn,
                   COALESCE(SUM(CASE WHEN it.transactionType = 'outbound'
                                THEN tl.quantity ELSE 0 END), 0) AS totalOut,
                   COALESCE(SUM(CASE WHEN it.transactionType = 'inbound'
                                THEN tl.quantity ELSE 0 END), 0) -
                   COALESCE(SUM(CASE WHEN it.transactionType = 'outbound'
                                THEN tl.quantity ELSE 0 END), 0) AS stockLevel
            FROM Item i
            LEFT JOIN TransactionLine tl ON i.itemId = tl.itemId
            LEFT JOIN InventoryTransaction it ON tl.transactionID = it.transactionID
            GROUP BY i.itemId, i.itemName, i.category
            HAVING stockLevel < 0
        """,
    },
    {
        'id': 'A12',
        'name': 'Employee With No Permissions',
        'description': 'Does any employee have zero permissions assigned?',
        'severity': 'LOW',
        'sql': """
            SELECT u.userId, u.userName
            FROM User u
            JOIN Employee e ON u.userId = e.userId
            WHERE u.userId NOT IN (
                SELECT DISTINCT userId
                FROM RoleHasPermission
            )
        """,
    },
]


def _run_all():
    """Execute all assertions and return structured results + summary."""
    results = []
    for a in ASSERTIONS:
        try:
            rows = query_db(a['sql'])
        except Exception as exc:
            logging.error(f"Assertion {a['id']} query error: {exc}")
            rows = []

        status = 'PASS' if not rows else 'FAIL'
        # Serialise row values so they're JSON-safe
        safe_rows = []
        for row in rows:
            safe_rows.append({k: (str(v) if v is not None else None)
                               for k, v in row.items()})
        results.append({
            'id':          a['id'],
            'name':        a['name'],
            'description': a['description'],
            'severity':    a['severity'],
            'status':      status,
            'row_count':   len(rows),
            'rows':        safe_rows,
        })

    total    = len(results)
    passed   = sum(1 for r in results if r['status'] == 'PASS')
    failed   = total - passed
    high_f   = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'HIGH')
    medium_f = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'MEDIUM')
    low_f    = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'LOW')

    summary = {
        'total':           total,
        'passed':          passed,
        'failed':          failed,
        'high_failures':   high_f,
        'medium_failures': medium_f,
        'low_failures':    low_f,
    }
    return results, summary


# ── Routes ──────────────────────────────────────────────────────────────────

@integrity_bp.route('/admin/integrity')
@login_required_session
@admin_required
def index():
    """Render the integrity check page. Assertions are run via AJAX."""
    assertion_meta = [
        {'id': a['id'], 'name': a['name'],
         'description': a['description'], 'severity': a['severity']}
        for a in ASSERTIONS
    ]
    return render_template(
        'admin/integrity.html',
        assertions=assertion_meta,
        total=len(ASSERTIONS),
    )


@integrity_bp.route('/admin/integrity/run', methods=['POST'])
@login_required_session
@admin_required
def run():
    """Run all 12 assertions and return JSON results."""
    try:
        results, summary = _run_all()
        return jsonify({
            'run_time': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'summary':  summary,
            'results':  results,
        })
    except Exception as exc:
        logging.error(f"Integrity run error: {exc}")
        return jsonify({'error': 'Failed to run integrity checks.'}), 500
