import os
import sys
sys.path.append(os.path.abspath("../../"))

import unittest
from PyQt6.QtWidgets import QApplication, QPushButton, QDialogButtonBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt

from SuperAppProject1.SuperAPP.ui.widgets.game_stats_widget import GameStatsWidget

app = QApplication([])

class TestGameStatsWidget(unittest.TestCase):
    def setUp(self):
        self.widget = GameStatsWidget()

    def test_load_games(self):
        """Проверка загрузки игр из каталога и прогресса."""
        self.widget.load_games()
        self.assertGreater(self.widget.games_table.rowCount(), 0)
        self.assertIsNotNone(self.widget.chart_canvas.figure)

    def test_add_game(self):
        """Проверка добавления новой игры через виджет."""
        # Исправил findChild: теперь ищем по типу и имени
        add_btn = self.widget.findChild(QPushButton, "➕ Новая игра")
        QTest.mouseClick(add_btn, Qt.MouseButton.LeftButton)

        # Эмулируем ввод данных в диалоге
        dlg = QApplication.activeModalWidget()
        dlg.title_edit.setText("Test Game")
        dlg.description_edit.setPlainText("This is a test game.")
        dlg.achievements_edit.setPlainText("Achieve 1\nAchieve 2")
        QTest.mouseClick(dlg.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
        self.assertEqual(self.widget.games_table.rowCount(), 1)

    def test_edit_game(self):
        """Проверка редактирования игры."""
        self.test_add_game()  # Создаём тестовую игру
        self.widget.games_table.setCurrentRow(0)

        # Исправил findChild: теперь ищем по типу и имени
        edit_btn = self.widget.findChild(QPushButton, "✏️ Редактировать")
        QTest.mouseClick(edit_btn, Qt.MouseButton.LeftButton)

        # Эмулируем изменение данных в диалоге
        dlg = QApplication.activeModalWidget()
        dlg.title_edit.setText("Edited Title")
        QTest.mouseClick(dlg.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
        self.assertEqual(self.widget.games_table.item(0, 0).text(), "Edited Title")

    def test_delete_game(self):
        """Проверка удаления игры."""
        self.test_add_game()  # Создаём тестовую игру
        self.widget.games_table.setCurrentRow(0)

        # Исправил findChild: теперь ищем по типу и имени
        delete_btn = self.widget.findChild(QPushButton, "🗑️ Удалить игру")
        QTest.mouseClick(delete_btn, Qt.MouseButton.LeftButton)

        # Эмулируем подтверждение удаления
        QTest.keyClicks(QApplication.activeModalWidget(), "Yes")
        self.assertEqual(self.widget.games_table.rowCount(), 0)

    def test_save_progress(self):
        """Проверка сохранения прогресса (оценки и достижений)."""
        self.test_add_game()  # Создаём тестовую игру
        self.widget.games_table.setCurrentRow(0)
        self.widget.on_game_selected(0, 0)  # Выбираем игру
        self.widget.rating_spinbox.setValue(4)
        self.widget.checkboxes[0].setChecked(True)
        self.widget.review_textarea.setPlainText("Great game!")
        QTest.mouseClick(self.widget.save_btn, Qt.MouseButton.LeftButton)

        # Проверяем, что данные сохранились
        self.assertEqual(self.widget.player_progress[self.widget.current_game_id]["rating"], 4)
        self.assertIn(self.widget.checkboxes[0].text(), self.widget.player_progress[self.widget.current_game_id]["completed"])

if __name__ == '__main__':
    unittest.main()