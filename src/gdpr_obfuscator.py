import json
import boto3
import csv
import logging
from io import StringIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('gdpr_obfuscator')


def obfuscate_pii(input_json: str) -> bytes:
    """
    Obfuscates personally identifiable information (PII) in a CSV file stored in S3.

    Args:
        input_json: A JSON string containing:
            - "file_to_obfuscate": S3 path to the CSV file (e.g., "s3://bucket/key.csv")
            - "pii_fields": List of column names to obfuscate.
            - "output_location": Optional S3 path to write results (e.g., "s3://bucket/output.csv")

    Returns:
        bytes: The obfuscated CSV content as a byte-stream, compatible with boto3 S3 PutObject.

    Raises:
        ValueError: If the input JSON is invalid, missing required keys, or if S3/CSV processing
        fails.
    """
    logger.info("Starting PII obfuscation process")
    # Parse input JSON
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError:
        logger.error("Invalid JSON input provided")
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

    # Validate key against path traversal
    if '..' in key or key.startswith('/'):
        raise ValueError("Invalid S3 key: potential path traversal detected")

    # Create S3 client with explicit region
    session = boto3.session.Session()
    region = session.region_name or 'us-east-1'
    s3_client = boto3.client('s3', region_name=region)

    # Get output location if specified
    output_location = input_data.get('output_location', None)

    # Download CSV from S3
    try:
        logger.info(f"Downloading CSV from S3: bucket={bucket}, key={key}")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        csv_content = response['Body'].read().decode('utf-8')
        logger.info(f"Successfully downloaded CSV, size: {len(csv_content)} bytes")
    except s3_client.exceptions.NoSuchKey:
        logger.error(f"S3 file not found: bucket={bucket}, key={key}")
        raise ValueError("S3 file not found")
    except s3_client.exceptions.ClientError as e:
        logger.error(f"S3 client error: {e}")
        raise ValueError(f"S3 client error: {e}")

    # Process CSV
    csv_file = StringIO(csv_content)
    reader = csv.DictReader(csv_file)

    # Validate PII fields exist in CSV headers
    if not reader.fieldnames:
        logger.error("CSV file has no headers")
        raise ValueError("CSV file has no headers")

    logger.info(f"CSV headers: {reader.fieldnames}")

    for field in pii_fields:
        if field not in reader.fieldnames:
            logger.error(f"PII field '{field}' not found in CSV headers")
            raise ValueError(f"PII field '{field}' not found in CSV headers")

    logger.info(f"Obfuscating fields: {pii_fields}")

    # Process rows
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=reader.fieldnames)
    writer.writeheader()

    row_count = 0
    for row in reader:
        for field in pii_fields:
            row[field] = '***'
        writer.writerow(row)
        row_count += 1

    logger.info(f"Processed {row_count} rows")

    result = output.getvalue().encode('utf-8')
    logger.info(f"Obfuscation complete, output size: {len(result)} bytes")

    if output_location and output_location.startswith("s3://"):
        try:
            output_bucket, output_key = output_location[5:].split("/", 1)
            logger.info(f"Writing output to S3: bucket={output_bucket}, key={output_key}")
            s3_client.put_object(
                Bucket=output_bucket,
                Key=output_key,
                Body=result,
                ContentType='text/csv'
            )
            logger.info("Successfully wrote output to S3")
        except s3_client.exceptions.ClientError as e:
            logger.error(f"Failed to write to S3: {e}")

    return result
