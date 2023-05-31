import datetime
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional, List


@dataclass()
class DocumentFields:
    bird_date: Optional[datetime.date]
    sex: str
    expiration_date: Optional[datetime.date]
    nationality_country_code: str
    nationality_country_name: str
    nuip: str

    first_names: str
    last_names: str
    is_truncated: bool

    doc_type: str
    country_code: str
    country_name: str
    doc_number: str
    doc_number_check_digit: str
    mun_code: str
    mun_name: str
    dep_code: str
    dep_name: str

    errors: List[BaseException]


@dataclass()
class DocumentMetadata:
    lines: List[str]
    confidence: float


@dataclass()
class Document:
    fields: DocumentFields
    metadata: DocumentMetadata


class Sex(StrEnum):
    MALE = 'M'
    FEMALE = 'F'
    OTHER = 'O'

    @staticmethod
    def parse(s: str) -> 'Sex':
        if s == 'M':
            return Sex.MALE
        elif s == 'F':
            return Sex.FEMALE
        return Sex.OTHER
