"""
Migration: Decouple Customer from User table.
Removes the User-based login linkage for customers.
Run once: python scripts/migrate_customer_decoupling.py
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'cable_tv_erp'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'cable_tv_erp', '.env'))

from db import get_db_connection


def run():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Step 1/4: Adding standalone customerId column...")
    cursor.execute("""
        ALTER TABLE Customer
        ADD COLUMN newCustomerId INT NOT NULL AUTO_INCREMENT UNIQUE FIRST
    """)

    print("Step 2/4: Dropping foreign key constraint to User...")
    cursor.execute("""
        SELECT CONSTRAINT_NAME
        FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_NAME = 'Customer'
        AND COLUMN_NAME = 'customerId'
        AND REFERENCED_TABLE_NAME = 'User'
        AND TABLE_SCHEMA = DATABASE()
    """)
    row = cursor.fetchone()
    if row:
        fk_name = row[0]
        cursor.execute(f"ALTER TABLE Customer DROP FOREIGN KEY `{fk_name}`")
        print(f"  Dropped FK: {fk_name}")
    else:
        print("  No FK constraint found (already removed or not present).")

    print("Step 3/4: Replacing old customerId with new standalone key...")
    cursor.execute("ALTER TABLE Customer DROP PRIMARY KEY")
    cursor.execute("ALTER TABLE Customer DROP COLUMN customerId")
    cursor.execute("ALTER TABLE Customer CHANGE newCustomerId customerId INT NOT NULL AUTO_INCREMENT PRIMARY KEY")

    print("Step 4/4: Removing customer rows from User table...")
    cursor.execute("""
        DELETE FROM User
        WHERE userId NOT IN (SELECT userId FROM Admin)
        AND userId NOT IN (SELECT userId FROM Employee)
    """)
    deleted = cursor.rowcount
    print(f"  Removed {deleted} customer user account(s).")

    conn.commit()
    cursor.close()
    conn.close()
    print("Migration complete. Customers are now decoupled from User accounts.")
    print("Existing customer data (subscriptions, invoices, tickets, devices) is unaffected.")


if __name__ == '__main__':
    run()
