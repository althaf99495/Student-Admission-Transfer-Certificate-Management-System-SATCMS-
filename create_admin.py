from models.db_pool import db_manager
from werkzeug.security import generate_password_hash
from app import create_app

def create_admin():
    username = input("Enter admin username: ").strip()
    password = input("Enter admin password: ").strip()
    if not username or not password:
        print("Username and password cannot be empty.")
        return

    # Check if username already exists
    existing = db_manager.execute_query(
        "SELECT id FROM admins WHERE username = ?",
        (username,),
        fetch_one=True
    )
    if existing:
        print(f"Error: Username '{username}' already exists.")
        return

    password_hash = generate_password_hash(password)
    db_manager.execute_query(
        "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
        commit=True
    )
    print(f"Admin user '{username}' created successfully!")

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        create_admin()