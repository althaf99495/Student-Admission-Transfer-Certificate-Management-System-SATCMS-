# routes/__init__.py
"""
Route blueprints for Student TC Management System
"""

from .students import students_bp
from .courses import courses_bp
from .academic_years import academic_years_bp
from .fees import fees_bp
from .tc import tc_bp
from .reports import reports_bp

__all__ = [
    'students_bp',
    'courses_bp', 
    'academic_years_bp',
    'fees_bp',
    'tc_bp',
    'reports_bp'
]
