import pytest
import os
import sys
import tempfile
from unittest.mock import patch
# Remove unused imports
from moto import mock_aws
import cli


@mock_aws
def test_process_local_file():
    """Test processing a local file"""
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
def test_process_local_file_stdout():
    """Test processing a local file with output to stdout"""
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

            # Check that write was called with binary data
            mock_write.assert_called_once()
            # Get the binary data that was written
            binary_data = mock_write.call_args[0][0]
            # Convert to string for assertion
            result = binary_data.decode('utf-8').replace('\r\n', '\n')
            assert "id,name" in result
            assert "1,***" in result
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


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


@mock_aws
def test_process_local_file_error_handling():
    """Test error handling in process_local_file"""
    # Test with non-existent file
    with pytest.raises(SystemExit) as excinfo:
        cli.process_local_file(
            local_file='non_existent_file.csv',
            pii_fields=['name'],
            output_file=None
        )
    assert excinfo.value.code == 1  # Check that the exit code is 1
