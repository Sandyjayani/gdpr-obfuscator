import json
import boto3
import csv
from io import StringIO


def obfuscate_pii(input_json: str) -> bytes:
    """
    Obfuscates personally identifiable information (PII) in a CSV file stored in S3.

    Args:
        input_json: A JSON string containing:
            - "file_to_obfuscate": S3 path to the CSV file (e.g., "s3://bucket/key.csv")
            - "pii_fields": List of column names to obfuscate.

    Returns:
        bytes: The obfuscated CSV content as a byte-stream, compatible with boto3 S3 PutObject.

    Raises:
        ValueError: If the input JSON is invalid, missing required keys, or if S3/CSV processing
        fails.
    """
    # Parse input JSON
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON input")

    if 'file_to_obfuscate' not in input_data or 'pii_fields' not in input_data:
        raise ValueError("Missing required keys in input JSON")

    s3_path = input_data['file_to_obfuscate']
    pii_fields = input_data['pii_fields']

    if not isinstance(pii_fields, list):
        raise ValueError("pii_fields must be a list")
    if not s3_path.startswith("s3://"):
        raise ValueError("Invalid S3 path")

    # Extract bucket and key from S3 path
    bucket, key = s3_path[5:].split("/", 1)
    s3_client = boto3.client('s3')

    # Download CSV from S3
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
    except s3_client.exceptions.NoSuchKey:
        raise ValueError("S3 file not found")
    except s3_client.exceptions.ClientError as e:
        raise ValueError(f"S3 client error: {e}")

    # Process CSV
    csv_file = StringIO(csv_content)
    reader = csv.DictReader(csv_file)

    # Validate PII fields exist in CSV headers
    if not reader.fieldnames:
        raise ValueError("CSV file has no headers")
    for field in pii_fields:
        if field not in reader.fieldnames:
            raise ValueError(f"PII field '{field}' not found in CSV headers")

    # Process rows
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()

    for row in reader:
        for field in pii_fields:
            row[field] = '***'
        writer.writerow(row)

    return output.getvalue().encode('utf-8')
