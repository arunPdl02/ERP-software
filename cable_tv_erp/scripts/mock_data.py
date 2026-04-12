"""
scripts/mock_data.py — Hardcoded ERP data matching the seeded database,
used to test the embedding/retrieval pipeline without a MySQL connection.
"""

MOCK_CHUNKS = [
    # --- Customers ---
    {
        "id": "customer_11",
        "text": (
            "Customer ID: 11\n"
            "Name: Alice Smith\n"
            "Address: 101 Maple St, Vancouver\n"
            "Account Status: active\n"
            "Active Subscriptions: Basic ($29.99/month) since 2024-01-01\n"
            "Open Tickets: 0\n"
            "Overdue Invoices: 0"
        ),
        "metadata": {"table": "customer", "record_id": "11"},
    },
    {
        "id": "customer_12",
        "text": (
            "Customer ID: 12\n"
            "Name: Bob Jones\n"
            "Address: 202 Oak Ave, Burnaby\n"
            "Account Status: active\n"
            "Active Subscriptions: Standard ($49.99/month) since 2024-02-01\n"
            "Open Tickets: 1\n"
            "Overdue Invoices: 0"
        ),
        "metadata": {"table": "customer", "record_id": "12"},
    },
    {
        "id": "customer_13",
        "text": (
            "Customer ID: 13\n"
            "Name: Charlie Brown\n"
            "Address: 303 Pine Rd, Surrey\n"
            "Account Status: active\n"
            "Active Subscriptions: Premium ($79.99/month) since 2024-03-01\n"
            "Open Tickets: 1\n"
            "Overdue Invoices: 0"
        ),
        "metadata": {"table": "customer", "record_id": "13"},
    },
    {
        "id": "customer_14",
        "text": (
            "Customer ID: 14\n"
            "Name: Diana Prince\n"
            "Address: 404 Elm Blvd, Richmond\n"
            "Account Status: suspended\n"
            "Active Subscriptions: None\n"
            "Open Tickets: 0\n"
            "Overdue Invoices: 1"
        ),
        "metadata": {"table": "customer", "record_id": "14"},
    },
    {
        "id": "customer_15",
        "text": (
            "Customer ID: 15\n"
            "Name: Evan Wright\n"
            "Address: 505 Cedar Ln, Coquitlam\n"
            "Account Status: active\n"
            "Active Subscriptions: Ultimate ($99.99/month) since 2024-06-01\n"
            "Open Tickets: 1\n"
            "Overdue Invoices: 0"
        ),
        "metadata": {"table": "customer", "record_id": "15"},
    },
    # --- Packages ---
    {
        "id": "package_1",
        "text": (
            "Package ID: 1\nName: Basic\nMonthly Price: $29.99\nActive Subscribers: 1"
        ),
        "metadata": {"table": "package", "record_id": "1"},
    },
    {
        "id": "package_2",
        "text": (
            "Package ID: 2\nName: Standard\nMonthly Price: $49.99\nActive Subscribers: 1"
        ),
        "metadata": {"table": "package", "record_id": "2"},
    },
    {
        "id": "package_3",
        "text": (
            "Package ID: 3\nName: Premium\nMonthly Price: $79.99\nActive Subscribers: 1"
        ),
        "metadata": {"table": "package", "record_id": "3"},
    },
    {
        "id": "package_4",
        "text": (
            "Package ID: 4\nName: Sports\nMonthly Price: $59.99\nActive Subscribers: 0"
        ),
        "metadata": {"table": "package", "record_id": "4"},
    },
    {
        "id": "package_5",
        "text": (
            "Package ID: 5\nName: Ultimate\nMonthly Price: $99.99\nActive Subscribers: 1"
        ),
        "metadata": {"table": "package", "record_id": "5"},
    },
    # --- Subscriptions ---
    {
        "id": "subscription_1",
        "text": (
            "Subscription ID: 1\n"
            "Customer: Alice Smith (ID: 11)\n"
            "Package: Basic ($29.99/month)\n"
            "Start Date: 2024-01-01\nEnd Date: N/A\nStatus: active"
        ),
        "metadata": {"table": "subscription", "record_id": "1"},
    },
    {
        "id": "subscription_2",
        "text": (
            "Subscription ID: 2\n"
            "Customer: Bob Jones (ID: 12)\n"
            "Package: Standard ($49.99/month)\n"
            "Start Date: 2024-02-01\nEnd Date: N/A\nStatus: active"
        ),
        "metadata": {"table": "subscription", "record_id": "2"},
    },
    {
        "id": "subscription_3",
        "text": (
            "Subscription ID: 3\n"
            "Customer: Charlie Brown (ID: 13)\n"
            "Package: Premium ($79.99/month)\n"
            "Start Date: 2024-03-01\nEnd Date: N/A\nStatus: active"
        ),
        "metadata": {"table": "subscription", "record_id": "3"},
    },
    {
        "id": "subscription_4",
        "text": (
            "Subscription ID: 4\n"
            "Customer: Diana Prince (ID: 14)\n"
            "Package: Sports ($59.99/month)\n"
            "Start Date: 2024-01-15\nEnd Date: 2025-01-15\nStatus: expired"
        ),
        "metadata": {"table": "subscription", "record_id": "4"},
    },
    {
        "id": "subscription_5",
        "text": (
            "Subscription ID: 5\n"
            "Customer: Evan Wright (ID: 15)\n"
            "Package: Ultimate ($99.99/month)\n"
            "Start Date: 2024-06-01\nEnd Date: N/A\nStatus: active"
        ),
        "metadata": {"table": "subscription", "record_id": "5"},
    },
    # --- Invoices ---
    {
        "id": "invoice_1",
        "text": (
            "Invoice ID: 1\n"
            "Customer: Alice Smith (ID: 11)\n"
            "Billing Period: JAN-2025\n"
            "Total Amount: $29.99\nAmount Paid: $59.98\nBalance: $-29.99\n"
            "Status: paid\nDue Date: 2025-01-15"
        ),
        "metadata": {"table": "invoice", "record_id": "1"},
    },
    {
        "id": "invoice_2",
        "text": (
            "Invoice ID: 2\n"
            "Customer: Bob Jones (ID: 12)\n"
            "Billing Period: JAN-2025\n"
            "Total Amount: $49.99\nAmount Paid: $49.99\nBalance: $0.00\n"
            "Status: paid\nDue Date: 2025-01-15"
        ),
        "metadata": {"table": "invoice", "record_id": "2"},
    },
    {
        "id": "invoice_3",
        "text": (
            "Invoice ID: 3\n"
            "Customer: Charlie Brown (ID: 13)\n"
            "Billing Period: JAN-2025\n"
            "Total Amount: $79.99\nAmount Paid: $40.00\nBalance: $39.99\n"
            "Status: unpaid\nDue Date: 2025-01-15"
        ),
        "metadata": {"table": "invoice", "record_id": "3"},
    },
    {
        "id": "invoice_4",
        "text": (
            "Invoice ID: 4\n"
            "Customer: Diana Prince (ID: 14)\n"
            "Billing Period: JAN-2025\n"
            "Total Amount: $59.99\nAmount Paid: $0.00\nBalance: $59.99\n"
            "Status: overdue\nDue Date: 2025-01-15"
        ),
        "metadata": {"table": "invoice", "record_id": "4"},
    },
    {
        "id": "invoice_5",
        "text": (
            "Invoice ID: 5\n"
            "Customer: Evan Wright (ID: 15)\n"
            "Billing Period: JAN-2025\n"
            "Total Amount: $99.99\nAmount Paid: $99.99\nBalance: $0.00\n"
            "Status: paid\nDue Date: 2025-01-15"
        ),
        "metadata": {"table": "invoice", "record_id": "5"},
    },
    # --- Payments ---
    {
        "id": "payment_1",
        "text": (
            "Payment ID: 1\n"
            "Customer: Alice Smith (ID: 11)\n"
            "Amount: $29.99\nDate: 2025-01-10\nMethod: credit card\n"
            "Allocated To Invoice(s): Invoice #1 ($29.99)"
        ),
        "metadata": {"table": "payment", "record_id": "1"},
    },
    {
        "id": "payment_2",
        "text": (
            "Payment ID: 2\n"
            "Customer: Bob Jones (ID: 12)\n"
            "Amount: $49.99\nDate: 2025-01-12\nMethod: debit card\n"
            "Allocated To Invoice(s): Invoice #2 ($49.99)"
        ),
        "metadata": {"table": "payment", "record_id": "2"},
    },
    {
        "id": "payment_3",
        "text": (
            "Payment ID: 3\n"
            "Customer: Charlie Brown (ID: 13)\n"
            "Amount: $40.00\nDate: 2025-01-14\nMethod: bank transfer\n"
            "Allocated To Invoice(s): Invoice #3 ($40.00)"
        ),
        "metadata": {"table": "payment", "record_id": "3"},
    },
    {
        "id": "payment_4",
        "text": (
            "Payment ID: 4\n"
            "Customer: Evan Wright (ID: 15)\n"
            "Amount: $99.99\nDate: 2025-01-13\nMethod: credit card\n"
            "Allocated To Invoice(s): Invoice #5 ($99.99)"
        ),
        "metadata": {"table": "payment", "record_id": "4"},
    },
    {
        "id": "payment_5",
        "text": (
            "Payment ID: 5\n"
            "Customer: Alice Smith (ID: 11)\n"
            "Amount: $29.99\nDate: 2025-02-10\nMethod: credit card\n"
            "Allocated To Invoice(s): Invoice #1 ($29.99)"
        ),
        "metadata": {"table": "payment", "record_id": "5"},
    },
    # --- Tickets ---
    {
        "id": "ticket_1",
        "text": (
            "Ticket ID: 1\n"
            "Customer: Alice Smith (ID: 11)\n"
            "Handled By: emp_mike (Employee ID: 6)\n"
            "Priority: high\nStatus: resolved\nCreated: 2025-01-10 09:00:00"
        ),
        "metadata": {"table": "ticket", "record_id": "1"},
    },
    {
        "id": "ticket_2",
        "text": (
            "Ticket ID: 2\n"
            "Customer: Bob Jones (ID: 12)\n"
            "Handled By: emp_linda (Employee ID: 7)\n"
            "Priority: medium\nStatus: open\nCreated: 2025-01-15 10:30:00"
        ),
        "metadata": {"table": "ticket", "record_id": "2"},
    },
    {
        "id": "ticket_3",
        "text": (
            "Ticket ID: 3\n"
            "Customer: Charlie Brown (ID: 13)\n"
            "Handled By: emp_carlos (Employee ID: 8)\n"
            "Priority: low\nStatus: open\nCreated: 2025-02-01 11:00:00"
        ),
        "metadata": {"table": "ticket", "record_id": "3"},
    },
    {
        "id": "ticket_4",
        "text": (
            "Ticket ID: 4\n"
            "Customer: Diana Prince (ID: 14)\n"
            "Handled By: emp_nina (Employee ID: 9)\n"
            "Priority: high\nStatus: in-progress\nCreated: 2025-02-10 14:00:00"
        ),
        "metadata": {"table": "ticket", "record_id": "4"},
    },
    {
        "id": "ticket_5",
        "text": (
            "Ticket ID: 5\n"
            "Customer: Evan Wright (ID: 15)\n"
            "Handled By: Unassigned\n"
            "Priority: low\nStatus: open\nCreated: 2025-03-01 08:00:00"
        ),
        "metadata": {"table": "ticket", "record_id": "5"},
    },
    # --- Devices ---
    {
        "id": "device_1",
        "text": (
            "Device ID: 1\nItem: HD Set-Top Box\n"
            "Card Number: CARD-1001\nSerial Number: SN-A001\n"
            "Status: assigned\n"
            "Currently Assigned To: Alice Smith (ID: 11) since 2024-01-01"
        ),
        "metadata": {"table": "device", "record_id": "1"},
    },
    {
        "id": "device_2",
        "text": (
            "Device ID: 2\nItem: HD Set-Top Box\n"
            "Card Number: CARD-1002\nSerial Number: SN-A002\n"
            "Status: assigned\n"
            "Currently Assigned To: Bob Jones (ID: 12) since 2024-02-01"
        ),
        "metadata": {"table": "device", "record_id": "2"},
    },
    {
        "id": "device_3",
        "text": (
            "Device ID: 3\nItem: 4K Set-Top Box\n"
            "Card Number: CARD-2001\nSerial Number: SN-B001\n"
            "Status: assigned\n"
            "Currently Assigned To: Charlie Brown (ID: 13) since 2024-03-01"
        ),
        "metadata": {"table": "device", "record_id": "3"},
    },
    {
        "id": "device_4",
        "text": (
            "Device ID: 4\nItem: 4K Set-Top Box\n"
            "Card Number: CARD-2002\nSerial Number: SN-B002\n"
            "Status: available\n"
            "Currently Assigned To: Not assigned"
        ),
        "metadata": {"table": "device", "record_id": "4"},
    },
    {
        "id": "device_5",
        "text": (
            "Device ID: 5\nItem: HD Set-Top Box\n"
            "Card Number: CARD-1003\nSerial Number: SN-A003\n"
            "Status: assigned\n"
            "Currently Assigned To: Evan Wright (ID: 15) since 2024-06-01"
        ),
        "metadata": {"table": "device", "record_id": "5"},
    },
    # --- Inventory ---
    {
        "id": "inventory_1",
        "text": (
            "Item ID: 1\nName: HD Set-Top Box\nCategory: Device\n"
            "Total Inbound: 10\nTotal Outbound: 3\nCurrent Stock Level: 7"
        ),
        "metadata": {"table": "inventory", "record_id": "1"},
    },
    {
        "id": "inventory_2",
        "text": (
            "Item ID: 2\nName: 4K Set-Top Box\nCategory: Device\n"
            "Total Inbound: 5\nTotal Outbound: 0\nCurrent Stock Level: 5"
        ),
        "metadata": {"table": "inventory", "record_id": "2"},
    },
    {
        "id": "inventory_3",
        "text": (
            "Item ID: 3\nName: Remote Control\nCategory: Accessory\n"
            "Total Inbound: 20\nTotal Outbound: 0\nCurrent Stock Level: 20"
        ),
        "metadata": {"table": "inventory", "record_id": "3"},
    },
    {
        "id": "inventory_4",
        "text": (
            "Item ID: 4\nName: HDMI Cable\nCategory: Accessory\n"
            "Total Inbound: 15\nTotal Outbound: 0\nCurrent Stock Level: 15"
        ),
        "metadata": {"table": "inventory", "record_id": "4"},
    },
    {
        "id": "inventory_5",
        "text": (
            "Item ID: 5\nName: Signal Booster\nCategory: Equipment\n"
            "Total Inbound: 0\nTotal Outbound: 0\nCurrent Stock Level: 0"
        ),
        "metadata": {"table": "inventory", "record_id": "5"},
    },
    # --- Permissions ---
    {
        "id": "permission_1",
        "text": (
            "User ID: 1\nUsername: admin_sara\nRole: admin\n"
            "Permissions: MANAGE_BILLING, MANAGE_CUSTOMERS"
        ),
        "metadata": {"table": "permission", "record_id": "1"},
    },
    {
        "id": "permission_2",
        "text": (
            "User ID: 2\nUsername: admin_james\nRole: admin\n"
            "Permissions: MANAGE_INVENTORY, VIEW_REPORTS"
        ),
        "metadata": {"table": "permission", "record_id": "2"},
    },
    {
        "id": "permission_3",
        "text": (
            "User ID: 3\nUsername: admin_peter\nRole: admin\n"
            "Permissions: HANDLE_TICKETS, MANAGE_CUSTOMERS"
        ),
        "metadata": {"table": "permission", "record_id": "3"},
    },
    {
        "id": "permission_4",
        "text": (
            "User ID: 4\nUsername: admin_lisa\nRole: admin\n"
            "Permissions: MANAGE_BILLING"
        ),
        "metadata": {"table": "permission", "record_id": "4"},
    },
    {
        "id": "permission_5",
        "text": (
            "User ID: 5\nUsername: admin_kevin\nRole: admin\n"
            "Permissions: VIEW_REPORTS"
        ),
        "metadata": {"table": "permission", "record_id": "5"},
    },
    {
        "id": "permission_6",
        "text": (
            "User ID: 6\nUsername: emp_mike\nRole: employee\n"
            "Permissions: HANDLE_TICKETS"
        ),
        "metadata": {"table": "permission", "record_id": "6"},
    },
    {
        "id": "permission_7",
        "text": (
            "User ID: 7\nUsername: emp_linda\nRole: employee\n"
            "Permissions: MANAGE_INVENTORY"
        ),
        "metadata": {"table": "permission", "record_id": "7"},
    },
    {
        "id": "permission_8",
        "text": (
            "User ID: 8\nUsername: emp_carlos\nRole: employee\n"
            "Permissions: HANDLE_TICKETS"
        ),
        "metadata": {"table": "permission", "record_id": "8"},
    },
    {
        "id": "permission_9",
        "text": (
            "User ID: 9\nUsername: emp_nina\nRole: employee\n"
            "Permissions: VIEW_REPORTS"
        ),
        "metadata": {"table": "permission", "record_id": "9"},
    },
    {
        "id": "permission_10",
        "text": (
            "User ID: 10\nUsername: emp_david\nRole: employee\n"
            "Permissions: MANAGE_CUSTOMERS"
        ),
        "metadata": {"table": "permission", "record_id": "10"},
    },
]
