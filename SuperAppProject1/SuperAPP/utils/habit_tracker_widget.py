from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
    QLineEdit, QPushButton, QLabel, QMessageBox,
    QFileDialog, QFrame
)
from PyQt6.QtCore import Qt
from datetime import date


class HabitTrackerWidget(QWidget):
    def __init__(self, model):
        """
        Виджет для вкладки "Трекер привычек".

        Args:
            model: Экземпляр модели данных HabitTrackerModel.
        """
        super().__init__()
        self.model = model

        # --- ОСНОВНОЙ СЛОЙ ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)  # Убираем зазоры между основными блоками
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- БЛОК 1: Управление привычками (Панель сверху) ---
        control_frame = QFrame()
        control_frame.setObjectName("controlPanel")
        control_layout = QHBoxLayout(control_frame)
        control_layout.setContentsMargins(15, 10, 15, 8)

        self.habit_name_input = QLineEdit()
        self.habit_name_input.setPlaceholderText("Новая привычка...")
        self.habit_name_input.returnPressed.connect(self.add_habit)  # Можно добавлять по Enter

        add_button = QPushButton("➕ Добавить")
        add_button.clicked.connect(self.add_habit)

        delete_button = QPushButton("🗑️ Удалить")
        delete_button.clicked.connect(self.delete_habit)

        control_layout.addWidget(self.habit_name_input)
        control_layout.addWidget(add_button)
        control_layout.addWidget(delete_button)

        main_layout.addWidget(control_frame)

        # --- БЛОК 2: Список и Детали (Разделение экрана) ---
        details_layout = QHBoxLayout()
        details_layout.setContentsMargins(15, 10, 15, 10)

        # Левая часть: Список привычек
        self.habits_list = QListWidget()
        self.habits_list.currentRowChanged.connect(self.update_habit_details)
        details_layout.addWidget(self.habits_list, 3)

        # Правая часть: Контейнер для деталей
        details_box = QWidget()
        details_box.setObjectName("detailsBox")
        self.details_layout_inner = QVBoxLayout(details_box)
        self.details_layout_inner.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Заголовок блока деталей
        self.details_name_label = QLabel("<h2>Выберите привычку слева</h2>")
        self.streaks_label = QLabel("Серия: <b>0</b> дней подряд | Лучшая серия: <b>0</b> дней")

        stats_frame = QFrame()
        stats_frame.setObjectName("statsFrame")
        stats_layout = QVBoxLayout(stats_frame)
        stats_layout.addWidget(self.details_name_label)
        stats_layout.addWidget(self.streaks_label)

        # Кнопки для отметки выполнения
        mark_buttons_layout = QHBoxLayout()
        self.mark_done_btn = QPushButton("✅ Выполнено сегодня")
        self.mark_skipped_btn = QPushButton("❌ Пропущено сегодня")
        mark_buttons_layout.addWidget(self.mark_done_btn)
        mark_buttons_layout.addWidget(self.mark_skipped_btn)

        # Кнопки импорта/экспорта
        io_buttons_layout = QHBoxLayout()
        export_btn = QPushButton("💾 Экспорт (JSON)")
        import_btn = QPushButton("📥 Импорт (JSON)")
        io_buttons_layout.addWidget(export_btn)
        io_buttons_layout.addWidget(import_btn)

        # Собираем правый контейнер воедино
        self.details_layout_inner.addWidget(stats_frame)
        self.details_layout_inner.addLayout(mark_buttons_layout)
        self.details_layout_inner.addLayout(io_buttons_layout)

        details_layout.addWidget(details_box, 2)

        main_layout.addLayout(details_layout)

        # --- СТИЛИ (CSS для Qt) ---
        self.setStyleSheet("""
                    /* Стили для всей вкладки */
                    * {
                        font-size: 14px;
                        color: #333;
                    }

                    /* Панель управления сверху */
                    #controlPanel {
                        background-color: #f0f4f8;
                        border-bottom: 1px solid #d9e2ec;
                    }
                    #controlPanel QLineEdit {
                        padding: 8px;
                        border: 1px solid #ccc;
                        border-radius: 20px; /* Скругление углов поля ввода */
                        width: 250px;
                    }
                    /* Стильные кнопки с эмодзи */
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        font-size: 20px;
                        cursor: pointer;
                    }
                    QPushButton:hover {
                        color: #0078d4; /* Цвет иконки при наведении */
                    }
                    QPushButton:pressed {
                        color: #005a9e; /* Цвет иконки при нажатии */
                    }

                    /* Блок статистики справа */
                    #statsFrame {
                        background-color: white;
                        padding: 15px;
                        border-radius: 10px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                        margin-bottom: 15px;
                    }
                    #statsFrame h2 {
                        margin-top: 0;
                        color: #2c3e50;
                    }

                    /* Кнопки действий внизу */
                    QPushButton {
                    min-width: 160px; /* Сохраняем фиксированную ширину */
                    padding: 10px;
                    margin: 5px 0; /* Добавляем отступы между кнопками по вертикали */
                    
                    /* Делаем кнопку белой с черной рамкой */
                    background-color: white;
                    color: black;
                    border: 2px solid black;
                    
                    /* Убираем скругление углов, чтобы сделать их прямоугольными */
                    border-radius: 4px; 
                    
                    font-weight: bold;
                    }
                    /* При наведении курсора мышки */
                    QPushButton:hover {
                        /* Меняем фон на серый */
                        background-color: #e0e0e0; /* Светло-серый цвет */
                    }
                    /* В момент нажатия */
                    QPushButton:pressed {
                        /* Сдвигаем виджет вниз и вправо, создавая эффект "нажатия" */
                        top: 2px;
                        left: 2px;
                        background-color: #c0c0c0; /* Чуть более темный серый */
                    }
                """)

        # Инициализация данных
        self.update_habits_list()

        # Подключаем сигналы к слотам
        self.mark_done_btn.clicked.connect(lambda: self.mark_habit(True))
        self.mark_skipped_btn.clicked.connect(lambda: self.mark_habit(False))
        export_btn.clicked.connect(self.export_data)
        import_btn.clicked.connect(self.import_data)

    # --- Методы для обновления интерфейса ---

    def update_habits_list(self):
        """Обновляет список привычек в QListWidget."""
        self.habits_list.clear()
        for habit in self.model.habits:
            self.habits_list.addItem(habit.name)

    def update_habit_details(self, index):
        """Обновляет блок деталей при выборе привычки в списке."""
        if index == -1 or not self.model.habits:
            # Ничего не выбрано или нет привычек
            self.details_name_label.setText("<h2>Выберите привычку слева</h2>")
            self.streaks_label.setText("Серии:")
            return

        habit = self.model.habits[index]
        self.details_name_label.setText(f"<h2>{habit.name}</h2>")
        self.streaks_label.setText(
            f"Текущая серия: <b>{habit.current_streak} дн.</b><br>"
            f"Лучшая серия: <b>{habit.best_streak} дн.</b>"
        )

    # --- Методы для обработки действий пользователя ---

    def add_habit(self):
        """Обработчик кнопки 'Добавить'."""
        name = self.habit_name_input.text().strip()
        if name:
            self.model.add_habit(name)
            self.update_habits_list()
            self.habit_name_input.clear()
            # Выделяем только что добавленную привычку
            last_index = len(self.model.habits) - 1
            self.habits_list.setCurrentRow(last_index)

    def delete_habit(self):
        """Обработчик кнопки 'Удалить'."""
        index = self.habits_list.currentRow()
        if index != -1:
            reply = QMessageBox.question(
                self, 'Подтверждение',
                f"Вы действительно хотите удалить привычку '{self.model.get_habit(index).name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.model.delete_habit(index)
                self.update_habits_list()
                # Очищаем детали после удаления
                self.update_habit_details(-1)

    def mark_habit(self, is_completed: bool):
        """Отмечает выбранную привычку как выполненную или пропущенную за сегодня."""
        index = self.habits_list.currentRow()
        if index != -1:
            today = date.today()
            habit = self.model.get_habit(index)
            if habit:
                habit.add_check(today, is_completed)
                # Сразу сохраняем изменения
                self.model.save_to_file()
                # Обновляем и список, и детали
                self.update_habits_list()
                self.update_habit_details(index)

    # --- Методы для импорта и экспорта ---

    def export_data(self):
        """Экспортирует данные в файл .json по выбору пользователя."""
        json_data = self.model.export_to_json()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить данные трекера",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(json_data)
                QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить файл: {e}")

    def import_data(self):
        """Импортирует данные из файла .json по выбору пользователя."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить данные трекера",
            "",
            "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_string = f.read()
                self.model.import_from_json(json_string)
                # После успешного импорта сохраняем данные как основные
                self.model.save_to_file()
                self.update_habits_list()
                QMessageBox.information(self, "Импорт", "Данные успешно импортированы.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить файл: {e}")