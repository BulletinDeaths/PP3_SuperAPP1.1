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

    def add_utility_tab(self, widget_instance, title):
        """Метод для добавления новой вкладки-утилиты."""
        self.tab_widget.addTab(widget_instance, title)