# Filename: 8_merge_layers.py
import pandas as pd
import os
from config import FILES, DIRS

def merge_layers():
    print("\n🔗 RESILIALLOC DATA FUSION")
    print("============================")
    
    # 1. Verify Inputs
    missing = []
    for name, path in [
        ("Assets", FILES["ASSETS"]), 
        ("Weather", FILES["WEATHER"]), 
        ("Traffic", FILES["TRAFFIC"]), 
        ("Social", FILES["SOCIAL"])
    ]:
        if not os.path.exists(path):
            missing.append(name)
        else:
            print(f"   ✅ Found: {os.path.basename(path)}")
    
    if missing:
        print(f"\n❌ CRITICAL ERROR: Missing layers: {missing}")
        print("   Please run the corresponding fetch scripts (2, 3, 4, or 5) again.")
        return

    # 2. Load & Merge
    print("\n   ⚡ Merging Datasets...")
    try:
        df_assets = pd.read_csv(FILES["ASSETS"])
        df_weather = pd.read_csv(FILES["WEATHER"])
        df_traffic = pd.read_csv(FILES["TRAFFIC"])
        df_social = pd.read_csv(FILES["SOCIAL"])
        
        # Left merge ensures we don't lose assets if enrichment failed for some
        master = df_assets.merge(df_weather, on="asset_id", how="left") \
                          .merge(df_traffic, on="asset_id", how="left") \
                          .merge(df_social, on="asset_id", how="left")
        
        # Fill NaNs for failed enrichment (Safety net)
        master.fillna({
            'L2_precip': 900, 'L2_freeze_cycles': 60, 'L2_salt_usage': 2,
            'L2_traffic_aadt': 5000, 'L3_detour_mins': 15, 
            'L3_night_lights': 10, 'L3_senior_pop': 100
        }, inplace=True)

        # 3. Save
        master.to_csv(FILES["MASTER"], index=False)
        print(f"   🎉 SUCCESS: Master Dataset Created ({len(master)} records)")
        print(f"   📂 Location: {FILES['MASTER']}")
        
    except Exception as e:
        print(f"   ❌ Merge Failed: {e}")

if __name__ == "__main__":
    merge_layers()