import os
import re
import subprocess
from datetime import datetime
from settings import settings

directory = 'result/'
binary_path = settings['MEMBRANEMODEL_PATH'] + '/cmake-build-Release/benchmarks/IdealSuturedLeaf/av_in_cilinder'
timestamp_cutoff = datetime(2025, 8, 8, 11, 40)



filename_pattern = re.compile(
    r"A_(?P<A>\d+)_P_(?P<P>\d+)_D_(?P<D>\d+)_NCC_closure\.vtk"
)

for filename in os.listdir(directory):
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

    print(f"Обработка файла: {filename}")
    print(f"A={a}, P={p}, D={d}, mtime={mtime}")

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

    # Запуск бинарника с аргументами
    try:
        subprocess.run(
            binary_path + " " + params,
            shell=True,
            check=True
        )
        print(f"  ✔️ Успешно запущено")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Ошибка при запуске на {filename}: {e}")
    finally:
        print("==============\n")