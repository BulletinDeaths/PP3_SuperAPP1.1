"""
Вспомогательные функции для определения путей к файлам данных проекта.

Все пути строятся от корня пакета SuperAPP (родитель папки core),
поэтому работают независимо от того, откуда запущен main.py.
"""

import os

_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
SUPERAPP_DIR = os.path.dirname(_CORE_DIR)
DATA_DIR = os.path.join(SUPERAPP_DIR, "data")


def data_path(filename: str) -> str:
    """Возвращает абсолютный путь к файлу в папке data/."""
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, filename)