# Filename: app.py
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import os

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")
SILVER_FILE = os.path.join(DATA_DIR, "silver_processed", "Master_Enriched_Dataset.csv")
GOLD_FILE = os.path.join(DATA_DIR, "gold_insights", "06_Final_Budget_Plan.csv")

# --- 🎨 COLOR PALETTE ---
COLOR_ACTION = [0, 100, 255, 255]    # 🔵 Blue (Funded)
COLOR_CRITICAL = [255, 0, 0, 200]    # 🔴 Red (Critical Unfunded)
COLOR_WARNING = [255, 170, 0, 180]   # 🟡 Yellow (Warning)
COLOR_SAFE = [0, 180, 80, 100]       # 🟢 Green (Safe)

st.set_page_config(layout="wide", page_title="ResiliAlloc Mission Control")

# --- DATA LOADING ---
@st.cache_data(ttl=300)
def load_data():
    if not os.path.exists(SILVER_FILE) or not os.path.exists(GOLD_FILE):
        return None, False

    try:
        df_raw = pd.read_csv(SILVER_FILE)
        df_opt = pd.read_csv(GOLD_FILE)
    except Exception as e:
        st.error(f"Corrupt CSV files: {e}")
        return None, False

    if 'asset_id' not in df_raw.columns or 'asset_id' not in df_opt.columns:
        st.error("Schema Mismatch: 'asset_id' missing.")
        return None, False

    # Merge Strategy
    cols_to_merge = ['asset_id', 'FINAL_RISK_SCORE', 'Primary_Risk_Factor', 
                     'estimated_cost', 'funded']
    
    overlap = [c for c in cols_to_merge if c in df_raw.columns and c != 'asset_id']
    df_raw.drop(columns=overlap, inplace=True)

    df = pd.merge(df_raw, df_opt[cols_to_merge], on='asset_id', how='left')
    df['funded'] = df['funded'].fillna(0).astype(int)
    df['estimated_cost'] = df['estimated_cost'].fillna(0)
    
    return df, True

# --- SIMULATION ENGINE ---
def run_simulation(df, budget_limit):
    df_sim = df.copy()
    
    # Sort by ROI
    cost_safe = df_sim['estimated_cost'].replace(0, 1e9)
    df_sim['roi'] = df_sim['FINAL_RISK_SCORE'] / cost_safe
    
    df_sim.sort_values('roi', ascending=False, inplace=True)
    
    # Allocate Budget
    cumulative_cost = df_sim['estimated_cost'].cumsum()
    df_sim['funded_sim'] = (cumulative_cost <= budget_limit).astype(int)
    
    return df_sim

# --- UI LAYOUT ---
def main():
    st.title("🛡️ ResiliAlloc: G7 Infrastructure Resilience Platform")
    
    df, success = load_data()
    if not success:
        st.error("Data Lake Empty. Please run 'py orchestrator.py' first.")
        return

    # --- SIDEBAR CONTROLS ---
    st.sidebar.header("⚙️ Policy Controls")
    
    # 1. Budget Slider
    total_need_raw = int(df['estimated_cost'].sum())
    total_need_millions = int(total_need_raw / 1_000_000) + 1
    
    # FIX: Correct default value scaling
    default_budget = 25 # Represents $25 Million
    
    budget_millions = st.sidebar.slider(
        "Maintenance Budget ($ Millions)", 
        min_value=0, 
        max_value=total_need_millions, 
        value=min(default_budget, total_need_millions),
        step=1
    )
    budget_limit = budget_millions * 1_000_000
    
    # 2. Risk Thresholds
    st.sidebar.subheader("🎯 Risk Sensitivity")
    critical_threshold = st.sidebar.slider("Critical Level (Red)", 0, 100, 70)
    warning_threshold = st.sidebar.slider("Warning Level (Yellow)", 0, 100, 30)
    
    # --- RUN SIMULATION ---
    df_sim = run_simulation(df, budget_limit)
    
    # --- METRICS ---
    col1, col2, col3, col4 = st.columns(4)
    funded = df_sim[df_sim['funded_sim']==1]
    risk_removed = funded['FINAL_RISK_SCORE'].sum()
    total_risk = df_sim['FINAL_RISK_SCORE'].sum() or 1
    
    col1.metric("Budget Deployed", f"${budget_millions}M")
    col2.metric("Projects Funded", len(funded))
    col3.metric("Risk Eliminated", f"{risk_removed:.0f} pts")
    col4.metric("Resilience Score", f"{(risk_removed/total_risk)*100:.1f}%")

    # --- MAP VISUALIZATION ---
    st.subheader("📍 Digital Twin: Ontario Assets")
    
    # Color Logic
    def get_color(row):
        if row['funded_sim'] == 1: return COLOR_ACTION
        if row['FINAL_RISK_SCORE'] > critical_threshold: return COLOR_CRITICAL
        if row['FINAL_RISK_SCORE'] > warning_threshold: return COLOR_WARNING
        return COLOR_SAFE

    df_sim['color'] = df_sim.apply(get_color, axis=1)
    
    # Dynamic Traffic Column
    if 'L2_traffic_aadt' in df_sim.columns: traffic_col = 'L2_traffic_aadt'
    elif 'L3_traffic_aadt' in df_sim.columns: traffic_col = 'L3_traffic_aadt'
    else: 
        df_sim['traffic_placeholder'] = 5000
        traffic_col = 'traffic_placeholder'

    max_traffic = df_sim[traffic_col].max() or 1
    df_sim['radius'] = (df_sim[traffic_col] / max_traffic) * 800 + 100

    layer = pdk.Layer(
        "ScatterplotLayer",
        df_sim,
        get_position=["longitude", "latitude"],
        get_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_min_pixels=3,
        radius_max_pixels=20,
    )

    mid_lat = df_sim['latitude'].mean()
    mid_lon = df_sim['longitude'].mean()
    view_state = pdk.ViewState(latitude=mid_lat, longitude=mid_lon, zoom=6, pitch=40)

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10",
        layers=[layer],
        initial_view_state=view_state,
        tooltip={"text": "Asset: {asset_id}\nRisk: {FINAL_RISK_SCORE}\nCost: ${estimated_cost}\nIssue: {Primary_Risk_Factor}"}
    ))

    # --- TABLE ---
    st.subheader("📋 Funded Intervention List (Blue)")
    
    table_df = df_sim[df_sim['funded_sim']==1].copy()
    
    display_cols = {
        'asset_id': 'Asset ID',
        'FINAL_RISK_SCORE': 'Risk Score (0-100)',
        'estimated_cost': 'Estimated Repair Cost ($) ℹ️', # Added icon
        'Primary_Risk_Factor': 'Primary Defect'
    }
    
    if not table_df.empty:
        st.dataframe(
            table_df[list(display_cols.keys())].rename(columns=display_cols).sort_values('Risk Score (0-100)', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Estimated Repair Cost ($) ℹ️": st.column_config.NumberColumn(
                    "Estimated Repair Cost ($) ℹ️",
                    help="⚠️ DEMO DATA: These costs are generated by the AI heuristic model (Base * Risk Multiplier * Traffic). For production use, please integrate with SAP/Oracle for actual contractor quotes.",
                    format="$%d"
                )
            }
        )
    else:
        st.info("No projects funded. Increase budget slider.")

if __name__ == "__main__":
    main()