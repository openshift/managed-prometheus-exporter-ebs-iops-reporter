import unittest
import mock
import time
from main import round_time

from datetime import datetime, timedelta


class TestMain(unittest.TestCase):
    @mock.patch('main.get_utcnow')
    def test_round_time(self, mock_datetime):
        mock_datetime.utcnow.return_value = datetime(
            2012, 12, 12, 12, 12, 12, 12)
        r = round_time(mock_datetime.utcnow.return_value, 5)
        verify = datetime(2012, 12, 12, 12, 10)
        self.assertEqual(verify, r)
        mock_datetime.utcnow.return_value = datetime(
            2021, 11, 11, 17, 49, 1, 13)
        r = round_time(mock_datetime.utcnow.return_value, 5)
        verify = datetime(2021, 11, 11, 17, 50)
        self.assertEqual(verify, r)


if __name__ == "__main__":
    unittest.main()
