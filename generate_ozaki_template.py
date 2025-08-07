# Файл сгенерирован средствами DeepSeek, используйте на свой страх и риск

import gmsh
import math
import numpy as np
import meshio
import os

import argparse


# fiber_angle = math.pi / 10;        # угол наклона главного направления анизотропии
parser = argparse.ArgumentParser(description="Generate Ozaki template mesh")
parser.add_argument("--fiber_angle", type=float, default=math.pi / 10, help="Angle of the main fiber direction in radians")
parser.add_argument("--template_size", type=float, default=25.0, help="Size of the template (D in mm)")

parser.add_argument("--output_dir", type=str, default="data", help="Directory to save the output mesh file")
parser.add_argument("--output_file", type=str, default="ozaki_template.vtk", help="Name of the output mesh file")

args = parser.parse_args()


# Параметры модели
D = args.template_size                      # [mm], размер шаблона (номер шаблона в терминологии Озаки)
h = 11.0 + math.erf( 2*(D-16.0) )  # [mm], высота дополнительного участка у свободного края
beta = 2.5 + 0.5*math.erf( 2*(D-24.0) ) # [mm], подъём над центром дуги окружности
alpha = 1.0                        # [mm], ширина "ушка" шаблона
s = 0.0                            # [mm], отсекаемая в ходе пришивания ширина
m = 0.0                            # [mm], утолщение "ушка" шаблона
w = 0.0                            # [mm], дополнительное удлинение радиуса дуги шаблона

dh = 1.0                           # [mm], рекомендуемый шаг сетки


fiber_angle = args.fiber_angle      # угол наклона главного направления анизотропии

target_dir = args.output_dir        # целевая папка для сохранения результата
res_file = args.output_file         # имя файла для сохранения финальной .vtk сетки

# Схема геометрии:
#       A
#     E   B
#      D C  

# Вычисление координат
r0 = D/2 + w
O = np.array([0, 0, 0])
A = np.array([0.0, h + beta, 0.0])
B1 = np.array([r0 + alpha, h, 0.0])
B2 = B1 + m * (B1 - A)/np.linalg.norm(B1 - A);
gamma = math.atan2(B2[0], -B2[1]) - math.acos(r0 / np.linalg.norm(B2 - O));
B = B2 - s * (B2 - A)/np.linalg.norm(B2 - A);
r1 = r0 - s
C = np.array([r1 * math.sin(gamma), -r1 * math.cos(gamma), 0.0])
D = np.array([-C[0], C[1], 0.0])
E = np.array([-B[0], B[1], 0.0])


# Инициализация GMSH
gmsh.initialize()
# gmsh.option.setNumber("General.Terminal", 0)  # Отключаем вывод в консоль
gmsh.model.add("triangular_mesh")

# Создание точек
pA = gmsh.model.geo.addPoint(A[0], A[1], A[2], dh)
pB = gmsh.model.geo.addPoint(B[0], B[1], B[2], dh)
pC = gmsh.model.geo.addPoint(C[0], C[1], C[2], dh)
pD = gmsh.model.geo.addPoint(D[0], D[1], D[2], dh)
pE = gmsh.model.geo.addPoint(E[0], E[1], E[2], dh)
pO = gmsh.model.geo.addPoint(O[0], O[1], O[2], dh)

# Создание линий
line_AB = gmsh.model.geo.addLine(pA, pB)
line_BC = gmsh.model.geo.addLine(pB, pC)
circle_CD = gmsh.model.geo.addCircleArc(pC, pO, pD)
line_DE = gmsh.model.geo.addLine(pD, pE)
line_EA = gmsh.model.geo.addLine(pE, pA)

# Создание поверхности
curve_loop = gmsh.model.geo.addCurveLoop([line_AB, line_BC, circle_CD, line_DE, line_EA])
surface = gmsh.model.geo.addPlaneSurface([curve_loop])

# Синхронизация
gmsh.model.geo.synchronize()

# Физические группы
    # Точки
B_ID = 7; E_ID = 3; FREE_ID = 1; SUTURED_ID = 2; NONE_ID = 0;
gmsh.model.addPhysicalGroup(0, [pB], B_ID) # "Right"
gmsh.model.addPhysicalGroup(0, [pE], E_ID) # "Left"

    # Границы
gmsh.model.addPhysicalGroup(1, [line_EA, line_AB], FREE_ID)               # "Free boundary"
gmsh.model.addPhysicalGroup(1, [line_BC, circle_CD, line_DE], SUTURED_ID) # "Sutured boundary"
    
    #Поверхность
gmsh.model.addPhysicalGroup(2, [surface], NONE_ID) # "Surface"

# Настройки сетки
gmsh.option.setNumber("Mesh.CharacteristicLengthMin", 0.9*dh)
gmsh.option.setNumber("Mesh.CharacteristicLengthMax", 1.2*dh)
gmsh.option.setNumber("Mesh.Optimize", 1)
gmsh.option.setNumber("Mesh.Algorithm", 6)

# Синхронизация и генерация сетки
gmsh.model.geo.synchronize()
gmsh.model.mesh.generate(2)

# Сохранение gmsh-сетки <<< не годится по формату хранения для симулятора
# gmsh.write("triangular_mesh.vtk")

# Запуск GUI для просмотра
# gmsh.fltk.run()

# Конвертируем gmsh-сетку в meshio-сетку
# Получение данных сетки
node_tags, node_coords, _ = gmsh.model.mesh.getNodes()
points = np.array(node_coords).reshape(-1, 3)

# Получение элементов и фильтрация треугольников
element_types, element_tags, element_node_tags = gmsh.model.mesh.getElements()
triangles = []
for elem_type, tags, node_tags_list in zip(element_types, element_tags, element_node_tags):
    if elem_type == 2:  # Треугольные элементы
        triangles.append(node_tags_list)
triangles = np.array(triangles[0], dtype=np.int64).reshape(-1, 3)

# Получение физических групп
physical_groups = {}
for dim, tag in gmsh.model.getPhysicalGroups():
    entities = gmsh.model.getEntitiesForPhysicalGroup(dim, tag)
    
    group_nodes = set()
    for entity in entities:
        node_tags_ent, _, _ = gmsh.model.mesh.getNodes(dim, entity, includeBoundary = True)
        group_nodes.update(node_tags_ent)
    
    physical_groups[tag] = (dim, tag, group_nodes)

# Финализация GMSH
gmsh.finalize()

# Создаем массив тегов для узлов
v_label = np.zeros(len(node_tags), dtype=int)
node_id_map = {tag: i for i, tag in enumerate(node_tags)}

# Приоритетная разметка (точки > границы)
# 1. Точки
if B_ID in physical_groups:
    for node_tag in physical_groups[B_ID][2]:
        #if node_tag in node_id_map:
            idx = node_id_map[node_tag]
            v_label[idx] = B_ID

if E_ID in physical_groups:
    for node_tag in physical_groups[E_ID][2]:
        #if node_tag in node_id_map:
            idx = node_id_map[node_tag]
            v_label[idx] = E_ID

# 2. Границы
if FREE_ID in physical_groups:
    for node_tag in physical_groups[FREE_ID][2]:
        #if node_tag in node_id_map:
            idx = node_id_map[node_tag]
            if v_label[idx] == 0:  # Перезаписываем только если не помечено как точка
                v_label[idx] = FREE_ID

if SUTURED_ID in physical_groups:
    for node_tag in physical_groups[SUTURED_ID][2]:
        #if node_tag in node_id_map:
            idx = node_id_map[node_tag]
            if v_label[idx] == 0:
                v_label[idx] = SUTURED_ID

# Фильтрация точек: удаляем неиспользуемые в элементах
used_nodes = set(triangles.flatten())
used_indices = [i for i, tag in enumerate(node_tags) if tag in used_nodes]

# Проверка на соответствие элементов и точек
if len(used_indices) == 0:
    raise ValueError("No matching nodes between elements and points")

# Создаем новые массивы только с используемыми точками
filtered_points = points[used_indices]
filtered_labels = v_label[used_indices]

# Переиндексация элементов
tag_to_new_index = {tag: new_idx for new_idx, tag in enumerate(np.array(node_tags)[used_indices])}
filtered_triangles = np.vectorize(tag_to_new_index.get)(triangles)

# Создаем meshio-сетку
mesh = meshio.Mesh(
    points=filtered_points,
    cells=[("triangle", filtered_triangles)],
    point_data={"v:boundary_lbl": filtered_labels}
)

def add_direction_tag(mesh, tag_name, compute_vector_at_point):
    """
    Добавляет тег f:direction с использованием пользовательской функции
    
    Параметры:
    mesh : meshio.Mesh - входная сетка
    tag_name : str - имя нового тега
    compute_vector_at_point : function - функция, принимающая (index, centroid, normal) 
                            и возвращающая вектор для треугольника
    """
    # Проверяем наличие треугольных элементов
    if not mesh.cells or mesh.cells[0].type != "triangle":
        raise ValueError("Сетка не содержит треугольных элементов или первый блок не треугольники")
    
    # Предполагаем, что есть только один блок треугольников
    triangles = mesh.cells[0].data
    n_triangles = len(triangles)
    
    # Получаем все точки треугольников за одну операцию
    tri_points = mesh.points[triangles]  # Форма: (n_tri, 3, 3)
    
    # Вычисляем центроиды для всех треугольников
    centroids = np.mean(tri_points, axis=1)  # Форма: (n_tri, 3)
    
    # Вычисляем векторы сторон треугольников
    v1 = tri_points[:, 1] - tri_points[:, 0]
    v2 = tri_points[:, 2] - tri_points[:, 0]
    
    # Вычисляем нормали для всех треугольников
    normals = np.cross(v1, v2)  # Форма: (n_tri, 3)
    
    # Вычисляем длины нормалей
    norms = np.linalg.norm(normals, axis=1, keepdims=True)
    
    # Защита от деления на ноль
    norms_safe = np.where(norms == 0, 1, norms)
    
    # Вычисляем единичные нормали
    unit_normals = normals / norms_safe
    
    # Применяем пользовательскую функцию для каждого треугольника
    directions = np.zeros((n_triangles, 3), dtype=np.float64)
    
    for i in range(n_triangles):
        # Вызываем пользовательскую функцию
        directions[i] = compute_vector_at_point(
            index=i,
            centroid=centroids[i],
            normal=unit_normals[i]
        )
    
    # Добавляем тег в cell_data
    mesh.cell_data[tag_name] = [directions]

def write_legacy_vtk_without_offsets(
    filename,
    points,
    cells,  # Для треугольников: массив формы (n_cells, 3)
    point_data=None,
    cell_data=None,
    cell_type=5,  # Тип 5 = треугольник в VTK
    title="Created by VTK Writer",
    reverse=False
):
    """
    Записывает сетку в VTK Legacy формат без использования OFFSETS в блоке CELLS
    
    Параметры:
    filename (str): Имя выходного файла
    points (np.array): Массив точек формы (n_points, 3)
    cells (np.array): Массив ячеек (треугольников) формы (n_cells, 3)
    point_data (dict): Словарь точечных данных (необязательный)
    cell_data (dict): Словарь ячеечных данных (необязательный)
    cell_type (int): Тип ячейки VTK (по умолчанию 5 - треугольник)
    title (str): Заголовок файла
    reverse (bool): Если True, индексы узлов записываются в обратном порядке
    """
    n_points = len(points)
    n_cells = len(cells)
    
    with open(filename, "w") as f:
        # Заголовок файла
        f.write("# vtk DataFile Version 3.0\n")
        f.write(f"{title}\n")
        f.write("ASCII\n")
        f.write("DATASET UNSTRUCTURED_GRID\n\n")
        
        # Запись точек
        f.write(f"POINTS {n_points} double\n")
        for point in points:
            f.write(f"{point[0]} {point[1]} {point[2]}\n")
        f.write("\n")
        
        # Запись ячеек (без OFFSETS)
        total_entries = n_cells * (1 + cells.shape[1])  # 1 + количество вершин в ячейке
        f.write(f"CELLS {n_cells} {total_entries}\n")
        for cell in cells:
            if reverse:
                # Инвертируем порядок индексов
                cell_indices = cell[::-1]
            else:
                cell_indices = cell
            # Формат: [количество_вершин, индекс1, индекс2, ...]
            f.write(f"{cells.shape[1]} {' '.join(map(str, cell_indices))}\n")
        f.write("\n")
        
        # Запись типов ячеек
        f.write(f"CELL_TYPES {n_cells}\n")
        for _ in range(n_cells):
            f.write(f"{cell_type}\n")
        f.write("\n")
        
        # Запись точечных данных
        if point_data:
            f.write(f"POINT_DATA {n_points}\n")
            for name, data in point_data.items():
                _write_data(f, name, data)
        
        # Запись ячеечных данных
        if cell_data:
            f.write(f"CELL_DATA {n_cells}\n")
            for name, data in cell_data.items():
                # Данные ячеек могут быть вложены в списки (по блокам), 
                # но у нас только один блок
                if isinstance(data, list) and len(data) == 1:
                    _write_data(f, name, data[0])
                else:
                    _write_data(f, name, data)

def _write_data(f, name, data):
    """Вспомогательная функция для записи данных в VTK формат"""
    # Определяем тип данных
    if hasattr(data, 'dtype'):
        dtype = data.dtype
    else:
        dtype = np.array(data).dtype
        
    if dtype.kind in {'i', 'u'}:
        data_type = "int"
    elif dtype.kind == 'f':
        data_type = "double"
    else:
        data_type = "double"  # Значение по умолчанию
    
    # Определяем размерность данных
    if len(data.shape) == 1 or (len(data.shape) == 2 and data.shape[1] == 1):
        # Скалярные данные
        f.write(f"SCALARS {name} {data_type} 1\n")
        f.write("LOOKUP_TABLE default\n")
        for value in data.ravel():
            f.write(f"{value}\n")
        f.write("\n")
    elif len(data.shape) == 2 and data.shape[1] == 3:
        # Векторные данные
        f.write(f"VECTORS {name} {data_type}\n")
        for vector in data:
            f.write(f"{vector[0]} {vector[1]} {vector[2]}\n")
        f.write("\n")
    else:
        # Для неизвестных форматов сохраняем как скалярные данные
        f.write(f"SCALARS {name} {data_type} 1\n")
        f.write("LOOKUP_TABLE default\n")
        for value in data.ravel():
            f.write(f"{value}\n")
        f.write("\n")

# создание главного направления анизотропии
def fiber_field(index, centroid, normal):
    return np.array([math.cos(fiber_angle), math.sin(fiber_angle), 0]);
add_direction_tag(mesh, "f:fiber_f", fiber_field)

# создание побочного направления анизотропии
def orthogonal_fiber_field(index, centroid, normal):
    fiber = mesh.cell_data["f:fiber_f"][0][index]
    res = np.cross(normal, fiber)
    res /= np.linalg.norm(res);
    return res
add_direction_tag(mesh, "f:fiber_s", orthogonal_fiber_field)

os.makedirs(target_dir, exist_ok=True) 
# Сохраняем в ASCII формате
# mesh.write(
#      os.path.join(target_dir, res_file),
#      file_format="vtk",  # Формат VTK
#      #binary=False        # ASCII вместо бинарного <<< будет неподдерживаемый формат
# )

# запись в файл
write_legacy_vtk_without_offsets(
        filename=os.path.join(target_dir, res_file),
        points=mesh.points,
        cells=mesh.cells[0].data,
        point_data=mesh.point_data,
        cell_data=mesh.cell_data,
        title="Created by custom VTK writer"
    )
