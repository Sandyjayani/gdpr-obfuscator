import time
import json
import boto3
import random
import string
from moto import mock_aws
from src.gdpr_obfuscator import obfuscate_pii
import os
import psutil
import gc


def generate_test_csv(rows, columns=5, pii_columns=2):
    """Generate a test CSV with specified number of rows and columns"""
    header = ['id'] + [f'col{i}' for i in range(1, columns)]

    # Identify which columns will contain PII
    pii_column_indices = random.sample(range(1, columns), pii_columns)
    pii_column_names = [f'col{i}' for i in pii_column_indices]

    # Generate CSV content
    csv_content = [','.join(header)]
    for i in range(rows):
        row = [str(i)]
        for j in range(1, columns):
            # Generate random data (10-20 chars)
            length = random.randint(10, 20)
            data = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
            row.append(data)
        csv_content.append(','.join(row))

    return '\n'.join(csv_content), pii_column_names


@mock_aws
def test_performance_small_file():
    """Test performance with a small file (100 rows)"""
    # Generate test data
    csv_content, pii_columns = generate_test_csv(rows=100, columns=10, pii_columns=3)

    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'performance_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Upload test file to mock S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key='test_small.csv',
        Body=csv_content.encode('utf-8')
    )

    # Prepare input
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/test_small.csv",
        "pii_fields": pii_columns
    })

    # Measure performance
    start_time = time.time()
    result = obfuscate_pii(input_json)
    end_time = time.time()

    # Verify result
    assert isinstance(result, bytes)

    # Performance should be under 1 second for small file
    assert end_time - start_time < 1.0, f"Processing took {end_time - start_time:.2f} seconds"


@mock_aws
def test_performance_medium_file():
    """Test performance with a medium file (1000 rows)"""
    # Generate test data
    csv_content, pii_columns = generate_test_csv(rows=1000, columns=15, pii_columns=5)

    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'performance_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Upload test file to mock S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key='test_medium.csv',
        Body=csv_content.encode('utf-8')
    )

    # Prepare input
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/test_medium.csv",
        "pii_fields": pii_columns
    })

    # Measure performance
    start_time = time.time()
    result = obfuscate_pii(input_json)
    end_time = time.time()

    # Verify result
    assert isinstance(result, bytes)

    # Performance should be under 5 seconds for medium file
    assert end_time - start_time < 5.0, f"Processing took {end_time - start_time:.2f} seconds"


@mock_aws
def test_memory_usage():
    """Test memory usage during processing"""
    # Generate test data (larger file to test memory usage)
    csv_content, pii_columns = generate_test_csv(rows=5000, columns=20, pii_columns=8)

    # Set up mock S3
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = 'performance_test_bucket'
    s3_client.create_bucket(Bucket=bucket_name)

    # Upload test file to mock S3
    s3_client.put_object(
        Bucket=bucket_name,
        Key='test_large.csv',
        Body=csv_content.encode('utf-8')
    )

    # Prepare input
    input_json = json.dumps({
        "file_to_obfuscate": f"s3://{bucket_name}/test_large.csv",
        "pii_fields": pii_columns
    })

    # Force garbage collection before measuring
    gc.collect()

    # Get memory usage before
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB

    # Process the file
    result = obfuscate_pii(input_json)

    # Force garbage collection after processing
    gc.collect()

    # Get memory usage after
    memory_after = process.memory_info().rss / 1024 / 1024  # MB

    # Verify result
    assert isinstance(result, bytes)

    # Calculate memory increase
    memory_increase = memory_after - memory_before

    # Memory increase should be reasonable (less than 100MB for this test)
    # This is a flexible threshold and may need adjustment based on implementation
    assert memory_increase < 100, f"Memory usage increased by {memory_increase:.2f} MB"

    # Log memory usage for information
    print(f"Memory before: {memory_before:.2f} MB")
    print(f"Memory after: {memory_after:.2f} MB")
    print(f"Memory increase: {memory_increase:.2f} MB")


if __name__ == "__main__":
    # Run tests directly when script is executed
    test_performance_small_file()
    test_performance_medium_file()
    test_memory_usage()
