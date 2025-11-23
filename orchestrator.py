# Filename: orchestrator.py
import os
import pandas as pd
from config import FILES

# THE COMPLETE CHAIN
MODULES = [
    "1_fetch_ground_truth.py",    # Stage 1: Get Learning Data
    "2_fetch_assets.py",          # Stage 1: Get Targets
    "3_fetch_weather.py",         # Stage 1: Enrich Layer 2
    "4_fetch_traffic.py",         # Stage 1: Enrich Layer 2
    "5_fetch_social.py"           # Stage 1: Enrich Layer 3
]

ANALYTICS_MODULES = [
    "advanced_risk_analytics.py", # Stage 2: ML Prediction
    "6_optimize_budget.py",       # Stage 3: Budget Optimization
    "7_visualization_dashboard.py"# Stage 4: Map Generation
]

def run_module(script_name):
    print(f"------------------------------------------------")
    print(f"▶️  EXECUTING: {script_name}")
    exit_code = os.system(f"python {script_name}")
    if exit_code != 0:
        print(f"❌ FAILED: {script_name}")
        exit(1)

def merge_layers():
    print("\n🔗 [INTERLUDE] Merging Data Layers into Master Dataset...")
    try:
        # Load all parts
        df_assets = pd.read_csv(FILES["ASSETS"])
        df_weather = pd.read_csv(FILES["WEATHER"])
        df_traffic = pd.read_csv(FILES["TRAFFIC"])
        df_social = pd.read_csv(FILES["SOCIAL"])
        
        # Merge
        master = df_assets.merge(df_weather, on="asset_id") \
                          .merge(df_traffic, on="asset_id") \
                          .merge(df_social, on="asset_id")
        
        master.to_csv(FILES["MASTER"], index=False)
        print(f"   ✅ Master Data Lake Built: {len(master)} records")
    except Exception as e:
        print(f"❌ Merge Failed: {e}")
        exit(1)

if __name__ == "__main__":
    print("🚀 RESILIALLOC: FULL STACK DEPLOYMENT")
    
    # 1. Data Engineering (The Swarm)
    for m in MODULES: run_module(m)
        
    # 2. Data Integration
    merge_layers()
    
    # 3. Data Science (The Brain)
    for m in ANALYTICS_MODULES: run_module(m)
        
    print("\n🎉 SYSTEM COMPLETE. CHECK 'gold_insights' FOLDER.")