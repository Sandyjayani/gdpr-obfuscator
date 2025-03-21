# GDPR Data Obfuscator

A robust Python service designed to automatically detect and obfuscate personally identifiable information (PII) in CSV files stored in AWS S3. This enterprise-ready tool helps organizations achieve GDPR compliance by efficiently masking sensitive data while maintaining the structural integrity of the original files.

## Features

- Intelligent detection and obfuscation of specified PII fields in CSV files
- Seamless AWS Lambda integration for scalable serverless processing
- Highly configurable PII field mapping to meet specific compliance requirements
- Complete preservation of CSV structure and non-PII data
- Comprehensive error handling and validation:
  - Path traversal detection for S3 keys
  - Unicode character support
  - CSV structure validation
  - JSON input validation
- Optimized AWS S3 integration:
  - Region-aware client initialization
  - Proper Content-Type setting
  - Flexible output location specification
- Performance-optimized for handling large datasets efficiently

## Requirements

- Python 3.8+
- AWS account with appropriate S3 access permissions
- Required Python packages:
  - boto3 (AWS SDK for Python)
  - pandas (for efficient data processing)
  - pytest (for comprehensive testing)
  - moto (for AWS service mocking in tests)
  - flake8 (for code quality)
  - bandit (for security scanning)
  - safety (for dependency vulnerability checks)

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

4. Verify installation:
```bash
python -m pytest tests/
```

## Usage

### Command Line Usage

The tool can be used in two modes:

1. **Local Mode** (No AWS credentials needed):
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

2. **S3 Mode** (Requires AWS credentials):
```bash
# Process an S3 file
python cli.py --s3-path s3://my-bucket/file.csv --pii-fields name email_address

# Save output to local file
python cli.py --s3-path s3://my-bucket/file.csv --pii-fields name email_address --output masked.csv

# Process and save directly to another S3 location
python cli.py --s3-path s3://my-bucket/file.csv --pii-fields name email_address --output s3://output-bucket/masked.csv
```

Arguments:
- `--s3-path`: S3 path to the CSV file (requires AWS credentials)
- `--local-file`: Path to local CSV file (no AWS credentials needed)
- `--pii-fields`: List of column names to obfuscate (space-separated)
- `--output`: Optional path to save the obfuscated CSV (defaults to stdout, can be local or S3 path)
- `--bucket`: Optional mock S3 bucket name for local testing (default: my_ingestion_bucket)

Note: 
- Local mode uses mocked AWS services, so no real AWS credentials are required
- When using S3 output paths, the file will be uploaded with 'text/csv' Content-Type
- The tool will exit with status code 1 if any errors occur during processing
- Common error scenarios handled:
  - File not found (local or S3)
  - Invalid input format
  - S3 access or upload errors
  - Processing errors


### As an AWS Lambda Function

The Lambda function supports two invocation methods:
1. Direct invocation with a specific file to process
2. S3 event-triggered processing

#### Direct Invocation
```python
# Example event for direct invocation
{
  "file_to_obfuscate": "s3://gdpr-input-bucket/sample.csv",
  "pii_fields": [
    "name",
    "email_address"
  ],
    "output_path": "s3://gdpr-output-bucket/sample_obfuscated.csv"
}
```

#### S3 Event Processing
The function automatically processes files when they are uploaded to a configured S3 bucket.

1. Deploy the Lambda function code to AWS:
   ```bash
   # Create a deployment package manually
   mkdir -p package
   pip install -r lambda_function/requirements.txt -t package/
   cp -r src/ package/
   cp lambda_function/lambda_function.py package/
   cd package && zip -r ../lambda_deployment.zip . && cd ..
   ```

2. Configure the Lambda function:
   - Runtime: Python 3.8+
   - Handler: lambda_function.lambda_handler
   - Memory: 256MB (recommended minimum)
   - Timeout: 3 minutes (for larger files)


3. Set up S3 trigger for new files:
   - Configure event type: ObjectCreated
   - Prefix: input/ (or your preferred input directory)
   - Suffix: .csv

4. The function will:
   - Process files either through direct invocation or S3 events
   - Obfuscate configured PII fields from environment variables
   - Return appropriate HTTP status codes (200, 400, 404, 500)
   - Provide detailed error messages for troubleshooting
   - Log comprehensive processing details to CloudWatch

#### Response Format
The function returns a JSON object with:
```json
{
    "statusCode": 200,  // HTTP status code
    "body": "Processing result or error message"
}
```

Status Codes:
- 200: Successful processing
- 400: Invalid input or validation error
- 404: File not found in S3
- 500: Internal processing error

## Testing with AWS

### Prerequisites

1. Configure AWS credentials:
   ```bash
   aws configure
   ```

2. Create S3 buckets for testing:
   ```bash
   aws s3 mb s3://gdpr-input-bucket
   aws s3 mb s3://gdpr-output-bucket
   ```

### Testing the CLI with S3

1. Create a sample CSV file:
   ```csv
   student_id,name,course,cohort,graduation_date,email_address
   1234,John Doe,Software,2024,2024-03-31,john@example.com
   5678,Jane Smith,Data,2024,2024-06-30,jane@example.com
   ```

2. Upload the file to S3:
   ```bash
   aws s3 cp sample.csv s3://gdpr-input-bucket/
   ```

3. Process the file with the CLI:
   ```bash
   python cli.py --s3-path s3://gdpr-input-bucket/sample.csv --pii-fields name email_address --output s3://gdpr-output-bucket/obfuscated-sample.csv
   ```

4. Verify the result:
   ```bash
   aws s3 cp s3://gdpr-output-bucket/obfuscated-sample.csv ./
   cat obfuscated-sample.csv
   ```

### Testing the Lambda Function

1. Create a deployment package:
   ```bash
   mkdir -p lambda_package
   cp lambda_function/lambda_function.py lambda_package/
   mkdir -p lambda_package/src
   cp src/gdpr_obfuscator.py lambda_package/src/
   touch lambda_package/src/__init__.py

   cd lambda_package
   zip -r ../gdpr-obfuscator-lambda.zip .
   cd ..
   ```

2. Deploy to AWS Lambda using the AWS CLI:
   ```bash
   aws lambda create-function \
     --function-name gdpr-obfuscator \
     --runtime python3.8 \
     --role arn:aws:iam::YOUR_ACCOUNT_ID:role/lambda-s3-role \
     --handler lambda_function.lambda_handler \
     --zip-file fileb://lambda_deployment.zip \
     --timeout 180 \
     --memory-size 256 \
     --environment "Variables={DEFAULT_OUTPUT_BUCKET=gdpr-output-bucket,DEFAULT_PII_FIELDS=name,email_address}"
   ```

3. Configure S3 trigger:
   ```bash
   aws lambda add-permission \
     --function-name gdpr-obfuscator \
     --statement-id s3-trigger \
     --action lambda:InvokeFunction \
     --principal s3.amazonaws.com \
     --source-arn arn:aws:s3:::gdpr-input-bucket
   ```

4. Test by uploading a file to the input bucket:
   ```bash
   aws s3 cp sample.csv s3://gdpr-input-bucket/input/
   ```

5. Check the output bucket for the processed file:
   ```bash
   aws s3 ls s3://gdpr-output-bucket/
   ```

### Performance Testing with AWS

To test performance with larger files:

1. Generate a test file with the provided utility:
   ```bash
   python tools/generate_test_file.py --rows 10000 --output large_sample.csv
   ```

2. Upload and process the file:
   ```bash
   aws s3 cp large_sample.csv s3://gdpr-input-bucket/
   python cli.py --s3-path s3://gdpr-input-bucket/large_sample.csv --pii-fields name email_address --output s3://gdpr-output-bucket/large_sample_obfuscated.csv
   ```

3. For Lambda performance testing, monitor execution metrics in CloudWatch.

## Project Structure

```
gdpr-obfuscator/
├── src/
│   ├── __init__.py
│   └── gdpr_obfuscator.py       # Core obfuscation logic
├── lambda_function/
│   ├── lambda_function.py       # AWS Lambda handler
│   └── requirements.txt         # Lambda-specific dependencies
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Test fixtures
│   ├── test_cli.py              # CLI tests
│   ├── test_gdpr_obfuscator.py  # Core functionality tests
│   ├── test_lambda_function.py  # Lambda integration tests
│   └── test_performance.py      # Performance benchmarks
├── tools/
│   └── generate_test_file.py    # Utility to generate test files
├── cli.py                       # Command-line interface
├── requirements.txt             # Project dependencies
├── sample.csv                   # Sample data for testing
├── LICENSE                      # License file
└── README.md                    # Project documentation
```

## Configuration

The obfuscator accepts the following configuration in JSON format:

```json
{
    "file_to_obfuscate": "s3://bucket-name/path/to/file.csv",
    "pii_fields": ["name", "email_address", "phone_number", "address"],
    "output_path": "s3://output-bucket/processed/file.csv",
    "obfuscation_char": "*",
    "preserve_format": false,
    "csv_options": {
        "delimiter": ",",
        "quotechar": "\"",
        "encoding": "utf-8"
    },
    "logging": {
        "level": "INFO",
        "include_timestamps": true
    }
}
```

### Configuration Options

- `file_to_obfuscate`: S3 path to the CSV file (must start with "s3://"). Path traversal attempts (e.g., "../") are detected and blocked
- `pii_fields`: List of column names to be obfuscated
- `output_location`: (Optional) S3 path for the processed file (e.g., "s3://bucket/processed/file.csv")
- `obfuscation_char`: (Optional) Character used for obfuscation (default: "*")
- `preserve_format`: (Optional) Whether to preserve data format patterns (default: false)
- `csv_options`: (Optional) CSV parsing options
  - `delimiter`: CSV field separator (default: ",")
  - `quotechar`: Character for quoting fields (default: '"')
  - `encoding`: File encoding (default: "utf-8", full Unicode support)
- `logging`: (Optional) Logging configuration
  - `level`: Logging level (default: "INFO")
  - `include_timestamps`: Whether to include timestamps in logs (default: true)

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/gdpr-obfuscator.git
cd gdpr-obfuscator

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (includes development tools)
pip install -r requirements.txt

# Run tests to verify setup
pytest
```

### Code Quality and Security

This project follows strict PEP 8 style guidelines and implements comprehensive security checks.

#### Style Checking
```bash
# Run flake8 on all Python files
flake8 .

# Run flake8 on specific file
flake8 src/gdpr_obfuscator.py
```

#### Security Scanning

The project uses multiple security scanning tools:

1. **Bandit** - For Python code security analysis:
```bash
# Scan entire project
bandit -r .

# Scan specific directory
bandit -r src/

# Generate detailed report
bandit -r . -f json -o bandit_report.json
```

2. **Safety** - For checking dependencies against known security vulnerabilities:
```bash
# Check installed packages
safety check

# Check requirements file
safety check -r requirements.txt

# Generate detailed report
safety check --full-report -o safety_report.txt
```

3. **Run all security checks**:
```bash
# Run all security checks
flake8 .
bandit -r .
safety check
```

### Testing

The project includes comprehensive test suites:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_gdpr_obfuscator.py

# Run tests with coverage report
pip install pytest-cov
pytest --cov=src tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/

# Run tests without deprecation warnings
pytest --disable-warnings
```

#### Handling Deprecation Warnings

The tests may show deprecation warnings from the boto3/botocore libraries. These warnings are related to the use of `datetime.datetime.utcnow()` which is deprecated in newer Python versions. 

These warnings don't affect functionality and are handled in two ways:
1. Through the `pytest.ini` configuration file
2. Via a fixture in `tests/conftest.py`

If you want to run tests without seeing these warnings, use:
```bash
pytest --disable-warnings
```

#### Handling Region-Specific Issues

When running tests or using the local mode, you might encounter region-specific errors like:
```
IllegalLocationConstraintException: The unspecified location constraint is incompatible for the region specific endpoint this request was sent to.
```

This happens because:
1. The AWS SDK uses your configured region (from `~/.aws/config` or environment variables)
2. When creating S3 buckets without specifying a region, it can cause conflicts

The codebase handles this by explicitly setting the region to `us-east-1` when creating mock S3 resources. If you're still encountering this error, you can:

1. Set the AWS region in your environment:
   ```bash
   export AWS_DEFAULT_REGION=us-east-1
   ```

2. Or configure it in your AWS config file:
   ```bash
   aws configure set region us-east-1
   ```

### Troubleshooting the IllegalLocationConstraintException

If you're still encountering the `IllegalLocationConstraintException` error after setting your region, here are additional troubleshooting steps:

1. **Check your current AWS region configuration**:
   ```bash
   aws configure get region
   ```

2. **Verify the code is using your region**:
   The latest version of the code should automatically detect your configured region. If you're using an older version, you might need to update the S3 client initialization to use your region:
   
   ```python
   # Get the default region from the session or use us-east-1 as fallback
   session = boto3.session.Session()
   region = session.region_name or 'us-east-1'
   
   # Create S3 client with your region
   s3_client = boto3.client('s3', region_name=region)
   ```

3. **For non-us-east-1 regions**: When creating buckets in regions other than `us-east-1`, you may need to explicitly specify the location constraint:
   
   ```python
   # Only needed for regions other than us-east-1
   if region != 'us-east-1':
       s3_client.create_bucket(
           Bucket=bucket,
           CreateBucketConfiguration={'LocationConstraint': region}
       )
   else:
       s3_client.create_bucket(Bucket=bucket)
   ```

4. **For testing purposes only**: If you're just testing locally and don't need to interact with real AWS services, you can set a dummy region:
   
   ```bash
   export AWS_DEFAULT_REGION=us-east-1
   ```

The tests cover:
- Core obfuscation functionality
- Error handling and edge cases
- AWS Lambda integration
- S3 interaction
- Performance benchmarks
- Security considerations

#### Performance Testing

The project includes performance tests to ensure it meets the requirement of processing 1MB files in under 1 minute:

```bash
# Run just the performance tests
pytest tests/test_performance.py -v

# Run the memory usage test
pytest tests/test_performance.py::test_memory_usage -v
```

Performance tests verify:
- Processing time for files up to 10MB
- Memory usage during processing
- Throughput (MB/second) for different file sizes
- Scalability with increasing file complexity

These tests help ensure the service meets performance criteria and can be deployed within AWS Lambda's constraints.

## Error Handling

The service implements robust error handling for production reliability:

- **Input Validation**:
  - Invalid JSON input detection
  - Missing or malformed CSV files
  - Missing or invalid PII fields
  - Invalid S3 paths and path traversal attempts
  - CSV files without headers
  - Unicode character validation
  - Special character handling in CSV

- **AWS Service Errors**:
  - S3 access permission issues
  - Bucket not found errors
  - Network connectivity problems
  - Service throttling and quotas
  - Region-specific handling

- **Processing Errors**:
  - CSV parsing errors
  - Memory limitations
  - Timeout handling
  - Malformed data handling
  - Character encoding issues

- **Logging and Monitoring**:
  - Detailed error messages
  - CloudWatch integration
  - Error classification
  - Retry mechanisms for transient errors
  - Processing metrics tracking

## Contributing

We welcome contributions to improve the GDPR Data Obfuscator!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Implement your changes
4. Run tests and style checks (`pytest && flake8`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Contribution Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR
- Include a clear description of changes in PR

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Security Considerations

- The tool replaces PII data with configurable obfuscation characters
- Original data is never stored or logged
- AWS credentials should be properly secured using IAM roles
- S3 bucket permissions should be properly configured with least privilege
- All dependencies are regularly scanned for vulnerabilities
- Input validation prevents injection attacks
- Logging excludes sensitive data

## AWS Lambda Deployment

### Creating a Deployment Package for Manual Upload

Create a properly structured deployment package for manual upload through the AWS Console:

```bash
# Create a deployment directory with proper structure
mkdir -p lambda_deployment/src

# Copy the files to the correct locations
cp lambda_function/lambda_function.py lambda_deployment/
cp src/gdpr_obfuscator.py lambda_deployment/src/

# Create an __init__.py file in the src directory to make it a proper package
touch lambda_deployment/src/__init__.py

# Create the zip file with the correct structure
cd lambda_deployment
zip -r ../lambda_deployment.zip .
cd ..
```

This creates a deployment package with the correct directory structure:
```
lambda_deployment.zip
├── lambda_function.py
└── src/
    ├── __init__.py
    └── gdpr_obfuscator.py
```

### Manual Upload to AWS Lambda

1. Go to the [AWS Lambda Console](https://console.aws.amazon.com/lambda)
2. Click "Create function" or select your existing function
3. Under the "Code source" section:
   - Click "Upload from"
   - Select ".zip file"
   - Upload your `lambda_deployment.zip`
4. Configure the function:
   - Runtime: Python 3.8+
   - Handler: lambda_function.lambda_handler
   - Memory: 256MB (recommended minimum)
   - Timeout: 3 minutes (for larger files)


### Configure IAM Role

Ensure your Lambda function has an IAM role with:
- AmazonS3ReadOnlyAccess (for reading input files)
- Custom policy for writing to output bucket:
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "s3:PutObject",
          "s3:PutObjectAcl"
        ],
        "Resource": "arn:aws:s3:::gdpr-output-bucket/*"
      }
    ]
  }
  ```
- CloudWatchLogsFullAccess (for logging)

### Monitoring and Maintenance

- Set up CloudWatch alarms for errors and performance
- Configure SNS notifications for processing failures
- Regularly update dependencies for security patches
- Monitor Lambda execution metrics (duration, memory usage)
- Set up AWS X-Ray for tracing (optional)