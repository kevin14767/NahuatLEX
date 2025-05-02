"""
Initial Data Processing Module

This script serves multiple crucial functions in the NahuatLEX project:
1. Data Initialization and Validation
2. Project Structure Setup
3. Data Preprocessing
4. Logging and Error Tracking
5. Configuration Management

Key Benefits: Standardizes data loading and preprocessing, ensures consistent project structure,
provides robust error handling, facilitates reproducible research workflow

"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import json
import hashlib

class WHPInitializer:
    def __init__(self, config_path='config/whp_config.json'):
        """
        Initialize the WHP data processing workflow
        
        Args:
            config_path (str): Path to configuration JSON file
        """
        self._setup_logging()
        # load configuration
        self.config = self._load_configuration(config_path)
        # if no config was found, use default configuration
        if self.config is None:
            self.config = {
                'input_file_pattern': 'WHP_EarlyNahuatl_data_*.csv',
                'required_columns': [
                    'Ref', 'Headword', 'Orthographic Variants', 
                    'Principal English Translation'
                ],
                'data_validation_rules': {
                    'Ref': {'type': str, 'required': True},
                    'Headword': {'type': str, 'required': True}
                }
            }
        
        
    @staticmethod
    def _clean_text(text):
        """
        Clean text by removing HTML tags and extra whitespace
        Args:
            text (str): Input text
        Returns:
            str: Cleaned text
        """
        if pd.isna(text):
            return ''
        
        import re
        from bs4 import BeautifulSoup
        
        # remove HTML tags
        if isinstance(text, str) and ('<' in text and '>' in text):
            text = BeautifulSoup(text, 'html.parser').get_text(strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _validate_data_integrity(self, df):
        """
        Performs data integrity check
        Args:
            df (pd.DataFrame): Input DataFrame
        """
        # check's for duplicate references (ids)
        dup_refs = df[df.duplicated(subset=['Ref'], keep=False)]
        if not dup_refs.empty:
            self.logger.warning(f"Found {len(dup_refs
                                )} duplicate reference entries")
        # validate col. types and content
        validation_rules = self.config.get('data_validation_rules', {})
        
        for column, rules in validation_rules.items():
            if column not in df.columns:
                self.logger.warning(f"Column '{column}' not found in the dataset")
                continue
            
            # type validation
            if rules.get('type'):
                # find rows with incorrect type
                incorrect_type_rows = df[
                    df[column].apply(lambda x: not isinstance(x, rules['type']))
                ]
                
                # log warning if any incorrect type rows found
                if not incorrect_type_rows.empty:
                    incorrect_count = len(incorrect_type_rows)
                    error_percentage = (incorrect_count / len(df)) * 100
                    
                    self.logger.warning(
                        f"Type mismatch in column '{column}': "
                        f"{incorrect_count} rows have incorrect type "
                        f"(Expected: {rules['type'].__name__}, "
                        f"Percentage: {error_percentage:.2f}%)"
                    )
            
            # req. field validation
            if rules.get('required', False):
                # Find rows with missing values
                missing_value_rows = df[df[column].isna()]
                
                # log warning if any missing values found
                if not missing_value_rows.empty:
                    missing_count = len(missing_value_rows)
                    missing_percentage = (missing_count / len(df)) * 100
                    
                    self.logger.warning(
                        f"Missing values in required column '{column}': "
                        f"{missing_count} rows are empty "
                        f"(Percentage: {missing_percentage:.2f}%)"
                    )

    def _load_configuration(self, config_path):
        """
        Load project configuration from JSON file
        Args:
            config_path (str): Path to configuration file
        Returns:
            dict: Configuration dictionary
        """        
        try:
            with open(config_path, 'r') as config_file:
                config = json.load(config_file)
            return config
        except FileNotFoundError:
            self.logger.warning(f"Configuration file not found at {config_path}. Using default settings.")
            return None

    def _setup_logging(self):
        """Configure logging for the initializer"""
        # log directory if it doesn't exist
        logs_dir = Path(__file__).resolve().parent.parent / 'logs'
        logs_dir.mkdir(exist_ok=True)
        
        # logging configuration
        log_file = logs_dir / f'whp_init_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)

    def load_and_preprocess_data(self, input_file=None):
        """
        Load and preprocess the WHP dataset
        
        Args:
            input_file (str, optional): Specific input file path
        
        Returns:
            pd.DataFrame: Preprocessed DataFrame
        """
        # if no file is provided, find the most recent CSV
        if not input_file:
            import glob
            data_dir = Path(__file__).resolve().parent.parent / 'data' / 'raw'
            csv_files = glob.glob(str(data_dir / 'WHP_EarlyNahuatl_data_*.csv'))
            
            if not csv_files:
                self.logger.error("No input files found.")
                raise FileNotFoundError("No WHP data files found.")
            
            input_file = max(csv_files, key=os.path.getctime)
        
        # read the CSV
        df = pd.read_csv(input_file)
        
        # validate data integrity
        self._validate_data_integrity(df)
        
        # preprocess text columns
        text_columns = [
            "Ref", "Headword", "Orthographic Variants", 
            "Principal English Translation", "Attestations from sources in English",
            "Attestations from sources in Spanish", "Alonso de Molina", "Frances Karttunen",
            "Horacio Carochi / English", "Andrés de Olmos", "Lockhart’s Nahuatl as Written",
            "themes" , "Spanish Loanword"
        ]
        
        for col in text_columns:
            if col in df.columns:
                df[col] = df[col].apply(self._clean_text)
        
        return df

    def export_processed_data(self, df, output_filename=None):
        """
        Export processed data to CSV
        
        Args:
            df (pd.DataFrame): Processed DataFrame
            output_filename (str, optional): Custom output filename
        
        Returns:
            Path: Path to exported file
        """
        if output_filename is None:
            output_filename = f'processed_whp_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        
        # ensure processed directory exists
        processed_dir = Path(__file__).resolve().parent.parent / 'data' / 'processed'
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = processed_dir / output_filename
        
        try:
            df.to_csv(output_path, index=False, encoding='utf-8')
            self.logger.info(f"Processed data exported to {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error exporting processed data: {e}")
            raise
        
        
def main():
    """
    Main execution function for WHP data initialization
    """
    try:
        # init the WHP processing workflow
        initializer = WHPInitializer()
        
        # load and preprocess data
        df = initializer.load_and_preprocess_data()
        
        # export processed data
        initializer.export_processed_data(df)
        
        print("WHP Data Initialization Completed Successfully!")
    
    except Exception as e:
        print(f"Error in WHP Data Initialization: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()