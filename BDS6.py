"""
🚰 Question 6: Public Utility Coverage Index (PUCI)
📌 Problem Statement

Identify areas in Coimbatore that are best covered by
public utilities such as water infrastructure and transport access.

Public utilities are critical for:
- Urban livability
- Sustainable development
- Infrastructure planning

🧠 Concept & Explanation

An area is considered well-served if it has:
1. Water bodies / water infrastructure nearby
2. Dense road network for access
3. Adequate buildings indicating habitation

We define a Public Utility Coverage Index (PUCI):

PUCI = (0.5 × Water_Features)
     + (0.3 × Road_Segments)
     + (0.2 × Buildings)

Why these weights?
- Water is the most critical public utility
- Roads enable utility distribution
- Buildings indicate demand and usability

Higher PUCI ⇒ Better public utility coverage
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
# Compute PUCI per grid
# -----------------------------
for point in grid_points:

    water_count = water.count_documents({
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

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, SEARCH_RADIUS_RAD]
            }
        }
    })

    puci = (
        0.5 * water_count +
        0.3 * road_count +
        0.2 * building_count
    )

    results.append({
        "center": point,
        "water": water_count,
        "roads": road_count,
        "buildings": building_count,
        "PUCI": round(puci, 2)
    })

# -----------------------------
# Sort by Utility Coverage
# -----------------------------
results.sort(key=lambda x: x["PUCI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🚰 Public Utility Coverage Index (Top Area):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Water features: {top['water']}")
print(f"Road segments: {top['roads']}")
print(f"Buildings: {top['buildings']}")
print(f"Public Utility Coverage Index (PUCI): {top['PUCI']}")
