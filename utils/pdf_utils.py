# utils/pdf_utils.py

import os
from docx import Document
from docx2pdf import convert
from flask import current_app
import logging
from typing import Optional, Union
from datetime import date, datetime
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.shared import Inches, Pt # Added Pt for font size
from num2words import num2words # For converting numbers to words
import pythoncom # Import for CoInitialize

# Get the logger for the current module
logger = logging.getLogger(__name__)

class TCGenerator:
    """Generates Transfer Certificates (TC) as Word (.docx) and PDF documents."""

    def __init__(self, template_path: Optional[str] = None):
        """
        Initializes the TCGenerator.
        Args:
            template_path (str, optional): Path to the Word TC template.
                                           Defaults to TC_TEMPLATE_PATH from app config.
        """
        self.template_path = template_path or current_app.config.get('TC_TEMPLATE_PATH')
        self.output_path_base = current_app.config.get('TC_OUTPUT_PATH')

        if not self.output_path_base:
            logger.error("TC_OUTPUT_PATH is not configured in the application.")
            raise ValueError("TC output path is not configured.")

        # Ensure output directory exists
        try:
            os.makedirs(self.output_path_base, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create TC output directory {self.output_path_base}: {e}")
            raise

    def _get_safe_filename_part(self, value: str) -> str:
        """Cleans a string for use in filenames by replacing invalid characters."""
        return str(value).replace('/', '_').replace('\\', '_')

    def generate_tc_files(self, student_data: dict, tc_data: dict) -> tuple[str, str]:
        """
        Generates TC files (.docx and .pdf) from data.

        Args:
            student_data (dict): Dictionary containing student information.
            tc_data (dict): Dictionary containing TC specific data.

        Returns:
            tuple[str, str]: A tuple containing the paths to the generated (docx_path, pdf_path).

        Raises:
            FileNotFoundError: If the template path is specified but the file doesn't exist.
            RuntimeError: For other errors during document generation or conversion.
        """
        docx_path = ""
        try:
            # Step 1: Create the Word Document
            if self.template_path and os.path.exists(self.template_path):
                doc = Document(self.template_path)
            elif self.template_path:
                logger.error(f"TC template specified but not found: {self.template_path}")
                raise FileNotFoundError(f"TC template not found at {self.template_path}")
            else:
                logger.info("No TC template path provided. A default TC will be created.")
                doc = self._create_default_tc_template()

            self._replace_placeholders(doc, student_data, tc_data)

            # Generate a unique and predictable filename
            clean_adm_no = self._get_safe_filename_part(student_data.get('admission_no', ''))
            tc_number_safe = self._get_safe_filename_part(tc_data.get('tc_number', ''))
            base_filename = f"TC_{clean_adm_no}_{tc_number_safe}"
            
            docx_path = os.path.join(self.output_path_base, f"{base_filename}.docx")
            pdf_path = os.path.join(self.output_path_base, f"{base_filename}.pdf")

            doc.save(docx_path)
            logger.info(f"TC Word document generated successfully: {docx_path}")

            # Step 2: Convert Word Document to PDF
            try:
                pythoncom.CoInitialize() # Initialize COM
                convert(docx_path, pdf_path)
                logger.info(f"TC PDF generated successfully: {pdf_path}")
            finally:
                pythoncom.CoUninitialize() # Uninitialize COM


            return docx_path, pdf_path

        except Exception as e:
            logger.error(f"Error during TC file generation (from DOCX: {docx_path}): {e}", exc_info=True)
            # Clean up docx if PDF fails and docx exists
            if docx_path and os.path.exists(docx_path):
                try:
                    os.remove(docx_path)
                    logger.info(f"Cleaned up intermediate DOCX file after PDF generation failure: {docx_path}")
                except OSError as rm_e:
                    logger.error(f"Failed to cleanup DOCX file {docx_path}: {rm_e}")
            raise RuntimeError(f"Failed to generate TC files: {e}")

    def _replace_placeholders(self, doc: Document, student_data: dict, tc_data: dict):
        """Replaces placeholder strings in the document with actual data."""
        replacements = self._prepare_replacement_data(student_data, tc_data)

        # Helper to perform replacement in paragraphs (in body, tables, headers, footers)
        def replace_text_in_paragraph(paragraph):
            for placeholder, value in replacements.items():
                if placeholder in paragraph.text:
                    inline = paragraph.runs
                    # Replace text in each run to preserve formatting
                    for i in range(len(inline)):
                        if placeholder in inline[i].text:
                            text = inline[i].text.replace(placeholder, str(value))
                            inline[i].text = text

        # Iterate through all parts of the document
        for paragraph in doc.paragraphs:
            replace_text_in_paragraph(paragraph)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        replace_text_in_paragraph(paragraph)
        for section in doc.sections:
            for header_paragraph in section.header.paragraphs:
                replace_text_in_paragraph(header_paragraph)
            for footer_paragraph in section.footer.paragraphs:
                replace_text_in_paragraph(footer_paragraph)

    def _format_display_date(self, date_value: Union[str, datetime, date, None]) -> str:
        """Formats a date into the app's display format (e.g., DD/MM/YYYY)."""
        if not date_value:
            return 'N/A'
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, current_app.config.get('DATE_FORMAT', '%Y-%m-%d'))
            else:
                date_obj = date_value
            return date_obj.strftime(current_app.config.get('DISPLAY_DATE_FORMAT', '%d/%m/%Y'))
        except (ValueError, TypeError):
            return str(date_value) # Fallback

    def _date_to_words(self, date_value: Union[str, datetime, date, None]) -> str:
        """Converts a date into words (e.g., "Fifteenth August Nineteen Ninety-Nine")."""
        if not date_value:
            return 'N/A'
        
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, current_app.config.get('DATE_FORMAT', '%Y-%m-%d')).date()
            elif isinstance(date_value, datetime):
                date_obj = date_value.date()
            elif isinstance(date_value, date):
                date_obj = date_value
            else:
                return str(date_value) # Fallback

            day_words = num2words(date_obj.day, to='ordinal').title()
            month_words = date_obj.strftime("%B")
            
            # Year to words - simple approach for now
            year = date_obj.year
            if 1900 <= year <= 2099: # Common range for TCs
                year_part1 = num2words(year // 100, to='cardinal').title()
                year_part2_num = year % 100
                if year_part2_num == 0:
                    year_words = f"{year_part1} Hundred"
                else:
                    year_part2 = num2words(year_part2_num, to='cardinal').title()
                    year_words = f"{year_part1} {year_part2}"
            else: # Fallback for years outside typical range
                year_words = num2words(year, to='year').title()

            return f"{day_words} {month_words} {year_words}"
        except Exception as e:
            logger.error(f"Error converting date to words ('{date_value}'): {e}", exc_info=True)
            return str(date_value) # Fallback

    def _prepare_replacement_data(self, student_data: dict, tc_data: dict) -> dict:
        """Prepares a dictionary of placeholder keys and their corresponding values."""
        # Use a helper to safely get data and provide a default
        def get_data(key, default=''):
            return student_data.get(key) or tc_data.get(key) or default

         # --- Pronoun and Salutation Logic ---
        gender = str(get_data('gender', 'other')).lower()
        salutation = "Kum." if gender == 'female' else "Sri."
        possessive_pronoun = "Her" if gender == 'female' else "His"

        # --- Placeholder Value Logic ---
        admission_no = get_data('admission_no', '0000')
        # [TC_SNO] is the last four digits of the Admission Number 
        tc_sno = admission_no[-4:]

        dob = get_data('dob')
        date_of_leaving = get_data('date_of_leaving') or get_data('issue_date')

        return {
            '[TC_SNO]': tc_sno,
            '[ADM_NO]': admission_no,
            '[STUDENT_NAME]': str(get_data('student_name')).title(),
            '[FATHER_NAME]': str(get_data('father_name')).title(),
            '[NATIONALITY]': str(get_data('nationality', 'Indian')).title(),
            '[RELIGION]': str(get_data('religion')).title(),
            '[CASTE]': str(get_data('caste')).title(),
            '[DOB]': self._format_display_date(dob),
            '[DOB_WORDS]': self._date_to_words(dob), # Populates [DOB_WORDS] placeholder 
            '[COURSE_NAME_FULL]': str(get_data('course_full_name') or get_data('course_name')),
            '[COURSE_NAME]': str(get_data('course_name')),
            '[COURSE_CODE]': str(get_data('course_code')), # For the line with parentheses 
            '[DATE_OF_ADMISSION]': self._format_display_date(get_data('date_of_admission')),
            '[PROMOTION_STATUS]': get_data('promotion_status', 'N/A'), # From manual entry 
            '[DATE_OF_LEAVING]': self._format_display_date(date_of_leaving), # From manual entry 
            '[ACADEMIC_PERIOD]': str(get_data('academic_year')), # For Study Certificate 
            '[CONDUCT]': str(get_data('conduct', 'Good')).title(),
            '[SALUTATION]': salutation, # For "Sri / Kum." 
            '[POSSESSIVE_PRONOUN]': possessive_pronoun # For "His / Her" 
        }

    def _create_default_tc_template(self) -> Document:
        """Creates a basic, default TC template if no external template is provided."""
        doc = Document()
        # Implementation of a default template can be added here if needed
        doc.add_heading(current_app.config.get('COLLEGE_NAME'), 0)
        doc.add_heading('Transfer Certificate', level=1)
        doc.add_paragraph("This is to certify that [STUDENT_NAME] (Adm. No: [ADMISSION_NO]) was a student of this college.")
        # ... add more placeholders
        return doc


def generate_tc_number_for_student(student_id: int) -> str:
    """
    Generates a unique TC number for the given student.
    Format: TC/YYYY/XXXX (XXXX is a 4-digit sequential number for that year).
    """
    from models.db_pool import db_manager
    year_str = str(datetime.now().year)

    last_tc_for_year = db_manager.execute_query(
        "SELECT tc_number FROM transfer_certificates WHERE tc_number LIKE ? ORDER BY tc_number DESC LIMIT 1",
        (f"TC/{year_str}/%",),
        fetch_one=True
    )

    next_serial = 1
    if last_tc_for_year and last_tc_for_year['tc_number']:
        try:
            last_serial_str = last_tc_for_year['tc_number'].split('/')[-1]
            next_serial = int(last_serial_str) + 1
        except (IndexError, ValueError):
            logger.warning(f"Could not parse serial from TC number {last_tc_for_year['tc_number']}. Defaulting to 1.")

    return f"TC/{year_str}/{next_serial:04d}"

class ReportGenerator:
    """Generates various reports (e.g., Admission Register) as Word documents."""

    def __init__(self):
        self.output_path_base = current_app.config.get('TC_OUTPUT_PATH') # Reports can go to same generated files area
        if not self.output_path_base:
            logger.error("TC_OUTPUT_PATH (used for reports) is not configured.")
            raise ValueError("Report output path is not configured.")
        os.makedirs(self.output_path_base, exist_ok=True)

    def _format_report_date(self, date_value):
        """Helper to format dates for reports."""
        if not date_value: return ''
        try:
            if isinstance(date_value, str):
                date_obj = datetime.strptime(date_value, current_app.config.get('DATE_FORMAT', '%Y-%m-%d')).date()
            elif isinstance(date_value, datetime):
                date_obj = date_value.date()
            elif isinstance(date_value, date):
                date_obj = date_value
            else: return str(date_value)
            return date_obj.strftime(current_app.config.get('DISPLAY_DATE_FORMAT', '%d/%m/%Y'))
        except ValueError:
            return str(date_value)


    def generate_admission_register_pdf(self, course_id: Optional[int] = None, academic_year_id: Optional[int] = None) -> str:
        """
        Generates an Admission Register report as a PDF document.
        
        Args:
            course_id (Optional[int]): Filter by course ID.
            academic_year_id (Optional[int]): Filter by academic year ID.
        
        Returns:
            str: Path to the generated .pdf report.
        """
        from models.db_pool import get_all_students 

        # Fetch student data
        students = get_all_students(course_id=course_id, academic_year_id=academic_year_id, order_by="s.admission_no ASC")

        # --- Document and Page Setup ---
        doc = Document()
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        # Custom page size: 14.67 inches width, 11.33 inches height
        section.page_width = Inches(14.67)
        section.page_height = Inches(11.33)
        
        # Set margins (e.g., 0.5 inches all around)
        margin_size = Inches(0.5)
        section.top_margin = margin_size
        section.bottom_margin = margin_size
        section.left_margin = margin_size
        section.right_margin = margin_size
        # --- End Page Setup ---

        # --- Main Report Headings ---
        college_name_config = current_app.config.get('COLLEGE_NAME', 'YOUR COLLEGE NAME') # Get from app config
        
        college_name_p = doc.add_paragraph()
        college_name_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        college_name_run = college_name_p.add_run(college_name_config.upper())
        college_name_run.font.size = Pt(16) # Example: Make college name larger
        college_name_run.bold = True

        report_title_p = doc.add_paragraph()
        report_title_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        report_title_run = report_title_p.add_run('ADMISSION REGISTER')
        report_title_run.font.size = Pt(14) # Example: Report title size
        report_title_run.bold = True
        # --- End Main Report Headings ---

        # --- Add filter information to header ---
        filter_texts = []
        if course_id:
            # Fetch course name for display if possible
            from models.db_pool import db_manager
            course_info = db_manager.execute_query(
                "SELECT course_name, course_code, type FROM courses WHERE id = ?", 
                (course_id,), 
                fetch_one=True
            )
            if course_info:
                filter_texts.append(f"Course: {course_info['course_name']} ({course_info['course_code']}) - Type: {course_info['type']}")
            else:
                filter_texts.append(f"Course ID: {course_id} (Details not found)")

        if academic_year_id:
            from models.db_pool import db_manager
            ay_info = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (academic_year_id,), fetch_one=True)
            filter_texts.append(f"Academic Year: {ay_info['academic_year']}" if ay_info else f"Academic Year ID: {academic_year_id}")

        if filter_texts:
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run("Filters Applied: " + "; ".join(filter_texts)).italic = True
        doc.add_paragraph() # Spacer
        # --- End filter information ---

        if not students:
            doc.add_paragraph("No students found matching the criteria.")
        else:
            table = doc.add_table(rows=1, cols=9) # Adjusted column count
            table.style = 'Table Grid' # Apply a table style
            
            # Header row
            hdr_cells = table.rows[0].cells
            headers = ['S.No', 'Adm. No', 'Student Name', 'Father Name', 'Course', 'Acad. Year', 'DOB', 'Date of Adm.', 'Phone']
            for i, header_text in enumerate(headers):
                hdr_cells[i].text = header_text
                hdr_cells[i].paragraphs[0].runs[0].font.bold = True

            # Data rows
            for idx, student in enumerate(students, 1):
                row_cells = table.add_row().cells
                row_cells[0].text = str(idx)
                row_cells[1].text = student['admission_no'] or ''
                row_cells[2].text = student['student_name'] or ''
                row_cells[3].text = student['father_name'] or ''
                row_cells[4].text = f"{student['course_name'] or ''} ({student['course_code'] or ''})"
                row_cells[5].text = student['academic_year'] or ''
                row_cells[6].text = self._format_report_date(student['dob'])
                row_cells[7].text = self._format_report_date(student['date_of_admission'])
                row_cells[8].text = student['phone_no'] or ''
        
        # Save document
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"admission_register_{timestamp}"
        docx_filepath = os.path.join(self.output_path_base, f"{base_filename}.docx")
        pdf_filepath = os.path.join(self.output_path_base, f"{base_filename}.pdf")

        try:
            doc.save(docx_filepath)
            logger.info(f"Admission Register (DOCX) generated: {docx_filepath}")

            # Convert to PDF
            try:
                pythoncom.CoInitialize() # Initialize COM
                convert(docx_filepath, pdf_filepath)
                logger.info(f"Admission Register (PDF) generated: {pdf_filepath}")
            finally:
                pythoncom.CoUninitialize() # Uninitialize COM
            
            # Clean up the DOCX file after successful PDF conversion
            if os.path.exists(docx_filepath):
                os.remove(docx_filepath)
                logger.info(f"Cleaned up intermediate DOCX file: {docx_filepath}")
            
            return pdf_filepath
        except Exception as e:
            logger.error(f"Error during Admission Register PDF generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate Admission Register PDF: {e}")

    def generate_fee_collection_report_pdf(self, start_date: Optional[str] = None, end_date: Optional[str] = None,
                                           course_id: Optional[int] = None, academic_year_id: Optional[int] = None) -> str:
        """Generates a Fee Collection report as a PDF document."""
        from models.db_pool import get_fee_payments_for_report, db_manager

        payments = get_fee_payments_for_report(start_date, end_date, course_id, academic_year_id)

        doc = Document()
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11) # Standard Letter Landscape
        section.page_height = Inches(8.5)
        margin_size = Inches(0.75)
        section.top_margin = margin_size
        section.bottom_margin = margin_size
        section.left_margin = margin_size
        section.right_margin = margin_size

        college_name_config = current_app.config.get('COLLEGE_NAME', 'YOUR COLLEGE NAME')
        doc.add_paragraph().add_run(college_name_config.upper()).bold = True
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_heading('Fee Collection Report', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER

        filter_texts = []
        if start_date: filter_texts.append(f"From: {self._format_report_date(start_date)}")
        if end_date: filter_texts.append(f"To: {self._format_report_date(end_date)}")
        if course_id:
            course_info = db_manager.execute_query("SELECT course_name FROM courses WHERE id = ?", (course_id,), fetch_one=True)
            if course_info: filter_texts.append(f"Course: {course_info['course_name']}")
        if academic_year_id:
            ay_info = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (academic_year_id,), fetch_one=True)
            if ay_info: filter_texts.append(f"Academic Year: {ay_info['academic_year']}")
        
        if filter_texts:
            doc.add_paragraph(f"Filters: {'; '.join(filter_texts)}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        if not payments:
            doc.add_paragraph("No fee payments found matching the criteria.")
        else:
            table = doc.add_table(rows=1, cols=8)
            table.style = 'Table Grid'
            headers = ['S.No', 'Payment Date', 'Adm. No', 'Student Name', 'Course', 'Amount Paid', 'Transaction ID', 'Method']
            for i, header_text in enumerate(headers):
                table.cell(0, i).text = header_text
                table.cell(0,i).paragraphs[0].runs[0].font.bold = True

            total_collected = 0
            for idx, p_data in enumerate(payments, 1):
                row_cells = table.add_row().cells
                row_cells[0].text = str(idx)
                row_cells[1].text = self._format_report_date(p_data['payment_date'])
                row_cells[2].text = p_data['admission_no'] or ''
                row_cells[3].text = p_data['student_name'] or ''
                row_cells[4].text = p_data['course_name'] or ''
                row_cells[5].text = f"{p_data['amount_paid']:.2f}"
                row_cells[6].text = p_data['transaction_id'] or 'N/A'
                row_cells[7].text = p_data['payment_method'] or ''
                total_collected += p_data['amount_paid']
            
            # Add total row
            total_row_cells = table.add_row().cells
            total_row_cells[4].text = "Total Collected:"
            total_row_cells[4].paragraphs[0].runs[0].font.bold = True
            total_row_cells[5].text = f"{total_collected:.2f}"
            total_row_cells[5].paragraphs[0].runs[0].font.bold = True

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"fee_collection_report_{timestamp}"
        docx_filepath = os.path.join(self.output_path_base, f"{base_filename}.docx")
        pdf_filepath = os.path.join(self.output_path_base, f"{base_filename}.pdf")

        try:
            doc.save(docx_filepath)
            pythoncom.CoInitialize()
            convert(docx_filepath, pdf_filepath)
            pythoncom.CoUninitialize()
            if os.path.exists(docx_filepath): os.remove(docx_filepath)
            return pdf_filepath
        except Exception as e:
            logger.error(f"Error during Fee Collection Report PDF generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate Fee Collection Report PDF: {e}")

    def generate_tc_issued_report_pdf(self, course_id: Optional[int] = None, 
                                      academic_year_id: Optional[int] = None) -> str:
        """Generates a TC Issued report as a PDF document."""
        from models.db_pool import get_tc_issued_for_report, db_manager # Ensure db_manager is imported if not already

        tcs_issued = get_tc_issued_for_report(course_id=course_id, academic_year_id=academic_year_id)

        doc = Document()
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = Inches(11)
        section.page_height = Inches(8.5)
        margin_size = Inches(0.75)
        section.top_margin = margin_size
        section.bottom_margin = margin_size
        section.left_margin = margin_size
        section.right_margin = margin_size


        college_name_config = current_app.config.get('COLLEGE_NAME', 'YOUR COLLEGE NAME')
        doc.add_paragraph().add_run(college_name_config.upper()).bold = True
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_heading('TC Issued Report', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER

        filter_texts = []
        if course_id:
            course_info = db_manager.execute_query("SELECT course_name FROM courses WHERE id = ?", (course_id,), fetch_one=True)
            if course_info: filter_texts.append(f"Course: {course_info['course_name']}")
        if academic_year_id:
            ay_info = db_manager.execute_query("SELECT academic_year FROM academic_years WHERE id = ?", (academic_year_id,), fetch_one=True)
            if ay_info: filter_texts.append(f"Academic Year: {ay_info['academic_year']}")

        if filter_texts: doc.add_paragraph(f"Filters: {'; '.join(filter_texts)}").alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph()

        if not tcs_issued:
            doc.add_paragraph("No TCs found matching the criteria.")
        else:
            table = doc.add_table(rows=1, cols=7)
            table.style = 'Table Grid'
            headers = ['S.No', 'TC Number', 'Issue Date', 'Student Name', 'Adm. No', 'Course', 'Date of Leaving']
            for i, header_text in enumerate(headers): 
                table.cell(0, i).text = header_text
                table.cell(0,i).paragraphs[0].runs[0].font.bold = True # Bold headers

            for idx, tc_data in enumerate(tcs_issued, 1):
                row_cells = table.add_row().cells
                row_cells[0].text = str(idx); row_cells[1].text = tc_data['tc_number']
                row_cells[2].text = self._format_report_date(tc_data['issue_date']); row_cells[3].text = tc_data['student_name']
                row_cells[4].text = tc_data['admission_no']; row_cells[5].text = tc_data['course_name']
                row_cells[6].text = self._format_report_date(tc_data['date_of_leaving'])

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"tc_issued_report_{timestamp}"
        docx_filepath = os.path.join(self.output_path_base, f"{base_filename}.docx")
        pdf_filepath = os.path.join(self.output_path_base, f"{base_filename}.pdf")
        try:
            doc.save(docx_filepath)
            pythoncom.CoInitialize()
            convert(docx_filepath, pdf_filepath)
            pythoncom.CoUninitialize()
            if os.path.exists(docx_filepath): os.remove(docx_filepath)
            return pdf_filepath
        except Exception as e:
            logger.error(f"Error during TC Issued Report PDF generation: {e}", exc_info=True)
            raise RuntimeError(f"Failed to generate TC Issued Report PDF: {e}")