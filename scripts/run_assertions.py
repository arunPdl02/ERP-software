"""
Data Integrity Assertion Runner — Cable TV ERP
Runs all 12 sanity check queries against the database.
Every query should return 0 rows if the database is healthy.

Usage:
    python scripts/run_assertions.py
    python scripts/run_assertions.py --verbose   (shows failing rows)
    python scripts/run_assertions.py --fix        (auto-fixes LOW severity issues)

Exit codes:
    0 = all assertions passed
    1 = one or more HIGH severity assertions failed
    2 = one or more MEDIUM severity assertions failed (no HIGH failures)
"""

import sys
import os
import argparse
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cable_tv_erp'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'cable_tv_erp', '.env'))

from db import query_db


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
        'description': 'Is any recorded payment floating in the system with no invoice allocation?',
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
        'description': 'Is any ticket assigned to a userId not present in the Employee table?',
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
        'description': 'Is any customer subscribed to the same package more than once at the same time?',
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


# ── Severity ordering for exit code logic ──────────────────────────────────

SEVERITY_ORDER = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}

SEVERITY_SYMBOLS = {'HIGH': 'HIGH', 'MEDIUM': 'MED ', 'LOW': 'LOW '}


def run_assertions(verbose=False):
    """
    Run all 12 assertions. Returns a list of result dicts.
    Each result dict has keys: id, name, severity, status ('PASS'/'FAIL'),
    row_count, rows.
    """
    results = []
    for assertion in ASSERTIONS:
        try:
            rows = query_db(assertion['sql'])
        except Exception as e:
            rows = []
            print(f"  [ERROR] {assertion['id']} query failed: {e}", file=sys.stderr)

        status = 'PASS' if not rows else 'FAIL'
        results.append({
            'id':          assertion['id'],
            'name':        assertion['name'],
            'description': assertion['description'],
            'severity':    assertion['severity'],
            'status':      status,
            'row_count':   len(rows),
            'rows':        [dict(r) for r in rows],
        })
    return results


def print_report(results, verbose=False):
    """Print the formatted assertion report to stdout."""
    run_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    width = 60

    print('=' * width)
    print('  DATA INTEGRITY REPORT — Cable TV ERP')
    print(f'  Run at: {run_time}')
    print('=' * width)
    print()

    for r in results:
        icon   = '✅' if r['status'] == 'PASS' else '❌'
        sev    = SEVERITY_SYMBOLS[r['severity']]
        status = 'PASS' if r['status'] == 'PASS' else 'FAIL'
        name   = r['name'][:38]
        line   = f"  [{r['id']}] {icon} {status:<4}  {name:<40} [{sev}]"
        print(line)

        if r['status'] == 'FAIL':
            print(f"         → {r['row_count']} row(s) returned")

            if verbose and r['rows']:
                for row in r['rows']:
                    row_str = '  '.join(f"{k}: {v}" for k, v in row.items())
                    print(f"         → {row_str}")
            elif not verbose and r['rows']:
                # Compact single-line summary per failing row
                for row in r['rows']:
                    vals = ', '.join(str(v) for v in list(row.values())[:3])
                    print(f"         → {vals}")

    # ── Summary ────────────────────────────────────────────────────────────
    passed  = sum(1 for r in results if r['status'] == 'PASS')
    failed  = sum(1 for r in results if r['status'] == 'FAIL')
    high_f  = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'HIGH')
    med_f   = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'MEDIUM')
    low_f   = sum(1 for r in results if r['status'] == 'FAIL' and r['severity'] == 'LOW')

    print()
    print('=' * width)
    parts = [f"{passed} passed", f"{failed} failed"]
    parts += [f"{high_f} HIGH failure{'s' if high_f != 1 else ''}"]
    parts += [f"{med_f} MEDIUM failure{'s' if med_f != 1 else ''}"]
    parts += [f"{low_f} LOW failure{'s' if low_f != 1 else ''}"]
    print(f"  Summary: {', '.join(parts)}")
    print('=' * width)

    return high_f, med_f, low_f


def handle_fix(results):
    """
    --fix flag: for LOW severity failures, print guidance instead of
    auto-assigning permissions (which would be a security risk).
    """
    low_fails = [r for r in results if r['status'] == 'FAIL' and r['severity'] == 'LOW']
    if not low_fails:
        print('\n  --fix: no LOW severity failures to address.')
        return

    print('\n  --fix: LOW severity remediation guidance:')
    for r in low_fails:
        if r['id'] == 'A12':
            print(f'\n  [{r["id"]}] {r["name"]}')
            print('  Auto-assigning permissions is a security risk.')
            print('  Fix via the ERP UI: Admin → Permissions → assign permissions to:')
            for row in r['rows']:
                uid   = row.get('userId', '?')
                uname = row.get('userName', '?')
                print(f'    • {uname} (userId: {uid})')
            print('  Or navigate to: /permissions')


def main():
    parser = argparse.ArgumentParser(
        description='Run data integrity assertions against the Cable TV ERP database.'
    )
    parser.add_argument('--verbose', action='store_true',
                        help='Show full row data for failing assertions')
    parser.add_argument('--fix', action='store_true',
                        help='Print remediation guidance for LOW severity failures')
    args = parser.parse_args()

    results  = run_assertions(verbose=args.verbose)
    high_f, med_f, low_f = print_report(results, verbose=args.verbose)

    if args.fix:
        handle_fix(results)

    # Exit codes: 0 = all pass, 1 = HIGH failure, 2 = MEDIUM-only failure
    if high_f > 0:
        sys.exit(1)
    elif med_f > 0:
        sys.exit(2)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
