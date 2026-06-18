import unittest
from unittest.mock import patch
from io import BytesIO

from SuperAppProject1.SuperAPP.ui.widgets.currency_widget import CurrencyWidget

class TestCurrencyParsing(unittest.TestCase):
    def test_parse_xml(self):
        widget = CurrencyWidget()
        sample_xml = '''
        <?xml version="1.0"?>
        <ValCurs Date="01.01.2023">
            <Record Date="01.01.2023" Id="R01235">
                <Nominal>1</Nominal>
                <Value>75.00</Value>
            </Record>
        </ValCurs>
        '''
        df = widget.parse_cbr_data(BytesIO(sample_xml.encode()))
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]['Value'], 75.0)

    @patch('requests.get')
    def test_fetch_data(self, mock_get):
        mock_response = unittest.mock.Mock()
        mock_response.content = b'<ValCurs><Record Date="01.01.2023"><Value>75.00</Value></Record></ValCurs>'
        mock_get.return_value = mock_response
        widget = CurrencyWidget()
        df = widget.fetch_and_plot_data()
        self.assertGreater(len(df), 0)

if __name__ == '__main__':
    unittest.main()