"""
🚒 Question 11: Emergency Service Coverage Gap Analysis
📌 Problem Statement

Identify regions in Coimbatore that are poorly covered by emergency services
(hospitals + fire stations) despite having high population density.

🧠 Concept & Explanation

Emergency preparedness depends on:
• Availability of emergency facilities (hospitals, fire stations)
• Population concentration (buildings used as proxy)
• Road accessibility for response time

We define an Emergency Coverage Gap Score (ECGS):

ECGS = (1.3 × Building Density) − (1.5 × Emergency Facilities) − (0.4 × Roads)

Interpretation:
• Higher ECGS ⇒ Worse emergency coverage
• High population + low emergency access = priority area
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
RADIUS_KM = 3
RADIUS_RAD = RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute Emergency Coverage Gap
# -----------------------------
for point in grid_points:

    # Population proxy
    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    # Emergency services
    emergency_count = pois.count_documents({
        "properties.fclass": {
            "$in": ["hospital", "fire_station"]
        },
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    # Road accessibility
    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    ecgs = (
        1.3 * building_count
        - 1.5 * emergency_count
        - 0.4 * road_count
    )

    results.append({
        "center": point,
        "buildings": building_count,
        "emergency_services": emergency_count,
        "roads": road_count,
        "ECGS": round(ecgs, 2)
    })

# -----------------------------
# Sort by worst coverage
# -----------------------------
results.sort(key=lambda x: x["ECGS"], reverse=True)

# -----------------------------
# Output
# -----------------------------
worst = results[0]

print("\n🚒 Emergency Service Coverage Gap (Worst Area):\n")
print(f"Center (lon,lat): {worst['center']}")
print(f"Buildings (population proxy): {worst['buildings']}")
print(f"Emergency facilities: {worst['emergency_services']}")
print(f"Road segments: {worst['roads']}")
print(f"Emergency Coverage Gap Score (ECGS): {worst['ECGS']}")
