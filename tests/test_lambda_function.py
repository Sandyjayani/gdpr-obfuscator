import os
from moto import mock_aws
import boto3
from lambda_function.lambda_function import lambda_handler


@mock_aws
def test_lambda_handler_success():
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,email_address'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
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

        # Check the processed content - decode bytes to string if needed
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')

        # Normalize line endings for comparison
        result = result.replace('\r\n', '\n')

        expected = (
            "student_id,name,course,cohort,graduation_date,email_address\n"
            "1234,***,Software,2024,2024-03-31,***\n"
            "5678,***,Data,2024,2024-06-30,***\n"
        )
        assert result == expected
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_invalid_event():
    # For invalid event test, we need to check for "Invalid event structure"
    # First, set PII_FIELDS to avoid that error
    os.environ['PII_FIELDS'] = 'name,email_address'

    try:
        event = {}  # Empty event
        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        assert "Invalid event structure" in response["body"]
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_missing_file():
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,email_address'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
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
        assert "File not found" in result["body"]
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_custom_pii_fields():
    """Test using custom PII fields from environment variables"""
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,course'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
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

        # Check the processed content
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        result = result.replace('\r\n', '\n')

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
def test_lambda_handler_direct_invocation():
    """Test direct invocation with file_to_obfuscate parameter"""
    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='custom_folder/data.csv', Body=csv_content)

        # Create test event for direct invocation with pii_fields in the event
        event = {
            "file_to_obfuscate": f"s3://{bucket_name}/custom_folder/data.csv",
            "pii_fields": ["name"]
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200

        # Check the processed content
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        result = result.replace('\r\n', '\n')

        expected = (
            "student_id,name,email_address\n"
            "1234,***,john@example.com\n"
        )
        assert result == expected
    finally:
        pass


@mock_aws
def test_lambda_handler_with_output_path():
    """Test direct invocation with output path"""
    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        input_bucket = 'input-bucket'
        output_bucket = 'output-bucket'
        s3_client.create_bucket(Bucket=input_bucket)
        s3_client.create_bucket(Bucket=output_bucket)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=input_bucket, Key='data.csv', Body=csv_content)

        # Create test event for direct invocation with output path
        event = {
            "file_to_obfuscate": f"s3://{input_bucket}/data.csv",
            "pii_fields": ["name", "email_address"],
            "output_path": f"s3://{output_bucket}/obfuscated.csv"
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200

        # Check the processed content
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')

        expected = (
            "student_id,name,email_address\n"
            "1234,***,***\n"
        ).replace('\r\n', '\n')

        assert result.replace('\r\n', '\n') == expected
    finally:
        pass


@mock_aws
def test_lambda_handler_missing_pii_fields():
    """Test error handling when PII fields are missing"""
    # Don't set environment variable for PII fields

    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV
    csv_content = (
        b"student_id,name,email_address\n"
        b"1234,John Doe,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

    # Create test event
    event = {
        "Records": [
            {
                "s3": {
                    "bucket": {"name": bucket_name},
                    "object": {"key": "data.csv"}
                }
            }
        ]
    }

    # Call lambda handler
    response = lambda_handler(event, None)

    assert response["statusCode"] == 400
    assert "PII_FIELDS environment variable must be set" in response["body"]

# ... rest of code remains same


@mock_aws
def test_lambda_handler_invalid_pii_fields_in_event():
    """Test error handling when PII fields in event are invalid"""
    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

        # Create test event with empty pii_fields list
        event = {
            "file_to_obfuscate": f"s3://{bucket_name}/data.csv",
            "pii_fields": []  # Empty list
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        assert "PII fields must be a non-empty list" in response["body"]

        # Test with non-list pii_fields
        event = {
            "file_to_obfuscate": f"s3://{bucket_name}/data.csv",
            "pii_fields": "name,email"  # String instead of list
        }

        response = lambda_handler(event, None)
        assert response["statusCode"] == 400
        assert "PII fields must be a non-empty list" in response["body"]
    finally:
        pass


@mock_aws
def test_lambda_handler_empty_pii_fields_env_var():
    """Test error handling when PII_FIELDS environment variable is empty"""
    try:
        # Set empty PII_FIELDS environment variable
        os.environ['PII_FIELDS'] = ''

        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

        # Create test event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket_name},
                        "object": {"key": "data.csv"}
                    }
                }
            ]
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 400
        assert "PII_FIELDS environment variable must be set" in response["body"]
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_s3_event_with_output_path():
    """Test S3 event trigger with output path specified"""
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,email_address'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        input_bucket = 'input-bucket'
        output_bucket = 'output-bucket'
        s3_client.create_bucket(Bucket=input_bucket)
        s3_client.create_bucket(Bucket=output_bucket)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=input_bucket, Key='data.csv', Body=csv_content)

        # Create test event with S3 trigger and output path
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": input_bucket},
                        "object": {"key": "data.csv"}
                    }
                }
            ],
            "output_path": f"s3://{output_bucket}/obfuscated.csv"
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200

        # Check the processed content
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')

        expected = (
            "student_id,name,email_address\n"
            "1234,***,***\n"
        ).replace('\r\n', '\n')

        assert result.replace('\r\n', '\n') == expected
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_validation_error():
    """Test handling of validation errors during obfuscation"""
    # This test simulates a validation error in the obfuscate_pii function
    # by providing a field that doesn't exist in the CSV

    # Set environment variable for PII fields with a non-existent column
    os.environ['PII_FIELDS'] = 'non_existent_field'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,email_address\n"
            b"1234,John Doe,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

        # Create test event
        event = {
            "Records": [
                {
                    "s3": {
                        "bucket": {"name": bucket_name},
                        "object": {"key": "data.csv"}
                    }
                }
            ]
        }

        # Call lambda handler
        # The exact response depends on how obfuscate_pii handles missing fields,
        # but we expect a 400 status code for validation errors
        response = lambda_handler(event, None)

        # Assert that we get an error status code
        assert response["statusCode"] in [400, 500]
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']


@mock_aws
def test_lambda_handler_event_pii_fields_override_env():
    """Test that PII fields in event override environment variables"""
    # Set environment variable for PII fields
    os.environ['PII_FIELDS'] = 'name,email_address'

    try:
        # Set up mock S3
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'my_ingestion_bucket'
        s3_client.create_bucket(Bucket=bucket_name)

        # Create sample CSV
        csv_content = (
            b"student_id,name,course,email_address\n"
            b"1234,John Doe,Python,john@example.com\n"
        )
        s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

        # Create test event with pii_fields that override environment variables
        event = {
            "file_to_obfuscate": f"s3://{bucket_name}/data.csv",
            "pii_fields": ["course"]  # Only obfuscate course, not name or email
        }

        # Call lambda handler
        response = lambda_handler(event, None)

        assert response["statusCode"] == 200

        # Check the processed content
        result = response["body"]
        if isinstance(result, bytes):
            result = result.decode('utf-8')
        result = result.replace('\r\n', '\n')

        # Only course should be obfuscated, name and email should remain intact
        expected = (
            "student_id,name,course,email_address\n"
            "1234,John Doe,***,john@example.com\n"
        )
        assert result == expected
    finally:
        # Clean up environment variable
        if 'PII_FIELDS' in os.environ:
            del os.environ['PII_FIELDS']
