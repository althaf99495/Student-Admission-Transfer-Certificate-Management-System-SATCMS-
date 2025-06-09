import sqlite3
import os

SCHEMA_PATH = os.path.join("db", "schema.sql")
DATABASE_PATH = "college.db"

def initialize_database():
    if not os.path.exists(SCHEMA_PATH):
        print("❌ Schema file not found:", SCHEMA_PATH)
        return

    with open(SCHEMA_PATH, 'r') as schema_file:
        schema_sql = schema_file.read()

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        conn.close()
        print("✅ Database initialized successfully at:", DATABASE_PATH)
    except sqlite3.Error as e:
        print("❌ Failed to initialize database:", e)

if __name__ == "__main__":
    initialize_database()
