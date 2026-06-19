import unittest
from unittest.mock import patch, MagicMock

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
