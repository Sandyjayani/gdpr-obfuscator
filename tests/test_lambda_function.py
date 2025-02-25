import os
from moto import mock_aws
import boto3
from lambda_function.lambda_function import lambda_handler


@mock_aws
def test_lambda_handler_success():
    # Set up mock S3
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV
    csv_content = (
        b"student_id,name,course,cohort,graduation_date,email_address\n"
        b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
        b"5678,Jane Smith,Data,2024,2024-06-30,jane@example.com"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/file1.csv', Body=csv_content)

    # Create test event
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": "new_data/file1.csv"}
                }
            }
        ]
    }

    # Call lambda handler
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    assert "Successfully processed" in response["body"]

    # Verify the obfuscated file was created
    response = s3_client.get_object(Bucket=bucket_name, Key='processed_data/file1.csv')
    result = response['Body'].read().decode('utf-8').replace('\r\n', '\n')

    expected = (
        "student_id,name,course,cohort,graduation_date,email_address\n"
        "1234,***,Software,2024,2024-03-31,***\n"
        "5678,***,Data,2024,2024-06-30,***\n"
    )
    assert result == expected


@mock_aws
def test_lambda_handler_invalid_event():
    event = {}  # Empty event
    response = lambda_handler(event, None)
    assert response["statusCode"] == 400
    assert "Invalid event structure" in response["body"]


@mock_aws
def test_lambda_handler_missing_file():
    # Set up mock S3
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create test event with non-existent file
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": "new_data/missing.csv"}
                }
            }
        ]
    }

    # Call lambda handler and assert the response
    result = lambda_handler(event, None)
    assert result["statusCode"] == 404  # Status code for missing file
    assert "Error processing" in result["body"] or "File not found" in result["body"]


@mock_aws
def test_lambda_handler_custom_pii_fields():
    """Test using custom PII fields from environment variables"""
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,course'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,course,cohort,graduation_date,email_address\n"
            b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='new_data/file2.csv', Body=csv_content)

        # Create test event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket_name},
                        "object": {"key": "new_data/file2.csv"}
                    }
                }
            ]
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        assert "Successfully processed" in response["body"]

        # Verify the obfuscated file was created with the right fields masked
        response = s3_client.get_object(Bucket=bucket_name, Key='processed_data/file2.csv')
        result = response['Body'].read().decode('utf-8').replace('\r\n', '\n')

        expected = (
            "student_id,name,course,cohort,graduation_date,email_address\n"
            "1234,***,***,2024,2024-03-31,john@example.com\n"
        )
        assert result == expected
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_non_standard_path():
    """Test processing a file not in the new_data folder"""
    # Set environment variable for PII fields to match our test data
    os.environ['PII_FIELDS'] = 'name'

    # Set up mock S3
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV in a different folder
    csv_content = (
        b"student_id,name,email_address\n"
        b"1234,John Doe,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='custom_folder/data.csv', Body=csv_content)

    # Create test event
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": "custom_folder/data.csv"}
                }
            }
        ]
    }

    try:
        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200
        assert "Successfully processed" in response["body"]

        # Verify the obfuscated file was created in the processed_data folder
        response = s3_client.get_object(Bucket=bucket_name, Key='processed_data/data.csv')
        result = response['Body'].read().decode('utf-8').replace('\r\n', '\n')

        expected = (
            "student_id,name,email_address\n"
            "1234,***,john@example.com\n"
        )
        assert result == expected
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']
