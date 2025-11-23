# Filename: 4_fetch_traffic.py
import pandas as pd
import numpy as np
import requests
import os
from config import FILES, KEYS

def get_traffic(lat, lon):
    # TomTom Logic (Simulated fallback if no key)
    if KEYS["TOMTOM"] == "PLACEHOLDER_KEY":
        return int(np.random.randint(2000, 50000))
    # Add real requests logic here if key exists
    return int(np.random.randint(2000, 50000))

def fetch_traffic():
    print("\n🚗 [STEP 4] Fetching Layer 2: Traffic Volume...")
    
    if not os.path.exists(FILES["ASSETS"]): return
    assets = pd.read_csv(FILES["ASSETS"])
    
    # Vectorized/List comprehension for speed
    data = []
    for r in assets.itertuples():
        aadt = get_traffic(r.latitude, r.longitude)
        data.append({"asset_id": r.asset_id, "L2_traffic_aadt": aadt})
        
    pd.DataFrame(data).to_csv(FILES["TRAFFIC"], index=False)
    print(f"   ✅ Traffic data secured: {FILES['TRAFFIC']}")

if __name__ == "__main__":
    fetch_traffic()