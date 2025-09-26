#!/usr/bin/env python3
"""
Student Admission & Transfer Certificate Management System (SATCMS)
Main Flask Application Entry Point
"""

from flask import Flask, render_template, session, redirect, url_for, flash, request, send_from_directory
from flask_wtf.csrf import CSRFProtect
import sqlite3
import os
from werkzeug.security import generate_password_hash # For default admin setup

from config import config # Import the config dictionary
from models.db_pool import db_manager, DatabaseManager # Import db_manager instance and class
# Import route blueprints (ensure these files exist and define blueprints correctly)
from routes.auth import auth_bp # Assuming you have an auth blueprint
from routes.students import students_bp
from routes.courses import courses_bp
from routes.academic_years import academic_years_bp
from routes.fees import fees_bp
from routes.tc import tc_bp
from routes.reports import reports_bp
from utils.template_filters import format_datetime_filter, format_currency_filter, nl2br_filter # Import filters
from utils.caching import init_app_cache # If you implement a more robust cache init

def create_app(config_name=None, init_db=True):
    """Application factory pattern."""
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app) # Call init_app for selected config (e.g. to create folders)

    # Initialize CSRF protection
    CSRFProtect(app)

    # Initialize database manager with the app
    # The db_manager instance itself doesn't need init with app, 
    # but its methods like init_db_schema need app context.
    # Connections are handled per-request using Flask's 'g'.
    app.teardown_appcontext(db_manager.close_db) # Close DB connection at end of request/app_context

    # Initialize database schema if it's the first run or DB doesn't exist
    # This check is performed within the app context during creation.
    # A dedicated CLI command (e.g., `flask init-db`) is a more robust approach
    # for production/deployment, but this simple check works for basic setups.
    if init_db: # Allow skipping init_db for testing or specific scenarios
        with app.app_context():
            if not os.path.exists(app.config['DATABASE_PATH']):
                app.logger.info(f"Database not found at {app.config['DATABASE_PATH']}. Initializing...")
                try:
                    # Ensure the directory for the database exists (also done in Config.init_app)
                    # os.makedirs(os.path.dirname(app.config['DATABASE_PATH']), exist_ok=True) # Redundant, handled by Config.init_app
                    db_manager.init_db(app) # This also ensures the db dir exists via Config.init_app
                    _setup_default_admin_if_needed(app) # Setup default admin after schema creation
                except Exception as e:
                    app.logger.error(f"Failed to initialize database or setup admin: {e}", exc_info=True)
            else:
                app.logger.info(f"Database found at {app.config['DATABASE_PATH']}.")
                _setup_default_admin_if_needed(app) # Check admin even if DB exists

    # Initialize caching if you have a sophisticated cache manager
    if 'init_app_cache' in globals():
        init_app_cache(app)

    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth') # Example for auth
    app.register_blueprint(students_bp, url_prefix='/students')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(academic_years_bp, url_prefix='/academic-years')
    app.register_blueprint(fees_bp, url_prefix='/fees')
    app.register_blueprint(tc_bp, url_prefix='/tc')
    app.register_blueprint(reports_bp, url_prefix='/reports')

    # Register custom template filters
    app.jinja_env.filters['datetime'] = format_datetime_filter
    app.jinja_env.filters['currency'] = format_currency_filter
    app.jinja_env.filters['nl2br'] = nl2br_filter
    
    # --- Favicon Route ---
    # Serve the favicon to prevent 404 errors in browser logs
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # --- Base Routes ---
    @app.route('/')
    def index():
        if session.get('admin_logged_in'):
            # Fetch dashboard stats if user is logged in
            try:
                dashboard_stats = db_manager.get_dashboard_stats()
                academic_years = db_manager.execute_query("SELECT * FROM academic_years ORDER BY academic_year DESC", fetch_all=True)
                return render_template('index.html', stats=dashboard_stats, academic_years=academic_years)
            except Exception as e:
                app.logger.error(f"Error fetching dashboard stats: {e}", exc_info=True)
                flash("Could not load dashboard statistics.", "error")
                return render_template('index.html', stats=None, academic_years=[]) # Render even if stats fail
        return render_template('index.html', stats=None, academic_years=[]) # Or redirect to login if preferred

    # Redirects for auth routes - assuming an 'auth' blueprint handles actual logic
    # If your auth blueprint is named e.g. 'authentication', use 'authentication.login'
    # If login is at root, then just 'login'
    AUTH_BLUEPRINT_NAME = 'auth' # Change if your auth blueprint has a different name

    @app.route('/setup_admin', methods=['GET', 'POST'])
    def setup_admin_redirect():
        # This route should ideally be handled by the auth blueprint itself
        # or removed if setup is done via CLI or initial _setup_default_admin_if_needed
        return redirect(url_for(f'{AUTH_BLUEPRINT_NAME}.setup_admin') if AUTH_BLUEPRINT_NAME in app.blueprints else '/')


    @app.route('/login', methods=['GET', 'POST'])
    def login_redirect():
        # Check if already logged in
        if session.get('admin_logged_in'):
            return redirect(url_for('index'))
        return redirect(url_for(f'{AUTH_BLUEPRINT_NAME}.login', next=request.args.get('next')) if AUTH_BLUEPRINT_NAME in app.blueprints else '/')


    @app.route('/logout')
    def logout_redirect():
        return redirect(url_for(f'{AUTH_BLUEPRINT_NAME}.logout') if AUTH_BLUEPRINT_NAME in app.blueprints else '/')

    # --- Error Handlers ---
    @app.errorhandler(400)
    def bad_request_error(error):
        app.logger.warning(f"Bad Request (400): {error} - URL: {request.url}")
        if "CSRF" in str(error).upper(): # More robust check for CSRF
            return render_template('errors/400_csrf.html', error=error), 400
        return render_template('errors/400.html', error=error), 400

    @app.errorhandler(403)
    def forbidden_error(error):
        app.logger.warning(f"Forbidden (403): {error} - URL: {request.url}")
        return render_template('errors/403.html', error=error), 403

    @app.errorhandler(404)
    def not_found_error(error):
        app.logger.warning(f"Not Found (404): {error} - URL: {request.url}")
        return render_template('errors/404.html', error=error), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f"Internal Server Error (500): {error} - URL: {request.url}", exc_info=True)
        # It's good practice to rollback database session in case of 500 if one was active and caused error
        # db_manager.get_db().rollback() # Careful, this assumes get_db() won't fail or create new TX
        return render_template('errors/500.html', error=error), 500
    
    @app.errorhandler(sqlite3.Error) # Catch SQLite specific errors globally
    def handle_database_error(error):
        app.logger.error(f"Global SQLite Error: {error} - URL: {request.url}", exc_info=True)
        # Potentially rollback here too
        # db = getattr(g, '_database', None)
        # if db: db.rollback()
        flash("A database error occurred. Please try again or contact support.", "danger")
        return render_template('errors/500.html', error="Database operation failed"), 500


    # --- Context Processors ---
    @app.context_processor
    def inject_global_vars():
        from datetime import datetime
        return dict(
            current_user_username=session.get('username'),
            app_name=app.config.get('APP_NAME', 'SATCMS'),
            current_year=datetime.now().year
        )

    return app

def _setup_default_admin_if_needed(app_instance):
    """Checks and creates a default admin if none exists. Requires app context."""
    # This function should be called within an app_context
    # from models.db_pool import db_manager # Already imported
    # from werkzeug.security import generate_password_hash # Already imported

    admin_exists = db_manager.execute_query('SELECT id FROM admins LIMIT 1', fetch_one=True)
    if not admin_exists:
        default_username = 'admin'
        default_password = 'admin123ChangeMe' # Make it slightly more "secure" by default
        app_instance.logger.info(f"No admin found. Creating a default admin '{default_username}' with password '{default_password}'.")
        hashed_password = generate_password_hash(default_password)
        try:
            db_manager.execute_query(
                "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                (default_username, hashed_password),
                commit=True
            )
            app_instance.logger.info("Default admin created. PLEASE CHANGE THE PASSWORD IMMEDIATELY after first login.")
        except sqlite3.IntegrityError:
            app_instance.logger.warning(f"Default admin '{default_username}' already exists (race condition or previous attempt).")
        except Exception as e:
            app_instance.logger.error(f"Could not create default admin: {e}", exc_info=True)


if __name__ == '__main__':
    app = create_app() # Uses 'default' config (DevelopmentConfig) by default
    
    with app.app_context(): # Operations needing app context, like logging
        # The database and admin setup is now part of create_app's logic when app context is available
        pass # Keep the context open for potential future use or logging, satisfy syntax
        
    # Run the app. We pass debug=True explicitly if DEBUG is set in config.
    # The host and port are configured in your config.py file.
    # For network access, set HOST to '0.0.0.0' in the development config.
    app.run(host=app.config.get('HOST'),
            port=app.config.get('PORT'),
            debug=app.config.get('DEBUG'))