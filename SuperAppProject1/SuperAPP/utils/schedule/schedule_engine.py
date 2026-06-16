import datetime
from typing import List, Dict, Optional


class Lesson:
    def __init__(self, name: str, day_of_week: str, start_time: str, end_time: str,
                 lesson_type: str = "Лекция", room: str = "Не указано"):
        self.name = name
        self.day_of_week = day_of_week
        self.start_time = start_time
        self.end_time = end_time
        self.lesson_type = lesson_type
        self.room = room
        self.status = "Запланировано"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "lesson_type": self.lesson_type,
            "room": self.room,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(
            name=data["name"],
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            lesson_type=data.get("lesson_type", "Лекция"),
            room=data.get("room", "Не указано"),
        )


class ScheduleEngine:
    VALID_DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    def __init__(self, storage):
        self.storage = storage
        self.lessons = self.storage.load_data()

    def _is_valid_time(self, time_str: str) -> bool:
        try:
            datetime.datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def _times_overlap(self, start1, end1, start2, end2) -> bool:
        """Проверяет, пересекаются ли два временных интервала.
           Также проверяет запрет на ночное время (20:00 — 08:00)."""

        # Парсим строки времени в целые числа (часы)
        # Сначала обрабатываем первый интервал
        hour_start1 = int(start1.split(":")[0])  # Час начала первого занятия
        hour_end1 = int(end1.split(":")[0])  # Час окончания первого занятия

        # Затем обрабатываем второй интервал
        hour_start2 = int(start2.split(":")[0])  # Час начала второго занятия
        hour_end2 = int(end2.split(":")[0])  # Час окончания второго занятия

        # ❗️ ПРОВЕРКА ЗАПРЕТА ❗️
        # Проверяем, попадают ли границы любого из двух интервалов в ночной промежуток
        if (hour_start1 >= 20 or hour_end1 <= 8) or \
                (hour_start2 >= 20 or hour_end2 <= 8):  # Второе занятие в ночи
            raise ValueError("Нельзя создавать занятия в период с 20:00 до 08:00!")

        # Стандартная проверка на пересечение интервалов
        t_start1 = datetime.datetime.strptime(start1, "%H:%M")
        t_end1 = datetime.datetime.strptime(end1, "%H:%M")
        t_start2 = datetime.datetime.strptime(start2, "%H:%M")
        t_end2 = datetime.datetime.strptime(end2, "%H:%M")

        # Проверка на некорректное время (конец раньше начала)
        if t_end1 <= t_start1 or t_end2 <= t_start2:
            return True  # Считаем это ошибкой/пересечением

        latest_start = max(t_start1, t_start2)
        earliest_end = min(t_end1, t_end2)
        return (earliest_end - latest_start).total_seconds() > 0

    def create_lesson(self, lesson: Lesson) -> bool:
        if not all([lesson.name, lesson.day_of_week, lesson.start_time, lesson.end_time]):
            return False

        if lesson.day_of_week not in self.VALID_DAYS:
            return False

        if not (self._is_valid_time(lesson.start_time) and self._is_valid_time(lesson.end_time)):
            return False

        for existing in self.lessons:
            existing_lesson = Lesson.from_dict(existing)
            if existing_lesson.day_of_week == lesson.day_of_week:
                if self._times_overlap(lesson.start_time, lesson.end_time,
                                       existing_lesson.start_time, existing_lesson.end_time):
                    return False

        self.lessons.append(lesson.to_dict())
        self.storage.save_data(self.lessons)
        return True

    def get_lessons_for_day(self, day_of_week: str) -> List[Lesson]:
        return [Lesson.from_dict(l) for l in self.lessons if l["day_of_week"] == day_of_week]

    def update_lesson(self, index: int, updated_lesson: Lesson) -> bool:
        if 0 <= index < len(self.lessons):
            self.lessons[index] = updated_lesson.to_dict()
            self.storage.save_data(self.lessons)
            return True
        return False

    def delete_lesson(self, index: int) -> bool:
        if 0 <= index < len(self.lessons):
            del self.lessons[index]
            self.storage.save_data(self.lessons)
            return True
        return False

    def mark_status(self, index: int, status: str) -> bool:
        if 0 <= index < len(self.lessons):
            self.lessons[index]["status"] = status
            self.storage.save_data(self.lessons)
            return True