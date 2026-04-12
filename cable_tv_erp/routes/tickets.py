from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, session
from db import query_db
from routes.auth import login_required_session
from routes.decorators import permission_required
from rag.sync import sync_ticket
import logging

tickets_bp = Blueprint('tickets', __name__)


@tickets_bp.route('/tickets')
@login_required_session
def list_tickets():
    try:
        status_filter = request.args.get('status', '')
        priority_filter = request.args.get('priority', '')

        sql = """
            SELECT t.ticketId, t.priority, t.status, t.createdAt,
                   c.firstName, c.lastName, c.customerId,
                   u.userName AS employeeName, t.handledBy
            FROM Ticket t
            JOIN Customer c ON t.customerId = c.customerId
            LEFT JOIN User u ON t.handledBy = u.userId
            WHERE 1=1
        """
        args = []
        if status_filter:
            sql += " AND t.status = %s"
            args.append(status_filter)
        if priority_filter:
            sql += " AND t.priority = %s"
            args.append(priority_filter)
        sql += " ORDER BY t.createdAt DESC"

        tickets_list = query_db(sql, tuple(args))
        return render_template('tickets/list.html',
                               tickets=tickets_list,
                               status_filter=status_filter,
                               priority_filter=priority_filter)
    except Exception as e:
        logging.error(f"Ticket list error: {e}")
        flash('Something went wrong loading tickets.', 'error')
        return render_template('tickets/list.html', tickets=[], status_filter='', priority_filter='')


@tickets_bp.route('/tickets/<int:tid>')
@login_required_session
def ticket_detail(tid):
    try:
        ticket = query_db(
            """SELECT t.*, c.firstName, c.lastName,
                      u.userName AS employeeName
               FROM Ticket t
               JOIN Customer c ON t.customerId = c.customerId
               LEFT JOIN User u ON t.handledBy = u.userId
               WHERE t.ticketId = %s""",
            (tid,), one=True
        )
        if not ticket:
            abort(404)

        employees = query_db(
            "SELECT u.userId, u.userName FROM User u JOIN Employee e ON u.userId = e.userId ORDER BY u.userName"
        )

        return render_template('tickets/detail.html', ticket=ticket, employees=employees)
    except Exception as e:
        logging.error(f"Ticket detail error: {e}")
        flash('Something went wrong.', 'error')
        return redirect(url_for('tickets.list_tickets'))


@tickets_bp.route('/tickets/new', methods=['GET', 'POST'])
@login_required_session
def new_ticket():
    customers = query_db(
        "SELECT customerId, firstName, lastName FROM Customer ORDER BY lastName"
    )

    if request.method == 'POST':
        customer_id = request.form.get('customerId')
        priority = request.form.get('priority', '').strip()

        errors = []
        if not customer_id: errors.append('Customer is required.')
        if priority not in ('low', 'medium', 'high'):
            errors.append('Priority must be low, medium, or high.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('tickets/form.html', customers=customers, form=request.form)

        try:
            new_id = query_db(
                "INSERT INTO Ticket (customerId, priority, status) VALUES (%s, %s, 'open')",
                (customer_id, priority), commit=True
            )
            sync_ticket(new_id)
            flash('Ticket created successfully.', 'success')
            return redirect(url_for('tickets.list_tickets'))
        except Exception as e:
            logging.error(f"Create ticket error: {e}")
            flash('Something went wrong creating the ticket.', 'error')

    return render_template('tickets/form.html', customers=customers, form={})


@tickets_bp.route('/tickets/<int:tid>/assign', methods=['POST'])
@login_required_session
@permission_required('HANDLE_TICKETS')
def assign_ticket(tid):
    try:
        ticket = query_db("SELECT * FROM Ticket WHERE ticketId = %s", (tid,), one=True)
        if not ticket:
            abort(404)
        employee_id = request.form.get('employeeId')
        if not employee_id:
            flash('Employee is required.', 'error')
            return redirect(url_for('tickets.ticket_detail', tid=tid))

        query_db(
            "UPDATE Ticket SET handledBy=%s WHERE ticketId=%s",
            (employee_id, tid), commit=True
        )
        sync_ticket(tid)
        flash('Ticket assigned successfully.', 'success')
    except Exception as e:
        logging.error(f"Assign ticket error: {e}")
        flash('Something went wrong assigning the ticket.', 'error')
    return redirect(url_for('tickets.ticket_detail', tid=tid))


@tickets_bp.route('/tickets/<int:tid>/update-status', methods=['POST'])
@login_required_session
@permission_required('HANDLE_TICKETS')
def update_status(tid):
    try:
        ticket = query_db("SELECT * FROM Ticket WHERE ticketId = %s", (tid,), one=True)
        if not ticket:
            abort(404)

        new_status = request.form.get('status', '').strip()
        if new_status not in ('open', 'in-progress', 'resolved', 'closed'):
            flash('Invalid status.', 'error')
            return redirect(url_for('tickets.ticket_detail', tid=tid))

        query_db(
            "UPDATE Ticket SET status=%s WHERE ticketId=%s",
            (new_status, tid), commit=True
        )
        sync_ticket(tid)
        flash('Ticket status updated.', 'success')
    except Exception as e:
        logging.error(f"Update ticket status error: {e}")
        flash('Something went wrong updating the ticket.', 'error')
    return redirect(url_for('tickets.ticket_detail', tid=tid))
