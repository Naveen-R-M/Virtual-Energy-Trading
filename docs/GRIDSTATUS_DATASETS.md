# 📊 GridStatus Dataset Configuration Guide

## Getting the Correct Dataset IDs

To get the exact dataset IDs from GridStatus API, run this command:

```bash
# Option 1: Using Docker
docker-compose exec backend python scripts/get_datasets.py

# Option 2: Using local Python
cd backend
python scripts/get_datasets.py
```

This will fetch and display all available dataset IDs from GridStatus.

## Manual Check via Command Line

You can also run this directly:

```python
import requests
API_KEY = "6574119a04954abd93469f85194e07a0"
url = f"https://api.gridstatus.io/v1/datasets?api_key={API_KEY}"
resp = requests.get(url, timeout=30)
data = resp.json()
for item in data.get("data", []):
    if "id" in item:
        print(item["id"])
```

## Common GridStatus Dataset Patterns

Based on GridStatus documentation, the common patterns are:

### PJM
- Day-Ahead: `pjm_lmp_da` or `pjm_lmp_day_ahead_hourly`
- Real-Time: `pjm_lmp_rt_5min` or `pjm_lmp_real_time_5_min`

### CAISO
- Day-Ahead: `caiso_lmp_da` or `caiso_lmp_day_ahead_hourly`
- Real-Time: `caiso_lmp_rt_5min` or `caiso_lmp_real_time_5_min`

### ERCOT
- Day-Ahead: `ercot_spp_da` or `ercot_spp_day_ahead_hourly`
- Real-Time: `ercot_spp_rt_5min` or `ercot_spp_real_time_5_min`

### NYISO
- Day-Ahead: `nyiso_lmp_da` or `nyiso_lmp_day_ahead_hourly`
- Real-Time: `nyiso_lmp_rt_5min` or `nyiso_lmp_real_time_5_min`

### MISO
- Day-Ahead: `miso_lmp_da` or `miso_lmp_day_ahead_hourly`
- Real-Time: `miso_lmp_rt_5min` or `miso_lmp_real_time_5_min`

## Updating the Configuration

Once you have the correct dataset IDs, update `gridstatus_api.py`:

```python
self.iso_datasets = {
    "PJM": {
        "lmp_hourly_da": "ACTUAL_DATASET_ID_HERE",
        "lmp_5min_rt": "ACTUAL_DATASET_ID_HERE",
        "default_location": "PJM RTO",
        "location_column": "location_name"
    },
    # ... other ISOs
}
```

## Testing the Configuration

After updating, test with:

```bash
docker-compose exec backend python scripts/test_gridstatus.py
```

## Troubleshooting

### 400 Bad Request
- Wrong dataset ID
- Wrong filter column name
- Missing required parameters

### 404 Not Found
- Dataset doesn't exist
- Check the exact ID from the API

### 429 Too Many Requests
- Rate limit hit (1 req/sec)
- Wait and retry with delays

## Fallback Strategy

The system automatically falls back to mock data if:
1. Dataset ID is wrong
2. API is unavailable
3. Rate limit is exceeded
4. No data for requested date/time

This ensures the application always works, regardless of API issues.

## Current Status

The system is configured to:
1. Try real data first (if USE_REAL_DATA=true)
2. Handle API errors gracefully
3. Fall back to mock data automatically
4. Log all issues for debugging

To switch to mock-only mode:
```bash
# In .env or docker-compose.yml
USE_REAL_DATA=false
```
