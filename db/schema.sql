-- schema.sql - SQLite DB Schema for Student Admission & TC App

-- Table for admin users
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

-- Table: courses
CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_name TEXT NOT NULL,
    course_full_name TEXT,
    course_code TEXT NOT NULL UNIQUE CHECK (LENGTH(course_code) BETWEEN 2 AND 3), -- Allow 2 or 3 char course codes
    type TEXT NOT NULL CHECK (type IN ('PA', 'R', 'SF', 'SS')), /* PA=Private Aided, R=Regular, SF=Self-Finance, SS=Self-Supporting */
    year INTEGER NOT NULL CHECK (year BETWEEN 2000 AND 2100), /* e.g., Curriculum year */
    is_special_format INTEGER NOT NULL DEFAULT 0 CHECK (is_special_format IN (0, 1)) -- 0 for YYYYCCSSS, 1 for YYYYCCCSSS
);

-- Table: academic_years
CREATE TABLE IF NOT EXISTS academic_years (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    academic_year TEXT NOT NULL UNIQUE CHECK (
    academic_year LIKE '____-____'
    AND CAST(SUBSTR(academic_year, 6, 4) AS INTEGER) > CAST(SUBSTR(academic_year, 1, 4) AS INTEGER)
    AND CAST(SUBSTR(academic_year, 6, 4) AS INTEGER) - CAST(SUBSTR(academic_year, 1, 4) AS INTEGER) IN (1,2,3)
) /* e.g., 2024-2025, 2024-2026, 2024-2027 */
);

-- Table: students
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    academic_year_id INTEGER NOT NULL,
    is_manual_admission_no INTEGER NOT NULL DEFAULT 0 CHECK (is_manual_admission_no IN (0, 1)), /* 0 for auto admission_no, 1 for manual. Both are 9 chars (YYYYCCSSS or YYYYCCCSS). */
    admission_no TEXT NOT NULL UNIQUE,
    serial_no INTEGER NOT NULL, /* Serial component. Auto: 1-999 (std) or 1-99 (spcl). Manual: 0-999 (std) or 0-99 (spcl). Unique for course_id & academic_year_id. */
    type TEXT NOT NULL, /* e.g., New Admission, Readmission */
    student_name TEXT NOT NULL,
    surname TEXT,
    father_name TEXT,
    mother_name TEXT,
    gender TEXT CHECK (gender IN ('Male', 'Female', 'Other')),
    address1 TEXT,
    address2 TEXT,
    address3 TEXT,
    town TEXT,
    state TEXT,
    dob TEXT NOT NULL CHECK (dob LIKE '____-__-__'), /* Format YYYY-MM-DD, actual date validity checked in Python */
    age INTEGER CHECK (age BETWEEN 0 AND 150), /* Calculated at time of admission */
    phone_no TEXT CHECK (phone_no IS NULL OR (NOT phone_no GLOB '*[^0-9+-() ]*' AND LENGTH(phone_no) BETWEEN 7 AND 15)), /* Allows digits and common phone chars, or NULL */
    email TEXT CHECK (email IS NULL OR (email LIKE '_%@_%._%')), /* Basic check, or NULL */
    nationality TEXT,
    religion TEXT,
    caste TEXT,
    sub_caste TEXT,
    mother_tongue TEXT,
    previous_college TEXT,
    date_of_admission TEXT NOT NULL CHECK (date_of_admission LIKE '____-__-__'),
    date_of_leaving TEXT CHECK (date_of_leaving IS NULL OR (date_of_leaving LIKE '____-__-__' AND date_of_leaving >= date_of_admission)),
    old_tc_no_date TEXT, /* TC from previous institution */
    aadhar_no TEXT CHECK (aadhar_no IS NULL OR (LENGTH(aadhar_no) = 12 AND NOT aadhar_no GLOB '*[^0-9]*')), /* 12 digits or NULL */
    remarks TEXT,
    fee_structure_id INTEGER, /* Automatically assigned based on course and academic year if available */
    starting_year INTEGER CHECK (starting_year BETWEEN 2000 AND 2100), /* Academic starting year part of admission_no */
    ending_year INTEGER CHECK (ending_year BETWEEN 2000 AND 2100),   /* Academic ending year */
    conduct TEXT DEFAULT 'Good', /* Student's conduct, for TC */
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE RESTRICT, /* Prevent course deletion if students enrolled */
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE RESTRICT, /* Prevent AY deletion if students enrolled */
    FOREIGN KEY (fee_structure_id) REFERENCES fee_structure(id) ON DELETE SET NULL
);
-- Index to ensure unique admission serials per course and year
CREATE UNIQUE INDEX IF NOT EXISTS idx_students_course_acad_serial ON students (course_id, academic_year_id, serial_no);
-- Index to improve performance of student name searches
CREATE INDEX IF NOT EXISTS idx_students_student_name ON students (student_name);


-- Table: fee_structure
CREATE TABLE IF NOT EXISTS fee_structure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    academic_year_id INTEGER NOT NULL,
    total_fee REAL NOT NULL CHECK (total_fee >= 0),
    FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
    FOREIGN KEY (academic_year_id) REFERENCES academic_years(id) ON DELETE CASCADE,
    UNIQUE(course_id, academic_year_id)
);


-- Table: student_fee_payments
CREATE TABLE IF NOT EXISTS student_fee_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    fee_structure_id INTEGER NOT NULL, /* Should match student's assigned fee_structure_id at time of payment */
    amount_paid REAL NOT NULL CHECK (amount_paid > 0),
    payment_date TEXT NOT NULL DEFAULT CURRENT_DATE CHECK (payment_date LIKE '____-__-__'),
    transaction_id TEXT UNIQUE, /* Optional, but unique if provided. Application should handle converting empty strings to NULL. */
    payment_method TEXT CHECK (payment_method IN ('Cash', 'Online', 'Cheque', 'DD', 'Card', 'UPI', 'Bank Transfer', 'Other')),
    remarks TEXT,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE, /* If student deleted, payments are removed */
    FOREIGN KEY (fee_structure_id) REFERENCES fee_structure(id) ON DELETE RESTRICT /* Prevent fee structure deletion if payments exist */
);

-- Table: transfer_certificates
CREATE TABLE IF NOT EXISTS transfer_certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL UNIQUE,
    issue_date TEXT NOT NULL DEFAULT CURRENT_DATE CHECK (issue_date LIKE '____-__-__'),
    tc_number TEXT NOT NULL UNIQUE,
    notes TEXT,
    promotion_status TEXT, -- This is defined
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);
