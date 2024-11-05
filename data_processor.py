import pandas as pd
import os
from typing import List, Dict
import re
import logging
import redis
from cachetools import TTLCache
import json
import math
from typing import Optional
import io

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points using Haversine formula"""
    R = 3959.87433  # Earth's radius in miles

    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

class DataProcessor:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.data_files = {}
        self.summary_files = {}
        
        # Initialize Redis connection
        try:
            self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
            self.redis_client.ping()  # Test connection
            logger.info("Redis connection established successfully")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache fallback.")
            self.redis_client = None
        
        # Fallback in-memory cache with 1-hour TTL
        self.memory_cache = TTLCache(maxsize=100, ttl=3600)
        
        self.load_data()

    def _get_cache_key(self, prefix: str, *args) -> str:
        """Generate a cache key from prefix and arguments"""
        return f"{prefix}:{':'.join(str(arg) for arg in args)}"

    def _get_from_cache(self, key: str):
        """Try to get value from Redis, fallback to memory cache"""
        if self.redis_client:
            try:
                cached_value = self.redis_client.get(key)
                if cached_value:
                    return json.loads(cached_value)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        return self.memory_cache.get(key)

    def _set_in_cache(self, key: str, value, ttl: int = 3600):
        """Try to set value in Redis, fallback to memory cache"""
        try:
            if self.redis_client:
                self.redis_client.setex(key, ttl, json.dumps(value))
            self.memory_cache[key] = value
        except Exception as e:
            logger.warning(f"Cache set failed: {e}")

    def _parse_insurance_info(self, filename: str) -> Optional[Dict[str, str]]:
        """Parse insurance and type from filename"""
        data_pattern = r"Austin_(.+?)_data\.csv"
        summary_pattern = r"summary_Austin_(.+?)\.csv"
        
        data_match = re.match(data_pattern, filename)
        summary_match = re.match(summary_pattern, filename)
        
        if data_match:
            insurance_full = data_match.group(1)
            logger.info(f"Parsed data file: {filename} -> insurance: {insurance_full}")
            return {
                "insurance": insurance_full,
                "type": "",
                "is_summary": False
            }
        elif summary_match:
            insurance_full = summary_match.group(1)
            logger.info(f"Parsed summary file: {filename} -> insurance: {insurance_full}")
            return {
                "insurance": insurance_full,
                "type": "",
                "is_summary": True
            }
        logger.warning(f"Could not parse filename: {filename}")
        return None

    def load_data(self):
        """Load all CSV files into memory with caching"""
        if not os.path.exists(self.data_dir):
            logger.warning(f"Data directory not found at {self.data_dir}")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_data_dirs = [
                os.path.join(current_dir, 'static', 'data'),
                os.path.join(current_dir, 'data'),
                os.path.join(os.path.dirname(current_dir), 'static', 'data'),
                os.path.join(os.path.dirname(current_dir), 'data')
            ]
            
            for dir_path in possible_data_dirs:
                if os.path.exists(dir_path):
                    self.data_dir = dir_path
                    logger.info(f"Found data directory at: {dir_path}")
                    break
            else:
                logger.error("Could not find data directory")
                return

        logger.info(f"Loading data from directory: {self.data_dir}")
        
        # Try to get cached file list
        cache_key = self._get_cache_key("file_list", self.data_dir)
        cached_files = self._get_from_cache(cache_key)
        
        if cached_files:
            logger.info("Using cached file list")
            self.data_files = {k: pd.DataFrame(v) for k, v in cached_files.get("data_files", {}).items()}
            self.summary_files = {k: pd.DataFrame(v) for k, v in cached_files.get("summary_files", {}).items()}
            return

        for filename in os.listdir(self.data_dir):
            if not filename.endswith('.csv'):
                continue
                
            filepath = os.path.join(self.data_dir, filename)
            file_info = self._parse_insurance_info(filename)
            
            if not file_info:
                logger.warning(f"Skipping file with invalid naming pattern: {filename}")
                continue
                
            try:
                df = pd.read_csv(filepath, low_memory=False)
                
                if file_info["is_summary"]:
                    self.summary_files[filename] = df
                    logger.info(f"Loaded summary file: {filename}")
                else:
                    self.data_files[filename] = df
                    logger.info(f"Loaded data file: {filename}")
                
                # Cache individual file data
                file_cache_key = self._get_cache_key("file_data", filename)
                self._set_in_cache(file_cache_key, df.to_dict())
                
            except Exception as e:
                logger.error(f"Error loading {filename}: {str(e)}")

        # Cache file list
        file_list = {
            "data_files": {k: v.to_dict() for k, v in self.data_files.items()},
            "summary_files": {k: v.to_dict() for k, v in self.summary_files.items()}
        }
        self._set_in_cache(cache_key, file_list)
        
        logger.info(f"Loaded {len(self.data_files)} data files and {len(self.summary_files)} summary files")

    def get_insurance_plans(self) -> List[Dict[str, str]]:
        """Get list of available insurance plans with caching"""
        cache_key = self._get_cache_key("insurance_plans")
        cached_plans = self._get_from_cache(cache_key)
        
        if cached_plans:
            return cached_plans
            
        if not self.data_files:
            logger.warning("No data files loaded")
            return []
        
        plans = set()
        for filename in self.data_files.keys():
            file_info = self._parse_insurance_info(filename)
            if file_info:
                plans.add((file_info["insurance"], file_info["type"]))
        
        result = [{"insurance": ins, "type": typ} for ins, typ in sorted(plans)]
        self._set_in_cache(cache_key, result)
        return result

    def search_procedures(self, insurance_plan: str, insurance_type: str, search_term: str) -> List[Dict]:
        """Search procedures by term with caching"""
        if not search_term.strip():
            return []
            
        cache_key = self._get_cache_key("procedures", insurance_plan, search_term)
        cached_procedures = self._get_from_cache(cache_key)
        
        if cached_procedures:
            return cached_procedures
            
        filename = f"Austin_{insurance_plan}_data.csv"
        if filename not in self.data_files:
            logger.warning(f"Data file not found: {filename}")
            return []
            
        df = self.data_files[filename]
        
        try:
            filtered = df[
                (df['procedure_name'].str.contains(search_term, case=False, na=False)) |
                (df['billing_code'].str.contains(search_term, case=False, na=False))
            ]
            
            unique_procedures = filtered[['procedure_name', 'billing_code']].drop_duplicates()
            result = unique_procedures.to_dict('records')
            
            self._set_in_cache(cache_key, result)
            return result
            
        except Exception as e:
            logger.error(f"Error searching procedures: {str(e)}")
            return []

    def get_search_results(self, insurance_plan: str, insurance_type: str = '', procedure: str = None, 
                          zipcode: str = None, sort_by: str = 'price', provider: str = None,
                          min_price: float = None, max_price: float = None, distance: int = None) -> Dict:
        """Get search results for a procedure with advanced filtering options"""
        cache_key = self._get_cache_key(
            "search_results", insurance_plan, procedure, zipcode, sort_by,
            provider, min_price, max_price, distance
        )
        cached_results = self._get_from_cache(cache_key)
        
        if cached_results:
            return cached_results
            
        filename = f"Austin_{insurance_plan}_data.csv"
        if filename not in self.data_files:
            logger.warning(f"Data file not found: {filename}")
            return {"error": f"No data available for {insurance_plan}", "results": []}
            
        df = self.data_files[filename]
        
        try:
            results = df[df['procedure_name'] == procedure].copy()
        except Exception as e:
            logger.error(f"Error filtering results: {str(e)}")
            return {"error": f"Error filtering results: {str(e)}", "results": []}
        
        if results.empty:
            return {"error": "No results found for this procedure", "results": []}

        # Apply provider filter
        if provider:
            results = results[
                results['Provider Organization Name (Legal Business Name)']
                .str.contains(provider, case=False, na=False)
            ]

        # Apply price range filters
        if min_price is not None:
            results = results[results['negotiated_rate'] >= float(min_price)]
        if max_price is not None:
            results = results[results['negotiated_rate'] <= float(max_price)]

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
            logger.error(f"Error selecting columns: {str(e)}")
            return {"error": f"Error selecting columns: {str(e)}", "results": []}
        
        # Handle sorting and distance calculations
        if zipcode:
            try:
                results['zip_distance'] = abs(
                    results['Provider Business Practice Location Address Postal Code']
                    .astype(str).str[:5].astype(int) - int(zipcode)
                )
                
                if distance:
                    # Filter by distance range (approximate using ZIP code difference)
                    max_zip_diff = int(distance * 0.2)  # Rough approximation
                    results = results[results['zip_distance'] <= max_zip_diff]
                
                if sort_by == 'proximity':
                    results = results.sort_values('zip_distance')
            except (ValueError, TypeError) as e:
                logger.error(f"Error calculating zip distances: {str(e)}")
                if sort_by == 'proximity':
                    sort_by = 'price'  # Fallback to price sorting

        if sort_by == 'price' or not zipcode:
            results = results.sort_values('negotiated_rate')
        
        result = {"error": None, "results": results.to_dict('records')}
        self._set_in_cache(cache_key, result)
        return result

    def get_stats_data(self, procedure: str) -> Dict:
        """Get statistics data for a procedure with caching"""
        cache_key = self._get_cache_key("stats_data", procedure)
        cached_stats = self._get_from_cache(cache_key)
        
        if cached_stats:
            return cached_stats
            
        if not self.summary_files:
            logger.warning("No summary files loaded")
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
                    plan_key = file_info['insurance']
                    stats_data[plan_key] = {
                        'min': procedure_stats['min'].iloc[0],
                        'Q1': procedure_stats['Q1'].iloc[0],
                        'median': procedure_stats['median'].iloc[0],
                        'Q3': procedure_stats['Q3'].iloc[0],
                        'max': procedure_stats['max'].iloc[0]
                    }
            except Exception as e:
                logger.error(f"Error processing stats for {filename}: {str(e)}")
                continue
        
        if not found_data:
            return {"error": "No statistics available for this procedure"}
            
        self._set_in_cache(cache_key, stats_data)
        return stats_data

    def export_search_results(self, results: Dict) -> str:
        """Export search results to CSV format"""
        if results.get("error") or not results.get("results"):
            return ""
            
        df = pd.DataFrame(results["results"])
        
        # Rename columns for better readability
        column_mapping = {
            'negotiated_rate': 'Price',
            'Provider Organization Name (Legal Business Name)': 'Provider Name',
            'npi': 'NPI',
            'Provider First Line Business Practice Location Address': 'Address Line 1',
            'Provider Second Line Business Practice Location Address': 'Address Line 2',
            'Provider Business Practice Location Address City Name': 'City',
            'Provider Business Practice Location Address State Name': 'State',
            'Provider Business Practice Location Address Postal Code': 'ZIP Code'
        }
        df = df.rename(columns=column_mapping)
        
        # Format price column
        df['Price'] = df['Price'].apply(lambda x: f"${x:.2f}")
        
        # Format ZIP code
        df['ZIP Code'] = df['ZIP Code'].astype(str).str[:5]
        
        # Remove empty columns
        df = df.replace('', pd.NA).dropna(axis=1, how='all')
        
        # Convert to CSV string
        output = io.StringIO()
        df.to_csv(output, index=False)
        return output.getvalue()
