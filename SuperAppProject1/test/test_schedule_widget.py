import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QMessageBox

from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import ScheduleEngine, Lesson
from SuperAppProject1.SuperAPP.models.schedule.storage import Storage
from SuperAppProject1.SuperAPP.ui.widgets.schedule_widget import ScheduleWidget


class TestScheduleWidget(unittest.TestCase):
    def setUp(self):

        self._tmp_dir = tempfile.mkdtemp()
        data_path = os.path.join(self._tmp_dir, "test_schedule.json")

        storage = Storage(data_path)
        self.engine = ScheduleEngine(storage)
        self.widget = ScheduleWidget(self.engine)

    def tearDown(self):
        self.widget._timer.stop()
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_load_lessons(self):
        """Проверка загрузки занятий для дня."""
        lesson_obj = Lesson(
            name="Test Lesson",
            day_of_week="Понедельник",
            start_time="08:00",
            end_time="09:30",
        )
        self.engine.create_lesson(lesson_obj)
        self.widget.load_lessons_for_day("Понедельник")
        self.assertGreater(self.widget.lesson_list.count(), 0)

    def test_add_lesson(self):
        """Проверка добавления занятия через виджет."""
        self.widget.day_field.setCurrentText("Понедельник")
        self.widget.name_field.setText("Test Lesson")
        self.widget.time_start_field.setTime(QTime.fromString("08:00", "HH:mm"))
        self.widget.time_end_field.setTime(QTime.fromString("09:30", "HH:mm"))
        QTest.mouseClick(self.widget.save_btn, Qt.MouseButton.LeftButton)
        self.assertGreater(self.widget.lesson_list.count(), 0)

    def test_delete_lesson(self):
        """Проверка удаления занятия."""
        self.test_add_lesson()

        self.widget.load_lessons_for_day("Понедельник")

        self.widget.lesson_list.setCurrentRow(0)

        with patch(
            "SuperAppProject1.SuperAPP.ui.widgets.schedule_widget.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            QTest.mouseClick(self.widget.del_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(len(self.engine.lessons), 0)

    def test_countdown_logic(self):
        """Проверка логики обратного отсчёта."""
        now = datetime.now()
        today_dow_name = self.widget.DAY_MAP[now.isoweekday()]

        active_now = Lesson(
            name="Active Now",
            day_of_week=today_dow_name,
            start_time=f"{(now.hour - 1) % 24:02d}:00",
            end_time=f"{(now.hour + 1) % 24:02d}:00",
        )
        self.engine.create_lesson(active_now)
        self.widget.load_lessons_for_day(today_dow_name)
        self.widget._update_countdown()
        self.assertIn("Идёт", self.widget.countdown_label.text())

        future_hour = (now.hour + 2) % 24
        future_lesson = Lesson(
            name="Future Lesson",
            day_of_week=today_dow_name,
            start_time=f"{future_hour:02d}:00",
            end_time=f"{(future_hour + 1) % 24:02d}:00",
        )
        self.engine.create_lesson(future_lesson)
        self.widget.load_lessons_for_day(today_dow_name)
        self.widget._update_countdown()

        text = self.widget.countdown_label.text()
        self.assertTrue("Идёт" in text or "Следующая" in text)

    def test_load_chart(self):
        """Проверка графика нагрузки."""
        now = datetime.now()
        today_dow_name = self.widget.DAY_MAP[now.isoweekday()]

        lesson_obj = Lesson(
            name="Test Lesson",
            day_of_week=today_dow_name,
            start_time=f"{now.hour:02d}:00",
            end_time=f"{(now.hour + 1) % 24:02d}:00",
        )
        self.engine.create_lesson(lesson_obj)
        self.widget._refresh_chart()

        stats = self.engine.get_stats()
        self.assertGreater(sum(stats.values()), 0)
        # Проверяем реальный публичный атрибут — внутренние данные диаграммы.
        self.assertEqual(len(self.widget.load_chart._data), 7)


if __name__ == '__main__':
    unittest.main()
