import logging
import sys
from pathlib import Path

def setup_logging(log_file="vkinder.log", log_level=logging.INFO):
    """
    Настраивает корневой логгер.
    - Вывод в консоль (INFO и выше)
    - Вывод в файл (DEBUG и выше, с ротацией по времени)
    """
    # Удаляем все существующие обработчики, чтобы избежать дублирования
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Создаём форматтер
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Обработчик для консоли (stderr) – уровень INFO и выше
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Обработчик для файла – уровень DEBUG и выше
    # Файл будет храниться в папке logs (создаём, если её нет)
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_path = log_dir / log_file
    file_handler = logging.FileHandler(file_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Обработчики фильтруют по своим уровням
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    return root_logger
