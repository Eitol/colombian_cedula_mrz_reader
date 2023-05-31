import uuid
from abc import abstractmethod, ABC

from parser.mrz_parser import Document, MRZParser
from scanner.analyzer import DocumentAnalyzer


class TextractClient(ABC):
    @abstractmethod
    def analyze_id(self, file_name, bucket_name):
        pass


class Boto3TextractClient(TextractClient):

    def __init__(self, textract_client):
        self._client = textract_client

    def analyze_id(self, file_name, bucket_name) -> dict:
        return self._client.analyze_id(
            DocumentPages=[{'S3Object': {'Bucket': bucket_name, 'Name': file_name}}],
        )


class S3Client(ABC):
    @abstractmethod
    def put_object(self, bucket, key, body):
        pass


class Boto3S3Client(S3Client):

    def __init__(self, s3_client):
        self._client = s3_client

    def put_object(self, bucket: str, key: str, body: str):
        self._client.put_object(Bucket=bucket, Key=key, Body=body)


class TextractColCedulaMRZAnalyzer(DocumentAnalyzer):
    def __init__(self, textract_client: TextractClient, s3_client: S3Client, bucket_name: str, mrz_parser: MRZParser):
        self._textract_client = textract_client
        self._s3_client = s3_client
        self._bucket_name = bucket_name
        self._mrz_parser = mrz_parser

    def analyze_document_id(self, file: bytes) -> Document:
        file_name = self._upload_to_s3(file)
        mrz_text = self._analyze_using_textract(file_name)
        return self._mrz_parser.parse(mrz_text)

    def _upload_to_s3(self, file: bytes) -> str:
        random_file_name = str(uuid.uuid4())
        self._s3_client.put_object(self._bucket_name, random_file_name, file)
        return random_file_name

    def _analyze_using_textract(self, file_name) -> str:
        response = self._textract_client.analyze_id(file_name, self._bucket_name)
        return self._extract_mrz_text_from_response(response)

    @staticmethod
    def _extract_mrz_text_from_response(response) -> str:
        if 'IdentityDocuments' not in response or len(response['IdentityDocuments']) <= 0:
            raise Exception('No document detected')
        confidence = 0.0
        doc = response['IdentityDocuments'][0]
        if 'Blocks' not in doc or len(doc['Blocks']) <= 0:
            raise Exception('No document detected')
        mrz_line_1 = ''
        mrz_line_2 = ''
        mrz_line_3 = ''
        for i in range(0, len(doc['Blocks'])):
            b = doc['Blocks'][i]
            if 'BlockType' not in b or 'Text' not in b:
                continue
            block_type = b['BlockType']
            content: str = b['Text'].strip().replace(' ', '')
            if block_type == 'LINE':
                if content == '.CO':
                    confidence += 10.0
                if content == 'REGISTRADOR NACIONAL':
                    confidence += 10.0
                if content.startswith('ICCOL'):
                    confidence += 10.0
                    if len(doc['Blocks']) >= i + 2:
                        mrz_line_1 = doc['Blocks'][i]['Text']
                        mrz_line_2 = doc['Blocks'][i + 1]['Text']
                        mrz_line_3 = doc['Blocks'][i + 2]['Text']
        if len(mrz_line_1) == 0 or len(mrz_line_2) == 0 or len(mrz_line_3) == 0:
            raise Exception('No document detected')
        return f"{mrz_line_1}\n{mrz_line_2}\n{mrz_line_3}"
