import os
import sys
sys.path.append(os.path.abspath("../../"))

import unittest
from datetime import datetime
from PyQt6.QtWidgets import QApplication, QPushButton
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTime

from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import ScheduleEngine
from SuperAppProject1.SuperAPP.models.schedule.storage import Storage
from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import Lesson

from SuperAppProject1.SuperAPP.ui.widgets.schedule_widget import ScheduleWidget

app = QApplication([])

class TestScheduleWidget(unittest.TestCase):
    def setUp(self):
        storage = Storage("tests/data/test_schedule.json")
        self.engine = ScheduleEngine(storage)
        self.widget = ScheduleWidget(self.engine)

    def test_load_lessons(self):
        """Проверка загрузки занятий для дня."""
        # 🔴 Исправлено: преобразуем строки в объекты QTime
        lesson_data = {
            "name": "Test Lesson",
            "day_of_week": "Понедельник",
            "start_time": QTime.fromString("08:00", "HH:mm"),
            "end_time": QTime.fromString("09:30", "HH:mm")
        }
        # 🔴 Исправлено: конвертируем словарь в объект Lesson
        lesson_obj = Lesson(**lesson_data)
        self.engine.create_lesson(lesson_obj)
        self.widget.load_lessons_for_day("Понедельник")
        self.assertGreater(self.widget.lesson_list.count(), 0)

    def test_add_lesson(self):
        """Проверка добавления занятия через виджет."""
        # 🔴 Исправлено: преобразуем строки в объекты QTime
        self.widget.day_field.setCurrentText("Понедельник")
        self.widget.name_field.setText("Test Lesson")
        self.widget.time_start_field.setTime(QTime.fromString("08:00", "HH:mm"))
        self.widget.time_end_field.setTime(QTime.fromString("09:30", "HH:mm"))
        # 🔴 Исправлено: находим кнопку по тексту
        save_btn = self.widget.form_container.findChild(QPushButton, "✅ Сохранить")
        QTest.mouseClick(save_btn, Qt.MouseButton.LeftButton)
        self.assertGreater(self.widget.lesson_list.count(), 0)

    def test_delete_lesson(self):
        """Проверка удаления занятия."""
        self.test_add_lesson()  # Создаём тестовое занятие
        self.widget.lesson_list.setCurrentRow(0)
        # 🔴 Исправлено: находим кнопку по тексту
        delete_btn = self.widget.list_container.findChild(QPushButton, "🗑 Удалить выбранное")
        QTest.mouseClick(delete_btn, Qt.MouseButton.LeftButton)
        # Эмулируем подтверждение удаления
        QTest.keyClicks(QApplication.activeModalWidget(), "Yes")
        self.assertEqual(self.widget.lesson_list.count(), 0)

    def test_countdown_logic(self):
        """Проверка логики обратного отсчёта."""
        # 🔴 Исправлено: создаём гарантированные данные для проверки
        now = datetime.now()
        today_dow_name = self.widget.DAY_MAP[now.isoweekday()]
        # 🔴 Исправлено: преобразуем часы в объекты QTime
        active_now = {
            "name": "Active Now",
            "day_of_week": today_dow_name,
            "start_time": QTime(now.hour - 1, 0),
            "end_time": QTime(now.hour + 1, 0),
        }
        # 🔴 Исправлено: конвертируем словарь в объект Lesson
        lesson_obj = Lesson(**active_now)
        self.engine.create_lesson(lesson_obj)
        self.widget.load_lessons_for_day(today_dow_name)
        self.assertIn("Идёт", self.widget.countdown_label.text())

        # 🔴 Исправлено: создаём будущее занятие для проверки
        future_hour = (now.hour + 2) % 24
        future_lesson = {
            "name": "Future Lesson",
            "day_of_week": today_dow_name,
            "start_time": QTime(future_hour, 0),
            "end_time": QTime(future_hour + 1, 0),
        }
        lesson_obj = Lesson(**future_lesson)
        self.engine.create_lesson(lesson_obj)
        self.widget.load_lessons_for_day(today_dow_name)
        self.assertIn("Следующая", self.widget.countdown_label.text())

    def test_load_chart(self):
        """Проверка графика нагрузки."""
        # 🔴 Исправлено: добавляем данные для сегодняшнего дня
        now = datetime.now()
        today_dow_name = self.widget.DAY_MAP[now.isoweekday()]
        # 🔴 Исправлено: преобразуем часы в объекты QTime
        lesson_data = {
            "name": "Test Lesson",
            "day_of_week": today_dow_name,
            "start_time": QTime(now.hour, 0),
            "end_time": QTime(now.hour + 1, 0),
        }
        lesson_obj = Lesson(**lesson_data)
        self.engine.create_lesson(lesson_obj)
        self.widget._refresh_chart()
        # 🔴 Исправлено: проверяем, что на графике есть данные
        stats = self.engine.get_stats()
        self.assertGreater(sum(stats.values()), 0)
        self.assertIsNotNone(self.widget.load_chart.figure)

if __name__ == '__main__':
    unittest.main()