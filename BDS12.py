"""
🏙️ Question 12: Smart City Infrastructure Priority Index (SCIPI)
📌 Problem Statement

Identify the regions in Coimbatore that should be prioritized for Smart City
infrastructure upgrades (smart roads, sensors, utilities, governance).

🧠 Concept & Explanation

A Smart City requires:
• High population density
• Strong road connectivity
• High activity zones (POIs)
• Existing built-up infrastructure

We compute a Smart City Infrastructure Priority Index (SCIPI):

SCIPI =
(0.6 × Buildings)
+ (0.8 × POIs)
+ (0.4 × Roads)

Interpretation:
• Higher SCIPI ⇒ Higher priority for smart upgrades
• Focuses on places where investment impacts more people
"""

from pymongo import MongoClient

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
# Grid points (Coimbatore)
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

EARTH_RADIUS_KM = 6378.1
RADIUS_KM = 2
RADIUS_RAD = RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute SCIPI
# -----------------------------
for point in grid_points:

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    poi_count = pois.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    scipi = (
        0.6 * building_count
        + 0.8 * poi_count
        + 0.4 * road_count
    )

    results.append({
        "center": point,
        "buildings": building_count,
        "pois": poi_count,
        "roads": road_count,
        "SCIPI": round(scipi, 2)
    })

# -----------------------------
# Sort by SCIPI
# -----------------------------
results.sort(key=lambda x: x["SCIPI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
top = results[0]

print("\n🏙️ Smart City Infrastructure Priority (Top Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings: {top['buildings']}")
print(f"POIs: {top['pois']}")
print(f"Road segments: {top['roads']}")
print(f"Smart City Priority Index (SCIPI): {top['SCIPI']}")
