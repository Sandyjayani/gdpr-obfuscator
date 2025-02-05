import json
import boto3
import io
from urllib.parse import urlparse
from .obfuscator import GDPRObfuscator
import logging

logger = logging.getLogger(__name__)

def lambda_handler(event: dict, context) -> dict:
    """
    AWS Lambda handler for GDPR obfuscation.

    Args:
        event: Dict containing file_to_obfuscate and pii_fields
        context: AWS Lambda context

    Returns:
        Dict with statusCode and body
    """
    try:
        logger.info("Processing Lambda event")

        # Validate input
        if not event.get('file_to_obfuscate') or not event.get('pii_fields'):
            raise ValueError("Missing required parameters")

        # Parse S3 location
        s3_path = event['file_to_obfuscate']
        parsed_path = urlparse(s3_path)
        bucket = parsed_path.netloc
        key = parsed_path.path.lstrip('/')

        # Get file from S3
        s3 = boto3.client('s3')
        response = s3.get_object(Bucket=bucket, Key=key)
        csv_data = io.StringIO(response['Body'].read().decode('utf-8'))

        # Obfuscate data
        obfuscator = GDPRObfuscator()
        result = obfuscator.obfuscate_csv(csv_data, event['pii_fields'])

        logger.info("Successfully processed file")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'processed_data': result.decode('utf-8')
            })
        }

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': str(e)
            })
        }
