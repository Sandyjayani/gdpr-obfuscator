import pytest
import os
import json
import io
import pandas as pd
from src.obfuscator import GDPRObfuscator

class TestGDPRObfuscator:
    @pytest.fixture
    def sample_data_path(self):
        return os.path.join(os.path.dirname(__file__), 'sample_data')

    @pytest.fixture
    def pii_configurations(self, sample_data_path):
        with open(os.path.join(sample_data_path, 'pii_fields.json'), 'r') as f:
            return json.load(f)['configurations']

    def test_valid_data_basic_pii(self, sample_data_path, pii_configurations):
        with open(os.path.join(sample_data_path, 'sample.csv'), 'r') as f:
            csv_data = io.StringIO(f.read())

        basic_pii = next(config for config in pii_configurations
                        if config['name'] == 'basic_pii')

        obfuscator = GDPRObfuscator()
        result = obfuscator.obfuscate_csv(csv_data, basic_pii['fields'])

        # Convert result to DataFrame for verification
        result_df = pd.read_csv(io.StringIO(result.decode('utf-8')))

        # Verify obfuscation
        assert all(result_df['name'] == '***')
        assert all(result_df['email_address'] == '***')
        assert 'Software Engineering' in result_df['course'].values

    def test_invalid_data(self, sample_data_path):
        with open(os.path.join(sample_data_path, 'invalid.csv'), 'r') as f:
            csv_data = io.StringIO(f.read())

        obfuscator = GDPRObfuscator()
        with pytest.raises(ValueError):
            obfuscator.obfuscate_csv(csv_data, ["name", "email_address"])

    def test_extended_pii_fields(self, sample_data_path, pii_configurations):
        with open(os.path.join(sample_data_path, 'sample.csv'), 'r') as f:
            csv_data = io.StringIO(f.read())

        extended_pii = next(config for config in pii_configurations
                          if config['name'] == 'extended_pii')

        obfuscator = GDPRObfuscator()
        result = obfuscator.obfuscate_csv(csv_data, extended_pii['fields'])

        result_df = pd.read_csv(io.StringIO(result.decode('utf-8')))

        assert all(result_df['name'] == '***')
        assert all(result_df['email_address'] == '***')
        assert all(result_df['phone_number'] == '***')

    def test_null_input(self):
        obfuscator = GDPRObfuscator()
        with pytest.raises(ValueError):
            obfuscator.obfuscate_csv(None, ["name"])
