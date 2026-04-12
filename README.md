# Cable TV ERP

A full-stack ERP system for managing cable TV operations, built with Flask and MySQL. Includes an AI-powered chatbot that answers questions about your business data using Retrieval-Augmented Generation (RAG).

## Features

- **Customer Management** -- add, edit, and view customer accounts
- **Subscriptions & Packages** -- create service packages and manage customer subscriptions
- **Billing** -- generate invoices, record payments, and allocate payments to invoices
- **Inventory & Devices** -- track inventory items, individual devices (with card/serial numbers), and device assignments to customers
- **Support Tickets** -- create and manage customer support tickets with priority levels
- **Employee Management** -- manage employee accounts with role-based access control
- **Permissions** -- granular permission system (MANAGE_CUSTOMERS, MANAGE_BILLING, MANAGE_INVENTORY, HANDLE_TICKETS, VIEW_REPORTS) with admin override
- **Reports** -- business reporting dashboard
- **AI Chatbot** -- ask natural-language questions about ERP data, powered by ChromaDB + OpenAI GPT-4o-mini
- **Admin Integrity** -- database integrity checks for administrators

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Flask, Flask-Bcrypt, Flask-Login |
| Database | MySQL |
| Vector DB | ChromaDB |
| Embeddings | Sentence-Transformers |
| LLM | OpenAI GPT-4o-mini |
| Frontend | Jinja2 templates, CSS, JavaScript |

## Prerequisites

- Python 3.10+
- MySQL 8.0+
- An OpenAI API key (for the chatbot feature)

## Getting Started

### 1. Clone the repository

```bash
git clone <repo-url>
cd ERP-Software
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate
pip install -r cable_tv_erp/requirements.txt
```

### 3. Configure environment variables

Copy the example file and fill in your values:

```bash
cp cable_tv_erp/.env.example cable_tv_erp/.env
```

Edit `cable_tv_erp/.env`:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_NAME=cable_tv_erp
SECRET_KEY=your-secret-key-here
OPENAI_API_KEY=your-openai-api-key-here
```

### 4. Initialize the database

This creates the `cable_tv_erp` database, sets up all tables, and inserts seed data with hashed passwords:

```bash
python init_db.py
```

### 5. Build the RAG index (for the chatbot)

Export ERP data into the ChromaDB vector index:

```bash
cd cable_tv_erp
python scripts/build_index.py
```

To build the index without a running MySQL instance (uses mock data):

```bash
python scripts/build_index.py --mock
```

### 6. Run the application

```bash
cd cable_tv_erp
python app.py
```

The app will be available at **http://localhost:5000**.

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin_sara` | `admin_sara_pass` |
| Employee | `emp_mike` | `emp_mike_pass` |

All seed users follow the pattern `{username}_pass`.

## Project Structure

```
ERP-Software/
├── init_db.py                  # Database schema + seed data
├── cable_tv_erp/
│   ├── app.py                  # Flask application entry point
│   ├── config.py               # Environment variable loading
│   ├── db.py                   # MySQL connection helper
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variable template
│   ├── routes/                 # Flask blueprints
│   │   ├── auth.py             # Login/logout
│   │   ├── dashboard.py        # Home dashboard
│   │   ├── customers.py        # Customer CRUD
│   │   ├── employees.py        # Employee management
│   │   ├── packages.py         # Service packages
│   │   ├── subscriptions.py    # Subscription management
│   │   ├── billing.py          # Invoices & payments
│   │   ├── inventory.py        # Items & devices
│   │   ├── tickets.py          # Support tickets
│   │   ├── permissions.py      # Permission management
│   │   ├── reports.py          # Business reports
│   │   ├── chatbot.py          # AI chatbot endpoint
│   │   ├── admin_integrity.py  # DB integrity checks
│   │   └── decorators.py       # Auth & permission decorators
│   ├── rag/                    # RAG pipeline
│   │   ├── embedder.py         # ChromaDB index builder
│   │   ├── exporter.py         # MySQL → document exporter
│   │   ├── retriever.py        # Vector search retrieval
│   │   ├── generator.py        # OpenAI answer generation
│   │   └── sync.py             # Vector DB sync utilities
│   ├── eval/                   # Chatbot evaluation framework
│   │   ├── eval_runner.py      # Test runner
│   │   └── ground_truth.py     # Ground truth Q&A pairs
│   ├── scripts/
│   │   ├── build_index.py      # Build the vector index
│   │   ├── mock_data.py        # Mock data for index building
│   │   └── run_eval.py         # Run chatbot evaluations
│   ├── templates/              # Jinja2 HTML templates
│   └── static/                 # CSS and JavaScript
└── scripts/
    ├── migrate_customer_decoupling.py
    └── run_assertions.py
```

## Database Schema

The system uses 14 tables organized around these entities:

- **User / Admin / Employee** -- authentication and role hierarchy
- **Customer** -- customer accounts
- **Package / Subscription** -- service offerings and active subscriptions
- **Invoice / InvoiceLineItem** -- billing with line-item detail
- **Payment / PaymentAllocation** -- payments with allocation to specific invoices
- **Item / Device / DeviceAssignment** -- inventory items, individual tracked devices, and customer assignments
- **Ticket** -- support tickets linked to customers and employees
- **Permission / RoleHasPermission** -- granular permission assignments

## Running Evaluations

The eval framework tests the chatbot's accuracy against ground truth Q&A pairs:

```bash
cd cable_tv_erp

# Dry run (no OpenAI calls, tests retrieval only)
python scripts/run_eval.py --dry-run

# Full evaluation (requires OPENAI_API_KEY)
python scripts/run_eval.py
```

Results are saved to `cable_tv_erp/eval/results/`.
