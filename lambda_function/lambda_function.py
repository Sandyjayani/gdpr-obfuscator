import json
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
        # Get PII fields from event or environment variables
        if 'pii_fields' in event:
            pii_fields = event['pii_fields']
            if not isinstance(pii_fields, list) or not pii_fields:
                logger.error("Invalid PII fields in event")
                return {
                    'statusCode': 400,
                    'body': 'PII fields must be a non-empty list'
                }
        else:
            pii_fields = os.environ.get('PII_FIELDS')
            if not pii_fields:
                logger.error("PII_FIELDS environment variable not set")
                return {
                    'statusCode': 400,
                    'body': 'PII_FIELDS environment variable must be set'
                }
            pii_fields = pii_fields.split(',')
            if not pii_fields:
                logger.error("PII_FIELDS cannot be empty")
                return {
                    'statusCode': 400,
                    'body': 'PII_FIELDS cannot be empty'
                }

        logger.info(f"Using PII fields: {pii_fields}")

        # Handle direct invocation
        if 'file_to_obfuscate' in event:
            input_data = {
                'file_to_obfuscate': event['file_to_obfuscate'],
                'pii_fields': pii_fields
            }

            # Add output_path if provided
            if 'output_path' in event and event['output_path']:
                input_data['output_location'] = event['output_path']
                logger.info(f"Output will be written to: {event['output_path']}")

            input_json = json.dumps(input_data)
        # Handle S3 event
        elif 'Records' in event and event['Records']:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            logger.info(f"Processing file: bucket={bucket}, key={key}")

            input_data = {
                'file_to_obfuscate': f's3://{bucket}/{key}',
                'pii_fields': pii_fields
            }

            # Add output_path if provided in the event
            if 'output_path' in event and event['output_path']:
                input_data['output_location'] = event['output_path']
                logger.info(f"Output will be written to: {event['output_path']}")

            input_json = json.dumps(input_data)
        else:
            logger.error("Invalid event structure")
            return {
                'statusCode': 400,
                'body': 'Invalid event structure'
            }

        # Process the file
        try:
            result = obfuscate_pii(input_json)

            # If output_location was provided, log success message
            if 'output_location' in input_data:
                logger.info(
                    f"Successfully processed file and wrote to {input_data['output_location']}"
                )

            return {
                'statusCode': 200,
                'body': result,
                'isBase64Encoded': True,
                'headers': {
                    'Content-Type': 'application/octet-stream',
                    'Content-Disposition': 'attachment; filename="obfuscated_data.csv"'
                }
            }
        except ValueError as e:
            if "S3 file not found" in str(e):
                logger.error("File not found")
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
