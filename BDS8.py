"""
🌊 Question 8: Disaster Vulnerability Index (DVI)
📌 Problem Statement

Identify regions in Coimbatore that are highly vulnerable to
urban disasters such as floods, infrastructure collapse,
and emergency inaccessibility.

🧠 Concept & Explanation

Urban disasters are more likely in areas where:
1. Water bodies are present (flood risk)
2. Building density is high (population & asset exposure)
3. Road connectivity is low (poor evacuation access)

We define Disaster Vulnerability Index (DVI) as:

DVI = (0.5 × Buildings)
    + (0.4 × Water_Features)
    − (0.2 × Roads)

Interpretation:
- Higher DVI ⇒ Higher disaster vulnerability
- Roads reduce vulnerability by improving evacuation & response
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
# Grid points over Coimbatore
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
# Compute DVI per grid
# -----------------------------
for point in grid_points:

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, SEARCH_RADIUS_RAD]
            }
        }
    })

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

    dvi = (
        0.5 * building_count
        + 0.4 * water_count
        - 0.2 * road_count
    )

    results.append({
        "center": point,
        "buildings": building_count,
        "water": water_count,
        "roads": road_count,
        "DVI": round(dvi, 2)
    })

# -----------------------------
# Sort by Disaster Vulnerability
# -----------------------------
results.sort(key=lambda x: x["DVI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🌊 Disaster Vulnerability Index (Highest Risk Zone):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings: {top['buildings']}")
print(f"Water bodies: {top['water']}")
print(f"Roads: {top['roads']}")
print(f"Disaster Vulnerability Index (DVI): {top['DVI']}")
