"""
Configuration settings for SATCMS Application
"""
from dotenv import load_dotenv # Import load_dotenv
import os
import secrets

# Load environment variables from .env file if it exists
load_dotenv()

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
    COLLEGE_NAME = "SRI VENKATESWARA UNIVERSITY, TIRUPATHI" # Add a default college name

    # Pagination settings
    STUDENTS_PER_PAGE = 25
    RECORDS_PER_PAGE = 20

    # TC Generation settings
    TC_TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), 'templates', 'tc_template.docx')
    TC_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'static', 'uploads', 'tc_generated')

    # Date format settings
    # NOTE: The DATE_FORMAT is used for parsing date strings from forms.
    # Storing dates in 'DD-MM-YYYY' format in the database is not recommended as it breaks sorting.
    # The ideal approach is to parse this format in the view and convert to 'YYYY-MM-DD' for storage.
    DATE_FORMAT = '%d-%m-%Y'
    DISPLAY_DATE_FORMAT = '%d-%m-%Y'

    # Email settings (configure these for your SMTP server)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.example.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587)) # Default for TLS
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't'] # Usually one or the other
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # e.g., 'your-email@example.com'
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # e.g., 'your-email-password'
    MAIL_DEFAULT_SENDER_NAME = os.environ.get('MAIL_DEFAULT_SENDER_NAME', 'College Administration')
    MAIL_DEFAULT_SENDER_EMAIL = os.environ.get('MAIL_DEFAULT_SENDER_EMAIL', 'noreply@example.com') # Default sender address

    # Allowed payment methods for fee payments (from schema.sql)
    ALLOWED_PAYMENT_METHODS = ['Cash', 'Online', 'Cheque', 'DD', 'Card', 'UPI', 'Bank Transfer', 'Other']

    # Caching settings (for Flask-Caching)
    CACHE_TYPE = "RedisCache"
    CACHE_REDIS_HOST = "localhost"
    CACHE_REDIS_PORT = 6379
    CACHE_REDIS_DB = 0
    CACHE_REDIS_PASSWORD = None
    CACHE_DEFAULT_TIMEOUT = 300 # Default cache timeout in seconds (5 minutes)

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
    HOST = '0.0.0.0'  # Use '0.0.0.0' to be accessible on your network
    PORT = 5001       # Or your preferred port
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