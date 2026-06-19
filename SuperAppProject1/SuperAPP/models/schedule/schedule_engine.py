import datetime
from typing import List, Dict, Optional


class Lesson:
    def __init__(self, name: str, day_of_week: str, start_time: str, end_time: str,
                 lesson_type: str = "Лекция", room: str = ""):
        self.name = name
        self.day_of_week = day_of_week
        self.start_time = self._normalise_time(start_time)
        self.end_time   = self._normalise_time(end_time)
        self.lesson_type = lesson_type
        self.room = room
        self.status = "Запланировано"

    @staticmethod
    def _normalise_time(t: str) -> str:
        """Приводит любой формат ЧЧ:ММ / Ч:ММ к 'HH:MM' с ведущим нулём."""
        t = t.strip()
        for fmt in ("%H:%M", "%I:%M %p", "%I:%M"):
            try:
                return datetime.datetime.strptime(t, fmt).strftime("%H:%M")
            except ValueError:
                pass
        # разобрать вручную
        if ":" in t:
            h, m = t.split(":", 1)
            return f"{int(h):02d}:{int(m.split()[0]):02d}"
        raise ValueError(f"Неверный формат времени: '{t}'")

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "day_of_week": self.day_of_week,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "lesson_type": self.lesson_type,
            "room": self.room,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Lesson":
        obj = cls.__new__(cls)
        obj.name        = data["name"]
        obj.day_of_week = data["day_of_week"]
        obj.start_time  = cls._normalise_time(data["start_time"])
        obj.end_time    = cls._normalise_time(data["end_time"])
        obj.lesson_type = data.get("lesson_type", "Лекция")
        obj.room        = data.get("room", "")
        obj.status      = data.get("status", "Запланировано")
        return obj


class ScheduleEngine:
    VALID_DAYS = [
        "Понедельник", "Вторник", "Среда", "Четверг",
        "Пятница", "Суббота", "Воскресенье",
    ]
    NIGHT_START = datetime.time(20, 0)
    DAY_START   = datetime.time(8, 0)

    def __init__(self, storage):
        self.storage = storage
        self.lessons: List[Dict] = self.storage.load_data()

    @staticmethod
    def _to_time(s: str) -> datetime.time:
        return datetime.datetime.strptime(s, "%H:%M").time()

    def _validate_new_lesson_time(self, start: str, end: str) -> None:
        """Проверяет только новое занятие (не трогает существующие)."""
        t_start = self._to_time(start)
        t_end   = self._to_time(end)

        if t_end <= t_start:
            raise ValueError("Время окончания должно быть позже времени начала.")

        if t_start < self.DAY_START or t_start >= self.NIGHT_START:
            raise ValueError("Время начала занятия должно быть в диапазоне 08:00–19:59.")

        if t_end <= self.DAY_START or t_end > self.NIGHT_START:
            raise ValueError("Время окончания занятия должно быть в диапазоне 08:01–20:00.")

    @staticmethod
    def _overlaps(s1: str, e1: str, s2: str, e2: str) -> bool:
        """True если интервалы [s1,e1) и [s2,e2) пересекаются."""
        a = datetime.datetime.strptime(s1, "%H:%M")
        b = datetime.datetime.strptime(e1, "%H:%M")
        c = datetime.datetime.strptime(s2, "%H:%M")
        d = datetime.datetime.strptime(e2, "%H:%M")
        # Пропускаем существующие с некорректным временем
        if b <= a or d <= c:
            return False
        return max(a, c) < min(b, d)

    def create_lesson(self, lesson: Lesson) -> bool:
        if not lesson.name.strip():
            raise ValueError("Название предмета не может быть пустым.")

        if lesson.day_of_week not in self.VALID_DAYS:
            raise ValueError(f"Неверный день недели: '{lesson.day_of_week}'.")

        # Нормализация (на случай, если виджет передал нестандартный формат)
        start = Lesson._normalise_time(lesson.start_time)
        end   = Lesson._normalise_time(lesson.end_time)

        self._validate_new_lesson_time(start, end)

        # Проверка пересечений ТОЛЬКО внутри того же дня недели
        for existing in self.lessons:
            if existing["day_of_week"] != lesson.day_of_week:
                continue
            ex_start = Lesson._normalise_time(existing["start_time"])
            ex_end   = Lesson._normalise_time(existing["end_time"])
            if self._overlaps(start, end, ex_start, ex_end):
                raise ValueError(
                    f"Пересечение с '{existing['name']}' "
                    f"({ex_start}–{ex_end}) в {lesson.day_of_week}."
                )

        lesson.start_time = start
        lesson.end_time   = end
        self.lessons.append(lesson.to_dict())
        self.storage.save_data(self.lessons)
        return True

    def update_lesson(self, index: int, updated: Lesson) -> bool:
        if not (0 <= index < len(self.lessons)):
            return False

        if not updated.name.strip():
            raise ValueError("Название предмета не может быть пустым.")

        if updated.day_of_week not in self.VALID_DAYS:
            raise ValueError(f"Неверный день недели: '{updated.day_of_week}'.")

        start = Lesson._normalise_time(updated.start_time)
        end   = Lesson._normalise_time(updated.end_time)
        self._validate_new_lesson_time(start, end)

        for i, existing in enumerate(self.lessons):
            if i == index:
                continue
            if existing["day_of_week"] != updated.day_of_week:
                continue
            ex_start = Lesson._normalise_time(existing["start_time"])
            ex_end   = Lesson._normalise_time(existing["end_time"])
            if self._overlaps(start, end, ex_start, ex_end):
                raise ValueError(
                    f"Пересечение с '{existing['name']}' "
                    f"({ex_start}–{ex_end}) в {updated.day_of_week}."
                )

        updated.start_time = start
        updated.end_time   = end
        self.lessons[index] = updated.to_dict()
        self.storage.save_data(self.lessons)
        return True

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
        return False

    def get_lessons_for_day(self, day_of_week: str) -> List[Lesson]:
        return [
            Lesson.from_dict(l)
            for l in self.lessons
            if l["day_of_week"] == day_of_week
        ]

    def get_all_lessons(self) -> List[Lesson]:
        return [Lesson.from_dict(l) for l in self.lessons]

    def get_stats(self) -> Dict[str, int]:
        """Возвращает словарь {день_недели: кол-во занятий} для графика нагрузки."""
        stats: Dict[str, int] = {d: 0 for d in self.VALID_DAYS}
        for l in self.lessons:
            day = l.get("day_of_week", "")
            if day in stats:
                stats[day] += 1
        return stats
