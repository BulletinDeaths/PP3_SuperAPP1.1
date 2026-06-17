import json
import os
from datetime import date
from typing import List, Optional

# --- Модели данных ---

class HabitCheck:
    """Модель для хранения одной отметки о выполнении привычки."""
    def __init__(self, check_date: date, is_completed: bool):
        self.check_date = check_date.isoformat()  # Сохраняем в формате 'YYYY-MM-DD'
        self.is_completed = is_completed

class Habit:
    """Модель для хранения информации об одной привычке."""
    def __init__(self, name: str):
        self.name = name
        self.checks: List[HabitCheck] = []
        self.current_streak = 0
        self.best_streak = 0

    def add_check(self, check_date: date, is_completed: bool):
        """Добавляет новую отметку и пересчитывает серии."""
        # Запрет на повторную отметку в тот же день
        if any(c.check_date == check_date.isoformat() for c in self.checks):
            return

        new_check = HabitCheck(check_date, is_completed)
        self.checks.append(new_check)

        # Пересчет серий
        self._recalculate_streaks()

    def _recalculate_streaks(self):
        """Пересчитывает текущую и лучшую серии."""
        # Сортируем отметки по дате
        sorted_checks = sorted(self.checks, key=lambda c: c.check_date)

        current_streak = 0
        best_streak = 0

        # Проходим по отметкам с конца к началу
        for check in reversed(sorted_checks):
            if check.is_completed:
                current_streak += 1
                best_streak = max(best_streak, current_streak)
            else:
                # Как только встретили пропуск, текущая серия обрывается
                break

        self.current_streak = current_streak
        self.best_streak = best_streak

# --- Менеджер данных ---

class HabitTrackerModel:
    """Менеджер для управления коллекцией привычек и их сохранением."""
    def __init__(self, data_file_path: str):
        self.data_file_path = data_file_path
        self.habits: List[Habit] = []

    def load_from_file(self):
        """Загружает данные из файла .json."""
        if not os.path.exists(self.data_file_path):
            self.habits = []
            return

        with open(self.data_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.habits = []
            for habit_data in data.get('habits', []):
                habit = Habit(habit_data['name'])
                habit.checks = [HabitCheck(date.fromisoformat(c['check_date']), c['is_completed']) for c in habit_data['checks']]
                # После загрузки пересчитываем серии на случай, если данные были повреждены
                habit._recalculate_streaks()
                habit.current_streak = habit_data.get('current_streak', 0)
                habit.best_streak = habit_data.get('best_streak', 0)
                self.habits.append(habit)

    def save_to_file(self):
        """Сохраняет данные в файл .json."""
        data = {
            "habits": [
                {
                    "name": h.name,
                    "checks": [{"check_date": c.check_date, "is_completed": c.is_completed} for c in h.checks],
                    "current_streak": h.current_streak,
                    "best_streak": h.best_streak,
                }
                for h in self.habits
            ]
        }

        os.makedirs(os.path.dirname(self.data_file_path), exist_ok=True)
        with open(self.data_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # Методы для управления привычками
    def add_habit(self, name: str):
        new_habit = Habit(name)
        self.habits.append(new_habit)

    def delete_habit(self, index: int):
        if 0 <= index < len(self.habits):
            self.habits.pop(index)

    def get_habit(self, index: int) -> Optional[Habit]:
        if 0 <= index < len(self.habits):
            return self.habits[index]
        return None

    # Методы для экспорта/импорта
    def export_to_json(self) -> str:
        """Экспортирует данные в строку JSON."""
        return json.dumps({
            "habits": [
                {
                    "name": h.name,
                    "checks": [{"check_date": c.check_date, "is_completed": c.is_completed} for c in h.checks]
                }
                for h in self.habits
            ]
        }, ensure_ascii=False, indent=4)

    def import_from_json(self, json_string: str):
        """Импортирует данные из строки JSON, заменяя текущие."""
        data = json.loads(json_string)
        self.habits = []
        for habit_data in data.get('habits', []):
            habit = Habit(habit_data['name'])
            habit.checks = [HabitCheck(date.fromisoformat(c['check_date']), c['is_completed']) for c in habit_data['checks']]
            habit._recalculate_streaks()
            self.habits.append(habit)