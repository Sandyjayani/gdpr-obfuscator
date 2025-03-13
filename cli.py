#!/Users/sandy/Desktop/abacus_vscode/gdpr-obfuscator/cli.py
#!/usr/bin/env python3
import argparse
import json
import sys
import os
import boto3
from moto import mock_aws
from src.gdpr_obfuscator import obfuscate_pii


@mock_aws
def process_local_file(
    local_file: str,
    pii_fields: list,
    output_file: str = None,
    bucket: str = 'my_ingestion_bucket'
):
    """Process a local file using mocked AWS services"""
    try:
        # Create mock S3 bucket
        s3_client = boto3.client('s3')
        s3_client.create_bucket(Bucket=bucket)

        # Read local file and upload to mock S3
        with open(local_file, 'rb') as f:
            file_content = f.read()

        filename = os.path.basename(local_file)
        s3_client.put_object(Bucket=bucket, Key=f'input/{filename}', Body=file_content)

        # Prepare input for obfuscator
        input_json = json.dumps({
            "file_to_obfuscate": f"s3://{bucket}/input/{filename}",
            "pii_fields": pii_fields
        })

        # Process the file
        result = obfuscate_pii(input_json)
        
        # Handle different response types
        if isinstance(result, str):
            try:
                result_dict = json.loads(result)
            except json.JSONDecodeError:
                print("Error: Invalid JSON response from obfuscator", file=sys.stderr)
                sys.exit(1)
        elif isinstance(result, bytes):
            # If result is bytes, decode it to string and try to parse as JSON
            try:
                result_dict = json.loads(result.decode('utf-8'))
            except json.JSONDecodeError:
                # If it's not JSON, treat the bytes as the direct output
                if output_file:
                    with open(output_file, 'wb') as f:
                        f.write(result)
                    print(f"Obfuscated CSV saved to: {output_file}")
                else:
                    sys.stdout.buffer.write(result)
                return
        elif isinstance(result, dict):
            result_dict = result
        else:
            print(f"Error: Unexpected response type from obfuscator: {type(result)}", file=sys.stderr)
            sys.exit(1)

        # Check response status
        if result_dict.get('statusCode') != 200:
            print(f"Error: {result_dict.get('body', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

        # Get the response body
        body = result_dict.get('body', '')
        
        # Handle output
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(body)
            print(f"Obfuscated CSV saved to: {output_file}")
        else:
            # Print directly to stdout - using buffer.write instead of print to avoid extra newline
            sys.stdout.buffer.write(body.encode('utf-8') if isinstance(body, str) else body)

    except FileNotFoundError:
        print(f"Error: Input file '{local_file}' not found. Please check the file path.",
              file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def process_s3_file(s3_path: str, pii_fields: list, output_file: str = None):
    """Process an S3 file using real AWS services"""
    try:
        input_json = json.dumps({
            "file_to_obfuscate": s3_path,
            "pii_fields": pii_fields
        })

        # Process the file
        result = obfuscate_pii(input_json)
        
        # Handle different response types
        if isinstance(result, str):
            try:
                result_dict = json.loads(result)
            except json.JSONDecodeError:
                print("Error: Invalid JSON response from obfuscator", file=sys.stderr)
                sys.exit(1)
        elif isinstance(result, bytes):
            # If result is bytes, decode it to string and try to parse as JSON
            try:
                result_dict = json.loads(result.decode('utf-8'))
            except json.JSONDecodeError:
                # If it's not JSON, treat the bytes as the direct output
                if output_file:
                    if output_file.startswith('s3://'):
                        # Parse S3 path
                        s3_parts = output_file[5:].split('/', 1)
                        if len(s3_parts) < 2:
                            print("Error: Invalid S3 output path format", file=sys.stderr)
                            sys.exit(1)

                        bucket = s3_parts[0]
                        key = s3_parts[1]

                        # Upload to S3
                        s3_client = boto3.client('s3')
                        s3_client.put_object(
                            Bucket=bucket,
                            Key=key,
                            Body=result,
                            ContentType='text/csv'
                        )
                        print(f"Obfuscated CSV saved to S3: {output_file}")
                    else:
                        with open(output_file, 'wb') as f:
                            f.write(result)
                        print(f"Obfuscated CSV saved to: {output_file}")
                else:
                    sys.stdout.buffer.write(result)
                return
        elif isinstance(result, dict):
            result_dict = result
        else:
            print(f"Error: Unexpected response type from obfuscator: {type(result)}", file=sys.stderr)
            sys.exit(1)

        # Check response status
        if result_dict.get('statusCode') != 200:
            print(f"Error: {result_dict.get('body', 'Unknown error')}", file=sys.stderr)
            sys.exit(1)

        # Get the response body
        body = result_dict.get('body', '')
        if not body:
            print("Error: Empty response body from obfuscator", file=sys.stderr)
            sys.exit(1)

        if output_file:
            # Check if output is an S3 path
            if output_file.startswith('s3://'):
                # Parse S3 path
                s3_parts = output_file[5:].split('/', 1)
                if len(s3_parts) < 2:
                    print("Error: Invalid S3 output path format", file=sys.stderr)
                    sys.exit(1)

                bucket = s3_parts[0]
                key = s3_parts[1]

                # Upload to S3
                s3_client = boto3.client('s3')
                s3_client.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=body.encode('utf-8') if isinstance(body, str) else body,
                    ContentType='text/csv'
                )
                print(f"Obfuscated CSV saved to S3: {output_file}")
            else:
                # Local file output
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(body)
                print(f"Obfuscated CSV saved to: {output_file}")
        else:
            # Print directly to stdout - using buffer.write instead of print to avoid extra newline
            sys.stdout.buffer.write(body.encode('utf-8') if isinstance(body, str) else body)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='GDPR Data Obfuscator - Mask PII data in CSV files'
    )

    # Input source group
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        '--s3-path',
        help='S3 path to the CSV file (e.g., s3://bucket-name/path/to/file.csv)'
    )
    source_group.add_argument(
        '--local-file',
        help='Path to local CSV file'
    )

    parser.add_argument(
        '--pii-fields',
        required=True,
        nargs='+',
        help='List of column names to obfuscate (e.g., name email_address)'
    )
    parser.add_argument(
        '--output',
        help='Path to save the obfuscated CSV (optional, defaults to stdout)'
    )
    parser.add_argument(
        '--bucket',
        default='my_ingestion_bucket',
        help='S3 bucket name for local testing (default: my_ingestion_bucket)'
    )

    args = parser.parse_args()

    if args.s3_path:
        process_s3_file(args.s3_path, args.pii_fields, args.output)
    else:
        process_local_file(args.local_file, args.pii_fields, args.output, args.bucket)


if __name__ == '__main__':
    main()
