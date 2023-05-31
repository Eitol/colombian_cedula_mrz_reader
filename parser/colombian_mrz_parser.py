import datetime
from dataclasses import dataclass
from typing import List, Optional

from iso3166 import countries

from domain.model import DocumentFields, Sex, DocumentMetadata
from parser.locatilities import LOCALITIES
from parser.mrz_parser import MRZParser, Document


@dataclass()
class _MRZL1:
    doc_type: str
    country_code: str
    country_name: str
    doc_number: str
    doc_number_check_digit: str
    mun_code: str
    mun_name: str
    dep_code: str
    dep_name: str
    confidence: float
    errors: List[BaseException]


@dataclass()
class _MRZL2:
    bird_date: Optional[datetime.date]
    sex: str
    expiration_date: Optional[datetime.date]
    nationality_country_code: str
    nationality_country_name: str
    nuip: str
    confidence: float
    errors: List[BaseException]


@dataclass()
class _MRZL3:
    first_names: str
    last_names: str
    is_truncated: bool


class ColombianMRZParser(MRZParser):
    """
    This class provides a parser for Colombian Machine Readable Zone (MRZ) strings
    The parser can validate and extract relevant data from the MRZ string.
    The MRZ string is broken down into 3 lines, each of which is parsed separately.
    """

    def parse(self, mrz: str) -> Document:
        lines = mrz.strip().replace(' ', '').split('\n')
        if len(lines) != 3:
            raise Exception('Invalid MRZ format: Invalid number of lines')
        return self._parse_by_lines(lines[0], lines[1], lines[2])

    @classmethod
    def _parse_by_lines(cls, l1: str, l2: str, l3: str) -> Document:
        parsed_l1 = cls._parse_mrz_l1(l1)
        parsed_l2 = cls._parse_mrz_l2(l2)
        parsed_l3 = cls._parse_mrz_l3(l3)
        fields = DocumentFields(
            bird_date=parsed_l2.bird_date,
            sex=Sex.parse(parsed_l2.sex),
            expiration_date=parsed_l2.expiration_date,
            nationality_country_code=parsed_l2.nationality_country_code,
            nationality_country_name=parsed_l2.nationality_country_name.upper(),
            nuip=parsed_l2.nuip,
            first_names=parsed_l3.first_names,
            last_names=parsed_l3.last_names,
            is_truncated=parsed_l3.is_truncated,
            doc_type=parsed_l1.doc_type,
            country_code=parsed_l1.country_code,
            country_name=parsed_l1.country_name.upper(),
            doc_number=parsed_l1.doc_number,
            doc_number_check_digit=parsed_l1.doc_number_check_digit,
            mun_code=parsed_l1.mun_code,
            mun_name=parsed_l1.mun_name,
            dep_code=parsed_l1.dep_code,
            dep_name=parsed_l1.dep_name,
            errors=parsed_l1.errors + parsed_l2.errors,
        )
        metadata = DocumentMetadata(
            lines=[l1, l2, l3],
            confidence=min(parsed_l1.confidence, parsed_l2.confidence),
        )
        return Document(fields=fields, metadata=metadata)

    @classmethod
    def _parse_mrz_l1(cls, l1: str) -> _MRZL1:
        errors: List[Exception] = []
        confidence = 100
        doc_type = l1[0].upper()
        if doc_type in ['L', 'l', "1", "|"]:
            doc_type = 'I'
        if doc_type not in ['A', 'C', 'I']:
            errors.append(Exception('Invalid MRZ format: Invalid document type'))
        if l1[1] in ['C', '<']:
            confidence += 10.0
        raw_country = l1[2:5]
        c = countries.get(raw_country.upper().replace("0", "O"))
        if c is None:
            confidence -= 10.0
            errors.append(Exception('Invalid MRZ format: Invalid country'))
        country_name = c.name
        country_code = c.alpha3

        doc_number = l1[5:14].lstrip('0')
        if not doc_number.isnumeric():
            confidence -= 30.0
            errors.append(Exception('Invalid MRZ format: Invalid document number is not numeric'))
        if len(doc_number) > len(doc_number) and l1[5] == '0':
            confidence += 10.0
        doc_number_check_digit = l1[14]
        if not doc_number_check_digit.isnumeric():
            confidence -= 10.0
            errors.append(Exception('Invalid MRZ format: Invalid document number check digit is not numeric'))
        calculated_check_digit = cls._calculate_check_digit(doc_number)
        if doc_number_check_digit != calculated_check_digit:
            confidence -= 10.0
            errors.append(Exception(f'Invalid MRZ format: Invalid document number check digit {doc_number_check_digit} '
                                    f'expected {calculated_check_digit}'))
        mun_code = l1[15:17]
        dep_code = l1[17:20]
        is_valid_location = True
        if not mun_code.isnumeric():
            confidence -= 10.0
            errors.append(Exception('Invalid MRZ format: Invalid municipality is not numeric'))
            is_valid_location = False
        if not dep_code.isnumeric():
            errors.append(Exception('Invalid MRZ format: Invalid department is not numeric'))
            is_valid_location = False
        mun_name = ''
        dep_name = ''
        if is_valid_location:
            for loc in LOCALITIES:
                if loc[0] == mun_code and loc[1] == dep_code:
                    mun_name = loc[2]
                    dep_name = loc[3]
                    break
        if mun_name == '':
            confidence -= 10.0
            raise Exception('Invalid MRZ format: Invalid municipality and department')
        return _MRZL1(
            doc_type=doc_type,
            country_code=country_code,
            country_name=country_name,
            doc_number=doc_number,
            doc_number_check_digit=doc_number_check_digit,
            mun_code=mun_code,
            mun_name=mun_name,
            dep_code=dep_code,
            dep_name=dep_name,
            confidence=confidence,
            errors=errors,
        )

    @classmethod
    def _parse_mrz_l2(cls, l2: str) -> _MRZL2:
        errors: List[Exception] = []
        confidence = 100.0
        bird_date = None
        try:
            bird_date = cls._parse_date(l2[0:6], l2[6], True, 'bird_date')
        except Exception as e:
            confidence -= 10.0
            errors.append(e)
        sex_str = l2[7]
        sex = Sex.parse(sex_str)
        expiration_date_str = l2[8:14]
        expiration_date = None
        try:
            validator_digit = l2[14]
            expiration_date = cls._parse_date(expiration_date_str, validator_digit, False, 'expiration_date')
        except Exception as e:
            confidence -= 10.0
            errors.append(e)
        expiration_date_check_digit = l2[14]
        if not expiration_date_check_digit.isnumeric():
            confidence -= 10.0
            errors.append(Exception('Invalid MRZ format: Invalid expiration date check digit is not numeric'))
        calculated_check_digit = cls._calculate_check_digit(expiration_date_str)
        if expiration_date_check_digit != calculated_check_digit:
            confidence -= 10.0
            errors.append(
                Exception(f'Invalid MRZ format: Invalid expiration date check digit {expiration_date_check_digit} '
                          f'expected {calculated_check_digit}'))
        nationality_str = l2[15:18].replace("0", "O")
        c = countries.get(nationality_str.upper())
        if c is None:
            confidence -= 10.0
            errors.append(Exception(f'Invalid MRZ format: Invalid nationality {nationality_str}'))
        nationality_name = c.name
        nationality_code = c.alpha3
        nuip = l2[18:28].lstrip('0')
        if not nuip.isnumeric():
            confidence -= 30.0
            errors.append(Exception(f'Invalid MRZ format: Invalid nuip is not numeric: {nuip}'))
        return _MRZL2(
            bird_date=bird_date,
            sex=sex,
            expiration_date=expiration_date,
            nationality_country_code=nationality_code,
            nationality_country_name=nationality_name,
            nuip=nuip,
            confidence=confidence,
            errors=errors,
        )

    @staticmethod
    def _parse_mrz_l3(l2: str) -> _MRZL3:
        l2 = l2.rstrip('<')
        names = l2.split('<<')
        last_names = names[0].replace('<', ' ')
        is_truncated = False
        if len(names) < 2:
            is_truncated = True
        first_names = names[1].replace('<', ' ')
        return _MRZL3(
            last_names=last_names,
            first_names=first_names,
            is_truncated=is_truncated,
        )
