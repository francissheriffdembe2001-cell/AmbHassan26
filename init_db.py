"""
init_db.py — Run this ONCE to create the database and load sample data.
Usage:  python init_db.py
"""

import mysql.connector
from mysql.connector import Error
import os

DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASS = ''           # XAMPP default: blank password

SQL_FILE = os.path.join(os.path.dirname(__file__), 'database.sql')


def run():
    print("=" * 56)
    print("  SLeClear MIS — Database Initialisation")
    print("  Limkokwing University Sierra Leone")
    print("=" * 56)

    try:
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASS
        )
        cursor = conn.cursor()
        print("[OK] Connected to MySQL server.")
    except Error as e:
        print(f"[ERROR] Cannot connect to MySQL: {e}")
        print("       Make sure XAMPP MySQL service is running.")
        return

    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        raw = f.read()

    # Split on semicolons but skip empty statements
    statements = [s.strip() for s in raw.split(';') if s.strip() and not s.strip().startswith('--')]

    ok = 0
    for stmt in statements:
        try:
            cursor.execute(stmt)
            conn.commit()
            ok += 1
        except Error as e:
            # Duplicate entry warnings are fine on re-run
            if e.errno not in (1062, 1050, 1007):
                print(f"  [WARN] {e.msg[:80]}")

    print(f"[OK] Executed {ok} SQL statements.")

    # Verify
    cursor.execute("USE sleclear_db")
    cursor.execute("SELECT COUNT(*) FROM students")
    sc = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM payments")
    pc = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users")
    uc = cursor.fetchone()[0]

    print(f"[OK] Database ready:  {uc} users | {sc} students | {pc} payments")
    print()
    print("  Default login credentials:")
    print("    admin    / admin123    (Administrator)")
    print("    finance  / finance123  (Finance Officer)")
    print("    registry / registry123 (Registry Officer)")
    print()
    print("  Start the app:  python app.py")
    print("  Open browser:   http://localhost:5000")
    print("=" * 56)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    run()
