import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objs as go
import requests

from PyQt6.QtCore import QDate
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QDateEdit, QHBoxLayout


class CurrencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Курсы валют")
        self.setMinimumSize(800, 600)
        self.layout = QVBoxLayout(self)

        # Виджеты для выбора валют и дат
        self.from_currency = QComboBox()
        self.to_currency = QComboBox()
        self.from_date = QDateEdit(calendarPopup=True)
        self.to_date = QDateEdit(calendarPopup=True)
        self.btn_plot = QPushButton("Построить график")
        self.status_label = QLabel("Выберите валюты и период")

        # Настройка дат
        self.to_date.setDate(QDate.currentDate())
        self.from_date.setDate(QDate.currentDate().addDays(-30))

        self.currency_codes = {
            'RUB': 'RUB',
            'USD': 'R01235',
            'EUR': 'R01239',
            'CNY': 'R01375',
            'GBP': 'R01035',
            'JPY': 'R01820',
            'CHF': 'R01775'
        }

        currencies = ['RUB', 'USD', 'EUR', 'CNY', 'GBP', 'JPY', 'CHF']
        self.from_currency.addItems(currencies)
        self.to_currency.addItems(currencies)

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

        # График
        self.plot_view = QWebEngineView()
        self.plot_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        self.layout.addWidget(self.plot_view)

        self.btn_plot.clicked.connect(self.fetch_and_plot_data)

    def fetch_and_plot_data(self):
        """Получение данных и отображение графика"""
        # 1. Очищаем статус-листу
        self.status_label.clear()

        # 2. Удаляем старый из макета, если он существует
        if hasattr(self, 'plot_view'):
            self.layout.removeWidget(self.plot_view)

            self.plot_view.close()
            self.plot_view.deleteLater()

        self.status_label.setText("Загрузка данных...")
        self.status_label.setStyleSheet("color: blue;")

        #UI
        QApplication.processEvents()

        code_from = self.from_currency.currentText()
        code_to = self.to_currency.currentText()

        date1 = self.from_date.date().toString('dd/MM/yyyy')
        date2 = self.to_date.date().toString('dd/MM/yyyy')

        try:
            df = None
            # Если обе валюты одинаковы
            if code_from == code_to:
                self.show_simple_graph(code_from, date1, date2)
                return

            # Получаем данные для исходной валюты
            if code_from != 'RUB':
                code_from_real = self.currency_codes[code_from]
                url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_from_real}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()

                df_from = self.parse_cbr_data(response.content)

                if df_from.empty:
                    self.status_label.setText("❌ Нет данных за выбранный период для исходной валюты.")
                    self.status_label.setStyleSheet("color: red;")
                    return

                df = df_from[['Date', 'Value']].copy()
                df.columns = ['Date', 'RateToRUB']
            else:
                # Если исходная валюта RUB
                start_date = pd.to_datetime(date1, format='%d/%m/%Y')
                end_date = pd.to_datetime(date2, format='%d/%m/%Y')
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                df = pd.DataFrame({'Date': date_range, 'RateToRUB': 1.0})

            # Получаем данные для целевой валюты
            if code_to != 'RUB':
                code_to_real = self.currency_codes[code_to]
                url_to = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_to_real}"
                response_to = requests.get(url_to, timeout=10)
                response_to.raise_for_status()

                df_to = self.parse_cbr_data(response_to.content)

                if df_to.empty:
                    self.status_label.setText("❌ Нет данных за выбранный период для целевой валюты.")
                    self.status_label.setStyleSheet("color: red;")
                    return

                df = pd.merge(df, df_to[['Date', 'Value']], on='Date', how='inner')
                df['Rate'] = df['RateToRUB'] / df['Value']
            else:
                df['Rate'] = df['RateToRUB']

            if df.empty or len(df) == 0:
                self.status_label.setText("❌ Нет данных для построения графика.")
                self.status_label.setStyleSheet("color: red;")
                return

            # Этот блок выполняется только если данные успешно получены
            self.plot_view = QWebEngineView()
            self.plot_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

            self.layout.addWidget(self.plot_view)

            # Сортируем по дате
            df = df.sort_values('Date')

            # Строим график
            self.create_and_display_plot(df, code_from, code_to, date1, date2)

        except requests.RequestException as e:
            # Если произошла ошибка, создать пустой plot_view,
            self.plot_view = QWebEngineView()
            self.layout.addWidget(self.plot_view)

            self.status_label.setText(f"❌ Ошибка сети: {e}")
            self.status_label.setStyleSheet("color: red;")
        except Exception as e:
            self.status_label.setText(f"❌ Ошибка: {str(e)}")
            self.status_label.setStyleSheet("color: red;")
            print(f"Детали ошибки: {e}")

    def show_simple_graph(self, currency, date1, date2):
        """Показывает простой график для одинаковых валют."""
        dates = pd.date_range(start=pd.to_datetime(date1, format='%d/%m/%Y'),
                              end=pd.to_datetime(date2, format='%d/%m/%Y'),
                              freq='D')
        values = [1.0] * len(dates)
        df = pd.DataFrame({'Date': dates, 'Rate': values})
        self.create_and_display_plot(df, currency, currency, date1, date2)

    def parse_cbr_data(self, xml_content):
        """Парсит XML данные ЦБ РФ."""
        try:
            root = ET.fromstring(xml_content)
            data = []

            for record in root.findall('.//Record'):
                date = record.get('Date')
                value_elem = record.find('Value')
                nominal_elem = record.find('Nominal')

                if value_elem is not None and value_elem.text:
                    value_str = value_elem.text.strip().replace(',', '.')
                    try:
                        value = float(value_str)
                        # Учитываем номинал, если он есть
                        if nominal_elem is not None and nominal_elem.text:
                            nominal = int(nominal_elem.text)
                            value = value / nominal
                        data.append({'Date': pd.to_datetime(date, format='%d.%m.%Y'), 'Value': value})
                    except ValueError:
                        continue

            return pd.DataFrame(data)
        except ET.ParseError as e:
            print(f"Ошибка парсинга XML: {e}")
            return pd.DataFrame()

    def create_and_display_plot(self, df, code_from, code_to, date1, date2):
        """Создает и отображает график."""
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Rate'],
            mode='lines+markers',
            name=f'{code_from}/{code_to}',
            line=dict(width=2, color='royalblue'),
            marker=dict(size=6, color='darkblue'),
            hovertemplate='<b>Дата:</b> %{x|%d.%m.%Y}<br>' +
                          '<b>Курс:</b> %{y:.4f}<br>' +
                          '<extra></extra>'
        ))

        # Настройка оформления
        fig.update_layout(
            title=dict(
                text=f'<b>Динамика курса {code_from} к {code_to}</b>',
                x=0.5,
                xanchor='center',
                font=dict(size=16)
            ),
            xaxis_title='<b>Дата</b>',
            yaxis_title=f'<b>Курс ({code_from}/{code_to})</b>',
            template='plotly_white',
            hovermode='x unified',
            plot_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                tickformat='%d.%m.%Y'
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='lightgray',
                tickformat='.4f'
            ),
            margin=dict(l=60, r=40, t=60, b=50)
        )

        # Генерирует HTML
        html_content = fig.to_html(
            full_html=True,
            include_plotlyjs='cdn',
            config={'responsive': True, 'displayModeBar': True}
        )

        profile = self.plot_view.page().profile()
        # меням кэш на "не использовать кэш"
        profile.setCachePath("")
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.NoCache)

        # Отображает график
        self.plot_view.setHtml(html_content)

        # Статус
        self.status_label.setText(f"✅ График построен. Период: с {date1} по {date2} (точек: {len(df)})")
        self.status_label.setStyleSheet("color: green;")

        # Принудительно обновляет виджет графика
        self.plot_view.reload()
        QApplication.processEvents()
