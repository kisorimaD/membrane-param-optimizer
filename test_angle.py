import subprocess
import numpy as np
from tqdm import tqdm
from logger import log_info, log_error, log_debug
from db_online import create_connection, close_connection, create_table, insert_data, find_data
from settings import settings

conn = create_connection()


def generate_angle_mesh(angle: float):
    subprocess.run(
        ["python3", settings['SCHOOL25_PATH'] + "/generate_ozaki_template.py",
            "--fiber_angle", str(angle)],
        check=True,
        stdout=subprocess.PIPE,
    )

    log_debug(f"Mesh generated with fiber angle: {angle} radians")


def transform_parameters():
    with open("parameters.txt", "r") as f:
        lines = f.readlines()

        return ' '.join(lines).replace('<SCHOOL25_PATH>', settings['SCHOOL25_PATH']).replace("\n", " ")


def run_av_in_cilinder():
    transform_args = transform_parameters()
    # log_debug(f"Transform args: {transform_args}")

    av_proc = subprocess.Popen(
        settings['MEMBRANEMODEL_PATH'] +
        "/cmake-build-Release/benchmarks/IdealSuturedLeaf/av_in_cilinder " + transform_args,
        shell=True,
        stdout=subprocess.PIPE,
        text=True
    )

    out, _ = av_proc.communicate()
    return out


def grep_lines(lines) -> tuple[float, float]:
    billowing_str = lines[-6].split("{")[1].split(",")[0].strip()
    collide_area_str = lines[-4].split("=")[1].split("(")[0].strip()

    try:
        billowing = float(billowing_str)
        collide_area = float(collide_area_str)
    except ValueError:
        raise ValueError("Could not convert billowing or collide area to float\n billowing: {}, collide_area: {}".format(
            billowing_str, collide_area_str))

    return billowing, collide_area


def round_angle(angle: float) -> int:
    # угол хранится в целых градусах * 10
    return int(np.round(angle * 1800 / np.pi))


def analyse():
    angle_num = 10

    angles = np.linspace(0, np.pi / 2, angle_num)

    results = []

    for angle in tqdm(angles):

        if precalc_data := find_data(conn, round_angle(angle)):
            log_debug(f"Precalculated data found for angle: {angle} radians")
            results.append(precalc_data)
        else:
                
            generate_angle_mesh(angle)

            log_debug(f"Running av_in_cilinder for angle: {angle} radians")
            output = run_av_in_cilinder()

            lines = output.splitlines()
            log_debug(f"Output lines: {lines[-6:]}")

            if lines[-1].startswith("ERROR"):
                log_error(f"Error in calculation for angle {angle} radians")
                with open("error_log.txt", "a") as error_file:
                    error_file.write(f"===== Error for angle {angle} radians =====\n")
                    
                    for line in lines:
                        error_file.write(line + "\n")
                    
                    error_file.write("\n\n")

            billowing, collide_area = grep_lines(lines[-6:])

            results.append((angle, billowing, collide_area))

            data = {
                'angle': round_angle(angle),
                'billowing': billowing,
                'collide_area': collide_area,
                'created_by': settings['USERNAME']
            }

            insert_data(conn, data)

    results = np.array(results)


if __name__ == "__main__":
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
