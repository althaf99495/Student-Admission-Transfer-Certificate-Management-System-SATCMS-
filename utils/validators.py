import re
from datetime import datetime, date
from typing import Optional, Union, Dict, Any

class ValidationError(Exception):
    """Custom validation error"""
    def __init__(self, message, errors: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.errors = errors or {}

def validate_email(email: Optional[str]) -> bool:
    """Validate email format. Returns True if email is None or valid."""
    if not email:
        return True  # Email is optional
    # Basic regex, for more comprehensive validation consider libraries like 'email-validator'
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def validate_phone(phone: Optional[str]) -> bool:
    """Validate phone number. Returns True if phone is None or valid."""
    if not phone:
        return True  # Phone is optional
    
    # Remove common non-digit characters used in phone numbers
    cleaned = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if remaining characters are digits and length is appropriate
    return cleaned.isdigit() and 7 <= len(cleaned) <= 15

def validate_date_format(date_str: Optional[str], field_name: str = "Date") -> Optional[date]:
    """
    Validate date string format (YYYY-MM-DD) and return date object.
    Returns None if date_str is None or empty.
    
    Args:
        date_str: Date string to validate.
        field_name: Name of the field for error messages.
    
    Returns:
        date: Parsed date object or None.
    
    Raises:
        ValidationError: If date_str is provided but invalid.
    """
    if not date_str:
        return None # Optional date fields
    
    try:
        return datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        raise ValidationError(f"{field_name} must be in YYYY-MM-DD format. Received: '{date_str}'")

def validate_age(age_val: Union[int, str], min_age: int = 0, max_age: int = 150) -> int:
    """
    Validate age.
    
    Args:
        age_val: Age to validate.
        min_age: Minimum allowed age.
        max_age: Maximum allowed age.
    
    Returns:
        int: Validated age.
    
    Raises:
        ValidationError: If age is invalid.
    """
    try:
        age_int = int(age_val)
        if not (min_age <= age_int <= max_age):
            raise ValidationError(f"Age must be between {min_age} and {max_age}. Received: {age_int}")
        return age_int
    except (ValueError, TypeError):
        raise ValidationError(f"Age must be a valid number. Received: '{age_val}'")

def validate_aadhar(aadhar: Optional[str]) -> bool:
    """Validate Aadhar number (12 digits). Returns True if aadhar is None or valid."""
    if not aadhar:
        return True  # Aadhar is optional
    
    cleaned = str(aadhar).replace(' ', '')
    return cleaned.isdigit() and len(cleaned) == 12

def validate_academic_year_format(academic_year: str) -> bool:
    """
    Validate academic year format (YYYY-YYYY) and logical consistency.
    
    Args:
        academic_year: Academic year string (e.g., "2023-2024").
    
    Returns:
        bool: True if valid, False otherwise.
    """
    if not academic_year:
        return False
    
    pattern = r'^\d{4}-\d{4}$'
    if not re.match(pattern, academic_year):
        return False
    
    try:
        start_year, end_year = map(int, academic_year.split('-'))
    except ValueError:
        return False # Should not happen if regex matched

    if not (2000 <= start_year <= 2100 and 2000 <= end_year <= 2100):
        return False
    
    year_diff = end_year - start_year
    return year_diff in [1, 2, 3] # Allows 1, 2, or 3 year durations

def validate_course_code_format(course_code: str) -> bool:
    """
    Validate course code format (alphanumeric, optionally with hyphens/underscores, max 10 chars).
    
    Args:
        course_code: Course code to validate.
    
    Returns:
        bool: True if valid, False otherwise.
    """
    if not course_code or len(course_code) > 10:
        return False
    # Allows alphanumeric, hyphen, underscore. Does not check for existence in DB here.
    return re.match(r'^[a-zA-Z0-9_-]+$', course_code) is not None

def validate_required_field(value: Optional[str], field_name: str) -> str:
    """
    Validate that a field is not empty or just whitespace.
    
    Args:
        value: Value to validate.
        field_name: Name of the field for error messages.
    
    Returns:
        str: The stripped, validated value.
    
    Raises:
        ValidationError: If field is empty.
    """
    if value is None or not str(value).strip():
        raise ValidationError(f"{field_name} is required.")
    return str(value).strip()


def validate_student_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate complete student data from a dictionary.
    
    Args:
        data: Student data dictionary.
    
    Returns:
        dict: Validated and cleaned data.
    
    Raises:
        ValidationError: If validation fails, with an 'errors' attribute containing field-specific messages.
    """
    errors: Dict[str, str] = {}
    validated_data: Dict[str, Any] = {}

    # --- Required Fields ---
    try:
        validated_data['student_name'] = validate_required_field(data.get('student_name'), 'Student Name')
    except ValidationError as e:
        errors['student_name'] = str(e)

    try:
        validated_data['father_name'] = validate_required_field(data.get('father_name'), 'Father Name')
    except ValidationError as e:
        errors['father_name'] = str(e)

    # DOB and Age calculation
    dob_str = data.get('dob')
    if not dob_str:
        errors['dob'] = "Date of Birth is required."
    else:
        try:
            validated_data['dob'] = validate_date_format(dob_str, 'Date of Birth')
            if validated_data['dob']:
                today = date.today()
                age = today.year - validated_data['dob'].year - \
                      ((today.month, today.day) < (validated_data['dob'].month, validated_data['dob'].day))
                validated_data['age'] = validate_age(age) # This validate_age will check bounds
        except ValidationError as e:
            errors['dob'] = str(e)
        except Exception: # Catch any other error during age calculation
             errors['dob'] = "Invalid Date of Birth for age calculation."


    # Date of Admission
    admission_date_str = data.get('date_of_admission')
    if not admission_date_str:
        errors['date_of_admission'] = "Date of Admission is required."
    else:
        try:
            validated_data['date_of_admission'] = validate_date_format(admission_date_str, 'Date of Admission')
        except ValidationError as e:
            errors['date_of_admission'] = str(e)
    
    # Type (e.g., New Admission)
    try:
        validated_data['type'] = validate_required_field(data.get('type'), 'Admission Type')
    except ValidationError as e:
        errors['type'] = str(e)


    # Course ID
    try:
        course_id_val = data.get('course_id')
        if course_id_val is None or str(course_id_val).strip() == "":
            errors['course_id'] = "Course is required."
        else:
            validated_data['course_id'] = int(course_id_val)
            if validated_data['course_id'] <= 0:
                errors['course_id'] = "Invalid Course selection."
    except (ValueError, TypeError):
        errors['course_id'] = "Course ID must be a valid number."

    # Academic Year ID
    try:
        academic_year_id_val = data.get('academic_year_id')
        if academic_year_id_val is None or str(academic_year_id_val).strip() == "":
            errors['academic_year_id'] = "Academic Year is required."
        else:
            validated_data['academic_year_id'] = int(academic_year_id_val)
            if validated_data['academic_year_id'] <= 0:
                errors['academic_year_id'] = "Invalid Academic Year selection."
    except (ValueError, TypeError):
        errors['academic_year_id'] = "Academic Year ID must be a valid number."


    # --- Optional Fields with Validation ---
    validated_data['surname'] = str(data.get('surname', '') or '').strip()
    validated_data['mother_name'] = str(data.get('mother_name', '') or '').strip()
    
    gender = str(data.get('gender', '') or '').strip()
    if gender and gender not in ['Male', 'Female', 'Other']:
        errors['gender'] = "Gender must be Male, Female, or Other."
    else:
        validated_data['gender'] = gender or None # Store as None if empty

    email = str(data.get('email', '') or '').strip()
    if email and not validate_email(email):
        errors['email'] = "Invalid email format."
    else:
        validated_data['email'] = email or None

    phone = str(data.get('phone_no', '') or '').strip()
    if phone and not validate_phone(phone):
        errors['phone_no'] = "Invalid phone number format (7-15 digits, can include +, -, (), spaces)."
    else:
        validated_data['phone_no'] = phone or None

    aadhar = str(data.get('aadhar_no', '') or '').strip()
    if aadhar and not validate_aadhar(aadhar):
        errors['aadhar_no'] = "Aadhar number must be 12 digits."
    else:
        validated_data['aadhar_no'] = aadhar or None
    
    date_of_leaving_str = data.get('date_of_leaving')
    if date_of_leaving_str: # Only validate if provided
        try:
            validated_data['date_of_leaving'] = validate_date_format(date_of_leaving_str, 'Date of Leaving')
            if validated_data.get('date_of_leaving') and validated_data.get('date_of_admission') and \
               validated_data['date_of_leaving'] < validated_data['date_of_admission']:
                errors['date_of_leaving'] = "Date of Leaving cannot be before Date of Admission."
        except ValidationError as e:
            errors['date_of_leaving'] = str(e)
    else:
        validated_data['date_of_leaving'] = None

    # --- Other Optional Fields (basic strip) ---
    for field in ['address1', 'address2', 'address3', 'town', 'state', 
                  'nationality', 'religion', 'caste', 'sub_caste', 
                  'mother_tongue', 'previous_college', 'old_tc_no_date', 'remarks']:
        validated_data[field] = str(data.get(field, '') or '').strip() or None

    validated_data['conduct'] = str(data.get('conduct') or 'Good').strip()


    if errors:
        raise ValidationError("Student data validation failed.", errors=errors)
    
    return validated_data


def validate_course_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate course data.
    
    Args:
        data: Course data dictionary.
    
    Returns:
        dict: Validated course data.
    
    Raises:
        ValidationError: If validation fails, with an 'errors' attribute.
    """
    errors: Dict[str, str] = {}
    validated_data: Dict[str, Any] = {}

    try:
        validated_data['course_name'] = validate_required_field(data.get('course_name'), 'Course Name')
    except ValidationError as e:
        errors['course_name'] = str(e)

    try:
        course_code_val = validate_required_field(data.get('course_code'), 'Course Code').upper()
        if not validate_course_code_format(course_code_val): # Just format, not existence
            errors['course_code'] = "Course code must be alphanumeric (hyphens/underscores allowed) and max 10 characters."
        else:
            validated_data['course_code'] = course_code_val
    except ValidationError as e:
        errors['course_code'] = str(e)
    
    course_type = str(data.get('type', '') or '').strip()
    if not course_type:
        errors['type'] = "Course type is required."
    elif course_type not in ['PA', 'R', 'SF', 'SS']:
        errors['type'] = "Course type must be one of: PA, R, SF, SS."
    else:
        validated_data['type'] = course_type

    try:
        year_val = data.get('year')
        if year_val is None or str(year_val).strip() == "":
             errors['year'] = "Curriculum Year is required."
        else:
            year_int = int(year_val)
            if not (2000 <= year_int <= 2100): # As per schema
                errors['year'] = "Curriculum Year must be between 2000 and 2100."
            else:
                validated_data['year'] = year_int
    except (ValueError, TypeError):
        errors['year'] = "Curriculum Year must be a valid number."
        
    validated_data['course_full_name'] = str(data.get('course_full_name', '') or '').strip() or None

    if errors:
        raise ValidationError("Course data validation failed.", errors=errors)
        
    return validated_data

def clean_string(value: Optional[str], max_length: Optional[int] = None) -> Optional[str]:
    """
    Clean and sanitize string input. Strips whitespace, reduces multiple spaces to one.
    
    Args:
        value: String to clean.
        max_length: Maximum allowed length after cleaning.
    
    Returns:
        str: Cleaned string, or None if input was None or empty after stripping.
    """
    if value is None:
        return None
    
    cleaned = ' '.join(str(value).strip().split()) # Strip and reduce multiple spaces
    
    if not cleaned: # If string becomes empty after stripping
        return None

    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length].strip() # Ensure it doesn't end with partial word if possible, though simple slice here
    
    return cleaned