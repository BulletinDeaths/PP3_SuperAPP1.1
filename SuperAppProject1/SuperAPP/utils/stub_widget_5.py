from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel


class StubWidget(QWidget):
    def __init__(self, number):
        super().__init__()
        self.setWindowTitle(f"Заглушка Утилита №{number}")

        layout = QVBoxLayout(self)

        label_info = QLabel(f"Эта вкладка является заглушкой для Утилиты №{number}.")
        label_info.setWordWrap(True)

        label_desc = QLabel("Здесь будет реализован функционал в будущем.")

        layout.addWidget(label_info)
        layout.addWidget(label_desc)