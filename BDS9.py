"""
🏥 Question 9: Healthcare Accessibility Index (HAI)
📌 Problem Statement

Identify areas in Coimbatore that have poor access to healthcare facilities
and hence require new hospitals or primary health centers.

🧠 Concept & Explanation

Healthcare accessibility depends on:
1. Number of hospitals nearby
2. Road connectivity (reachability)
3. Building density (population pressure)

We define a Healthcare Accessibility Index (HAI):

HAI = (1.2 × Hospitals)
    + (0.3 × Roads)
    − (0.5 × Buildings)

Interpretation:
- Higher HAI ⇒ Better healthcare access
- Lower HAI ⇒ Healthcare-deficient zone (priority for planning)

Buildings reduce HAI because higher population increases demand.
"""

from pymongo import MongoClient

# -----------------------------
# MongoDB Connection
# -----------------------------
client = MongoClient(
    "mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/"
)
db = client["bigdata_spatial"]

pois = db.pois_area
roads = db.roads
buildings = db.buildings

# -----------------------------
# Filter only hospitals
# -----------------------------
hospitals = pois

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

# -----------------------------
# Radius parameters
# -----------------------------
EARTH_RADIUS_KM = 6378.1
SEARCH_RADIUS_KM = 4
SEARCH_RADIUS_RAD = SEARCH_RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute HAI
# -----------------------------
for point in grid_points:

    hospital_count = hospitals.count_documents({
        "properties.fclass": "hospital",
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

    hai = (
        1.2 * hospital_count
        + 0.3 * road_count
        - 0.5 * building_count
    )

    results.append({
        "center": point,
        "hospitals": hospital_count,
        "roads": road_count,
        "buildings": building_count,
        "HAI": round(hai, 2)
    })

# -----------------------------
# Sort by LOWEST accessibility
# -----------------------------
results.sort(key=lambda x: x["HAI"])

# -----------------------------
# Output
# -----------------------------
print("\n🏥 Healthcare Accessibility Index (Lowest Access Zone):\n")

worst = results[0]
print(f"Center (lon,lat): {worst['center']}")
print(f"Hospitals: {worst['hospitals']}")
print(f"Roads: {worst['roads']}")
print(f"Buildings: {worst['buildings']}")
print(f"Healthcare Accessibility Index (HAI): {worst['HAI']}")
