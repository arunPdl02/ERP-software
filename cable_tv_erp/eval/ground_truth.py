"""
eval/ground_truth.py — Ground truth Q&A pairs for the Cable TV ERP RAG eval suite.

These are based on the EXACT seeded data in the database. Do not change them.
"""

GROUND_TRUTH = [
    # --- Customer questions ---
    {
        "id": "q01",
        "question": "How many active customers are there?",
        "expected_answer": "4",
        "expected_keywords": ["4", "four"],
        "category": "customers"
    },
    {
        "id": "q02",
        "question": "Which customer has a suspended account?",
        "expected_answer": "Diana Prince",
        "expected_keywords": ["diana", "prince", "14"],
        "category": "customers"
    },
    {
        "id": "q03",
        "question": "What is Alice Smith's address?",
        "expected_answer": "101 Maple St, Vancouver",
        "expected_keywords": ["maple", "vancouver"],
        "category": "customers"
    },

    # --- Subscription questions ---
    {
        "id": "q04",
        "question": "How many active subscriptions are there?",
        "expected_answer": "4",
        "expected_keywords": ["4", "four"],
        "category": "subscriptions"
    },
    {
        "id": "q05",
        "question": "Which customer is subscribed to the Ultimate package?",
        "expected_answer": "Evan Wright",
        "expected_keywords": ["evan", "wright", "15"],
        "category": "subscriptions"
    },
    {
        "id": "q06",
        "question": "What is the most expensive package and its price?",
        "expected_answer": "Ultimate, $99.99",
        "expected_keywords": ["ultimate", "99.99"],
        "category": "packages"
    },

    # --- Billing questions ---
    {
        "id": "q07",
        "question": "Which customer has an overdue invoice?",
        "expected_answer": "Diana Prince",
        "expected_keywords": ["diana", "prince"],
        "category": "billing"
    },
    {
        "id": "q08",
        "question": "What is the total amount of invoice number 3?",
        "expected_answer": "$79.99",
        "expected_keywords": ["79.99"],
        "category": "billing"
    },
    {
        "id": "q09",
        "question": "How did Bob Jones pay his January 2025 invoice?",
        "expected_answer": "debit card",
        "expected_keywords": ["debit"],
        "category": "billing"
    },
    {
        "id": "q10",
        "question": "What is the balance remaining on Charlie Brown's January invoice?",
        "expected_answer": "$39.99",
        "expected_keywords": ["39.99"],
        "category": "billing"
    },

    # --- Inventory questions ---
    {
        "id": "q11",
        "question": "What is the current stock level of HD Set-Top Boxes?",
        "expected_answer": "7",
        "expected_keywords": ["7", "seven"],
        "category": "inventory"
    },
    {
        "id": "q12",
        "question": "Which device is assigned to Alice Smith?",
        "expected_answer": "HD Set-Top Box, CARD-1001",
        "expected_keywords": ["card-1001", "sn-a001", "hd set-top"],
        "category": "inventory"
    },

    # --- Ticket questions ---
    {
        "id": "q13",
        "question": "How many open tickets are there?",
        "expected_answer": "3",
        "expected_keywords": ["3", "three"],
        "category": "tickets"
    },
    {
        "id": "q14",
        "question": "Which employee is handling Evan Wright's ticket?",
        "expected_answer": "unassigned",
        "expected_keywords": ["unassigned", "no employee", "null", "not assigned"],
        "category": "tickets"
    },
    {
        "id": "q15",
        "question": "What is the priority of ticket number 4?",
        "expected_answer": "high",
        "expected_keywords": ["high"],
        "category": "tickets"
    },

    # --- Permissions questions ---
    {
        "id": "q16",
        "question": "What permissions does admin_sara have?",
        "expected_answer": "MANAGE_CUSTOMERS, MANAGE_BILLING",
        "expected_keywords": ["manage_customers", "manage_billing"],
        "category": "permissions"
    },
    {
        "id": "q17",
        "question": "Which employee handles inventory management?",
        "expected_answer": "emp_linda",
        "expected_keywords": ["linda", "emp_linda", "7"],
        "category": "permissions"
    },

    # --- Cross-entity questions (harder) ---
    {
        "id": "q18",
        "question": "Which customers have paid all their invoices?",
        "expected_answer": "Alice Smith, Bob Jones, Evan Wright",
        "expected_keywords": ["alice", "bob", "evan"],
        "category": "cross_entity"
    },
    {
        "id": "q19",
        "question": "What package is Charlie Brown subscribed to and how much does it cost?",
        "expected_answer": "Premium, $79.99",
        "expected_keywords": ["premium", "79.99", "charlie"],
        "category": "cross_entity"
    },
    {
        "id": "q20",
        "question": "How many devices are currently available for assignment?",
        "expected_answer": "1",
        "expected_keywords": ["1", "one", "card-2002"],
        "category": "cross_entity"
    },
]
