from datetime import datetime

def convert_date_to_words(date_str: str, input_format: str = '%Y-%m-%d') -> str:
    """
    Converts a date string to a word format like "DD - MM - YYYY"
    where each digit is spelled out.
    Example: "16-11-2002" -> "ONE SIX - ONE ONE - TWO ZERO ZERO TWO"
    """
    digit_to_word = {
        '0': 'ZERO', '1': 'ONE', '2': 'TWO', '3': 'THREE', '4': 'FOUR',
        '5': 'FIVE', '6': 'SIX', '7': 'SEVEN', '8': 'EIGHT', '9': 'NINE'
    }

    date_obj = None
    try:
        date_obj = datetime.strptime(date_str, input_format)
    except (ValueError, TypeError):
        # If the primary format fails, try the display format from config.py
        # This handles cases where DB might contain dates in DD-MM-YYYY despite schema
        from flask import current_app
        display_format = current_app.config.get('DISPLAY_DATE_FORMAT', '%d-%m-%Y')
        if input_format != display_format: # Avoid trying the same format twice
            try:
                date_obj = datetime.strptime(date_str, display_format)
            except (ValueError, TypeError):
                pass # Fall through to return "INVALID DATE"

        # Handle cases where date_str might be None or invalid
        return "INVALID DATE"

    day_str = date_obj.strftime('%d')
    month_str = date_obj.strftime('%m')
    year_str = date_obj.strftime('%Y')

    def spell_out_digits(s):
        return ' '.join(digit_to_word[char] for char in s)

    formatted_day = spell_out_digits(day_str)
    formatted_month = spell_out_digits(month_str)
    formatted_year = spell_out_digits(year_str)

    return f"{formatted_day} - {formatted_month} - {formatted_year}"