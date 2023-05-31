from abc import ABC, abstractmethod

from domain.model import Document


class DocumentAnalyzer(ABC):

    @abstractmethod
    def analyze_document_id(self, file: bytes) -> Document:
        pass
