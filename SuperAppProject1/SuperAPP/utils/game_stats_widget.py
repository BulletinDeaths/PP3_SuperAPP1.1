import json
import os
import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QSpinBox, QPlainTextEdit, QCheckBox, QGroupBox,
    QLabel, QMessageBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSizePolicy
from PyQt6.QtGui import QFont, QPixmap, QPainter, QPaintEvent, QColor
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure



class PieChart(Canvas):
    """Простой виджет для круговой диаграммы"""
    def __init__(self, parent=None):
        fig = Figure(figsize=(4, 4), dpi=72)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.parent = parent
        self.draw_chart([])

    def draw_chart(self, distribution: list):
        labels = [f"{stars}★ ({count})" for stars, count in distribution]
        sizes = [count for _, count in distribution]

        if not distribution:  # <--- ИСПРАВЛЕНИЕ: Проверка на пустой список
            self.ax.clear()
            self.ax.axis('off')
            self.ax.text(0.5, 0.5, "Нет данных", ha='center', va='center', fontsize=14)
        else:
            colors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff']
            explode = [0.1 if size != max(sizes) else 0 for size in sizes]

            self.ax.clear()
            self.ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                        shadow=True, startangle=90, colors=colors[:len(labels)], explode=explode)
            self.ax.axis('equal')

        self.draw_idle()


class GameStatsWidget(QWidget):
    """Вкладка для сбора и анализа статистики прохождения игр."""

    def __init__(self):
        super().__init__()

        # *** НАСТРОЙКА ХРАНЕНИЯ ДАННЫХ ***
        self.games_catalog = self.load_json("data/games_catalog.json")
        self.player_progress = self.load_json("data/player_progress.json")

        # *** СОЗДАЕМ ИНТЕРФЕЙС ***
        main_layout = QVBoxLayout(self)

        # Верхняя панель: Заголовок и кнопка "Оценить"
        header = QHBoxLayout()
        title_label = QLabel("🎮 Статистика игр")
        title_font = QFont(); title_font.setPointSize(18); title_font.setBold(True)
        title_label.setFont(title_font)
        header.addWidget(title_label)

        rate_btn = QPushButton("☆ Поставить оценку")
        rate_btn.clicked.connect(self.on_rate_game_clicked)
        header.addWidget(rate_btn)

        main_layout.addLayout(header)

        # Центральная область: Список игр и Диаграмма
        central_grid = QHBoxLayout()

        # Левая сторона: Каталог игр (Список)
        games_box = QGroupBox("Доступные игры")
        games_layout = QVBoxLayout(games_box)

        self.games_table = QTableWidget()
        self.games_table.setColumnCount(3)
        self.games_table.setHorizontalHeaderLabels([
            "Название", "Моя оценка", "Количество достижений"
        ])
        self.games_table.horizontalHeader().setStretchLastSection(True)
        self.games_table.verticalHeader().setVisible(False)
        self.games_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.games_table.cellClicked.connect(self.on_game_selected)  # Одно нажатие
        self.games_table.cellDoubleClicked.connect(self.on_game_opened)  # Двойное нажатие

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.games_table)
        games_layout.addWidget(scroll_area)
        central_grid.addWidget(games_box, stretch=2)

        # Правая сторона: Круговая диаграмма (Matplotlib)
        chart_box = QGroupBox("Распределение моих оценок")
        chart_layout = QVBoxLayout(chart_box)

        self.chart_canvas = PieChart(parent=self)
        self.chart_canvas.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        chart_layout.addWidget(self.chart_canvas)
        central_grid.addWidget(chart_box, stretch=1)

        main_layout.addLayout(central_grid)

        # Нижняя часть: Форма для заполнения (Скрытая)
        self.form_container = QWidget()
        form_layout = QVBoxLayout(self.form_layout.addWidget(self.form_container))

        # Группа: Название и Оценка игры
        game_group = QHBoxLayout()
        self.title_label = QLabel("")  # Название игры (только для чтения)
        self.title_label.setFont(QFont("Arial", 14, weight=QFont.Bold))
        game_group.addWidget(self.title_label)

        rating_label = QLabel("Моя оценка (звёзды):")
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(1, 5)
        game_group.addWidget(rating_label)
        game_group.addWidget(self.rating_spinbox)
        form_layout.addLayout(game_group)

        # Группа: Достижения (Checkbox'ы)
        self.achievement_group = QGroupBox("Мои успехи в этой игре:")
        achievement_layout = QVBoxLayout()
        self.checkboxes = []  # Для хранения ссылок
        self.achievement_group.setLayout(achievement_layout)
        form_layout.addWidget(self.achievement_group)

        # Группа: Подробный отзыв
        review_group = QHBoxLayout()
        review_label = QLabel("Мой отзыв:")
        self.review_textarea = QPlainTextEdit()
        review_group.addWidget(review_label)
        review_group.addWidget(self.review_textarea)
        form_layout.addLayout(review_group)

        # Кнопки формы
        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("✅ Сохранить")
        self.save_btn.clicked.connect(self.on_save_clicked)
        btn_row.addWidget(self.save_btn)

        cancel_btn = QPushButton("❌ Отмена")
        cancel_btn.setProperty("cancel", True)
        cancel_btn.clicked.connect(self.hide_form)
        btn_row.addWidget(cancel_btn)

        form_layout.addLayout(btn_row)
        self.form_container.hide()  # Скрываем форму по умолчанию
        main_layout.addWidget(self.form_container)

        # *** КОНЕЦ ИНТЕРФЕЙСА ***

        # Инициализация
        self.load_games()

        print("Каталог игр:", self.games_catalog)
        print("Прогресс пользователя:", self.player_progress)

    ### РАБОТА С ФАЙЛАМИ ###
    def load_json(self, path: str) -> any:
        """Безопасная загрузка JSON-файлов."""
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_json(self, path: str, data: any) -> None:
        """Сохранение данных обратно в JSON."""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    ### ОБРАБОТЧИКИ СИГНАЛОВ ###
    def on_rate_game_clicked(self):
        """Нажата кнопка 'Поставить оценку'.
        Если ни одна игра не выбрана, покажем предупреждение.
        """
        selected_rows = set(self.games_table.selectionModel().selectedRows())
        if not selected_rows:
            QMessageBox.information(self, "Внимание", "Сначала выберите игру из списка.")
            return

        # Если выбрано несколько игр, работаем только с первой
        first_row = next(iter(selected_rows)).row()
        self.on_game_selected(first_row, 0)  # Симулируем выбор
        self.show_form()

    def on_game_selected(self, row: int, column: int):
        """Одно нажатие по ячейке таблицы.
        Выбираем игру, подгружаем её данные и заполняем форму.
        """
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        self.current_game_id = game_id

        # Загружаем шаблон игры из каталога
        catalog_entry = next((g for g in self.games_catalog if g["id"] == game_id), {})
        if not catalog_entry:
            return

        # Загружаем прогресс пользователя для этой игры
        player_entry = self.player_progress.get(game_id, {})

        # Заполняем форму
        self.title_label.setText(catalog_entry["title"])
        self.rating_spinbox.setValue(player_entry.get("rating", 1))

        # Генерируем CheckBox'ы для достижений
        self.clear_checkboxes()
        for achievement in catalog_entry.get("achievements", []):
            cb = QCheckBox(achievement)
            cb.setChecked(achievement in player_entry.get("completed", []))
            self.checkboxes.append(cb)
            self.achievement_group.layout().addWidget(cb)

        self.review_textarea.setPlainText(player_entry.get("review", ""))

    def on_game_opened(self, row: int, column: int):
        """Двойной клик по ячейке таблицы.
        Переходим в режим детального просмотра игры.
        """
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        catalog_entry = next((g for g in self.games_catalog if g["id"] == game_id), {})
        if not catalog_entry:
            return

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Детали игры: {catalog_entry['title']}")
        msg.setText(catalog_entry.get("description", "(Нет описания)"))
        msg.exec()

    def on_save_clicked(self):
        """Срабатывает при нажатии кнопки 'Сохранить'.
        Сохраняет оценку, прогресс по достижениям и отзыв.
        """
        if not hasattr(self, "current_game_id"):
            return

        # Собираем данные
        progress = {
            "rating": self.rating_spinbox.value(),
            "completed": [cb.text() for cb in self.checkboxes if cb.isChecked()],
            "review": self.review_textarea.toPlainText().strip()
        }

        # Сохраняем в прогресс
        self.player_progress[self.current_game_id] = progress
        self.save_json("data/player_progress.json", self.player_progress)

        # Обновляем таблицу и график
        self.load_games()
        self.hide_form()

    ### РАБОТА С ФОРМОЙ ###

    def show_form(self):
        """Показывает форму и скрывает таблицу."""
        self.games_table.hide()
        self.form_container.show()

    def hide_form(self):
        """Прячет форму и показывает таблицу."""
        self.form_container.hide()
        self.games_table.show()

    def clear_checkboxes(self):
        """Очистка группы CheckBox'ов перед загрузкой новой игры."""
        while self.achievement_group.layout().count():
            child = self.achievement_group.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.checkboxes.clear()

    ### РАБОТА С ДАННЫМИ ###

    def load_games(self):
        """Загружает все игры из каталога и строит таблицу."""
        self.games_table.setRowCount(len(self.games_catalog))

        for row, game in enumerate(self.games_catalog):
            # Столбец 1: Название игры (ссылка на ID)
            title_item = QTableWidgetItem(game["title"])
            title_item.setData(Qt.ItemDataRole.UserRole, game["id"])  # Скрытое поле
            title_item.setToolTip(game.get("description", ""))
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # <--- Защита от редактирования
            self.games_table.setItem(row, 0, title_item)

            # Столбец 2: Моя оценка
            progress = self.player_progress.get(game["id"], {})
            rating_item = QTableWidgetItem(f"{progress.get('rating', '-')} ☆")
            rating_item.setFlags(rating_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # <--- Защита от редактирования
            self.games_table.setItem(row, 1, rating_item)

            # Столбец 3: Количество выполненных достижений
            completed_count = len(progress.get("completed", []))
            total_count = len(game.get("achievements", []))
            ratio = f"{completed_count}/{total_count}" if total_count else "-"
            achievements_item = QTableWidgetItem(ratio)
            achievements_item.setFlags(achievements_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # <--- Защита от редактирования
            self.games_table.setItem(row, 2, achievements_item)

        # Строим график распределения оценок
        ratings = [sess.get("rating") for sess in self.player_progress.values()]
        distribution = [(stars, ratings.count(stars)) for stars in range(1, 6)]
        self.chart_canvas.draw_chart(distribution)