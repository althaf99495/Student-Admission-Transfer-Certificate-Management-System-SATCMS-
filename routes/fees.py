from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.db_pool import db_manager, get_student_by_id, get_courses, get_academic_years
from utils.auth_helpers import admin_required
from datetime import datetime
import sqlite3

fees_bp = Blueprint('fees', __name__)

@fees_bp.route('/student/<int:student_id>')
@admin_required
def view_student_fees(student_id):
    """Displays the fee history for a single student."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))

    fee_records = db_manager.execute_query(
        "SELECT * FROM student_fee_payments WHERE student_id = ? ORDER BY payment_date DESC",
        (student_id,),
        fetch_all=True
    )
    total_paid = sum(r['amount_paid'] for r in fee_records) if fee_records else 0

    return render_template('fees/view_student_fees.html', student=student, fee_records=fee_records, total_paid=total_paid)

@fees_bp.route('/record-payment/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def record_payment(student_id):
    """Form to record a new fee payment for a student. Automatically assigns fee structure if missing."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))

    # --- ENHANCED LOGIC: AUTO-ASSIGN FEE STRUCTURE ---
    if not student['fee_structure_id']:
        # Attempt to find and assign the fee structure automatically.
        fee_structure = db_manager.execute_query(
            "SELECT id FROM fee_structure WHERE course_id = ? AND academic_year_id = ?",
            (student['course_id'], student['academic_year_id']),
            fetch_one=True
        )
        
        if fee_structure:
            # A matching structure exists, so link it to the student.
            db_manager.execute_query(
                "UPDATE students SET fee_structure_id = ? WHERE id = ?",
                (fee_structure['id'], student_id),
                commit=True
            )
            flash(f"Automatically linked student to the fee structure for {student['course_name']} - {student['academic_year']}.", 'success')
            # Re-fetch student data to reflect the change immediately.
            student = get_student_by_id(student_id)
        else:
            # If no structure is found after checking, then it truly is missing.
            flash(f"Could not find a fee structure for Course '{student['course_name']}' and Academic Year '{student['academic_year']}'. Please create one first.", 'danger')

    # After the attempt, check the status again.
    fee_structure_missing = not student['fee_structure_id']

    if request.method == 'POST':
        if fee_structure_missing:
            # This error will now only be triggered if the auto-assignment above failed.
            flash('Cannot record payment because a fee structure for this course and year has not been created.', 'danger')
            return render_template('fees/record_payment.html', 
                                   student=student, 
                                   today_date=datetime.now().strftime('%Y-%m-%d'), 
                                   fee_structure_missing=True,
                                   form_data=request.form)

        amount = request.form.get('amount', type=float)
        payment_date = request.form.get('payment_date')
        transaction_id = request.form.get('transaction_id')
        payment_method = request.form.get('payment_method')
        remarks = request.form.get('remarks')

        if not amount or amount <= 0:
            flash('Invalid amount.', 'danger')
        elif not payment_date:
            flash('Payment date is required.', 'danger')
        elif not payment_method:
            flash('Payment method is required.', 'danger')
        else:
            try:
                transaction_id_to_db = transaction_id.strip() if transaction_id else None
                db_manager.execute_query(
                    """INSERT INTO student_fee_payments 
                       (student_id, fee_structure_id, amount_paid, payment_date, transaction_id, payment_method, remarks)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (student_id, student['fee_structure_id'], amount, payment_date, transaction_id_to_db, payment_method, remarks),
                    commit=True
                )
                flash('Fee payment recorded successfully.', 'success')
                return redirect(url_for('fees.view_student_fees', student_id=student_id))
            except Exception as e:
                flash(f'Failed to record payment: {e}', 'danger')
        
        return render_template('fees/record_payment.html', 
                               student=student, 
                               today_date=datetime.now().strftime('%Y-%m-%d'), 
                               fee_structure_missing=fee_structure_missing,
                               form_data=request.form)

    # For GET request
    if fee_structure_missing:
        # The flash message for missing structure is now handled by the auto-assign logic above.
        # This prevents showing a warning if the auto-assign was successful.
        pass

    today_date = datetime.now().strftime('%Y-%m-%d')
    return render_template('fees/record_payment.html', 
                           student=student, 
                           today_date=today_date, 
                           fee_structure_missing=fee_structure_missing)

@fees_bp.route('/select-student/record-payment', methods=['GET'])
@admin_required
def select_student_to_record_payment():
    """Page to select a student to record a fee payment, with filtering."""
    selected_course_id = request.args.get('course_id', type=int)
    selected_academic_year_id = request.args.get('academic_year_id', type=int)
    student_query = "SELECT id, student_name, surname, admission_no FROM students"
    conditions = []
    params = []
    if selected_course_id:
        conditions.append("course_id = ?")
        params.append(selected_course_id)
    if selected_academic_year_id:
        conditions.append("academic_year_id = ?")
        params.append(selected_academic_year_id)
    if conditions:
        student_query += " WHERE " + " AND ".join(conditions)
    student_query += " ORDER BY student_name, surname"
    students = db_manager.execute_query(student_query, tuple(params), fetch_all=True)
    all_courses = get_courses()
    all_academic_years = get_academic_years()
    return render_template(
        'fees/select_student.html', 
        students=students, 
        action_url_name='fees.record_payment', 
        action_title="Record Payment For",
        courses=all_courses,
        academic_years=all_academic_years,
        selected_course_id=selected_course_id,
        selected_academic_year_id=selected_academic_year_id,
        show_filters=True,
        filter_form_action=url_for('fees.select_student_to_record_payment')
    )

@fees_bp.route('/select-student/view-history', methods=['GET'])
@admin_required
def select_student_to_view_fees():
    """Page to select a student to view their fee history."""
    students = db_manager.execute_query(
        "SELECT id, student_name, surname, admission_no FROM students ORDER BY student_name, surname",
        fetch_all=True
    )
    return render_template(
        'fees/select_student.html', 
        students=students, 
        action_url_name='fees.view_student_fees', 
        action_title="View Fee History For",
        show_filters=False
    )

@fees_bp.route('/manage-payments')
@admin_required
def manage_fee_payments():
    """Displays all fee payments with options to manage them."""
    payments = db_manager.execute_query(
        """SELECT p.*, s.student_name, s.admission_no
           FROM student_fee_payments p
           JOIN students s ON p.student_id = s.id
           ORDER BY p.payment_date DESC, p.id DESC""",
        fetch_all=True
    )
    return render_template('fees/manage_fee_payments.html', payments=payments)

@fees_bp.route('/fee-structures')
@admin_required
def list_fee_structures():
    """Displays a list of all fee structures."""
    fee_structures = db_manager.execute_query(
        """SELECT fs.id, c.course_name, ay.academic_year, fs.total_fee
           FROM fee_structure fs
           JOIN courses c ON fs.course_id = c.id
           JOIN academic_years ay ON fs.academic_year_id = ay.id
           ORDER BY c.course_name, ay.academic_year""",
        fetch_all=True
    )
    return render_template('fees/list_fee_structures.html', fee_structures=fee_structures)

@fees_bp.route('/fee-structures/add', methods=['GET', 'POST'])
@admin_required
def add_fee_structure():
    """Handles adding a new fee structure."""
    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        academic_year_id = request.form.get('academic_year_id', type=int)
        total_fee = request.form.get('total_fee', type=float)

        if not course_id or not academic_year_id or total_fee is None or total_fee < 0:
            flash('All fields are required and total fee must be non-negative.', 'danger')
        else:
            updated_students_count = 0
            try:
                with db_manager.get_db_cursor(commit=False) as cursor:
                    cursor.execute(
                        "INSERT INTO fee_structure (course_id, academic_year_id, total_fee) VALUES (?, ?, ?)",
                        (course_id, academic_year_id, total_fee)
                    )
                    new_structure_id = cursor.lastrowid
                    if new_structure_id:
                        res = cursor.execute(
                            """UPDATE students SET fee_structure_id = ? 
                               WHERE course_id = ? AND academic_year_id = ? AND fee_structure_id IS NULL""",
                            (new_structure_id, course_id, academic_year_id)
                        )
                        updated_students_count = res.rowcount if res else 0
                    cursor.connection.commit()
                flash(f'Fee structure added successfully! {updated_students_count} unassigned student(s) linked.', 'success')
                return redirect(url_for('fees.list_fee_structures'))
            except sqlite3.IntegrityError:
                flash('A fee structure already exists for this course and academic year.', 'danger')
            except Exception as e:
                flash(f'Failed to add fee structure: {e}', 'danger')
    
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('fees/add_edit_fee_structure.html', action="Add", courses=courses, academic_years=academic_years, fee_structure={})

@fees_bp.route('/fee-structures/edit/<int:structure_id>', methods=['GET', 'POST'])
@admin_required
def edit_fee_structure(structure_id):
    original_fee_structure = db_manager.execute_query("SELECT * FROM fee_structure WHERE id = ?", (structure_id,), fetch_one=True)
    if not original_fee_structure:
        flash('Fee structure not found.', 'danger')
        return redirect(url_for('fees.list_fee_structures'))

    if request.method == 'POST':
        course_id = request.form.get('course_id', type=int)
        academic_year_id = request.form.get('academic_year_id', type=int)
        total_fee = request.form.get('total_fee', type=float)
        updated_students_count = 0

        if not course_id or not academic_year_id or total_fee is None or total_fee < 0:
            flash('All fields are required and total fee must be non-negative.', 'danger')
        else:
            try:
                with db_manager.get_db_cursor(commit=False) as cursor:
                    cursor.execute(
                        "UPDATE fee_structure SET course_id = ?, academic_year_id = ?, total_fee = ? WHERE id = ?",
                        (course_id, academic_year_id, total_fee, structure_id)
                    )
                    cursor.execute(
                        "UPDATE students SET fee_structure_id = NULL WHERE fee_structure_id = ?",
                        (structure_id,)
                    )
                    res = cursor.execute(
                        """UPDATE students SET fee_structure_id = ?
                           WHERE course_id = ? AND academic_year_id = ?""",
                        (structure_id, course_id, academic_year_id)
                    )
                    updated_students_count = res.rowcount if res else 0
                    cursor.connection.commit()
                flash(f'Fee structure updated successfully! {updated_students_count} student(s) now linked to this structure.', 'success')
                return redirect(url_for('fees.list_fee_structures'))
            except sqlite3.IntegrityError:
                flash('A fee structure already exists for the selected course and academic year.', 'danger')
            except Exception as e:
                flash(f'Failed to update fee structure: {e}', 'danger')
    
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('fees/add_edit_fee_structure.html', action="Edit", courses=courses, academic_years=academic_years, fee_structure=original_fee_structure)

@fees_bp.route('/fee-structures/delete/<int:structure_id>', methods=['POST'])
@admin_required
def delete_fee_structure(structure_id):
    try:
        # Unlink students before deleting the structure
        db_manager.execute_query(
            "UPDATE students SET fee_structure_id = NULL WHERE fee_structure_id = ?",
            (structure_id,),
            commit=True
        )
        # Now, check for payments
        payment_linked = db_manager.execute_query(
            "SELECT 1 FROM student_fee_payments WHERE fee_structure_id = ? LIMIT 1",
            (structure_id,),
            fetch_one=True
        )
        if payment_linked:
            flash('Cannot delete fee structure: Payments have been recorded against it. It has been unlinked from students, but the structure itself cannot be removed.', 'danger')
            return redirect(url_for('fees.list_fee_structures'))

        db_manager.execute_query("DELETE FROM fee_structure WHERE id = ?", (structure_id,), commit=True)
        flash('Fee structure deleted successfully.', 'success')
    except sqlite3.IntegrityError as e:
        flash(f'Failed to delete fee structure. It might be in use by payments (Error: {e}).', 'danger')
    except Exception as e:
        flash(f'Error deleting fee structure: {e}', 'danger')
    return redirect(url_for('fees.list_fee_structures'))

@fees_bp.route('/edit-payment/<int:payment_id>', methods=['GET', 'POST'])
@admin_required
def edit_fee_payment(payment_id):
    payment = db_manager.execute_query("SELECT * FROM student_fee_payments WHERE id = ?", (payment_id,), fetch_one=True)
    if not payment:
        flash('Fee payment record not found.', 'danger')
        return redirect(url_for('fees.manage_fee_payments'))

    student = get_student_by_id(payment['student_id'])
    if not student:
        flash('Associated student not found for this payment.', 'danger')
        return redirect(url_for('fees.manage_fee_payments'))

    if request.method == 'POST':
        amount = request.form.get('amount', type=float)
        payment_date = request.form.get('payment_date')
        transaction_id = request.form.get('transaction_id')
        payment_method = request.form.get('payment_method')
        remarks = request.form.get('remarks')

        if not amount or amount <= 0: flash('Invalid amount.', 'danger')
        elif not payment_date: flash('Payment date is required.', 'danger')
        elif not payment_method: flash('Payment method is required.', 'danger')
        else:
            try:
                transaction_id_to_db = transaction_id.strip() if transaction_id else None
                db_manager.execute_query(
                    """UPDATE student_fee_payments SET amount_paid = ?, payment_date = ?, 
                       transaction_id = ?, payment_method = ?, remarks = ? WHERE id = ?""",
                    (amount, payment_date, transaction_id_to_db, payment_method, remarks, payment_id), commit=True)
                flash('Fee payment updated successfully.', 'success')
                return redirect(url_for('fees.view_student_fees', student_id=student['id']))
            except Exception as e:
                flash(f'Failed to update payment: {e}', 'danger')
        
        payment_form_data = request.form.to_dict()
        payment_form_data['id'] = payment_id
        payment_form_data['amount_paid'] = amount
        return render_template('fees/edit_fee_payment.html', payment=payment_form_data, student=student, action="Edit")

    return render_template('fees/edit_fee_payment.html', payment=payment, student=student, action="Edit")

@fees_bp.route('/delete-payment/<int:payment_id>', methods=['POST'])
@admin_required
def delete_fee_payment(payment_id):
    try:
        payment = db_manager.execute_query("SELECT student_id FROM student_fee_payments WHERE id = ?", (payment_id,), fetch_one=True)
        student_id_redirect = payment['student_id'] if payment else None

        db_manager.execute_query("DELETE FROM student_fee_payments WHERE id = ?", (payment_id,), commit=True)
        flash('Fee payment record deleted successfully.', 'success')
        
        if student_id_redirect:
            return redirect(url_for('fees.view_student_fees', student_id=student_id_redirect))
    except Exception as e:
        flash(f'Error deleting fee payment record: {e}', 'danger')

    return redirect(url_for('fees.manage_fee_payments'))

@fees_bp.route('/summary')
@admin_required
def fee_summary():
    """Displays a summary of fees for all students."""
    course_filter = request.args.get('course_id', type=int)
    year_filter = request.args.get('academic_year_id', type=int)

    params = []
    where_clauses = []
    query = """
        SELECT
            s.id AS student_id,
            s.student_name,
            s.surname,
            s.admission_no,
            c.course_name,
            ay.academic_year,
            fs.total_fee,
            COALESCE(SUM(p.amount_paid), 0) AS total_paid
        FROM
            students s
        JOIN
            courses c ON s.course_id = c.id
        JOIN
            academic_years ay ON s.academic_year_id = ay.id
        LEFT JOIN
            fee_structure fs ON s.fee_structure_id = fs.id
        LEFT JOIN
            student_fee_payments p ON s.id = p.student_id
    """

    if course_filter:
        where_clauses.append("s.course_id = ?")
        params.append(course_filter)
    if year_filter:
        where_clauses.append("s.academic_year_id = ?")
        params.append(year_filter)

    if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += """ GROUP BY
            s.id, s.student_name, s.surname, s.admission_no, c.course_name, ay.academic_year, fs.total_fee
        ORDER BY
            c.course_name, ay.academic_year, s.student_name, s.surname;
    """
    student_fee_summary = db_manager.execute_query(query, tuple(params), fetch_all=True)
    
    courses = get_courses()
    academic_years = get_academic_years()
    
    return render_template('fees/fee_summary.html', student_fee_summary=student_fee_summary,
                           courses=courses, academic_years=academic_years,
                           course_filter=course_filter, year_filter=year_filter)
