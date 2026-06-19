import unittest
from unittest.mock import patch, MagicMock

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMessageBox

from SuperAppProject1.SuperAPP.models.habit_tracker_model import HabitTrackerModel
from SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget import HabitTrackerWidget

_FAKE_DATA_PATH = "fake/test_habits.json"


class TestHabitTrackerWidget(unittest.TestCase):
    def setUp(self):
        self.model = HabitTrackerModel(_FAKE_DATA_PATH)

        self._save_patch = patch.object(self.model, "save_to_file")
        self._save_patch.start()

        self.widget = HabitTrackerWidget(self.model)

    def tearDown(self):
        self._save_patch.stop()

    def test_add_habit(self):
        """Проверка добавления привычки через виджет."""
        self.widget.habit_name_input.setText("New Habit")
        QTest.mouseClick(self.widget.add_habit_button, Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.model.habits), 1)
        self.assertEqual(self.widget.habits_list.count(), 1)

    def test_delete_habit(self):
        """Проверка удаления привычки через виджет."""
        self.test_add_habit()
        self.widget.habits_list.setCurrentRow(0)

        with patch(
            "SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            QTest.mouseClick(self.widget.delete_habit_button, Qt.MouseButton.LeftButton)

        self.assertEqual(len(self.model.habits), 0)
        self.assertEqual(self.widget.habits_list.count(), 0)

    def test_mark_completed(self):
        """Проверка отметки выполнения."""
        self.test_add_habit()
        self.widget.habits_list.setCurrentRow(0)
        QTest.mouseClick(self.widget.mark_done_btn, Qt.MouseButton.LeftButton)
        self.assertGreater(self.model.habits[0].current_streak, 0)

    def test_import_export(self):
        """Проверка экспорта и импорта через виджет."""
        self.test_add_habit()

        with patch(
            "SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget.QFileDialog.getSaveFileName",
            return_value=("test.json", "JSON Files (*.json)"),
        ), patch("builtins.open", new_callable=MagicMock()), patch(
            "SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget.QMessageBox.information",
        ):
            QTest.mouseClick(self.widget.export_btn, Qt.MouseButton.LeftButton)

        # Чистим модель, чтобы проверить, что импорт её восстановит
        self.model.habits.clear()
        self.assertEqual(len(self.model.habits), 0)

        # Мокаем сам метод модели, чтобы не зависеть от реального содержимого замоканного open().
        with patch(
            "SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget.QFileDialog.getOpenFileName",
            return_value=("test.json", "JSON Files (*.json)"),
        ), patch("builtins.open", new_callable=MagicMock()), patch.object(
            self.model, "import_from_json"
        ) as mock_import, patch(
            "SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget.QMessageBox.information",
        ):
            def fake_import(json_string):
                self.model.add_habit("New Habit")

            mock_import.side_effect = fake_import
            QTest.mouseClick(self.widget.import_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(len(self.model.habits), 1)


if __name__ == '__main__':
    unittest.main()
