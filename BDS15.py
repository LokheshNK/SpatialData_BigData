"""
🌍 Question 15: Disaster Risk Exposure Index (DREI)
📌 Problem Statement

Identify regions in Coimbatore that are at higher disaster risk
(flooding & evacuation difficulty) using spatial data.

🧠 Concept & Explanation

Urban disaster risk increases when:
• Area is close to water bodies (flood risk)
• High building density exists (population exposure)
• Poor road connectivity (difficult evacuation)

We define Disaster Risk Exposure Index (DREI):

DREI =
(1.8 × Buildings)
+ (1.2 × Water proximity)
− (0.6 × Roads)

Interpretation:
• Higher DREI ⇒ Higher disaster vulnerability
• Used for evacuation planning & resilience design
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
water = db.water

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
RADIUS_KM = 3
RADIUS_RAD = RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute DREI
# -----------------------------
for point in grid_points:

    building_count = buildings.count_documents({
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

    water_count = water.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    drei = (
        1.8 * building_count
        + 1.2 * water_count
        - 0.6 * road_count
    )

    results.append({
        "center": point,
        "buildings": building_count,
        "water_bodies": water_count,
        "roads": road_count,
        "DREI": round(drei, 2)
    })

# -----------------------------
# Sort by Risk (High → Low)
# -----------------------------
results.sort(key=lambda x: x["DREI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
top = results[0]

print("\n🌍 Disaster Risk Exposure Index (Highest Risk Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings: {top['buildings']}")
print(f"Water Bodies Nearby: {top['water_bodies']}")
print(f"Roads: {top['roads']}")
print(f"Disaster Risk Exposure Index (DREI): {top['DREI']}")
