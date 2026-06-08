import requests
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QDateEdit, QHBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QDate, Qt
import plotly.graph_objs as go


class CurrencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Курсы валют")
        self.layout = QVBoxLayout(self)

        # Виджеты для выбора валют и дат
        self.from_currency = QComboBox()
        self.to_currency = QComboBox()
        self.from_date = QDateEdit(calendarPopup=True)
        self.to_date = QDateEdit(calendarPopup=True)
        self.btn_plot = QPushButton("Построить график")
        self.status_label = QLabel("Выберите валюты и период")

        # Настройка дат (по умолчанию - последние 7 дней)
        self.to_date.setDate(QDate.currentDate())
        self.from_date.setDate(QDate.currentDate().addDays(-7))

        # Заполнение списков валют (основные)
        currencies = ['USD', 'EUR', 'CNY', 'GBP', 'JPY', 'CHF']
        self.from_currency.addItems(currencies)
        self.to_currency.addItems(currencies)

        # Компоновка
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("От:"))
        top_layout.addWidget(self.from_currency)
        top_layout.addWidget(QLabel("К:"))
        top_layout.addWidget(self.to_currency)
        top_layout.addWidget(QLabel("С:"))
        top_layout.addWidget(self.from_date)
        top_layout.addWidget(QLabel("По:"))
        top_layout.addWidget(self.to_date)
        top_layout.addWidget(self.btn_plot)

        self.layout.addLayout(top_layout)
        self.layout.addWidget(self.status_label)

        # График будет отображаться здесь
        self.plot_view = QWebEngineView()
        self.layout.addWidget(self.plot_view)

        # Подключение сигнала кнопки к функции построения графика
        self.btn_plot.clicked.connect(self.fetch_and_plot_data)

    def fetch_and_plot_data(self):
        """Получает данные с сайта ЦБ РФ и строит график."""
        self.status_label.setText("Загрузка данных...")

        code_from = self.from_currency.currentText()
        code_to = self.to_currency.currentText()

        date1 = self.from_date.date().toString('dd/MM/yyyy')
        date2 = self.to_date.date().toString('dd/MM/yyyy')

        url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_from}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            # Парсим XML в DataFrame с помощью pandas
            df = pd.read_xml(response.content, xpath=".//Record")

            if df.empty:
                self.status_label.setText("Нет данных за выбранный период.")
                return

            # Преобразуем дату и значение курса
            df['Date'] = pd.to_datetime(df['@Date'], format='%d.%m.%Y')
            # Курс к рублю находится в элементе 'Value', курс к другой валюте нужно рассчитать
            if code_to == 'RUB':
                df['Rate'] = df['Value'].str.replace(',', '.').astype(float)
            else:
                # Получаем курс второй валюты к рублю на те же даты (для упрощения примера - запрос к RUB)
                url_to = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_to}"
                df_to = pd.read_xml(requests.get(url_to).content, xpath=".//Record")
                df_to['Date'] = pd.to_datetime(df_to['@Date'], format='%d.%m.%Y')
                df_to['RateToRUB'] = df_to['Value'].str.replace(',', '.').astype(float)

                # Сливаем DataFrame'ы и считаем кросс-курс
                df = pd.merge_asof(df.sort_values('Date'), df_to.sort_values('Date'), on='Date')
                df['Rate'] = df['Value'].str.replace(',', '.').astype(float) / df['RateToRUB']

            # Строим график с помощью Plotly
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df['Date'], y=df['Rate'], mode='lines+markers', name=f'{code_from}/{code_to}'))
            fig.update_layout(
                title_text=f'Динамика курса {code_from} к {code_to}',
                xaxis_title='Дата',
                yaxis_title='Курс',
                template='plotly_white'
            )

            # Отображаем график в QWebEngineView. Метод to_html() создает автономный HTML.
            self.plot_view.setHtml(fig.to_html(full_html=True))
            self.status_label.setText(f"График построен за период с {date1} по {date2}.")

        except Exception as e:
            self.status_label.setText(f"Ошибка при загрузке данных: {e}")