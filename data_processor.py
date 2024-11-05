import pandas as pd
import os
from typing import List, Dict
import numpy as np

class DataProcessor:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.data_files = {}
        self.summary_files = {}
        self.load_data()

    def load_data(self):
        """Load all CSV files into memory"""
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.csv'):
                if filename.startswith('summary_'):
                    self.summary_files[filename] = pd.read_csv(os.path.join(self.data_dir, filename))
                else:
                    self.data_files[filename] = pd.read_csv(os.path.join(self.data_dir, filename))

    def get_insurance_plans(self) -> List[str]:
        """Get list of available insurance plans"""
        plans = []
        for filename in self.data_files.keys():
            plan = filename.split('_')[1]  # Extract plan name from filename
            plans.append(plan)
        return sorted(list(set(plans)))

    def search_procedures(self, insurance_plan: str, search_term: str) -> List[Dict]:
        """Search procedures by term"""
        filename = f"Austin_{insurance_plan}_OAP_data.csv"
        df = self.data_files[filename]
        
        filtered = df[
            (df['procedure_name'].str.contains(search_term, case=False, na=False)) |
            (df['billing_code'].str.contains(search_term, case=False, na=False))
        ]
        
        unique_procedures = filtered[['procedure_name', 'billing_code']].drop_duplicates()
        return unique_procedures.to_dict('records')

    def get_search_results(self, insurance_plan: str, procedure: str, zipcode: str, sort_by: str) -> List[Dict]:
        """Get search results for a procedure"""
        filename = f"Austin_{insurance_plan}_OAP_data.csv"
        df = self.data_files[filename]
        
        results = df[df['procedure_name'] == procedure].copy()
        
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
        
        results = results[columns].copy()
        
        if sort_by == 'price':
            results = results.sort_values('negotiated_rate')
        elif sort_by == 'proximity' and zipcode:
            results['zip_distance'] = abs(
                results['Provider Business Practice Location Address Postal Code']
                .astype(str).str[:5].astype(int) - int(zipcode)
            )
            results = results.sort_values('zip_distance')
        
        return results.to_dict('records')

    def get_stats_data(self, procedure: str) -> Dict:
        """Get statistics data for a procedure"""
        stats_data = {}
        
        for filename, df in self.summary_files.items():
            plan = filename.split('_')[2]  # Extract plan name
            procedure_stats = df[df['procedure_name'] == procedure]
            
            if not procedure_stats.empty:
                stats_data[plan] = {
                    'min': procedure_stats['min'].iloc[0],
                    'Q1': procedure_stats['Q1'].iloc[0],
                    'median': procedure_stats['median'].iloc[0],
                    'Q3': procedure_stats['Q3'].iloc[0],
                    'max': procedure_stats['max'].iloc[0]
                }
        
        return stats_data
