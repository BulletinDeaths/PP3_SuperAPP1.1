import os
import sys

sys.path.append(os.path.abspath("../../"))

import unittest
from unittest.mock import patch, MagicMock
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from SuperAppProject1.SuperAPP.models.habit_tracker_model import HabitTrackerModel
from SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget import HabitTrackerWidget

app = QApplication([])


class TestHabitTrackerWidget(unittest.TestCase):
    def setUp(self):
        self.model = HabitTrackerModel("tests/data/test_habits.json")
        self.widget = HabitTrackerWidget(self.model)

    def test_add_habit(self):
        """Проверка добавления привычки через виджет."""
        self.widget.habit_name_input.setText("New Habit")

        # 🔴 ИСПРАВЛЁННЫЙ СПОСОБ: Используем позиционный аргумент
        add_btn = self.widget.findChild(QPushButton, "add_habit_btn")
        QTest.mouseClick(add_btn, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.model.habits), 1)
        self.assertEqual(self.widget.habits_list.count(), 1)

    def test_delete_habit(self):
        """Проверка удаления привычки через виджет."""
        self.test_add_habit()  # Создаём тестовую привычку
        self.widget.habits_list.setCurrentRow(0)

        # 🔴 ИСПРАВЛЁННЫЙ СПОСОБ: Используем позиционный аргумент
        delete_btn = self.widget.findChild(QPushButton, "delete_habit_btn")
        QTest.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

        # Эмулируем подтверждение удаления
        QTest.keyClicks(QApplication.activeModalWidget(), "Yes")
        self.assertEqual(len(self.model.habits), 0)
        self.assertEqual(self.widget.habits_list.count(), 0)

    def test_mark_completed(self):
        """Проверка отметки выполнения."""
        self.test_add_habit()  # Создаём тестовую привычку
        self.widget.habits_list.setCurrentRow(0)

        # 🔴 ИСПРАВЛЁННЫЙ СПОСОБ: Используем позиционный аргумент
        done_btn = self.widget.findChild(QPushButton, "mark_done_btn")
        QTest.mouseClick(done_btn, Qt.MouseButton.LeftButton)
        self.assertGreater(self.model.habits[0].current_streak, 0)

    def test_import_export(self):
        """Проверка экспорта и импорта через виджет."""
        self.test_add_habit()  # Создаём тестовую привычку

        # 🔴 ИСПРАВЛЁННЫЙ СПОСОБ: Используем позиционный аргумент
        export_btn = self.widget.findChild(QPushButton, "export_habits_btn")
        QTest.mouseClick(export_btn, Qt.MouseButton.LeftButton)

        # Эмулируем выбор файла (используем backslash для переноса строки)
        with patch('PyQt6.QtWidgets.QFileDialog.getSaveFileName', return_value=("test.json", "JSON Files (*.json)")), \
                patch('builtins.open', new_callable=MagicMock()):
            QTest.mouseClick(QApplication.activeModalWidget(), Qt.MouseButton.LeftButton)

        # Чистим модель
        self.model.habits.clear()
        self.assertEqual(len(self.model.habits), 0)

        # 🔴 ИСПРАВЛЁННЫЙ СПОСОБ: Используем позиционный аргумент
        import_btn = self.widget.findChild(QPushButton, "import_habits_btn")
        QTest.mouseClick(import_btn, Qt.MouseButton.LeftButton)

        # Эмулируем выбор файла (используем backslash для переноса строки)
        with patch('PyQt6.QtWidgets.QFileDialog.getOpenFileName', return_value=("test.json", "JSON Files (*.json)")), \
                patch('builtins.open', new_callable=MagicMock()):
            QTest.mouseClick(QApplication.activeModalWidget(), Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.model.habits), 1)


if __name__ == '__main__':
    unittest.main()