"""
🏥 Question 14: Healthcare Accessibility Index (HAI)
📌 Problem Statement

Evaluate how accessible healthcare facilities are across different
regions of Coimbatore using spatial analysis.

🧠 Concept & Explanation

Healthcare accessibility improves when:
• More hospitals/clinics are nearby
• Road connectivity is good (easy access)
• Population indicators (buildings) are reasonable

We compute a Healthcare Accessibility Index (HAI):

HAI =
(1.5 × Hospitals)
+ (0.5 × Roads)
− (0.2 × Buildings)

Why?
• Hospitals get the highest weight
• Roads support emergency access
• High building density may strain facilities

Higher HAI ⇒ Better healthcare access
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
# Compute HAI
# -----------------------------
for point in grid_points:

    hospital_count = pois.count_documents({
        "properties.fclass": "hospital",
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

    building_count = buildings.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [point, RADIUS_RAD]
            }
        }
    })

    hai = (
        1.5 * hospital_count
        + 0.5 * road_count
        - 0.2 * building_count
    )

    results.append({
        "center": point,
        "hospitals": hospital_count,
        "roads": road_count,
        "buildings": building_count,
        "HAI": round(hai, 2)
    })

# -----------------------------
# Sort by HAI
# -----------------------------
results.sort(key=lambda x: x["HAI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
top = results[0]

print("\n🏥 Healthcare Accessibility Index (Top Area):\n")
print(f"Center (lon,lat): {top['center']}")
print(f"Hospitals: {top['hospitals']}")
print(f"Roads: {top['roads']}")
print(f"Buildings: {top['buildings']}")
print(f"Healthcare Accessibility Index (HAI): {top['HAI']}")
