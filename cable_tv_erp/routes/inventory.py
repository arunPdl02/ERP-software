from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from db import query_db
from routes.auth import login_required_session
from routes.decorators import permission_required
from rag.sync import sync_device, sync_item
from datetime import date
import logging

inventory_bp = Blueprint('inventory', __name__)


# ---- Items ----

@inventory_bp.route('/inventory/items')
@login_required_session
def items():
    try:
        items_list = query_db(
            """SELECT i.itemId, i.itemName, i.category,
                      COALESCE(SUM(CASE WHEN it.transactionType='inbound' THEN tl.quantity ELSE 0 END), 0)
                        - COALESCE(SUM(CASE WHEN it.transactionType='outbound' THEN tl.quantity ELSE 0 END), 0)
                        AS stockLevel
               FROM Item i
               LEFT JOIN TransactionLine tl ON i.itemId = tl.itemId
               LEFT JOIN InventoryTransaction it ON tl.transactionID = it.transactionID
               GROUP BY i.itemId, i.itemName, i.category
               ORDER BY i.category, i.itemName"""
        )
        return render_template('inventory/items.html', items=items_list)
    except Exception as e:
        logging.error(f"Items list error: {e}")
        flash('Something went wrong loading items.', 'error')
        return render_template('inventory/items.html', items=[])


@inventory_bp.route('/inventory/items/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_INVENTORY')
def new_item():
    if request.method == 'POST':
        name = request.form.get('itemName', '').strip()
        category = request.form.get('category', '').strip()

        errors = []
        if not name: errors.append('Item name is required.')
        if not category: errors.append('Category is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('inventory/new_item.html', form=request.form)

        try:
            existing = query_db("SELECT itemId FROM Item WHERE itemName = %s", (name,), one=True)
            if existing:
                flash('An item with that name already exists.', 'error')
                return render_template('inventory/new_item.html', form=request.form)

            new_id = query_db(
                "INSERT INTO Item (itemName, category) VALUES (%s, %s)",
                (name, category), commit=True
            )
            sync_item(new_id)
            flash(f'Item "{name}" created successfully.', 'success')
            return redirect(url_for('inventory.items'))
        except Exception as e:
            logging.error(f"Create item error: {e}")
            flash('Something went wrong creating the item.', 'error')

    return render_template('inventory/new_item.html', form={})


# ---- Devices ----

@inventory_bp.route('/inventory/devices')
@login_required_session
def devices():
    try:
        devices_list = query_db(
            """SELECT d.deviceId, d.cardNumber, d.serialNumber, d.status,
                      it.itemName,
                      c.firstName, c.lastName, c.customerId,
                      da.assignedDate
               FROM Device d
               JOIN Item it ON d.itemId = it.itemId
               LEFT JOIN DeviceAssignment da ON d.deviceId = da.deviceId AND da.returnedDate IS NULL
               LEFT JOIN Customer c ON da.customerId = c.customerId
               ORDER BY d.status, it.itemName"""
        )
        items_list = query_db("SELECT itemId, itemName FROM Item ORDER BY itemName")
        customers_list = query_db(
            "SELECT customerId, firstName, lastName FROM Customer WHERE accountStatus='active' ORDER BY lastName"
        )
        return render_template('inventory/devices.html',
                               devices=devices_list,
                               items=items_list,
                               customers=customers_list)
    except Exception as e:
        logging.error(f"Devices list error: {e}")
        flash('Something went wrong loading devices.', 'error')
        return render_template('inventory/devices.html', devices=[], items=[], customers=[])


@inventory_bp.route('/inventory/devices/new', methods=['GET', 'POST'])
@login_required_session
@permission_required('MANAGE_INVENTORY')
def new_device():
    items_list = query_db("SELECT itemId, itemName FROM Item ORDER BY itemName")

    if request.method == 'POST':
        item_id = request.form.get('itemId')
        card_number = request.form.get('cardNumber', '').strip()
        serial_number = request.form.get('serialNumber', '').strip()

        errors = []
        if not item_id: errors.append('Item is required.')
        if not card_number: errors.append('Card number is required.')
        if not serial_number: errors.append('Serial number is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('inventory/new_device.html', items=items_list, form=request.form)

        try:
            dup_card = query_db("SELECT deviceId FROM Device WHERE cardNumber=%s", (card_number,), one=True)
            dup_sn = query_db("SELECT deviceId FROM Device WHERE serialNumber=%s", (serial_number,), one=True)
            if dup_card:
                flash('Card number already exists.', 'error')
                return render_template('inventory/new_device.html', items=items_list, form=request.form)
            if dup_sn:
                flash('Serial number already exists.', 'error')
                return render_template('inventory/new_device.html', items=items_list, form=request.form)

            new_id = query_db(
                "INSERT INTO Device (itemId, cardNumber, serialNumber, status) VALUES (%s, %s, %s, 'available')",
                (item_id, card_number, serial_number), commit=True
            )
            sync_device(new_id)
            flash('Device created successfully.', 'success')
            return redirect(url_for('inventory.devices'))
        except Exception as e:
            logging.error(f"Create device error: {e}")
            flash('Something went wrong creating the device.', 'error')

    return render_template('inventory/new_device.html', items=items_list, form={})


@inventory_bp.route('/inventory/devices/<int:did>/assign', methods=['POST'])
@login_required_session
@permission_required('MANAGE_INVENTORY')
def assign_device(did):
    try:
        device = query_db("SELECT * FROM Device WHERE deviceId = %s", (did,), one=True)
        if not device:
            abort(404)
        if device['status'] != 'available':
            flash('Device is not available for assignment.', 'error')
            return redirect(url_for('inventory.devices'))

        customer_id = request.form.get('customerId')
        if not customer_id:
            flash('Customer is required.', 'error')
            return redirect(url_for('inventory.devices'))

        assigned_date = date.today().isoformat()
        query_db(
            "INSERT INTO DeviceAssignment (customerId, deviceId, assignedDate) VALUES (%s, %s, %s)",
            (customer_id, did, assigned_date), commit=True
        )
        query_db("UPDATE Device SET status='assigned' WHERE deviceId=%s", (did,), commit=True)
        flash('Device assigned successfully.', 'success')
    except Exception as e:
        logging.error(f"Assign device error: {e}")
        flash('Something went wrong assigning the device.', 'error')
    return redirect(url_for('inventory.devices'))


@inventory_bp.route('/inventory/devices/<int:did>/return', methods=['POST'])
@login_required_session
@permission_required('MANAGE_INVENTORY')
def return_device(did):
    try:
        device = query_db("SELECT * FROM Device WHERE deviceId = %s", (did,), one=True)
        if not device:
            abort(404)

        today = date.today().isoformat()
        query_db(
            "UPDATE DeviceAssignment SET returnedDate=%s WHERE deviceId=%s AND returnedDate IS NULL",
            (today, did), commit=True
        )
        query_db("UPDATE Device SET status='available' WHERE deviceId=%s", (did,), commit=True)
        flash('Device returned successfully.', 'success')
    except Exception as e:
        logging.error(f"Return device error: {e}")
        flash('Something went wrong returning the device.', 'error')
    return redirect(url_for('inventory.devices'))


# ---- Transactions ----

@inventory_bp.route('/inventory/transactions')
@login_required_session
def transactions():
    try:
        txn_list = query_db(
            """SELECT it.transactionID, it.transactionType, it.transactionDate,
                      COUNT(tl.lineNumber) AS lineCount
               FROM InventoryTransaction it
               LEFT JOIN TransactionLine tl ON it.transactionID = tl.transactionID
               GROUP BY it.transactionID, it.transactionType, it.transactionDate
               ORDER BY it.transactionDate DESC"""
        )
        return render_template('inventory/transactions.html', transactions=txn_list)
    except Exception as e:
        logging.error(f"Transactions list error: {e}")
        flash('Something went wrong loading transactions.', 'error')
        return render_template('inventory/transactions.html', transactions=[])


@inventory_bp.route('/inventory/transactions/<int:tid>')
@login_required_session
def transaction_detail(tid):
    try:
        txn = query_db(
            "SELECT * FROM InventoryTransaction WHERE transactionID = %s", (tid,), one=True
        )
        if not txn:
            abort(404)

        lines = query_db(
            """SELECT tl.lineNumber, tl.quantity, i.itemName, i.category
               FROM TransactionLine tl
               JOIN Item i ON tl.itemId = i.itemId
               WHERE tl.transactionID = %s ORDER BY tl.lineNumber""",
            (tid,)
        )
        return render_template('inventory/transaction_detail.html', txn=txn, lines=lines)
    except Exception as e:
        logging.error(f"Transaction detail error: {e}")
        flash('Something went wrong.', 'error')
        return redirect(url_for('inventory.transactions'))


@inventory_bp.route('/inventory/transactions/new', methods=['GET', 'POST'])
@login_required_session
def new_transaction():
    items_list = query_db("SELECT itemId, itemName FROM Item ORDER BY itemName")

    if request.method == 'POST':
        txn_type = request.form.get('transactionType', '').strip()
        txn_date = request.form.get('transactionDate', '').strip()
        item_ids = request.form.getlist('itemId[]')
        quantities = request.form.getlist('quantity[]')

        errors = []
        if txn_type not in ('inbound', 'outbound'):
            errors.append('Transaction type must be inbound or outbound.')
        if not txn_date:
            errors.append('Transaction date is required.')
        if not item_ids:
            errors.append('At least one line item is required.')

        valid_lines = []
        for i, (iid, qty) in enumerate(zip(item_ids, quantities)):
            if iid and qty:
                try:
                    q = int(qty)
                    if q <= 0:
                        errors.append(f'Line {i+1}: quantity must be greater than 0.')
                    else:
                        valid_lines.append((iid, q))
                except ValueError:
                    errors.append(f'Line {i+1}: invalid quantity.')

        if not valid_lines:
            errors.append('At least one valid line item is required.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('inventory/new_transaction.html',
                                   items=items_list, form=request.form)

        try:
            txn_id = query_db(
                "INSERT INTO InventoryTransaction (transactionType, transactionDate) VALUES (%s, %s)",
                (txn_type, txn_date), commit=True
            )
            for line_num, (item_id, qty) in enumerate(valid_lines, start=1):
                query_db(
                    "INSERT INTO TransactionLine (transactionID, lineNumber, itemId, quantity) VALUES (%s, %s, %s, %s)",
                    (txn_id, line_num, item_id, qty), commit=True
                )
            flash(f'Transaction #{txn_id} created successfully.', 'success')
            return redirect(url_for('inventory.transaction_detail', tid=txn_id))
        except Exception as e:
            logging.error(f"Create transaction error: {e}")
            flash('Something went wrong creating the transaction.', 'error')

    return render_template('inventory/new_transaction.html', items=items_list, form={})
