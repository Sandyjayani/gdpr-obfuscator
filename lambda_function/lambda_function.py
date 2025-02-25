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
        # Validate event structure
        if 'Records' not in event or not event['Records']:
            logger.error("Invalid event structure: missing Records")
            return {
                'statusCode': 400,
                'body': 'Invalid event structure: missing Records'
            }

        # Get bucket and key from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        logger.info(f"Processing file: bucket={bucket}, key={key}")

        # Get PII fields from environment variables or use defaults
        pii_fields = os.environ.get('PII_FIELDS', 'name,email_address').split(',')
        logger.info(f"Using PII fields: {pii_fields}")

        # Prepare input for obfuscator
        input_json = json.dumps({
            'file_to_obfuscate': f's3://{bucket}/{key}',
            'pii_fields': pii_fields
        })

        # Process the file
        try:
            result = obfuscate_pii(input_json)
        except ValueError as e:
            if "S3 file not found" in str(e):
                logger.error(f"File not found: {key}")
                return {
                    'statusCode': 404,
                    'body': f'File not found: {key}'
                }
            logger.error(f"Validation error: {str(e)}")
            return {
                'statusCode': 400,
                'body': str(e)
            }

        # Save result to processed_data folder
        if 'new_data' in key:
            output_key = key.replace('new_data', 'processed_data')
        else:
            # If not in new_data folder, place in processed_data with same filename
            filename = key.split('/')[-1]
            output_key = f'processed_data/{filename}'

        logger.info(f"Saving obfuscated file to: bucket={bucket}, key={output_key}")
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=result
        )
        logger.info("File successfully processed and saved")

        return {
            'statusCode': 200,
            'body': f'Successfully processed {key} to {output_key}'
        }

    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        return {
            'statusCode': 500,
            'body': f'Error processing file: {str(e)}'
        }
