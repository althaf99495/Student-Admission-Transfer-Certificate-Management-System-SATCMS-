from models.db_pool import db_manager # Assuming db_manager is initialized and available
from datetime import datetime
import logging
from typing import Optional

logger = logging.getLogger(__name__)

def generate_admission_number(course_id: int, academic_year_id: int):
    """
    Generate an *automatic* admission number. Total length is 9 characters.
    - Standard (2-char course code, 3-digit serial): YYYYCCSSS (e.g., 2024CS001)
    - Special  (3-char course code, 2-digit serial): YYYYCCCSS (e.g., 2024CSE01)
    (Where YEAR is the starting year of the academic session,
     COURSE_CODE is the 2 or 3 character code of the course,
     SERIAL is an incrementing number (2 or 3 digits) for that course and academic year)

    Args:
        course_id: ID of the course.
        academic_year_id: ID of the academic year.

    Returns:
        tuple: (admission_number, serial_no)

    Raises:
        ValueError: If course or academic year not found.
    """
    course = db_manager.execute_query(
        "SELECT course_code, type, is_special_format FROM courses WHERE id = ?", # Fetch is_special_format
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
           WHERE course_id = ? AND academic_year_id = ? AND is_manual_admission_no = 0""", # Only consider auto-generated serials for next auto serial
        (course_id, academic_year_id),
        fetch_one=True
    )
    
    next_serial = (max_serial_row['max_serial'] if max_serial_row and max_serial_row['max_serial'] is not None else 0) + 1

    course_code_str = course['course_code'].upper()
    is_special = course['is_special_format'] == 1

    if is_special:
        # 3-char course code, 2-digit serial (e.g., YYYYCCCSS)
        if len(course_code_str) != 3:
            logger.error(f"Configuration Error: Special format course ID {course_id} has code '{course_code_str}' (length {len(course_code_str)}), expected 3 chars.")
            raise ValueError(f"Configuration error for special course {course_code_str}. Expected 3-character code.")
        if next_serial > 99:
            logger.warning(f"Serial number for special course {course_id} (code: {course_code_str}) in AY {academic_year_id} exceeds 99 (is {next_serial}).")
            # Consider raising ValueError("Maximum serial number (99) exceeded for this special course and academic year.")
        formatted_serial = f"{next_serial:02d}"
    else:
        # 2-char course code, 3-digit serial (e.g., YYYYCCSSS)
        if len(course_code_str) != 2:
            logger.error(f"Configuration Error: Standard format course ID {course_id} has code '{course_code_str}' (length {len(course_code_str)}), expected 2 chars.")
            raise ValueError(f"Configuration error for standard course {course_code_str}. Expected 2-character code.")
        if next_serial > 999:
            logger.warning(f"Serial number for standard course {course_id} (code: {course_code_str}) in AY {academic_year_id} exceeds 999 (is {next_serial}).")
            # Consider raising ValueError("Maximum serial number (999) exceeded for this standard course and academic year.")
        formatted_serial = f"{next_serial:03d}"

    admission_number = f"{starting_year_str}{course_code_str}{formatted_serial}"
    
    logger.info(f"Generated admission number: {admission_number} with serial: {next_serial} for course: {course_id} (special: {is_special}), ay: {academic_year_id}")
    return admission_number, next_serial

def validate_admission_number(admission_number: str) -> bool:
    """
    Validate general admission number format (9 characters).
    - YYYYCCSSS (Standard Course: 2-char code, 3-digit serial)
    - YYYYCCCSS (Special Course: 3-char code, 2-digit serial)
    This function checks if the format is valid against existing course configurations.
    It does not distinguish between auto-generated or manually entered serials here,
    only that the structure and serial ranges are plausible.

    Args:
        admission_number: Admission number to validate.

    Returns:
        bool: True if valid, False otherwise.
    """
    if not admission_number or len(admission_number) != 9:
        return False

    try:
        year_part_str = admission_number[:4]
        if not year_part_str.isdigit():
            return False
        year_int = int(year_part_str)
        if not (2000 <= year_int <= 2100): # As per schema
            return False

        # Try parsing as 3-char course code + 2-char serial (YYYYCCCSS)
        course_code_part_3char = admission_number[4:7]
        serial_part_2digit = admission_number[7:9]

        if course_code_part_3char.isalnum() and serial_part_2digit.isdigit(): # Course code can be alphanumeric
            course_info = db_manager.execute_query(
                "SELECT id, is_special_format FROM courses WHERE course_code = ? AND LENGTH(course_code) = 3",
                (course_code_part_3char.upper(),),
                fetch_one=True
            )
            if course_info and course_info['is_special_format'] == 1:
                serial_int = int(serial_part_2digit)
                # For validation, manual serials can be 0-99, auto 1-99. So 0-99 is the valid range for the number part.
                if 0 <= serial_int <= 99:
                    return True

        # Try parsing as 2-char course code + 3-char serial (YYYYCCSSS)
        course_code_part_2char = admission_number[4:6]
        serial_part_3digit = admission_number[6:9]

        if course_code_part_2char.isalnum() and serial_part_3digit.isdigit(): # Course code can be alphanumeric
            course_info = db_manager.execute_query(
                "SELECT id, is_special_format FROM courses WHERE course_code = ? AND LENGTH(course_code) = 2",
                (course_code_part_2char.upper(),),
                fetch_one=True
            )
            if course_info and course_info['is_special_format'] == 0:
                serial_int = int(serial_part_3digit)
                # For validation, manual serials can be 0-999, auto 1-999. So 0-999 is the valid range.
                if 0 <= serial_int <= 999:
                    return True
        
        return False # Did not match a valid known course structure

    except (ValueError, IndexError, TypeError):
        logger.warning(f"Validation failed for admission number '{admission_number}' due to parsing error.", exc_info=True)
        return False # Failed to parse parts

def get_admission_number_components(admission_number: str) -> Optional[dict]:
    """
    Extract components from a 9-character admission number (YYYYCOURSE_CODESERIAL).
    Determines if it matches a standard (YYYYCCSSS) or special (YYYYCCCSS) course format.

    Args:
        admission_number: Admission number to parse.

    Returns:
        dict: Components like {'year', 'serial', 'formatted_serial', 'is_manual_format', 'course_code', 'is_special_format'} or None.
    """
    if not admission_number or len(admission_number) != 9:
        return None
    
    try:
        year_part_str = admission_number[:4]
        year_int = int(year_part_str)
        if not (2000 <= year_int <= 2100): return None

        # Try 3-char course code (YYYYCCCSS)
        course_code_3char = admission_number[4:7]
        serial_2digit_str = admission_number[7:9]

        if course_code_3char.isalnum() and serial_2digit_str.isdigit():
            # Check against DB to confirm this course_code exists and is special
            course_info = db_manager.execute_query(
                "SELECT id, is_special_format FROM courses WHERE course_code = ? AND LENGTH(course_code) = 3",
                (course_code_3char.upper(),),
                fetch_one=True
            )
            if course_info and course_info['is_special_format'] == 1:
                serial_int = int(serial_2digit_str)
                if 0 <= serial_int <= 99: # Valid serial range for 2-digit serials (manual or auto)
                    return {
                        'course_code': course_code_3char.upper(),
                        'is_special_format': 1,
                        'year': year_int,
                        'serial': serial_int,
                        'formatted_serial': serial_2digit_str
                    }

        # Try 2-char course code (YYYYCCSSS)
        course_code_2char = admission_number[4:6]
        serial_3digit_str = admission_number[6:9]
        
        if course_code_2char.isalnum() and serial_3digit_str.isdigit():
            # Check against DB to confirm this course_code exists and is standard
            course_info = db_manager.execute_query(
                "SELECT id, is_special_format FROM courses WHERE course_code = ? AND LENGTH(course_code) = 2",
                (course_code_2char.upper(),),
                fetch_one=True
            )
            if course_info and course_info['is_special_format'] == 0:
                serial_int = int(serial_3digit_str)
                if 0 <= serial_int <= 999: # Valid serial range for 3-digit serials (manual or auto)
                    return {
                        'course_code': course_code_2char.upper(),
                        'is_special_format': 0,
                        'year': year_int,
                        'serial': serial_int,
                        'formatted_serial': serial_3digit_str
                    }
        
        return None # No valid format matched

    except (ValueError, IndexError, TypeError):
        logger.error(f"Error parsing components from admission number: {admission_number}", exc_info=True)
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

def regenerate_admission_numbers_for_academic_year(academic_year_id: int, course_id: Optional[int] = None) -> int:
    """
    Regenerate all admission numbers for a specific academic year, grouped by course.
    Optionally, can regenerate for a specific course within that academic year.
    This function will update existing student admission numbers and serial numbers.
    **IMPORTANT: This function will only regenerate for students with automatically assigned admission numbers (is_manual_admission_no = 0).**
    **USE WITH EXTREME CAUTION - THIS MODIFIES EXISTING DATA.**

    Args:
        academic_year_id: ID of the academic year to process.
        course_id (Optional[int]): If provided, only regenerate for this course within the academic year.

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

    # Base query to get students
    query_students = """SELECT s.id, s.student_name, s.surname, s.course_id, c.course_code, c.is_special_format
           FROM students s
           JOIN courses c ON s.course_id = c.id
           WHERE s.academic_year_id = ? AND s.is_manual_admission_no = 0""" # Only process non-manual
    params = [academic_year_id]

    if course_id:
        query_students += " AND s.course_id = ?"
        params.append(course_id)
        logger.info(f"Regenerating for specific course ID: {course_id} in academic year ID: {academic_year_id}")
    else:
        logger.info(f"Regenerating for all courses in academic year ID: {academic_year_id}")

    query_students += " ORDER BY s.course_id, s.surname ASC, s.student_name ASC, s.id ASC"
    
    students_to_update = db_manager.execute_query(query_students, tuple(params), fetch_all=True)
    
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

        course_code_str = student['course_code'].upper()
        is_special = student['is_special_format'] == 1
        
        max_serial_for_format = 0
        formatted_serial = ""

        if is_special:
            # 3-char course code, 2-digit serial
            if len(course_code_str) != 3:
                logger.error(f"Regen Error: Special format course ID {student['course_id']} (student ID {student['id']}) has code '{course_code_str}', expected 3 chars. Skipping.")
                continue
            max_serial_for_format = 99
            formatted_serial = f"{current_serial:02d}"
        else:
            # 2-char course code, 3-digit serial
            if len(course_code_str) != 2:
                logger.error(f"Regen Error: Standard format course ID {student['course_id']} (student ID {student['id']}) has code '{course_code_str}', expected 2 chars. Skipping.")
                continue
            max_serial_for_format = 999
            formatted_serial = f"{current_serial:03d}"

        if current_serial > max_serial_for_format:
            logger.error(f"Serial number overflow (>{max_serial_for_format}) for student ID {student['id']}, course ID {current_course_id} (special: {is_special}) during regeneration. Serial was {current_serial}. Skipping update for this student.")
            continue 

        new_admission_number = f"{starting_year_str}{course_code_str}{formatted_serial}"
        
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