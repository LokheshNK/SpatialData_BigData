"""
🛣️ Question 2: Road Accessibility Score (RAS)

📌 Problem Statement
Identify the area in Coimbatore with the highest road accessibility.

🧠 Concept & Explanation
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

from pymongo import MongoClient

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
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

grid_points = [
    [76.94, 11.01], [76.95, 11.01], [76.96, 11.01],
    [76.94, 11.02], [76.95, 11.02], [76.96, 11.02],
    [76.94, 11.03], [76.95, 11.03], [76.96, 11.03],
]

results = []

# -----------------------------
# Compute RAS
# -----------------------------
for point in grid_points:
    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    sample_road = roads.find_one({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    intersections = 0
    if sample_road:
        intersections = roads.count_documents({
            "geometry": {
                "$geoIntersects": {
                    "$geometry": sample_road["geometry"]
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
# Output
# -----------------------------
top = results[0]
print("\n🛣️ Road Accessibility Score (Top Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Road segments: {top['roads']}")
print(f"Intersections: {top['intersections']}")
print(f"Road Accessibility Score (RAS): {top['RAS']}")
