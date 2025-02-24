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

    response = lambda_handler(event, None)
    assert response["statusCode"] == 404
    assert "File not found" in response["body"]
