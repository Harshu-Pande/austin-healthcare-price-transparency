import pandas as pd
import os
from typing import List, Dict
import re

class DataProcessor:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.data_files = {}
        self.summary_files = {}
        self.load_data()

    def _parse_insurance_info(self, filename: str) -> Dict[str, str]:
        """Parse insurance and type from filename"""
        # For data files: Austin_[Insurance]_[Type]_data.csv
        # For summary files: summary_Austin_[Insurance]_[Type].csv
        data_pattern = r"Austin_([^_]+)_([^_]+)_data\.csv"
        summary_pattern = r"summary_Austin_([^_]+)_([^_]+)\.csv"
        
        data_match = re.match(data_pattern, filename)
        summary_match = re.match(summary_pattern, filename)
        
        if data_match:
            return {
                "insurance": data_match.group(1),
                "type": data_match.group(2),
                "is_summary": False
            }
        elif summary_match:
            return {
                "insurance": summary_match.group(1),
                "type": summary_match.group(2),
                "is_summary": True
            }
        return None

    def load_data(self):
        """Load all CSV files into memory"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            return

        for filename in os.listdir(self.data_dir):
            if not filename.endswith('.csv'):
                continue
                
            filepath = os.path.join(self.data_dir, filename)
            file_info = self._parse_insurance_info(filename)
            
            if not file_info:
                print(f"Warning: Skipping file with invalid naming pattern: {filename}")
                continue
                
            try:
                if file_info["is_summary"]:
                    self.summary_files[filename] = pd.read_csv(filepath)
                else:
                    self.data_files[filename] = pd.read_csv(filepath)
            except Exception as e:
                print(f"Error loading {filename}: {str(e)}")

    def get_insurance_plans(self) -> List[Dict[str, str]]:
        """Get list of available insurance plans with their types"""
        if not self.data_files:
            return []
        
        plans = set()
        for filename in self.data_files.keys():
            file_info = self._parse_insurance_info(filename)
            if file_info:
                plans.add((file_info["insurance"], file_info["type"]))
                
        return [{"insurance": ins, "type": typ} for ins, typ in sorted(plans)]

    def search_procedures(self, insurance_plan: str, insurance_type: str, search_term: str) -> List[Dict]:
        """Search procedures by term"""
        filename = f"Austin_{insurance_plan}_{insurance_type}_data.csv"
        if filename not in self.data_files:
            return []
            
        df = self.data_files[filename]
        
        if search_term.strip() == "":
            return []
            
        try:
            filtered = df[
                (df['procedure_name'].str.contains(search_term, case=False, na=False)) |
                (df['billing_code'].str.contains(search_term, case=False, na=False))
            ]
        except Exception as e:
            print(f"Error searching procedures: {str(e)}")
            return []
        
        unique_procedures = filtered[['procedure_name', 'billing_code']].drop_duplicates()
        return unique_procedures.to_dict('records')

    def get_search_results(self, insurance_plan: str, insurance_type: str, procedure: str, zipcode: str, sort_by: str) -> Dict:
        """Get search results for a procedure"""
        filename = f"Austin_{insurance_plan}_{insurance_type}_data.csv"
        if filename not in self.data_files:
            return {"error": f"No data available for {insurance_plan} {insurance_type}", "results": []}
            
        df = self.data_files[filename]
        
        try:
            results = df[df['procedure_name'] == procedure].copy()
        except Exception as e:
            return {"error": f"Error filtering results: {str(e)}", "results": []}
        
        if results.empty:
            return {"error": "No results found for this procedure", "results": []}

        # Select relevant columns
        columns = [
            'negotiated_rate',
            'Provider Organization Name (Legal Business Name)',
            'npi',
            'Provider First Line Business Practice Location Address',
            'Provider Second Line Business Practice Location Address',
            'Provider Business Practice Location Address City Name',
            'Provider Business Practice Location Address State Name',
            'Provider Business Practice Location Address Postal Code'
        ]
        
        try:
            results = results[columns].copy()
        except Exception as e:
            return {"error": f"Error selecting columns: {str(e)}", "results": []}
        
        if sort_by == 'price':
            results = results.sort_values('negotiated_rate')
        elif sort_by == 'proximity' and zipcode:
            try:
                results['zip_distance'] = abs(
                    results['Provider Business Practice Location Address Postal Code']
                    .astype(str).str[:5].astype(int) - int(zipcode)
                )
                results = results.sort_values('zip_distance')
            except (ValueError, TypeError):
                # If there's an error converting zip codes, fall back to price sorting
                results = results.sort_values('negotiated_rate')
        
        return {"error": None, "results": results.to_dict('records')}

    def get_stats_data(self, procedure: str) -> Dict:
        """Get statistics data for a procedure"""
        if not self.summary_files:
            return {"error": "No statistics data available"}
            
        stats_data = {}
        found_data = False
        
        for filename, df in self.summary_files.items():
            file_info = self._parse_insurance_info(filename)
            if not file_info:
                continue
                
            try:
                procedure_stats = df[df['procedure_name'] == procedure]
                
                if not procedure_stats.empty:
                    found_data = True
                    plan_key = f"{file_info['insurance']} {file_info['type']}"
                    stats_data[plan_key] = {
                        'min': procedure_stats['min'].iloc[0],
                        'Q1': procedure_stats['Q1'].iloc[0],
                        'median': procedure_stats['median'].iloc[0],
                        'Q3': procedure_stats['Q3'].iloc[0],
                        'max': procedure_stats['max'].iloc[0]
                    }
            except Exception as e:
                print(f"Error processing stats for {filename}: {str(e)}")
                continue
        
        if not found_data:
            return {"error": "No statistics available for this procedure"}
            
        return {"error": None, "data": stats_data}
