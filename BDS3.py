"""
🌊 Question 3: Flood Risk Index (FRI)
📌 Problem Statement

Identify flood-prone urban regions in Coimbatore by analyzing proximity
of built infrastructure to water bodies.

Flood risk increases when:
- Many buildings are close to water bodies
- Roads are located near rivers, canals, or lakes

🧠 Concept & Explanation

Flood risk is a spatial vulnerability problem.

Key assumptions:
- Buildings near water → higher property damage risk
- Roads near water → transport disruption risk

We compute a Flood Risk Index (FRI) using:

FRI = (0.7 × Buildings_near_water) + (0.3 × Roads_near_water)

Why this weighting?
- Buildings suffer permanent damage → higher weight
- Roads are repairable → lower weight

Higher FRI ⇒ Higher flood vulnerability
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
# Grid points (same grid used earlier)
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
# Radius settings
# -----------------------------
EARTH_RADIUS_KM = 6378.1
BUFFER_KM = 1.5
BUFFER_RAD = BUFFER_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute Flood Risk Index
# -----------------------------
for point in grid_points:

    buildings_near_water = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, BUFFER_RAD]
            }
        }
    })

    roads_near_water = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, BUFFER_RAD]
            }
        }
    })

    flood_risk = (0.7 * buildings_near_water) + (0.3 * roads_near_water)

    results.append({
        "center": point,
        "buildings_near_water": buildings_near_water,
        "roads_near_water": roads_near_water,
        "FRI": round(flood_risk, 2)
    })

# -----------------------------
# Sort by Flood Risk
# -----------------------------
results.sort(key=lambda x: x["FRI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🌊 Flood Risk Index Results (Highest Risk Area):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings near water: {top['buildings_near_water']}")
print(f"Roads near water: {top['roads_near_water']}")
print(f"Flood Risk Index (FRI): {top['FRI']}")
