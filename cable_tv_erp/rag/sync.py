"""
rag/sync.py
Convenience wrappers for keeping the ChromaDB index in sync with the MySQL database.
Import these in route files after any write operation.
"""
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from rag.exporter import (
    export_single_customer, export_single_subscription,
    export_single_invoice, export_single_payment,
    export_single_ticket, export_single_device, export_single_item
)
from rag.embedder import upsert_document, delete_document


def sync_customer(customer_id: int) -> None:
    chunk = export_single_customer(customer_id)
    if chunk:
        upsert_document(chunk)


def sync_subscription(subscription_id: int) -> None:
    chunk = export_single_subscription(subscription_id)
    if chunk:
        upsert_document(chunk)


def sync_invoice(invoice_id: int) -> None:
    chunk = export_single_invoice(invoice_id)
    if chunk:
        upsert_document(chunk)


def sync_payment(payment_id: int) -> None:
    chunk = export_single_payment(payment_id)
    if chunk:
        upsert_document(chunk)


def sync_ticket(ticket_id: int) -> None:
    chunk = export_single_ticket(ticket_id)
    if chunk:
        upsert_document(chunk)


def sync_device(device_id: int) -> None:
    chunk = export_single_device(device_id)
    if chunk:
        upsert_document(chunk)


def sync_item(item_id: int) -> None:
    chunk = export_single_item(item_id)
    if chunk:
        upsert_document(chunk)


def remove_customer(customer_id: int) -> None:
    delete_document(f"customer_{customer_id}")


def remove_ticket(ticket_id: int) -> None:
    delete_document(f"ticket_{ticket_id}")


def remove_device(device_id: int) -> None:
    delete_document(f"device_{device_id}")


def remove_invoice(invoice_id: int) -> None:
    delete_document(f"invoice_{invoice_id}")
