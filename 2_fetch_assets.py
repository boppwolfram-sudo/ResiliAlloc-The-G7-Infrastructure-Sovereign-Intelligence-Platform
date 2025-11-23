# Filename: 2_fetch_assets.py
import pandas as pd
import requests
import numpy as np
from config import FILES, API_TIMEOUT

def fetch_assets():
    print("\n🏗️ [STEP 2] Fetching Layer 1: Asset Geospatial (ODIN)...")
    
    # CKAN Handshake
    base = "https://data.ontario.ca/api/3/action"
    try:
        print("   📡 Querying Ontario Data Catalogue...")
        # Dynamic Resource ID lookup
        pkg = requests.get(f"{base}/package_show", params={"id": "bridge-conditions"}, timeout=API_TIMEOUT).json()
        res_id = next(r['id'] for r in pkg['result']['resources'] if r['format'].lower() == 'csv')
        
        # Fetch Data
        resp = requests.get(f"{base}/datastore_search", params={"resource_id": res_id, "limit": 5000}, timeout=API_TIMEOUT)
        records = resp.json()['result']['records']
        
        # Clean
        clean_data = []
        for r in records:
            lat = r.get('Latitude') or r.get('LATITUDE')
            lon = r.get('Longitude') or r.get('LONGITUDE')
            if lat and lon:
                clean_data.append({
                    "asset_id": str(r.get('_id')),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "year_built": int(r.get('Year Built') or r.get('Year_Built') or 1970),
                    "design_capacity": 15000 # Default
                })
        
        df = pd.DataFrame(clean_data)
        df.to_csv(FILES["ASSETS"], index=False)
        print(f"   ✅ Saved {len(df)} assets to {FILES['ASSETS']}")
        
    except Exception as e:
        print(f"   ⚠️ API Error: {e}. Generating Simulation.")
        # Fallback
        mock = [{"asset_id": f"SIM_{i}", "latitude": 43.6, "longitude": -79.3, "year_built": 1980} for i in range(200)]
        pd.DataFrame(mock).to_csv(FILES["ASSETS"], index=False)

if __name__ == "__main__":
    fetch_assets()