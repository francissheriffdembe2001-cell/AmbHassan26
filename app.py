"""
SLeClear MIS — Sierra Leone Student Clearance & Financial Management IS
Limkokwing University Sierra Leone
Flask Backend Application
"""

from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, jsonify, make_response)
import mysql.connector
from mysql.connector import Error
import urllib.parse as _urlparse
import bcrypt
import os
import csv
import io
from datetime import datetime, date
from functools import wraps
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                 Paragraph, Spacer, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ──────────────────────────────────────────────────────────────
# Flask App Config
# ──────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = 'SLeClear@LimkokwingSL#2025'
app.config['SESSION_TYPE'] = 'filesystem'

# ──────────────────────────────────────────────────────────────
# Database Configuration (read from environment, with sensible defaults)
# Supports individual env vars or a single `DATABASE_URL` (mysql://user:pass@host:port/db)
# ──────────────────────────────────────────────────────────────
# Defaults matching the previous XAMPP/dev settings
_DB_HOST = os.environ.get('DB_HOST', 'localhost')
_DB_PORT = int(os.environ.get('DB_PORT', 3306))
_DB_USER = os.environ.get('DB_USER', 'root')
_DB_PASS = os.environ.get('DB_PASS', '')
_DB_NAME = os.environ.get('DB_NAME', 'sleclear_db')
_DB_CHARSET = os.environ.get('DB_CHARSET', 'utf8mb4')

# If a DATABASE_URL is provided, parse and override the above
_DATABASE_URL = os.environ.get('DATABASE_URL')
if _DATABASE_URL:
    try:
        p = _urlparse.urlparse(_DATABASE_URL)
        if p.scheme and p.scheme.startswith('mysql'):
            if p.username:
                _DB_USER = p.username
            if p.password:
                _DB_PASS = p.password
            if p.hostname:
                _DB_HOST = p.hostname
            if p.port:
                _DB_PORT = p.port
            if p.path and len(p.path) > 1:
                _DB_NAME = p.path.lstrip('/')
    except Exception:
        # ignore parse errors and fall back to individual env vars/defaults
        pass

DB_CONFIG = {
    'host':     _DB_HOST,
    'port':     _DB_PORT,
    'user':     _DB_USER,
    'password': _DB_PASS,
    'database': _DB_NAME,
    'charset':  _DB_CHARSET
}

def get_db():
    """Return a fresh MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        return None

def query_db(sql, params=(), fetchone=False, commit=False):
    """Execute a query and return results."""
    conn = get_db()
    if not conn:
        return None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if commit:
            conn.commit()
            return cur.lastrowid if cur.lastrowid else True
        if fetchone:
            return cur.fetchone()
        return cur.fetchall()
    except Error as e:
        print(f"[QUERY ERROR] {e}")
        if commit:
            conn.rollback()
        return None
    finally:
        cur.close()
        conn.close()

def log_activity(action, module='General'):
    """Write an entry to activity_log."""
    uid = session.get('user_id')
    query_db(
        "INSERT INTO activity_log (user_id, action, module, ip_address) VALUES (%s,%s,%s,%s)",
        (uid, action, module, request.remote_addr), commit=True
    )

# ──────────────────────────────────────────────────────────────
# Auth Decorators
# ──────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get('role') not in roles:
                flash('Access denied: insufficient permissions.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def sync_clearance(student_id):
    """Recompute clearance status based on current balance."""
    student = query_db(
        "SELECT balance FROM students WHERE student_id=%s", (student_id,), fetchone=True)
    if not student:
        return
    status = 'Cleared' if float(student['balance']) <= 0 else 'Not Cleared'
    existing = query_db(
        "SELECT id FROM clearances WHERE student_id=%s", (student_id,), fetchone=True)
    if existing:
        if status == 'Cleared':
            query_db(
                "UPDATE clearances SET status=%s, cleared_date=NOW(), valid_until='2025-08-31' WHERE student_id=%s",
                (status, student_id), commit=True)
        else:
            query_db(
                "UPDATE clearances SET status=%s, cleared_date=NULL, valid_until=NULL WHERE student_id=%s",
                (status, student_id), commit=True)
    else:
        cd = 'NOW()' if status == 'Cleared' else 'NULL'
        query_db(
            "INSERT INTO clearances (student_id, status, cleared_date) VALUES (%s,%s,%s)",
            (student_id, status, datetime.now() if status == 'Cleared' else None), commit=True)

# ──────────────────────────────────────────────────────────────
# Routes — Authentication
# ──────────────────────────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = query_db(
            "SELECT * FROM users WHERE username=%s AND is_active=1",
            (username,), fetchone=True)

        if user:
            stored_hash = user['password']
            # Support both bcrypt and plain-text passwords for dev convenience
            valid = False
            try:
                valid = bcrypt.checkpw(password.encode(), stored_hash.encode())
            except Exception:
                valid = (password == stored_hash)

            # Fallback: plain text comparison for dev/demo
            plain_map = {'admin': 'admin123', 'finance': 'finance123', 'registry': 'registry123'}
            if not valid and plain_map.get(username) == password:
                valid = True

            if valid:
                session['user_id']   = user['id']
                session['username']  = user['username']
                session['full_name'] = user['full_name']
                session['role']      = user['role']
                query_db("UPDATE users SET last_login=NOW() WHERE id=%s",
                         (user['id'],), commit=True)
                log_activity(f"User '{username}' logged in", 'Auth')
                flash(f"Welcome back, {user['full_name']}!", 'success')
                return redirect(url_for('dashboard'))

        flash('Invalid username or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    uname = session.get('username', 'Unknown')
    log_activity(f"User '{uname}' logged out", 'Auth')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ──────────────────────────────────────────────────────────────
# Routes — Dashboard
# ──────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    stats = {
        'total_students':   query_db("SELECT COUNT(*) AS c FROM students", fetchone=True)['c'],
        'cleared':          query_db("SELECT COUNT(*) AS c FROM clearances WHERE status='Cleared'", fetchone=True)['c'],
        'not_cleared':      query_db("SELECT COUNT(*) AS c FROM clearances WHERE status='Not Cleared'", fetchone=True)['c'],
        'deferred_pending': query_db("SELECT COUNT(*) AS c FROM deferred_assessments WHERE status='Pending'", fetchone=True)['c'],
        'total_payments':   query_db("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE status='Verified'", fetchone=True)['s'],
        'pending_payments': query_db("SELECT COUNT(*) AS c FROM payments WHERE status='Pending'", fetchone=True)['c'],
        'total_balance':    query_db("SELECT COALESCE(SUM(balance),0) AS s FROM students", fetchone=True)['s'],
    }

    # Dept breakdown for chart
    dept_data = query_db(
        "SELECT department, COUNT(*) AS cnt FROM students GROUP BY department ORDER BY cnt DESC")

    # Monthly payments for chart (last 6 months)
    monthly = query_db(
        """SELECT DATE_FORMAT(payment_date,'%b %Y') AS month,
                  SUM(amount) AS total
           FROM payments WHERE status='Verified'
           AND payment_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
           GROUP BY YEAR(payment_date), MONTH(payment_date)
           ORDER BY payment_date""")

    recent_activity = query_db(
        """SELECT a.action, a.module, a.created_at, u.full_name
           FROM activity_log a LEFT JOIN users u ON a.user_id=u.id
           ORDER BY a.created_at DESC LIMIT 8""")

    recent_payments = query_db(
        """SELECT p.*, s.full_name FROM payments p
           JOIN students s ON p.student_id=s.student_id
           ORDER BY p.created_at DESC LIMIT 5""")

    return render_template('dashboard.html',
                           stats=stats,
                           dept_data=dept_data or [],
                           monthly=monthly or [],
                           recent_activity=recent_activity or [],
                           recent_payments=recent_payments or [])

# ──────────────────────────────────────────────────────────────
# Routes — Students
# ──────────────────────────────────────────────────────────────
@app.route('/students')
@login_required
def students():
    search = request.args.get('search', '')
    dept   = request.args.get('dept', '')
    level  = request.args.get('level', '')

    sql = "SELECT s.*, c.status AS clearance_status FROM students s LEFT JOIN clearances c ON s.student_id=c.student_id WHERE 1=1"
    params = []
    if search:
        sql += " AND (s.student_id LIKE %s OR s.full_name LIKE %s OR s.email LIKE %s)"
        like = f'%{search}%'
        params += [like, like, like]
    if dept:
        sql += " AND s.department=%s"
        params.append(dept)
    if level:
        sql += " AND s.level=%s"
        params.append(level)
    sql += " ORDER BY s.student_id"

    student_list = query_db(sql, params) or []
    departments  = query_db("SELECT DISTINCT department FROM students ORDER BY department") or []
    levels       = query_db("SELECT DISTINCT level FROM students ORDER BY level") or []

    return render_template('students.html',
                           students=student_list,
                           departments=departments,
                           levels=levels,
                           search=search, dept=dept, level=level)

@app.route('/students/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'registry')
def add_student():
    if request.method == 'POST':
        f = request.form
        try:
            query_db(
                """INSERT INTO students
                   (student_id, full_name, gender, department, programme, level,
                    phone, email, academic_year, total_fee, amount_paid)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (f['student_id'], f['full_name'], f['gender'], f['department'],
                 f['programme'], f['level'], f['phone'], f['email'],
                 f['academic_year'], float(f['total_fee']), float(f.get('amount_paid', 0))),
                commit=True)
            sync_clearance(f['student_id'])
            log_activity(f"Added student {f['student_id']} – {f['full_name']}", 'Students')
            flash(f"Student {f['full_name']} added successfully.", 'success')
            return redirect(url_for('students'))
        except Exception as e:
            flash(f'Error adding student: {e}', 'danger')
    return render_template('student_form.html', student=None, action='Add')

@app.route('/students/edit/<sid>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'registry')
def edit_student(sid):
    student = query_db("SELECT * FROM students WHERE student_id=%s", (sid,), fetchone=True)
    if not student:
        flash('Student not found.', 'warning')
        return redirect(url_for('students'))

    if request.method == 'POST':
        f = request.form
        try:
            query_db(
                """UPDATE students SET full_name=%s, gender=%s, department=%s,
                   programme=%s, level=%s, phone=%s, email=%s, academic_year=%s,
                   total_fee=%s, amount_paid=%s WHERE student_id=%s""",
                (f['full_name'], f['gender'], f['department'], f['programme'],
                 f['level'], f['phone'], f['email'], f['academic_year'],
                 float(f['total_fee']), float(f['amount_paid']), sid),
                commit=True)
            sync_clearance(sid)
            log_activity(f"Updated student {sid}", 'Students')
            flash('Student record updated.', 'success')
            return redirect(url_for('students'))
        except Exception as e:
            flash(f'Error updating student: {e}', 'danger')

    return render_template('student_form.html', student=student, action='Edit')

@app.route('/students/delete/<sid>', methods=['POST'])
@login_required
@role_required('admin')
def delete_student(sid):
    query_db("DELETE FROM deferred_assessments WHERE student_id=%s", (sid,), commit=True)
    query_db("DELETE FROM clearances WHERE student_id=%s", (sid,), commit=True)
    query_db("DELETE FROM payments WHERE student_id=%s", (sid,), commit=True)
    query_db("DELETE FROM students WHERE student_id=%s", (sid,), commit=True)
    log_activity(f"Deleted student {sid}", 'Students')
    flash('Student deleted.', 'success')
    return redirect(url_for('students'))

@app.route('/students/view/<sid>')
@login_required
def view_student(sid):
    student  = query_db("SELECT * FROM students WHERE student_id=%s", (sid,), fetchone=True)
    if not student:
        flash('Student not found.', 'warning')
        return redirect(url_for('students'))
    payments  = query_db("SELECT * FROM payments WHERE student_id=%s ORDER BY payment_date DESC", (sid,)) or []
    clearance = query_db("SELECT * FROM clearances WHERE student_id=%s", (sid,), fetchone=True)
    deferred  = query_db("SELECT * FROM deferred_assessments WHERE student_id=%s ORDER BY submitted_at DESC", (sid,)) or []
    return render_template('student_view.html',
                           student=student, payments=payments,
                           clearance=clearance, deferred=deferred)

# ──────────────────────────────────────────────────────────────
# Routes — Payments
# ──────────────────────────────────────────────────────────────
@app.route('/payments')
@login_required
def payments():
    status_filter = request.args.get('status', '')
    search        = request.args.get('search', '')
    sql = """SELECT p.*, s.full_name, s.department FROM payments p
             JOIN students s ON p.student_id=s.student_id WHERE 1=1"""
    params = []
    if status_filter:
        sql += " AND p.status=%s"
        params.append(status_filter)
    if search:
        sql += " AND (p.student_id LIKE %s OR s.full_name LIKE %s OR p.payment_id LIKE %s)"
        like = f'%{search}%'
        params += [like, like, like]
    sql += " ORDER BY p.created_at DESC"
    payment_list = query_db(sql, params) or []
    return render_template('payments.html', payments=payment_list,
                           status_filter=status_filter, search=search)

@app.route('/payments/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'finance')
def add_payment():
    if request.method == 'POST':
        f = request.form
        try:
            amount = float(f['amount'])
            sid    = f['student_id']
            # Generate payment ID
            last = query_db("SELECT payment_id FROM payments ORDER BY id DESC LIMIT 1", fetchone=True)
            num  = 1
            if last:
                try:
                    num = int(last['payment_id'].split('-')[-1]) + 1
                except Exception:
                    num = 1
            pid = f"PAY-{datetime.now().year}-{num:03d}"

            query_db(
                """INSERT INTO payments
                   (payment_id, student_id, amount, semester, payment_date,
                    payment_method, status, reference_no, recorded_by, notes)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (pid, sid, amount, f['semester'], f['payment_date'],
                 f['payment_method'], f['status'], f.get('reference_no',''),
                 session['user_id'], f.get('notes','')),
                commit=True)

            if f['status'] == 'Verified':
                query_db("UPDATE students SET amount_paid = amount_paid + %s WHERE student_id=%s",
                         (amount, sid), commit=True)
                sync_clearance(sid)

            log_activity(f"Payment {pid} recorded for {sid}", 'Payments')
            flash(f'Payment {pid} recorded successfully.', 'success')
            return redirect(url_for('payments'))
        except Exception as e:
            flash(f'Error recording payment: {e}', 'danger')

    students_list = query_db("SELECT student_id, full_name FROM students ORDER BY full_name") or []
    return render_template('payment_form.html', students=students_list)

@app.route('/payments/verify/<int:pid>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def verify_payment(pid):
    pmt = query_db("SELECT * FROM payments WHERE id=%s", (pid,), fetchone=True)
    if pmt and pmt['status'] == 'Pending':
        query_db("UPDATE payments SET status='Verified' WHERE id=%s", (pid,), commit=True)
        query_db("UPDATE students SET amount_paid=amount_paid+%s WHERE student_id=%s",
                 (pmt['amount'], pmt['student_id']), commit=True)
        sync_clearance(pmt['student_id'])
        log_activity(f"Payment {pmt['payment_id']} verified", 'Payments')
        flash('Payment verified and balance updated.', 'success')
    return redirect(url_for('payments'))

@app.route('/payments/reject/<int:pid>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def reject_payment(pid):
    pmt = query_db("SELECT * FROM payments WHERE id=%s", (pid,), fetchone=True)
    if pmt:
        query_db("UPDATE payments SET status='Rejected' WHERE id=%s", (pid,), commit=True)
        log_activity(f"Payment {pmt['payment_id']} rejected", 'Payments')
        flash('Payment marked as rejected.', 'warning')
    return redirect(url_for('payments'))

# ──────────────────────────────────────────────────────────────
# Routes — Clearance
# ──────────────────────────────────────────────────────────────
@app.route('/clearance')
@login_required
def clearance():
    status_filter = request.args.get('status', '')
    search = request.args.get('search', '')
    sql = """SELECT s.*, c.status AS clearance_status, c.cleared_date, c.valid_until, c.notes AS cl_notes
             FROM students s LEFT JOIN clearances c ON s.student_id=c.student_id WHERE 1=1"""
    params = []
    if status_filter:
        sql += " AND c.status=%s"
        params.append(status_filter)
    if search:
        sql += " AND (s.student_id LIKE %s OR s.full_name LIKE %s)"
        like = f'%{search}%'
        params += [like, like]
    sql += " ORDER BY s.student_id"
    items = query_db(sql, params) or []
    return render_template('clearance.html', items=items,
                           status_filter=status_filter, search=search)

@app.route('/clearance/regenerate', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def regenerate_clearances():
    students_all = query_db("SELECT student_id FROM students") or []
    for s in students_all:
        sync_clearance(s['student_id'])
    log_activity("Bulk clearance regeneration", 'Clearance')
    flash('All clearance statuses have been recalculated.', 'success')
    return redirect(url_for('clearance'))

@app.route('/clearance/provisional/<sid>', methods=['POST'])
@login_required
@role_required('admin', 'finance')
def provisional_clearance(sid):
    query_db("UPDATE clearances SET status='Provisional', cleared_date=NOW(), valid_until=DATE_ADD(CURDATE(), INTERVAL 30 DAY) WHERE student_id=%s",
             (sid,), commit=True)
    log_activity(f"Provisional clearance granted for {sid}", 'Clearance')
    flash(f'Provisional clearance granted for student {sid}.', 'info')
    return redirect(url_for('clearance'))

@app.route('/clearance/slip/<sid>')
@login_required
def clearance_slip(sid):
    student   = query_db("SELECT * FROM students WHERE student_id=%s", (sid,), fetchone=True)
    clearance = query_db("SELECT * FROM clearances WHERE student_id=%s", (sid,), fetchone=True)
    if not student or not clearance:
        flash('Record not found.', 'warning')
        return redirect(url_for('clearance'))
    return render_template('clearance_slip.html', student=student, clearance=clearance,
                           generated=datetime.now().strftime('%d %B %Y %H:%M'))

@app.route('/clearance/slip/pdf/<sid>')
@login_required
def clearance_slip_pdf(sid):
    student   = query_db("SELECT * FROM students WHERE student_id=%s", (sid,), fetchone=True)
    clearance = query_db("SELECT * FROM clearances WHERE student_id=%s", (sid,), fetchone=True)
    if not student or not clearance:
        flash('Record not found.', 'warning')
        return redirect(url_for('clearance'))

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4,
                               rightMargin=2*cm, leftMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Header
    title_style = ParagraphStyle('title', parent=styles['Title'],
                                 fontSize=18, textColor=colors.HexColor('#1a3a5c'),
                                 spaceAfter=4)
    sub_style   = ParagraphStyle('sub', parent=styles['Normal'],
                                 fontSize=11, textColor=colors.HexColor('#555'),
                                 alignment=TA_CENTER)
    normal      = ParagraphStyle('n', parent=styles['Normal'], fontSize=11, spaceAfter=6)
    bold_n      = ParagraphStyle('bn', parent=normal, fontName='Helvetica-Bold')

    story.append(Paragraph("LIMKOKWING UNIVERSITY SIERRA LEONE", title_style))
    story.append(Paragraph("Office of Finance & Registry", sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#1a3a5c')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("STUDENT FINANCIAL CLEARANCE CERTIFICATE", bold_n))
    story.append(Spacer(1, 0.4*cm))

    status_color = colors.green if clearance['status'] == 'Cleared' else (
        colors.orange if clearance['status'] == 'Provisional' else colors.red)

    data = [
        ['Student ID',     student['student_id']],
        ['Full Name',      student['full_name']],
        ['Department',     student['department']],
        ['Programme',      student['programme']],
        ['Level',          student['level']],
        ['Academic Year',  student['academic_year']],
        ['Total Fee',      f"Le {float(student['total_fee']):,.2f}"],
        ['Amount Paid',    f"Le {float(student['amount_paid']):,.2f}"],
        ['Outstanding',    f"Le {float(student['balance']):,.2f}"],
        ['Status',         clearance['status'].upper()],
        ['Valid Until',    str(clearance['valid_until']) if clearance['valid_until'] else 'N/A'],
        ['Date Issued',    datetime.now().strftime('%d %B %Y')],
    ]

    tbl = Table(data, colWidths=[5*cm, 10*cm])
    tbl.setStyle(TableStyle([
        ('BACKGROUND',  (0,0), (0,-1), colors.HexColor('#e8f0fe')),
        ('FONTNAME',    (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTSIZE',    (0,0), (-1,-1), 10),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor('#f8f9fc')]),
        ('GRID',        (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('PADDING',     (0,0), (-1,-1), 6),
        ('TEXTCOLOR',   (1,9), (1,9), status_color),
        ('FONTNAME',    (1,9), (1,9), 'Helvetica-Bold'),
        ('FONTSIZE',    (1,9), (1,9), 12),
    ]))
    story.append(tbl)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("_______________________________", normal))
    story.append(Paragraph("Finance Officer Signature", sub_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cccccc')))
    story.append(Paragraph("This certificate is computer-generated. Verify at registry@limkokwing.sl",
                            ParagraphStyle('footer', parent=styles['Normal'],
                                           fontSize=8, textColor=colors.grey,
                                           alignment=TA_CENTER)))

    doc.build(story)
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=clearance_{sid}.pdf'
    return response

# ──────────────────────────────────────────────────────────────
# Routes — Deferred Assessments
# ──────────────────────────────────────────────────────────────
@app.route('/deferred')
@login_required
def deferred():
    status_filter = request.args.get('status', '')
    sql = """SELECT d.*, s.full_name, s.department, s.programme
             FROM deferred_assessments d JOIN students s ON d.student_id=s.student_id
             WHERE 1=1"""
    params = []
    if status_filter:
        sql += " AND d.status=%s"
        params.append(status_filter)
    sql += " ORDER BY d.submitted_at DESC"
    items = query_db(sql, params) or []
    return render_template('deferred.html', items=items, status_filter=status_filter)

@app.route('/deferred/add', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'registry')
def add_deferred():
    if request.method == 'POST':
        f = request.form
        try:
            query_db(
                """INSERT INTO deferred_assessments
                   (student_id, course_code, course_name, semester, reason, status)
                   VALUES (%s,%s,%s,%s,%s,'Pending')""",
                (f['student_id'], f['course_code'], f['course_name'],
                 f['semester'], f['reason']),
                commit=True)
            log_activity(f"Deferred application submitted for {f['student_id']}", 'Deferred')
            flash('Deferred assessment application submitted.', 'success')
            return redirect(url_for('deferred'))
        except Exception as e:
            flash(f'Error: {e}', 'danger')
    students_list = query_db("SELECT student_id, full_name FROM students ORDER BY full_name") or []
    return render_template('deferred_form.html', students=students_list)

@app.route('/deferred/review/<int:did>', methods=['GET', 'POST'])
@login_required
@role_required('admin', 'registry')
def review_deferred(did):
    item = query_db(
        """SELECT d.*, s.full_name, s.programme FROM deferred_assessments d
           JOIN students s ON d.student_id=s.student_id WHERE d.id=%s""",
        (did,), fetchone=True)
    if not item:
        flash('Record not found.', 'warning')
        return redirect(url_for('deferred'))
    if request.method == 'POST':
        new_status = request.form.get('status')
        notes      = request.form.get('review_notes', '')
        query_db(
            """UPDATE deferred_assessments SET status=%s, reviewed_by=%s,
               review_date=NOW(), review_notes=%s WHERE id=%s""",
            (new_status, session['user_id'], notes, did), commit=True)
        log_activity(f"Deferred application {did} marked {new_status}", 'Deferred')
        flash(f'Application {new_status.lower()}.', 'success')
        return redirect(url_for('deferred'))
    return render_template('deferred_review.html', item=item)

# ──────────────────────────────────────────────────────────────
# Routes — Reports
# ──────────────────────────────────────────────────────────────
@app.route('/reports')
@login_required
def reports():
    cleared_count    = query_db("SELECT COUNT(*) AS c FROM clearances WHERE status='Cleared'",       fetchone=True)['c']
    not_cleared      = query_db("SELECT COUNT(*) AS c FROM clearances WHERE status='Not Cleared'",   fetchone=True)['c']
    deferred_total   = query_db("SELECT COUNT(*) AS c FROM deferred_assessments",                    fetchone=True)['c']
    total_collected  = query_db("SELECT COALESCE(SUM(amount),0) AS s FROM payments WHERE status='Verified'", fetchone=True)['s']
    total_outstanding= query_db("SELECT COALESCE(SUM(balance),0) AS s FROM students",               fetchone=True)['s']

    dept_summary = query_db(
        """SELECT s.department,
                  COUNT(s.student_id) AS total,
                  SUM(CASE WHEN c.status='Cleared' THEN 1 ELSE 0 END) AS cleared,
                  COALESCE(SUM(s.balance),0) AS outstanding
           FROM students s LEFT JOIN clearances c ON s.student_id=c.student_id
           GROUP BY s.department ORDER BY s.department""") or []

    return render_template('reports.html',
                           cleared_count=cleared_count,
                           not_cleared=not_cleared,
                           deferred_total=deferred_total,
                           total_collected=total_collected,
                           total_outstanding=total_outstanding,
                           dept_summary=dept_summary)

@app.route('/reports/export/<report_type>/<fmt>')
@login_required
def export_report(report_type, fmt):
    """Export report as CSV or PDF."""
    data   = []
    header = []

    if report_type == 'cleared':
        header = ['Student ID','Full Name','Department','Programme','Level','Cleared Date','Valid Until']
        rows   = query_db(
            """SELECT s.student_id, s.full_name, s.department, s.programme, s.level,
                      c.cleared_date, c.valid_until
               FROM students s JOIN clearances c ON s.student_id=c.student_id
               WHERE c.status='Cleared' ORDER BY s.student_id""") or []
        data   = [[r['student_id'], r['full_name'], r['department'], r['programme'],
                   r['level'], str(r['cleared_date']), str(r['valid_until'])] for r in rows]

    elif report_type == 'pending_payments':
        header = ['Student ID','Full Name','Total Fee','Amount Paid','Balance']
        rows   = query_db(
            "SELECT * FROM students WHERE balance>0 ORDER BY balance DESC") or []
        data   = [[r['student_id'], r['full_name'],
                   f"Le {float(r['total_fee']):,.2f}",
                   f"Le {float(r['amount_paid']):,.2f}",
                   f"Le {float(r['balance']):,.2f}"] for r in rows]

    elif report_type == 'deferred':
        header = ['Student ID','Full Name','Course','Semester','Reason','Status']
        rows   = query_db(
            """SELECT d.student_id, s.full_name, d.course_name, d.semester, d.reason, d.status
               FROM deferred_assessments d JOIN students s ON d.student_id=s.student_id
               ORDER BY d.submitted_at DESC""") or []
        data   = [[r['student_id'], r['full_name'], r['course_name'],
                   r['semester'], r['reason'], r['status']] for r in rows]

    elif report_type == 'finance':
        header = ['Payment ID','Student ID','Full Name','Amount','Semester','Date','Method','Status']
        rows   = query_db(
            """SELECT p.payment_id, p.student_id, s.full_name, p.amount, p.semester,
                      p.payment_date, p.payment_method, p.status
               FROM payments p JOIN students s ON p.student_id=s.student_id
               ORDER BY p.payment_date DESC""") or []
        data   = [[r['payment_id'], r['student_id'], r['full_name'],
                   f"Le {float(r['amount']):,.2f}", r['semester'],
                   str(r['payment_date']), r['payment_method'], r['status']] for r in rows]

    if fmt == 'csv':
        si  = io.StringIO()
        cw  = csv.writer(si)
        cw.writerow(header)
        cw.writerows(data)
        out = make_response(si.getvalue())
        out.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.csv'
        out.headers['Content-type'] = 'text/csv'
        return out

    elif fmt == 'pdf':
        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   rightMargin=1.5*cm, leftMargin=1.5*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []
        title_s = ParagraphStyle('t', parent=styles['Title'], fontSize=14,
                                 textColor=colors.HexColor('#1a3a5c'), spaceAfter=6)
        story.append(Paragraph("LIMKOKWING UNIVERSITY SIERRA LEONE — SLeClear MIS", title_s))
        story.append(Paragraph(f"Report: {report_type.replace('_',' ').title()}  |  Generated: {datetime.now().strftime('%d %B %Y %H:%M')}",
                               styles['Normal']))
        story.append(Spacer(1, 0.4*cm))

        col_w = [(A4[0] - 3*cm) / len(header)] * len(header)
        tbl_data = [header] + data
        tbl = Table(tbl_data, colWidths=col_w, repeatRows=1)
        tbl.setStyle(TableStyle([
            ('BACKGROUND',  (0,0), (-1,0), colors.HexColor('#1a3a5c')),
            ('TEXTCOLOR',   (0,0), (-1,0), colors.white),
            ('FONTNAME',    (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE',    (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f0f4ff')]),
            ('GRID',        (0,0), (-1,-1), 0.4, colors.HexColor('#cccccc')),
            ('PADDING',     (0,0), (-1,-1), 5),
            ('ALIGN',       (0,0), (-1,-1), 'LEFT'),
        ]))
        story.append(tbl)
        doc.build(story)
        buffer.seek(0)
        resp = make_response(buffer.read())
        resp.headers['Content-Type'] = 'application/pdf'
        resp.headers['Content-Disposition'] = f'attachment; filename={report_type}_report.pdf'
        return resp

    flash('Unknown format.', 'danger')
    return redirect(url_for('reports'))

# ──────────────────────────────────────────────────────────────
# Routes — API (JSON endpoints for AJAX)
# ──────────────────────────────────────────────────────────────
@app.route('/api/student/<sid>')
@login_required
def api_student(sid):
    s = query_db("SELECT * FROM students WHERE student_id=%s", (sid,), fetchone=True)
    if s:
        return jsonify({k: str(v) if v is not None else '' for k, v in s.items()})
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/stats')
@login_required
def api_stats():
    return jsonify({
        'total_students': query_db("SELECT COUNT(*) AS c FROM students", fetchone=True)['c'],
        'cleared':        query_db("SELECT COUNT(*) AS c FROM clearances WHERE status='Cleared'", fetchone=True)['c'],
        'pending':        query_db("SELECT COUNT(*) AS c FROM payments WHERE status='Pending'", fetchone=True)['c'],
    })

# ──────────────────────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', code=404, msg='Page not found.'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', code=500, msg='Internal server error.'), 500

# ──────────────────────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
