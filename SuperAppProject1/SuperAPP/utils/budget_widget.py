import os
import sqlite3

import plotly.graph_objs as go
import plotly.io as pio

from PyQt6.QtCore import QDate, Qt, QUrl
from PyQt6.QtGui import QColor
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QComboBox, QDateEdit, QDialog, QDialogButtonBox, QDoubleSpinBox,
    QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QMessageBox,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

# БД всегда рядом с этим файлом — независимо от рабочей директории
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'budget_data.db')

DEFAULT_INCOME_CATEGORIES  = ["Зарплата", "Стипендия", "Подработка", "Фриланс", "Прочий доход"]
DEFAULT_EXPENSE_CATEGORIES = ["Продукты", "Транспорт", "Развлечения", "ЖКХ", "Одежда", "Здоровье", "Прочий расход"]


class AddCategoryDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Новая категория")
        self.setMinimumWidth(320)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Название категории:"))
        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText("Введите название...")
        layout.addWidget(self.le_name)
        layout.addWidget(QLabel("Тип:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Доход", "Расход"])
        layout.addWidget(self.cmb_type)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> tuple:
        return self.le_name.text().strip(), self.cmb_type.currentText()


class AddGoalDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Новая цель накоплений")
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Название цели:"))
        self.le_name = QLineEdit()
        self.le_name.setPlaceholderText("Например: Отпуск, Ноутбук...")
        layout.addWidget(self.le_name)
        layout.addWidget(QLabel("Целевая сумма (₽):"))
        self.spin_target = QDoubleSpinBox()
        self.spin_target.setRange(1, 100_000_000)
        self.spin_target.setDecimals(2)
        self.spin_target.setValue(10000)
        layout.addWidget(self.spin_target)
        layout.addWidget(QLabel("Уже накоплено (₽):"))
        self.spin_saved = QDoubleSpinBox()
        self.spin_saved.setRange(0, 100_000_000)
        self.spin_saved.setDecimals(2)
        self.spin_saved.setValue(0)
        layout.addWidget(self.spin_saved)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def get_data(self) -> tuple:
        return self.le_name.text().strip(), self.spin_target.value(), self.spin_saved.value()


class BudgetWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Бюджет и накопления")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(8, 8, 8, 8)

        self.init_db()

        self.inner_tabs = QTabWidget()
        self.main_layout.addWidget(self.inner_tabs)

        self.tab_operations = QWidget()
        self.tab_operations.setLayout(QVBoxLayout())
        self.inner_tabs.addTab(self.tab_operations, "💰 Операции")

        self.tab_chart = QWidget()
        self.tab_chart.setLayout(QVBoxLayout())
        self.inner_tabs.addTab(self.tab_chart, "📊 Диаграмма расходов")

        self.tab_goals = QWidget()
        self.tab_goals.setLayout(QVBoxLayout())
        self.inner_tabs.addTab(self.tab_goals, "🎯 Цели накоплений")

        self.build_operations_tab()
        self.build_chart_tab()
        self.build_goals_tab()

        self.refresh_data()

    # ================================================================
    # БД
    # ================================================================
    def init_db(self) -> None:
        self.conn = sqlite3.connect(_DB_PATH)
        self.cursor = self.conn.cursor()

        # --- transactions ---
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                date     TEXT,
                type     TEXT,
                category TEXT,
                amount   REAL,
                comment  TEXT
            )
        ''')

        # --- categories: сносим и пересоздаём если схема старая ---
        self.cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='categories'"
        )
        row = self.cursor.fetchone()
        needs_recreate = False
        if row:
            ddl = (row[0] or '').lower()
            # старая схема не имеет составного уникального ключа (name, type)
            if 'unique(name, type)' not in ddl and 'unique(name,type)' not in ddl:
                needs_recreate = True
        if needs_recreate:
            self.cursor.execute("ALTER TABLE categories RENAME TO _categories_bak")
            self.cursor.execute('''
                CREATE TABLE categories (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    UNIQUE(name, type)
                )
            ''')
            self.cursor.execute('''
                INSERT OR IGNORE INTO categories (name, type)
                SELECT name, type FROM _categories_bak
            ''')
            self.cursor.execute("DROP TABLE _categories_bak")
        elif not row:
            self.cursor.execute('''
                CREATE TABLE categories (
                    id   INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    type TEXT,
                    UNIQUE(name, type)
                )
            ''')

        # --- goals: колонка saved (не current — зарезервировано в SQLite) ---
        self.cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='goals'"
        )
        row = self.cursor.fetchone()
        if row:
            ddl = (row[0] or '').lower()
            if 'saved' not in ddl:
                # старая таблица с колонкой current — мигрируем
                self.cursor.execute("ALTER TABLE goals RENAME TO _goals_bak")
                self.cursor.execute('''
                    CREATE TABLE goals (
                        id     INTEGER PRIMARY KEY AUTOINCREMENT,
                        name   TEXT,
                        target REAL,
                        saved  REAL
                    )
                ''')
                # копируем данные — колонка могла называться current или target_amount и т.д.
                self.cursor.execute("PRAGMA table_info(_goals_bak)")
                old_cols = [c[1] for c in self.cursor.fetchall()]
                saved_src = 'saved' if 'saved' in old_cols else ('current' if 'current' in old_cols else None)
                if saved_src and 'target' in old_cols:
                    self.cursor.execute(f'''
                        INSERT INTO goals (id, name, target, saved)
                        SELECT id, name, target, "{saved_src}" FROM _goals_bak
                    ''')
                self.cursor.execute("DROP TABLE _goals_bak")
        else:
            self.cursor.execute('''
                CREATE TABLE goals (
                    id     INTEGER PRIMARY KEY AUTOINCREMENT,
                    name   TEXT,
                    target REAL,
                    saved  REAL
                )
            ''')

        self.conn.commit()

        # Заполняем категории по умолчанию если таблица пустая
        self.cursor.execute("SELECT COUNT(*) FROM categories")
        if self.cursor.fetchone()[0] == 0:
            for cat in DEFAULT_INCOME_CATEGORIES:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)", (cat, "Доход")
                )
            for cat in DEFAULT_EXPENSE_CATEGORIES:
                self.cursor.execute(
                    "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)", (cat, "Расход")
                )
            self.conn.commit()

    # ================================================================
    # ВКЛАДКА 1: ОПЕРАЦИИ
    # ================================================================
    def build_operations_tab(self) -> None:
        layout = self.tab_operations.layout()

        input_frame = QFrame()
        input_frame.setFrameShape(QFrame.Shape.StyledPanel)
        input_layout = QVBoxLayout(input_frame)
        input_layout.setSpacing(6)
        input_layout.addWidget(QLabel("<b>Добавить операцию</b>"))

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Тип:"))
        self.cmb_type = QComboBox()
        self.cmb_type.addItems(["Доход", "Расход"])
        self.cmb_type.currentTextChanged.connect(self.on_type_changed)
        row1.addWidget(self.cmb_type)
        row1.addWidget(QLabel("Категория:"))
        self.cmb_category = QComboBox()
        row1.addWidget(self.cmb_category)
        btn_add_cat = QPushButton("+ Категория")
        btn_add_cat.setToolTip("Добавить свою категорию")
        btn_add_cat.clicked.connect(self.add_custom_category)
        row1.addWidget(btn_add_cat)
        row1.addStretch()

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Сумма (₽):"))
        self.le_amount = QLineEdit()
        self.le_amount.setPlaceholderText("0.00")
        self.le_amount.setMaximumWidth(140)
        row2.addWidget(self.le_amount)
        row2.addWidget(QLabel("Комментарий:"))
        self.le_comment = QLineEdit()
        row2.addWidget(self.le_comment)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Дата:"))
        self.de_date = QDateEdit()
        self.de_date.setCalendarPopup(True)
        self.de_date.setDate(QDate.currentDate())
        row3.addWidget(self.de_date)
        row3.addStretch()
        self.btn_add = QPushButton("✚ Добавить операцию")
        self.btn_add.setMinimumHeight(32)
        self.btn_add.clicked.connect(self.add_transaction)
        row3.addWidget(self.btn_add)

        input_layout.addLayout(row1)
        input_layout.addLayout(row2)
        input_layout.addLayout(row3)
        layout.addWidget(input_frame)

        balance_row = QHBoxLayout()
        balance_row.addWidget(QLabel("<h2>Текущий баланс:</h2>"))
        self.lbl_balance = QLabel("0.00 ₽")
        self.lbl_balance.setStyleSheet("font-size: 20px; font-weight: bold;")
        balance_row.addWidget(self.lbl_balance)
        balance_row.addStretch()
        layout.addLayout(balance_row)

        history_header = QHBoxLayout()
        history_header.addWidget(QLabel("<b>Последние 10 операций:</b>"))
        history_header.addStretch()
        self.btn_delete = QPushButton("🗑 Удалить выбранную")
        self.btn_delete.setToolTip("Выберите строку и нажмите для удаления")
        self.btn_delete.clicked.connect(self.delete_selected_transaction)
        history_header.addWidget(self.btn_delete)
        layout.addLayout(history_header)

        self.tbl_history = QTableWidget(0, 6)
        self.tbl_history.setHorizontalHeaderLabels(
            ["Дата", "Тип", "Категория", "Сумма", "Комментарий", "id"]
        )
        self.tbl_history.setColumnHidden(5, True)
        self.tbl_history.horizontalHeader().setStretchLastSection(True)
        self.tbl_history.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tbl_history.setAlternatingRowColors(True)
        self.tbl_history.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.tbl_history)

        self.refresh_categories()

    def on_type_changed(self, type_text: str) -> None:
        self.refresh_categories(type_text)

    def refresh_categories(self, type_text: str = None) -> None:
        if type_text is None:
            type_text = self.cmb_type.currentText()
        self.cursor.execute(
            "SELECT name FROM categories WHERE type=? ORDER BY name", (type_text,)
        )
        cats = [r[0] for r in self.cursor.fetchall()]
        self.cmb_category.clear()
        self.cmb_category.addItems(cats)

    def add_custom_category(self) -> None:
        dlg = AddCategoryDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, cat_type = dlg.get_data()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название категории.")
            return
        self.cursor.execute(
            "SELECT id FROM categories WHERE name=? AND type=?", (name, cat_type)
        )
        if self.cursor.fetchone():
            QMessageBox.information(
                self, "Уже существует",
                f"Категория «{name}» ({cat_type}) уже есть в списке."
            )
            return
        self.cursor.execute(
            "INSERT INTO categories (name, type) VALUES (?, ?)", (name, cat_type)
        )
        self.conn.commit()
        if cat_type != self.cmb_type.currentText():
            self.cmb_type.setCurrentText(cat_type)
        self.refresh_categories()
        idx = self.cmb_category.findText(name)
        if idx >= 0:
            self.cmb_category.setCurrentIndex(idx)

    def add_transaction(self) -> None:
        amount_text = self.le_amount.text().replace(',', '.')
        if not amount_text:
            QMessageBox.warning(self, "Ошибка", "Введите сумму.")
            return
        try:
            amount = float(amount_text)
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Введите корректную сумму.")
            return
        if amount <= 0:
            QMessageBox.warning(self, "Ошибка", "Сумма должна быть больше нуля.")
            return
        op_type = self.cmb_type.currentText()
        stored_amount = amount if op_type == "Доход" else -amount
        self.cursor.execute(
            "INSERT INTO transactions (date, type, category, amount, comment) VALUES (?, ?, ?, ?, ?)",
            (
                self.de_date.date().toString('yyyy-MM-dd'),
                op_type,
                self.cmb_category.currentText(),
                stored_amount,
                self.le_comment.text(),
            )
        )
        self.conn.commit()
        self.le_amount.clear()
        self.le_comment.clear()
        self.refresh_data()

    def delete_selected_transaction(self) -> None:
        row = self.tbl_history.currentRow()
        if row < 0 or not self.tbl_history.selectedItems():
            QMessageBox.information(self, "Удаление", "Выберите строку для удаления.")
            return
        id_item = self.tbl_history.item(row, 5)
        if not id_item:
            return
        transaction_id = int(id_item.text())
        date_val = (self.tbl_history.item(row, 0) or QTableWidgetItem()).text()
        type_val = (self.tbl_history.item(row, 1) or QTableWidgetItem()).text()
        cat_val  = (self.tbl_history.item(row, 2) or QTableWidgetItem()).text()
        amt_val  = (self.tbl_history.item(row, 3) or QTableWidgetItem()).text()
        reply = QMessageBox.question(
            self, "Удалить операцию",
            f"Удалить операцию?\n\nДата: {date_val}\nТип: {type_val}\nКатегория: {cat_val}\nСумма: {amt_val}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cursor.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
            self.conn.commit()
            self.refresh_data()

    # ================================================================
    # ВКЛАДКА 2: ДИАГРАММА
    # ================================================================
    def build_chart_tab(self) -> None:
        layout = self.tab_chart.layout()

        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Месяц:"))
        self.cmb_chart_month = QComboBox()
        self.cmb_chart_month.addItems([
            "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
        ])
        self.cmb_chart_month.setCurrentIndex(QDate.currentDate().month() - 1)
        ctrl.addWidget(self.cmb_chart_month)

        ctrl.addWidget(QLabel("Год:"))
        self.cmb_chart_year = QComboBox()
        current_year = QDate.currentDate().year()
        for y in range(current_year - 3, current_year + 1):
            self.cmb_chart_year.addItem(str(y))
        self.cmb_chart_year.setCurrentText(str(current_year))
        ctrl.addWidget(self.cmb_chart_year)

        btn_build = QPushButton("📊 Построить диаграмму")
        btn_build.clicked.connect(self.build_pie_chart)
        ctrl.addWidget(btn_build)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        # Изолированный профиль без сетевых запросов — убирает SSL ошибки
        self._web_profile = QWebEngineProfile("budget_chart_profile", self)
        self._web_profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

        self.chart_view = QWebEngineView()
        self.chart_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, True
        )
        self.chart_view.settings().setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.chart_view)

    def build_pie_chart(self) -> None:
        month = self.cmb_chart_month.currentIndex() + 1
        year  = int(self.cmb_chart_year.currentText())
        month_str = f"{year}-{month:02d}"

        self.cursor.execute(
            """
            SELECT category, SUM(amount) AS total
            FROM transactions
            WHERE type='Расход' AND date LIKE ?
            GROUP BY category
            ORDER BY total ASC
            """,
            (f"{month_str}%",)
        )
        rows = self.cursor.fetchall()

        if not rows:
            self.chart_view.setHtml(
                "<html><body style='display:flex;align-items:center;justify-content:center;"
                "height:100vh;font-family:sans-serif;color:#888;font-size:18px;'>"
                "Нет данных о расходах за выбранный месяц</body></html>"
            )
            return

        labels = [r[0] for r in rows]
        values = [abs(r[1]) for r in rows]

        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.35,
            textinfo='label+percent',
            hovertemplate='<b>%{label}</b><br>Сумма: %{value:.2f} ₽<br>Доля: %{percent}<extra></extra>',
        )])
        month_name = self.cmb_chart_month.currentText()
        fig.update_layout(
            title=dict(
                text=f"<b>Расходы по категориям — {month_name} {year}</b>",
                x=0.5, xanchor='center', font=dict(size=16),
            ),
            legend=dict(orientation='v', x=1.02, y=0.5),
            margin=dict(l=20, r=20, t=60, b=20),
            template='plotly_white',
        )

        # Берём plotly.min.js из установленного пакета — без сети, без файлов
        import plotly as _plotly_pkg
        plotly_js_path = os.path.join(
            os.path.dirname(_plotly_pkg.__file__), 'package_data', 'plotly.min.js'
        )
        fig_json = fig.to_json()
        if os.path.isfile(plotly_js_path):
            js_url = QUrl.fromLocalFile(plotly_js_path).toString()
            html = (
                '<!DOCTYPE html><html><head><meta charset="utf-8">'
                f'<script src="{js_url}"></script>'
                '</head><body style="margin:0;padding:0;">'
                '<div id="chart" style="width:100%;height:100vh;"></div>'
                '<script>'
                f'var fig={fig_json};'
                'Plotly.newPlot("chart",fig.data,fig.layout,{responsive:true,displayModeBar:false});'
                '</script></body></html>'
            )
            self.chart_view.setHtml(html, QUrl.fromLocalFile(plotly_js_path))
        else:
            html = pio.to_html(
                fig, full_html=True, include_plotlyjs='inline',
                config={'responsive': True, 'displayModeBar': False},
            )
            self.chart_view.setHtml(html)

    # ================================================================
    # ВКЛАДКА 3: ЦЕЛИ НАКОПЛЕНИЙ
    # ================================================================
    def build_goals_tab(self) -> None:
        layout = self.tab_goals.layout()

        top = QHBoxLayout()
        btn_add_goal = QPushButton("✚ Добавить цель")
        btn_add_goal.clicked.connect(self.add_goal)
        top.addWidget(btn_add_goal)
        top.addStretch()
        layout.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.goals_container = QWidget()
        self.goals_layout = QVBoxLayout(self.goals_container)
        self.goals_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.goals_layout.setSpacing(8)

        scroll.setWidget(self.goals_container)
        layout.addWidget(scroll)

    def add_goal(self) -> None:
        dlg = AddGoalDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        name, target, saved = dlg.get_data()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название цели.")
            return
        self.cursor.execute(
            "INSERT INTO goals (name, target, saved) VALUES (?, ?, ?)",
            (name, target, saved)
        )
        self.conn.commit()
        self.refresh_goals()

    def refresh_goals(self) -> None:
        while self.goals_layout.count():
            item = self.goals_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.cursor.execute("SELECT id, name, target, saved FROM goals ORDER BY id")
        goals = self.cursor.fetchall()

        if not goals:
            lbl = QLabel("Нет целей. Добавьте первую цель накоплений!")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #888; font-size: 14px; padding: 30px;")
            self.goals_layout.addWidget(lbl)
            return

        for goal_id, name, target, saved in goals:
            card = QFrame()
            card.setFrameShape(QFrame.Shape.StyledPanel)
            card_layout = QVBoxLayout(card)
            card_layout.setSpacing(4)

            header = QHBoxLayout()
            lbl_name = QLabel(f"<b>{name}</b>")
            lbl_name.setStyleSheet("font-size: 14px;")
            header.addWidget(lbl_name)
            header.addStretch()

            pct = min(saved / target * 100, 100) if target > 0 else 0.0
            lbl_pct = QLabel(f"{pct:.1f}%")
            lbl_pct.setStyleSheet("font-size: 13px; color: #555;")
            header.addWidget(lbl_pct)

            btn_fill = QPushButton("+ Пополнить")
            btn_fill.setMaximumWidth(110)
            btn_fill.clicked.connect(
                lambda _c, gid=goal_id, gsaved=saved: self.fill_goal(gid, gsaved)
            )
            header.addWidget(btn_fill)

            btn_del = QPushButton("✕")
            btn_del.setMaximumWidth(30)
            btn_del.setToolTip("Удалить цель")
            btn_del.clicked.connect(lambda _c, gid=goal_id: self.delete_goal(gid))
            header.addWidget(btn_del)

            card_layout.addLayout(header)

            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(pct))
            bar.setTextVisible(False)
            bar.setMinimumHeight(18)
            if pct >= 100:
                bar.setStyleSheet("QProgressBar::chunk { background: #27ae60; }")
            elif pct >= 60:
                bar.setStyleSheet("QProgressBar::chunk { background: #2980b9; }")
            else:
                bar.setStyleSheet("QProgressBar::chunk { background: #e67e22; }")
            card_layout.addWidget(bar)

            remaining = max(target - saved, 0)
            lbl_sums = QLabel(
                f"{saved:,.2f} ₽  из  {target:,.2f} ₽  (осталось: {remaining:,.2f} ₽)"
            )
            lbl_sums.setStyleSheet("color: #444; font-size: 12px;")
            card_layout.addWidget(lbl_sums)

            self.goals_layout.addWidget(card)

    def fill_goal(self, goal_id: int, saved: float) -> None:
        amount, ok = QInputDialog.getDouble(
            self, "Пополнить цель", "Сумма пополнения (₽):", 0, 0, 100_000_000, 2
        )
        if ok and amount > 0:
            self.cursor.execute(
                "UPDATE goals SET saved=? WHERE id=?", (saved + amount, goal_id)
            )
            self.conn.commit()
            self.refresh_goals()

    def delete_goal(self, goal_id: int) -> None:
        reply = QMessageBox.question(
            self, "Удалить цель", "Вы уверены, что хотите удалить эту цель?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.cursor.execute("DELETE FROM goals WHERE id=?", (goal_id,))
            self.conn.commit()
            self.refresh_goals()

    # ================================================================
    # ОБНОВЛЕНИЕ ДАННЫХ
    # ================================================================
    def refresh_data(self) -> None:
        try:
            self.update_balance()
            self.update_history_table()
            self.refresh_goals()
        except Exception as e:
            print(f"Ошибка при обновлении данных: {e}")

    def update_balance(self) -> None:
        self.cursor.execute('SELECT SUM(amount) FROM transactions')
        result = self.cursor.fetchone()[0]
        balance = result if result is not None else 0.0
        color = "#27ae60" if balance >= 0 else "#e74c3c"
        self.lbl_balance.setText(f"{balance:,.2f} ₽")
        self.lbl_balance.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {color};")

    def update_history_table(self) -> None:
        self.cursor.execute('''
            SELECT id, date, type, category, amount, comment
            FROM transactions
            ORDER BY date DESC, id DESC
            LIMIT 10
        ''')
        rows = self.cursor.fetchall()
        self.tbl_history.setRowCount(0)

        for row_idx, row in enumerate(rows):
            self.tbl_history.insertRow(row_idx)
            # row: (id, date, type, category, amount, comment)
            # таблица: col0=date col1=type col2=category col3=amount col4=comment col5=id(скрыт)
            for col_idx, db_idx in enumerate([1, 2, 3, 4, 5]):
                value = row[db_idx]
                item_text = str(value) if value is not None else ""
                item = QTableWidgetItem(item_text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col_idx == 3:  # amount
                    try:
                        amt = float(item_text)
                        item.setText(f"{amt:+,.2f} ₽")
                        item.setForeground(QColor("#27ae60") if amt >= 0 else QColor("#e74c3c"))
                        item.setTextAlignment(
                            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                        )
                    except ValueError:
                        pass
                self.tbl_history.setItem(row_idx, col_idx, item)

            id_item = QTableWidgetItem(str(row[0]))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.tbl_history.setItem(row_idx, 5, id_item)

        self.tbl_history.resizeColumnsToContents()
