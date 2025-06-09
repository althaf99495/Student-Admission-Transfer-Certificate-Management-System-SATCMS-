from models.db_pool import db_manager # Assuming db_manager is initialized and available
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_admission_number(course_id: int, academic_year_id: int):
    """
    Generate admission number in the format: YEARCOURSE_CODESERIAL
    Example: 2024CSE001, 2024MBA015
    (Where YEAR is the starting year of the academic session,
     COURSE_CODE is the code of the course,
     SERIAL is a 3-digit incrementing number for that course and academic year)

    Args:
        course_id: ID of the course.
        academic_year_id: ID of the academic year.

    Returns:
        tuple: (admission_number, serial_no)
    
    Raises:
        ValueError: If course or academic year not found.
    """
    course = db_manager.execute_query(
        "SELECT course_code FROM courses WHERE id = ?",
        (course_id,),
        fetch_one=True
    )
    if not course:
        logger.error(f"Course with ID {course_id} not found for admission number generation.")
        raise ValueError(f"Course details not found for ID {course_id}.")

    academic_year_details = db_manager.execute_query(
        "SELECT academic_year FROM academic_years WHERE id = ?",
        (academic_year_id,),
        fetch_one=True
    )
    if not academic_year_details:
        logger.error(f"Academic year with ID {academic_year_id} not found for admission number generation.")
        raise ValueError(f"Academic year details not found for ID {academic_year_id}.")

    # Extract starting year from academic year (e.g., "2024-2025" -> "2024")
    try:
        starting_year_str = academic_year_details['academic_year'].split('-')[0]
        # Ensure starting_year_str is a valid year string if needed, though schema constraints should handle it
    except (AttributeError, IndexError, TypeError):
        logger.error(f"Could not parse starting year from academic_year string: {academic_year_details['academic_year']}")
        raise ValueError(f"Invalid academic year format: {academic_year_details['academic_year']}")


    # Get next serial number for this course and academic year
    # The serial_no in students table should be the source of truth for the next serial.
    max_serial_row = db_manager.execute_query(
        """SELECT MAX(serial_no) as max_serial
           FROM students
           WHERE course_id = ? AND academic_year_id = ?""",
        (course_id, academic_year_id),
        fetch_one=True
    )
    
    next_serial = (max_serial_row['max_serial'] if max_serial_row and max_serial_row['max_serial'] is not None else 0) + 1
    
    if next_serial > 999:
        logger.warning(f"Serial number for course {course_id} in academic year {academic_year_id} exceeds 999.")
        # Potentially raise an error or handle as per application policy
        # raise ValueError("Maximum serial number (999) exceeded for this course and academic year.")

    formatted_serial = f"{next_serial:03d}"
    admission_number = f"{starting_year_str}{course['course_code'].upper()}{formatted_serial}"
    
    logger.info(f"Generated admission number: {admission_number} with serial: {next_serial} for course: {course_id}, ay: {academic_year_id}")
    return admission_number, next_serial

def validate_admission_number(admission_number: str) -> bool:
    """
    Validate admission number format: YEARCOURSE_CODESERIAL (e.g., 2024CSE001).
    Assumes YEAR is 4 digits, SERIAL is 3 digits. Course code length is variable.

    Args:
        admission_number: Admission number to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    if not admission_number or len(admission_number) < 7: # Min: YYYY + CC + S (4+2+1 if course code is min 2, serial 1)
                                                        # Based on current generation: 4 (year) + 1 (min course code) + 3 (serial) = 8
        return False

    try:
        year_part = admission_number[:4]
        serial_part = admission_number[-3:]
        course_code_part = admission_number[4:-3]

        if not (year_part.isdigit() and serial_part.isdigit()):
            return False

        year_int = int(year_part)
        if not (2000 <= year_int <= 2100): # As per schema
            return False

        serial_int = int(serial_part)
        if not (1 <= serial_int <= 999): # Serial is 001 to 999
            return False
        
        if not course_code_part: # Course code cannot be empty
            return False

    except (ValueError, IndexError):
        return False # Failed to parse parts

    # Validate course code (should exist in database and match extracted part)
    # This check assumes course codes are stored and compared in uppercase.
    course_exists = db_manager.execute_query(
        "SELECT id FROM courses WHERE course_code = ?",
        (course_code_part.upper(),), # Ensure comparison is case-insensitive if codes stored differently
        fetch_one=True
    )
    return course_exists is not None

def get_admission_number_components(admission_number: str) -> Optional[dict]:
    """
    Extract components from an admission number (YEARCOURSE_CODESERIAL).

    Args:
        admission_number: Admission number to parse.

    Returns:
        dict: Components {'course_code', 'year', 'serial', 'formatted_serial'} or None if invalid.
    """
    if not validate_admission_number(admission_number):
        return None
    
    try:
        year_part = admission_number[:4]
        serial_part = admission_number[-3:]
        course_code_part = admission_number[4:-3]

        return {
            'course_code': course_code_part,
            'year': int(year_part),
            'serial': int(serial_part),
            'formatted_serial': serial_part # Keep the 3-digit formatted string
        }
    except (ValueError, IndexError): # Should be caught by validate_admission_number
        logger.error(f"Error parsing components from a supposedly valid admission number: {admission_number}")
        return None

def check_admission_number_exists(admission_number: str, exclude_student_id: Optional[int] = None) -> bool:
    """
    Check if an admission number already exists in the students table.

    Args:
        admission_number: The admission number to check.
        exclude_student_id: Optional student ID to exclude from the check (for edit operations).

    Returns:
        bool: True if the admission number exists (excluding the specified student), False otherwise.
    """
    query = "SELECT 1 FROM students WHERE admission_no = ?"
    params = [admission_number]
    
    if exclude_student_id is not None:
        query += " AND id != ?"
        params.append(exclude_student_id)
    
    result = db_manager.execute_query(query, tuple(params), fetch_one=True)
    return result is not None

def get_next_available_admission_number_preview(course_id: int, academic_year_id: int) -> str:
    """
    Get the next available admission number for preview purposes without actually reserving it.

    Args:
        course_id: ID of the course.
        academic_year_id: ID of the academic year.

    Returns:
        str: Next available admission number string, or an error message if generation fails.
    """
    try:
        admission_number, _ = generate_admission_number(course_id, academic_year_id)
        return admission_number
    except ValueError as e:
        logger.warning(f"Could not generate preview admission number for course {course_id}, AY {academic_year_id}: {e}")
        return f"Error: {str(e)}"

def regenerate_admission_numbers_for_academic_year(academic_year_id: int) -> int:
    """
    Regenerate all admission numbers for a specific academic year, grouped by course.
    This function will update existing student admission numbers and serial numbers.
    USE WITH EXTREME CAUTION - THIS MODIFIES EXISTING DATA.

    Args:
        academic_year_id: ID of the academic year to process.

    Returns:
        int: Number of student records updated.
    """
    logger.warning(f"Starting regeneration of admission numbers for academic year ID: {academic_year_id}. THIS IS A DESTRUCTIVE OPERATION.")
    
    # Get academic year details (specifically the starting year string)
    academic_year_details = db_manager.execute_query(
        "SELECT academic_year FROM academic_years WHERE id = ?",
        (academic_year_id,),
        fetch_one=True
    )
    if not academic_year_details:
        logger.error(f"Cannot regenerate: Academic year with ID {academic_year_id} not found.")
        raise ValueError(f"Academic year details not found for ID {academic_year_id}, regeneration aborted.")

    try:
        starting_year_str = academic_year_details['academic_year'].split('-')[0]
    except (AttributeError, IndexError, TypeError):
        logger.error(f"Could not parse starting year from academic_year string: {academic_year_details['academic_year']}")
        raise ValueError(f"Invalid academic year format: {academic_year_details['academic_year']}")

    # Get all students for the academic year, ordered by course and then by original admission date
    # to preserve original admission order as much as possible for serial numbering.
    students_to_update = db_manager.execute_query(
        """SELECT s.id, s.course_id, c.course_code
           FROM students s
           JOIN courses c ON s.course_id = c.id
           WHERE s.academic_year_id = ?
           ORDER BY s.course_id, s.date_of_admission, s.id""", # s.id as tie-breaker
        (academic_year_id,),
        fetch_all=True
    )

    if not students_to_update:
        logger.info(f"No students found for academic year ID {academic_year_id} to regenerate admission numbers.")
        return 0

    updated_count = 0
    current_course_id = None
    current_serial = 0

    for student in students_to_update:
        if student['course_id'] != current_course_id:
            current_course_id = student['course_id']
            current_serial = 0  # Reset serial for new course

        current_serial += 1
        
        if current_serial > 999:
            logger.error(f"Serial number overflow (>999) for student ID {student['id']}, course ID {current_course_id} during regeneration. Skipping update for this student.")
            # Decide on handling: skip, error out, or alternative numbering.
            continue 

        formatted_serial = f"{current_serial:03d}"
        new_admission_number = f"{starting_year_str}{student['course_code'].upper()}{formatted_serial}"
        
        try:
            # Check for potential conflicts before updating if paranoid, though ordering should prevent it
            # if this is the sole process modifying these numbers.
            db_manager.execute_query(
                "UPDATE students SET admission_no = ?, serial_no = ? WHERE id = ?",
                (new_admission_number, current_serial, student['id']),
                commit=True 
            )
            updated_count += 1
            logger.debug(f"Updated student ID {student['id']} to admission_no: {new_admission_number}, serial_no: {current_serial}")
        except Exception as e: # Catch specific db errors if possible
            logger.error(f"Failed to update admission number for student ID {student['id']} to {new_admission_number} (Serial: {current_serial}): {e}", exc_info=True)
            # Potentially rollback or collect errors for summary

    logger.info(f"Successfully regenerated admission numbers for {updated_count} students in academic year ID {academic_year_id}.")
    return updated_count