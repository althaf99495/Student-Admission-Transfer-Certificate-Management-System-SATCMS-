from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.db_pool import db_manager, get_academic_years
from utils.auth_helpers import admin_required
from utils.validators import validate_academic_year_format # Import validate_academic_year_format
from utils.caching import cache_manager, clear_cache # Import cache_manager and clear_cache

academic_years_bp = Blueprint('academic_years', __name__)

@academic_years_bp.route('/')
@admin_required
def list_academic_years():
    """Displays a list of all academic years."""
    years = get_academic_years()
    return render_template('academic_years/list_academic_years.html', academic_years=years)

@academic_years_bp.route('/add', methods=['GET', 'POST'])
@admin_required
def add_academic_year():
    """Handles adding a new academic year."""
    if request.method == 'POST':
        year_str = request.form.get('academic_year', '').strip()
        
        if not validate_academic_year_format(year_str):
            flash('Invalid academic year format. Use YYYY-YYYY.', 'danger')
        else:
            exists = db_manager.execute_query(
                "SELECT id FROM academic_years WHERE academic_year = ?",
                (year_str,),
                fetch_one=True
            )
            if exists:
                flash(f'Academic year {year_str} already exists.', 'danger')
            else:
                db_manager.execute_query(
                    "INSERT INTO academic_years (academic_year) VALUES (?)",
                    (year_str,),
                    commit=True
                )
                clear_cache() # Clear cache after adding an academic year
                flash('Academic year added successfully!', 'success')
                return redirect(url_for('academic_years.list_academic_years'))
                
    return render_template('academic_years/add_edit_academic_year.html', action="Add", year={})

@academic_years_bp.route('/edit/<int:year_id>', methods=['GET', 'POST'])
@admin_required
def edit_academic_year(year_id):
    """Handles editing an existing academic year."""
    year = db_manager.execute_query("SELECT * FROM academic_years WHERE id = ?", (year_id,), fetch_one=True)
    if not year:
        flash('Academic year not found.', 'danger')
        return redirect(url_for('academic_years.list_academic_years'))

    if request.method == 'POST':
        year_str = request.form.get('academic_year', '').strip()
        
        if not validate_academic_year_format(year_str):
            flash('Invalid academic year format. Use YYYY-YYYY.', 'danger')
        else:
            exists = db_manager.execute_query(
                "SELECT id FROM academic_years WHERE academic_year = ? AND id != ?",
                (year_str, year_id),
                fetch_one=True
            )
            if exists:
                flash(f"Academic year {year_str} already exists.", 'danger')
            else:
                db_manager.execute_query(
                    "UPDATE academic_years SET academic_year = ? WHERE id = ?",
                    (year_str, year_id),
                    commit=True
                )
                clear_cache() # Clear cache after editing an academic year
                flash('Academic year updated successfully!', 'success')
                return redirect(url_for('academic_years.list_academic_years'))
                
    return render_template('academic_years/add_edit_academic_year.html', action="Edit", year=year)

@academic_years_bp.route('/delete/<int:year_id>', methods=['POST'])
@admin_required
def delete_academic_year(year_id):
    """Deletes an academic year."""
    try:
        student_count = db_manager.execute_query(
            "SELECT COUNT(id) as count FROM students WHERE academic_year_id = ?",
            (year_id,),
            fetch_one=True
        )['count']
        
        if student_count > 0:
            flash('Cannot delete this academic year as students are associated with it.', 'danger')
        else:
            db_manager.execute_query("DELETE FROM academic_years WHERE id = ?", (year_id,), commit=True)
            clear_cache() # Clear cache after deleting an academic year
            flash('Academic year deleted successfully.', 'success')
    except Exception as e:
        flash(f'An error occurred while deleting the academic year: {e}', 'danger')
        
    return redirect(url_for('academic_years.list_academic_years'))