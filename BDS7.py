"""
🌱 Question 7: Environmental Sensitivity Index (ESI)
📌 Problem Statement

Identify environmentally sensitive zones in Coimbatore
that require protection from excessive urban development.

These zones are important for:
- Flood control
- Ecological balance
- Sustainable urban planning

🧠 Concept & Explanation

Environmentally sensitive areas usually have:
1. High presence of water bodies
2. Low building density
3. Limited road infrastructure

Too much construction near water leads to:
- Flood risk
- Groundwater depletion
- Ecosystem damage

We define Environmental Sensitivity Index (ESI):

ESI = (0.6 × Water_Features)
    − (0.3 × Buildings)
    − (0.1 × Roads)

Interpretation:
- Higher ESI ⇒ More environmentally sensitive
- Negative weights penalize urbanization pressure
"""

from pymongo import MongoClient

# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient(
    "mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/"
)
db = client["bigdata_spatial"]

water = db.water
roads = db.roads
buildings = db.buildings

# -----------------------------
# Grid points (same grid)
# -----------------------------
grid_points = [
    [76.94, 11.01],
    [76.95, 11.01],
    [76.96, 11.01],
    [76.94, 11.02],
    [76.95, 11.02],
    [76.96, 11.02],
    [76.94, 11.03],
    [76.95, 11.03],
    [76.96, 11.03],
]

# -----------------------------
# Radius parameters
# -----------------------------
EARTH_RADIUS_KM = 6378.1
SEARCH_RADIUS_KM = 3
SEARCH_RADIUS_RAD = SEARCH_RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute ESI per grid
# -----------------------------
for point in grid_points:

    water_count = water.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, SEARCH_RADIUS_RAD]
            }
        }
    })

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, SEARCH_RADIUS_RAD]
            }
        }
    })

    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, SEARCH_RADIUS_RAD]
            }
        }
    })

    esi = (
        0.6 * water_count
        - 0.3 * building_count
        - 0.1 * road_count
    )

    results.append({
        "center": point,
        "water": water_count,
        "buildings": building_count,
        "roads": road_count,
        "ESI": round(esi, 2)
    })

# -----------------------------
# Sort by Environmental Sensitivity
# -----------------------------
results.sort(key=lambda x: x["ESI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🌱 Environmental Sensitivity Index (Top Sensitive Area):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Water features: {top['water']}")
print(f"Buildings: {top['buildings']}")
print(f"Roads: {top['roads']}")
print(f"Environmental Sensitivity Index (ESI): {top['ESI']}")
