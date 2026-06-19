import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QTimer

import SuperAppProject1.SuperAPP.ui.widgets.game_stats_widget as game_stats_module
from SuperAppProject1.SuperAPP.ui.widgets.game_stats_widget import GameStatsWidget


class TestGameStatsWidget(unittest.TestCase):
    def setUp(self):
        # GameStatsWidget читает/пишет каталог игр и прогресс через
        # data_path(GAMES_CATALOG_FILE) / data_path(PLAYER_PROGRESS_FILE) —
        # это реальные файлы приложения в SuperAPP/data/. Подменяем
        # data_path на функцию, возвращающую путь во временной папке,
        # созданной отдельно для каждого теста — это полностью изолирует
        # тесты от данных пользователя и не оставляет файлов на диске.
        self._tmp_dir = tempfile.mkdtemp()

        def fake_data_path(filename):
            return os.path.join(self._tmp_dir, filename)

        self._data_path_patch = patch.object(game_stats_module, "data_path", fake_data_path)
        self._data_path_patch.start()

        self.widget = GameStatsWidget()

    def tearDown(self):
        self._data_path_patch.stop()

    def test_load_games(self):
        """Проверка загрузки игр из каталога и прогресса."""
        self.widget.games_catalog.append({
            "id": "game_001",
            "title": "Test Game",
            "description": "desc",
            "achievements": ["A1"],
        })
        self.widget.load_games()
        self.assertGreater(self.widget.games_table.rowCount(), 0)
        self.assertIsNotNone(self.widget.chart_canvas.figure)

    def test_add_game(self):
        """Проверка добавления новой игры через виджет."""
        def fill_add_game_dialog():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                dlg.title_edit.setText("Test Game")
                dlg.description_edit.setPlainText("This is a test game.")
                dlg.achievements_edit.setPlainText("Achieve 1\nAchieve 2")
                btn_box = dlg.findChild(QDialogButtonBox)
                QTest.mouseClick(btn_box.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)

        QTimer.singleShot(100, fill_add_game_dialog)
        QTest.mouseClick(self.widget.add_game_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(self.widget.games_table.rowCount(), 1)

    def test_edit_game(self):
        """Проверка редактирования игры."""
        self.test_add_game()
        # games_table — QTableWidget с SelectionBehavior.SelectRows;
        # _selected_row() читает selectionModel().selectedRows(), поэтому
        # нужно реально выделить строку через selectRow().
        self.widget.games_table.selectRow(0)

        def fill_edit_dialog():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                dlg.title_edit.setText("Edited Title")
                btn_box = dlg.findChild(QDialogButtonBox)
                QTest.mouseClick(btn_box.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)

        QTimer.singleShot(100, fill_edit_dialog)
        QTest.mouseClick(self.widget.edit_game_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(self.widget.games_table.item(0, 0).text(), "Edited Title")

    def test_delete_game(self):
        """Проверка удаления игры."""
        self.test_add_game()
        self.widget.games_table.selectRow(0)

        def confirm_delete():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                yes_button = dlg.button(QMessageBox.StandardButton.Yes)
                if yes_button:
                    QTest.mouseClick(yes_button, Qt.MouseButton.LeftButton)

        QTimer.singleShot(100, confirm_delete)
        QTest.mouseClick(self.widget.delete_game_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(self.widget.games_table.rowCount(), 0)

    def test_save_progress(self):
        """Проверка сохранения прогресса (оценки и достижений)."""
        self.test_add_game()

        # selectRow() не вызывает cellClicked сам по себе, а
        # on_game_selected (заполняет форму и включает form_box)
        # подключён именно к cellClicked — вызываем его явно, как это
        # сделал бы реальный клик по ячейке.
        self.widget.games_table.selectRow(0)
        self.widget.on_game_selected(0, 0)

        self.widget.rating_spinbox.setValue(4)
        self.widget.checkboxes[0].setChecked(True)
        self.widget.review_textarea.setPlainText("Great game!")

        # on_save_clicked() в конце вызывает QMessageBox.information(),
        # блокирующий выполнение до закрытия — закрываем через QTimer.
        def confirm_saved():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                QTest.keyClick(dlg, Qt.Key.Key_Enter)

        QTimer.singleShot(100, confirm_saved)
        QTest.mouseClick(self.widget.save_btn, Qt.MouseButton.LeftButton)

        self.assertEqual(self.widget.player_progress[self.widget.current_game_id]["rating"], 4)
        self.assertIn(
            self.widget.checkboxes[0].text(),
            self.widget.player_progress[self.widget.current_game_id]["completed"],
        )


if __name__ == '__main__':
    unittest.main()
