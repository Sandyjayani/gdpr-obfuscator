#!/usr/bin/env python3
"""
Generate a large CSV file for performance testing.

This script creates a CSV file of the specified size with random data,
which can be used for performance testing of the GDPR obfuscator.
"""

import os
import sys
import random
import string
import argparse


def generate_large_csv(size_mb=1, num_columns=10, num_pii_columns=2, output_file='test_data.csv'):
    """Generate a large CSV file of approximately the specified size in MB."""
    # Calculate approximate row size and number of rows needed
    row_size_bytes = num_columns * 15  # Assume average 15 bytes per column
    num_rows = int((size_mb * 1024 * 1024) // row_size_bytes)  # Convert to integer

    print(f"Generating CSV file with {num_rows} rows and {num_columns} columns...")
    print(f"Target size: {size_mb} MB")
    print(f"PII columns: {num_pii_columns}")

    # Generate column names
    columns = [f"column_{i}" for i in range(num_columns)]
    pii_columns = columns[:num_pii_columns]

    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)

    # Write CSV file
    with open(output_file, 'w') as f:
        # Write header
        f.write(",".join(columns) + "\n")

        # Write rows
        for i in range(num_rows):
            row_values = []
            for j in range(num_columns):
                # Generate random string for each cell
                if j < num_pii_columns:
                    # PII columns get longer values
                    value = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
                else:
                    value = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                row_values.append(value)

            f.write(",".join(row_values) + "\n")

            # Show progress
            if i % max(1, num_rows // 10) == 0:  # Ensure we don't divide by zero
                sys.stdout.write(f"\rProgress: {i/num_rows*100:.1f}%")
                sys.stdout.flush()

    # Get actual file size
    actual_size = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\nFile generated: {output_file}")
    print(f"Actual size: {actual_size:.2f} MB")
    print(f"PII columns: {', '.join(pii_columns)}")

    return pii_columns


def main():
    parser = argparse.ArgumentParser(
        description='Generate a large CSV file for performance testing'
    )
    parser.add_argument(
        '--size',
        type=float,
        default=1.0,
        help='Target file size in MB (default: 1.0)'
    )
    parser.add_argument(
        '--columns',
        type=int,
        default=10,
        help='Number of columns (default: 10)'
    )
    parser.add_argument(
        '--pii-columns',
        type=int,
        default=2,
        help='Number of PII columns (default: 2)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='test_data.csv',
        help='Output file path (default: test_data.csv)'
    )

    args = parser.parse_args()

    if args.pii_columns > args.columns:
        parser.error("Number of PII columns cannot exceed total number of columns")

    pii_columns = generate_large_csv(
        size_mb=args.size,
        num_columns=args.columns,
        num_pii_columns=args.pii_columns,
        output_file=args.output
    )

    # Print command for testing with the generated file
    print("\nTo test with this file using the CLI:")
    pii_fields_str = " ".join(pii_columns)
    print(f"python cli.py --local-file {args.output} --pii-fields {pii_fields_str}")


if __name__ == "__main__":
    main()
