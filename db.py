import sqlite3
from logger import log_info, log_error, log_debug
from settings import settings

user_name = "damir"

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        log_info("Connection established")
    except sqlite3.Error as e:
        log_error(e)
    return conn

def close_connection(conn):
    if conn:
        conn.close()
        log_info("Connection closed")

def create_table(conn):
    sql = f''' CREATE TABLE IF NOT EXISTS results_raw_{settings['POTENTIAL_CHOICE']}_D (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                angle INTEGER NOT NULL,
                D INTEGER NOT NULL,
                billowing REAL NOT NULL,
                collide_area REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT DEFAULT 'unknown'
              ); ''' # угол - целое число (в градусах * 10)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        log_info("Table created successfully")
    except sqlite3.Error as e:
        log_error(e)


def insert_data(conn, data):
    sql = f''' INSERT INTO results_raw_{settings['POTENTIAL_CHOICE']}_D(angle, D, billowing, collide_area, created_by)
              VALUES(?,?,?,?,?) '''

    cur = conn.cursor()
    cur.execute(sql, (data['angle'], data['D'], data['billowing'], data['collide_area'], data['created_by']))
    conn.commit()
    log_debug(f"Data inserted: {data}")


def find_data(conn, angle, D) -> tuple:
    sql = f''' SELECT * FROM results_raw_{settings['POTENTIAL_CHOICE']}_D WHERE angle = ? AND D = ? '''
    cur = conn.cursor()
    cur.execute(sql, (angle, D))
    return cur.fetchone()