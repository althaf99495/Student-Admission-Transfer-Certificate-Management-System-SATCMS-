# routes/tc.py

import os
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory, g # Import g
)
from models.db_pool import db_manager, get_student_by_id, get_courses, get_academic_years
from utils.auth_helpers import admin_required
from utils.pdf_utils import TCGenerator, generate_tc_number_for_student
from utils.date_utils import convert_date_to_words # NEW IMPORT
from datetime import datetime
import logging
import sqlite3

tc_bp = Blueprint('tc', __name__)
logger = logging.getLogger(__name__)

@tc_bp.route('/select-student', methods=['GET'])
@admin_required
def select_student():
    """Page to search and filter students for TC generation. """
    try:
        search_query = request.args.get('search', '').strip()
        course_id_filter = request.args.get('course_id', type=int)
        academic_year_id_filter = request.args.get('academic_year_id', type=int)

        # Query to find students who DO NOT have a TC yet
        base_query = """
            SELECT s.id, s.student_name, s.admission_no, c.course_name, ay.academic_year
            FROM students s
            JOIN courses c ON s.course_id = c.id
            JOIN academic_years ay ON s.academic_year_id = ay.id
            WHERE s.id NOT IN (SELECT student_id FROM transfer_certificates)
        """
        params = []
        conditions = []

        if search_query:
            conditions.append("(s.student_name LIKE ? OR s.admission_no LIKE ?)")
            params.extend([f'%{search_query}%', f'%{search_query}%'])
        if course_id_filter:
            conditions.append("s.course_id = ?")
            params.append(course_id_filter)
        if academic_year_id_filter:
            conditions.append("s.academic_year_id = ?")
            params.append(academic_year_id_filter)

        if conditions:
            base_query += " AND " + " AND ".join(conditions)
        base_query += " ORDER BY s.student_name LIMIT 100"

        students = db_manager.execute_query(base_query, tuple(params), fetch_all=True)
        courses = get_courses()
        academic_years = get_academic_years()

        return render_template(
            'tc/select_student.html',
            students=students, courses=courses, academic_years=academic_years,
            search_query=search_query, course_id_filter=course_id_filter,
            academic_year_id_filter=academic_year_id_filter
        )
    except Exception as e:
        logger.error(f"Error fetching students for TC selection: {e}", exc_info=True)
        flash("An error occurred while fetching student data.", "danger")
        return render_template('tc/select_student.html', students=[], courses=[], academic_years=[])

@tc_bp.route('/redirect-to-generate', methods=['POST'])
@admin_required
def redirect_to_generate_tc():
    """Handles form submission from selection page and redirects to the generation form."""
    student_id = request.form.get('student_id')
    if not student_id:
        flash("Please select a student to proceed.", "warning")
        return redirect(url_for('tc.select_student'))
    return redirect(url_for('tc.generate_tc', student_id=student_id))


@tc_bp.route('/generate/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def generate_tc(student_id):
    """Displays the form to generate a TC and handles its submission."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('tc.select_student'))
    student = dict(student) # Convert sqlite3.Row to a dictionary for easier attribute access

    # Check if TC already exists
    if db_manager.execute_query("SELECT 1 FROM transfer_certificates WHERE student_id = ?", (student_id,), fetch_one=True):
        flash('A Transfer Certificate has already been generated for this student.', 'info')
        return redirect(url_for('tc.preview_tc_for_student', student_id=student_id))

    if request.method == 'POST':
        # Consistently use tc_form_input for data from the POST request
        tc_form_input = {
            'tc_number': request.form.get('tc_number'),
            'issue_date': request.form.get('issue_date'),
            'date_of_leaving': request.form.get('date_of_leaving'),
            'conduct': request.form.get('conduct') or 'Good', # Use conduct from TC form, default to 'Good' if empty
            'promotion_status': request.form.get('promotion_status'),
            'notes': request.form.get('notes'),
            'dob_in_words': '' # Placeholder, will be set below
        }

        # --- Date Conversion and Validation ---
        form_dol_str = tc_form_input.get('date_of_leaving')
        form_doi_str = tc_form_input.get('issue_date') # Date of Issue
        student_doa_str = student['date_of_admission'] # From DB (should be YYYY-MM-DD)

        if not form_dol_str:
            flash('Date of Leaving is required for the TC.', 'danger')
            return render_template('tc/tc_generate.html', student=student, tc_data=tc_form_input)
        if not form_doi_str:
            flash('Date of Issue is required for the TC.', 'danger')
            return render_template('tc/tc_generate.html', student=student, tc_data=tc_form_input)

        try:
            # Convert dates from display format (e.g., dd-mm-yyyy) to DB format (YYYY-MM-DD)
            input_format = current_app.config.get('DATE_FORMAT', '%d-%m-%Y')
            date_of_leaving_obj = datetime.strptime(form_dol_str, input_format).date()
            date_of_issue_obj = datetime.strptime(form_doi_str, input_format).date()

            # Store back in YYYY-MM-DD format for DB operations
            tc_form_input['date_of_leaving'] = date_of_leaving_obj.strftime('%Y-%m-%d')
            tc_form_input['issue_date'] = date_of_issue_obj.strftime('%Y-%m-%d')

            if student_doa_str: # student_doa_str is NOT NULL in schema
                date_of_admission_obj = datetime.strptime(student_doa_str, '%Y-%m-%d').date()
                if date_of_leaving_obj < date_of_admission_obj:
                    flash('Date of Leaving cannot be before Date of Admission.', 'danger')
                    # Re-render with original DD-MM-YYYY format by reverting the change
                    tc_form_input['date_of_leaving'] = form_dol_str
                    tc_form_input['issue_date'] = form_doi_str
                    return render_template('tc/tc_generate.html', student=student, tc_data=tc_form_input)
        except ValueError:
            flash(f"Invalid date format. Please use {input_format.replace('%', '').upper()}.", 'danger')
            return render_template('tc/tc_generate.html', student=student, tc_data=tc_form_input)

        # Convert DOB to words for TC document
        student_dob_from_db = student.get('dob')
        logger.debug(f"TC Generation: Raw DOB from DB for student {student_id}: '{student_dob_from_db}' (type: {type(student_dob_from_db)})")

        # Check if DOB is present and not just whitespace
        if student_dob_from_db and student_dob_from_db.strip():
            tc_form_input['dob_in_words'] = convert_date_to_words(student_dob_from_db, input_format='%Y-%m-%d')
            if tc_form_input['dob_in_words'] == "INVALID DATE":
                logger.warning(f"DOB_WORDS conversion failed for student {student_id}. Raw DOB from DB: '{student_dob_from_db}'. Setting to 'INVALID DATE'.")
        else:
            tc_form_input['dob_in_words'] = 'N/A'
            logger.warning(f"Student {student_id} has no valid DOB in DB (or it's empty/whitespace). Setting DOB_WORDS to 'N/A'. Raw DOB from DB: '{student_dob_from_db}'.")

        try:
            # Step 1: Generate the physical TC files
            generator = TCGenerator()
            docx_path, _ = generator.generate_tc_files(dict(student), tc_form_input)
            
            # Step 2: Save records to database within a single transaction
            with db_manager.get_db_cursor(commit=True) as cursor:
                # Insert the new TC record
                cursor.execute(
                    """INSERT INTO transfer_certificates
                       (student_id, tc_number, issue_date, notes, promotion_status)
                       VALUES (?, ?, ?, ?, ?)""",
                    (student_id, tc_form_input['tc_number'], tc_form_input['issue_date'],
                     tc_form_input['notes'], tc_form_input.get('promotion_status'))
                )
                # Update the student's record with leaving date and conduct
                cursor.execute(
                    "UPDATE students SET date_of_leaving = ?, conduct = ? WHERE id = ?",
                    (tc_form_input['date_of_leaving'], tc_form_input['conduct'], student_id)
                )

            

            flash(f"TC (No: {tc_form_input['tc_number']}) generated successfully for {student['student_name']}.", 'success')
            return redirect(url_for('tc.preview_tc_for_student', student_id=student_id))

        except (RuntimeError, sqlite3.Error, FileNotFoundError) as e:
            logger.error(f"TC Generation failed for student {student_id}: {e}", exc_info=True)
            flash(f"Failed to generate TC. Error: {e}", 'danger')
            return render_template('tc/tc_generate.html', student=student, tc_data=tc_form_input)

    # For GET request, prepare default data
    display_format = current_app.config.get('DISPLAY_DATE_FORMAT', '%d-%m-%Y')
    today_formatted = datetime.now().strftime(display_format) # Date of Issue

    # Convert date_of_leaving from DB (YYYY-MM-DD) to display format
    date_of_leaving_display = student['date_of_leaving']
    if date_of_leaving_display:
        try:
            date_of_leaving_display = datetime.strptime(date_of_leaving_display, '%Y-%m-%d').strftime(display_format)
        except (ValueError, TypeError):
            pass # Keep original on error, or default below
    else:
        # Default to March 1st of the current year if date_of_leaving is not set
        current_year = datetime.now().year
        # Ensure March 1st is a valid date (it always is)
        may_first_current_year = datetime(current_year, 5, 1) # Changed month from 3 (March) to 5 (May)
        date_of_leaving_display = may_first_current_year.strftime(display_format)

    tc_data = {
        'issue_date': today_formatted,
        'date_of_leaving': date_of_leaving_display,
        'tc_number': generate_tc_number_for_student(student_id),
        'conduct': student.get('conduct', 'Good'),
        'dob_in_words': '' # Placeholder, will be set below
    }
    # Convert DOB to words for TC document (for GET request display)
    student_dob_from_db = student.get('dob')
    logger.debug(f"TC Generation (GET): Raw DOB from DB for student {student_id}: '{student_dob_from_db}' (type: {type(student_dob_from_db)})")

    if student_dob_from_db and student_dob_from_db.strip():
        tc_data['dob_in_words'] = convert_date_to_words(student_dob_from_db, input_format='%Y-%m-%d')
        if tc_data['dob_in_words'] == "INVALID DATE":
            logger.warning(f"DOB_WORDS conversion failed for student {student_id} (GET request). Raw DOB from DB: '{student_dob_from_db}'. Setting to 'INVALID DATE'.")
    else:
        tc_data['dob_in_words'] = 'N/A'
        logger.warning(f"Student {student_id} has no valid DOB in DB (or it's empty/whitespace) for GET request. Setting DOB_WORDS to 'N/A'. Raw DOB from DB: '{student_dob_from_db}'.")
    return render_template('tc/tc_generate.html', student=student, tc_data=tc_data)

@tc_bp.route('/preview/<int:student_id>')
@admin_required
def preview_tc_for_student(student_id):
    """Shows a preview/download page for an already generated TC."""
    student = get_student_by_id(student_id)
    tc_record = db_manager.execute_query("SELECT * FROM transfer_certificates WHERE student_id = ?", (student_id,), fetch_one=True)

    if not student or not tc_record:
        flash("TC record not found for this student.", "warning")
        return redirect(url_for('tc.select_student'))
    
    # Generate expected PDF filename based on the stored TC number and student data
    safe_adm_no = str(student['admission_no']).replace('/', '_')
    safe_tc_no = str(tc_record['tc_number']).replace('/', '_')
    pdf_filename = f"TC_{safe_adm_no}_{safe_tc_no}.pdf"

    # Prepare data for display directly from student and tc_record
    # This avoids relying on internal methods of TCGenerator
    # If you need formatted dates, use the template filters directly in the template

    # Simplified data structure for display
    display_items = [
        ("TC Number", tc_record['tc_number']),
        ("Date of Issue", tc_record['issue_date']), # Use filter in template
        ("Date of Leaving", student['date_of_leaving']), # Use filter in template
        ("Student Name", student['student_name']),
        ("Admission No", student['admission_no']),
        ("Course", f"{student['course_name']} ({student['course_code']})"),
        ("Academic Year", student['academic_year']),
        ("Father's Name", student['father_name']),
        ("Date of Birth", student['dob']), # Use filter in template
        ("Nationality", student['nationality'] or 'N/A'),
        ("Religion", student['religion'] or 'N/A'),
        ("Caste", student['caste'] or 'N/A'),
        ("Conduct", student['conduct'] or 'N/A'),
        ("Promotion Status", tc_record['promotion_status'] if tc_record and 'promotion_status' in tc_record.keys() and tc_record['promotion_status'] else 'N/A'),
        ("Notes/Remarks", tc_record['notes'] or 'N/A'),
        # Add other relevant fields from student or tc_record as needed
    ]

    # You might still want to pass the raw student and tc_record objects
    # to the template for easier access to all fields.

    return render_template('tc/tc_preview.html', student=student, tc_record=tc_record, pdf_filename=pdf_filename, display_items=display_items)

@tc_bp.route('/download/<path:filename>')
@admin_required
def download_tc(filename):
    """Handles the download of generated TC files."""
    directory = current_app.config['TC_OUTPUT_PATH']
    return send_from_directory(directory, filename, as_attachment=True)

@tc_bp.route('/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_tc(student_id):
    """
    Deletes a Transfer Certificate record for a student and resets
    the student's date_of_leaving and conduct fields.
    """
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))

    try:
        with db_manager.get_db_cursor(commit=True) as cursor:
            # 1. Delete the TC record
            cursor.execute("DELETE FROM transfer_certificates WHERE student_id = ?", (student_id,))
            # 2. Reset date_of_leaving and conduct in the students table
            cursor.execute("UPDATE students SET date_of_leaving = NULL, conduct = 'Good' WHERE id = ?", (student_id,))
        flash(f'Transfer Certificate for {student["student_name"]} deleted successfully. Student\'s Date of Leaving and Conduct have been reset.', 'success')
    except Exception as e:
        logger.error(f"Error deleting TC for student {student_id}: {e}", exc_info=True)
        flash(f'Error deleting Transfer Certificate: {e}', 'danger')
    return redirect(url_for('students.view_student', student_id=student_id))