from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.db_pool import db_manager, get_courses
from utils.auth_helpers import admin_required
from utils.validators import validate_course_data, ValidationError

courses_bp = Blueprint('courses', __name__)

@courses_bp.route('/')
@admin_required
def list_courses():
    """Displays a list of all courses."""
    courses = get_courses()
    return render_template('courses/list_courses.html', courses=courses)

@courses_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_course():
    """Handles adding a new course."""
    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            validated_data = validate_course_data(form_data)
            
            # Check for existing course code
            exists = db_manager.execute_query(
                "SELECT id FROM courses WHERE course_code = ?",
                (validated_data['course_code'],),
                fetch_one=True
            )
            if exists:
                flash(f"Course code '{validated_data['course_code']}' already exists.", 'danger')
            else:
                db_manager.execute_query(
                    "INSERT INTO courses (course_name, course_code, type, year, course_full_name) VALUES (?, ?, ?, ?, ?)",
                    (validated_data['course_name'], validated_data['course_code'], validated_data['type'], validated_data['year'], validated_data.get('course_full_name')),
                    commit=True
                )
                flash('Course added successfully!', 'success')
                return redirect(url_for('courses.list_courses'))

        except ValidationError as e:
            for field, error_msg in e.errors.items():
                flash(f"{field.replace('_', ' ').title()}: {error_msg}", 'danger')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')
            
    return render_template('courses/add_edit_course.html', action="Add", course={})

@courses_bp.route('/edit/<int:course_id>', methods=['GET', 'POST'])
@admin_required
def edit_course(course_id):
    """Handles editing an existing course."""
    course = db_manager.execute_query("SELECT * FROM courses WHERE id = ?", (course_id,), fetch_one=True)
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('courses.list_courses'))

    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            validated_data = validate_course_data(form_data)
            
            # Check if new course code conflicts with another existing course
            exists = db_manager.execute_query(
                "SELECT id FROM courses WHERE course_code = ? AND id != ?",
                (validated_data['course_code'], course_id),
                fetch_one=True
            )
            if exists:
                 flash(f"Course code '{validated_data['course_code']}' is already in use by another course.", 'danger')
            else:
                db_manager.execute_query(
                    "UPDATE courses SET course_name=?, course_code=?, type=?, year=?, course_full_name=? WHERE id=?",
                    (validated_data['course_name'], validated_data['course_code'], validated_data['type'], validated_data['year'], validated_data.get('course_full_name'), course_id),
                    commit=True
                )
                flash('Course updated successfully!', 'success')
                return redirect(url_for('courses.list_courses'))
        
        except ValidationError as e:
            for field, error_msg in e.errors.items():
                flash(f"{field.replace('_', ' ').title()}: {error_msg}", 'danger')
        except Exception as e:
            flash(f"An unexpected error occurred: {e}", 'danger')

    return render_template('courses/add_edit_course.html', action="Edit", course=course)

@courses_bp.route('/delete/<int:course_id>', methods=['POST'])
@admin_required
def delete_course(course_id):
    """Deletes a course."""
    try:
        # Check if any student is enrolled in this course
        student_count = db_manager.execute_query(
            "SELECT COUNT(id) as count FROM students WHERE course_id = ?",
            (course_id,),
            fetch_one=True
        )['count']
        
        if student_count > 0:
            flash('Cannot delete this course as students are currently enrolled in it.', 'danger')
        else:
            db_manager.execute_query("DELETE FROM courses WHERE id = ?", (course_id,), commit=True)
            flash('Course deleted successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred while deleting the course: {e}', 'danger')
        
    return redirect(url_for('courses.list_courses'))