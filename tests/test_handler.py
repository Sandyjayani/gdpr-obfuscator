import pytest
import json
import boto3
from moto import mock_s3
from src.lambda_handler import lambda_handler
import os

class TestLambdaHandler:
    @pytest.fixture
    def sample_data_path(self):
        return os.path.join(os.path.dirname(__file__), 'sample_data')

    @mock_s3
    def test_lambda_handler_success(self, sample_data_path):
        # Set up mock S3
        s3 = boto3.client('s3')
        bucket_name = 'my_ingestion_bucket'
        file_key = 'new_data/file1.csv'

        # Read sample data
        with open(os.path.join(sample_data_path, 'sample.csv'), 'r') as f:
            csv_content = f.read()

        # Create mock bucket and file
        s3.create_bucket(Bucket=bucket_name)
        s3.put_object(Bucket=bucket_name, Key=file_key, Body=csv_content)

        # Test event
        event = {
            "file_to_obfuscate": f"s3://{bucket_name}/{file_key}",
            "pii_fields": ["name", "email_address"]
        }

        response = lambda_handler(event, None)

        assert response['statusCode'] == 200
        assert 'body' in response

        body = json.loads(response['body'])
        assert '***' in body['processed_data']

    def test_lambda_handler_invalid_input(self):
        event = {
            "file_to_obfuscate": "invalid_path",
            "pii_fields": ["name"]
        }

        response = lambda_handler(event, None)
        assert response['statusCode'] == 400
