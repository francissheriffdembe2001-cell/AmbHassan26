# SLeClear MIS
## Sierra Leone Student Clearance & Financial Management Information System
### Limkokwing University Sierra Leone

---

## Tech Stack

| Layer      | Technology                        |
|------------|-----------------------------------|
| Frontend   | HTML5, CSS3, Bootstrap 5, JS      |
| Backend    | Python Flask                      |
| Database   | MySQL (via XAMPP)                 |
| PDF Export | ReportLab                         |
| Server     | XAMPP localhost                   |

---

## Project Structure

```
sleclear/
├── app.py               ← Flask application (all routes + logic)
├── init_db.py           ← One-time DB setup script
├── database.sql         ← Full schema + sample data
├── requirements.txt     ← Python dependencies
├── templates/
│   ├── base.html        ← Sidebar layout, dark UI
│   ├── login.html       ← Authentication page
│   ├── dashboard.html   ← KPI dashboard + charts
│   ├── students.html    ← Student list + search
│   ├── student_form.html← Add / Edit student
│   ├── student_view.html← Student profile detail
│   ├── payments.html    ← Payment list + verify
│   ├── payment_form.html← Record payment
│   ├── clearance.html   ← Clearance management
│   ├── clearance_slip.html ← Printable slip
│   ├── deferred.html    ← Deferred applications list
│   ├── deferred_form.html  ← New application
│   ├── deferred_review.html← Registry review
│   ├── reports.html     ← Reports + export
│   └── error.html       ← 404 / 500 error pages
└── static/
    ├── css/             ← Optional custom overrides
    └── js/              ← Optional custom scripts
```

---

## Setup Instructions (XAMPP)

### Step 1 — Install Prerequisites

1. Install **XAMPP** from https://www.apachefriends.org
2. Install **Python 3.10+** from https://python.org
3. Open XAMPP Control Panel → Start **MySQL** (port 3306)

### Step 2 — Install Python Dependencies

Open a terminal / Command Prompt in the project folder:

```bash
pip install -r requirements.txt
```

> On Linux/Mac you may need `pip3`

### Step 3 — Initialise the Database

```bash
python init_db.py
```

This will:
- Create the `sleclear_db` MySQL database
- Create all tables (`users`, `students`, `payments`, `clearances`, `deferred_assessments`, `activity_log`)
- Insert 15 sample students, 24 payments, clearance records, and deferred applications

### Step 4 — Start the Flask Application

```bash
python app.py
```

### Step 5 — Open in Browser

```
http://localhost:5000
```

---

## Default Credentials

| Role     | Username | Password    |
|----------|----------|-------------|
| Admin    | admin    | admin123    |
| Finance  | finance  | finance123  |
| Registry | registry | registry123 |

---

## Role Permissions

| Feature              | Admin | Finance | Registry |
|----------------------|-------|---------|----------|
| Dashboard            | ✅    | ✅      | ✅       |
| View Students        | ✅    | ✅      | ✅       |
| Add/Edit Students    | ✅    | ❌      | ✅       |
| Delete Students      | ✅    | ❌      | ❌       |
| View Payments        | ✅    | ✅      | ✅       |
| Record Payments      | ✅    | ✅      | ❌       |
| Verify Payments      | ✅    | ✅      | ❌       |
| Clearance View       | ✅    | ✅      | ✅       |
| Provisional Clearance| ✅    | ✅      | ❌       |
| Generate Clearance   | ✅    | ✅      | ❌       |
| Deferred View        | ✅    | ✅      | ✅       |
| Submit Deferred      | ✅    | ❌      | ✅       |
| Review Deferred      | ✅    | ❌      | ✅       |
| Reports & Export     | ✅    | ✅      | ✅       |

---

## Clearance Logic

```
IF student.total_fee - student.amount_paid <= 0
    → status = CLEARED
ELSE
    → status = NOT CLEARED

PROVISIONAL CLEARANCE:
    → Manually granted by Admin/Finance
    → Valid for 30 days
    → Auto-recorded in clearances table
```

---

## Database Schema

```sql
users               — System login accounts (admin/finance/registry)
students            — Student enrolment records with fee balances
payments            — Fee payment transactions
clearances          — Clearance status per student (auto-calculated)
deferred_assessments— Deferred exam applications with approval workflow
activity_log        — Audit trail of all system actions
```

---

## Export Formats

All reports can be exported as:
- **CSV** — For Excel/spreadsheet analysis
- **PDF** — Formatted report with headers and table styling

Available reports:
1. Cleared Students Report
2. Pending Payments Report
3. Deferred Assessments Report
4. Full Finance Summary

---

## Troubleshooting

**Cannot connect to MySQL**
- Make sure XAMPP MySQL is running (port 3306)
- Check DB_CONFIG in `app.py` — default password is blank for XAMPP

**ModuleNotFoundError**
- Run `pip install -r requirements.txt` again

**Port 5000 already in use**
- Change port in `app.py`: `app.run(port=5001)`

**Database already exists error from init_db.py**
- Safe to ignore — the script uses `CREATE IF NOT EXISTS`

---

© 2025 Limkokwing University Sierra Leone — SLeClear MIS v1.0
