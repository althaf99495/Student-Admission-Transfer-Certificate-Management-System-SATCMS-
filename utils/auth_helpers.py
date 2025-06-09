from functools import wraps
from flask import session, redirect, url_for, flash, request, current_app

def admin_required(f):
    """
    Decorator to ensure that a route is accessed only by a logged-in admin.
    If not logged in, flashes a message and redirects to the login page,
    preserving the originally requested URL as the 'next' parameter.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('You need to be logged in to access this page.', 'warning')
            # Ensure 'auth.login' is a valid endpoint for your auth blueprint
            # If auth blueprint is named differently, adjust 'auth.login'
            login_url = url_for('auth.login', next=request.url) if 'auth' in current_app.blueprints else url_for('login', next=request.url) # Fallback if auth BP missing
            return redirect(login_url)
        return f(*args, **kwargs)
    return decorated_function

def check_password_complexity(password: str) -> tuple[bool, str]:
    """
    Checks if the given password meets complexity requirements.
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - (Optional: At least one special character) - Not currently implemented

    Args:
        password (str): The password to check.

    Returns:
        tuple[bool, str]: (True, "Password is complex enough.") if valid, 
                          (False, "Error message explaining failure.") otherwise.
    """
    if not password:
        return False, "Password cannot be empty."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(c.islower() for c in password): # Added lowercase check for completeness
        return False, "Password must contain at least one lowercase letter."
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit."
    # Example for special character check (can be enabled if needed)
    # if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
    #     return False, "Password must contain at least one special character."
    return True, "Password meets complexity requirements."

# Example usage (typically in a registration or password change route):
# is_complex, message = check_password_complexity(new_password)
# if not is_complex:
#     flash(message, 'danger')
# else:
#     # Proceed with password hashing and saving