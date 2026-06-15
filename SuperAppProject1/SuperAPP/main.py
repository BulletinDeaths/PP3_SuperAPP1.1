import sys
from PyQt6.QtWidgets import QApplication

from SuperAppProject1.SuperAPP.ui.main_window import MainWindow
from SuperAppProject1.SuperAPP.utils.currency_widget import CurrencyWidget
from SuperAppProject1.SuperAPP.utils.budget_widget import BudgetWidget
from SuperAppProject1.SuperAPP.utils.habit_tracker_widget import HabitTrackerWidget
from SuperAppProject1.SuperAPP.utils.habit_tracker_model import HabitTrackerModel
from SuperAppProject1.SuperAPP.utils.stub_widget_4 import StubWidget as StubWidget4
from SuperAppProject1.SuperAPP.utils.stub_widget_5 import StubWidget as StubWidget5


def main():
    app = QApplication(sys.argv)

    DATA_FILE_PATH = "data/habits.json"
    habit_tracker_model = HabitTrackerModel(DATA_FILE_PATH)
    habit_tracker_model.load_from_file()

    window = MainWindow()

    # Добавляем первую реализованную утилиту
    window.add_utility_tab(CurrencyWidget(), "Курсы валют")

    # Добавляем вторую реализованную утилиту
    window.add_utility_tab(BudgetWidget(), "Бюджет и накопления")

    # Добавляем третью реализованную утилиту
    window.add_utility_tab(HabitTrackerWidget(habit_tracker_model), "Трекер привычек")

    # Заглушки для остальных утилит
    window.add_utility_tab(StubWidget4(4), "Утилита №4")
    window.add_utility_tab(StubWidget5(5), "Утилита №5")

    window.showMaximized()

    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.instance().aboutToQuit.connect(habit_tracker_model.save_to_file)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()