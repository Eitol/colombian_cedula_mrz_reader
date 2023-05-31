import datetime
from abc import ABC, abstractmethod

from domain.model import Document


class CheckDigitCalculator:
    @staticmethod
    def compute_check_digit(data: str) -> str:
        """
        Compute the validation digit for the given data
        :param data: e.g. "900101"
        :return: e.g. "1"
        """
        weights = [7, 3, 1]
        check_sum = 0
        for i in range(len(data)):
            char = data[i]
            if char.isdigit():
                check_sum += int(char) * weights[i % 3]
            elif char.isupper():
                check_sum += (ord(char) - 55) * weights[i % 3]
            elif char == '<':
                check_sum += 0
        return str(check_sum % 10)


class MRZParser(ABC):

    @abstractmethod
    def parse(self, mrz: str) -> Document:
        pass

    @classmethod
    def _parse_date(cls, date_str: str, date_check_digit: str, is_past: bool, field_name: str) -> datetime.date:
        """
        :param date_str: i.e. "900101" for January 1st, 1990
        :param date_check_digit: i.e. "1"
        :param is_past: if True, the year is assumed to be in the past, otherwise in the future
        :param field_name: i.e. "bird_date"
        :return: datetime.date
        """
        year_str = date_str[0:2]
        if not year_str.isnumeric():
            raise Exception(f'Invalid MRZ format: Invalid {field_name} year is not numeric')
        current_year = int(str(datetime.datetime.now().year)[2:4])
        year = int(year_str)
        if is_past:
            if year > current_year:
                year = 1900 + year
            else:
                year = 2000 + year
        else:
            year = 2000 + year
        date_month_str = date_str[2:4]
        if not date_month_str.isnumeric():
            raise Exception(f'Invalid MRZ format: Invalid {field_name} month is not numeric')
        date_day_str = date_str[4:6]
        if not date_day_str.isnumeric():
            raise Exception(f'Invalid MRZ format: Invalid {field_name} day is not numeric')
        date = datetime.date(year, int(date_month_str), int(date_day_str))
        if not date_check_digit.isnumeric():
            raise Exception(f'Invalid MRZ format: Invalid {field_name} check digit is not numeric')
        calculated_check_digit = cls._calculate_check_digit(date_str[0:2] + date_month_str + date_day_str)
        if date_check_digit != calculated_check_digit:
            raise Exception(f'Invalid MRZ format: Invalid {field_name} check digit {date_check_digit} '
                            f'expected {calculated_check_digit}')
        return date

    @staticmethod
    def _calculate_check_digit(data) -> str:
        return CheckDigitCalculator.compute_check_digit(data)
