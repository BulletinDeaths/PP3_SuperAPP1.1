import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTime, QTimer

from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import ScheduleEngine, Lesson
from SuperAppProject1.SuperAPP.models.schedule.storage import Storage
from SuperAppProject1.SuperAPP.ui.widgets.schedule_widget import ScheduleWidget


class TestScheduleWidget(unittest.TestCase):
    def setUp(self):
        # Storage.__init__ делает os.makedirs(...), а ScheduleEngine
        # вызывает storage.save_data(...) при каждом create_lesson — то
        # есть JSON реально пишется на диск. Используем отдельную
        # временную папку для каждого теста, чтобы ничего не оставалось
        # на диске после прогона тестов.
        self._tmp_dir = tempfile.mkdtemp()
        data_path = os.path.join(self._tmp_dir, "test_schedule.json")

        storage = Storage(data_path)
        self.engine = ScheduleEngine(storage)
        self.widget = ScheduleWidget(self.engine)

    def tearDown(self):
        # ScheduleWidget запускает собственный QTimer с интервалом 1с
        # в __init__ (self._timer.start()), который продолжает работать
        # после завершения теста, если явно его не остановить.
        self.widget._timer.stop()
        shutil.rmtree(self._tmp_dir, ignore_errors=True)

    def test_load_lessons(self):
        """Проверка загрузки занятий для дня."""
        # Lesson ожидает start_time/end_time как строки "HH:MM"
        # (см. schedule_engine.Lesson._normalise_time), а не объекты QTime.
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
        # countdown_label обновляется методом _update_countdown(),
        # который подключён к QTimer с интервалом 1000мс — он НЕ
        # вызывается автоматически из load_lessons_for_day(). Вызываем
        # его явно, чтобы тест не зависел от реального ожидания таймера.
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
        # "Active Now" может всё ещё идти, и _update_countdown сообщит
        # про него первым, а не про "Следующая" — это ожидаемое
        # поведение реального кода, не ошибка теста. Допускаем оба
        # исхода.
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
        # LoadChart — кастомный QWidget с собственным paintEvent, у него
        # нет атрибута .figure (это не matplotlib canvas). Проверяем
        # реальный публичный атрибут — внутренние данные диаграммы.
        self.assertEqual(len(self.widget.load_chart._data), 7)


if __name__ == '__main__':
    unittest.main()
