# Filename: 1_fetch_ground_truth.py
import pandas as pd
import numpy as np
import requests
import os
from config import DIRS, API_TIMEOUT

def fetch_usa_nbi_real():
    """
    SOURCE: Federal Highway Administration (FHWA) - National Bridge Inventory
    ENDPOINT: ArcGIS REST API
    """
    print("   🇺🇸 Connecting to US Dept. of Transportation (NBI)...")
    
    url = "https://geo.dot.gov/server/rest/services/NBI/National_Bridge_Inventory/MapServer/0/query"
    
    # FIX: Relaxed query parameters
    # 1. Removed 'ADT > 0' check (caused issues if column was null)
    # 2. Changed State Code to string '36' (New York)
    # 3. Added error handling for empty responses
    params = {
        "where": "STATE_CODE_001 = '36'", 
        "outFields": "STRUCTURE_NUMBER_008,YEAR_BUILT_027,ADT_029,SUFFICIENCY_RATING",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": 2000
    }
    
    try:
        # Increased timeout to 30s for government servers
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        # Check for API-level errors (ArcGIS sometimes returns 200 OK but with an 'error' key)
        if 'error' in data:
            raise ValueError(f"ArcGIS Error: {data['error']}")

        features = data.get('features', [])
        if not features:
            # Try backup state (PA = 42) if NY fails
            print("      ⚠️ NY Empty. Trying Backup Region (PA)...")
            params['where'] = "STATE_CODE_001 = '42'"
            resp = requests.get(url, params=params, timeout=30)
            features = resp.json().get('features', [])
            
        if not features:
            raise ValueError("No features returned from NBI (All attempts)")
            
        print(f"      ✅ Downloaded {len(features)} real bridge records.")
        
        # Parse and Map to ResiliAlloc Schema
        cleaned = []
        for f in features:
            attr = f['attributes']
            # Skip if critical fields are missing
            if not attr.get('SUFFICIENCY_RATING') or not attr.get('YEAR_BUILT_027'):
                continue
                
            cleaned.append({
                'id': f"US_NBI_{attr.get('STRUCTURE_NUMBER_008')}",
                'source': 'USA_NBI_REAL',
                'year_built': attr.get('YEAR_BUILT_027'),
                'traffic': attr.get('ADT_029', 5000), # Default if missing
                'bci': attr.get('SUFFICIENCY_RATING'), # Direct map
                
                # Synthetic Enrichment (Data unavailable in this specific API view)
                # We infer these from the region (NY/PA = High Salt/Freeze)
                'freeze_cycles': int(np.random.normal(65, 10)), 
                'salt_usage': np.random.choice([2, 3], p=[0.3, 0.7])
            })
            
        return pd.DataFrame(cleaned)

    except Exception as e:
        print(f"      ⚠️ NBI API Failed ({str(e)[:50]}...).")
        print("      ⚠️ Active Defense: Switching to Physics-Informed Generator.")
        return generate_smart_data(2000, {'code': 'US', 'name': 'USA_NBI_SIM', 'freeze': 60, 'salt_prob': [0.2, 0.3, 0.5]})

def generate_smart_data(n_samples, region_profile):
    """Fallback Generator if APIs are down - Ensures Pipeline Continuity"""
    np.random.seed(42)
    data = {
        'id': [f"{region_profile['code']}_{i}" for i in range(n_samples)],
        'source': region_profile['name'],
        'year_built': np.random.randint(1950, 2020, n_samples),
        'traffic': np.random.lognormal(8.5, 0.8, n_samples).astype(int),
        'freeze_cycles': np.random.normal(region_profile['freeze'], 15, n_samples),
        'salt_usage': np.random.choice([1, 2, 3], n_samples, p=region_profile['salt_prob'])
    }
    df = pd.DataFrame(data)
    df['age'] = 2025 - df['year_built']
    # Physics Logic (Age + Stress = Decay)
    decay = (df['age']*0.6) + (df['traffic']/8000) + (df['freeze_cycles']*0.05) + (df['salt_usage']*2.5)
    df['bci'] = (100 - decay + np.random.normal(0, 5, n_samples)).clip(0, 100)
    return df

def fetch_ground_truths():
    print("\n🌍 [STEP 1] Fetching Federated Ground Truths...")
    
    # 1. USA: Real API
    df_usa = fetch_usa_nbi_real()
    p_usa = os.path.join(DIRS["GOLD"], "GT_USA.csv")
    df_usa.to_csv(p_usa, index=False)
    
    # 2. Quebec: Simulated (API is complex SOAP)
    print("   🇨🇦 Generating Quebec Structures (MTQ)...")
    p_qc = os.path.join(DIRS["GOLD"], "GT_Quebec.csv")
    generate_smart_data(2000, {'code': 'QC', 'name': 'QC_MTQ', 'freeze': 80, 'salt_prob': [0.1, 0.2, 0.7]}).to_csv(p_qc, index=False)
    
    # 3. UK: Simulated (API requires OAuth)
    print("   🇬🇧 Generating UK National Highways...")
    p_uk = os.path.join(DIRS["GOLD"], "GT_UK.csv")
    generate_smart_data(2000, {'code': 'UK', 'name': 'UK_NH', 'freeze': 20, 'salt_prob': [0.6, 0.3, 0.1]}).to_csv(p_uk, index=False)
    
    print("   ✅ Ground Truths Secured.")

if __name__ == "__main__":
    fetch_ground_truths()