import os
from datetime import date, timedelta
import unittest
from SuperAppProject1.SuperAPP.utils.habit_tracker_model import Habit, HabitTrackerModel

class TestHabit(unittest.TestCase):
    """Тесты для класса Habit."""

    def test_initial_streaks(self):
        habit = Habit("Read a book")
        self.assertEqual(habit.current_streak, 0)
        self.assertEqual(habit.best_streak, 0)

    def test_add_check_completed_increases_streak(self):
        habit = Habit("Run")
        yesterday = date.today() - timedelta(days=1)
        today = date.today()

        # Создаем вчерашнюю отметку о выполнении
        habit.add_check(yesterday, True)
        self.assertEqual(habit.current_streak, 1)
        self.assertEqual(habit.best_streak, 1)

        # Добавляем сегодняшнее выполнение, серия должна увеличиться
        habit.add_check(today, True)
        self.assertEqual(habit.current_streak, 2)
        self.assertEqual(habit.best_streak, 2)

    def test_skip_breaks_current_streak(self):
        habit = Habit("Meditate")
        yesterday = date.today() - timedelta(days=1)
        today = date.today()

        # Вчера выполнили
        habit.add_check(yesterday, True)
        self.assertEqual(habit.current_streak, 1)

        # Сегодня пропустили
        habit.add_check(today, False)
        self.assertEqual(habit.current_streak, 0)
        # Лучшая серия остается прежней
        self.assertEqual(habit.best_streak, 1)

    def test_no_duplicate_checks_for_same_day(self):
        habit = Habit("Code for 1 hour")
        today = date.today()

        # Первая отметка
        habit.add_check(today, True)
        initial_streak = habit.current_streak

        # Вторая попытка отметить тот же день не должна ничего изменить
        habit.add_check(today, False)
        self.assertEqual(habit.current_streak, initial_streak)


class TestHabitTrackerModel(unittest.TestCase):
    """Тесты для класса HabitTrackerModel."""

    TEST_DATA_FILE = 'tests/test_data.json'

    @classmethod
    def tearDownClass(cls):
        """Удаляет тестовый файл после всех тестов."""
        if os.path.exists(cls.TEST_DATA_FILE):
            os.remove(cls.TEST_DATA_FILE)

    def setUp(self):
        """Очищает тестовый файл перед каждым тестом."""
        if os.path.exists(self.TEST_DATA_FILE):
            os.remove(self.TEST_DATA_FILE)
        self.model = HabitTrackerModel(self.TEST_DATA_FILE)

    def test_save_and_load_empty_list(self):
        self.model.save_to_file()
        self.model.load_from_file()
        self.assertEqual(len(self.model.habits), 0)

    def test_persistence_of_habits(self):
        # Создаем привычку и добавляем данные
        self.model.add_habit("Test Habit")
        self.model.habits[0].add_check(date.today(), True)
        self.model.save_to_file()

        # Загружаем модель заново
        new_model = HabitTrackerModel(self.TEST_DATA_FILE)
        new_model.load_from_file()

        # Проверяем, что данные сохранились
        self.assertEqual(len(new_model.habits), 1)
        loaded_habit = new_model.habits[0]
        self.assertEqual(loaded_habit.name, "Test Habit")
        self.assertEqual(loaded_habit.current_streak, 1)

if __name__ == '__main__':
    unittest.main()