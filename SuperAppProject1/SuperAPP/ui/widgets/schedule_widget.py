import datetime

from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name

from PyQt6.QtCore import QDate, QSize, Qt, QTime, QTimer
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtWidgets import (
    QCalendarWidget, QComboBox, QFormLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMessageBox, QPushButton, QSizePolicy, QTimeEdit,
    QVBoxLayout, QWidget
)

from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import Lesson


#  Мини-гистограмма нагрузки
class LoadChart(QWidget):
    """Простой bar-chart нагрузки по дням недели."""

    DAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    BAR_COLOR  = QColor("#4CAF50")
    BG_COLOR   = QColor("#F5F5F5")
    AXIS_COLOR = QColor("#AAAAAA")

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = [0] * 7
        self.setMinimumHeight(110)
        self.setMaximumHeight(130)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_data(self, stats: dict):
        keys = ["Понедельник","Вторник","Среда","Четверг","Пятница","Суббота","Воскресенье"]
        self._data = [stats.get(k, 0) for k in keys]
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        padding_x = 8
        padding_top = 10
        label_h = 18
        bar_area_h = h - padding_top - label_h

        p.fillRect(0, 0, w, h, self.BG_COLOR)

        max_val = max(self._data) if any(self._data) else 1
        bar_w = (w - padding_x * 2) / 7

        font = QFont()
        font.setPixelSize(10)
        p.setFont(font)

        for i, val in enumerate(self._data):
            x = int(padding_x + i * bar_w)
            bar_h = int((val / max_val) * bar_area_h) if max_val else 0

            # Столбец
            if bar_h > 0:
                p.fillRect(
                    x + 3,
                    padding_top + bar_area_h - bar_h,
                    int(bar_w) - 6,
                    bar_h,
                    self.BAR_COLOR,
                )

            # Подпись дня
            p.setPen(QColor("#555"))
            p.drawText(x, h - label_h, int(bar_w), label_h,
                       Qt.AlignmentFlag.AlignCenter, self.DAYS_SHORT[i])

            # Цифра над столбцом
            if val > 0:
                p.setPen(QColor("#2E7D32"))
                p.drawText(x, padding_top + bar_area_h - bar_h - 12,
                           int(bar_w), 12,
                           Qt.AlignmentFlag.AlignCenter, str(val))

        # Ось X
        p.setPen(self.AXIS_COLOR)
        p.drawLine(padding_x, padding_top + bar_area_h,
                   w - padding_x, padding_top + bar_area_h)
        p.end()


#  Основной виджет
class ScheduleWidget(QWidget):

    DAY_MAP = {
        1: "Понедельник", 2: "Вторник",  3: "Среда",
        4: "Четверг",     5: "Пятница",  6: "Суббота",
        7: "Воскресенье",
    }
    DAY_MAP_REVERSE = {v: k - 1 for k, v in DAY_MAP.items()}

    def __init__(self, schedule_engine):
        super().__init__()
        self.engine = schedule_engine
        self.current_editing_index: int = -1   # -1 = новое занятие

        self._build_ui()

        # Таймер обратного отсчёта
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._update_countdown)
        self._timer.start()

        # Первичная загрузка
        today_name = self.DAY_MAP[QDate.currentDate().dayOfWeek()]
        # Выставляем комбобокс без срабатывания сигнала
        self.day_selector.blockSignals(True)
        self.day_selector.setCurrentText(today_name)
        self.day_selector.blockSignals(False)

        self.load_lessons_for_day(today_name)
        self._refresh_chart()

    #  Построение UI
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(4)
        root.setContentsMargins(6, 6, 6, 6)

        # Верхняя панель
        top = QHBoxLayout()

        add_btn = QPushButton("📚 Добавить занятие")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self.on_add_clicked)
        top.addWidget(add_btn)

        today_btn = QPushButton("📅 Сегодня")
        today_btn.setFixedHeight(32)
        today_btn.clicked.connect(self.on_today_clicked)
        top.addWidget(today_btn)

        self.day_selector = QComboBox()
        self.day_selector.addItems(list(self.DAY_MAP.values()))
        self.day_selector.setFixedHeight(32)
        self.day_selector.currentIndexChanged.connect(self.on_day_changed)
        top.addWidget(self.day_selector)

        top.addStretch()

        # Обратный отсчёт
        self.countdown_label = QLabel("⏱ —")
        self.countdown_label.setStyleSheet(
            "font-size:13px; color:#555; padding:0 6px;"
        )
        top.addWidget(self.countdown_label)

        root.addLayout(top)

        # Основная область
        main = QHBoxLayout()
        main.setSpacing(8)

        # Левая колонка: календарь + кнопки недели + график
        left = QVBoxLayout()
        left.setSpacing(4)

        self.calendar = QCalendarWidget()
        self.calendar.setFixedSize(260, 220)
        self.calendar.setGridVisible(True)
        self.calendar.clicked.connect(self.on_calendar_click)
        left.addWidget(self.calendar)

        week_nav = QHBoxLayout()
        prev_btn = QPushButton("← Назад")
        prev_btn.clicked.connect(lambda: self.calendar.setSelectedDate(
            self.calendar.selectedDate().addDays(-7)
        ))
        next_btn = QPushButton("Вперёд →")
        next_btn.clicked.connect(lambda: self.calendar.setSelectedDate(
            self.calendar.selectedDate().addDays(7)
        ))
        week_nav.addWidget(prev_btn)
        week_nav.addWidget(next_btn)
        left.addLayout(week_nav)

        # Задание 4: гистограмма нагрузки
        chart_header = QLabel("📊 Нагрузка по дням")
        chart_header.setStyleSheet("font-size:12px; color:#555; margin-top:6px;")
        left.addWidget(chart_header)

        self.load_chart = LoadChart()
        left.addWidget(self.load_chart)

        left.addStretch()
        main.addLayout(left)

        # Правая колонка: список / форма
        right = QVBoxLayout()
        right.setSpacing(4)

        # Заголовок текущего дня
        self.day_title_label = QLabel()
        self.day_title_label.setStyleSheet(
            "font-size:15px; font-weight:bold; color:#333; padding:4px 0;"
        )
        right.addWidget(self.day_title_label)

        # Список занятий
        self.list_container = QWidget()
        list_lay = QVBoxLayout(self.list_container)
        list_lay.setContentsMargins(0, 0, 0, 0)

        self.lesson_list = QListWidget()
        self.lesson_list.setAlternatingRowColors(True)
        self.lesson_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        list_lay.addWidget(self.lesson_list)

        # Кнопка удаления
        self.del_btn = QPushButton("🗑 Удалить выбранное")
        self.del_btn.clicked.connect(self.on_delete_clicked)
        list_lay.addWidget(self.del_btn)

        right.addWidget(self.list_container)

        # Форма добавления/редактирования
        self.form_container = QWidget()
        self.form_container.hide()
        form_lay = QFormLayout(self.form_container)
        form_lay.setSpacing(8)

        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Название предмета")
        form_lay.addRow("Предмет:", self.name_field)

        self.day_field = QComboBox()
        self.day_field.addItems(list(self.DAY_MAP.values()))
        form_lay.addRow("День недели:", self.day_field)

        self.time_start_field = QTimeEdit()
        self.time_start_field.setDisplayFormat("HH:mm")
        self.time_start_field.setTime(QTime(8, 0))
        form_lay.addRow("Начало:", self.time_start_field)

        self.time_end_field = QTimeEdit()
        self.time_end_field.setDisplayFormat("HH:mm")
        self.time_end_field.setTime(QTime(9, 30))
        form_lay.addRow("Окончание:", self.time_end_field)

        self.type_field = QComboBox()
        self.type_field.addItems(["Лекция", "Практика", "Самоподготовка", "Семинар", "Лабораторная"])
        form_lay.addRow("Тип:", self.type_field)

        self.room_field = QLineEdit()
        self.room_field.setPlaceholderText("Номер аудитории")
        form_lay.addRow("Аудитория:", self.room_field)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("✅ Сохранить")
        self.save_btn.clicked.connect(self.on_save_clicked)
        self.cancel_btn = QPushButton("❌ Отмена")
        self.cancel_btn.clicked.connect(self.hide_form)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        form_lay.addRow("", btn_row)

        right.addWidget(self.form_container)
        main.addLayout(right, 1)
        root.addLayout(main, 1)

    #  Навигация / обработчики
    def on_today_clicked(self):
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        day_name = self.DAY_MAP[today.dayOfWeek()]
        self.day_selector.blockSignals(True)
        self.day_selector.setCurrentText(day_name)
        self.day_selector.blockSignals(False)
        self.load_lessons_for_day(day_name)

    def on_day_changed(self, index: int):
        day_name = self.DAY_MAP[index + 1]
        self.load_lessons_for_day(day_name)

    def on_calendar_click(self, date: QDate):
        day_name = self.DAY_MAP[date.dayOfWeek()]
        self.day_selector.blockSignals(True)
        self.day_selector.setCurrentText(day_name)
        self.day_selector.blockSignals(False)
        self.load_lessons_for_day(day_name)

    def on_add_clicked(self):
        self.current_editing_index = -1
        # Предзаполняем день из текущего выбора
        current_day = self.day_selector.currentText()
        self.day_field.setCurrentText(current_day)
        self.name_field.clear()
        self.time_start_field.setTime(QTime(8, 0))
        self.time_end_field.setTime(QTime(9, 30))
        self.type_field.setCurrentIndex(0)
        self.room_field.clear()
        self.show_form()

    def on_item_double_clicked(self, item: QListWidgetItem):
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx < 0:
            return
        self.current_editing_index = idx
        self._populate_form(idx)
        self.show_form()

    def on_delete_clicked(self):
        item = self.lesson_list.currentItem()
        if item is None:
            return
        idx = item.data(Qt.ItemDataRole.UserRole)
        if idx is None or idx < 0:
            return
        lesson = self.engine.lessons[idx]
        reply = QMessageBox.question(
            self, "Удалить занятие",
            f"Удалить «{lesson['name']}» ({lesson['day_of_week']}, "
            f"{lesson['start_time']}–{lesson['end_time']})?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.engine.delete_lesson(idx)
            self.load_lessons_for_day(self.day_selector.currentText())
            self._refresh_chart()

    #  Форма
    def show_form(self):
        self.list_container.hide()
        self.form_container.show()

    def hide_form(self):
        self.form_container.hide()
        self.list_container.show()

    def _populate_form(self, idx: int):
        d = self.engine.lessons[idx]
        self.name_field.setText(d["name"])
        self.day_field.setCurrentText(d["day_of_week"])
        self.time_start_field.setTime(QTime.fromString(d["start_time"], "HH:mm"))
        self.time_end_field.setTime(QTime.fromString(d["end_time"],   "HH:mm"))
        self.type_field.setCurrentText(d.get("lesson_type", "Лекция"))
        self.room_field.setText(d.get("room", ""))

    def on_save_clicked(self):
        # Читаем время строго через QTime
        t_start = self.time_start_field.time()
        t_end   = self.time_end_field.time()
        start_str = t_start.toString("HH:mm")
        end_str   = t_end.toString("HH:mm")

        lesson_obj = Lesson(
            name        = self.name_field.text().strip(),
            day_of_week = self.day_field.currentText(),
            start_time  = start_str,
            end_time    = end_str,
            lesson_type = self.type_field.currentText(),
            room        = self.room_field.text().strip(),
        )

        try:
            if self.current_editing_index == -1:
                self.engine.create_lesson(lesson_obj)
            else:
                self.engine.update_lesson(self.current_editing_index, lesson_obj)
        except ValueError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            return
        except Exception as e:
            QMessageBox.critical(self, "Критическая ошибка", str(e))
            return

        self.hide_form()
        self.load_lessons_for_day(self.day_selector.currentText())
        self._refresh_chart()

    #  Список занятий
    def load_lessons_for_day(self, day_name: str):
        self.lesson_list.clear()
        self.day_title_label.setText(f"📋 {day_name}")

        try:
            tz   = ZoneInfo(get_localzone_name())
            now  = datetime.datetime.now(tz)
        except Exception:
            now = datetime.datetime.now()

        lessons = self.engine.get_lessons_for_day(day_name)

        if not lessons:
            item = QListWidgetItem()
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            item.setSizeHint(QSize(0, 40))
            lbl = QLabel("<i style='color:#999;'>Занятий в этот день нет</i>")
            lbl.setContentsMargins(12, 8, 12, 8)
            self.lesson_list.addItem(item)
            self.lesson_list.setItemWidget(item, lbl)
            return

        for lesson in sorted(lessons, key=lambda x: x.start_time):
            sh, sm = map(int, lesson.start_time.split(":"))
            eh, em = map(int, lesson.end_time.split(":"))
            s_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            e_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)

            cur_dow = now.weekday()          # 0=Пн
            les_dow = self.DAY_MAP_REVERSE[day_name]

            if cur_dow > les_dow or (cur_dow == les_dow and e_dt <= now):
                border, badge_bg, badge_fg, badge_txt = "#AAA","#EEE","#888","Прошедшее"
            elif cur_dow == les_dow and s_dt <= now < e_dt:
                border, badge_bg, badge_fg, badge_txt = "#DAA520","#FFF8DC","#B8860B","Идёт сейчас"
            else:
                border, badge_bg, badge_fg, badge_txt = "#4CAF50","#E8F5E9","#2E7D32","Запланировано"

            room_txt = lesson.room or "—"

            html = (
                f"<div style='font-family:Arial,sans-serif;padding:6px 10px;"
                f"border-left:4px solid {border};'>"
                f"<table width='100%' cellspacing='0' cellpadding='0'><tr>"
                f"<td><b style='font-size:13px;color:#1a1a1a;'>{lesson.name}</b></td>"
                f"<td align='right'>"
                f"<span style='font-size:10px;background:{badge_bg};color:{badge_fg};"
                f"padding:1px 6px;border-radius:7px;font-weight:bold;'>{badge_txt}</span>"
                f"</td></tr></table>"
                f"<div style='margin-top:2px;color:#555;font-size:11px;'>"
                f"🕐 <b>{lesson.start_time}–{lesson.end_time}</b>"
                f"&nbsp;|&nbsp;{lesson.lesson_type}"
                f"&nbsp;|&nbsp;🚪 {room_txt}"
                f"</div></div>"
            )

            lesson_dict = lesson.to_dict()
            global_idx = next(
                (i for i, d in enumerate(self.engine.lessons)
                 if d["day_of_week"] == lesson_dict["day_of_week"]
                 and d["start_time"] == lesson_dict["start_time"]
                 and d["name"] == lesson_dict["name"]),
                -1,
            )

            item = QListWidgetItem()
            item.setSizeHint(QSize(0, 66))
            item.setData(Qt.ItemDataRole.UserRole, global_idx)

            lbl = QLabel(html)
            lbl.setTextFormat(Qt.TextFormat.RichText)
            lbl.setWordWrap(True)

            self.lesson_list.addItem(item)
            self.lesson_list.setItemWidget(item, lbl)

    #  Обратный отсчёт
    def _update_countdown(self):
        try:
            tz  = ZoneInfo(get_localzone_name())
            now = datetime.datetime.now(tz)
        except Exception:
            now = datetime.datetime.now()

        today_dow_name = self.DAY_MAP[now.isoweekday()]   # isoweekday: 1=Пн
        lessons_today  = self.engine.get_lessons_for_day(today_dow_name)

        # Ищем текущее занятие
        for lesson in lessons_today:
            sh, sm = map(int, lesson.start_time.split(":"))
            eh, em = map(int, lesson.end_time.split(":"))
            s_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            e_dt = now.replace(hour=eh, minute=em, second=0, microsecond=0)
            if s_dt <= now < e_dt:
                remaining = int((e_dt - now).total_seconds())
                m, s = divmod(remaining, 60)
                self.countdown_label.setText(
                    f"⏱ Идёт: <b>{lesson.name}</b> — осталось {m}м {s:02d}с"
                )
                self.countdown_label.setStyleSheet("font-size:12px;color:#B8860B;")
                return

        # Ищем следующее занятие сегодня
        future = sorted(
            [l for l in lessons_today
             if now < now.replace(
                 hour=int(l.start_time.split(":")[0]),
                 minute=int(l.start_time.split(":")[1]),
                 second=0, microsecond=0
             )],
            key=lambda l: l.start_time,
        )
        if future:
            nxt = future[0]
            sh, sm = map(int, nxt.start_time.split(":"))
            s_dt = now.replace(hour=sh, minute=sm, second=0, microsecond=0)
            remaining = int((s_dt - now).total_seconds())
            h, rem = divmod(remaining, 3600)
            m, s   = divmod(rem, 60)
            parts = []
            if h: parts.append(f"{h}ч")
            parts.append(f"{m}м {s:02d}с")
            self.countdown_label.setText(
                f"⏱ Следующая: <b>{nxt.name}</b> через {''.join(parts)}"
            )
            self.countdown_label.setStyleSheet("font-size:12px;color:#2E7D32;")
            return

        self.countdown_label.setText("⏱ Занятий сегодня больше нет")
        self.countdown_label.setStyleSheet("font-size:12px;color:#888;")

    #  График нагрузки
    def _refresh_chart(self):
        self.load_chart.set_data(self.engine.get_stats())
