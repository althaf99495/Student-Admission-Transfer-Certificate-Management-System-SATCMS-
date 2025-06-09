from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from models.db_pool import db_manager
from utils.auth_helpers import admin_required, check_password_complexity

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handles the admin login process."""
    if session.get('admin_logged_in'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and password are required.', 'danger')
            return render_template('auth/login.html')

        # In a real app, you would query the database for the user
        admin = db_manager.execute_query("SELECT * FROM admins WHERE username = ?", (username,), fetch_one=True)

        if admin and check_password_hash(admin['password_hash'], password):
            session['admin_logged_in'] = True
            session['username'] = admin['username']
            session['admin_id'] = admin['id']
            flash('You have been logged in successfully!', 'success')
            
            next_url = request.args.get('next')
            return redirect(next_url or url_for('index'))
        else:
            flash('Invalid username or password.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@admin_required
def logout():
    """Logs the admin out."""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change_password', methods=['GET', 'POST'])
@admin_required
def change_password():
    """Allows the logged-in admin to change their password."""
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        admin_id = session.get('admin_id')

        admin = db_manager.execute_query("SELECT * FROM admins WHERE id = ?", (admin_id,), fetch_one=True)

        if not admin or not check_password_hash(admin['password_hash'], current_password):
            flash('Your current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('auth.change_password'))

        is_complex, message = check_password_complexity(new_password)
        if not is_complex:
            flash(message, 'danger')
            return redirect(url_for('auth.change_password'))

        new_password_hash = generate_password_hash(new_password)
        try:
            db_manager.execute_query(
                "UPDATE admins SET password_hash = ? WHERE id = ?",
                (new_password_hash, admin_id),
                commit=True
            )
            flash('Your password has been updated successfully.', 'success')
            return redirect(url_for('index'))
        except Exception as e:
            flash(f'An error occurred while updating your password: {e}', 'danger')

    return render_template('auth/change_password.html')