# Filename: config.py
import os

# --- PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LAKE_DIR = os.path.join(BASE_DIR, "data_lake")

# Sub-directories
DIRS = {
    "BRONZE": os.path.join(LAKE_DIR, "bronze_raw"),
    "SILVER": os.path.join(LAKE_DIR, "silver_processed"),
    "GOLD":   os.path.join(LAKE_DIR, "gold_training"),
}

# Create them immediately
for d in DIRS.values():
    os.makedirs(d, exist_ok=True)

# --- FILE REGISTRY ---
FILES = {
    "ASSETS": os.path.join(DIRS["SILVER"], "01_Asset_Backbone.csv"),
    "WEATHER": os.path.join(DIRS["SILVER"], "02_Layer_Weather.csv"),
    "TRAFFIC": os.path.join(DIRS["SILVER"], "02_Layer_Traffic.csv"),
    "SOCIAL": os.path.join(DIRS["SILVER"], "03_Layer_Social.csv"),
    "MASTER": os.path.join(DIRS["SILVER"], "Master_Enriched_Dataset.csv")
}

# --- API SETTINGS ---
KEYS = {
    "TOMTOM": os.getenv("TOMTOM_API_KEY", "PLACEHOLDER_KEY"),
    "NASA": os.getenv("NASA_API_KEY", "DEMO_KEY")
}

# --- TUNING ---
BATCH_SIZE = 50
MAX_WORKERS = 8
API_TIMEOUT = 15