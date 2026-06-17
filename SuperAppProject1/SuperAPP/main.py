import sys
from PyQt6.QtWidgets import QApplication

from SuperAppProject1.SuperAPP.core.navigation import data_path
from SuperAppProject1.SuperAPP.ui.main_window import MainWindow
from SuperAppProject1.SuperAPP.ui.widgets.currency_widget import CurrencyWidget

from SuperAppProject1.SuperAPP.ui.widgets.budget_widget import BudgetWidget

from SuperAppProject1.SuperAPP.ui.widgets.habit_tracker_widget import HabitTrackerWidget
from SuperAppProject1.SuperAPP.models.habit_tracker_model import HabitTrackerModel

from SuperAppProject1.SuperAPP.models.schedule.storage import Storage
from SuperAppProject1.SuperAPP.models.schedule.schedule_engine import ScheduleEngine
from SuperAppProject1.SuperAPP.ui.widgets.schedule_widget import ScheduleWidget

from SuperAppProject1.SuperAPP.ui.widgets.game_stats_widget import GameStatsWidget


def main():
    app = QApplication(sys.argv)

    habit_tracker_model = HabitTrackerModel(data_path("habits.json"))
    habit_tracker_model.load_from_file()

    storage = Storage(data_path("schedule.json"))
    # Создаем ядро логики расписания и передаем ему хранилище.
    schedule_engine = ScheduleEngine(storage)
    # Создаем виджет расписания и передаем ему ядро логики.
    schedule_widget = ScheduleWidget(schedule_engine)

    window = MainWindow()

    # Добавляем первую реализованную утилиту
    window.add_utility_tab(CurrencyWidget(), "Курсы валют")

    # Добавляем вторую реализованную утилиту
    window.add_utility_tab(BudgetWidget(), "Бюджет и накопления")

    # Добавляем третью реализованную утилиту
    window.add_utility_tab(HabitTrackerWidget(habit_tracker_model), "Трекер привычек")

    # Добавляем четвёртую реализованную утилиту
    window.add_utility_tab(schedule_widget, "Расписание")

    # Добавляем пятую реализованную утилиту
    window.add_utility_tab(GameStatsWidget(), "Статистика игры")

    window.showMaximized()

    from PyQt6.QtCore import QCoreApplication
    QCoreApplication.instance().aboutToQuit.connect(habit_tracker_model.save_to_file)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
