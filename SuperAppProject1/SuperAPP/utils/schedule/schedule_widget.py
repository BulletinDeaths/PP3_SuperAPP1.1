from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QCalendarWidget, QListWidget, QPushButton, QLineEdit,
    QComboBox, QTimeEdit, QLabel, QMessageBox, QListWidgetItem, QFormLayout
)
from PyQt6.QtCore import QDate, QTimer, Qt, QTime
from PyQt6.QtGui import QColor

import datetime

from zoneinfo import ZoneInfo
from tzlocal import get_localzone_name

from .schedule_engine import Lesson


class ScheduleWidget(QWidget):
    """
    Виджет для управления расписанием.
    Отображает сетку недель (календарь) и список занятий.
    Позволяет добавлять, удалять и редактировать уроки.
    """

    # Константа для перевода чисел в дни недели
    DAY_MAP = {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье"
    }

    # ✅ Фиксим ошибку: Раньше использовался несуществующий DAY_MAP_REVERSE
    # Создадим правильную обратную карту (номер дня -> цифра)
    DAY_MAP_REVERSE = {value: key - 1 for key, value in DAY_MAP.items()}

    def __init__(self, schedule_engine):
        super().__init__()

        # Ядро логики (база данных и операции над ней)
        self.engine = schedule_engine

        # Переменные состояния
        self.current_editing_index = None  # Индекс урока, который редактируется (-1 = новый)

        # *** СОЗДАЕМ ИНТЕРФЕЙС ***
        layout = QVBoxLayout(self)

        # === НАВИГАЦИОННАЯ ПАНЕЛЬ (Верхний ряд) ===
        top_bar = QHBoxLayout()
        top_bar.setSpacing(20)  # Расстояние между элементами

        # Кнопка "Добавить" (быстрое создание нового занятия)
        add_btn = QPushButton("📚 Добавить занятие")
        add_btn.clicked.connect(self.on_add_clicked)
        top_bar.addWidget(add_btn)

        # Кнопка "Сегодня" (переход на текущую дату)
        today_btn = QPushButton("Сегодня")
        today_btn.clicked.connect(self.on_today_clicked)
        top_bar.addWidget(today_btn)

        # Комбо-бокс выбора дня недели
        self.day_selector = QComboBox()
        self.day_selector.addItems(list(self.DAY_MAP.values()))  # Наполнение из константы
        self.day_selector.currentIndexChanged.connect(self.on_day_changed)
        top_bar.addWidget(self.day_selector)

        # Разделительная линия для красоты
        separator = QLabel("|")
        separator.setStyleSheet("font-size: 24px;")
        top_bar.addWidget(separator)

        # Временная зона (можно убрать, если не актуально)
        timezone_label = QLabel("⏰ Москва")
        top_bar.addWidget(timezone_label)

        layout.addLayout(top_bar)  # Прикрепляем панель сверху

        # === ОСНОВНОЙ ЭКРАН (Календарь и Занятия) ===
        grid = QHBoxLayout()

        # Левая колонка: Календарь (Компактный)
        calendar_col = QVBoxLayout()
        self.calendar = QCalendarWidget()
        # ✅ СДЕЛАЛИ КВАДРАТНЫМ (300x300)
        self.calendar.setFixedSize(300, 300)  
        self.calendar.clicked.connect(self.on_calendar_click)  # Обработка клика мышью
        calendar_col.addWidget(self.calendar)

        # Панель навигации по неделе (Стрелки)
        week_nav = QHBoxLayout()
        prev_week_btn = QPushButton("← Неделя назад")
        prev_week_btn.clicked.connect(self.move_calendar_prev_week)
        week_nav.addWidget(prev_week_btn)

        next_week_btn = QPushButton("Неделя вперед →")
        next_week_btn.clicked.connect(self.move_calendar_next_week)
        week_nav.addWidget(next_week_btn)

        calendar_col.addLayout(week_nav)

        grid.addLayout(calendar_col)

        # Правая колонка: Список занятий и Форма
        lessons_col = QVBoxLayout()

        # Контейнер для списка (будет прятаться при показе формы)
        self.list_container = QWidget()
        list_layout = QVBoxLayout()

        # Сам список занятий
        self.lesson_list = QListWidget()
        self.lesson_list.itemDoubleClicked.connect(self.on_item_double_clicked)
        list_layout.addWidget(self.lesson_list)

        # Ранее кнопка "Добавить" стояла тут. Теперь она переехала в TOP_BAR
        # add_btn = QPushButton("Добавить занятие")
        # add_btn.clicked.connect(self.on_add_clicked)
        # list_layout.addWidget(add_btn)

        self.list_container.setLayout(list_layout)
        lessons_col.addWidget(self.list_container)

        # Контейнер для формы (будет показывать поля ввода)
        self.form_container = QWidget()
        form_layout = QFormLayout()  # Удобная сетка для полей

        # Поля формы
        self.name_field = QLineEdit()
        form_layout.addRow("Предмет:", self.name_field)

        self.day_field = QComboBox()
        self.day_field.addItems(list(self.DAY_MAP.values()))
        form_layout.addRow("День недели:", self.day_field)

        self.time_start_field = QTimeEdit()
        form_layout.addRow("Начало:", self.time_start_field)

        self.time_end_field = QTimeEdit()
        form_layout.addRow("Окончание:", self.time_end_field)

        self.type_field = QComboBox()
        self.type_field.addItems(["Лекция", "Практика", "Самоподготовка"])
        form_layout.addRow("Тип:", self.type_field)

        self.room_field = QLineEdit()
        form_layout.addRow("Аудитория:", self.room_field)  # <--- ИСПРАВЛЕННАЯ СТРОКА

        # Кнопки формы
        btn_row = QHBoxLayout()
        self.save_button = QPushButton("✅ Сохранить")
        self.save_button.clicked.connect(self.on_save_clicked)
        btn_row.addWidget(self.save_button)

        cancel_button = QPushButton("❌ Отмена")
        cancel_button.setProperty("cancel", True)  # Атрибут для красного стиля
        cancel_button.clicked.connect(self.hide_form)
        btn_row.addWidget(cancel_button)

        form_layout.addRow("", btn_row)  # Пустая метка для правильной сетки

        self.form_container.setLayout(form_layout)
        self.form_container.hide()  # Скрываем форму по умолчанию
        lessons_col.addWidget(self.form_container)

        grid.addLayout(lessons_col)
        layout.addLayout(grid)

        # *** КОНЕЦ ИНТЕРФЕЙСА ***

        # Инициализация
        self.load_current_week()  # Показываем текущую неделю в календаре
        self.select_today()  # Выделяем сегодня
        self.load_lessons_for_day(self.get_current_day())  # Загружаем уроки на сегодня

    ### НАВИГАЦИЯ И УПРАВЛЕНИЕ ###

    def move_calendar_prev_week(self):
        """Перемещает календарь на неделю назад"""
        current = self.calendar.selectedDate()
        new_date = current.addDays(-7)
        self.calendar.setSelectedDate(new_date)

    def move_calendar_next_week(self):
        """Перемещает календарь на неделю вперёд"""
        current = self.calendar.selectedDate()
        new_date = current.addDays(+7)
        self.calendar.setSelectedDate(new_date)

    def select_today(self):
        """Подсвечивает сегодняшнюю дату красным"""
        today = QDate.currentDate()
        fmt = self.calendar.paintCell  # Сохраняем оригинал
        def custom_paint(painter, rect, date):
            if date == today:
                painter.fillRect(rect, QColor("#FFCCCC"))  # Светло-красный
            fmt(painter, rect, date)
        self.calendar.paintCell = custom_paint

    ### РАБОТА С ДНЕМ НЕДЕЛИ ###

    def get_current_day(self) -> str:
        """Возвращает название текущего дня недели (русскими буквами)"""
        num = QDate.currentDate().dayOfWeek()
        return self.DAY_MAP[num]

    def get_selected_day(self) -> str:
        """Получает выбранный в комбобоксе день недели"""
        return self.day_selector.currentText()

    ### ОБРАБОТЧИКИ СИГНАЛОВ ###

    def on_today_clicked(self):
        """Переходит на сегодняшний день в календаре и комбобоксе"""
        today = QDate.currentDate()
        self.calendar.setSelectedDate(today)
        self.day_selector.setCurrentText(self.get_current_day())
        self.load_lessons_for_day(self.get_current_day())

    def on_day_changed(self, index: int):
        """Меняется выбор дня в комбобоксе"""
        selected_day = self.DAY_MAP[index + 1]  # Индексы в ComboBox начинаются с 0, а дни с 1
        self.load_lessons_for_day(selected_day)

    def on_calendar_click(self, date: QDate):
        """Кликают мышью по календарю."""
        # Получаем порядковый номер дня недели (1-Пн, 7-Вс)
        day_number = date.dayOfWeek()
        # Через карту превращаем цифру в слово
        day_name = self.DAY_MAP[day_number]

        # Синхронизируем выпадающее меню с календарем
        self.day_selector.setCurrentText(day_name)
        self.load_lessons_for_day(day_name)

    def on_add_clicked(self):
        """Нажата кнопка 'Добавить' рядом со списком"""
        self.current_editing_index = -1  # Создание нового
        self.clear_form()  # <--- ОБЯЗАТЕЛЬНО ОЧИСТИМ ПОЛЯ
        self.show_form()

    def on_item_double_clicked(self, item: QListWidgetItem):
        """Двойной клик по уроку в списке"""
        idx = item.data(Qt.ItemDataRole.UserRole)  # Берем сохранённый индекс
        self.current_editing_index = idx
        self.populate_form(idx)
        self.show_form()

    ### РАБОТА С ФОРМОЙ ###

    def show_form(self):
        """Показывает форму и скрывает список"""
        self.list_container.hide()
        self.form_container.show()

    def hide_form(self):
        """Прячет форму и показывает список"""
        self.form_container.hide()
        self.list_container.show()

    def populate_form(self, lesson_idx: int):
        """Заполняет форму данными существующего урока"""
        lesson = self.engine.lessons[lesson_idx]

        self.name_field.setText(lesson['name'])
        self.day_field.setCurrentText(lesson['day_of_week'])

        # ✅ ФИКС: Преобразуем строки в QTime
        self.time_start_field.setTime(QTime.fromString(lesson['start_time'], "hh:mm"))
        self.time_end_field.setTime(QTime.fromString(lesson['end_time'], "hh:mm"))

        self.type_field.setCurrentText(lesson['lesson_type'])
        self.room_field.setText(lesson['room'])

    def clear_form(self):
        """Очищает все поля формы"""
        self.name_field.clear()
        self.day_field.setCurrentIndex(0)
        self.time_start_field.setTime("08:00")  # <--- ФИКС: Передаем строку, а не список
        self.time_end_field.setTime("09:30")    # <--- ФИКС: Передаем строку, а не список
        self.type_field.setCurrentIndex(0)
        self.room_field.clear()

    ### РАБОТА С БАЗОЙ ДАННЫХ ###

    def on_save_clicked(self):
        """Срабатывает при нажатии кнопки 'Сохранить'"""
        try:
            # Собираем данные из формы в словарь
            raw_data = {
                "name": self.name_field.text(),
                "day_of_week": self.day_field.currentText(),
                "start_time": self.time_start_field.text(),
                "end_time": self.time_end_field.text(),
                "lesson_type": self.type_field.currentText(),
                "room": self.room_field.text()
            }

            # Проверка на обязательное поле
            if not raw_data["name"].strip():
                QMessageBox.warning(self, "Ошибка", "Название предмета обязательно!")
                return

            # Преобразуем словарь в объект Lesson
            lesson_obj = Lesson(
                name=raw_data["name"],
                day_of_week=raw_data["day_of_week"],
                start_time=raw_data["start_time"],  # Начало
                end_time=raw_data["end_time"],  # Окончание (Было дублем!)
                lesson_type=raw_data["lesson_type"],
                room=raw_data["room"]
            )

            # Определяем режим (Создание или Редактирование)
            if self.current_editing_index == -1:
                success = self.engine.create_lesson(lesson_obj)
            else:
                success = self.engine.update_lesson(self.current_editing_index, lesson_obj)

            if success:
                self.hide_form()
                self.load_lessons_for_day(self.get_selected_day())
            else:
                QMessageBox.warning(self, "Ошибка", "Неизвестная ошибка при сохранении.")

        except ValueError as ve:
            # Ядро выбросило исключение (занятое время или ночь)
            QMessageBox.critical(self, "Ошибка", str(ve))

        except Exception as ex:
            # Любая другая неожиданная ошибка
            QMessageBox.critical(self, "Критическая ошибка", f"Внутренняя ошибка: {str(ex)}")

    def load_lessons_for_day(self, day_name: str):
        """Загружает уроки для выбранного дня и рисует их в списке."""
        self.lesson_list.clear()

        # Получаем текущее время на компьютере пользователя
        # ZoneInfo - это стандартная библиотека Python 3.9+
        # Если у вас старая версия, поставьте: pip install tzlocal zoneinfo-backport
        now = datetime.datetime.now(ZoneInfo(get_localzone_name()))

        # Получаем уроки из ядра (модели)
        lessons = self.engine.get_lessons_for_day(day_name)

        # Проходим по каждому уроку и формируем красивый вывод
        for lesson in sorted(lessons, key=lambda x: x['start_time']):
            # Парсим время начала и окончания в нормальные объекты datetime
            start_hour, start_minute = map(int, lesson['start_time'].split(":"))
            end_hour, end_minute = map(int, lesson['end_time'].split(":"))

            # Создаем виртуальные моменты времени (как будто это сегодня)
            # Это нужно для математических сравнений
            start_dt = datetime.datetime(now.year, now.month, now.day, start_hour, start_minute)
            end_dt = datetime.datetime(now.year, now.month, now.day, end_hour, end_minute)

            # 💡 ЛОГИКА ОТРИЦАНИЯ 💡
            # Если выбран прошлый день (например, вчера), ВСЕ уроки считаются прошедшими
            is_past_day = (now.weekday() > self.DAY_MAP_REVERSE[day_name])

            # Если выбран будущий день (завтра-послезавтра), ВСЕ уроки считаются будущими
            is_future_day = (now.weekday() < self.DAY_MAP_REVERSE[day_name])

            # Если выбран текущий день (сегодня), смотрим на точное время
            is_current_day = (now.weekday() == self.DAY_MAP_REVERSE[day_name])

            # 🟢 🟡 🟣 ЦВЕТОВАЯ ЛОГИКА 🟤 🟦
            # 1. Если это ПРОШЛЫЙ день ИЛИ занятие закончилось сегодня
            if is_past_day or (is_current_day and end_dt < now):
                color = "#AAA"  # Серый (Прошедшее)

            # 2. Если это БУДУЩИЙ день ИЛИ занятие начнется позже
            elif is_future_day or (is_current_day and start_dt > now):
                color = "#0A0"  # Ярко-зеленый (Будущее)

            # 3. Если занятие идет прямо сейчас
            elif start_dt <= now <= end_dt:
                color = "#DAA520"  # Золотистый (Актуально)

            # 4. Если что-то пошло не так (защита от багов)
            else:
                color = "black"

            # Формируем HTML-текст для элемента списка
            # ✅ ФИКС: Добавил тег <html> для совместимости
            html = '<html><span style="color:{};">'.format(color)
            html += '{} – {}'.format(lesson['start_time'], lesson['end_time'])
            html += ' | <b>{}</b> | '.format(lesson['lesson_type'])
            html += '{}({})</span></html>'.format(lesson['name'], lesson['room'])

            # Создаем элемент списка и привязываем к нему внутренний индекс
            item = QListWidgetItem(html)
            item.setData(Qt.ItemDataRole.UserRole, self.engine.lessons.index(lesson))
            self.lesson_list.addItem(item)

    ### НАСТРОЙКА КАЛЕНДАРЯ ###

    def load_current_week(self):
        """Устанавливает выделение на текущую неделю, но не ограничивает календарь."""
        # today = QDate.currentDate()
        # monday = today.addDays(-(today.dayOfWeek() - 1))  # Первый день недели
        # sunday = monday.addDays(6)
        # self.calendar.setMinimumDate(monday)  # <---- УДАЛИ ЭТИ СТРОКИ
        # self.calendar.setMaximumDate(sunday)  # <---- УДАЛИ ЭТИ СТРОКИ
        self.select_today()  # Просто выделим сегодня