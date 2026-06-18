import os
import sys
sys.path.append(os.path.abspath("../../"))

import unittest
from PyQt6.QtWidgets import QApplication, QPushButton, QDialogButtonBox
from PyQt6.QtTest import QTest
from PyQt6.QtCore import Qt, QDate

from SuperAppProject1.SuperAPP.ui.widgets.budget_widget import BudgetWidget

app = QApplication(sys.argv)

class TestBudgetWidget(unittest.TestCase):
    def setUp(self):
        self.widget = BudgetWidget()

    def test_add_income(self):
        """Проверка добавления дохода."""
        self.widget.cmb_type.setCurrentText("Доход")
        self.widget.cmb_category.setCurrentText("Зарплата")
        self.widget.le_amount.setText("1000")
        self.widget.de_date.setDate(QDate.currentDate())
        QTest.mouseClick(self.widget.btn_add, Qt.MouseButton.LeftButton)
        # Проверка, что транзакция попала в базу
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
        self.test_add_income()  # Создаём тестовую транзакцию
        self.widget.tbl_history.setCurrentRow(0)
        QTest.mouseClick(self.widget.btn_delete, Qt.MouseButton.LeftButton)
        # Эмулируем подтверждение удаления
        QTest.keyClicks(QApplication.activeModalWidget(), "Yes")
        self.assertEqual(self.widget.tbl_history.rowCount(), 0)

    def test_set_goal(self):
        """Проверка установки цели накоплений."""
        QTest.mouseClick(self.widget.findChild(QPushButton, text="✚ Добавить цель"), Qt.MouseButton.LeftButton)
        # Эмулируем ввод данных в диалоге
        dlg = QApplication.activeModalWidget()
        dlg.le_name.setText("Buy Car")
        dlg.spin_target.setValue(1000000)
        dlg.spin_saved.setValue(100000)
        QTest.mouseClick(dlg.button(QDialogButtonBox.StandardButton.Ok), Qt.MouseButton.LeftButton)
        # Проверка, что цель появилась в списке
        self.assertGreater(self.widget.goals_layout.count(), 0)

if __name__ == '__main__':
    unittest.main()