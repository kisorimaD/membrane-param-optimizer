import mysql.connector
from mysql.connector import Error
from logger import log_info, log_error, log_debug
from settings import settings

user_name = "damir"

MYSQL_CONFIG = {
    'host': '84.54.47.92',
    'user': 'user',
    'password': 'stvorkisirius',
    'database': 'sim_data'
}

def create_connection():
    conn = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        if conn.is_connected():
            log_info("Connection to MySQL established")
    except Error as e:
        log_error(f"MySQL connection error: {e}")
    return conn

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()
        log_info("Connection to MySQL closed")

def create_table(conn):
    sql = f''' 
    CREATE TABLE IF NOT EXISTS results_raw_{settings['POTENTIAL_CHOICE']}_D_new (
        id INT AUTO_INCREMENT PRIMARY KEY,
        angle INT NOT NULL,
        D INT NOT NULL,
        hcoapt DOUBLE NOT NULL,
        hcentral DOUBLE NOT NULL,
        billowing DOUBLE NOT NULL,
        collide_area DOUBLE NOT NULL,
        is_closed BOOLEAN NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(255) DEFAULT 'unknown'
    ); '''
    try:
        cur = conn.cursor()
        cur.execute(sql)
        log_info("Table created successfully in MySQL")
    except Error as e:
        log_error(f"MySQL table creation error: {e}")
    finally:
        if cur:
            cur.close()

def insert_data(conn, data):
    sql = f''' 
    INSERT INTO results_raw_{settings['POTENTIAL_CHOICE']}_D_new(angle, D, hcoapt, hcentral, billowing, collide_area, is_closed, created_by)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    '''
    try:
        cur = conn.cursor()
        cur.execute(sql, (data['angle'], data['D'], data['hcoapt'], data['hcentral'], data['billowing'], data['collide_area'], data['is_closed'], data['created_by']))
        conn.commit()
        log_debug(f"Data inserted: {data}")
    except Error as e:
        log_error(f"MySQL insert error: {e}")
    finally:
        if cur:
            cur.close()

def find_data(conn, angle, D) -> tuple:
    sql = f''' SELECT * FROM results_raw_{settings['POTENTIAL_CHOICE']}_D_new WHERE angle = %s AND D = %s '''
    log_debug(f"Finding data for angle: {angle}, D: {D}")
    try:
        cur = conn.cursor(buffered=True)
        cur.execute(sql, (angle, D))
        result = cur.fetchone()
        return result
    except Error as e:
        log_error(f"MySQL select error: {e}")
        return None
    finally:
        if cur:
            cur.close()
