import sqlite3
import threading
from contextlib import contextmanager
from flask import current_app, g
import os

class DatabaseManager:
    """Database connection manager with connection pooling"""
    
    def __init__(self):
        self._local = threading.local()
    
    def get_db(self):
        """Get database connection for current thread"""
        if not hasattr(g, 'db'):
            g.db = sqlite3.connect(
                current_app.config['DATABASE_PATH'],
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row  # Enable column access by name
            # Enable foreign key constraints
            g.db.execute('PRAGMA foreign_keys = ON')
        return g.db
    
    def close_db(self, error=None):
        """Close database connection"""
        db = g.pop('db', None)
        if db is not None:
            db.close()
    
    @contextmanager
    def get_db_cursor(self, commit=False):
        """Context manager for database operations"""
        db = self.get_db()
        cursor = db.cursor()
        try:
            yield cursor
            if commit:
                db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            cursor.close()
    
    def init_db(self, app):
        """Initializes the database schema."""
        with app.app_context():
            db = self.get_db()
            schema_path = os.path.join(current_app.root_path, 'db', 'schema.sql')
            with open(schema_path, 'r', encoding="utf-8") as f:
                db.executescript(f.read())
            db.commit()
            current_app.logger.info("Database schema initialized.")

    def execute_query(self, query, args=(), fetch_one=False, fetch_all=False, commit=False):
        """Execute a database query"""
        try:
            with self.get_db_cursor(commit=commit) as cursor:
                cursor.execute(query, args)
                if fetch_one:
                    return cursor.fetchone()
                if fetch_all:
                    return cursor.fetchall()
                return None
        except sqlite3.Error as e:
            current_app.logger.error(f"Database error: {e} - Query: {query} - Args: {args}")
            raise # Re-raise the exception to be handled by Flask's error handlers or caller

    def get_dashboard_stats(self):
        """Returns a dictionary of dashboard statistics."""
        stats = {}
        # Total students
        row = self.execute_query("SELECT COUNT(*) as count FROM students", fetch_one=True)
        stats['total_students'] = row['count'] if row else 0

        # Total courses
        row = self.execute_query("SELECT COUNT(*) as count FROM courses", fetch_one=True)
        stats['total_courses'] = row['count'] if row else 0

        # Total academic years
        row = self.execute_query("SELECT COUNT(*) as count FROM academic_years", fetch_one=True)
        stats['total_academic_years'] = row['count'] if row else 0

        # Recent students (last 10)
        stats['recent_students'] = self.execute_query(
            """SELECT s.id, s.student_name, s.admission_no, s.date_of_admission, c.course_name
               FROM students s
               JOIN courses c ON s.course_id = c.id
               ORDER BY s.date_of_admission DESC
               LIMIT 10""",
            fetch_all=True
        )

        return stats

# Global instance of DatabaseManager
db_manager = DatabaseManager()

def query_db(query, args=(), one=False):
    """
    Helper function to query the database.
    Use `db_manager.execute_query` instead for more control.
    Retained for compatibility with older code that might use it.
    """
    return db_manager.execute_query(query, args, fetch_one=one, fetch_all=not one)

def execute_db(query, args=(), commit=True):
    """
    Helper function to execute database commands (INSERT, UPDATE, DELETE).
    Use `db_manager.execute_query` instead for more control.
    Retained for compatibility with older code that might use it.
    """
    return db_manager.execute_query(query, args, commit=commit)

# Specific queries for common data
def get_student_by_id(student_id):
    """Get student details by ID, including course and academic year names."""
    query = """
        SELECT s.*, c.course_name, c.course_full_name, c.course_code, ay.academic_year
        FROM students s
        JOIN courses c ON s.course_id = c.id
        JOIN academic_years ay ON s.academic_year_id = ay.id
        WHERE s.id = ?
    """
    return db_manager.execute_query(query, (student_id,), fetch_one=True)

def get_courses():
    """Get all courses"""
    query = "SELECT * FROM courses ORDER BY course_name"
    return db_manager.execute_query(query, fetch_all=True)

def get_academic_years():
    """Get all academic years"""
    query = "SELECT * FROM academic_years ORDER BY academic_year DESC"
    return db_manager.execute_query(query, fetch_all=True)

def get_all_students(course_id=None, academic_year_id=None, order_by="s.admission_no ASC"):
    """
    Fetches all students with optional filters for course and academic year,
    and allows specifying an order.
    Returns comprehensive student data including course and academic year names.
    """
    base_query = """
        SELECT s.*, c.course_name, c.course_full_name, c.course_code, ay.academic_year
        FROM students s
        JOIN courses c ON s.course_id = c.id
        JOIN academic_years ay ON s.academic_year_id = ay.id
    """
    conditions = []
    params = []

    if course_id is not None:
        conditions.append("s.course_id = ?")
        params.append(course_id)
    
    if academic_year_id is not None:
        conditions.append("s.academic_year_id = ?")
        params.append(academic_year_id)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)
    
    if order_by:
        base_query += f" ORDER BY {order_by}" # Be cautious with unvalidated order_by strings

    return db_manager.execute_query(base_query, tuple(params), fetch_all=True)

def get_fee_payments_for_report(course_id=None, academic_year_id=None):
    """
    Fetches fee payment records for reporting, with optional filters.
    """
    query = """
        SELECT
            p.id as payment_id,
            p.payment_date,
            p.amount_paid,
            p.transaction_id,
            p.payment_method,
            s.student_name,
            s.admission_no,
            c.course_name,
            ay.academic_year
        FROM student_fee_payments p
        JOIN students s ON p.student_id = s.id
        JOIN courses c ON s.course_id = c.id
        JOIN academic_years ay ON s.academic_year_id = ay.id
    """
    conditions = []
    params = []

    # if start_date: # Removed date filters
    #     conditions.append("p.payment_date >= ?")
    #     params.append(start_date)
    # if end_date: # Removed date filters
    #     conditions.append("p.payment_date <= ?")
    #     params.append(end_date)
    if course_id:
        conditions.append("s.course_id = ?")
        params.append(course_id)
    if academic_year_id:
        conditions.append("s.academic_year_id = ?")
        params.append(academic_year_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY p.payment_date ASC, s.admission_no ASC"
    return db_manager.execute_query(query, tuple(params), fetch_all=True)

def get_tc_issued_for_report(course_id=None, academic_year_id=None):
    """
    Fetches TC issued records for reporting, with optional date filters.
    """
    query = """
        SELECT
            tc.tc_number,
            tc.issue_date,
            s.student_name,
            s.admission_no,
            s.date_of_leaving,
            c.course_name,
            ay.academic_year
        FROM transfer_certificates tc
        JOIN students s ON tc.student_id = s.id
        JOIN courses c ON s.course_id = c.id
        JOIN academic_years ay ON s.academic_year_id = ay.id
    """
    conditions = []
    params = []

    if course_id: # Added course filter
        conditions.append("s.course_id = ?")
        params.append(course_id)
    if academic_year_id: # Added academic year filter
        conditions.append("s.academic_year_id = ?")
        params.append(academic_year_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY tc.issue_date ASC, tc.tc_number ASC"
    return db_manager.execute_query(query, tuple(params), fetch_all=True)