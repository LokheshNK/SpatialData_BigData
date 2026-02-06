"""
Question 2: Road Accessibility Score (RAS)

Problem Statement
Identify the area in Coimbatore with the highest road accessibility.

Concept & Explanation
Road accessibility depends on:
- Number of road segments
- Number of road intersections

Intersections improve routing flexibility and traffic flow.

We define:

RAS = Road Segments + (2 × Intersections)

This favors:
- Dense road networks
- Well-connected junctions
"""

# =============================
# Road Accessibility Score (RAS)
# Coimbatore | Google Colab
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

roads = db.roads

# -----------------------------
# Grid parameters
# -----------------------------
GRID_RADIUS_KM = 1.5
GRID_RADIUS_M = GRID_RADIUS_KM * 1000
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

# -----------------------------
# Coimbatore bounding box
# -----------------------------
min_lon, max_lon = 76.85, 77.05
min_lat, max_lat = 10.95, 11.10

step = 0.03   # ~3 km spacing

grid_points = []
for lon in np.arange(min_lon, max_lon, step):
    for lat in np.arange(min_lat, max_lat, step):
        grid_points.append([lon, lat])

results = []

# -----------------------------
# Compute RAS
# -----------------------------
for point in grid_points:
    # Count road segments
    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    # Approximate intersections:
    # Count road geometries intersecting within the grid
    intersections = roads.count_documents({
        "geometry": {
            "$geoIntersects": {
                "$geometry": {
                    "type": "Point",
                    "coordinates": point
                }
            }
        }
    })

    ras = road_count + (2 * intersections)

    results.append({
        "center": point,
        "roads": road_count,
        "intersections": intersections,
        "RAS": ras
    })

results.sort(key=lambda x: x["RAS"], reverse=True)

# -----------------------------
# Create Folium Map
# -----------------------------
coimbatore_map = folium.Map(
    location=[11.0168, 76.9558],
    zoom_start=12,
    tiles="cartodbpositron"
)

max_ras = max(r["RAS"] for r in results) if results else 1

for r in results:
    lon, lat = r["center"]
    intensity = r["RAS"] / max_ras

    folium.Circle(
        location=[lat, lon],
        radius=GRID_RADIUS_M,
        fill=True,
        fill_color="blue",
        fill_opacity=0.2 + 0.6 * intensity,
        color=None,
        popup=(
            f"<b>Road Accessibility Score:</b> {r['RAS']}<br>"
            f"Road Segments: {r['roads']}<br>"
            f"Intersections: {r['intersections']}"
        )
    ).add_to(coimbatore_map)

# -----------------------------
# Highlight Top RAS Area
# -----------------------------
top = results[0]

folium.Marker(
    location=[top["center"][1], top["center"][0]],
    popup=f"Highest RAS Area<br>RAS: {top['RAS']}",
    icon=folium.Icon(color="blue", icon="road")
).add_to(coimbatore_map)

# -----------------------------
# Display Map (Colab)
# -----------------------------
print("Road Accessibility Score computed successfully")
display(coimbatore_map)

top = results[0]
print("\n Road Accessibility Score (Top Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Road segments: {top['roads']}")
print(f"Intersections: {top['intersections']}")
print(f"Road Accessibility Score (RAS): {top['RAS']}")
