import sys
from PyQt6.QtWidgets import QApplication

from SuperAppProject1.SuperAPP.ui.main_window import MainWindow
from SuperAppProject1.SuperAPP.utils.currency_widget import CurrencyWidget
from SuperAppProject1.SuperAPP.utils.stub_widget_2 import StubWidget as StubWidget2
from SuperAppProject1.SuperAPP.utils.stub_widget_3 import StubWidget as StubWidget3
from SuperAppProject1.SuperAPP.utils.stub_widget_4 import StubWidget as StubWidget4
from SuperAppProject1.SuperAPP.utils.stub_widget_5 import StubWidget as StubWidget5


def main():
    app = QApplication(sys.argv)

    window = MainWindow()

    # Добавляем первую реализованную утилиту
    window.add_utility_tab(CurrencyWidget(), "Курсы валют")

    # Добавляем заглушки для остальных утилит
    window.add_utility_tab(StubWidget2(2), "Утилита №2")
    window.add_utility_tab(StubWidget3(3), "Утилита №3")
    window.add_utility_tab(StubWidget4(4), "Утилита №4")
    window.add_utility_tab(StubWidget5(5), "Утилита №5")

    window.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()