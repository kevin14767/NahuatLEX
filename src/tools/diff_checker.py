#!/usr/bin/env python3
"""
diff_checker.py - Compare two CSV/Excel files based on specified columns

This script helps NahuatLEX contributors identify differences between versions
of lexical data files by comparing specified columns in two data files.
"""

import argparse
import sys
import pandas as pd
import json
from pathlib import Path
import numpy as np


def load_file(file_path):
    """Load a CSV or Excel file into a pandas DataFrame."""
    file_path = Path(file_path)
    
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        return pd.read_excel(file_path)
    elif file_path.suffix.lower() == '.csv':
        return pd.read_csv(file_path, low_memory=False)
    else:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")


def load_config(config_path):
    """Load the configuration file specifying which columns to compare."""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_files(file1_path, file2_path, config_path, output_path=None):
    """Compare two files based on the columns specified in config."""
    try:
        df1 = load_file(file1_path)
        df2 = load_file(file2_path)
        config = load_config(config_path)
    except Exception as e:
        print(f"Error loading files: {e}")
        return False
    
    # get columns to compare
    columns_to_compare = config.get("columns_to_compare", [])
    id_column = config.get("id_column", None)
    
    if not columns_to_compare:
        print("No columns specified for comparison in config file")
        return False
    
    # verify all specified columns exist in both files
    for col in columns_to_compare + ([id_column] if id_column else []):
        if col not in df1.columns or col not in df2.columns:
            print(f"Column '{col}' not found in one or both files")
            return False
    
    # check that id_column is specified
    if not id_column:
        print("No ID column specified in config file")
        return False
    
    # extract all unique reference IDs from both files
    refs_file1 = set(df1[id_column])
    refs_file2 = set(df2[id_column])
    
    in_df1_not_df2 = refs_file1.difference(refs_file2)
    in_df2_not_df1 = refs_file2.difference(refs_file1)
    
    # for common entries, find differences in the specified columns
    common_refs = refs_file1.intersection(refs_file2)
    differences = {}
    
    for ref in common_refs:
        # get rows from both dataframes with matching reference
        rows_df1 = df1[df1[id_column] == ref]
        rows_df2 = df2[df2[id_column] == ref]
        
        # compare each column in these rows
        entry_diffs = {}
        
        # first check if the number of rows with this reference differs
        if len(rows_df1) != len(rows_df2):
            entry_diffs["row_count"] = {
                "old": len(rows_df1),
                "new": len(rows_df2)
            }
        
        # for each column, compare values
        for col in columns_to_compare:
            vals1 = rows_df1[col].tolist()
            vals2 = rows_df2[col].tolist()
            
            # convert values to string for proper comparison (might not be the best but who knows)
            vals1 = [str(val) if not pd.isna(val) else "NA" for val in vals1]
            vals2 = [str(val) if not pd.isna(val) else "NA" for val in vals2]
            
            # compare values
            if vals1 != vals2:
                entry_diffs[col] = {
                    "old": vals1,
                    "new": vals2
                }
        
        if entry_diffs:
            differences[ref] = entry_diffs
    
    results = {
        "entries_only_in_file1": sorted(list(in_df1_not_df2)),
        "entries_only_in_file2": sorted(list(in_df2_not_df1)),
        "modified_entries": differences
    }
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"Diff results saved to {output_path}")
    else:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    
    print("\nSummary:")
    print(f"Entries only in first file: {len(in_df1_not_df2)}")
    print(f"Entries only in second file: {len(in_df2_not_df1)}")
    print(f"Modified entries: {len(differences)}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Compare two CSV/Excel files.")
    parser.add_argument("file1", help="Path to the first file")
    parser.add_argument("file2", help="Path to the second file")
    parser.add_argument("config", help="Path to the config file specifying columns to compare")
    parser.add_argument("-o", "--output", help="Output path for the diff results")
    
    args = parser.parse_args()
    
    if not compare_files(args.file1, args.file2, args.config, args.output):
        sys.exit(1)


if __name__ == "__main__":
    main()