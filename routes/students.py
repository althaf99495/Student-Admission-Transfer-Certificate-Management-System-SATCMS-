# routes/students.py
import sqlite3
import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_from_directory
from models.db_pool import db_manager, get_courses, get_academic_years, get_student_by_id
from utils.auth_helpers import admin_required # Ensure this is imported
from utils.validators import validate_student_data, ValidationError
from utils.admission_number import generate_admission_number, check_admission_number_exists, get_next_available_admission_number_preview
from datetime import datetime
import logging
from flask_wtf import FlaskForm
from wtforms import FileField, SubmitField
from wtforms.validators import DataRequired

logger = logging.getLogger(__name__)

class CSVUploadForm(FlaskForm):
    csv_file = FileField('CSV File', validators=[DataRequired()])
    submit = SubmitField('Import Students')

students_bp = Blueprint('students', __name__)

@students_bp.route('/list')
@admin_required
def list_students():
    """Displays a paginated list of all students with search and filtering."""
    page = request.args.get('page', 1, type=int)
    per_page = current_app.config.get('STUDENTS_PER_PAGE', 15)
    
    # Search and filter parameters
    search_query = request.args.get('search', '').strip()
    course_filter = request.args.get('course_id', type=int)
    year_filter = request.args.get('academic_year_id', type=int)

    base_query = """
        FROM students s
        JOIN courses c ON s.course_id = c.id
        JOIN academic_years ay ON s.academic_year_id = ay.id
        WHERE (s.student_name LIKE ? OR s.admission_no LIKE ?)
    """
    params = [f'%{search_query}%', f'%{search_query}%']

    if course_filter:
        base_query += " AND s.course_id = ?"
        params.append(course_filter)
    if year_filter:
        base_query += " AND s.academic_year_id = ?"
        params.append(year_filter)

    count_row = db_manager.execute_query(f"SELECT COUNT(s.id) as count {base_query}", tuple(params), fetch_one=True)
    total_students = count_row['count'] if count_row else 0
    
    offset = (page - 1) * per_page
    students = db_manager.execute_query(
        f"""SELECT s.id, s.admission_no, s.student_name,s.surname, s.father_name, c.course_code, ay.academic_year 
            {base_query} ORDER BY s.surname ASC, s.student_name ASC LIMIT ? OFFSET ?""",
        tuple(params + [per_page, offset]),
        fetch_all=True
    )
    
    total_pages = (total_students + per_page - 1) // per_page
    
    courses = get_courses()
    academic_years = get_academic_years()

    return render_template('students/list_students.html', students=students, page=page, total_pages=total_pages,
                           courses=courses, academic_years=academic_years, search_query=search_query,
                           course_filter=course_filter, year_filter=year_filter)

@students_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_student():
    """
    Handles adding a new student. Supports both standard form submission and AJAX.
    On validation failure, it re-renders the form with the user's previously entered data.
    """
    logger.debug(f"Received form data: {request.form}")
    if request.method == 'POST':
        errors_for_template = {}
        form_data = request.form.to_dict()
        original_form_data_for_template = form_data.copy() # Keep original DD-MM-YYYY for re-rendering
        try:
            # Convert date formats from DD-MM-YYYY to YYYY-MM-DD for backend processing
            date_fields = ['dob', 'date_of_admission']
            
            # Define a list of possible input formats for robustness
            # The primary format from config.py should be first
            # Add common variations that might come from user input or unexpected sources
            possible_input_formats = [
                current_app.config['DATE_FORMAT'], # e.g., '%d-%m-%Y'
                '%d/%m/%Y', # DD/MM/YYYY
                '%d.%m.%Y', # DD.MM.YYYY
                '%d-%m-%y', # DD-MM-YY (for two-digit year)
                '%d/%m/%y', # DD/MM/YY (for two-digit year)
            ]

            for field in date_fields:
                if form_data.get(field):
                    raw_date_string = form_data[field].strip()
                    parsed_date_obj = None
                    
                    if raw_date_string:
                        for fmt in possible_input_formats:
                            try:
                                parsed_date_obj = datetime.strptime(raw_date_string, fmt)
                                logger.debug(f"Successfully parsed '{field}' ('{raw_date_string}') with format '{fmt}'")
                                break # Found a working format, break inner loop
                            except ValueError:
                                continue # Try next format
                        
                        if parsed_date_obj:
                            form_data[field] = parsed_date_obj.strftime('%Y-%m-%d') # Convert to YYYY-MM-DD for DB
                            logger.debug(f"Converted '{field}' to DB format: '{form_data[field]}'")
                        else:
                            # If no format worked, raise error
                            logger.error(f"Failed to parse date field '{field}'. String: '{raw_date_string}'. Tried formats: {possible_input_formats}")
                            # Use the primary format for the error message to guide the user
                            errors_for_template[field] = f"Invalid date format. Please use {current_app.config['DATE_FORMAT'].replace('%', '').upper()}."
                    else:
                        # If raw_date_string is empty after strip, it's fine, validation will catch if required
                        form_data[field] = None # Ensure it's None if empty
            
            if errors_for_template:
                raise ValidationError("Invalid date format provided.", errors=errors_for_template)

            # Basic validation of student data (excluding admission number parts initially)
            validated_data = validate_student_data(form_data) 

            # Get academic year details for starting_year
            ay_details = db_manager.execute_query(
                "SELECT academic_year FROM academic_years WHERE id = ?",
                (validated_data['academic_year_id'],), fetch_one=True
            )
            if not ay_details:
                raise ValueError("Academic year details not found.")
            
            years = ay_details['academic_year'].split('-')
            validated_data['starting_year'] = int(years[0])
            validated_data['ending_year'] = int(years[1])
            starting_year_str = years[0]

            # Get course details for course_code and is_special_format
            course_details = db_manager.execute_query(
                "SELECT course_code, is_special_format FROM courses WHERE id = ?",
                (validated_data['course_id'],), fetch_one=True
            )
            if not course_details:
                raise ValueError("Course details not found.")
            
            course_code_str = course_details['course_code'].upper()
            is_course_special = course_details['is_special_format'] == 1

            is_manual_mode = form_data.get('is_manual_admission_mode') == 'on'
            adm_no_to_check = ""
            serial_no_to_store = 0 # This will be the integer value of the serial

            if is_manual_mode:
                manual_serial_str = form_data.get('manual_serial_no', '').strip()
                expected_len = 2 if is_course_special else 3
                max_val = 99 if is_course_special else 999
                
                if not (manual_serial_str.isdigit() and len(manual_serial_str) == expected_len):
                    errors_for_template['manual_serial_no'] = f"Manual serial must be exactly {expected_len} digits (e.g., {'01' if is_course_special else '001'})."
                else:
                    manual_serial_int = int(manual_serial_str)
                    if not (0 <= manual_serial_int <= max_val):
                        errors_for_template['manual_serial_no'] = f"Manual serial must be between 0 and {max_val}."
                    else:
                        # Construct admission number: YYYY + CourseCode + FormattedManualSerial
                        formatted_manual_serial = f"{manual_serial_int:0{expected_len}d}"
                        adm_no_to_check = f"{starting_year_str}{course_code_str}{formatted_manual_serial}"
                        serial_no_to_store = manual_serial_int
                        validated_data['is_manual_admission_no'] = 1
            else:
                # Automatic mode
                adm_no_to_check, serial_no_to_store = generate_admission_number(
                    validated_data['course_id'], validated_data['academic_year_id']
                )
                validated_data['is_manual_admission_no'] = 0

            if errors_for_template: # If manual serial validation failed
                raise ValidationError("Validation error", errors=errors_for_template)

            if not adm_no_to_check: 
                 raise ValueError("Admission number could not be determined.")

            if check_admission_number_exists(adm_no_to_check):
                error_msg = f"Admission number {adm_no_to_check} already exists. Please try again."
                if is_manual_mode:
                    errors_for_template['manual_serial_no'] = error_msg
                else: 
                    errors_for_template['admission_no'] = error_msg # For preview field if shown
                raise ValidationError("Admission number conflict", errors=errors_for_template)

            # Automatically assign fee_structure_id
            fee_structure = db_manager.execute_query(
                "SELECT id FROM fee_structure WHERE course_id = ? AND academic_year_id = ?",
                (validated_data['course_id'], validated_data['academic_year_id']),
                fetch_one=True
            )
            validated_data['fee_structure_id'] = fee_structure['id'] if fee_structure else None

            validated_data['admission_no'] = adm_no_to_check
            validated_data['serial_no'] = serial_no_to_store

            columns = ', '.join(validated_data.keys())
            placeholders = ', '.join(['?'] * len(validated_data))
            values = tuple(validated_data.values())

            with db_manager.get_db_cursor(commit=True) as cursor:
                cursor.execute(f"INSERT INTO students ({columns}) VALUES ({placeholders})", values)
                new_student_id = cursor.lastrowid
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'message': f"Student '{validated_data['student_name']}' added successfully!",
                    'admission_no': adm_no_to_check,
                    'student_url': url_for('students.view_student', student_id=new_student_id)
                }), 200

            flash(f"Student '{validated_data['student_name']}' added successfully with admission number {adm_no_to_check}.", 'success') # Use adm_no_to_check
            return redirect(url_for('students.list_students'))

        except (ValidationError, sqlite3.Error, ValueError) as e: # Added ValueError
            errors = {**errors_for_template, **(e.errors if isinstance(e, ValidationError) else {'db_error': str(e)})}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'errors': errors}), 400
            
            for field, error_msg in errors.items():
                flash(f"{field.replace('_', ' ').title()}: {error_msg}", 'danger')
            
            courses = get_courses()
            academic_years = get_academic_years()
            return render_template('students/add_student.html', courses=courses, academic_years=academic_years, form_data=original_form_data_for_template, errors=errors, now=datetime.now())

    # GET request
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('students/add_student.html', courses=courses, academic_years=academic_years, form_data={}, errors={}, now=datetime.now()) # Pass errors={} for GET

@students_bp.route('/edit/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    """Handles editing an existing student's details."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        original_form_data_for_template = form_data.copy()
        try:
            # Convert date formats from display format to YYYY-MM-DD for backend processing
            date_fields = ['dob', 'date_of_admission', 'date_of_leaving']
            errors = {}
            
            possible_input_formats = [
                current_app.config['DATE_FORMAT'], # e.g., '%d-%m-%Y'
                '%d/%m/%Y', # DD/MM/YYYY
                '%d.%m.%Y', # DD.MM.YYYY
                '%d-%m-%y', # DD-MM-YY
                '%d/%m/%y', # DD/MM/YY
            ]

            for field in date_fields:
                if form_data.get(field):
                    raw_date_string = form_data[field].strip()
                    parsed_date_obj = None
                    if raw_date_string:
                        for fmt in possible_input_formats:
                            try:
                                parsed_date_obj = datetime.strptime(raw_date_string, fmt)
                                break
                            except ValueError:
                                continue
                        if parsed_date_obj:
                            form_data[field] = parsed_date_obj.strftime('%Y-%m-%d')
                        else:
                            errors[field] = f"Invalid date format. Please use {current_app.config['DATE_FORMAT'].replace('%', '').upper()}."
                    else:
                        form_data[field] = None

            if errors:
                raise ValidationError("Invalid date format provided.", errors=errors)

            validated_data = validate_student_data(form_data, is_edit=True) # Pass is_edit if validation rules differ
            
            # Admission number is not regenerated on edit
            # Update starting/ending year if academic year changed
            ay_details = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (validated_data['academic_year_id'],), fetch_one=True)
            if ay_details:
                years = ay_details['academic_year'].split('-')
                validated_data['starting_year'] = int(years[0])
                validated_data['ending_year'] = int(years[1])
                
            
            # Automatically assign fee_structure_id
            fee_structure = db_manager.execute_query(
                "SELECT id FROM fee_structure WHERE course_id = ? AND academic_year_id = ?",
                (validated_data['course_id'], validated_data['academic_year_id']),
                fetch_one=True
            )
            validated_data['fee_structure_id'] = fee_structure['id'] if fee_structure else None

            update_clause = ', '.join([f"{key} = ?" for key in validated_data.keys()])
            values = tuple(list(validated_data.values()) + [student_id])
            
            db_manager.execute_query(f"UPDATE students SET {update_clause} WHERE id = ?", values, commit=True)
            flash(f"Student '{validated_data['student_name']}' updated successfully.", 'success')
            return redirect(url_for('students.view_student', student_id=student_id))
            
        except (ValidationError, sqlite3.Error) as e:
            errors = e.errors if isinstance(e, ValidationError) else {'db_error': str(e)}
            for field, error_msg in errors.items():
                flash(f"{field.replace('_', ' ').title()}: {error_msg}", 'danger')
            
            # On validation error, re-render form with submitted data
            courses = get_courses()
            academic_years = get_academic_years()
            return render_template('students/edit_student.html', student=original_form_data_for_template, student_id=student_id, courses=courses, academic_years=academic_years, errors=e.errors if isinstance(e, ValidationError) else {})

    # GET request
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))
    
    # Convert student Row to a mutable dict
    student_dict = dict(student)

    # Convert date formats for display
    date_fields = ['dob', 'date_of_admission', 'date_of_leaving']
    display_format = current_app.config['DISPLAY_DATE_FORMAT']
    for field in date_fields:
        if student_dict.get(field):
            try:
                date_obj = datetime.strptime(student_dict[field], '%Y-%m-%d')
                student_dict[field] = date_obj.strftime(display_format)
            except (ValueError, TypeError):
                pass # Ignore errors, leave as is

    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('students/edit_student.html', student=student_dict, student_id=student_id, courses=courses, academic_years=academic_years, errors={})

@students_bp.route('/view/<int:student_id>')
@admin_required
def view_student(student_id):
    """Shows a detailed view of a single student."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))

    # Fetch fee payments for the student
    payments = db_manager.execute_query(
        """SELECT p.*, fs.total_fee
           FROM student_fee_payments p
           LEFT JOIN fee_structure fs ON p.fee_structure_id = fs.id
           WHERE p.student_id = ?
           ORDER BY p.payment_date ASC""", # Chronological order
        (student_id,),
        fetch_all=True
    )

    # Fetch TC record for the student
    tc_record = db_manager.execute_query(
        "SELECT * FROM transfer_certificates WHERE student_id = ?",
        (student_id,),
        fetch_one=True
    )
    # Calculate TC issued count (0 or 1 based on current system logic)
    tc_issued_count = 1 if tc_record else 0

    # Compile event history
    event_history = []

    if student['date_of_admission']:
        event_history.append({
            'date': datetime.strptime(student['date_of_admission'], '%Y-%m-%d'),
            'type': 'Admission',
            'description': f"Admitted to {student['course_name']} ({student['academic_year']}). Type: {student['type']}.",
            'details': {} # No specific details for admission event in this format
        })

    if payments:
        for payment in payments:
            if payment['payment_date']: # Check if the key exists and has a value
                event_history.append({
                    'date': datetime.strptime(payment['payment_date'], '%Y-%m-%d'),
                    'type': 'Fee Payment',
                    'description': f"Paid {payment['amount_paid']:.2f} via {payment['payment_method']}.",
                    'details': {
                        'Transaction ID': payment['transaction_id'] if payment['transaction_id'] else 'N/A',
                        'Remarks': payment['remarks'] if payment['remarks'] else 'N/A'
                    }
                })

    if tc_record and tc_record['issue_date']:
        event_history.append({
            'date': datetime.strptime(tc_record['issue_date'], '%Y-%m-%d'),
            'type': 'TC Issued',
            'description': f"Transfer Certificate (No: {tc_record['tc_number']}) issued."
        })

    event_history.sort(key=lambda x: x['date'])

    return render_template('students/view_student.html', student=student, payments=payments, tc_record=tc_record, event_history=event_history, tc_issued_count=tc_issued_count)

@students_bp.route('/delete/<int:student_id>', methods=['POST'])
@admin_required
def delete_student(student_id):
    """Deletes a student record."""
    try:
        db_manager.execute_query("DELETE FROM students WHERE id = ?", (student_id,), commit=True)
        flash('Student deleted successfully.', 'success')
    except Exception as e:
        flash(f'Error deleting student. They may have related records (TCs, Fees). Details: {e}', 'danger')
    return redirect(url_for('students.list_students'))

@students_bp.route('/api/next-admission-no')
@admin_required
def api_next_admission_no():
    """API endpoint to get the next admission number for preview."""
    course_id = request.args.get('course_id', type=int)
    academic_year_id = request.args.get('academic_year_id', type=int)
    
    if not course_id or not academic_year_id:
        return jsonify({'error': 'Course and Academic Year are required.'}), 400
        
    preview_no = get_next_available_admission_number_preview(course_id, academic_year_id)
    return jsonify({'next_admission_number': preview_no})

@students_bp.route('/regenerate-admission-numbers', methods=['POST'])
@admin_required
def regenerate_admission_numbers_view():
    """
    Handles the request to regenerate admission numbers for a selected academic year.
    This is a sensitive operation and should be used with caution.
    """
    academic_year_id = request.form.get('regenerate_academic_year_id', type=int)
    course_id = request.form.get('regenerate_course_id') # Keep as string initially to check if empty
    
    # Convert course_id to int if provided, else None
    course_id = int(course_id) if course_id else None

    if not academic_year_id:
        flash("Please select an academic year to regenerate admission numbers.", 'danger')
        return redirect(url_for('students.list_students'))

    from utils.admission_number import regenerate_admission_numbers_for_academic_year # Import here to avoid circular dependency if any
    course_name_for_flash = ""
    try:
        ay_details = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (academic_year_id,), fetch_one=True)
        ay_name = ay_details['academic_year'] if ay_details else f"ID {academic_year_id}"

        if course_id:
            course_details = db_manager.execute_query("SELECT course_name FROM courses WHERE id = ?", (course_id,), fetch_one=True)
            course_name_for_flash = f" for course '{course_details['course_name']}'" if course_details else f" for course ID {course_id}"

        updated_count = regenerate_admission_numbers_for_academic_year(academic_year_id, course_id=course_id)
        flash(f"Successfully regenerated {updated_count} automatic admission numbers in academic year '{ay_name}'{course_name_for_flash}. Manual entries were skipped. Students are sorted by surname, then name.", 'success')
    except ValueError as ve:
        flash(f"Error during regeneration: {str(ve)}", 'danger')
    except Exception as e:
        current_app.logger.error(f"Failed to regenerate admission numbers for AY ID {academic_year_id}: {e}", exc_info=True)
        flash(f"An unexpected error occurred during admission number regeneration: {e}", 'danger')
    
    return redirect(url_for('students.list_students'))

def _add_student_from_csv(cursor, row_data):
    try:
        # Basic validation of student data
        validated_data = validate_student_data(row_data)

        # Get academic year details for starting_year
        ay_details = db_manager.execute_query(
            "SELECT academic_year FROM academic_years WHERE id = ?",
            (validated_data['academic_year_id'],), fetch_one=True
        )
        if not ay_details:
            raise ValueError("Academic year details not found.")
        
        years = ay_details['academic_year'].split('-')
        validated_data['starting_year'] = int(years[0])
        validated_data['ending_year'] = int(years[1])

        # Generate admission number
        admission_no, serial_no = generate_admission_number(
            validated_data['course_id'], validated_data['academic_year_id']
        )
        validated_data['admission_no'] = admission_no
        validated_data['serial_no'] = serial_no
        validated_data['is_manual_admission_no'] = 0

        # Automatically assign fee_structure_id
        fee_structure = db_manager.execute_query(
            "SELECT id FROM fee_structure WHERE course_id = ? AND academic_year_id = ?",
            (validated_data['course_id'], validated_data['academic_year_id']),
            fetch_one=True
        )
        validated_data['fee_structure_id'] = fee_structure['id'] if fee_structure else None

        columns = ', '.join(validated_data.keys())
        placeholders = ', '.join(['?'] * len(validated_data))
        values = tuple(validated_data.values())

        cursor.execute(f"INSERT INTO students ({columns}) VALUES ({placeholders})", values)

    except (ValidationError, ValueError) as e:
        # Re-raise the exception to be caught in the main bulk_import function
        raise e


@students_bp.route('/bulk_import', methods=['GET', 'POST'])
@admin_required
def bulk_import():
    form = CSVUploadForm()
    if form.validate_on_submit():
        csv_file = form.csv_file.data
        errors = []
        success_count = 0
        
        try:
            with io.TextIOWrapper(csv_file, encoding='utf-8') as text_file:
                csv_reader = csv.DictReader(text_file)
                students_data = list(csv_reader)

            with db_manager.get_db_cursor(commit=True) as cursor:
                for i, row in enumerate(students_data):
                    try:
                        # Map CSV columns to form fields
                        form_data = {
                            'student_name': row.get('student_name'),
                            'surname': row.get('surname'),
                            'father_name': row.get('father_name'),
                            'mother_name': row.get('mother_name'),
                            'dob': row.get('dob'),
                            'gender': row.get('gender'),
                            'mobile_no': row.get('mobile_no'),
                            'email': row.get('email'),
                            'address': row.get('address'),
                            'course_name': row.get('course_name'),
                            'academic_year': row.get('academic_year'),
                            'date_of_admission': row.get('date_of_admission'),
                            'type': row.get('type'),
                            'nationality': row.get('nationality'),
                            'religion': row.get('religion'),
                            'caste': row.get('caste'),
                            'category': row.get('category'),
                        }

                        # Get course_id from course_name
                        course = db_manager.execute_query("SELECT id FROM courses WHERE course_name = ?", (form_data['course_name'],), fetch_one=True)
                        if not course:
                            raise ValueError(f"Course '{form_data['course_name']}' not found.")
                        form_data['course_id'] = course['id']

                        # Get academic_year_id from academic_year
                        academic_year = db_manager.execute_query("SELECT id FROM academic_years WHERE academic_year = ?", (form_data['academic_year'],), fetch_one=True)
                        if not academic_year:
                            raise ValueError(f"Academic year '{form_data['academic_year']}' not found.")
                        form_data['academic_year_id'] = academic_year['id']
                        
                        _add_student_from_csv(cursor, form_data)
                        success_count += 1
                    except (ValidationError, ValueError) as e:
                        errors.append(f"Row {i+2}: {e}")

            if errors:
                flash(f'Import completed with {len(errors)} errors.', 'warning')
                for error in errors:
                    flash(error, 'danger')
            else:
                flash(f'Successfully imported {success_count} students.', 'success')

        except Exception as e:
            flash(f'An unexpected error occurred: {e}', 'danger')
            
        return redirect(url_for('students.list_students'))
        
    return render_template('students/bulk_import.html', form=form)


@students_bp.route('/download_sample_csv')
@admin_required
def download_sample_csv():
    return send_from_directory('static', 'sample_student_import.csv', as_attachment=True)
