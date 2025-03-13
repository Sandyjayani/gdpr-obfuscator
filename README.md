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

# Save output to file
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
- `--obfuscation-char`: Optional character to use for obfuscation (default: *)
- `--preserve-format`: Optional flag to preserve data format (e.g., email@example.com → ****@*******.com)

Note: Local mode uses mocked AWS services, so no real AWS credentials are required.

### As a Python Package

```python
from src.gdpr_obfuscator import obfuscate_pii
import json

# Prepare input JSON
input_json = {
    "file_to_obfuscate": "s3://my-bucket/path/to/file.csv",
    "pii_fields": ["name", "email_address"],
    "output_path": "s3://my-bucket/processed/file.csv",  # Optional
    "obfuscation_char": "#",  # Optional, defaults to *
    "preserve_format": True  # Optional, defaults to False
}

# Process the file
result = obfuscate_pii(json.dumps(input_json))
print(result)  # Contains status and output file location
```

### As an AWS Lambda Function

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
   - Environment variables:
     - `DEFAULT_OUTPUT_BUCKET`: Destination bucket for processed files
     - `DEFAULT_PII_FIELDS`: Comma-separated list of default PII fields
     - `OBFUSCATION_CHAR`: Character to use for obfuscation (optional)

3. Set up S3 trigger for new files:
   - Configure event type: ObjectCreated
   - Prefix: input/ (or your preferred input directory)
   - Suffix: .csv

4. The function will automatically:
   - Process new CSV files uploaded to the specified S3 bucket
   - Obfuscate configured PII fields
   - Save the processed file to the output bucket or 'processed/' folder
   - Log processing details to CloudWatch

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
pytest --cov=src tests/

# Generate HTML coverage report
pytest --cov=src --cov-report=html tests/
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

### Creating a Deployment Package

```bash
# Create a deployment package manually
mkdir -p package
pip install -r lambda_function/requirements.txt -t package/
cp -r src/ package/
cp lambda_function/lambda_function.py package/
cd package && zip -r ../lambda_deployment.zip . && cd ..
```

### Deploying to AWS Lambda

1. **Create a new Lambda function**:
   - Runtime: Python 3.8+
   - Handler: lambda_function.lambda_handler
   - Memory: 256MB (minimum recommended)
   - Timeout: 3 minutes (for larger files)
   - Upload the lambda_deployment.zip file

2. **Configure IAM permissions**:
   - Create a role with the following policies:
     - AmazonS3ReadOnlyAccess (for reading input files)
     - Custom policy for writing to output bucket
     - CloudWatchLogsFullAccess (for logging)

3. **Configure environment variables**:
   - `DEFAULT_OUTPUT_BUCKET`: Default S3 bucket for processed files
   - `DEFAULT_PII_FIELDS`: Comma-separated list of default PII fields
   - `OBFUSCATION_CHAR`: Character to use for obfuscation (optional)
   - `LOG_LEVEL`: Logging level (default: INFO)

4. **Set up S3 trigger**:
   - Event type: s3:ObjectCreated:*
   - Bucket: Your input bucket
   - Prefix: input/ (optional)
   - Suffix: .csv

5. **Test the deployment**:
   - Upload a CSV file to the configured S3 bucket
   - Check CloudWatch logs for processing details
   - Verify the obfuscated file in the output location

### Monitoring and Maintenance

- Set up CloudWatch alarms for errors and performance
- Configure SNS notifications for processing failures
- Regularly update dependencies for security patches
- Monitor Lambda execution metrics (duration, memory usage)
- Set up AWS X-Ray for tracing (optional)