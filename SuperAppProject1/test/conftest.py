"""
Общий conftest.py для всех тестов.
"""
import sys

import pytest
from PyQt6.QtWidgets import QApplication


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Не вызываем app.quit() — pytest сам завершит процесс. Принудительное
    # завершение Qt-приложения между тестами может привести к крашам при
    # повторном использовании виджетов в рамках одной сессии.
