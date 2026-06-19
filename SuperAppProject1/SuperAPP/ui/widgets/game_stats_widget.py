import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QSpinBox, QPlainTextEdit, QCheckBox, QGroupBox,
    QLabel, QMessageBox, QSplitter, QDialog, QDialogButtonBox,
    QAbstractItemView, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

try:
    from SuperAppProject1.SuperAPP.core.navigation import data_path
except ImportError:
    def data_path(filename: str) -> str:
        os.makedirs("data", exist_ok=True)
        return os.path.join("data", filename)


GAMES_CATALOG_FILE = "games_catalog.json"
PLAYER_PROGRESS_FILE = "player_progress.json"


class PieChart(Canvas):
    """Круговая диаграмма распределения оценок игрока (1-5 звёзд)."""

    def __init__(self, parent=None):
        fig = Figure(figsize=(5, 5), dpi=90)
        fig.patch.set_alpha(0)
        self.ax = fig.add_subplot(111)
        super().__init__(fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 320)
        self.draw_chart([])

    def draw_chart(self, distribution: list):
        """distribution — список пар (звёзды, количество игр с такой оценкой)."""
        self.ax.clear()

        filtered = [(stars, count) for stars, count in distribution if count > 0]

        if not filtered:
            self.ax.axis('off')
            self.ax.text(0.5, 0.5, "Нет оценённых игр", ha='center', va='center', fontsize=12)
        else:
            labels = [f"{stars}★ ({count})" for stars, count in filtered]
            sizes = [count for _, count in filtered]
            colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']
            # Цвет подбираем по номеру звёздности (1..5), а не по порядку в списке
            point_colors = [colors[stars - 1] for stars, _ in filtered]
            explode = [0.05] * len(sizes)

            self.ax.pie(
                sizes, labels=labels, autopct='%1.0f%%',
                startangle=90, colors=point_colors, explode=explode,
                textprops={'fontsize': 9}
            )
            self.ax.axis('equal')

        self.draw_idle()


class GameEditDialog(QDialog):
    """Диалог добавления новой игры в каталог или редактирования существующей."""

    def __init__(self, parent=None, game_data: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Игра в каталоге")
        self.setMinimumWidth(420)
        self._game_data = game_data or {}

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Название игры:"))
        self.title_edit = QLineEdit(self._game_data.get("title", ""))
        layout.addWidget(self.title_edit)

        layout.addWidget(QLabel("Краткое описание:"))
        self.description_edit = QPlainTextEdit(self._game_data.get("description", ""))
        self.description_edit.setFixedHeight(70)
        layout.addWidget(self.description_edit)

        layout.addWidget(QLabel("Достижения (каждое — на новой строке):"))
        self.achievements_edit = QPlainTextEdit(
            "\n".join(self._game_data.get("achievements", []))
        )
        self.achievements_edit.setFixedHeight(110)
        layout.addWidget(self.achievements_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _on_accept(self):
        if not self.title_edit.text().strip():
            QMessageBox.warning(self, "Внимание", "Название игры не может быть пустым.")
            return
        self.accept()

    def get_result(self) -> dict:
        """Возвращает словарь с данными игры; id сохраняется, если игра редактировалась."""
        achievements = [
            line.strip() for line in self.achievements_edit.toPlainText().splitlines()
            if line.strip()
        ]
        result = {
            "id": self._game_data.get("id"),
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "achievements": achievements,
        }
        return result


class GameStatsWidget(QWidget):
    """Вкладка 'Статистика игры': каталог игр + личный прогресс игрока."""

    def __init__(self):
        super().__init__()

        self.games_catalog: list = self.load_json(data_path(GAMES_CATALOG_FILE), default=[])
        self.player_progress: dict = self.load_json(data_path(PLAYER_PROGRESS_FILE), default={})
        self.current_game_id = None
        self.checkboxes: list = []

        self._build_ui()
        self.load_games()

    # ------------------------------------------------------------------ UI

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        # --- Верхняя панель: заголовок + кнопки управления каталогом ---
        header = QHBoxLayout()

        title_label = QLabel("🎮 Статистика игры")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header.addWidget(title_label)
        header.addStretch()

        self.add_game_btn = QPushButton("➕ Новая игра")
        self.add_game_btn.clicked.connect(self.on_add_game_clicked)
        header.addWidget(self.add_game_btn)

        self.edit_game_btn = QPushButton("✏️ Редактировать")
        self.edit_game_btn.clicked.connect(self.on_edit_game_clicked)
        header.addWidget(self.edit_game_btn)

        self.delete_game_btn = QPushButton("🗑️ Удалить игру")
        self.delete_game_btn.setProperty("cancel", True)
        self.delete_game_btn.clicked.connect(self.on_delete_game_clicked)
        header.addWidget(self.delete_game_btn)

        main_layout.addLayout(header)

        # --- Центральная область: список игр | диаграмма ---
        splitter = QSplitter(Qt.Orientation.Horizontal)

        games_box = QGroupBox("Каталог игр")
        games_layout = QVBoxLayout(games_box)
        self.games_table = QTableWidget()
        self.games_table.setColumnCount(3)
        self.games_table.setHorizontalHeaderLabels(["Название", "Моя оценка", "Достижения"])
        self.games_table.horizontalHeader().setStretchLastSection(True)
        self.games_table.verticalHeader().setVisible(False)
        self.games_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.games_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.games_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.games_table.cellClicked.connect(self.on_game_selected)
        self.games_table.cellDoubleClicked.connect(self.on_game_opened)
        games_layout.addWidget(self.games_table)
        splitter.addWidget(games_box)

        chart_box = QGroupBox("Распределение моих оценок")
        chart_layout = QVBoxLayout(chart_box)
        self.chart_canvas = PieChart(parent=self)
        chart_layout.addWidget(self.chart_canvas)
        splitter.addWidget(chart_box)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter, stretch=3)

        # --- Нижний блок: форма оценки выбранной игры ---
        form_box = QGroupBox("Моя оценка выбранной игры")
        form_layout = QVBoxLayout(form_box)

        name_row = QHBoxLayout()
        self.title_label = QLabel("Выберите игру в списке")
        title_label_font = QFont()
        title_label_font.setPointSize(13)
        title_label_font.setBold(True)
        self.title_label.setFont(title_label_font)
        name_row.addWidget(self.title_label)
        name_row.addStretch()

        name_row.addWidget(QLabel("Оценка (★):"))
        self.rating_spinbox = QSpinBox()
        self.rating_spinbox.setRange(1, 5)
        name_row.addWidget(self.rating_spinbox)
        form_layout.addLayout(name_row)

        self.achievement_group = QGroupBox("Выполненные достижения")
        self.achievement_layout = QVBoxLayout(self.achievement_group)
        form_layout.addWidget(self.achievement_group)

        review_row = QHBoxLayout()
        review_row.addWidget(QLabel("Отзыв:"))
        self.review_textarea = QPlainTextEdit()
        self.review_textarea.setFixedHeight(70)
        review_row.addWidget(self.review_textarea)
        form_layout.addLayout(review_row)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.save_btn = QPushButton("✅ Сохранить оценку")
        self.save_btn.clicked.connect(self.on_save_clicked)
        btn_row.addWidget(self.save_btn)
        form_layout.addLayout(btn_row)

        self.form_box = form_box
        self.form_box.setEnabled(False)
        main_layout.addWidget(form_box, stretch=2)

    # ------------------------------------------------------------------ Файлы

    def load_json(self, path: str, default):
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return default

    def save_json(self, path: str, data) -> None:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def save_catalog(self):
        self.save_json(data_path(GAMES_CATALOG_FILE), self.games_catalog)

    def save_progress(self):
        self.save_json(data_path(PLAYER_PROGRESS_FILE), self.player_progress)

    # ------------------------------------------------------------------ Таблица и диаграмма

    def load_games(self):
        """Перестраивает таблицу каталога и диаграмму оценок."""
        self.games_table.setRowCount(len(self.games_catalog))

        for row, game in enumerate(self.games_catalog):
            title_item = QTableWidgetItem(game["title"])
            title_item.setData(Qt.ItemDataRole.UserRole, game["id"])
            title_item.setToolTip(game.get("description", ""))
            self.games_table.setItem(row, 0, title_item)

            progress = self.player_progress.get(game["id"], {})
            rating_item = QTableWidgetItem(f"{progress.get('rating', '-')} ★" if progress.get('rating') else "—")
            self.games_table.setItem(row, 1, rating_item)

            completed_count = len(progress.get("completed", []))
            total_count = len(game.get("achievements", []))
            ratio = f"{completed_count}/{total_count}" if total_count else "—"
            achievements_item = QTableWidgetItem(ratio)
            self.games_table.setItem(row, 2, achievements_item)

        ratings = [entry.get("rating") for entry in self.player_progress.values() if entry.get("rating")]
        distribution = [(stars, ratings.count(stars)) for stars in range(1, 6)]
        self.chart_canvas.draw_chart(distribution)

    def _find_game(self, game_id: str) -> dict:
        return next((g for g in self.games_catalog if g["id"] == game_id), None)

    def _selected_row(self):
        rows = self.games_table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    # ------------------------------------------------------------------ Обработчики каталога

    def on_add_game_clicked(self):
        dialog = GameEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_result()
            data["id"] = self._generate_game_id()
            self.games_catalog.append(data)
            self.save_catalog()
            self.load_games()

    def on_edit_game_clicked(self):
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Внимание", "Сначала выберите игру из списка.")
            return
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        game = self._find_game(game_id)
        if not game:
            return

        dialog = GameEditDialog(self, game_data=game)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated = dialog.get_result()
            game.update(updated)
            self.save_catalog()
            self.load_games()
            self.on_game_selected(row, 0)

    def on_delete_game_clicked(self):
        row = self._selected_row()
        if row is None:
            QMessageBox.information(self, "Внимание", "Сначала выберите игру из списка.")
            return
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        game = self._find_game(game_id)
        if not game:
            return

        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить игру «{game['title']}» из каталога вместе с моей оценкой?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.games_catalog.remove(game)
            self.player_progress.pop(game_id, None)
            self.save_catalog()
            self.save_progress()
            self.current_game_id = None
            self.form_box.setEnabled(False)
            self.title_label.setText("Выберите игру в списке")
            self.load_games()

    def _generate_game_id(self) -> str:
        existing_numbers = []
        for g in self.games_catalog:
            try:
                existing_numbers.append(int(g["id"].split("_")[-1]))
            except (ValueError, IndexError, KeyError):
                continue
        next_number = max(existing_numbers, default=0) + 1
        return f"game_{next_number:03d}"


    def on_game_selected(self, row: int, column: int):
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        game = self._find_game(game_id)
        if not game:
            return

        self.current_game_id = game_id
        self.form_box.setEnabled(True)

        progress = self.player_progress.get(game_id, {})
        self.title_label.setText(game["title"])
        self.rating_spinbox.setValue(progress.get("rating", 1))

        self._rebuild_achievement_checkboxes(game.get("achievements", []), progress.get("completed", []))
        self.review_textarea.setPlainText(progress.get("review", ""))

    def on_game_opened(self, row: int, column: int):
        """Двойной клик — показать описание игры."""
        game_id = self.games_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        game = self._find_game(game_id)
        if not game:
            return
        QMessageBox.information(
            self, game["title"],
            game.get("description", "(Нет описания)")
        )

    def _rebuild_achievement_checkboxes(self, achievements: list, completed: list):
        while self.achievement_layout.count():
            item = self.achievement_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.checkboxes = []

        if not achievements:
            self.achievement_layout.addWidget(QLabel("Для этой игры пока не заданы достижения."))
            return

        for achievement in achievements:
            cb = QCheckBox(achievement)
            cb.setChecked(achievement in completed)
            self.checkboxes.append(cb)
            self.achievement_layout.addWidget(cb)

    def on_save_clicked(self):
        if not self.current_game_id:
            return

        progress = {
            "rating": self.rating_spinbox.value(),
            "completed": [cb.text() for cb in self.checkboxes if cb.isChecked()],
            "review": self.review_textarea.toPlainText().strip(),
        }
        self.player_progress[self.current_game_id] = progress
        self.save_progress()
        self.load_games()
        QMessageBox.information(self, "Сохранено", "Оценка и отзыв сохранены.")
