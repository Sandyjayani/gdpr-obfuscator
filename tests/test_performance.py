import time
import json
import pytest
import boto3
import random
import string
from moto import mock_aws
from src.gdpr_obfuscator import obfuscate_pii


def generate_large_csv(size_mb=1, num_columns=10, num_pii_columns=2):
    """Generate a large CSV file of approximately the specified size in MB."""
    # Calculate approximate row size and number of rows needed
    row_size_bytes = num_columns * 15  # Assume average 15 bytes per column
    num_rows = int((size_mb * 1024 * 1024) // row_size_bytes)  # Convert to integer

    # Generate column names
    columns = [f"column_{i}" for i in range(num_columns)]
    pii_columns = columns[:num_pii_columns]

    # Generate CSV content
    csv_content = ",".join(columns) + "\n"

    for i in range(num_rows):
        row_values = []
        for j in range(num_columns):
            # Generate random string for each cell
            if j < num_pii_columns:
                # PII columns get longer values
                value = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            else:
                value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            row_values.append(value)

        csv_content += ",".join(row_values) + "\n"

    return csv_content, pii_columns


@mock_aws
def test_performance_1mb_file():
    """Test that a 1MB file can be processed in under 1 minute."""
    # Set up mock S3
    s3_client = boto3.client('s3')
    bucket_name = 'performance_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Generate a ~1MB CSV file
    print("\nGenerating ~1MB test file...")
    csv_content, pii_columns = generate_large_csv(size_mb=1)
    file_size_mb = len(csv_content) / (1024 * 1024)
    print(f"Generated CSV size: {file_size_mb:.2f} MB")

    # Upload to mock S3
    key = 'performance_test.csv'
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_content.encode('utf-8'))

    # Prepare input for obfuscator
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/{key}",
        "pii_fields": pii_columns
    })

    # Measure processing time
    start_time = time.time()
    result = obfuscate_pii(input_json)
    end_time = time.time()

    processing_time = end_time - start_time
    print(f"Processing time: {processing_time:.2f} seconds")

    # Verify result
    assert len(result) > 0, "Result should not be empty"

    # Check processing time is under 1 minute
    assert processing_time < 60, f"Processing took {processing_time:.2f} seconds, which exceeds the 1 minute requirement"

    # Additional verification: check that PII fields were obfuscated
    result_str = result.decode('utf-8')
    result_lines = result_str.strip().split('\n')

    # Check a sample of lines to verify obfuscation
    sample_size = min(10, len(result_lines) - 1)  # -1 for header
    for i in range(1, sample_size + 1):  # Skip header
        line = result_lines[i]
        fields = line.split(',')

        # Verify PII fields are obfuscated
        for col_idx, col_name in enumerate(result_lines[0].split(',')):
            if col_name in pii_columns:
                assert fields[col_idx] == '***', f"PII field {col_name} was not obfuscated"


@mock_aws
def test_performance_with_varying_file_sizes():
    """Test performance with different file sizes to establish a performance profile."""
    sizes_mb = [0.1, 0.5, 1.0]
    results = []

    for size_mb in sizes_mb:
        # Set up mock S3
        s3_client = boto3.client('s3')
        bucket_name = f'performance_test_bucket_{size_mb}'
        s3_client.create_bucket(Bucket=bucket_name)

        # Generate CSV file
        print(f"\nGenerating ~{size_mb}MB test file...")
        csv_content, pii_columns = generate_large_csv(size_mb=size_mb)
        actual_size_mb = len(csv_content) / (1024 * 1024)
        print(f"Generated CSV size: {actual_size_mb:.2f} MB")

        # Upload to mock S3
        key = f'performance_test_{size_mb}mb.csv'
        s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_content.encode('utf-8'))

        # Prepare input for obfuscator
        input_json = json.dumps({
            "file_to_obfuscate": f"s3://{bucket_name}/{key}",
            "pii_fields": pii_columns
        })

        # Measure processing time
        start_time = time.time()
        result = obfuscate_pii(input_json)
        end_time = time.time()

        processing_time = end_time - start_time
        print(f"Processing time for {actual_size_mb:.2f}MB: {processing_time:.2f} seconds")

        # Store results
        results.append({
            'size_mb': actual_size_mb,
            'processing_time': processing_time,
            'throughput_mb_per_sec': actual_size_mb / processing_time
        })

        # Verify result
        assert len(result) > 0, "Result should not be empty"

    # Print performance summary
    print("\nPerformance Summary:")
    print("Size (MB) | Processing Time (s) | Throughput (MB/s)")
    print("---------|---------------------|------------------")
    for r in results:
        print(f"{r['size_mb']:.2f} | {r['processing_time']:.2f} | {r['throughput_mb_per_sec']:.2f}")

    # Verify all processing times are under 1 minute
    for r in results:
        assert r['processing_time'] < 60, f"Processing {r['size_mb']}MB took {r['processing_time']:.2f} seconds, exceeding the 1 minute requirement"


@mock_aws
def test_memory_usage():
    """Test memory usage during processing of a large file."""
    try:
        import psutil
        import os
    except ImportError:
        pytest.skip("psutil not installed, skipping memory usage test")

    # Set up mock S3
    s3_client = boto3.client('s3')
    bucket_name = 'memory_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Generate a ~1MB CSV file
    print("\nGenerating ~1MB test file for memory usage test...")
    csv_content, pii_columns = generate_large_csv(size_mb=1)
    file_size_mb = len(csv_content) / (1024 * 1024)
    print(f"Generated CSV size: {file_size_mb:.2f} MB")

    # Upload to mock S3
    key = 'memory_test.csv'
    s3_client.put_object(Bucket=bucket_name, Key=key, Body=csv_content.encode('utf-8'))

    # Prepare input for obfuscator
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/{key}",
        "pii_fields": pii_columns
    })

    # Get initial memory usage
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / (1024 * 1024)  # MB

    # Process the file
    result = obfuscate_pii(input_json)

    # Get final memory usage
    final_memory = process.memory_info().rss / (1024 * 1024)  # MB
    memory_increase = final_memory - initial_memory

    print(f"Initial memory usage: {initial_memory:.2f} MB")
    print(f"Final memory usage: {final_memory:.2f} MB")
    print(f"Memory increase: {memory_increase:.2f} MB")

    # Verify result
    assert len(result) > 0, "Result should not be empty"

    # Check memory usage is reasonable (less than 10x file size as a conservative estimate)
    assert memory_increase < (file_size_mb * 10), f"Memory increase ({memory_increase:.2f}MB) exceeds 10x file size ({file_size_mb:.2f}MB)"


if __name__ == "__main__":
    # Run tests directly when script is executed
    test_performance_1mb_file()
    test_performance_with_varying_file_sizes()
    try:
        test_memory_usage()
    except ImportError:
        print("psutil not installed, skipping memory usage test")
