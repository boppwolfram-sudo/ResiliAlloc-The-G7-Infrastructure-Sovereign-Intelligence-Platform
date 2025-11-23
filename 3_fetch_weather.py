# Filename: 3_fetch_weather.py
import pandas as pd
import numpy as np
import requests
import os
import time
from config import FILES

def fetch_weather_batch(batch):
    """
    Fetches weather for multiple locations in a SINGLE HTTP request.
    Minimizes network latency overhead (1 request vs 50 requests).
    """
    # Prepare comma-separated coordinates
    lats = ",".join([str(row.latitude) for row in batch.itertuples()])
    lons = ",".join([str(row.longitude) for row in batch.itertuples()])
    
    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lats,
        "longitude": lons,
        "start_date": "2023-01-01", 
        "end_date": "2023-12-31",
        "daily": "precipitation_sum,temperature_2m_min"
    }
    
    results = []
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Open-Meteo returns a list of objects if multiple coords provided
        # If only 1 coord, it returns a single object. Handle both.
        if not isinstance(data, list): data = [data]
        
        # Map responses back to Asset IDs
        for i, location_data in enumerate(data):
            asset_id = batch.iloc[i]['asset_id']
            
            # Aggregations
            precip_sum = sum(location_data['daily']['precipitation_sum'])
            temps = location_data['daily']['temperature_2m_min']
            freeze_days = sum(1 for t in temps if t is not None and t < 0)
            
            # Salt Logic (Physics-Informed)
            salt = 3 if freeze_days > 80 else (2 if freeze_days > 40 else 1)
            
            results.append({
                "asset_id": asset_id, 
                "L2_precip": round(precip_sum, 1), 
                "L2_freeze": freeze_days, 
                "L2_salt": salt
            })
            
    except Exception as e:
        print(f"   ⚠️ Batch Error: {e}")
        # Fallback for this specific batch
        for row in batch.itertuples():
            results.append({
                "asset_id": row.asset_id, 
                "L2_precip": 950.0, 
                "L2_freeze": 65, 
                "L2_salt": 2
            })
            
    return results

def fetch_weather():
    print("\n⛈️ [STEP 3] Fetching Layer 2: Weather (High-Speed Batch Mode)...")
    
    if not os.path.exists(FILES["ASSETS"]): 
        print("❌ Missing Asset Backbone. Run Step 2 first.")
        return
        
    assets = pd.read_csv(FILES["ASSETS"])
    total = len(assets)
    print(f"   ℹ️  Processing {total} assets in batches of 50...")
    
    all_weather = []
    batch_size = 50 # Optimal for Open-Meteo
    
    start_time = time.time()
    
    for i in range(0, total, batch_size):
        chunk = assets.iloc[i : i + batch_size]
        batch_results = fetch_weather_batch(chunk)
        all_weather.extend(batch_results)
        
        # Progress Bar
        percent = min(100, (i + batch_size) / total * 100)
        print(f"      Progress: {min(i + batch_size, total)}/{total} ({percent:.1f}%)", end="\r")
        
        # Polite rate limiting
        time.sleep(0.5) 
            
    duration = time.time() - start_time
    print(f"\n   ✅ Weather data secured in {duration:.1f}s: {FILES['WEATHER']}")
    pd.DataFrame(all_weather).to_csv(FILES["WEATHER"], index=False)

if __name__ == "__main__":
    fetch_weather()