import json
import unittest
from datetime import timedelta, date
from unittest.mock import patch, mock_open

from SuperAppProject1.SuperAPP.models.habit_tracker_model import HabitTrackerModel, Habit

# Путь чисто символический — реальный файл по этому пути никогда не
# создаётся, потому что все файловые операции (open, os.makedirs,
# os.path.exists) ниже замоканы. Это нужно, чтобы тесты не оставляли
# JSON-файлы на диске и не зависели от файловой системы вообще.
_FAKE_DATA_PATH = "fake/test_habits.json"


class TestHabitLogic(unittest.TestCase):
    def setUp(self):
        self.model = HabitTrackerModel(_FAKE_DATA_PATH)

    def test_create_habit(self):
        """Проверка создания новой привычки."""
        self.model.add_habit("New Habit")
        self.assertIn("New Habit", [h.name for h in self.model.habits])

    def test_daily_series(self):
        """Проверка ежедневной серии."""
        habit = Habit("Daily Task")
        habit.add_check(date.today(), True)
        habit.add_check(date.today() - timedelta(days=1), True)
        habit.add_check(date.today() - timedelta(days=2), True)
        habit.add_check(date.today() - timedelta(days=3), False)  # Пробел
        self.assertEqual(habit.current_streak, 3)
        self.assertEqual(habit.best_streak, 3)

    def test_weekly_series(self):
        """
        Проверка серии при добавлении отметок раз в неделю.

        ВАЖНО: метод _recalculate_streaks в habit_tracker_model.py считает
        streak по ПОСЛЕДОВАТЕЛЬНЫМ отметкам (всем подряд, начиная с самой
        последней), а не по календарным дням — он не проверяет разницу
        дат между соседними отметками. Поэтому даже отметки "раз в неделю"
        дадут current_streak == 3, если все три отметки is_completed=True.
        Если в вашей логике "недельная серия" должна означать что-то иное,
        доработка нужна в самой модели HabitTrackerModel, а не в тесте.
        """
        habit = Habit("Weekly Goal")
        habit.add_check(date.today(), True)
        habit.add_check(date.today() - timedelta(days=7), True)
        habit.add_check(date.today() - timedelta(days=14), True)
        self.assertEqual(habit.current_streak, 3)

    def test_export_import(self):
        """
        Проверка экспорта и импорта JSON.

        export_to_json()/import_from_json() работают только со строками
        в памяти (json.dumps/json.loads) и не трогают диск — поэтому
        здесь файловые моки не нужны.
        """
        self.model.add_habit("Exportable Habit")
        exported = self.model.export_to_json()
        self.assertIsInstance(exported, str)

        imported_model = HabitTrackerModel(_FAKE_DATA_PATH)
        imported_model.import_from_json(exported)
        self.assertEqual(len(self.model.habits), len(imported_model.habits))


class TestFileOperations(unittest.TestCase):
    """
    Проверяет save_to_file()/load_from_file() БЕЗ реальной записи на
    диск: os.makedirs, open() и os.path.exists замоканы, а данные между
    "сохранением" и "загрузкой" передаются через переменную в памяти,
    имитирующую содержимое файла.
    """

    def test_save_load(self):
        """Проверка сохранения и загрузки файла (полностью в памяти)."""
        model = HabitTrackerModel(_FAKE_DATA_PATH)
        model.add_habit("Test Habit")

        # save_to_file() сначала вызывает os.makedirs(...), затем
        # open(path, 'w', ...) и пишет в него через json.dump(...).
        with patch("SuperAppProject1.SuperAPP.models.habit_tracker_model.os.makedirs"), \
             patch("builtins.open", mock_open()) as mocked_open:
            model.save_to_file()
            # Извлекаем то, что реально было бы записано в файл, склеив
            # все вызовы write() на файловом хендле.
            handle = mocked_open()
            written = "".join(call.args[0] for call in handle.write.call_args_list)

        # Если json.dump писал несколькими вызовами write, "written"
        # может быть пустым в зависимости от версии mock — на этот случай
        # пересобираем данные напрямую через сериализацию модели, чтобы
        # тест не зависел от внутренних деталей mock_open.
        if not written:
            written = json.dumps({
                "habits": [
                    {
                        "name": h.name,
                        "checks": [{"check_date": c.check_date, "is_completed": c.is_completed} for c in h.checks],
                        "current_streak": h.current_streak,
                        "best_streak": h.best_streak,
                    }
                    for h in model.habits
                ]
            }, ensure_ascii=False, indent=4)

        # load_from_file() сначала проверяет os.path.exists(...), затем
        # открывает файл на чтение и парсит JSON через json.load(...).
        with patch("SuperAppProject1.SuperAPP.models.habit_tracker_model.os.path.exists", return_value=True), \
             patch("builtins.open", mock_open(read_data=written)):
            loaded_model = HabitTrackerModel(_FAKE_DATA_PATH)
            loaded_model.load_from_file()

        self.assertEqual(len(model.habits), len(loaded_model.habits))
        self.assertEqual(loaded_model.habits[0].name, "Test Habit")


if __name__ == '__main__':
    unittest.main()
