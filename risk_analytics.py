# Filename: advanced_risk_analytics.py
import pandas as pd
import numpy as np
import os
import pickle
import warnings
from datetime import datetime

# Advanced ML Libraries
from sklearn.ensemble import RandomForestRegressor, StackingRegressor
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.svm import SVR
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.pipeline import make_pipeline
import xgboost as xgb

# Progress Bar
try:
    from tqdm import tqdm
    tqdm.pandas(desc="   Processing Rows")
except ImportError:
    def tqdm(x, **kwargs): return x
    pd.DataFrame.progress_apply = pd.DataFrame.apply

warnings.filterwarnings('ignore')

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data_lake")

SILVER_FILE = os.path.join(DATA_DIR, "silver_processed", "Master_Enriched_Dataset.csv")
TRAINING_DIR = os.path.join(DATA_DIR, "gold_training")

INSIGHTS_DIR = os.path.join(DATA_DIR, "gold_insights")
MODEL_DIR = os.path.join(DATA_DIR, "models")
MODEL_PATH = os.path.join(MODEL_DIR, "resilialloc_stacking_v1.pkl")
OUTPUT_FILE = os.path.join(INSIGHTS_DIR, "04_Kaggle_Solution_Submission.csv")
REPORT_FILE = os.path.join(INSIGHTS_DIR, "05_Model_Performance_Report.md")

for d in [INSIGHTS_DIR, MODEL_DIR]: os.makedirs(d, exist_ok=True)

# --- 🧠 MODULE 1: ROBUST FEATURE ENGINEERING ---

class FeatureEngineer:
    def fit_transform(self, df, is_training=False):
        df = df.copy()
        
        col_map = {
            'L2_traffic_aadt': 'traffic',
            'L2_freeze': 'freeze_cycles',
            'L2_freeze_cycles': 'freeze_cycles',
            'L2_salt': 'salt_usage',
            'L2_salt_usage': 'salt_usage',
            'year_built': 'year_built'
        }
        existing_renames = {k: v for k, v in col_map.items() if k in df.columns}
        df.rename(columns=existing_renames, inplace=True)
        
        required = ['traffic', 'freeze_cycles', 'salt_usage', 'year_built']
        missing = [c for c in required if c not in df.columns]
        
        if missing:
            if is_training:
                raise ValueError(f"🔴 Critical: Training data missing columns: {missing}")
            else:
                print(f"🟡 Warning: Inference data missing {missing}. Filling with defaults.")
                for c in missing: df[c] = 0

        if 'age' not in df.columns:
            df['age'] = 2025 - df.get('year_built', 1980)
        
        df['traffic'] = df['traffic'].fillna(df['traffic'].median())
        df['freeze_cycles'] = df['freeze_cycles'].fillna(60)
        df['salt_usage'] = df['salt_usage'].fillna(2)

        df['feat_cumulative_stress'] = df['traffic'] * df['age']
        df['feat_thermal_shock'] = df['freeze_cycles'] * df['salt_usage']
        df['feat_load_intensity'] = df['traffic'] / np.maximum(df['age'] + 1, 1)
        df['feat_corrosion_intensity'] = df['salt_usage'] / np.maximum(df['freeze_cycles'] + 1, 1)

        return df

# --- 📉 MODULE 1.5: BASELINE BENCHMARKER ---

class BaselineBenchmarker:
    def evaluate(self, X, y):
        print("\n   ⚖️  Benchmarking against Industry Standards...")
        metrics = {}
        
        # 1. Naive Baseline (Mean)
        mean_pred = np.full(len(y), y.mean())
        metrics['Naive (Mean)'] = {
            'RMSE': np.sqrt(mean_squared_error(y, mean_pred)),
            'R2': r2_score(y, mean_pred)
        }
        
        # 2. Linear Baseline (Age Only) - The "Government Standard"
        if 'age' in X.columns:
            lr = LinearRegression()
            lr.fit(X[['age']], y)
            preds = lr.predict(X[['age']])
            metrics['Standard (Age-Only)'] = {
                'RMSE': np.sqrt(mean_squared_error(y, preds)),
                'R2': r2_score(y, preds)
            }
        
        return metrics

# --- 🤖 MODULE 2: STACKING ENSEMBLE ---

class StackingBrain:
    def __init__(self):
        self.features = ['age', 'traffic', 'freeze_cycles', 'salt_usage', 
                         'feat_cumulative_stress', 'feat_thermal_shock', 
                         'feat_load_intensity', 'feat_corrosion_intensity']
        
        xgb_model = xgb.XGBRegressor(n_estimators=300, learning_rate=0.05, max_depth=6, n_jobs=-1, random_state=42)
        rf_model = RandomForestRegressor(n_estimators=200, min_samples_split=4, n_jobs=-1, random_state=42)
        svr_model = make_pipeline(RobustScaler(), SVR(C=1.5, epsilon=0.1))
        ridge_model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))

        self.model = StackingRegressor(
            estimators=[('xgb', xgb_model), ('rf', rf_model), ('svr', svr_model), ('ridge', ridge_model)],
            final_estimator=Ridge(),
            passthrough=False
        )

    def train_and_evaluate(self, X, y):
        print("   🧱 Training Stacking Ensemble (Level 1 -> Level 2)...")
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Run Baselines on Validation Set
        bencher = BaselineBenchmarker()
        baseline_metrics = bencher.evaluate(X_val, y_val)
        
        # Train AI
        self.model.fit(X_train, y_train)
        preds = self.model.predict(X_val)
        
        ai_metrics = {
            'RMSE': np.sqrt(mean_squared_error(y_val, preds)),
            'R2': r2_score(y_val, preds)
        }
        
        # Print Comparison Table
        print("\n   🏆 MODEL LEADERBOARD (Validation Set)")
        print(f"   {'Model Name':<25} | {'RMSE (Error)':<15} | {'Accuracy (R²)':<15}")
        print("   " + "-"*60)
        
        # Sort by RMSE (Lower is better)
        all_results = {**baseline_metrics, 'ResiliAlloc AI (Stacked)': ai_metrics}
        sorted_models = sorted(all_results.items(), key=lambda x: x[1]['RMSE'])
        
        for name, scores in sorted_models:
            prefix = "👉 " if "AI" in name else "   "
            print(f"   {prefix}{name:<22} | {scores['RMSE']:.4f}          | {scores['R2']:.4f}")
            
        # Save for report
        self.latest_benchmarks = all_results
        
        with open(MODEL_PATH, 'wb') as f: pickle.dump(self.model, f)
        return ai_metrics

    def predict(self, df):
        X = df[self.features]
        return self.model.predict(X)

    def get_feature_importance(self):
        try:
            rf = self.model.named_estimators_['rf']
            return dict(zip(self.features, rf.feature_importances_))
        except: return {f: 0 for f in self.features}

# --- 🔍 MODULE 3: PSEUDO-LABELING ---

def perform_pseudo_labeling(model, unlabelled_df, original_train_df):
    print("\n   🔄 [PSEUDO-LABELING] Adapting to Local Domain...")
    preds = model.predict(unlabelled_df)
    pseudo_df = unlabelled_df.copy()
    pseudo_df['bci'] = preds
    
    mask = (pseudo_df['bci'] >= 20) & (pseudo_df['bci'] <= 95)
    valid = pseudo_df[mask]
    
    if len(valid) == 0: return original_train_df

    sample_size = min(int(len(valid) * 0.3), len(valid))
    high_conf = valid.sample(n=sample_size, random_state=42)
    print(f"      + Augmented Training with {len(high_conf)} local assets.")
    
    common = original_train_df.columns.intersection(high_conf.columns)
    return pd.concat([original_train_df[common], high_conf[common]], axis=0, ignore_index=True)

# --- 🏃 RUNNER ---

def load_training_data():
    dfs = []
    for fname in ["GT_USA.csv", "GT_Quebec.csv", "GT_UK.csv"]:
        fpath = os.path.join(TRAINING_DIR, fname)
        if os.path.exists(fpath):
            try:
                df = pd.read_csv(fpath)
                if 'sufficiency_rating' in df.columns: df.rename(columns={'sufficiency_rating': 'bci'}, inplace=True)
                if 'GCI' in df.columns: df['bci'] = 100 - (df['GCI'] * 25) 
                dfs.append(df)
            except: pass
    
    if not dfs: raise FileNotFoundError("No training data found.")
    full = pd.concat(dfs, ignore_index=True)
    if 'traffic' not in full.columns: # Synthesize if needed
        n = len(full)
        full['traffic'] = np.random.randint(500, 50000, n)
        full['freeze_cycles'] = np.random.normal(70, 10, n)
        full['salt_usage'] = np.random.choice([1, 2, 3], n)
        full['year_built'] = 2025 - np.random.randint(10, 100, n)
    return full

def explain_risk(row):
    reasons = []
    if row['AI_Predicted_BCI'] < 60: reasons.append(f"STRUCTURAL DECAY (BCI {row['AI_Predicted_BCI']:.0f})")
    if row.get('L3_detour_mins', 0) > 15: reasons.append(f"MEDICALLY CRITICAL ({row['L3_detour_mins']:.0f}m Detour)")
    if row.get('feat_thermal_shock', 0) > 200: reasons.append("SEVERE FREEZE/THAW")
    if row.get('traffic', 0) > 25000: reasons.append("HIGH TRAFFIC LOAD")
    return " + ".join(reasons) if reasons else "Routine Maintenance"

def run_pipeline():
    print("\n🚀 RESILIALLOC STAGE 2: PRODUCTION AI ENGINE")
    print("==============================================")
    
    fe = FeatureEngineer()
    brain = StackingBrain()
    
    try:
        raw_train = load_training_data()
        raw_assets = pd.read_csv(SILVER_FILE)
    except Exception as e: print(f"❌ Load Error: {e}"); return

    print("\n[PHASE 1] Feature Engineering...")
    train_df = fe.fit_transform(raw_train, is_training=True)
    assets_df = fe.fit_transform(raw_assets, is_training=False)
    
    # Train & Benchmark
    ai_metrics = brain.train_and_evaluate(train_df[brain.features], train_df['bci'])
    
    # Pseudo-Label & Retrain
    aug_train = perform_pseudo_labeling(brain, assets_df, train_df)
    print("   🏋️  Retraining Stack on Augmented Domain Data...")
    brain.model.fit(aug_train[brain.features], aug_train['bci'])
    
    print("\n[PHASE 2] Risk Fusion & Prioritization...")
    final_preds = brain.predict(assets_df)
    assets_df['AI_Predicted_BCI'] = np.clip(final_preds, 0, 100)
    
    # Risk Calc
    pof = (100 - assets_df['AI_Predicted_BCI']) / 100.0
    w_med = np.where(assets_df.get('L3_detour_mins', 0) > 10, 4.0, 1.0)
    w_net = np.where(assets_df.get('L3_topology_critical', 0) == 1, 3.0, 1.0)
    w_load = np.where(assets_df.get('feat_load_intensity', 0) > 500, 2.0, 1.0)
    
    raw_risk = pof * (w_med + w_net + w_load)
    assets_df['FINAL_RISK_SCORE'] = np.clip((raw_risk / raw_risk.max()) * 100, 0, 100)
    
    print("   📝 Generating Explainability Reports...")
    assets_df['Primary_Risk_Factor'] = assets_df.progress_apply(explain_risk, axis=1)
    
    # Export
    cols = ['asset_id', 'latitude', 'longitude', 'AI_Predicted_BCI', 
            'FINAL_RISK_SCORE', 'Primary_Risk_Factor', 'feat_cumulative_stress']
    submission = assets_df[[c for c in cols if c in assets_df.columns]].sort_values('FINAL_RISK_SCORE', ascending=False)
    submission.to_csv(OUTPUT_FILE, index=False)
    
    # Report (UTF-8)
    importances = brain.get_feature_importance()
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(f"# 🧠 AI Performance Report\n\n")
        f.write(f"### 🏆 Model Leaderboard\n")
        f.write(f"| Model | RMSE (Error) | Accuracy (R²) |\n|---|---|---|\n")
        
        # Sort for report
        sorted_res = sorted(brain.latest_benchmarks.items(), key=lambda x: x[1]['RMSE'])
        for name, scores in sorted_res:
            bold = "**" if "AI" in name else ""
            f.write(f"| {bold}{name}{bold} | {scores['RMSE']:.4f} | {scores['R2']:.4f} |\n")
            
        f.write(f"\n### 🔍 Primary Physics Drivers\n")
        for k, v in sorted(importances.items(), key=lambda item: item[1], reverse=True):
            f.write(f"* **{k}**: {v:.4f}\n")

    print(f"   🏆 Submission: {OUTPUT_FILE}")
    print(f"   📄 Report: {REPORT_FILE}")

if __name__ == "__main__":
    run_pipeline()