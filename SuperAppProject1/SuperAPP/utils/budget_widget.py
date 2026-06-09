# SuperApp/utils/budget_widget.py

import sqlite3
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QDateEdit, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor


class BudgetWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Бюджет и накопления")
        self.layout = QVBoxLayout(self)

        # --- Инициализация базы данных ---
        self.init_db()

        # 1. Блок для добавления операций (Доход/Расход)
        self.create_input_section()

        # 2. Блок для отображения информации (История, Баланс)
        self.create_display_section()

        # Загружаем данные при запуске виджета
        self.refresh_data()

    # --- МЕТОДЫ ПЕРЕНЕСЕНЫ В НАЧАЛО КЛАССА ---
    def add_transaction(self):
        """Обрабатывает нажатие кнопки 'Добавить операцию'."""
        try:
            amount_text = self.le_amount.text().replace(',', '.')
            amount = float(amount_text) if amount_text else 0.0

            # Если это расход, делаем сумму отрицательной для удобства подсчета баланса
            if self.cmb_type.currentText() == 'Расход':
                amount *= -1

            data = (
                self.de_date.date().toString('yyyy-MM-dd'),
                self.cmb_type.currentText(),
                self.cmb_category.currentText(),
                amount,
                self.le_comment.text()
            )
            # Вставляем данные в базу
            self.cursor.execute(
                "INSERT INTO transactions (date, type, category, amount, comment) VALUES (?, ?, ?, ?, ?)",
                data
            )
            self.conn.commit()

            # Очищаем поля ввода после успешной операции
            for widget in [self.le_amount, self.le_comment]:
                widget.clear()

            # Обновляем отображаемые данные
            self.refresh_data()

        except ValueError:
            print("Ошибка: введите корректную сумму.")
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")

    def refresh_data(self):
        """Обновляет баланс и таблицу истории."""
        try:
            if hasattr(self, 'lbl_balance'):
                self.update_balance()
            if hasattr(self, 'tbl_history'):
                self.update_history_table()
        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")

    def update_balance(self):
        """Вычисляет сумму всех операций и выводит её как баланс."""
        try:
            if hasattr(self, 'cursor'):
                self.cursor.execute('SELECT SUM(amount) FROM transactions')
                result = self.cursor.fetchone()[0]
                balance = result if result is not None else 0.0
                if hasattr(self, 'lbl_balance'):
                    self.lbl_balance.setText(f"{balance:.2f} ₽")
        except Exception as e:
            print(f"Ошибка при расчете баланса: {e}")

    def update_history_table(self):
        """Заполняет таблицу последними 10 операциями."""
        try:
            if hasattr(self, 'cursor') and hasattr(self, 'tbl_history'):
                self.cursor.execute('''
                     SELECT date, type, category, amount, comment FROM transactions ORDER BY date DESC LIMIT 10
                 ''')
                rows = self.cursor.fetchall()

                # Очищаем таблицу перед заполнением (чтобы избежать дублирования строк)
                for i in reversed(range(self.tbl_history.rowCount())):
                    self.tbl_history.removeRow(i)

                # Заполняем таблицу новыми данными
                for row_idx, row in enumerate(rows):
                    self.tbl_history.insertRow(row_idx)
                    for col_idx, value in enumerate(row):
                        item_text = str(value) if value is not None else ""
                        item = QTableWidgetItem(item_text)
                        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)

                        # Форматируем колонку "Сумма": цвет и выравнивание
                        if col_idx == 3:
                            try:
                                amount_val = float(item_text.replace(',', '.'))
                                item.setText(f"{amount_val:.2f} ₽")
                                item.setForeground(QColor('red' if amount_val < 0 else 'green'))
                                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                            except ValueError:
                                pass

                        self.tbl_history.setItem(row_idx, col_idx, item)

        except Exception as e:
            print(f"Ошибка при обновлении таблицы: {e}")

    # --- КОНЕЦ ПЕРЕНЕСЕННЫХ МЕТОДОВ ---

    def init_db(self):
        """Создает базу данных и таблицы, если их нет."""
        self.conn = sqlite3.connect('budget_data.db')
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                type TEXT,
                category TEXT,
                amount REAL,
                comment TEXT
            )
        ''')
        self.conn.commit()

    def create_input_section(self):
        """Создает интерфейс для ввода новых транзакций."""
        group = QWidget()
        layout = QVBoxLayout(group)

        # Ряд 1: Тип операции и Категория
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Тип:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Доход", "Расход"])
        row1.addWidget(self.cmb_type)

        row1.addWidget(QLabel("Категория:"))
        self.cmb_category = QComboBox()
        self.cmb_category.addItems(["Зарплата", "Продукты", "Транспорт", "Развлечения"])
        row1.addWidget(self.cmb_category)

        # Ряд 2: Сумма и Комментарий
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Сумма:"))
        self.le_amount = QLineEdit()
        self.le_amount.setPlaceholderText("0.00")
        row2.addWidget(self.le_amount)

        row2.addWidget(QLabel("Комментарий:"))
        self.le_comment = QLineEdit()
        row2.addWidget(self.le_comment)

        # Ряд 3: Дата и Кнопка "Добавить"
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Дата:"))
        self.de_date = QDateEdit(calendarPopup=True)
        self.de_date.setDate(QDate.currentDate())
        row3.addWidget(self.de_date)

        self.btn_add = QPushButton("Добавить операцию")
        # Теперь Python уже знает о методе add_transaction!
        self.btn_add.clicked.connect(self.add_transaction)

        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row3)
        layout.addWidget(self.btn_add)

        self.layout.addWidget(group)

    def create_display_section(self):
        pass


def create_display_section(self):
    """Создает интерфейс для отображения баланса и истории."""
    group = QWidget()
    layout = QVBoxLayout(group)

    # Баланс
    balance_layout = QHBoxLayout()
    balance_layout.addWidget(QLabel("<h2>Текущий баланс:</h2>"))
    self.lbl_balance = QLabel("0.00 ₽")
    self.lbl_balance.setStyleSheet("font-size: 20px; font-weight: bold;")
    balance_layout.addWidget(self.lbl_balance)
    balance_layout.addStretch()  # Отступ справа

    # История операций (Таблица)
    history_layout = QVBoxLayout()
    history_layout.addWidget(QLabel("<h3>Последние 10 операций:</h3>"))
    self.tbl_history = QTableWidget(10, 5)
    self.tbl_history.setHorizontalHeaderLabels(["Дата", "Тип", "Категория", "Сумма", "Комментарий"])

    history_layout.addWidget(self.tbl_history)

    layout.addLayout(balance_layout)
    layout.addLayout(history_layout)

    self.layout.addWidget(group)