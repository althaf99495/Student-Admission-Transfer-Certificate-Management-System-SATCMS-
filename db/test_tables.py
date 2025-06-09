import sqlite3
import os

DATABASE_PATH = "college.db"

EXPECTED_TABLES = [
    "courses",
    "academic_years",
    "students",
    "fee_structure",
    "student_fee_payments",
    "transfer_certificates"
]

def check_tables():
    if not os.path.exists(DATABASE_PATH):
        print("❌ Database not found:", DATABASE_PATH)
        return

    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        existing_tables = set()
        result = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
        for row in result:
            existing_tables.add(row[0])

        print("🔍 Checking tables in database...\n")
        for table in EXPECTED_TABLES:
            if table in existing_tables:
                print(f"✅ Table found: {table}")
            else:
                print(f"❌ Table missing: {table}")

        conn.close()

    except sqlite3.Error as e:
        print("❌ Failed to verify tables:", e)

if __name__ == "__main__":
    check_tables()
