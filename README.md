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
python main.py
```