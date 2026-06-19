import os
import tempfile
import unittest
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication, QDialogButtonBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QDate, QTimer

import SuperAppProject1.SuperAPP.ui.widgets.budget_widget as budget_widget_module
from SuperAppProject1.SuperAPP.ui.widgets.budget_widget import BudgetWidget


class TestBudgetWidget(unittest.TestCase):
    def setUp(self):
        # BudgetWidget.init_db() подключается к фиксированному пути
        # _DB_PATH = data_path('budget_data.db') — это реальная база
        # данных приложения. Изолируем тесты через отдельный временный
        # файл БД, подменяя модульную переменную _DB_PATH ДО создания
        # BudgetWidget (она читается в init_db() в момент создания
        # экземпляра).
        self._tmp_dir = tempfile.mkdtemp()
        self._tmp_db_path = os.path.join(self._tmp_dir, "test_budget_data.db")
        self._db_patch = patch.object(budget_widget_module, "_DB_PATH", self._tmp_db_path)
        self._db_patch.start()

        # ВАЖНО: build_chart_tab() создаёt QWebEngineView и сразу передаёт
        # его в layout.addWidget(self.chart_view) — это настоящий метод
        # Qt на уровне C++, который требует НАСТОЯЩИЙ QWidget. Если
        # подменить QWebEngineView на MagicMock, addWidget(MagicMock())
        # упадёт с TypeError ("argument 1 has unexpected type 'MagicMock'"),
        # как уже произошло в test_currency_widget.py с похожей ситуацией.
        # Создание самого QWebEngineView не зависает и не требует сети —
        # тяжесть появляется только при реальной загрузке HTML с большим
        # контентом или сетевыми ресурсами, чего наши тесты не делают
        # (build_pie_chart() не вызывается ни в одном тесте ниже).
        # Поэтому QWebEngineView/QWebEngineProfile НЕ мокаем.

        self.widget = BudgetWidget()

    def tearDown(self):
        self.widget.conn.close()
        self._db_patch.stop()
        if os.path.exists(self._tmp_db_path):
            os.remove(self._tmp_db_path)
        os.rmdir(self._tmp_dir)

    def test_add_income(self):
        """Проверка добавления дохода."""
        self.widget.cmb_type.setCurrentText("Доход")
        self.widget.cmb_category.setCurrentText("Зарплата")
        self.widget.le_amount.setText("1000")
        self.widget.de_date.setDate(QDate.currentDate())
        QTest.mouseClick(self.widget.btn_add, Qt.MouseButton.LeftButton)
        self.assertGreater(self.widget.tbl_history.rowCount(), 0)

    def test_add_expense(self):
        """Проверка добавления расхода."""
        self.widget.cmb_type.setCurrentText("Расход")
        self.widget.cmb_category.setCurrentText("Продукты")
        self.widget.le_amount.setText("500")
        self.widget.de_date.setDate(QDate.currentDate())
        QTest.mouseClick(self.widget.btn_add, Qt.MouseButton.LeftButton)
        self.assertGreater(self.widget.tbl_history.rowCount(), 0)

    def test_delete_transaction(self):
        """Проверка удаления транзакции."""
        self.test_add_income()

        # tbl_history — QTableWidget, у него нет setCurrentRow(); чтобы
        # delete_selected_transaction() увидел selectedItems(), строку
        # нужно реально выделить через selectRow().
        self.widget.tbl_history.selectRow(0)

        # delete_selected_transaction() вызывает QMessageBox.question(),
        # который блокирует выполнение до закрытия диалога (.exec()).
        # Закрываем его через QTimer, который сработает уже во время
        # открытого диалога, пока mouseClick ждёт завершения обработчика.
        def confirm_delete():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                QTest.keyClick(dlg, Qt.Key.Key_Enter)  # подтверждаем Yes (кнопка по умолчанию)

        QTimer.singleShot(100, confirm_delete)
        QTest.mouseClick(self.widget.btn_delete, Qt.MouseButton.LeftButton)

        self.assertEqual(self.widget.tbl_history.rowCount(), 0)

    def test_set_goal(self):
        """Проверка установки цели накоплений."""
        def fill_goal_dialog():
            dlg = QApplication.activeModalWidget()
            if dlg is not None:
                dlg.le_name.setText("Buy Car")
                dlg.spin_target.setValue(1000000)
                dlg.spin_saved.setValue(100000)
                btn_box = dlg.findChild(QDialogButtonBox)
                QTest.mouseClick(btn_box.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)

        QTimer.singleShot(100, fill_goal_dialog)
        QTest.mouseClick(self.widget.btn_add_goal, Qt.MouseButton.LeftButton)

        self.assertGreater(self.widget.goals_layout.count(), 0)


if __name__ == '__main__':
    unittest.main()
