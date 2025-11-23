# Filename: 7_visualization_dashboard.py
import pandas as pd
import folium
import os
import numpy as np
from config import DIRS

# --- CONFIGURATION ---
# Aligning paths with Stage 3 output
SILVER_FILE = os.path.join(DIRS["SILVER"], "Master_Enriched_Dataset.csv")
INSIGHTS_DIR = os.path.join(DIRS["GOLD"], "..", "gold_insights")
BUDGET_FILE = os.path.join(INSIGHTS_DIR, "06_Final_Budget_Plan.csv")
OUTPUT_MAP = os.path.join(INSIGHTS_DIR, "07_ResiliAlloc_Mission_Control.html")

# Visual Constants
COLOR_FUNDED = 'green'
COLOR_HIGH_RISK = 'red'
COLOR_SAFE = 'gray'

def generate_dashboard():
    print("   🗺️  Generating Mission Control Dashboard (Static HTML)...")
    
    # 1. Validation
    if not os.path.exists(BUDGET_FILE) or not os.path.exists(SILVER_FILE):
        print(f"❌ Missing input files.\n   Silver: {SILVER_FILE}\n   Budget: {BUDGET_FILE}")
        return

    # 2. Load Data
    try:
        df_geo = pd.read_csv(SILVER_FILE, usecols=['asset_id', 'latitude', 'longitude', 'year_built'])
        df_plan = pd.read_csv(BUDGET_FILE)
    except ValueError as e:
        print(f"❌ CSV Parsing Error: {e}")
        return

    # 3. Robust Merge
    # Drop columns in plan that might duplicate geo columns (except key)
    cols_to_use = df_plan.columns.difference(df_geo.columns).tolist()
    cols_to_use.append('asset_id')
    
    # Inner merge ensures we only map assets we have risk data for
    df = pd.merge(df_geo, df_plan[cols_to_use], on='asset_id', how='inner')
    
    # 4. Data Cleaning (NaN Protection)
    df['funded'] = df['funded'].fillna(0).astype(int)
    df['FINAL_RISK_SCORE'] = df['FINAL_RISK_SCORE'].fillna(0)
    df['estimated_cost'] = df['estimated_cost'].fillna(0)

    # 5. Initialize Map (Smart Centering)
    if not df.empty:
        start_lat = df['latitude'].mean()
        start_lon = df['longitude'].mean()
    else:
        start_lat, start_lon = 45.0, -78.0 # Fallback
        
    m = folium.Map(location=[start_lat, start_lon], zoom_start=6, tiles='CartoDB dark_matter')
    
    # 6. Add Layers
    funded_group = folium.FeatureGroup(name="✅ Funded Repairs").add_to(m)
    unfunded_group = folium.FeatureGroup(name="⚠️ Critical Unfunded").add_to(m)
    safe_group = folium.FeatureGroup(name="🛡️ Stable Assets", show=False).add_to(m)

    print(f"      Mapping {len(df)} assets...")

    for _, row in df.iterrows():
        # Logic
        is_funded = row['funded'] == 1
        risk_score = row['FINAL_RISK_SCORE']
        
        if is_funded:
            color = COLOR_FUNDED
            icon = 'wrench'
            group = funded_group
            status_text = "APPROVED FOR REPAIR"
        elif risk_score > 5.0:
            color = COLOR_HIGH_RISK
            icon = 'exclamation-triangle'
            group = unfunded_group
            status_text = "CRITICAL - BUDGET EXCEEDED"
        else:
            color = COLOR_SAFE
            icon = 'shield'
            group = safe_group
            status_text = "Monitoring"

        # Popup HTML
        popup_html = f"""
        <div style="font-family: sans-serif; width: 220px; color: #333;">
            <h4 style="margin-bottom: 5px; color: black;">{row['asset_id']}</h4>
            <span style="color: {color}; font-weight: bold;">{status_text}</span><br>
            <hr style="margin: 5px 0;">
            <b>Risk Score:</b> {risk_score:.2f} / 100<br>
            <b>Repair Cost:</b> ${row['estimated_cost']:,.0f}<br>
            <b>Primary Issue:</b><br>
            <i>{row.get('Primary_Risk_Factor', 'N/A')}</i>
        </div>
        """

        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_html, max_width=250),
            icon=folium.Icon(color=color, icon=icon, prefix='fa'),
            tooltip=f"{row['asset_id']} (Risk: {risk_score:.1f})"
        ).add_to(group)

    # 7. Stats HUD (Heads-Up Display)
    total_spend = df[df['funded'] == 1]['estimated_cost'].sum()
    risk_mitigated = df[df['funded'] == 1]['FINAL_RISK_SCORE'].sum()
    
    stats_html = f"""
    <div style="position: fixed; 
                bottom: 30px; right: 30px; width: 260px; 
                background-color: rgba(30, 30, 30, 0.9); color: white; z-index:9999; 
                border-left: 5px solid #00ff00; border-radius: 4px; padding: 15px;
                font-family: 'Courier New', monospace; box-shadow: 0 0 15px rgba(0,0,0,0.5);">
        <h4 style="margin-top:0; color: #00ff00; border-bottom: 1px solid #555; padding-bottom:5px;">RESILIALLOC HUD</h4>
        <div style="display:flex; justify-content:space-between;">
            <span>Budget Used:</span>
            <span style="font-weight:bold;">${total_spend/1_000_000:.1f}M</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span>Projects:</span>
            <span style="font-weight:bold;">{len(df[df['funded']==1])}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span>Risk Removed:</span>
            <span style="font-weight:bold;">{risk_mitigated:.0f} pts</span>
        </div>
        <div style="margin-top:10px; font-size:0.8em; color:#aaa;">
            System v2.4 | Lakehouse
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(stats_html))

    # 8. Save Output
    folium.LayerControl().add_to(m)
    m.save(OUTPUT_MAP)
    print(f"   🏆 Static Dashboard Saved: {OUTPUT_MAP}")

if __name__ == "__main__":
    generate_dashboard()