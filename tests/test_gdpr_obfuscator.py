import pytest
from moto import mock_aws
import boto3
import json
from src.gdpr_obfuscator import obfuscate_pii


@mock_aws
def test_obfuscate_pii_success():
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create sample CSV directly with LF line endings
    csv_content = (
        b"student_id,name,course,cohort,graduation_date,email_address\n"
        b"1234,John Doe,Software,2024,2024-03-31,john@example.com\n"
        b"5678,Jane Smith,Data,2024,2024-06-30,jane@example.com"
    )
    s3_client.put_object(Bucket=bucket_name, Key='new_data/file1.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/file1.csv",
        "pii_fields": ["name", "email_address"]
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = (
        "student_id,name,course,cohort,graduation_date,email_address\n"
        "1234,***,Software,2024,2024-03-31,***\n"
        "5678,***,Data,2024,2024-06-30,***\n"
    )
    assert result_str == expected


@mock_aws
def test_obfuscate_pii_single_column():
    """Test obfuscating only one column"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = (
        b"student_id,name,email_address\n"
        b"1234,John Doe,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/data.csv",
        "pii_fields": ["name"]  # Only obfuscate name
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = (
        "student_id,name,email_address\n"
        "1234,***,john@example.com\n"
    )
    assert result_str == expected


@mock_aws
def test_obfuscate_pii_empty_csv():
    """Test handling of CSV with only headers"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = b"student_id,name,email_address\n"
    s3_client.put_object(Bucket=bucket_name, Key='empty.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/empty.csv",
        "pii_fields": ["name", "email_address"]
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = "student_id,name,email_address\n"
    assert result_str == expected


@mock_aws
def test_obfuscate_pii_invalid_csv_no_headers():
    """Test handling of CSV without headers"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Create an empty CSV file
    csv_content = b""
    s3_client.put_object(Bucket=bucket_name, Key='new_data/invalid.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/new_data/invalid.csv",
        "pii_fields": ["name", "email_address"]
    })

    with pytest.raises(ValueError, match="CSV file has no headers"):
        obfuscate_pii(input_json)


@mock_aws
def test_obfuscate_pii_invalid_json():
    """Test handling of invalid JSON input"""
    with pytest.raises(ValueError, match="Invalid JSON input"):
        obfuscate_pii("not a json string")


@mock_aws
def test_obfuscate_pii_missing_required_fields():
    """Test handling of JSON missing required fields"""
    input_json = json.dumps({"invalid_key": "value"})
    with pytest.raises(ValueError, match="Missing required keys in input JSON"):
        obfuscate_pii(input_json)


@mock_aws
def test_obfuscate_pii_invalid_s3_path():
    """Test handling of invalid S3 path"""
    input_json = json.dumps({
        "file_to_obfuscate": "invalid_path",
        "pii_fields": ["name"]
    })
    with pytest.raises(ValueError, match="Invalid S3 path"):
        obfuscate_pii(input_json)


@mock_aws
def test_obfuscate_pii_invalid_pii_fields_type():
    """Test handling of invalid PII fields type"""
    input_json = json.dumps({
        "file_to_obfuscate": "s3://bucket/file.csv",
        "pii_fields": "not_a_list"
    })
    with pytest.raises(ValueError, match="pii_fields must be a list"):
        obfuscate_pii(input_json)


@mock_aws
def test_obfuscate_pii_missing_pii_field():
    """Test handling of non-existent PII field in CSV"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = (
        b"student_id,name,email_address\n"
        b"1234,John Doe,john@example.com\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='data.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/data.csv",
        "pii_fields": ["non_existent_field"]
    })

    with pytest.raises(ValueError, match="PII field 'non_existent_field' not found in CSV headers"):
        obfuscate_pii(input_json)


@mock_aws
def test_obfuscate_pii_special_characters():
    """Test handling of special characters in CSV"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = (
        b"student_id,name,notes\n"
        b'1234,"Doe, John","""Quoted"" and, comma"\n'
    )
    s3_client.put_object(Bucket=bucket_name, Key='special.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/special.csv",
        "pii_fields": ["name"]
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = (
        'student_id,name,notes\n'
        '1234,***,"""Quoted"" and, comma"\n'
    )
    assert result_str == expected


@mock_aws
def test_obfuscate_pii_multiple_rows():
    """Test handling of multiple rows with various data"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = (
        b"id,name,email,notes\n"
        b"1,John Doe,john@example.com,note1\n"
        b"2,Jane Smith,jane@example.com,note2\n"
        b"3,Bob Wilson,bob@example.com,note3\n"
    )
    s3_client.put_object(Bucket=bucket_name, Key='multi.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/multi.csv",
        "pii_fields": ["name", "email"]
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = (
        "id,name,email,notes\n"
        "1,***,***,note1\n"
        "2,***,***,note2\n"
        "3,***,***,note3\n"
    )
    assert result_str == expected


@mock_aws
def test_obfuscate_pii_unicode_characters():
    """Test handling of Unicode characters in CSV"""
    s3_client = boto3.client('s3')
    bucket_name = 'my_ingestion_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    csv_content = (
        "id,name,email\n"
        "1,José García,jose@example.com\n"
        "2,María Rodríguez,maria@example.com\n"
    ).encode('utf-8')

    s3_client.put_object(Bucket=bucket_name, Key='unicode.csv', Body=csv_content)

    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/unicode.csv",
        "pii_fields": ["name", "email"]
    })

    result = obfuscate_pii(input_json)
    result_str = result.decode('utf-8').replace('\r\n', '\n')

    expected = (
        "id,name,email\n"
        "1,***,***\n"
        "2,***,***\n"
    )
    assert result_str == expected
