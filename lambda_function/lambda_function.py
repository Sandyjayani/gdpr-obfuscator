import json
import boto3
import sys
import pathlib
from src.gdpr_obfuscator import obfuscate_pii

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
    try:
        # Validate event structure
        if 'Records' not in event or not event['Records']:
            return {
                'statusCode': 400,
                'body': 'Invalid event structure: missing Records'
            }

        # Get bucket and key from event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']

        # Prepare input for obfuscator
        input_json = json.dumps({
            'file_to_obfuscate': f's3://{bucket}/{key}',
            'pii_fields': ['name', 'email_address']
        })

        # Process the file
        try:
            result = obfuscate_pii(input_json)
        except ValueError as e:
            if "S3 file not found" in str(e):
                return {
                    'statusCode': 404,
                    'body': f'File not found: {key}'
                }
            return {
                'statusCode': 400,
                'body': str(e)
            }

        # Save result to processed_data folder
        output_key = key.replace('new_data', 'processed_data')
        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=bucket,
            Key=output_key,
            Body=result
        )

        return {
            'statusCode': 200,
            'body': f'Successfully processed {key} to {output_key}'
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error processing file: {str(e)}'
        }
