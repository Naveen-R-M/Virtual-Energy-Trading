#!/usr/bin/env python3
"""
Fetch all available dataset IDs from GridStatus API
"""

import requests
import json

API_KEY = "6574119a04954abd93469f85194e07a0"

def get_dataset_ids():
    """Fetch all dataset IDs from GridStatus"""
    url = f"https://api.gridstatus.io/v1/datasets?api_key={API_KEY}"
    
    print("Fetching GridStatus dataset IDs...")
    print("=" * 60)
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        all_datasets = []
        iso_datasets = {
            "PJM": [],
            "CAISO": [],
            "ERCOT": [],
            "NYISO": [],
            "MISO": [],
            "SPP": [],
            "ISONE": []
        }
        
        print("\nAll Available Dataset IDs:")
        print("-" * 60)
        
        for item in data.get("data", []):
            if "id" in item:
                dataset_id = item["id"]
                print(dataset_id)
                all_datasets.append(dataset_id)
                
                # Categorize by ISO
                for iso in iso_datasets.keys():
                    if iso.lower() in dataset_id.lower():
                        iso_datasets[iso].append(dataset_id)
        
        print("\n" + "=" * 60)
        print("Categorized by ISO:")
        print("=" * 60)
        
        for iso, datasets in iso_datasets.items():
            if datasets:
                print(f"\n{iso}:")
                print("-" * 30)
                for ds in sorted(datasets):
                    # Highlight LMP datasets
                    if "lmp" in ds.lower():
                        if "day_ahead" in ds or "da" in ds:
                            print(f"  📅 {ds} (Day-Ahead)")
                        elif "real_time" in ds or "rt" in ds or "5_min" in ds:
                            print(f"  ⚡ {ds} (Real-Time)")
                        else:
                            print(f"  📊 {ds}")
                    else:
                        print(f"  - {ds}")
        
        # Find the correct LMP dataset names
        print("\n" + "=" * 60)
        print("Recommended LMP Datasets for Trading:")
        print("=" * 60)
        
        recommendations = {
            "PJM": {
                "day_ahead": None,
                "real_time": None
            },
            "CAISO": {
                "day_ahead": None,
                "real_time": None
            },
            "ERCOT": {
                "day_ahead": None,
                "real_time": None
            },
            "NYISO": {
                "day_ahead": None,
                "real_time": None
            },
            "MISO": {
                "day_ahead": None,
                "real_time": None
            }
        }
        
        for dataset_id in all_datasets:
            lower_id = dataset_id.lower()
            
            # PJM
            if "pjm" in lower_id and "lmp" in lower_id:
                if "day_ahead" in lower_id or "_da_" in lower_id:
                    recommendations["PJM"]["day_ahead"] = dataset_id
                elif "real_time" in lower_id or "_rt_" in lower_id or "5_min" in lower_id:
                    recommendations["PJM"]["real_time"] = dataset_id
            
            # CAISO
            if "caiso" in lower_id and "lmp" in lower_id:
                if "day_ahead" in lower_id or "_da_" in lower_id:
                    recommendations["CAISO"]["day_ahead"] = dataset_id
                elif "real_time" in lower_id or "_rt_" in lower_id or "5_min" in lower_id:
                    recommendations["CAISO"]["real_time"] = dataset_id
            
            # ERCOT
            if "ercot" in lower_id and ("lmp" in lower_id or "spp" in lower_id):
                if "day_ahead" in lower_id or "_da_" in lower_id:
                    recommendations["ERCOT"]["day_ahead"] = dataset_id
                elif "real_time" in lower_id or "_rt_" in lower_id or "5_min" in lower_id:
                    recommendations["ERCOT"]["real_time"] = dataset_id
            
            # NYISO
            if "nyiso" in lower_id and "lmp" in lower_id:
                if "day_ahead" in lower_id or "_da_" in lower_id:
                    recommendations["NYISO"]["day_ahead"] = dataset_id
                elif "real_time" in lower_id or "_rt_" in lower_id or "5_min" in lower_id:
                    recommendations["NYISO"]["real_time"] = dataset_id
            
            # MISO
            if "miso" in lower_id and "lmp" in lower_id:
                if "day_ahead" in lower_id or "_da_" in lower_id:
                    recommendations["MISO"]["day_ahead"] = dataset_id
                elif "real_time" in lower_id or "_rt_" in lower_id or "5_min" in lower_id:
                    recommendations["MISO"]["real_time"] = dataset_id
        
        print("\nRecommended dataset mappings for gridstatus_api.py:")
        print("-" * 60)
        
        for iso, datasets in recommendations.items():
            if datasets["day_ahead"] or datasets["real_time"]:
                print(f'\n"{iso}": {{')
                if datasets["day_ahead"]:
                    print(f'    "lmp_hourly_da": "{datasets["day_ahead"]}",')
                if datasets["real_time"]:
                    print(f'    "lmp_5min_rt": "{datasets["real_time"]}",')
                print(f'    "default_location": "...",')
                print(f'    "location_column": "location_name"')
                print(f'}}')
        
        # Save to file for reference
        output_file = "gridstatus_datasets.json"
        with open(output_file, "w") as f:
            json.dump({
                "all_datasets": all_datasets,
                "categorized": iso_datasets,
                "recommendations": recommendations
            }, f, indent=2)
        
        print(f"\n✅ Dataset information saved to {output_file}")
        
        return all_datasets
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching datasets: {e}")
        return []

if __name__ == "__main__":
    datasets = get_dataset_ids()
    print(f"\n📊 Total datasets found: {len(datasets)}")
