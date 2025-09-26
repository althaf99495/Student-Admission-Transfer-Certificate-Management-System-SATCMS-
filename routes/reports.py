import os
from flask import Blueprint, render_template, request, flash, current_app, send_from_directory, url_for, redirect, Response, jsonify
from models.db_pool import get_courses, get_academic_years, db_manager, get_students_for_admission_register
from utils.auth_helpers import admin_required
from utils.pdf_utils import ReportGenerator
from utils.csv_utils import generate_csv_from_data
from datetime import datetime

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
            report_format = request.form.get('format', 'pdf')

            # Convert empty strings to None
            course_id = int(course_id) if course_id else None
            academic_year_id = int(academic_year_id) if academic_year_id else None

            if report_format == 'csv':
                # Redirect to the CSV download route, preserving filters
                return redirect(url_for('reports.download_admission_register_csv', 
                                        course_id=course_id, 
                                        academic_year_id=academic_year_id))

            # PDF generation logic remains the same
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

@reports_bp.route('/admission-register/download-csv')
@admin_required
def download_admission_register_csv():
    """Generates and serves the Admission Register as a CSV file."""
    try:
        # Use request.args.get to handle None values gracefully
        course_id = request.args.get('course_id', default=None, type=int)
        academic_year_id = request.args.get('academic_year_id', default=None, type=int)

        students = get_students_for_admission_register(course_id=course_id, academic_year_id=academic_year_id)

        if not students:
            flash('No students found for the selected criteria to generate CSV.', 'warning')
            return redirect(url_for('reports.admission_register'))

        # Convert Row objects to dictionaries for easier processing
        student_dicts = [dict(student) for student in students]

        headers = [
            'S.No', 'Adm. No', 'Student Details', 'Social Category', 
            'Education/Dates', 'TC/Adm Date', 'Remarks'
        ]
        
        # Prepare data for CSV, matching the structure of the PDF
        csv_data = []
        for idx, student in enumerate(student_dicts, 1):
            # Combine address fields
            address_parts = [student.get(key) for key in ['address1', 'address2', 'address3', 'town'] if student.get(key)]
            address_str = ', '.join(filter(None, address_parts))

            csv_data.append({
                'S.No': idx,
                'Adm. No': student.get('admission_no', 'N/A'),
                'Student Details': f"Name: {student.get('student_name', 'N/A')}, Father: {student.get('father_name', 'N/A')}, Addr: {address_str}, Phone: {student.get('phone_no', 'N/A')}, Aadhar: {student.get('aadhar_no', 'N/A')}",
                'Social Category': f"Caste: {student.get('caste', 'N/A')}, Sub-Caste: {student.get('sub_caste', 'N/A')}, Religion: {student.get('religion', 'N/A')}",
                'Education/Dates': f"DOB: {student.get('dob', 'N/A')}, Prev. College: {student.get('previous_college', 'N/A')}, Prev. TC: {student.get('old_tc_no_date', 'N/A')}",
                'TC/Adm Date': f"Date of Adm: {student.get('date_of_admission', 'N/A')}",
                'Remarks': student.get('remarks', '')
            })

        csv_content = generate_csv_from_data(csv_data, headers)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"admission_register_{timestamp}.csv"

        return Response(
            csv_content,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        flash(f"Failed to download CSV report: {e}", 'danger')
        current_app.logger.error(f"CSV Report Generation failed: {e}", exc_info=True)
        return redirect(url_for('reports.admission_register'))

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
            report_path = generator.generate_fee_summary_report_pdf( # Changed to call the new summary report
                course_id=course_id, academic_year_id=academic_year_id
            )
            # After generating the report
            filename = os.path.basename(report_path)
            return redirect(url_for('reports.fee_collection_report_file', filename=filename))
        except Exception as e:
            flash(f"Failed to generate Fee Collection Report: {e}", 'danger')
            current_app.logger.error(f"Fee Collection Report Generation failed: {e}", exc_info=True)
            return redirect(url_for('reports.fee_collection_report'))

    courses = get_courses()
    academic_years = get_academic_years()
    report_filename = request.args.get('report')
    return render_template(
        'reports/fee_collection_report.html',
        courses=courses,
        academic_years=academic_years,
        report_filename=report_filename
    )

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

@reports_bp.route('/fee-collection-report-file/<filename>')
@admin_required
def fee_collection_report_file(filename):
    generator = ReportGenerator()
    directory = generator.output_path_base
    return send_from_directory(directory, filename, as_attachment=True)

@reports_bp.route('/admission-register-data', methods=['POST'])
@admin_required
def admission_register_data():
    """Handles the submission of admission register data from the form."""
    try:
        data = request.get_json()
        current_app.logger.info(f"Received admission register data: {data}")  # Log the received data

        # Extract and log each field from the received data
        admission_no = data.get('admission_no')
        student_name = data.get('student_name')
        total_fee = data.get('total_fee')
        total_paid = data.get('total_paid')
        balance_due = data.get('balance_due')
        payment_date = data.get('payment_date')
        transaction_id = data.get('transaction_id')
        payment_method = data.get('payment_method')
        amount_paid = data.get('amount_paid')

        current_app.logger.info(f"Parsed data - Admission No: {admission_no}, Student Name: {student_name}, Total Fee: {total_fee}, Total Paid: {total_paid}, Balance Due: {balance_due}, Payment Date: {payment_date}, Transaction ID: {transaction_id}, Payment Method: {payment_method}, Amount Paid: {amount_paid}")

        # Here you would typically process the data, e.g., save it to the database
        # For demonstration, we're just logging it

        return {"status": "success", "message": "Admission register data processed successfully."}, 200
    except Exception as e:
        current_app.logger.error(f"Error processing admission register data: {e}", exc_info=True)
        return {"status": "error", "message": "Failed to process admission register data."}, 500

@reports_bp.route('/api/student-distribution/<int:academic_year_id>')
@admin_required
def get_student_distribution_data(academic_year_id):
    """API endpoint to get student distribution data for a specific academic year."""
    try:
        if academic_year_id == 0: # Use 0 to signify all years
            query = """
                SELECT c.course_name, COUNT(s.id) as student_count
                FROM courses c
                LEFT JOIN students s ON c.id = s.course_id
                GROUP BY c.course_name
                ORDER BY student_count DESC
            """
            params = ()
        else:
            query = """
                SELECT c.course_name, COUNT(s.id) as student_count
                FROM courses c
                LEFT JOIN students s ON c.id = s.course_id AND s.academic_year_id = ?
                GROUP BY c.course_name
                ORDER BY student_count DESC
            """
            params = (academic_year_id,)

        dist_data = db_manager.execute_query(query, params, fetch_all=True)
        
        chart_data = {
            'labels': [row['course_name'] for row in dist_data],
            'data': [row['student_count'] for row in dist_data]
        }
        return jsonify(chart_data)
    except Exception as e:
        current_app.logger.error(f"API Error for student distribution: {e}", exc_info=True)
        return jsonify({"error": "Could not retrieve chart data"}), 500
