"""
Configuration settings for SATCMS Application
"""
import os
import secrets

class Config:
    """Base configuration class"""

    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Database settings
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'college.db')

    # Security settings
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

    # Session settings
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx'}

    # Application settings
    APP_NAME = "Student Admission & Transfer Certificate Management System"
    APP_VERSION = "1.0.0"
    COLLEGE_NAME = "SV UNIVERSITY :: SVU COLLEGE OF CM & CS" # Add a default college name

    # Pagination settings
    STUDENTS_PER_PAGE = 25
    RECORDS_PER_PAGE = 20

    # TC Generation settings
    TC_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'tc_template.docx')
    TC_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'tc_generated')

    # Date format settings
    DATE_FORMAT = '%Y-%m-%d'
    DISPLAY_DATE_FORMAT = '%d/%m/%Y'

    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        # Create necessary folders if they don't exist
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(app.config['TC_OUTPUT_PATH'], exist_ok=True)
        # Ensure the directory for the database exists
        os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # For stable CSRF tokens during development with auto-reload
    SECRET_KEY = 'dev_secret_this_is_not_for_production_!@#' # Replace with your own static key
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True  # Enable in production with HTTPS

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'test_college.db')
    WTF_CSRF_ENABLED = False # Disable CSRF for easier testing
    SECRET_KEY = 'test_secret_key' # Use a fixed secret key for testing

# Dictionary to hold different config environments
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}