# GDPR Data Obfuscator

A Python service that automatically obfuscates personally identifiable information (PII) in CSV files stored in AWS S3. This tool helps organizations comply with GDPR requirements by masking sensitive data while preserving the structure of the original files.

## Features

- Automatically detects and obfuscates specified PII fields in CSV files
- AWS Lambda integration for serverless processing
- Configurable PII field mapping
- Preserves CSV structure and non-PII data
- Error handling for various edge cases
- AWS S3 integration for input and output

## Requirements

- Python 3.8+
- AWS account with S3 access
- Required Python packages:
  - boto3
  - pytest (for testing)
  - moto (for testing)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/gdpr-obfuscator.git
cd gdpr-obfuscator
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Usage

The tool can be used in two modes:

1. Local Mode (No AWS credentials needed):
```bash
# Process the sample file and print to screen
python cli.py --local-file sample.csv --pii-fields name email_address

# Save output to a new file
python cli.py --local-file sample.csv --pii-fields name email_address --output obfuscated.csv

# Obfuscate only specific fields
python cli.py --local-file sample.csv --pii-fields name
```

Example input (sample.csv):
```csv
student_id,name,course,cohort,graduation_date,email_address
1234,John Doe,Software,2024,2024-03-31,john@example.com
5678,Jane Smith,Data,2024,2024-06-30,jane@example.com
```

Example output:
```csv
student_id,name,course,cohort,graduation_date,email_address
1234,***,Software,2024,2024-03-31,***
5678,***,Data,2024,2024-06-30,***
```

2. S3 Mode (Requires AWS credentials):
```bash
# Process an S3 file
python cli.py --s3-path s3://my-bucket/file.csv --pii-fields name email_address

# Save output to file
python cli.py --s3-path s3://my-bucket/file.csv --pii-fields name email_address --output masked.csv
```

Arguments:
- `--s3-path`: S3 path to the CSV file (requires AWS credentials)
- `--local-file`: Path to local CSV file (no AWS credentials needed)
- `--pii-fields`: List of column names to obfuscate (space-separated)
- `--output`: Optional path to save the obfuscated CSV (defaults to stdout)
- `--bucket`: Optional mock S3 bucket name for local testing (default: my_ingestion_bucket)

Note: Local mode uses mocked AWS services, so no real AWS credentials are required.

### As a Python Package

```python
from src.gdpr_obfuscator import obfuscate_pii

# Prepare input JSON
input_json = {
    "file_to_obfuscate": "s3://my-bucket/path/to/file.csv",
    "pii_fields": ["name", "email_address"]
}

# Process the file
result = obfuscate_pii(json.dumps(input_json))
```

### As an AWS Lambda Function

1. Deploy the Lambda function code to AWS
2. Configure S3 trigger for new files
3. The function will automatically:
   - Process new CSV files uploaded to the specified S3 bucket
   - Obfuscate configured PII fields
   - Save the processed file to a 'processed_data' folder

## File Structure

```
gdpr-obfuscator/
├── src/
│   └── gdpr_obfuscator.py    # Main obfuscation logic
├── lambda_function/          # AWS Lambda function
│   ├── lambda_function.py
│   └── requirements.txt      # Lambda-specific dependencies
├── tests/
│   ├── test_gdpr_obfuscator.py
│   └── test_lambda_function.py
├── cli.py                    # Command-line interface
├── requirements.txt          # Project dependencies
└── README.md
```

## Configuration

The obfuscator accepts the following configuration in JSON format:

```json
{
    "file_to_obfuscate": "s3://bucket-name/path/to/file.csv",
    "pii_fields": ["name", "email_address"]
}
```

- `file_to_obfuscate`: S3 path to the CSV file (must start with "s3://")
- `pii_fields`: List of column names to be obfuscated

## Development

### Code Quality and Security

This project follows PEP 8 style guidelines and implements several security checks.

#### Style Checking
```bash
# Run flake8 on all Python files
flake8 .

# Run flake8 on specific file
flake8 src/gdpr_obfuscator.py
```

Common flake8 codes:
- E201-E299: Whitespace errors
- E301-E399: Blank line errors
- E401-E499: Import formatting
- E501: Line too long
- F401: Unused import
- F821: Undefined name

#### Security Scanning

The project uses multiple security scanning abilities:

1. Bandit - For Python code security analysis:
```bash
# Scan entire project
bandit -r .

# Scan specific directory
bandit -r src/

# Generate detailed report
bandit -r . -f json -ll
```

2. Safety - For checking dependencies against known security vulnerabilities:
```bash
# Check installed packages
safety check

# Check requirements file
safety check -r requirements.txt

# Generate detailed report
safety check --full-report
```

Run all security checks:
```bash
# Style and security checks
flake8 .
bandit -r .
safety check

### Testing

Run the test suite:
```bash
pytest
```

The tests cover:
- Basic obfuscation functionality
- Error handling
- AWS Lambda integration
- Edge cases

## Error Handling

The service handles various error conditions:
- Invalid JSON input
- Missing or malformed CSV files
- Missing PII fields
- Invalid S3 paths
- CSV files without headers
- AWS service errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Security Considerations

- The tool replaces PII data with '***' by default
- Original data is not stored or logged
- AWS credentials should be properly secured
- S3 bucket permissions should be properly configured

## AWS Lambda Deployment

1. Create a deployment package:
```bash
# Create a temporary directory for the package
mkdir package
cd package

# Install dependencies
pip install -r ../lambda/requirements.txt -t .

# Copy the Lambda function
cp ../lambda/lambda_function.py .

# Copy the source code
mkdir src
cp ../src/gdpr_obfuscator.py src/

# Create the ZIP file
zip -r ../lambda_function.zip .

# Clean up
cd ..
rm -rf package
```

2. Create a new Lambda function in AWS:
   - Runtime: Python 3.8+
   - Handler: lambda_function.lambda_handler
   - Upload the lambda_function.zip file
   - Configure memory and timeout as needed

3. Configure the function:
   - Set up S3 trigger for the input bucket
   - Configure appropriate IAM roles with S3 access
   - Set any needed environment variables

4. Test the deployment:
   - Upload a CSV file to the configured S3 bucket
   - Check the CloudWatch logs
   - Verify the obfuscated file in the output location

## Limitations

- Currently only supports CSV files
- PII fields must be exact matches of column headers
- All PII data is replaced with '***' (not configurable)
- No support for nested CSV structures