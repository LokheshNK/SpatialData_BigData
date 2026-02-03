"""
🚦 Question 13: Traffic Congestion Risk Index (TCRI)
📌 Problem Statement

Identify areas in Coimbatore that are most prone to traffic congestion
using spatial indicators.

🧠 Concept & Explanation

Traffic congestion typically increases when:
• Road density is high
• POIs are dense (commercial & activity hubs)
• Building density is high (residential + offices)

We compute a Traffic Congestion Risk Index (TCRI):

TCRI =
(0.7 × Roads)
+ (0.5 × POIs)
+ (0.3 × Buildings)

Interpretation:
• Higher TCRI ⇒ Higher congestion risk
• Helps traffic planners and smart signal deployment
"""

from pymongo import MongoClient

# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient(
    "mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/"
)
db = client["bigdata_spatial"]

roads = db.roads
pois = db.pois_area
buildings = db.buildings

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
# Compute TCRI
# -----------------------------
for point in grid_points:

    road_count = roads.count_documents({
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

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    tcri = (
        0.7 * road_count
        + 0.5 * poi_count
        + 0.3 * building_count
    )

    results.append({
        "center": point,
        "roads": road_count,
        "pois": poi_count,
        "buildings": building_count,
        "TCRI": round(tcri, 2)
    })

# -----------------------------
# Sort by TCRI
# -----------------------------
results.sort(key=lambda x: x["TCRI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
top = results[0]

print("\n🚦 Traffic Congestion Risk (Top Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Road segments: {top['roads']}")
print(f"POIs: {top['pois']}")
print(f"Buildings: {top['buildings']}")
print(f"Traffic Congestion Risk Index (TCRI): {top['TCRI']}")
