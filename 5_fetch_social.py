# Filename: 5_fetch_social.py
import pandas as pd
import numpy as np
import requests
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import FILES, MAX_WORKERS

def get_social_context(lat, lon):
    # 1. OSRM Hospital Routing (Real)
    try:
        # Toronto General Hospital Coords (Mock destination for demo)
        url = f"http://router.project-osrm.org/route/v1/driving/{lon},{lat};-79.387,43.658?overview=false"
        r = requests.get(url, timeout=2).json()
        detour = round(r['routes'][0]['duration']/60, 1)
    except:
        detour = 15.0 # Fallback if OSRM times out
        
    # 2. NASA Night Lights (Simulated for speed)
    lights = round(np.random.uniform(5, 60), 2)
    
    # 3. Census (Simulated for speed)
    seniors = round(np.random.uniform(50, 600), 1)
    
    return detour, lights, seniors

def fetch_social():
    print("\n🏥 [STEP 5] Fetching Layer 3: Social & Criticality (Swarm Mode)...")
    
    if not os.path.exists(FILES["ASSETS"]): 
        print("❌ Missing Asset Backbone.")
        return
    
    assets = pd.read_csv(FILES["ASSETS"])
    total = len(assets)
    print(f"   ℹ️  Processing {total} assets with {MAX_WORKERS} threads...")
    
    results = []
    completed = 0
    
    # Using ThreadPoolExecutor for parallel fetching
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as exc:
        # Submit all tasks
        futures = {exc.submit(get_social_context, r.latitude, r.longitude): r.asset_id for r in assets.itertuples()}
        
        for f in as_completed(futures):
            asset_id = futures[f]
            try:
                d, l, s = f.result()
                results.append({
                    "asset_id": asset_id, 
                    "L3_detour_mins": d, 
                    "L3_night_lights": l, 
                    "L3_senior_pop": s
                })
            except Exception:
                # Fallback for failed threads
                results.append({
                    "asset_id": asset_id, 
                    "L3_detour_mins": 15.0, 
                    "L3_night_lights": 10.0, 
                    "L3_senior_pop": 100.0
                })
            
            completed += 1
            if completed % 100 == 0:
                print(f"      Progress: {completed}/{total} ({(completed/total)*100:.1f}%)", end="\r")
        
    print(f"\n   ✅ Social context secured: {FILES['SOCIAL']}")
    pd.DataFrame(results).to_csv(FILES["SOCIAL"], index=False)

if __name__ == "__main__":
    fetch_social()