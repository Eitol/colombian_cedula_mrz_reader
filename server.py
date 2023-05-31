from fastapi import FastAPI, File, UploadFile
import os
import boto3

from parser.colombian_mrz_parser import ColombianMRZParser
from scanner.textract_analyzer import Boto3TextractClient, Boto3S3Client, TextractColCedulaMRZAnalyzer


def create_analyzer() -> TextractColCedulaMRZAnalyzer:
    aws_key_id = os.environ.get('AWS_ACCESS_KEY_ID')
    if not aws_key_id:
        raise Exception("AWS_ACCESS_KEY_ID not set")
    bucket_name = os.environ.get('AWS_BUCKET_NAME')
    if not bucket_name:
        raise Exception("AWS_BUCKET_NAME not set")

    region_name = os.environ.get('AWS_REGION_NAME')
    if not region_name:
        raise Exception("AWS_REGION_NAME not set")

    session = boto3.Session()
    _textract_client = session.client('textract', region_name=region_name)
    textract_client = Boto3TextractClient(_textract_client)
    _s3_client = session.client('s3')
    s3_client = Boto3S3Client(_s3_client)
    return TextractColCedulaMRZAnalyzer(
        textract_client, s3_client, bucket_name, ColombianMRZParser()
    )


app = FastAPI()
analyzer = create_analyzer()


@app.post("/analyze")
async def analyze_endpoint(file: UploadFile = File(...)):
    contents = await file.read()
    if len(contents) == 0:
        return {"filename": file.filename, "result": "empty file"}, 400
    if len(contents) > 5 * 1024 * 1024:
        return {"filename": file.filename, "result": "file too big"}, 413
    result = analyzer.analyze_document_id(contents)
    return {"filename": file.filename, "result": result}
