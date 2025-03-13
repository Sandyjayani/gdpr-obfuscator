import pytest
import os
import sys
import json
import tempfile
from unittest.mock import patch, Mock
from moto import mock_aws
import cli


@mock_aws
@patch('cli.obfuscate_pii')
def test_process_local_file(mock_obfuscate):
    """Test processing a local file"""
    # Mock successful response from obfuscate_pii
    mock_response = {
        'statusCode': 200,
        'body': "id,name,email\n1,***,***\n2,***,***\n"
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        temp_file.write("id,name,email\n")
        temp_file.write("1,John Doe,john@example.com\n")
        temp_file.write("2,Jane Smith,jane@example.com\n")
        temp_file_path = temp_file.name

    try:
        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as output_file:
            output_path = output_file.name

        # Process the file
        cli.process_local_file(
            local_file=temp_file_path,
            pii_fields=['name', 'email'],
            output_file=output_path
        )

        # Check that obfuscate_pii was called with correct input
        mock_obfuscate.assert_called_once()
        input_json = json.loads(mock_obfuscate.call_args[0][0])
        assert input_json['pii_fields'] == ['name', 'email']
        assert input_json['file_to_obfuscate'].startswith('s3://')

        # Check the output file
        with open(output_path, 'r') as f:
            result = f.read()

        expected = "id,name,email\n1,***,***\n2,***,***\n"
        # Normalize line endings for comparison
        result = result.replace('\r\n', '\n')
        assert result == expected

    finally:
        # Clean up temporary files
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        if os.path.exists(output_path):
            os.unlink(output_path)


@mock_aws
@patch('cli.obfuscate_pii')
def test_process_local_file_stdout(mock_obfuscate):
    """Test processing a local file with output to stdout"""
    # Mock successful response from obfuscate_pii
    mock_response = {
        'statusCode': 200,
        'body': "id,name\n1,***\n"
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    # Create a temporary CSV file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        temp_file.write("id,name\n")
        temp_file.write("1,John Doe\n")
        temp_file_path = temp_file.name

    try:
        # Patch sys.stdout.buffer.write to capture output
        with patch('sys.stdout.buffer.write') as mock_write:
            # Process the file with output to stdout
            cli.process_local_file(
                local_file=temp_file_path,
                pii_fields=['name'],
                output_file=None
            )

            # Check that write was called with correct binary data
            mock_write.assert_called_once()
            binary_data = mock_write.call_args[0][0]
            result = binary_data.decode('utf-8').replace('\r\n', '\n')
            assert result == "id,name\n1,***\n"

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@mock_aws
@patch('cli.obfuscate_pii')
def test_process_local_file_error_handling(mock_obfuscate):
    """Test error handling in process_local_file"""
    # Test with non-existent file
    with pytest.raises(SystemExit) as excinfo:
        cli.process_local_file(
            local_file='non_existent_file.csv',
            pii_fields=['name'],
            output_file=None
        )
    assert excinfo.value.code == 1

    # Test with error response from obfuscator
    mock_response = {
        'statusCode': 400,
        'body': 'Invalid input format'
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        temp_file.write("id,name\n1,John\n")
        temp_file_path = temp_file.name

    try:
        with pytest.raises(SystemExit) as excinfo:
            cli.process_local_file(
                local_file=temp_file_path,
                pii_fields=['name'],
                output_file=None
            )
        assert excinfo.value.code == 1
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

    # Test with invalid JSON response
    mock_obfuscate.return_value = "invalid json"
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as temp_file:
        temp_file.write("id,name\n1,John\n")
        temp_file_path = temp_file.name

    try:
        with pytest.raises(SystemExit) as excinfo:
            cli.process_local_file(
                local_file=temp_file_path,
                pii_fields=['name'],
                output_file=None
            )
        assert excinfo.value.code == 1
    finally:
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@mock_aws
@patch('cli.obfuscate_pii')
def test_process_s3_file(mock_obfuscate):
    """Test processing an S3 file"""
    # Mock successful response
    mock_response = {
        'statusCode': 200,
        'body': "id,name\n1,***\n"
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    # Test with local output file
    with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as output_file:
        output_path = output_file.name

    try:
        cli.process_s3_file(
            s3_path='s3://bucket/test.csv',
            pii_fields=['name'],
            output_file=output_path
        )

        # Check the output file
        with open(output_path, 'r') as f:
            result = f.read()
        assert result == "id,name\n1,***\n"

    finally:
        if os.path.exists(output_path):
            os.unlink(output_path)

    # Test with S3 output path
    with patch('boto3.client') as mock_boto3:
        mock_s3 = Mock()
        mock_boto3.return_value = mock_s3

        cli.process_s3_file(
            s3_path='s3://input-bucket/test.csv',
            pii_fields=['name'],
            output_file='s3://output-bucket/result.csv'
        )

        # Verify S3 upload was called correctly
        mock_s3.put_object.assert_called_once_with(
            Bucket='output-bucket',
            Key='result.csv',
            Body=mock_response['body'].encode('utf-8'),
            ContentType='text/csv'
        )


@mock_aws
@patch('cli.obfuscate_pii')
def test_process_s3_file_error_handling(mock_obfuscate):
    """Test error handling in process_s3_file"""
    # Test with error response
    mock_response = {
        'statusCode': 404,
        'body': 'File not found in S3'
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    with pytest.raises(SystemExit) as excinfo:
        cli.process_s3_file(
            s3_path='s3://bucket/nonexistent.csv',
            pii_fields=['name'],
            output_file=None
        )
    assert excinfo.value.code == 1

    # Test with invalid JSON response
    mock_obfuscate.return_value = "invalid json"

    with pytest.raises(SystemExit) as excinfo:
        cli.process_s3_file(
            s3_path='s3://bucket/test.csv',
            pii_fields=['name'],
            output_file=None
        )
    assert excinfo.value.code == 1

    # Test with S3 upload error
    mock_response = {
        'statusCode': 200,
        'body': "id,name\n1,***\n"
    }
    mock_obfuscate.return_value = json.dumps(mock_response)

    with patch('boto3.client') as mock_boto3:
        mock_s3 = Mock()
        mock_s3.put_object.side_effect = Exception("S3 upload failed")
        mock_boto3.return_value = mock_s3

        with pytest.raises(SystemExit) as excinfo:
            cli.process_s3_file(
                s3_path='s3://bucket/test.csv',
                pii_fields=['name'],
                output_file='s3://output-bucket/result.csv'
            )
        assert excinfo.value.code == 1


@mock_aws
@patch('cli.process_local_file')
@patch('cli.process_s3_file')
def test_main_local_file(mock_process_s3, mock_process_local):
    """Test CLI main function with local file"""
    # Mock sys.argv
    test_args = [
        'cli.py',
        '--local-file', 'test.csv',
        '--pii-fields', 'name', 'email',
        '--output', 'output.csv'
    ]
    with patch.object(sys, 'argv', test_args):
        cli.main()

    # Check that process_local_file was called with correct args
    mock_process_local.assert_called_once()
    args, _ = mock_process_local.call_args
    assert args[0] == 'test.csv'  # local_file
    assert args[1] == ['name', 'email']  # pii_fields
    assert args[2] == 'output.csv'  # output_file

    # Check that process_s3_file was not called
    mock_process_s3.assert_not_called()


@mock_aws
@patch('cli.process_local_file')
@patch('cli.process_s3_file')
def test_main_s3_file(mock_process_s3, mock_process_local):
    """Test CLI main function with S3 file"""
    # Mock sys.argv
    test_args = [
        'cli.py',
        '--s3-path', 's3://bucket/file.csv',
        '--pii-fields', 'name', 'email',
        '--output', 'output.csv'
    ]
    with patch.object(sys, 'argv', test_args):
        cli.main()

    # Check that process_s3_file was called with correct args
    mock_process_s3.assert_called_once()
    args, _ = mock_process_s3.call_args
    assert args[0] == 's3://bucket/file.csv'  # s3_path
    assert args[1] == ['name', 'email']  # pii_fields
    assert args[2] == 'output.csv'  # output_file

    # Check that process_local_file was not called
    mock_process_local.assert_not_called()