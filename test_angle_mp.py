import subprocess
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
from logger import log_info, log_error, log_debug
from db_online import create_connection, close_connection, create_table
from settings import settings
from concurrent.futures import ProcessPoolExecutor, as_completed
import random
import os

conn = create_connection()


def gen_random_name():
    return f"ozaki_template_{random.randint(1000, 9999)}.vtk"


# def gen_random_core_name():
#     return f"core_{random.randint(1000, 9999)}"


def generate_angle_mesh(angle: float, D: int, ozaki_template_name: str):
    subprocess.run(
        ["python3", "generate_ozaki_template.py",
         "--fiber_angle", str(angle),
         "--template_size", str(D),
         "--output_dir", "/tmp/data",
         "--output_file", ozaki_template_name],
        check=True,
        stdout=subprocess.PIPE,
    )

    log_debug(f"Mesh generated with fiber angle: {angle} radians")


def transform_parameters(ozaki_template_name: str, angle: float):
    with open("parameters_mp.txt", "r") as f:
        lines = f.readlines()

        return ' '.join(lines) \
            .replace('<SCHOOL25_PATH>', settings['SCHOOL25_PATH']) \
            .replace('<OZAKI_TEMPLATE_NAME>', ozaki_template_name) \
            .replace('<POTENTIAL_CHOICE>', str(settings['POTENTIAL_CHOICE'])).strip() \
            .replace('<FIBER_ANGLE>', str(round_angle(angle))) \
            .replace('<D>', str(settings['D'])) \
            .replace("\n", " ")


def run_av_in_cilinder(ozaki_template_name: str, angle: float):
    transform_args = transform_parameters(ozaki_template_name, angle)

    av_proc = subprocess.Popen(
        f"{settings['MEMBRANEMODEL_PATH']}/cmake-build-Release/benchmarks/IdealSuturedLeaf/av_in_cilinder {transform_args}",
        shell=True,
        stdout=subprocess.PIPE,
        text=True
    )

    out, _ = av_proc.communicate()

    return out


def grep_lines(lines) -> tuple[float, float, float, float, bool]:
    hcoapt_str = lines[-10].split("Hcoapt =")[1].split(",")[0].strip()
    hcentral_str = lines[-10].split("Hcentral =")[1].strip()
    is_closed_str = lines[-9].split("isClosed =")[1].strip()
    billowing_str = lines[-6].split("{")[1].split(",")[0].strip()
    collide_area_str = lines[-4].split("=")[1].split("(")[0].strip()

    try:
        hcoapt = float(hcoapt_str)
        hcentral = float(hcentral_str)
        is_closed = is_closed_str.lower() == "true"
        billowing = float(billowing_str)
        collide_area = float(collide_area_str)
    except ValueError:
        raise ValueError(
            f"Could not convert values to float/bool\n"
            f"hcoapt: {hcoapt_str}, hcentral: {hcentral_str}, isClosed: {is_closed_str}, "
            f"billowing: {billowing_str}, collide_area: {collide_area_str}"
        )

    return hcoapt, hcentral, billowing, collide_area, is_closed


def round_angle(angle: float) -> int:
    # угол хранится в целых градусах * 10
    return int(np.round(angle * 1800 / np.pi))


def process_angle(angle, D: int):
    from db_online import create_connection, insert_data, find_data
    from settings import settings
    from logger import log_debug, log_error

    ozaki_template_name = gen_random_name()

    conn_local = create_connection()
    try:
        if precalc_data := find_data(conn_local, round_angle(angle), D):
            log_debug(f"Precalculated data found for angle: {angle} radians")
            return precalc_data
        else:
            generate_angle_mesh(angle, D, ozaki_template_name)
            log_debug(f"Running av_in_cilinder for angle: {angle} radians")
            output = run_av_in_cilinder(ozaki_template_name, angle)
            lines = output.splitlines()
            log_debug(f"Output lines: {lines[-30:]}")
            if lines and lines[-1].startswith("ERROR"):
                log_error(f"Error in calculation for angle {angle} radians")
                with open("error_log.txt", "a") as error_file:
                    error_file.write(
                        f"===== Error for angle {angle} radians =====\n")
                    for line in lines:
                        error_file.write(line + "\n")
                    error_file.write("\n\n")
            hcoapt, hcentral, billowing, collide_area, is_closed = grep_lines(
                lines[-12:])

            data = {
                'angle': round_angle(angle),
                'D': D,
                'hcoapt': hcoapt,
                'hcentral': hcentral,
                'billowing': billowing,
                'collide_area': collide_area,
                'is_closed': is_closed,
                'created_by': settings['USERNAME']
            }
            insert_data(conn_local, data)
            return (angle, billowing, collide_area)
    finally:
        close_connection(conn_local)


def analyse():
    angle_num = int(settings['ANGLE_NUM'])
    angle_start = float(eval(settings['ANGLE_START'], {"PI": np.pi}))
    angle_end = float(eval(settings['ANGLE_END'], {"PI": np.pi}))

    D = int(settings['D'])


    log_info(
        f"Angle start: {angle_start} radians, Angle end: {angle_end} radians, Angle num: {angle_num}, D: {D}")

    angles = np.linspace(angle_start, angle_end, angle_num)

    log_debug(f"WORKERS: {settings['WORKERS']}")

    with ProcessPoolExecutor(max_workers=int(settings['WORKERS'])) as executor:
        futures = [executor.submit(process_angle, angle, D) for angle in angles]
        for f in tqdm(as_completed(futures), total=len(futures)):
            try:
                f.result()
            except Exception as e:
                log_error(f"Exception in process: {e}")


def create_dirs():
    import os
    dirs = ["/tmp/data", "/tmp/cores"]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d)
            log_info(f"Created directory: {d}")
        else:
            log_info(f"Directory already exists: {d}")


if __name__ == "__main__":
    create_dirs()
    create_table(conn)
    log_info("Starting analysis")

    try:
        analyse()
        log_info("Analysis completed successfully")
    except Exception as e:
        log_error(f"An error occurred during analysis: {e}")
        raise e
    finally:
        close_connection(conn)
        log_info("Database connection closed")
        log_info("Script execution finished")

        # clean up temporary files
        subprocess.run(["rm", "-rf", "/tmp/data"], check=True)
        subprocess.run(["rm", "-rf", "/tmp/cores"], check=True)
