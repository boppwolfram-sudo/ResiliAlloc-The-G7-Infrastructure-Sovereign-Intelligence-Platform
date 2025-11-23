import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

# --- Configuration ---
PS_POINTS_FILE = 'ps_points.csv'
ROAD_NETWORK_FILE = 'road_segments.shp'
OUTPUT_FILE = 'road_network_with_insar.shp'
VELOCITY_COLUMN = 'velocity_mm_yr' # Column name for the deformation rate in the CSV

# --- 1. Load and Prepare Road Network Data (Polygons) ---
# We assume the road segments file is a GeoDataFrame (polygons or lines with a buffer)
print(f"Loading road network from {ROAD_NETWORK_FILE}...")
road_gdf = gpd.read_file(ROAD_NETWORK_FILE)

# Ensure consistent Coordinate Reference System (CRS) for joining
# EPSG:4326 is standard WGS84 Lat/Lon, often used for InSAR results
road_gdf = road_gdf.to_crs(epsg=4326) 

# --- 2. Load and Prepare Persistent Scatterer (PS) Points ---
print(f"Loading PS points from {PS_POINTS_FILE}...")
points_df = pd.read_csv(PS_POINTS_FILE)

# Convert the DataFrame to a GeoDataFrame using the lat/lon columns
geometry = [Point(xy) for xy in zip(points_df['lon'], points_df['lat'])]
points_gdf = gpd.GeoDataFrame(points_df, geometry=geometry, crs="EPSG:4326")

# Filter out unreliable points (optional but recommended)
# We keep only points with a velocity value.
points_gdf = points_gdf.dropna(subset=[VELOCITY_COLUMN]) 

# --- 3. Spatial Join (Point-in-Polygon) ---
# This joins every PS point to the road segment it falls within.
print("Performing spatial join...")
# 'within' predicate checks if the point is within the polygon (road segment)
# 'left' join keeps all road segments, even those without PS points
joined_gdf = gpd.sjoin(road_gdf, points_gdf, how="left", predicate="contains", lsuffix='road', rsuffix='ps')

# --- 4. Aggregate Subsidence Velocity by Road Segment ---
print("Aggregating subsidence velocity...")

# Group by the original unique ID of the road segment
# We calculate the average velocity (the subsidence metric)
# The 'mean' aggregation rule is used for the velocity column.
aggregation_results = joined_gdf.groupby(road_gdf.index.name or 'index_road').agg(
    # Calculate the mean of the velocity_mm_yr column for each road segment
    InSAR_Avg_Subsidence_mm_yr=(VELOCITY_COLUMN, 'mean'),
    # Count how many PS points fell on the segment (for quality check)
    InSAR_PS_Count=('index_ps', 'count') 
).reset_index()

# --- 5. Merge Results back to the Main Road Network ---
# The aggregation results must be merged back to the original road GeoDataFrame.
road_gdf = road_gdf.reset_index().merge(
    aggregation_results, 
    on=road_gdf.index.name or 'index', 
    how='left'
)

# Rename the column for the POC feature (negative indicates sinking)
road_gdf = road_gdf.rename(columns={'InSAR_Avg_Subsidence_mm_yr': 'SUBSIDENCE_MM_YR'})

# Fill NaN values with 0.0, assuming segments with no PS points are stable (0 movement)
road_gdf['SUBSIDENCE_MM_YR'] = road_gdf['SUBSIDENCE_MM_YR'].fillna(0.0)
road_gdf['InSAR_PS_Count'] = road_gdf['InSAR_PS_Count'].fillna(0).astype(int)

# --- 6. Save Final Dataset ---
print(f"Saving final dataset to {OUTPUT_FILE}...")
# Remove the temporary 'index' column before saving
if 'index' in road_gdf.columns:
    road_gdf = road_gdf.drop(columns=['index'])
road_gdf.to_file(OUTPUT_FILE)

print("InSAR feature implementation complete!")
print(f"The final dataset has been saved and is ready for the Geo-PIR ML model.")