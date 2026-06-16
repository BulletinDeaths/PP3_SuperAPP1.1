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
        """Принимает форматы HH:MM и H:MM"""
        for fmt in ("%H:%M", "%I:%M"):
            try:
                datetime.datetime.strptime(time_str, fmt)
                return True
            except ValueError:
                pass
        return False

    def _parse_time(self, time_str: str) -> datetime.datetime:
        """Парсит время в форматах HH:MM и H:MM"""
        for fmt in ("%H:%M", "%I:%M"):
            try:
                return datetime.datetime.strptime(time_str, fmt)
            except ValueError:
                pass
        raise ValueError(f"Неверный формат времени: {time_str}")

    def _times_overlap(self, start1, end1, start2, end2) -> bool:
        """Проверяет пересечение двух интервалов.
        start1/end1 — новое занятие (проверяется на ночь).
        start2/end2 — существующее (только пересечение, без проверки на ночь)."""

        t_start1 = self._parse_time(start1)
        t_end1   = self._parse_time(end1)
        t_start2 = self._parse_time(start2)
        t_end2   = self._parse_time(end2)

        night_start = datetime.datetime.strptime("20:00", "%H:%M")
        night_end   = datetime.datetime.strptime("08:00", "%H:%M")

        def is_night(t: datetime.datetime) -> bool:
            return t >= night_start or t < night_end

        # Проверяем ночной запрет только для нового занятия
        if is_night(t_start1) or is_night(t_end1):
            raise ValueError("Нельзя создавать занятия в период с 20:00 до 08:00!")

        # Если существующее занятие имеет некорректное время — пропускаем его
        if t_end1 <= t_start1:
            raise ValueError("Время окончания должно быть позже времени начала!")
        if t_end2 <= t_start2:
            return False  # Некорректное существующее — не блокируем создание

        latest_start  = max(t_start1, t_start2)
        earliest_end  = min(t_end1,   t_end2)
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
                # ValueError (ночное время) пробрасывается наверх в виджет
                if self._times_overlap(lesson.start_time, lesson.end_time,
                                       existing_lesson.start_time, existing_lesson.end_time):
                    raise ValueError(
                        f"Занятие пересекается с '{existing_lesson.name}' "
                        f"({existing_lesson.start_time}–{existing_lesson.end_time})"
                    )

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