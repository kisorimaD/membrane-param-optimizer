import os
import re
import subprocess
from datetime import datetime
from settings import settings
from tqdm import tqdm
import mysql.connector

def grep_lines(lines) -> float:
    heff = ""

    try:
        heff = lines[-9].split("Heff =")[1].split(",")[0].strip()

        heff = float(heff)
    except IndexError as e:
        print('\n'.join(lines[-30:]))
        # raise e
    
    return heff

directory = 'result/'
binary_path = settings['MEMBRANEMODEL_PATH'] + '/cmake-build-Release/benchmarks/IdealSuturedLeaf/av_in_cilinder'
timestamp_cutoff = datetime(2025, 8, 8, 11, 40)



filename_pattern = re.compile(
    r"A_(?P<A>\d+)_P_(?P<P>\d+)_D_(?P<D>\d+)_NCC_closure\.vtk"
)


result = dict()

for filename in tqdm(os.listdir(directory)):
    match = filename_pattern.match(filename)
    if not match:
        continue

    filepath = os.path.join(directory, filename)
    if not os.path.isfile(filepath):
        continue

    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    if mtime <= timestamp_cutoff:
        continue

    a = match.group("A")
    p = match.group("P")
    d = match.group("D")

    params_raw = f"""
"--cusp_meshes" "{directory}/{filename}" "" ""
"--init_x_tag" "v:init_x" "--start_x_tag" "self:point"
"--suture_lines" "{settings['SCHOOL25_PATH']}/data/NCC.pp" "{settings['SCHOOL25_PATH']}/data/RCC.pp" "{settings['SCHOOL25_PATH']}/data/LCC.pp"
"--cusp_names" "NCC" "RCC" "LCC"
"--energy" "potentials/Potential_{settings['POTENTIAL_CHOICE']}.energy"
"--regen_expr" "false"
"--target" ""
"--save_meshes" "false"
"--skip_suture" "true"
"--skip_solution" "true"
"--save_coapt_zones" "false"
"--skip_process" "false"
"""
    params = params_raw.strip().replace("\n", " ")

    try:
        av_proc = subprocess.Popen(
            binary_path + " " + params,
            shell=True,
            stdout=subprocess.PIPE,
            text=True
        )
        output, _ = av_proc.communicate()
        heff = grep_lines(output.splitlines())
        if heff == '':
            continue
        result[(a, p, d)] = heff


    except subprocess.CalledProcessError as e:
        print(f"  ❌ Ошибка при запуске на {filename}: {e}")


user_name = "damir"

MYSQL_CONFIG = {
    'host': '84.54.47.92',
    'user': 'user',
    'password': 'stvorkisirius',
    'database': 'sim_data'
}

def create_connection():
    conn = None

    conn = mysql.connector.connect(**MYSQL_CONFIG)

    return conn

def close_connection(conn):
    if conn and conn.is_connected():
        conn.close()

def create_table(conn):
    sql = f''' 
    CREATE TABLE IF NOT EXISTS heff_data (
        id INT AUTO_INCREMENT PRIMARY KEY,
        angle INT NOT NULL,
        D INT NOT NULL,
        heff DOUBLE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        created_by VARCHAR(255) DEFAULT 'unknown'
    ); '''
    try:
        cur = conn.cursor()
        cur.execute(sql)
    
    finally:
        if cur:
            cur.close()

def insert_data(conn, data):
    sql = f''' 
    INSERT INTO heff_data(angle, D, heff, created_by)
    VALUES (%s, %s, %s, %s)
    '''
    try:
        cur = conn.cursor()
        cur.execute(sql, (data['angle'], data['D'], data['heff'], data['created_by']))
        conn.commit()
    finally:
        if cur:
            cur.close()


def find_data(conn, angle, D):
    sql = f''' SELECT * FROM heff_data WHERE angle = %s AND D = %s '''
    try:
        cur = conn.cursor(buffered=True)
        cur.execute(sql, (angle, D))
        result = cur.fetchone()
        return result
    finally:
        if cur:
            cur.close()

conn = create_connection()
create_table(conn)

for key, value in result.items():
    a, p, d = key

    a = float(a)
    p = int(p)
    d = int(d)

    if not find_data(conn, a, d):

        print(f"A: {a}, P: {p}, D: {d} -> Heff: {value}")

        insert_data(conn, {
            'angle': a,
            'D': d,
            'heff': value,
            'created_by': user_name
        })

        print(f"Insert data for A{a}P{p}D{d}")
    else:
        print(f"Data for A{a}P{p}D{d} already exists.")