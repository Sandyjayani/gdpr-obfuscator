import pandas as pd
import io
from typing import List, Union
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GDPRObfuscator:
    """
    A class to handle GDPR-compliant data obfuscation.
    """

    def __init__(self, obfuscation_char: str = '***'):
        """
        Initialize the GDPR Obfuscator.

        Args:
            obfuscation_char (str): Character(s) to use for obfuscation
        """
        self.obfuscation_char = obfuscation_char

    def validate_input(self, df: pd.DataFrame, pii_fields: List[str]) -> None:
        """
        Validate input DataFrame and PII fields.

        Args:
            df: Input DataFrame
            pii_fields: List of fields to obfuscate

        Raises:
            ValueError: If validation fails
        """
        if df.empty:
            raise ValueError("Input DataFrame is empty")

        invalid_fields = [field for field in pii_fields if field not in df.columns]
        if invalid_fields:
            raise ValueError(f"Invalid PII fields: {invalid_fields}")

    def obfuscate_csv(self, csv_data: Union[str, io.StringIO], pii_fields: List[str]) -> bytes:
        """
        Obfuscate PII fields in CSV data.

        Args:
            csv_data: CSV data as string or StringIO
            pii_fields: List of field names to obfuscate

        Returns:
            bytes: Obfuscated CSV data as bytes

        Raises:
            ValueError: If input validation fails
        """
        try:
            logger.info("Starting CSV obfuscation process")

            if csv_data is None:
                raise ValueError("CSV data cannot be None")

            # Read CSV data
            df = pd.read_csv(csv_data)

            # Validate input
            self.validate_input(df, pii_fields)

            # Obfuscate PII fields
            for field in pii_fields:
                df[field] = self.obfuscation_char
                logger.info(f"Obfuscated field: {field}")

            # Convert back to CSV bytes
            output = io.StringIO()
            df.to_csv(output, index=False)

            logger.info("CSV obfuscation completed successfully")
            return output.getvalue().encode('utf-8')

        except Exception as e:
            logger.error(f"Error during obfuscation: {str(e)}")
            raise
