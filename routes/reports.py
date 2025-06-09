import os
from flask import Blueprint, render_template, request, flash, current_app, send_from_directory, url_for, redirect
from models.db_pool import get_courses, get_academic_years, db_manager
from utils.auth_helpers import admin_required
from utils.pdf_utils import ReportGenerator

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@admin_required
def index():
    """Main page for reports section."""
    return render_template('reports/index.html')

@reports_bp.route('/admission-register', methods=['GET', 'POST'])
@admin_required
def admission_register():
    """Handles the generation of the Admission Register report."""
    if request.method == 'POST':
        try:
            course_id = request.form.get('course_id')
            academic_year_id = request.form.get('academic_year_id')
            
            # Convert empty strings to None
            course_id = int(course_id) if course_id else None
            academic_year_id = int(academic_year_id) if academic_year_id else None

            generator = ReportGenerator()
            report_path = generator.generate_admission_register_pdf(
                course_id=course_id,
                academic_year_id=academic_year_id
            )
            
            directory = os.path.dirname(report_path)
            filename = os.path.basename(report_path)
            
            flash('Admission Register generated successfully. Your download will begin shortly.', 'success')
            return send_from_directory(directory, filename, as_attachment=True)

        except Exception as e:
            flash(f"Failed to generate report: {e}", 'danger')
            current_app.logger.error(f"Report Generation failed: {e}", exc_info=True)
            return redirect(url_for('reports.admission_register'))
    
    # For GET request
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('reports/admission_register.html', courses=courses, academic_years=academic_years)

@reports_bp.route('/fee-collection-report', methods=['GET', 'POST'])
@admin_required
def fee_collection_report():
    if request.method == 'POST':
        try:            
            course_id = request.form.get('course_id')
            academic_year_id = request.form.get('academic_year_id')

            course_id = int(course_id) if course_id else None
            academic_year_id = int(academic_year_id) if academic_year_id else None
            
            generator = ReportGenerator()
            report_path = generator.generate_fee_collection_report_pdf(
                # start_date=start_date, end_date=end_date, # Removed date filters
                course_id=course_id, academic_year_id=academic_year_id
            )
            directory = os.path.dirname(report_path)
            filename = os.path.basename(report_path)
            flash('Fee Collection Report generated successfully. Download will begin shortly.', 'success')
            return send_from_directory(directory, filename, as_attachment=True)
        except Exception as e:
            flash(f"Failed to generate Fee Collection Report: {e}", 'danger')
            current_app.logger.error(f"Fee Collection Report Generation failed: {e}", exc_info=True)
            return redirect(url_for('reports.fee_collection_report'))

    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('reports/fee_collection_report.html', courses=courses, academic_years=academic_years)

@reports_bp.route('/tc-issued-report', methods=['GET', 'POST'])
@admin_required
def tc_issued_report():
    if request.method == 'POST':
        try:            
            course_id = request.form.get('course_id')
            academic_year_id = request.form.get('academic_year_id')

            course_id = int(course_id) if course_id else None
            academic_year_id = int(academic_year_id) if academic_year_id else None
            
            generator = ReportGenerator()
            report_path = generator.generate_tc_issued_report_pdf(
                course_id=course_id, 
                academic_year_id=academic_year_id
            )
            directory = os.path.dirname(report_path)
            filename = os.path.basename(report_path)
            flash('TC Issued Report generated successfully. Download will begin shortly.', 'success')
            return send_from_directory(directory, filename, as_attachment=True)
        except Exception as e:
            flash(f"Failed to generate TC Issued Report: {e}", 'danger')
            current_app.logger.error(f"TC Issued Report Generation failed: {e}", exc_info=True)
            return redirect(url_for('reports.tc_issued_report'))
            
    courses = get_courses()
    academic_years = get_academic_years()
    return render_template('reports/tc_issued_report.html', courses=courses, academic_years=academic_years)