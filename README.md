### Инструкция по установке
1. Установите окружение venv
```bash
python3 -m venv .venv
```

2. Активируйте окружение
```bash
source .venv/bin/activate
```

3. Установите зависимости
```bash
pip install -r requirements.txt
```

4. Создайте папку result, если она не существует
```bash
mkdir -p result
```

5. Измените конфигурационный файл `settings.ini` в соответствии с вашими настройками (путь к `school25` и т.д.)

### Запуск

```bash
python test_angle.py
```

#### Ошибки

Если возникают ошибки с gmsh типо
```
  File "/usr/lib/python3.12/ctypes/__init__.py", line 379, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libXcursor.so.1: cannot open shared object file: No such file or directory
```

то установите недостающие библиотеки:
```bash
apt install libxrender1 libx11-6 libxext6 libxcursor1 libxft2 libxfixes3 libxi6 libglu1-mesa libxinerama1
```
 