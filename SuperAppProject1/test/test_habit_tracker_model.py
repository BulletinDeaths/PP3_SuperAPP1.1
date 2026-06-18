import unittest
from datetime import timedelta, date
from unittest.mock import patch

from SuperAppProject1.SuperAPP.models.habit_tracker_model import HabitTrackerModel, Habit

class TestHabitLogic(unittest.TestCase):
    def setUp(self):
        self.model = HabitTrackerModel("tests/data/test_habits.json")
        self.model.load_from_file()

    def test_create_habit(self):
        """Проверка создания новой привычки."""
        initial_len = len(self.model.habits)
        self.model.add_habit("New Habit")  # Исправлено: передали только имя
        self.assertIn("New Habit", [h.name for h in self.model.habits])

    def test_daily_series(self):
        """Проверка ежедневной серии."""
        # Исправлено: создаём экземпляр только с именем
        habit = Habit("Daily Task")
        habit.frequency = "Ежедневно"  # Присвоили частоту отдельно
        habit.add_check(date.today(), True)
        habit.add_check(date.today() - timedelta(days=1), True)
        habit.add_check(date.today() - timedelta(days=2), True)
        habit.add_check(date.today() - timedelta(days=3), False)  # Пробел
        self.assertEqual(habit.current_streak, 3)
        self.assertEqual(habit.best_streak, 3)

    def test_weekly_series(self):
        """Проверка еженедельной серии."""
        # Исправлено: создаём экземпляр только с именем
        habit = Habit("Weekly Goal")
        habit.frequency = "Еженедельно"  # Присвоили частоту отдельно
        habit.add_check(date.today(), True)
        habit.add_check(date.today() - timedelta(days=7), True)
        habit.add_check(date.today() - timedelta(days=14), True)
        self.assertEqual(habit.current_streak, 3)

    def test_export_import(self):
        """Проверка экспорта и импорта JSON."""
        exported = self.model.export_to_json()
        self.assertIsInstance(exported, str)

        imported_model = HabitTrackerModel("")
        imported_model.import_from_json(exported)
        self.assertEqual(len(self.model.habits), len(imported_model.habits))

@patch('os.makedirs')
class TestFileOperations(unittest.TestCase):
    def test_save_load(self, mock_makedirs):
        """Проверка сохранения и загрузки файла."""
        model = HabitTrackerModel("tests/data/test_habits.json")
        model.add_habit("Test Habit")
        model.save_to_file()

        loaded_model = HabitTrackerModel("tests/data/test_habits.json")
        loaded_model.load_from_file()
        self.assertEqual(len(model.habits), len(loaded_model.habits))

if __name__ == '__main__':
    unittest.main()