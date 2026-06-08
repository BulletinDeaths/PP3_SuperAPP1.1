import requests
import pandas as pd
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QDateEdit, QHBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QDate, Qt
import plotly.graph_objs as go

# Словарь для конвертации понятных кодов в ID Центробанка РФ
CBR_CURRENCY_IDS = {
    'USD': 'R01235',
    'EUR': 'R01239',
    'CNY': 'R01375',
    'GBP': 'R01035',
    'JPY': 'R01365',
    'CHF': 'R01775',
    'RUB': 'RUB'  # Оставляем маркер для базовой валюты
}


class CurrencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Курсы валют")
        self.layout = QVBoxLayout(self)

        # Виджеты для выбора валют и дат
        self.from_currency = QComboBox()
        self.to_currency = QComboBox()

        # Исправлено: Настройка calendarPopup через методы, а не конструктор
        self.from_date = QDateEdit()
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit()
        self.to_date.setCalendarPopup(True)

        self.btn_plot = QPushButton("Построить график")
        self.status_label = QLabel("Выберите валюты и период")

        # Настройка дат (по умолчанию - последние 7 дней)
        self.to_date.setDate(QDate.currentDate())
        self.from_date.setDate(QDate.currentDate().addDays(-7))

        # Заполнение списков валют
        currencies = list(CBR_CURRENCY_IDS.keys())
        self.from_currency.addItems(currencies)
        self.to_currency.addItems(currencies)

        # Установим по умолчанию разные валюты, чтобы не считать кросс-курс к самой себе сразу
        self.from_currency.setCurrentText('USD')
        self.to_currency.setCurrentText('RUB')

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

        # Принудительно обрабатываем события интерфейса, чтобы надпись "Загрузка..." успела появиться
        self.status_label.repaint()

        code_from = self.from_currency.currentText()
        code_to = self.to_currency.currentText()

        if code_from == code_to:
            self.status_label.setText("Выберите две разные валюты!")
            return

        date1 = self.from_date.date().toString('dd/MM/yyyy')
        date2 = self.to_date.date().toString('dd/MM/yyyy')

        # Получаем внутренние ID для запроса к ЦБ
        id_from = CBR_CURRENCY_IDS[code_from]
        id_to = CBR_CURRENCY_IDS[code_to]

        try:
            # Сценарий 1: Конвертация иностранной валюты к Рублю напрямую
            if code_to == 'RUB':
                url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={id_from}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                df = pd.read_xml(response.content, xpath=".//Record")
                if df.empty or 'Value' not in df.columns:
                    self.status_label.setText("Нет данных за выбранный период.")
                    return

                df['Date'] = pd.to_datetime(df['@Date'], format='%d.%m.%Y')
                df['Rate'] = df['Value'].str.replace(',', '.').astype(float)

                # Корректируем курс с учетом номинала (Nominal), так как, например, 100 JPY отдаются одной записью
                if 'Nominal' in df.columns:
                    df['Rate'] = df['Rate'] / df['Nominal'].astype(float)

            # Сценарий 2: Расчет кросс-курса (две иностранные валюты, либо RUB к чему-то)
            else:
                # Если исходная валюта - Рубль
                if code_from == 'RUB':
                    url_to = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={id_to}"
                    df_to = pd.read_xml(requests.get(url_to, timeout=10).content, xpath=".//Record")

                    df_to['Date'] = pd.to_datetime(df_to['@Date'], format='%d.%m.%Y')
                    df_to['RateToRUB'] = df_to['Value'].str.replace(',', '.').astype(float)
                    if 'Nominal' in df_to.columns:
                        df_to['RateToRUB'] = df_to['RateToRUB'] / df_to['Nominal'].astype(float)

                    df = df_to.copy()
                    df['Rate'] = 1.0 / df['RateToRUB']

                # Если обе валюты иностранные (например, USD к EUR)
                else:
                    url_from = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={id_from}"
                    url_to = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={id_to}"

                    df_from = pd.read_xml(requests.get(url_from, timeout=10).content, xpath=".//Record")
                    df_to = pd.read_xml(requests.get(url_to, timeout=10).content, xpath=".//Record")

                    df_from['Date'] = pd.to_datetime(df_from['@Date'], format='%d.%m.%Y')
                    df_from['RateFromRUB'] = df_from['Value'].str.replace(',', '.').astype(float)
                    if 'Nominal' in df_from.columns:
                        df_from['RateFromRUB'] = df_from['RateFromRUB'] / df_from['Nominal'].astype(float)

                    df_to['Date'] = pd.to_datetime(df_to['@Date'], format='%d.%m.%Y')
                    df_to['RateToRUB'] = df_to['Value'].str.replace(',', '.').astype(float)
                    if 'Nominal' in df_to.columns:
                        df_to['RateToRUB'] = df_to['RateToRUB'] / df_to['Nominal'].astype(float)

                    # Объединяем по датам и вычисляем отношение
                    df = pd.merge_asof(df_from.sort_values('Date'), df_to.sort_values('Date'), on='Date')
                    df['Rate'] = df['RateFromRUB'] / df['RateToRUB']

            # Сортируем по дате для правильного отображения линии графика
            df = df.sort_values('Date')

            # Строим график с помощью Plotly
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df['Date'],
                y=df['Rate'],
                mode='lines+markers',
                name=f'{code_from}/{code_to}',
                line=dict(color='#2ca02c', width=2) # Зеленый оттенок
            ))

            fig.update_layout(
                title_text=f'Динамика курса {code_from} к {code_to}',
                xaxis_title='Дата',
                yaxis_title='Курс',
                template='plotly_white',
                margin=dict(l=40, r=40, t=40, b=40)
            )

            # Важно: используем include_plotlyjs='cdn'.
            # Это кардинально уменьшает размер строки данных, убирая XML/HTML ошибку обрезки в QtWebEngine.
            html_content = fig.to_html(include_plotlyjs='cdn', full_html=True)
            self.plot_view.setHtml(html_content)

            self.status_label.setText(f"График построен за период с {date1} по {date2}.")

        except Exception as e:
            self.status_label.setText(f"Ошибка при обработке или загрузке данных: {e}")