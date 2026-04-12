"""
rag/exporter.py — Export MySQL ERP data as plain-text documents for RAG indexing.

Each document is a self-contained, human-readable description of one record.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from db import query_db


def export_customers():
    """Export one document per customer with subscription/ticket/invoice summary."""
    rows = query_db(
        """
        SELECT c.customerId, c.firstName, c.lastName, c.address, c.accountStatus
        FROM Customer c
        ORDER BY c.customerId
        """
    )
    chunks = []
    for r in rows:
        cid = r['customerId']

        # Active subscriptions
        subs = query_db(
            """
            SELECT p.packageName, p.monthlyPrice, s.startDate
            FROM Subscription s
            JOIN Package p ON s.packageId = p.packageId
            WHERE s.customerId = %s AND s.status = 'active'
            """,
            (cid,)
        )
        subs_text = ', '.join(
            f"{s['packageName']} (${float(s['monthlyPrice']):.2f}/month) since {s['startDate']}"
            for s in subs
        ) if subs else 'None'

        # Open ticket count
        open_tickets = query_db(
            "SELECT COUNT(*) AS cnt FROM Ticket WHERE customerId = %s AND status = 'open'",
            (cid,), one=True
        )['cnt']

        # Overdue invoice count
        overdue_inv = query_db(
            "SELECT COUNT(*) AS cnt FROM Invoice WHERE customerId = %s AND invoiceStatus = 'overdue'",
            (cid,), one=True
        )['cnt']

        text = (
            f"Customer ID: {cid}\n"
            f"Name: {r['firstName']} {r['lastName']}\n"
            f"Address: {r['address']}\n"
            f"Account Status: {r['accountStatus']}\n"
            f"Active Subscriptions: {subs_text}\n"
            f"Open Tickets: {open_tickets}\n"
            f"Overdue Invoices: {overdue_inv}"
        )
        chunks.append({
            'id': f"customer_{cid}",
            'text': text,
            'metadata': {'table': 'customer', 'record_id': str(cid)}
        })
    return chunks


def export_packages():
    """Export one document per package."""
    rows = query_db(
        """
        SELECT p.packageId, p.packageName, p.monthlyPrice,
               COUNT(s.subscriptionId) AS activeSubs
        FROM Package p
        LEFT JOIN Subscription s ON p.packageId = s.packageId AND s.status = 'active'
        GROUP BY p.packageId, p.packageName, p.monthlyPrice
        ORDER BY p.packageId
        """
    )
    chunks = []
    for r in rows:
        text = (
            f"Package ID: {r['packageId']}\n"
            f"Name: {r['packageName']}\n"
            f"Monthly Price: ${float(r['monthlyPrice']):.2f}\n"
            f"Active Subscribers: {r['activeSubs']}"
        )
        chunks.append({
            'id': f"package_{r['packageId']}",
            'text': text,
            'metadata': {'table': 'package', 'record_id': str(r['packageId'])}
        })
    return chunks


def export_subscriptions():
    """Export one document per subscription."""
    rows = query_db(
        """
        SELECT s.subscriptionId, s.startDate, s.endDate, s.status,
               c.customerId, c.firstName, c.lastName,
               p.packageName, p.monthlyPrice
        FROM Subscription s
        JOIN Customer c ON s.customerId = c.customerId
        JOIN Package p ON s.packageId = p.packageId
        ORDER BY s.subscriptionId
        """
    )
    chunks = []
    for r in rows:
        end_date = str(r['endDate']) if r['endDate'] else 'N/A'
        text = (
            f"Subscription ID: {r['subscriptionId']}\n"
            f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
            f"Package: {r['packageName']} (${float(r['monthlyPrice']):.2f}/month)\n"
            f"Start Date: {r['startDate']}\n"
            f"End Date: {end_date}\n"
            f"Status: {r['status']}"
        )
        chunks.append({
            'id': f"subscription_{r['subscriptionId']}",
            'text': text,
            'metadata': {'table': 'subscription', 'record_id': str(r['subscriptionId'])}
        })
    return chunks


def export_invoices():
    """Export one document per invoice with payment allocation info."""
    rows = query_db(
        """
        SELECT i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
               i.issueDate, i.dueDate,
               c.customerId, c.firstName, c.lastName,
               COALESCE(SUM(pa.allocatedAmount), 0) AS amountPaid
        FROM Invoice i
        JOIN Customer c ON i.customerId = c.customerId
        LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
        GROUP BY i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                 i.issueDate, i.dueDate, c.customerId, c.firstName, c.lastName
        ORDER BY i.invoiceId
        """
    )
    chunks = []
    for r in rows:
        total = float(r['totalAmount'])
        paid = float(r['amountPaid'])
        balance = total - paid
        text = (
            f"Invoice ID: {r['invoiceId']}\n"
            f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
            f"Billing Period: {r['billingPeriod']}\n"
            f"Total Amount: ${total:.2f}\n"
            f"Amount Paid: ${paid:.2f}\n"
            f"Balance: ${balance:.2f}\n"
            f"Status: {r['invoiceStatus']}\n"
            f"Due Date: {r['dueDate']}"
        )
        chunks.append({
            'id': f"invoice_{r['invoiceId']}",
            'text': text,
            'metadata': {'table': 'invoice', 'record_id': str(r['invoiceId'])}
        })
    return chunks


def export_payments():
    """Export one document per payment with allocation details."""
    rows = query_db(
        """
        SELECT p.paymentId, p.amount, p.paymentDate, p.method,
               c.customerId, c.firstName, c.lastName
        FROM Payment p
        JOIN Customer c ON p.customerId = c.customerId
        ORDER BY p.paymentId
        """
    )
    chunks = []
    for r in rows:
        # Get allocations for this payment
        allocs = query_db(
            """
            SELECT pa.invoiceId, pa.allocatedAmount
            FROM PaymentAllocation pa
            WHERE pa.paymentId = %s
            """,
            (r['paymentId'],)
        )
        alloc_text = ', '.join(
            f"Invoice #{a['invoiceId']} (${float(a['allocatedAmount']):.2f})"
            for a in allocs
        ) if allocs else 'None'

        text = (
            f"Payment ID: {r['paymentId']}\n"
            f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
            f"Amount: ${float(r['amount']):.2f}\n"
            f"Date: {r['paymentDate']}\n"
            f"Method: {r['method']}\n"
            f"Allocated To Invoice(s): {alloc_text}"
        )
        chunks.append({
            'id': f"payment_{r['paymentId']}",
            'text': text,
            'metadata': {'table': 'payment', 'record_id': str(r['paymentId'])}
        })
    return chunks


def export_tickets():
    """Export one document per ticket."""
    rows = query_db(
        """
        SELECT t.ticketId, t.priority, t.status, t.createdAt, t.handledBy,
               c.customerId, c.firstName, c.lastName,
               u.userName AS employeeName
        FROM Ticket t
        JOIN Customer c ON t.customerId = c.customerId
        LEFT JOIN User u ON t.handledBy = u.userId
        ORDER BY t.ticketId
        """
    )
    chunks = []
    for r in rows:
        if r['handledBy'] and r['employeeName']:
            handler = f"{r['employeeName']} (Employee ID: {r['handledBy']})"
        else:
            handler = 'Unassigned'

        text = (
            f"Ticket ID: {r['ticketId']}\n"
            f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
            f"Handled By: {handler}\n"
            f"Priority: {r['priority']}\n"
            f"Status: {r['status']}\n"
            f"Created: {r['createdAt']}"
        )
        chunks.append({
            'id': f"ticket_{r['ticketId']}",
            'text': text,
            'metadata': {'table': 'ticket', 'record_id': str(r['ticketId'])}
        })
    return chunks


def export_devices():
    """Export one document per device with assignment info."""
    rows = query_db(
        """
        SELECT d.deviceId, d.cardNumber, d.serialNumber, d.status,
               it.itemName,
               da.customerId AS assignedCustomerId,
               da.assignedDate,
               c.firstName, c.lastName
        FROM Device d
        JOIN Item it ON d.itemId = it.itemId
        LEFT JOIN DeviceAssignment da ON d.deviceId = da.deviceId AND da.returnedDate IS NULL
        LEFT JOIN Customer c ON da.customerId = c.customerId
        ORDER BY d.deviceId
        """
    )
    chunks = []
    for r in rows:
        if r['assignedCustomerId']:
            assignment = (
                f"{r['firstName']} {r['lastName']} (ID: {r['assignedCustomerId']}) "
                f"since {r['assignedDate']}"
            )
        else:
            assignment = 'Not assigned'

        text = (
            f"Device ID: {r['deviceId']}\n"
            f"Item: {r['itemName']}\n"
            f"Card Number: {r['cardNumber']}\n"
            f"Serial Number: {r['serialNumber']}\n"
            f"Status: {r['status']}\n"
            f"Currently Assigned To: {assignment}"
        )
        chunks.append({
            'id': f"device_{r['deviceId']}",
            'text': text,
            'metadata': {'table': 'device', 'record_id': str(r['deviceId'])}
        })
    return chunks


def export_inventory_summary():
    """Export one document per item with stock level computed from transactions."""
    rows = query_db(
        """
        SELECT i.itemId, i.itemName, i.category,
               COALESCE(SUM(CASE WHEN it2.transactionType='inbound'  THEN tl.quantity ELSE 0 END), 0) AS totalIn,
               COALESCE(SUM(CASE WHEN it2.transactionType='outbound' THEN tl.quantity ELSE 0 END), 0) AS totalOut
        FROM Item i
        LEFT JOIN TransactionLine tl ON i.itemId = tl.itemId
        LEFT JOIN InventoryTransaction it2 ON tl.transactionID = it2.transactionID
        GROUP BY i.itemId, i.itemName, i.category
        ORDER BY i.itemId
        """
    )
    chunks = []
    for r in rows:
        total_in = int(r['totalIn'])
        total_out = int(r['totalOut'])
        stock = total_in - total_out
        text = (
            f"Item ID: {r['itemId']}\n"
            f"Name: {r['itemName']}\n"
            f"Category: {r['category']}\n"
            f"Total Inbound: {total_in}\n"
            f"Total Outbound: {total_out}\n"
            f"Current Stock Level: {stock}"
        )
        chunks.append({
            'id': f"inventory_{r['itemId']}",
            'text': text,
            'metadata': {'table': 'inventory', 'record_id': str(r['itemId'])}
        })
    return chunks


def export_permissions():
    """Export one document per user (admin or employee) showing their permissions."""
    users = query_db(
        """
        SELECT u.userId, u.userName,
               CASE WHEN a.userId IS NOT NULL THEN 'admin' ELSE 'employee' END AS role
        FROM User u
        LEFT JOIN Admin a ON u.userId = a.userId
        LEFT JOIN Employee e ON u.userId = e.userId
        WHERE a.userId IS NOT NULL OR e.userId IS NOT NULL
        ORDER BY u.userId
        """
    )
    chunks = []
    for u in users:
        perms = query_db(
            "SELECT permissionCode FROM RoleHasPermission WHERE userId = %s ORDER BY permissionCode",
            (u['userId'],)
        )
        perm_list = ', '.join(p['permissionCode'] for p in perms) if perms else 'None'
        text = (
            f"User ID: {u['userId']}\n"
            f"Username: {u['userName']}\n"
            f"Role: {u['role']}\n"
            f"Permissions: {perm_list}"
        )
        chunks.append({
            'id': f"permission_{u['userId']}",
            'text': text,
            'metadata': {'table': 'permission', 'record_id': str(u['userId'])}
        })
    return chunks


def export_single_customer(customer_id: int):
    """Export one customer record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        "SELECT customerId, firstName, lastName, address, accountStatus FROM Customer WHERE customerId = %s",
        (customer_id,), one=True
    )
    if not r:
        return None
    cid = r['customerId']
    subs = query_db(
        """SELECT p.packageName, p.monthlyPrice, s.startDate
           FROM Subscription s JOIN Package p ON s.packageId = p.packageId
           WHERE s.customerId = %s AND s.status = 'active'""",
        (cid,)
    )
    subs_text = ', '.join(
        f"{s['packageName']} (${float(s['monthlyPrice']):.2f}/month) since {s['startDate']}"
        for s in subs
    ) if subs else 'None'
    open_tickets = query_db(
        "SELECT COUNT(*) AS cnt FROM Ticket WHERE customerId = %s AND status = 'open'",
        (cid,), one=True
    )['cnt']
    overdue_inv = query_db(
        "SELECT COUNT(*) AS cnt FROM Invoice WHERE customerId = %s AND invoiceStatus = 'overdue'",
        (cid,), one=True
    )['cnt']
    text = (
        f"Customer ID: {cid}\n"
        f"Name: {r['firstName']} {r['lastName']}\n"
        f"Address: {r['address']}\n"
        f"Account Status: {r['accountStatus']}\n"
        f"Active Subscriptions: {subs_text}\n"
        f"Open Tickets: {open_tickets}\n"
        f"Overdue Invoices: {overdue_inv}"
    )
    return {'id': f"customer_{cid}", 'text': text, 'metadata': {'table': 'customer', 'record_id': str(cid)}}


def export_single_subscription(subscription_id: int):
    """Export one subscription record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT s.subscriptionId, s.startDate, s.endDate, s.status,
                  c.customerId, c.firstName, c.lastName, p.packageName, p.monthlyPrice
           FROM Subscription s
           JOIN Customer c ON s.customerId = c.customerId
           JOIN Package p ON s.packageId = p.packageId
           WHERE s.subscriptionId = %s""",
        (subscription_id,), one=True
    )
    if not r:
        return None
    end_date = str(r['endDate']) if r['endDate'] else 'N/A'
    text = (
        f"Subscription ID: {r['subscriptionId']}\n"
        f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
        f"Package: {r['packageName']} (${float(r['monthlyPrice']):.2f}/month)\n"
        f"Start Date: {r['startDate']}\n"
        f"End Date: {end_date}\n"
        f"Status: {r['status']}"
    )
    return {'id': f"subscription_{r['subscriptionId']}", 'text': text, 'metadata': {'table': 'subscription', 'record_id': str(r['subscriptionId'])}}


def export_single_invoice(invoice_id: int):
    """Export one invoice record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                  i.issueDate, i.dueDate, c.customerId, c.firstName, c.lastName,
                  COALESCE(SUM(pa.allocatedAmount), 0) AS amountPaid
           FROM Invoice i
           JOIN Customer c ON i.customerId = c.customerId
           LEFT JOIN PaymentAllocation pa ON i.invoiceId = pa.invoiceId
           WHERE i.invoiceId = %s
           GROUP BY i.invoiceId, i.billingPeriod, i.totalAmount, i.invoiceStatus,
                    i.issueDate, i.dueDate, c.customerId, c.firstName, c.lastName""",
        (invoice_id,), one=True
    )
    if not r:
        return None
    total = float(r['totalAmount'])
    paid = float(r['amountPaid'])
    text = (
        f"Invoice ID: {r['invoiceId']}\n"
        f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
        f"Billing Period: {r['billingPeriod']}\n"
        f"Total Amount: ${total:.2f}\n"
        f"Amount Paid: ${paid:.2f}\n"
        f"Balance: ${total - paid:.2f}\n"
        f"Status: {r['invoiceStatus']}\n"
        f"Due Date: {r['dueDate']}"
    )
    return {'id': f"invoice_{r['invoiceId']}", 'text': text, 'metadata': {'table': 'invoice', 'record_id': str(r['invoiceId'])}}


def export_single_payment(payment_id: int):
    """Export one payment record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT p.paymentId, p.amount, p.paymentDate, p.method,
                  c.customerId, c.firstName, c.lastName
           FROM Payment p JOIN Customer c ON p.customerId = c.customerId
           WHERE p.paymentId = %s""",
        (payment_id,), one=True
    )
    if not r:
        return None
    allocs = query_db(
        "SELECT pa.invoiceId, pa.allocatedAmount FROM PaymentAllocation pa WHERE pa.paymentId = %s",
        (r['paymentId'],)
    )
    alloc_text = ', '.join(
        f"Invoice #{a['invoiceId']} (${float(a['allocatedAmount']):.2f})" for a in allocs
    ) if allocs else 'None'
    text = (
        f"Payment ID: {r['paymentId']}\n"
        f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
        f"Amount: ${float(r['amount']):.2f}\n"
        f"Date: {r['paymentDate']}\n"
        f"Method: {r['method']}\n"
        f"Allocated To Invoice(s): {alloc_text}"
    )
    return {'id': f"payment_{r['paymentId']}", 'text': text, 'metadata': {'table': 'payment', 'record_id': str(r['paymentId'])}}


def export_single_ticket(ticket_id: int):
    """Export one ticket record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT t.ticketId, t.priority, t.status, t.createdAt, t.handledBy,
                  c.customerId, c.firstName, c.lastName, u.userName AS employeeName
           FROM Ticket t
           JOIN Customer c ON t.customerId = c.customerId
           LEFT JOIN User u ON t.handledBy = u.userId
           WHERE t.ticketId = %s""",
        (ticket_id,), one=True
    )
    if not r:
        return None
    handler = f"{r['employeeName']} (Employee ID: {r['handledBy']})" if r['handledBy'] else 'Unassigned'
    text = (
        f"Ticket ID: {r['ticketId']}\n"
        f"Customer: {r['firstName']} {r['lastName']} (ID: {r['customerId']})\n"
        f"Handled By: {handler}\n"
        f"Priority: {r['priority']}\n"
        f"Status: {r['status']}\n"
        f"Created: {r['createdAt']}"
    )
    return {'id': f"ticket_{r['ticketId']}", 'text': text, 'metadata': {'table': 'ticket', 'record_id': str(r['ticketId'])}}


def export_single_device(device_id: int):
    """Export one device record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT d.deviceId, d.cardNumber, d.serialNumber, d.status, it.itemName,
                  da.customerId AS assignedCustomerId, da.assignedDate,
                  c.firstName, c.lastName
           FROM Device d
           JOIN Item it ON d.itemId = it.itemId
           LEFT JOIN DeviceAssignment da ON d.deviceId = da.deviceId AND da.returnedDate IS NULL
           LEFT JOIN Customer c ON da.customerId = c.customerId
           WHERE d.deviceId = %s""",
        (device_id,), one=True
    )
    if not r:
        return None
    assignment = (
        f"{r['firstName']} {r['lastName']} (ID: {r['assignedCustomerId']}) since {r['assignedDate']}"
        if r['assignedCustomerId'] else 'Not assigned'
    )
    text = (
        f"Device ID: {r['deviceId']}\n"
        f"Item: {r['itemName']}\n"
        f"Card Number: {r['cardNumber']}\n"
        f"Serial Number: {r['serialNumber']}\n"
        f"Status: {r['status']}\n"
        f"Currently Assigned To: {assignment}"
    )
    return {'id': f"device_{r['deviceId']}", 'text': text, 'metadata': {'table': 'device', 'record_id': str(r['deviceId'])}}


def export_single_item(item_id: int):
    """Export one inventory item record as a RAG document chunk. Returns None if not found."""
    r = query_db(
        """SELECT i.itemId, i.itemName, i.category,
                  COALESCE(SUM(CASE WHEN it2.transactionType='inbound' THEN tl.quantity ELSE 0 END), 0) AS totalIn,
                  COALESCE(SUM(CASE WHEN it2.transactionType='outbound' THEN tl.quantity ELSE 0 END), 0) AS totalOut
           FROM Item i
           LEFT JOIN TransactionLine tl ON i.itemId = tl.itemId
           LEFT JOIN InventoryTransaction it2 ON tl.transactionID = it2.transactionID
           WHERE i.itemId = %s
           GROUP BY i.itemId, i.itemName, i.category""",
        (item_id,), one=True
    )
    if not r:
        return None
    total_in = int(r['totalIn'])
    total_out = int(r['totalOut'])
    text = (
        f"Item ID: {r['itemId']}\n"
        f"Name: {r['itemName']}\n"
        f"Category: {r['category']}\n"
        f"Total Inbound: {total_in}\n"
        f"Total Outbound: {total_out}\n"
        f"Current Stock Level: {total_in - total_out}"
    )
    return {'id': f"inventory_{r['itemId']}", 'text': text, 'metadata': {'table': 'inventory', 'record_id': str(r['itemId'])}}


def export_all_chunks():
    """Export all ERP entities as text chunks. Returns list of dicts."""
    entity_exporters = [
        ('customers',   export_customers),
        ('packages',    export_packages),
        ('subscriptions', export_subscriptions),
        ('invoices',    export_invoices),
        ('payments',    export_payments),
        ('tickets',     export_tickets),
        ('devices',     export_devices),
        ('inventory',   export_inventory_summary),
        ('permissions', export_permissions),
    ]

    all_chunks = []
    for name, fn in entity_exporters:
        result = fn()
        all_chunks.extend(result)

    total = len(all_chunks)
    entity_count = len(entity_exporters)
    print(f"Exported {total} documents across {entity_count} entity types.")
    return all_chunks


if __name__ == '__main__':
    chunks = export_all_chunks()
    for c in chunks[:3]:
        print(f"\n--- {c['id']} ---")
        print(c['text'])
