# utils/template_filters.py

from datetime import datetime as dt
import re
from flask import current_app
def format_datetime_filter(value, fmt=None):
    """
    Jinja filter to format a date string or datetime object.
    Uses DISPLAY_DATE_FORMAT from app config if no fmt is provided.
    """
    if not value:
        return ""
    if fmt is None:
        fmt = current_app.config.get('DISPLAY_DATE_FORMAT', '%d/%m/%Y')
    
    if isinstance(value, str):
        # Attempt to parse if it's a string, assuming YYYY-MM-DD format from DB
        value = dt.strptime(value, current_app.config.get('DATE_FORMAT', '%Y-%m-%d'))
    return value.strftime(fmt)

def format_currency_filter(value, currency_symbol='₹'):
    """
    Jinja filter to format a number as currency.
    e.g., 12345.67 -> ₹ 12,345.67
    """
    if value is None or value == "":
        return ""
    try:
        return f"{currency_symbol} {float(value):,.2f}"
    except (ValueError, TypeError):
        return str(value) # Return original value if conversion fails

def nl2br_filter(value: str) -> str:
    """
    Jinja filter to convert newlines in a string to HTML <br> tags.
    """
    if not isinstance(value, str):
        return value # Return as-is if not a string
    # Ensure HTML safety if the content might contain user-input HTML
    # For now, assuming the content is plain text.
    # If you need to escape HTML, use markupsafe.escape before replacing.
    return value.replace('\r\n', '<br>').replace('\n', '<br>').replace('\r', '<br>')