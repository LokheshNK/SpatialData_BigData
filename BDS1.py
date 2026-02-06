"""
 Question 1: Urban Density Index (UDI)

 Problem Statement
Identify the most densely developed urban region in Coimbatore using spatial data.

We compute an Urban Density Index (UDI) by combining:
- Number of buildings
- Number of points of interest (POIs)
- Number of road segments

 Concept & Explanation
Urban density reflects how intensively land is used.

- More buildings → higher built-up density
- More POIs → higher human activity
- More roads → better connectivity

To balance these factors, we define:

UDI = (0.5 × Buildings) + (0.3 × POIs) + (0.2 × Roads)

This weighted model:
- Prioritizes built-up area
- Rewards service availability
- Accounts for transport access
"""

# =============================
# Urban Density Index - Coimbatore
# Google Colab Compatible
# =============================

from pymongo import MongoClient
import folium
import numpy as np
from IPython.display import display

# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient(
    "mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/"
)
db = client["bigdata_spatial"]

buildings = db.buildings
roads = db.roads
pois = db.pois_area

# -----------------------------
# Grid parameters
# -----------------------------
GRID_RADIUS_KM = 2
GRID_RADIUS_M = GRID_RADIUS_KM * 1000
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

# -----------------------------
# Coimbatore bounding box
# -----------------------------
min_lon, max_lon = 76.85, 77.05
min_lat, max_lat = 10.95, 11.10

step = 0.03   # ~3 km grid spacing

grid_points = []
for lon in np.arange(min_lon, max_lon, step):
    for lat in np.arange(min_lat, max_lat, step):
        grid_points.append([lon, lat])

results = []

# -----------------------------
# Compute UDI
# -----------------------------
for point in grid_points:
    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    poi_count = pois.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    udi = (0.5 * building_count) + (0.3 * poi_count) + (0.2 * road_count)

    results.append({
        "center": point,
        "buildings": building_count,
        "pois": poi_count,
        "roads": road_count,
        "UDI": round(udi, 2)
    })

results.sort(key=lambda x: x["UDI"], reverse=True)

# -----------------------------
# Create Folium Map
# -----------------------------
coimbatore_map = folium.Map(
    location=[11.0168, 76.9558],
    zoom_start=12,
    tiles="cartodbpositron"
)

max_udi = max(r["UDI"] for r in results) if results else 1

for r in results:
    lon, lat = r["center"]
    intensity = r["UDI"] / max_udi

    folium.Circle(
        location=[lat, lon],
        radius=GRID_RADIUS_M,
        fill=True,
        fill_color="red",
        fill_opacity=0.2 + 0.6 * intensity,
        color=None,
        popup=(
            f"<b>Urban Density Index:</b> {r['UDI']}<br>"
            f"Buildings: {r['buildings']}<br>"
            f"POIs: {r['pois']}<br>"
            f"Roads: {r['roads']}"
        )
    ).add_to(coimbatore_map)

# -----------------------------
# Highlight Top UDI Region
# -----------------------------
top = results[0]

folium.Marker(
    location=[top["center"][1], top["center"][0]],
    popup=f" Highest UDI Area<br>UDI: {top['UDI']}",
    icon=folium.Icon(color="red", icon="info-sign")
).add_to(coimbatore_map)

# -----------------------------
# Display Map (Colab)
# -----------------------------
print("Urban Density Index computed successfully")
display(coimbatore_map)

top = results[0]
print("\n Urban Density Index Results (Top Region):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings: {top['buildings']}")
print(f"POIs: {top['pois']}")
print(f"Roads: {top['roads']}")
print(f"Urban Density Index (UDI): {top['UDI']}")
