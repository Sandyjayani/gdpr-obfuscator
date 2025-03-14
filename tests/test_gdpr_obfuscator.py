import pytest
from moto import mock_aws
import boto3
import json
from src.gdpr_obfuscator import obfuscate_pii


@mock_aws
def test_obfuscate_pii_success():
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

    # Prepare input JSON
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/file1.csv",
        "pii_fields": ["name", "email_address"]
    })

    # Call the function
    result = obfuscate_pii(input_json)

    # Check the result
    assert isinstance(result, bytes)
    result_str = result.decode('utf-8')
    assert "John Doe" not in result_str
    assert "jane@example.com" not in result_str
    assert "***" in result_str


@mock_aws
def test_obfuscate_pii_missing_file():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Prepare input JSON with non-existent file
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/nonexistent.csv",
        "pii_fields": ["name", "email_address"]
    })

    # Call the function and expect an error
    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii(input_json)
    assert "S3 file not found" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_invalid_json():
    # Test with invalid JSON
    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii("not a json")
    assert "Invalid JSON input" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_missing_keys():
    # Test with missing required keys
    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii('{"some_key": "some_value"}')
    assert "Missing required keys" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_invalid_s3_path():
    # Test with invalid S3 path
    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii('{"file_to_obfuscate": "not-s3-path", "pii_fields": ["name"]}')
    assert "Invalid S3 path" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_path_traversal():
    # Test path traversal detection
    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii('{"file_to_obfuscate": "s3://bucket/../file.csv", "pii_fields": ["name"]}')
    assert "path traversal" in str(excinfo.value).lower()


@mock_aws
def test_obfuscate_pii_invalid_pii_fields():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV
    csv_content = (
        b"student_id,name,course,cohort,graduation_date,email_address\n"
        b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/file1.csv', Body=csv_content)

    # Test with non-existent field
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/file1.csv",
        "pii_fields": ["non_existent_field"]
    })

    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii(input_json)
    assert "not found in CSV headers" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_no_headers():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create an empty CSV file (no headers, no data)
    csv_content = b""
    s3_client.put_object(Bucket=bucket_name, Key='new_data/empty.csv', Body=csv_content)

    # Test with CSV without headers
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/empty.csv",
        "pii_fields": ["name"]
    })

    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii(input_json)
    assert "CSV file has no headers" in str(excinfo.value)


@mock_aws
def test_obfuscate_pii_with_output_location():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    output_bucket = 'my_output_bucket'
    s3_client.create_bucket(Bucket=bucket_name)
    s3_client.create_bucket(Bucket=output_bucket)

    # Create sample CSV
    csv_content = (
        b"student_id,name,course,cohort,graduation_date,email_address\n"
        b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/file1.csv', Body=csv_content)

    # Prepare input JSON with output location
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/file1.csv",
        "pii_fields": ["name", "email_address"],
        "output_location": f"s3://{output_bucket}/processed/file1.csv"
    })

    # Call the function
    result = obfuscate_pii(input_json)

    # Check the result
    assert isinstance(result, bytes)

    # Verify the file was uploaded to the output location
    response = s3_client.get_object(Bucket=output_bucket, Key='processed/file1.csv')
    content = response['Body'].read().decode('utf-8')
    assert "John Doe" not in content
    assert "john@example.com" not in content
    assert "***" in content


@mock_aws
def test_obfuscate_pii_with_invalid_output_location():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV
    csv_content = (
        b"student_id,name,course,cohort,graduation_date,email_address\n"
        b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/file1.csv', Body=csv_content)

    # Prepare input JSON with invalid output location
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/file1.csv",
        "pii_fields": ["name", "email_address"],
        "output_location": "not-s3-path"
    })

    # Call the function - should still work but log a warning
    result = obfuscate_pii(input_json)

    # Check the result
    assert isinstance(result, bytes)
    result_str = result.decode('utf-8')
    assert "John Doe" not in result_str
    assert "john@example.com" not in result_str
    assert "***" in result_str


@mock_aws
def test_obfuscate_pii_field_not_in_headers():
    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create a CSV file with headers that don't include the PII field
    csv_content = (
        b"id,first_name,last_name,email\n"
        b"1234,John,Doe,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/missing_field.csv', Body=csv_content)

    # Test with a PII field that doesn't exist in the headers
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/missing_field.csv",
        "pii_fields": ["name"]  # 'name' is not in the headers
    })

    with pytest.raises(ValueError) as excinfo:
        obfuscate_pii(input_json)
    assert "PII field 'name' not found in CSV headers" in str(excinfo.value)
