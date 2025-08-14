#!/usr/bin/env python3
"""
Simple script to get GridStatus dataset IDs
Run this with: python get_datasets.py
"""

import requests

# Your API key
API_KEY = "6574119a04954abd93469f85194e07a0"

# Fetch datasets
url = f"https://api.gridstatus.io/v1/datasets?api_key={API_KEY}"
print(f"Fetching from: {url}\n")

try:
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    
    print("=" * 60)
    print("ALL DATASET IDs FROM GRIDSTATUS:")
    print("=" * 60)
    
    all_ids = []
    for item in data.get("data", []):
        if "id" in item:
            print(item["id"])
            all_ids.append(item["id"])
    
    print("\n" + "=" * 60)
    print("LMP DATASETS (for energy trading):")
    print("=" * 60)
    
    # Filter for LMP datasets
    for dataset_id in sorted(all_ids):
        lower = dataset_id.lower()
        if "lmp" in lower or ("ercot" in lower and "spp" in lower):
            # Determine type
            if "pjm" in lower:
                iso = "PJM"
            elif "caiso" in lower:
                iso = "CAISO"  
            elif "ercot" in lower:
                iso = "ERCOT"
            elif "nyiso" in lower:
                iso = "NYISO"
            elif "miso" in lower:
                iso = "MISO"
            elif "spp" in lower:
                iso = "SPP"
            elif "isone" in lower or "iso_ne" in lower:
                iso = "ISO-NE"
            else:
                iso = "OTHER"
            
            # Determine market type
            if "day_ahead" in lower or "_da" in lower:
                market = "Day-Ahead"
            elif "real_time" in lower or "_rt" in lower or "5_min" in lower:
                market = "Real-Time"
            else:
                market = "Unknown"
            
            print(f"{iso:8} | {market:12} | {dataset_id}")
    
    print("\n" + "=" * 60)
    print("Copy these exact IDs to update gridstatus_api.py")
    print("=" * 60)
    
except Exception as e:
    print(f"Error: {e}")
    print("\nPlease run this script directly:")
    print("cd backend")
    print("python scripts/get_datasets.py")
