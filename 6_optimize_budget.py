# Filename: 6_optimize_budget.py
import pandas as pd
import numpy as np
import os
from config import DIRS

# Progress Bar
try:
    from tqdm import tqdm
    tqdm.pandas(desc="   💸 Estimating Costs")
except ImportError:
    def tqdm(x, **kwargs): return x
    pd.DataFrame.progress_apply = pd.DataFrame.apply

# --- CONFIGURATION ---
INPUT_FILE = os.path.join(DIRS["GOLD"], "..", "gold_insights", "04_Kaggle_Solution_Submission.csv")
OUTPUT_FILE = os.path.join(DIRS["GOLD"], "..", "gold_insights", "06_Final_Budget_Plan.csv")
BUDGET_LIMIT = 25_000_000 # $25 Million

def estimate_costs(df):
    print("   💰 Estimating Repair Costs (Heuristic Model)...")
    
    # Base costs per asset type (approximate)
    base_costs = {
        'Bridge': 2_000_000, 
        'Tunnel': 5_000_000, 
        'Road': 500_000
    }
    
    def get_cost(row):
        # 1. Determine Type
        asset_type = 'Bridge' # Default if unknown
        
        # 2. Determine Condition Multiplier
        # Worse condition = Higher cost to fix
        risk = row['FINAL_RISK_SCORE']
        if risk > 80: multiplier = 2.5   # Emergency Rebuild
        elif risk > 50: multiplier = 1.0 # Major Rehab
        else: multiplier = 0.1           # Minor Maintenance
        
        # 3. Add Random Variance (Real world is messy)
        variance = np.random.uniform(0.8, 1.2)
        
        return int(base_costs[asset_type] * multiplier * variance)

    # Use progress_apply for visibility
    df['estimated_cost'] = df.progress_apply(get_cost, axis=1)
    return df

def run_optimization_fast(df):
    print(f"\n   ⚖️  Optimizing Portfolio (Budget: ${BUDGET_LIMIT:,})...")
    
    # 1. Filter Candidate Pool
    candidates = df[df['FINAL_RISK_SCORE'] > 1.0].copy()
    
    # 2. Calculate ROI (Risk Points Removed per Dollar)
    cost_safe = candidates['estimated_cost'].replace(0, 1)
    candidates['roi'] = candidates['FINAL_RISK_SCORE'] / cost_safe
    
    # 3. THE GREEDY ALGORITHM
    candidates.sort_values('roi', ascending=False, inplace=True)
    
    # 4. Allocate Budget
    candidates['cumulative_cost'] = candidates['estimated_cost'].cumsum()
    candidates['funded'] = np.where(candidates['cumulative_cost'] <= BUDGET_LIMIT, 1, 0)
    
    # 5. Stats
    funded = candidates[candidates['funded'] == 1]
    spend = funded['estimated_cost'].sum()
    risk_removed = funded['FINAL_RISK_SCORE'].sum()
    
    print(f"   ⚡ Algorithm: Greedy ROI Sort (High-Speed)")
    print(f"      -> Projects Approved: {len(funded)}")
    print(f"      -> Total Spend:       ${spend:,.2f}")
    print(f"      -> Risk Eliminated:   {risk_removed:,.2f} points")
    
    return candidates

if __name__ == "__main__":
    print("🚀 RESILIALLOC STAGE 3: BUDGET OPTIMIZATION")
    
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: Input file missing. Run 'advanced_risk_analytics.py' first.")
    else:
        # 1. Load Predictions
        df = pd.read_csv(INPUT_FILE)
        
        # 2. Add Financials
        df_with_costs = estimate_costs(df)
        
        # 3. Optimize (Fast Mode)
        final_plan = run_optimization_fast(df_with_costs)
        
        # 4. Save
        cols = ['asset_id', 'FINAL_RISK_SCORE', 'Primary_Risk_Factor', 'estimated_cost', 'funded']
        final_plan[cols].to_csv(OUTPUT_FILE, index=False)
        print(f"\n   🏆 Official Budget Plan Generated: {OUTPUT_FILE}")
        print(final_plan[cols].head(5).to_string(index=False))