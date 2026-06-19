import unittest
from unittest.mock import patch, MagicMock

# ВАЖНО: изначально планировалось мокать QWebEngineView, чтобы избежать
# возможной тяжести инициализации в headless/CI-среде. Но реальный
# CurrencyWidget.__init__ передаёт self.plot_view в несколько мест, где
# Qt на уровне C++ требует НАСТОЯЩИЙ QWidget/QObject, а не MagicMock:
#   - Loader(self.plot_view) -> super().__init__(view) ждёт QObject
#   - self.layout.addWidget(self.plot_view) -> ждёт QWidget
# Подмена класса целиком на MagicMock ломает оба места с TypeError.
# Простое СОЗДАНИЕ QWebEngineView само по себе не зависает и не требует
# сети — тяжесть появляется только при реальной загрузке HTML/JS
# (setHtml с большим контентом, сетевые ресурсы). Наши тесты не вызывают
# setHtml вообще (test_parse_xml) или вызывают его с локальным графиком
# без сети (test_fetch_data, через замоканный requests.get) — поэтому
# реальный QWebEngineView создавать безопасно, мокать не нужно.
from PyQt6.QtCore import QDate
from SuperAppProject1.SuperAPP.ui.widgets.currency_widget import CurrencyWidget


def _make_widget():
    return CurrencyWidget()


class TestCurrencyParsing(unittest.TestCase):
    def test_parse_xml(self):
        widget = _make_widget()
        sample_xml = (
            '<?xml version="1.0"?>'
            '<ValCurs Date="01.01.2023">'
            '<Record Date="01.01.2023" Id="R01235">'
            '<Nominal>1</Nominal>'
            '<Value>75.00</Value>'
            '</Record>'
            '</ValCurs>'
        )
        # parse_cbr_data вызывает ET.fromstring(xml_content), который
        # принимает строку/байты, а не файлоподобный объект — передаём
        # закодированную строку напрямую, а не BytesIO.
        df = widget.parse_cbr_data(sample_xml.strip().encode())
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Value'], 75.0)

    @patch('SuperAppProject1.SuperAPP.ui.widgets.currency_widget.requests.get')
    def test_fetch_data(self, mock_get):
        """
        Проверяет, что fetch_and_plot_data обрабатывает ответ сети без
        реального HTTP-запроса (requests.get замокан). QWebEngineView
        используется настоящий — setHtml с локальной строкой не требует
        сети и не зависает, поэтому мокать его не нужно (см. комментарий
        в начале файла).
        """
        widget = _make_widget()

        sample_xml = (
            b'<ValCurs Date="01.01.2023">'
            b'<Record Date="01.01.2023" Id="R01235">'
            b'<Nominal>1</Nominal><Value>75,00</Value>'
            b'</Record>'
            b'<Record Date="02.01.2023" Id="R01235">'
            b'<Nominal>1</Nominal><Value>76,00</Value>'
            b'</Record>'
            b'</ValCurs>'
        )
        mock_response = MagicMock()
        mock_response.content = sample_xml
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # from_currency/to_currency по умолчанию RUB -> USD: запрос на
        # USD реально уйдёт в requests.get (замоканный).
        widget.from_currency.setCurrentText('RUB')
        widget.to_currency.setCurrentText('USD')

        widget.from_date.setDate(QDate(2023, 1, 1))
        widget.to_date.setDate(QDate(2023, 1, 2))

        widget.fetch_and_plot_data()

        self.assertTrue(widget.is_loading)
        self.assertIsNotNone(widget._pending_status)
        self.assertIn("✅", widget._pending_status)


if __name__ == '__main__':
    unittest.main()
