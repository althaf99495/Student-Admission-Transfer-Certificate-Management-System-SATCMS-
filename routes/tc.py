# routes/tc.py

import os
from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    current_app, send_from_directory
)
from models.db_pool import db_manager, get_student_by_id, get_courses, get_academic_years
from utils.auth_helpers import admin_required
from utils.pdf_utils import TCGenerator, generate_tc_number_for_student
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

# routes/tc.py

# routes/tc.py

@tc_bp.route('/generate/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def generate_tc(student_id):
    """Displays the form to generate a TC and handles its submission."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('tc.select_student'))

    # Check if TC already exists
    if db_manager.execute_query("SELECT 1 FROM transfer_certificates WHERE student_id = ?", (student_id,), fetch_one=True):
        flash('A Transfer Certificate has already been generated for this student.', 'info')
        return redirect(url_for('tc.preview_tc_for_student', student_id=student_id))

    if request.method == 'POST':
        tc_data = {
            'tc_number': request.form.get('tc_number'),
            'issue_date': request.form.get('issue_date'),
            'date_of_leaving': request.form.get('date_of_leaving'),
            'conduct': request.form.get('conduct', 'Good'),
            'last_exam_passed': request.form.get('last_exam_passed'),
            'promotion_status': request.form.get('promotion_status'),
            'notes': request.form.get('notes')
        }

        try:
            # Step 1: Generate the physical TC files
            generator = TCGenerator()
            docx_path, _ = generator.generate_tc_files(dict(student), tc_data)
            
            # Step 2: Save records to database within a single transaction
            with db_manager.get_db_cursor(commit=True) as cursor:
                # Insert the new TC record
                cursor.execute(
                    """INSERT INTO transfer_certificates
                       (student_id, tc_number, issue_date, notes)
                       VALUES (?, ?, ?, ?)""",
                    (student_id, tc_data['tc_number'], tc_data['issue_date'], tc_data['notes'])
                )
                # Update the student's record with leaving date and conduct
                cursor.execute(
                    "UPDATE students SET date_of_leaving = ?, conduct = ? WHERE id = ?",
                    (tc_data['date_of_leaving'], tc_data['conduct'], student_id)
                )

            # Optional: Clean up the temporary .docx file after successful generation and DB commit
            if os.path.exists(docx_path):
                os.remove(docx_path)

            flash(f"TC (No: {tc_data['tc_number']}) generated successfully for {student['student_name']}.", 'success')
            return redirect(url_for('tc.preview_tc_for_student', student_id=student_id))

        except (RuntimeError, sqlite3.Error, FileNotFoundError) as e:
            logger.error(f"TC Generation failed for student {student_id}: {e}", exc_info=True)
            flash(f"Failed to generate TC. Error: {e}", 'danger')
            return render_template('tc/tc_generate.html', student=student, tc_data=request.form)

    # For GET request, prepare default data
    today = datetime.now().strftime(current_app.config['DATE_FORMAT'])
    tc_data = {
        'issue_date': today,
        'date_of_leaving': student['date_of_leaving'] or today,
        'tc_number': generate_tc_number_for_student(student_id),
        'conduct': student['conduct'] or 'Good'
    }
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
    
    # Generate filenames based on the stored TC number
    safe_adm_no = str(student['admission_no']).replace('/', '_')
    safe_tc_no = str(tc_record['tc_number']).replace('/', '_')
    pdf_filename = f"TC_{safe_adm_no}_{safe_tc_no}.pdf"

    # Prepare data for display, similar to how TCGenerator does for DOCX
    generator = TCGenerator()
    
    # Data expected by _prepare_replacement_data from its 'tc_data' argument
    # We source these from the student record (updated during TC gen) and tc_record
    tc_specific_data_for_preview = {
        'date_of_leaving': student['date_of_leaving'],
        'conduct': student['conduct'],
        'promotion_status': tc_record['promotion_status'] if 'promotion_status' in tc_record.keys() else 'N/A', # Access as dict
        # 'tc_number': tc_record['tc_number'], # Not directly used as a placeholder by _prepare_replacement_data
        # 'issue_date': tc_record['issue_date'], # Not directly used as a placeholder by _prepare_replacement_data
        # 'notes': tc_record['notes'] # Not directly used as a placeholder by _prepare_replacement_data
    }

    all_placeholders = generator._prepare_replacement_data(dict(student), tc_specific_data_for_preview)

    placeholder_labels = {
        '[TC_SNO]': "TC S.No. (from Admission No.)",
        '[ADM_NO]': "Admission No.",
        '[STUDENT_NAME]': "Student Name",
        '[FATHER_NAME]': "Father's Name",
        '[NATIONALITY]': "Nationality",
        '[RELIGION]': "Religion",
        '[CASTE]': "Caste",
        '[DOB]': "Date of Birth (DD/MM/YYYY)",
        '[DOB_WORDS]': "Date of Birth (In Words)",
        '[COURSE_NAME_FULL]': "Course (Full Name)",
        '[COURSE_NAME]': "Course (Short Name)",
        '[COURSE_CODE]': "Course Code",
        '[DATE_OF_ADMISSION]': "Date of Admission",
        '[PROMOTION_STATUS]': "Whether Qualified for Promotion", # This will now come from all_placeholders
        '[DATE_OF_LEAVING]': "Date of Leaving",
        '[ACADEMIC_PERIOD]': "Academic Period Studied",
        '[CONDUCT]': "Conduct", # This will now come from all_placeholders
        '[SALUTATION]': "Salutation",
        '[POSSESSIVE_PRONOUN]': "Possessive Pronoun (His/Her)"
    }

    display_items = []
    for key, label in placeholder_labels.items():
        display_items.append((label, all_placeholders.get(key, 'N/A')))
    
    # Add items directly from tc_record that are not part of the standard placeholders
    display_items.append(("TC Number (Generated)", tc_record['tc_number']))
    display_items.append(("Date of Issue (TC)", generator._format_display_date(tc_record['issue_date'])))
    display_items.append(("Remarks/Notes (on TC)", tc_record['notes'] or 'N/A'))

    return render_template('tc/tc_preview.html', student=student, tc_record=tc_record, pdf_filename=pdf_filename, display_items=display_items)

@tc_bp.route('/download/<path:filename>')
@admin_required
def download_tc(filename):
    """Handles the download of generated TC files."""
    directory = current_app.config['TC_OUTPUT_PATH']
    return send_from_directory(directory, filename, as_attachment=True)