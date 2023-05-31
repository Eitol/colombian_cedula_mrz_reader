import datetime
import json
import os
import unittest
from typing import Dict

import boto3

from domain.model import Sex
from parser.colombian_mrz_parser import ColombianMRZParser
from scanner.textract_analyzer import TextractColCedulaMRZAnalyzer, TextractClient, S3Client, Boto3TextractClient, \
    Boto3S3Client


class FakeTextractClient(TextractClient):

    def __init__(self, response: Dict, error: Exception = None):
        super().__init__()
        self._response = response
        self._error = error

    def analyze_id(self, file_name, bucket_name):
        if self._error:
            raise self._error
        return self._response


class FakeS3Client(S3Client):

    def __init__(self, error: Exception = None):
        self._error = error

    def put_object(self, bucket, key, body):
        if self._error:
            raise self._error


class AnalyzerTestCase(unittest.TestCase):

    def test_analizer_with_fake_aws_services(self):
        img_file_name = "data/fake_1.png"
        resp_file_name = "data/fake_1_textract_resp.json"
        with open(resp_file_name, 'rb') as f:
            resp_json = json.load(f)
        textract_client = FakeTextractClient(resp_json)
        s3_client = FakeS3Client()
        a = TextractColCedulaMRZAnalyzer(
            textract_client, s3_client, "bucket_name", ColombianMRZParser()
        )
        with open(img_file_name, 'rb') as f:
            img_file_bytes = f.read()
        doc = a.analyze_document_id(img_file_bytes)
        assert doc is not None
        assert doc.fields.doc_number == "12"
        assert doc.fields.bird_date == datetime.date(2004, 3, 15), doc.fields.bird_date
        assert doc.fields.sex == Sex.FEMALE
        assert doc.fields.expiration_date == datetime.date(2032, 3, 19)
        assert doc.fields.nationality_country_code == "COL"
        assert doc.fields.nationality_country_name == "COLOMBIA"
        assert doc.fields.nuip == "1234567890"
        assert doc.fields.first_names == "LAURA"
        assert doc.fields.last_names == "WALTEROS"
        assert doc.fields.is_truncated is False
        assert doc.fields.mun_code == "05"
        assert doc.fields.mun_name == "BOLIVAR"
        assert doc.fields.dep_code == "001"
        assert doc.fields.dep_name == "CARTAGENA"

    def test_analizer_with_real_aws_services(self):
        aws_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
        if not aws_key_id:
            self.skipTest("AWS_ACCESS_KEY_ID not set")
            return
        img_file_name = "data/fake_1.png"
        bucket_name = "testdocid"
        region_name = os.environ.get('AWS_REGION', 'us-east-1')

        session = boto3.Session()
        _textract_client = session.client('textract', region_name=region_name)
        textract_client = Boto3TextractClient(_textract_client)
        _s3_client = session.client('s3')
        s3_client = Boto3S3Client(_s3_client)
        a = TextractColCedulaMRZAnalyzer(
            textract_client, s3_client, bucket_name, ColombianMRZParser()
        )
        with open(img_file_name, 'rb') as f:
            img_file_bytes = f.read()
        a.analyze_document_id(img_file_bytes)
