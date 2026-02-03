"""
🏙️ Question 1: Urban Density Index (UDI)

📌 Problem Statement
Identify the most densely developed urban region in Coimbatore using spatial data.

We compute an Urban Density Index (UDI) by combining:
- Number of buildings
- Number of points of interest (POIs)
- Number of road segments

🧠 Concept & Explanation
Urban density reflects how intensively land is used.

- More buildings → higher built-up density
- More POIs → higher human activity
- More roads → better connectivity

To balance these factors, we define:

UDI = (0.5 × Buildings) + (0.3 × POIs) + (0.2 × Roads)

This weighted model:
- Prioritizes built-up area
- Rewards service availability
- Accounts for transport access
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
# Grid parameters
# -----------------------------
GRID_RADIUS_KM = 2
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

# Sample grid points over Coimbatore
grid_points = [
    [76.94, 11.01], [76.95, 11.01], [76.96, 11.01],
    [76.94, 11.02], [76.95, 11.02], [76.96, 11.02],
    [76.94, 11.03], [76.95, 11.03], [76.96, 11.03],
]

results = []

# -----------------------------
# Compute UDI
# -----------------------------
for point in grid_points:
    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    poi_count = pois.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    road_count = roads.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, GRID_RADIUS_RAD]
            }
        }
    })

    udi = (0.5 * building_count) + (0.3 * poi_count) + (0.2 * road_count)

    results.append({
        "center": point,
        "buildings": building_count,
        "pois": poi_count,
        "roads": road_count,
        "UDI": round(udi, 2)
    })

results.sort(key=lambda x: x["UDI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
top = results[0]
print("\n🏙️ Urban Density Index Results (Top Region):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Buildings: {top['buildings']}")
print(f"POIs: {top['pois']}")
print(f"Roads: {top['roads']}")
print(f"Urban Density Index (UDI): {top['UDI']}")
