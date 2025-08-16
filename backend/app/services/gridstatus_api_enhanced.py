"""
Enhanced GridStatus API Service with Round-Robin Key Rotation
Implements automatic key rotation to avoid rate limits
"""

import os
import asyncio
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging
import threading
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class ApiKeyStatus:
    """Track the status of each API key"""
    key: str
    last_used: Optional[float] = None
    rate_limited_until: Optional[float] = None
    request_count: int = 0
    success_count: int = 0
    failure_count: int = 0

class ApiKeyRotator:
    """Thread-safe round-robin API key rotation with intelligent retry"""
    
    def __init__(self, keys: List[str]):
        self.keys = [ApiKeyStatus(key=k) for k in keys]
        self.current_index = 0
        self.lock = threading.Lock()
        
        # Track rate limit windows (60 seconds for GridStatus)
        self.rate_limit_window_seconds = 60
        
    def get_next_key(self, skip_rate_limited: bool = True) -> Optional[str]:
        """Get the next available API key using round-robin"""
        with self.lock:
            attempts = 0
            keys_count = len(self.keys)
            current_time = time.time()
            
            while attempts < keys_count:
                key_status = self.keys[self.current_index]
                self.current_index = (self.current_index + 1) % keys_count
                attempts += 1
                
                # Skip rate-limited keys if requested
                if skip_rate_limited and key_status.rate_limited_until:
                    if current_time < key_status.rate_limited_until:
                        logger.debug(f"Skipping rate-limited key ...{key_status.key[-4:]}")
                        continue
                    else:
                        # Rate limit window has passed, reset
                        key_status.rate_limited_until = None
                
                key_status.last_used = current_time
                key_status.request_count += 1
                logger.debug(f"Using API key ...{key_status.key[-4:]} (request #{key_status.request_count})")
                return key_status.key
            
            # All keys are rate-limited
            logger.warning("All API keys are currently rate-limited")
            return None
    
    def mark_rate_limited(self, key: str):
        """Mark a key as rate-limited"""
        with self.lock:
            current_time = time.time()
            for key_status in self.keys:
                if key_status.key == key:
                    key_status.rate_limited_until = current_time + self.rate_limit_window_seconds
                    key_status.failure_count += 1
                    logger.info(f"Marked key ...{key[-4:]} as rate-limited for {self.rate_limit_window_seconds} seconds")
                    break
    
    def mark_success(self, key: str):
        """Mark a successful request for a key"""
        with self.lock:
            for key_status in self.keys:
                if key_status.key == key:
                    key_status.success_count += 1
                    break
    
    def get_status(self) -> Dict:
        """Get current status of all keys"""
        with self.lock:
            current_time = time.time()
            return {
                "total_keys": len(self.keys),
                "keys_status": [
                    {
                        "key_suffix": f"...{k.key[-4:]}",
                        "requests": k.request_count,
                        "successes": k.success_count,
                        "failures": k.failure_count,
                        "rate_limited": k.rate_limited_until is not None and current_time < k.rate_limited_until,
                        "seconds_until_available": max(0, k.rate_limited_until - current_time) if k.rate_limited_until else 0
                    }
                    for k in self.keys
                ]
            }

class GridStatusAPIServiceEnhanced:
    """Enhanced GridStatus API service with round-robin key rotation"""
    
    def __init__(self):
        # Load API keys from environment variable
        keys_str = os.getenv("GRIDSTATUS_API_KEYS", "")
        if not keys_str:
            # Fallback to single key for backward compatibility
            single_key = os.getenv("GRIDSTATUS_API_KEY", "")
            if single_key:
                keys_str = single_key
        
        # Parse comma-separated keys
        self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        
        if not self.api_keys:
            raise ValueError("No GridStatus API keys configured. Set GRIDSTATUS_API_KEYS in .env")
        
        logger.info(f"Initialized GridStatus API with {len(self.api_keys)} key(s)")
        
        # Initialize key rotator
        self.key_rotator = ApiKeyRotator(self.api_keys)
        
        # Base configuration
        self.base_url = os.getenv("GRIDSTATUS_BASE_URL", "https://api.gridstatus.io")
        
        # Rate limiting configuration
        self.min_interval = 1.2  # Slightly over 1 second to be safe
        self.max_retries = min(5, len(self.api_keys))  # Try each key once
        
        # Request tracking
        self._last_request_time: Optional[float] = None
        self._request_lock = asyncio.Lock()
        
        # ISO datasets configuration
        self.iso_datasets = self._get_iso_datasets()
    
    def _get_iso_datasets(self) -> Dict:
        """Get ISO dataset configurations"""
        return {
            "PJM": {
                "lmp_hourly_da": "pjm_lmp_day_ahead_hourly",
                "lmp_5min_rt": "pjm_lmp_real_time_5_min",
                "default_location": "PJM-RTO ZONE",
                "filter_candidates": ["location_name", "location", "pnode_name", "name"],
            },
            "CAISO": {
                "lmp_hourly_da": "caiso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "caiso_lmp_real_time_5_min",
                "default_location": "TH_NP15_GEN-APND",
                "filter_candidates": ["location_name", "location", "name"],
            },
            "ERCOT": {
                "lmp_hourly_da": "ercot_spp_day_ahead_hourly",
                "lmp_5min_rt": "ercot_spp_real_time_15_min",
                "default_location": "HB_HOUSTON",
                "filter_candidates": ["settlement_point", "location_name", "location", "name"],
            },
            "NYISO": {
                "lmp_hourly_da": "nyiso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "nyiso_lmp_real_time_5_min",
                "default_location": "N.Y.C.",
                "filter_candidates": ["location_name", "location", "name"],
            },
            "MISO": {
                "lmp_hourly_da": "miso_lmp_day_ahead_hourly",
                "lmp_5min_rt": "miso_lmp_real_time_5_min",
                "default_location": "HUB",
                "filter_candidates": ["location_name", "location", "name"],
            },
        }
    
    async def _make_request_with_retry(
        self, 
        url: str, 
        params: Dict,
        timeout: float = 30.0
    ) -> Optional[Dict]:
        """Make HTTP request with automatic key rotation on rate limit"""
        
        async with self._request_lock:
            # Enforce minimum interval between requests
            current_time = time.time()
            if self._last_request_time:
                elapsed = current_time - self._last_request_time
                if elapsed < self.min_interval:
                    await asyncio.sleep(self.min_interval - elapsed)
            
            for attempt in range(self.max_retries):
                # Get next available API key
                api_key = self.key_rotator.get_next_key(skip_rate_limited=True)
                
                if not api_key:
                    # All keys are rate-limited, wait and try again
                    logger.warning(f"All {len(self.api_keys)} keys rate-limited. Waiting 30 seconds...")
                    await asyncio.sleep(30)
                    api_key = self.key_rotator.get_next_key(skip_rate_limited=False)
                    
                    if not api_key:
                        raise Exception("No API keys available after waiting")
                
                headers = {
                    "x-api-key": api_key,
                    "accept": "application/json"
                }
                
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        logger.debug(f"Attempt {attempt + 1}/{self.max_retries}: Using key ...{api_key[-4:]}")
                        response = await client.get(url, params=params, headers=headers)
                        
                        self._last_request_time = time.time()
                        
                        if response.status_code == 200:
                            # Success!
                            self.key_rotator.mark_success(api_key)
                            data = response.json()
                            logger.debug(f"Successfully fetched data with key ...{api_key[-4:]}")
                            return data
                        
                        elif response.status_code == 429:
                            # Rate limited - mark this key and try next
                            logger.warning(f"Rate limit (429) for key ...{api_key[-4:]}")
                            self.key_rotator.mark_rate_limited(api_key)
                            
                            if attempt < self.max_retries - 1:
                                # Small delay before trying next key
                                await asyncio.sleep(1)
                                continue
                        
                        elif response.status_code == 400:
                            # Bad request - don't retry with different keys
                            logger.error(f"Bad request (400): {response.text[:200]}")
                            return None
                        
                        else:
                            logger.error(f"API error {response.status_code}: {response.text[:200]}")
                            
                except httpx.TimeoutException:
                    logger.error(f"Request timeout for key ...{api_key[-4:]}")
                except Exception as e:
                    logger.error(f"Request failed: {str(e)}")
        
        logger.error(f"All {self.max_retries} attempts failed")
        return None
    
    async def fetch_day_ahead_prices(
        self, 
        node: str, 
        date: datetime
    ) -> List[Dict]:
        """Fetch day-ahead prices with automatic key rotation"""
        
        iso = self._get_iso_from_node(node)
        dataset = self.iso_datasets[iso]["lmp_hourly_da"]
        
        # Format date range
        start_time = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        params = {
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
            "timezone": "market",
            "limit": 1000
        }
        
        # Add location filter
        location = self._normalize_node(iso, node)
        if location:
            params["filter_column"] = "location_name"
            params["filter_value"] = location
        
        url = f"{self.base_url}/v1/datasets/{dataset}/query"
        
        logger.info(f"Fetching DA prices for {node} on {date.date()}")
        result = await self._make_request_with_retry(url, params)
        
        if result and "data" in result:
            processed = self._process_da_data(result["data"], node)
            logger.info(f"Retrieved {len(processed)} DA prices")
            return processed
        
        logger.warning(f"No DA data returned for {node} on {date.date()}")
        return []
    
    async def fetch_real_time_prices(
        self, 
        node: str, 
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        """Fetch real-time prices with automatic key rotation"""
        
        iso = self._get_iso_from_node(node)
        dataset = self.iso_datasets[iso]["lmp_5min_rt"]
        
        params = {
            "start_time": start_time.isoformat() + "Z",
            "end_time": end_time.isoformat() + "Z",
            "timezone": "market",
            "limit": 5000
        }
        
        # Add location filter
        location = self._normalize_node(iso, node)
        if location:
            params["filter_column"] = "location_name"
            params["filter_value"] = location
        
        url = f"{self.base_url}/v1/datasets/{dataset}/query"
        
        logger.info(f"Fetching RT prices for {node} from {start_time} to {end_time}")
        result = await self._make_request_with_retry(url, params)
        
        if result and "data" in result:
            processed = self._process_rt_data(result["data"], node)
            logger.info(f"Retrieved {len(processed)} RT prices")
            return processed
        
        logger.warning(f"No RT data returned for {node}")
        return []
    
    def get_rotation_status(self) -> Dict:
        """Get current API key rotation status"""
        return self.key_rotator.get_status()
    
    # Helper methods
    def _get_iso_from_node(self, node: str) -> str:
        """Determine ISO from node name"""
        u = (node or "").upper()
        if u.startswith("PJM") or "RTO" in u: return "PJM"
        if u.startswith("CAISO") or u.startswith("TH_") or "GEN-APND" in u: return "CAISO"
        if u.startswith("ERCOT") or u.startswith("HB_"): return "ERCOT"
        if u.startswith("NYISO") or "N.Y.C." in u: return "NYISO"
        if u.startswith("MISO"): return "MISO"
        logger.warning(f"Unknown node '{node}', defaulting to PJM")
        return "PJM"
    
    def _normalize_node(self, iso: str, node: str) -> str:
        """Normalize node name for the specific ISO"""
        u = (node or "").upper().replace(" ", "").replace("_", "").replace("-", "")
        
        if iso == "PJM":
            if u in {"PJMRTO", "PJMRTOZONE", "PJMRT0"}: 
                return "PJM-RTO ZONE"
            # Try variations
            if "RTO" in u:
                return "PJM-RTO ZONE"
        elif iso == "CAISO":
            if u in {"NP15", "THNP15GENAPND"}: 
                return "TH_NP15_GEN-APND"
        elif iso == "ERCOT":
            if u in {"HBHOUSTON", "HOUSTON"}: 
                return "HB_HOUSTON"
        
        return node
    
    def _process_da_data(self, data: List[Dict], node: str) -> List[Dict]:
        """Process day-ahead data"""
        processed = []
        for item in data:
            processed.append({
                "node": node,
                "hour_start": item.get("hour_start", item.get("interval_start")),
                "price": float(item.get("lmp", 0)),
                "close_price": float(item.get("lmp", 0))
            })
        return processed
    
    def _process_rt_data(self, data: List[Dict], node: str) -> List[Dict]:
        """Process real-time data"""
        processed = []
        for item in data:
            processed.append({
                "node": node,
                "timestamp": item.get("interval_start"),
                "price": float(item.get("lmp", 0))
            })
        return processed
