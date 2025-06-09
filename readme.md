# 🏫 Student Admission & Transfer Certificate Management System (SATCMS)

## 📘 Project Description

SATCMS is a full-featured, secure, and modular web application built with Flask. It enables educational institutions to manage student admissions, academic records, fee payments, and transfer certificates with ease and automation. It combines reliability, usability, and modern web development practices to deliver a robust administrative portal.

---

## 🚀 Key Features

### 👤 User Authentication & Authorization

* Secure admin login using password hashing (`werkzeug`)
* First-time setup wizard for admin creation
* Session-based login with optional timeout support
* Role-based access control (designed for future extension)

### 🎓 Student Management

* Complete student admission form with personal & academic details
* Auto-generated admission number based on course and academic year
* View, edit, and delete student records with tracking
* Detailed student profile views with linked fee & TC data
* Bulk student import/export (CSV/Excel planned)

### 🏫 Academic Structure

* Course management with types (e.g., Regular, SF)
* Academic year configuration
* Course ↔ Year ↔ Fee structure linking

### 💰 Financial Management

* Define fee structures per course/year
* Track payments with multiple modes (Cash, UPI, DD, etc.)
* Generate receipts and maintain balance history
* Display outstanding dues per student
* Generate financial reports

### 📄 Transfer Certificate (TC) Management

* TC generation using `.docx` Word templates
* Auto-generate TC number (sequential)
* Generate and preview PDF versions
* Re-issue/re-generate TC if needed
* All TCs stored and retrievable by student ID

### 📊 Reporting

* Admission register by course/year
* Fee collection report (by date, course, year)
* TC issuance report
* Ready for custom report extension

---

## ⚙️ Technical Overview

### 🧠 Backend

* Python 3.10+ with Flask
* SQLite (default), PostgreSQL/MySQL ready
* Modular Blueprint architecture
* Custom validators and error handlers
* Logging and audit-ready structure

### 🎨 Frontend

* HTML5 + Jinja2 templates
* Bootstrap-based responsive layout
* Form validation and interactivity with JavaScript
* PDF/Word preview integration

---

## 🗂️ Database Schema (Entities)

* `students`: All student data including academics
* `courses`: Course/Program metadata
* `academic_years`: Academic session tracking
* `fee_structure`: Amounts tied to course/year
* `student_fee_payments`: Individual payment logs
* `transfer_certificates`: TC history & file refs
* `admins`: Authorized admin accounts

---

## 🔐 Security Measures

* Passwords hashed with `werkzeug.security`
* CSRF protection via Flask-WTF or middleware
* Input sanitization and validation
* Secure file handling (uploads, PDFs)
* Session timeout and re-authentication patterns

---

## 🧰 Utility Modules

* `admission_number.py`: Sequential admission ID logic
* `pdf_utils.py`: Word to PDF conversion and document merge
* `validators.py`: All form-level and value-level checks
* `report_generator.py`: For DOCX/PDF based reports

---

## 🧪 Testing Plan

* Unit tests for:

  * Admission number generator
  * Document generator
  * Validators
* Integration tests:

  * Route access
  * Auth/session flow
* Database consistency tests
* Frontend form validation

---

## 📚 Documentation

* ✅ API Reference (planned via Flask-RESTful or Swagger)
* ✅ Database schema diagrams
* ✅ Setup and installation guide
* ✅ Admin user guide

---

## 📦 Project Structure (Simplified)

```
student_tc_app/
├── app.py
├── config.py
├── models/
│   └── db_pool.py
├── routes/
│   ├── students.py
│   ├── courses.py
│   ├── fees.py
│   └── ...
├── utils/
│   ├── admission_number.py
│   ├── pdf_utils.py
│   └── validators.py
├── templates/
│   └── base.html, login.html, ...
├── static/
│   ├── css/
│   └── js/
├── db/
│   └── schema.sql
└── requirements.txt
```

---

## ✅ Next Steps

* [ ] Finish all blueprint template files
* [ ] Integrate `pdf_utils.py` with working `TCGenerator` and `ReportGenerator`
* [ ] Finalize testing utilities
* [ ] Prepare deployment setup for Linux server or Render/Heroku
