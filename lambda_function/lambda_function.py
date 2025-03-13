import json
import boto3
import sys
import os
import pathlib
import logging
from src.gdpr_obfuscator import obfuscate_pii

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('lambda_function')

# Add the project root to Python path so we can import the src module
root_dir = str(pathlib.Path(__file__).parent.parent)
sys.path.append(root_dir)


def lambda_handler(event, context):
    """
    AWS Lambda handler for processing CSV files from S3 and obfuscating PII data.

    Args:
        event: AWS Lambda event containing S3 bucket and key information
        context: AWS Lambda context

    Returns:
        dict: Response containing statusCode and message
    """
    logger.info("Lambda function invoked")
    try:
        # Get PII fields from environment variables or use defaults
        pii_fields = os.environ.get('PII_FIELDS', 'name,email_address').split(',')
        logger.info(f"Using PII fields: {pii_fields}")

        # Handle direct invocation
        if 'file_to_obfuscate' in event:
            input_json = json.dumps({
                'file_to_obfuscate': event['file_to_obfuscate'],
                'pii_fields': pii_fields
            })
        # Handle S3 event
        elif 'Records' in event and event['Records']:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            logger.info(f"Processing file: bucket={bucket}, key={key}")
            input_json = json.dumps({
                'file_to_obfuscate': f's3://{bucket}/{key}',
                'pii_fields': pii_fields
            })
        else:
            logger.error("Invalid event structure")
            return {
                'statusCode': 400,
                'body': 'Invalid event structure'
            }

        # Process the file
        try:
            result = obfuscate_pii(input_json)
            return {
                'statusCode': 200,
                'body': result
            }
        except ValueError as e:
            if "S3 file not found" in str(e):
                logger.error(f"File not found")
                return {
                    'statusCode': 404,
                    'body': 'File not found'
                }
            logger.error(f"Validation error: {str(e)}")
            return {
                'statusCode': 400,
                'body': str(e)
            }

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error processing file: {str(e)}'
        }
