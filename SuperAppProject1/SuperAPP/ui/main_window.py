from PyQt6.QtWidgets import QWidget, QTabWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SuperApp")

        main_layout = QVBoxLayout(self)

        header_label = QLabel("<h1>SuperApp</h1><p>Ваш универсальный помощник</p>")
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tab_widget = QTabWidget()

        main_layout.addWidget(header_label)
        main_layout.addWidget(self.tab_widget)

        # ГЛОБАЛЬНЫЕ СТИЛИ ДЛЯ ВСЕХ КОМПОНЕНТОВ ОКНА
        self.setStyleSheet("""
                    /* Общий стиль для всех кнопок */
                    QPushButton {
                        background-color: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #4CAF50, stop:1 #3E8E41);
                        color: white;
                        border-radius: 5px;
                        padding: 8px 16px;
                        font-weight: bold;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                    }

                    /* Ховер эффект */
                    QPushButton:hover {
                        background-color: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #45a049, stop:1 #38793B);
                    }

                    /* Кнопка отмены */
                    QPushButton[cancel="true"] {
                        background-color: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #f44336, stop:1 #d32f2f);
                    }

                    /* Кнопка отмены при ховере */
                    QPushButton[cancel="true"]:hover {
                        background-color: qlineargradient(x1:0 y1:0, x2:1 y2:0, stop:0 #d32f2f, stop:1 #c62828);
                    }

                    /* Надпись "Сегодня" */
                    QPushButton[today="true"] {
                        background-color: transparent;
                        color: blue;
                        font-style: italic;
                        padding-left: 0;
                    }

                    /* Надпись "Новая игра" */
                    QPushButton[new-game="true"] {
                        background-image: url(:/icons/new_game_icon.png); /* Можешь заменить на свой путь */
                        background-repeat: no-repeat;
                        background-position: center left;
                        padding-left: 30px;
                    }
                """)

    def add_utility_tab(self, widget_instance, title):
        """Метод для добавления новой вкладки-утилиты."""
        self.tab_widget.addTab(widget_instance, title)