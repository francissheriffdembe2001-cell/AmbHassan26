"""
create_db.py — Create the `sleclear_db` database and load schema using mysql-connector's multi-statement support.
Usage: python create_db.py
"""
import os
import mysql.connector
from mysql.connector import Error

DB_HOST = 'localhost'
DB_PORT = 3306
DB_USER = 'root'
DB_PASS = ''

SQL_FILE = os.path.join(os.path.dirname(__file__), 'database.sql')


def main():
    try:
        conn = mysql.connector.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS)
        cursor = conn.cursor()
        print('[OK] Connected to MySQL server.')
    except Error as e:
        print(f'[ERROR] Cannot connect to MySQL: {e}')
        return

    if not os.path.exists(SQL_FILE):
        print('[ERROR] SQL file not found:', SQL_FILE)
        return

    with open(SQL_FILE, 'r', encoding='utf-8') as f:
        sql = f.read()

    try:
        # Execute all statements using multi=True
        for result in cursor.execute(sql, multi=True):
            if result.with_rows:
                _ = result.fetchall()
        conn.commit()
        print('[OK] Executed SQL file.')
    except Error as e:
        print('[ERROR] While executing SQL:', e)
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()
