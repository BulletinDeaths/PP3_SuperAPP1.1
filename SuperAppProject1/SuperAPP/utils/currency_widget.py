import xml.etree.ElementTree as ET
import pandas as pd
import plotly.graph_objs as go
import requests

from PyQt6.QtCore import QDate, pyqtSignal, QObject
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox, QPushButton, QLabel, QDateEdit, QHBoxLayout


# --- Вспомогательный класс для сигнала о завершении загрузки страницы ---
class Loader(QObject):
    """Этот класс будет испускать сигнал, когда страница в QWebEngineView загружена."""
    finished = pyqtSignal()

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.view.loadFinished.connect(self.on_load_finished)

    def on_load_finished(self, success):
        self.finished.emit()


class CurrencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Утилита: Курсы валют")
        self.setMinimumSize(800, 600)
        self.layout = QVBoxLayout(self)

        # --- Виджеты ---
        self.from_currency = QComboBox()
        self.to_currency = QComboBox()
        self.from_date = QDateEdit(calendarPopup=True)
        self.to_date = QDateEdit(calendarPopup=True)
        self.btn_plot = QPushButton("Построить график")
        self.status_label = QLabel("Выберите валюты и период")

        # --- Настройки дат ---
        self.to_date.setDate(QDate.currentDate())
        self.from_date.setDate(QDate.currentDate().addDays(-30))

        # --- Словарь кодов валют ЦБ РФ ---
        self.currency_codes = {
            'RUB': 'RUB',
            'USD': 'R01235',
            'EUR': 'R01239',
            'CNY': 'R01375',
            'GBP': 'R01035',
            'JPY': 'R01820',
            'CHF': 'R01775'
        }

        self._currencies = ['RUB', 'USD', 'EUR', 'CNY', 'GBP', 'JPY', 'CHF']
        self.from_currency.addItems(self._currencies)
        self.to_currency.addItems(self._currencies)

        # По умолчанию «От» = USD, «К» = RUB — сразу разные
        self.from_currency.setCurrentText('USD')
        self.to_currency.setCurrentText('RUB')

        # Взаимная блокировка одинакового выбора
        self.from_currency.currentTextChanged.connect(self._on_from_changed)
        self.to_currency.currentTextChanged.connect(self._on_to_changed)

        # --- Компоновка UI ---
        top_layout = QHBoxLayout()
        top_layout.setSpacing(2)

        lbl_from = QLabel("От:")
        lbl_from.setContentsMargins(6, 0, 0, 0)
        top_layout.addWidget(lbl_from)
        top_layout.addWidget(self.from_currency)

        lbl_to = QLabel("К:")
        lbl_to.setContentsMargins(10, 0, 0, 0)
        top_layout.addWidget(lbl_to)
        top_layout.addWidget(self.to_currency)

        lbl_from_date = QLabel("С:")
        lbl_from_date.setContentsMargins(10, 0, 0, 0)
        top_layout.addWidget(lbl_from_date)
        top_layout.addWidget(self.from_date)

        lbl_to_date = QLabel("По:")
        lbl_to_date.setContentsMargins(10, 0, 0, 0)
        top_layout.addWidget(lbl_to_date)
        top_layout.addWidget(self.to_date)

        top_layout.addWidget(self.btn_plot)

        self.layout.addLayout(top_layout)
        self.layout.addWidget(self.status_label)

        # --- Инициализация атрибутов ---
        self.is_loading = False

        self.plot_view = QWebEngineView()
        self.plot_view.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        self._loader = Loader(self.plot_view)
        self._loader.finished.connect(self._on_plot_loaded)

        self.layout.addWidget(self.plot_view)

        self.btn_plot.clicked.connect(self.fetch_and_plot_data)

    def _on_from_changed(self, value: str) -> None:
        """Если «От» совпало с «К» — переключаем «К» на первую другую валюту."""
        if value == self.to_currency.currentText():
            for c in self._currencies:
                if c != value:
                    # Блокируем обратный сигнал чтобы не зациклиться
                    self.to_currency.blockSignals(True)
                    self.to_currency.setCurrentText(c)
                    self.to_currency.blockSignals(False)
                    break

    def _on_to_changed(self, value: str) -> None:
        """Если «К» совпало с «От» — переключаем «От» на первую другую валюту."""
        if value == self.from_currency.currentText():
            for c in self._currencies:
                if c != value:
                    self.from_currency.blockSignals(True)
                    self.from_currency.setCurrentText(c)
                    self.from_currency.blockSignals(False)
                    break

    def _on_plot_loaded(self):
        """Этот метод вызывается, когда график полностью отрисован."""
        self.is_loading = False
        if hasattr(self, '_pending_status') and self._pending_status:
            self.status_label.setText(self._pending_status)
            self.status_label.setStyleSheet('color: green;')
            self._pending_status = None

    def fetch_and_plot_data(self):
        """Получение данных и отображение графика"""

        # 1. Блокировка от повторных нажатий, пока идет загрузка
        if getattr(self, 'is_loading', False):
            return
        self.is_loading = True

        # Получаем текущие значения из интерфейса
        code_from = self.from_currency.currentText()
        code_to = self.to_currency.currentText()
        date1 = self.from_date.date().toString('dd/MM/yyyy')
        date2 = self.to_date.date().toString('dd/MM/yyyy')

        # 2. Обновляем статус
        self.status_label.setText("Загрузка данных...")
        self.status_label.setStyleSheet("color: blue;")
        QApplication.processEvents()

        df = None

        try:
            # --- Блок получения данных ---
            if code_from != 'RUB':
                code_from_real = self.currency_codes[code_from]
                url = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_from_real}"
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                df_from = self.parse_cbr_data(response.content)
                if df_from.empty:
                    raise ValueError(f"Нет данных за выбранный период для валюты {code_from}.")
                df = df_from[['Date', 'Value']].copy()
                df.columns = ['Date', 'RateToRUB']
            else:
                # Если исходная валюта - RUB, курс к RUB всегда 1
                start_date = pd.to_datetime(date1, format='%d/%m/%Y')
                end_date = pd.to_datetime(date2, format='%d/%m/%Y')
                date_range = pd.date_range(start=start_date, end=end_date, freq='D')
                df = pd.DataFrame({'Date': date_range, 'RateToRUB': 1.0})

            # Получаем данные для целевой валюты (К:)
            if code_to != 'RUB':
                code_to_real = self.currency_codes[code_to]
                url_to = f"https://www.cbr.ru/scripts/XML_dynamic.asp?date_req1={date1}&date_req2={date2}&VAL_NM_RQ={code_to_real}"
                response_to = requests.get(url_to, timeout=10)
                response_to.raise_for_status()
                df_to = self.parse_cbr_data(response_to.content)
                if df_to.empty:
                    raise ValueError(f"Нет данных за выбранный период для валюты {code_to}.")

                # Объединяем данные и вычисляем итоговый курс
                df = pd.merge(df, df_to[['Date', 'Value']], on='Date', how='inner')
                df['Rate'] = df['RateToRUB'] / df['Value']
            else:
                # Если целевая валюта - RUB, итоговый курс равен курсу к RUB
                df['Rate'] = df['RateToRUB']

            if df.empty or len(df) == 0:
                raise ValueError("Нет данных для построения графика.")

            # Сортируем по дате
            df = df.sort_values('Date').reset_index(drop=True)

            # --- Блок отображения графика ---
            html_content = self._generate_plot_html(df, code_from, code_to)
            self._pending_status = (
                f"✅ График построен: {code_from}/{code_to}, "
                f"период с {date1} по {date2} (точек: {len(df)})"
            )
            self.plot_view.setHtml(html_content)

        except requests.RequestException as e:
            self.status_label.setText(f"❌ Ошибка сети: {e}")
            self.status_label.setStyleSheet("color: red;")
            # В случае ошибки сразу разблокируем кнопку
            self.is_loading = False
        except Exception as e:
            error_msg = str(e)
            self.status_label.setText(f"❌ Ошибка: {error_msg}")
            self.status_label.setStyleSheet("color: red;")
            print(f"Детали ошибки: {e}")
            # В случае ошибки сразу разблокируем кнопку
            self.is_loading = False


    def _generate_plot_html(self, df, code_from, code_to):
        """Генерирует HTML-код для графика. Вынесено в отдельный метод для чистоты."""
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df['Date'],
            y=df['Rate'],
            mode='lines+markers',
            name=f'{code_from}/{code_to}',
            line=dict(width=2),
        ))
        fig.update_layout(
            title=f'Динамика курса {code_from} к {code_to}',
            xaxis_title='Дата',
            yaxis_title=f'Курс ({code_from}/{code_to})',
        )
        return fig.to_html(
            full_html=True,
            include_plotlyjs='cdn',
            config={'responsive': True}
        )

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