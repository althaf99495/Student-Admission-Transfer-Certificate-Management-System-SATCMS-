# routes/students.py

import sqlite3
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from models.db_pool import db_manager, get_courses, get_academic_years, get_student_by_id
from utils.auth_helpers import admin_required
from utils.validators import validate_student_data, ValidationError
from utils.admission_number import generate_admission_number, check_admission_number_exists, get_next_available_admission_number_preview
from datetime import datetime

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
        f"""SELECT s.id, s.admission_no, s.student_name, s.father_name, c.course_code, ay.academic_year 
            {base_query} ORDER BY s.admission_no DESC LIMIT ? OFFSET ?""",
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
    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            validated_data = validate_student_data(form_data)
            
            adm_no, serial_no = generate_admission_number(validated_data['course_id'], validated_data['academic_year_id'])
            
            if check_admission_number_exists(adm_no):
                 # For AJAX requests, return a JSON error
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'errors': {'admission_no': f"Admission number {adm_no} already exists. Please try again."}}), 400
                flash(f"Generated admission number {adm_no} already exists. Please try again.", 'danger')
                # Re-render with existing data
                courses = get_courses()
                academic_years = get_academic_years()
                return render_template('students/add_student.html', courses=courses, academic_years=academic_years, form_data=form_data, now=datetime.now())
            
            # Populate year fields from academic year
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

            validated_data['admission_no'] = adm_no
            validated_data['serial_no'] = serial_no

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
            

            with db_manager.get_db_cursor(commit=True) as cursor:
                cursor.execute(f"INSERT INTO students ({columns}) VALUES ({placeholders})", values)
                new_student_id = cursor.lastrowid
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'message': f"Student '{validated_data['student_name']}' added successfully!",
                    'admission_no': adm_no,
                    'student_url': url_for('students.view_student', student_id=new_student_id)
                }), 200

            flash(f"Student '{validated_data['student_name']}' added successfully with admission number {adm_no}.", 'success')
            return redirect(url_for('students.list_students'))

        except (ValidationError, sqlite3.Error) as e:
            errors = e.errors if isinstance(e, ValidationError) else {'db_error': str(e)}
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'errors': errors}), 400
            
            for field, error_msg in errors.items():
                flash(f"{field.replace('_', ' ').title()}: {error_msg}", 'danger')
            
            courses = get_courses()
            academic_years = get_academic_years()
            return render_template('students/add_student.html', courses=courses, academic_years=academic_years, form_data=form_data, now=datetime.now())

    # GET request
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('students/add_student.html', courses=courses, academic_years=academic_years, form_data={}, now=datetime.now())

@students_bp.route('/edit/<int:student_id>', methods=['GET', 'POST'])
@admin_required
def edit_student(student_id):
    """Handles editing an existing student's details."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            validated_data = validate_student_data(form_data)
            
            # Admission number is not regenerated on edit
            # Update starting/ending year if academic year changed
            ay_details = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (validated_data['academic_year_id'],), fetch_one=True)
            if ay_details:
                years = ay_details['academic_year'].split('-')
                validated_data['starting_year'] = int(years[0])
                validated_data['ending_year'] = int(years[1])
                
            
            # Automatically update fee_structure_id based on course and academic year
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
            return render_template('students/edit_student.html', student=form_data, student_id=student_id, courses=courses, academic_years=academic_years)

    # GET request
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))

    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('students/edit_student.html', student=student, student_id=student_id, courses=courses, academic_years=academic_years)

@students_bp.route('/view/<int:student_id>')
@admin_required
def view_student(student_id):
    """Shows a detailed view of a single student."""
    student = get_student_by_id(student_id)
    if not student:
        flash('Student not found.', 'danger')
        return redirect(url_for('students.list_students'))
    return render_template('students/view_student.html', student=student)

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