"""
🏥 Question 10: Optimal Location for New Hospital
📌 Problem Statement

Propose the most suitable location in Coimbatore to establish a new hospital
by combining results from:

• Healthcare Accessibility Index (HAI)
• Disaster Vulnerability Index (DVI)

🧠 Concept & Explanation

An ideal hospital location should:
1. Be in an area with LOW healthcare accessibility (underserved)
2. Be in an area with HIGH disaster vulnerability (risk-prone population)
3. Have reasonable road connectivity for emergency access

We define a Composite Hospital Priority Score (CHPS):

CHPS = (1.5 × DVI) − (1.2 × HAI)

Interpretation:
• Higher CHPS ⇒ Higher priority for new hospital
• Penalizes already well-served areas
• Rewards high-risk, underserved regions
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
RADIUS_KM = 4
RADIUS_RAD = RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute DVI + HAI + CHPS
# -----------------------------
for point in grid_points:

    # ---- Disaster Vulnerability (DVI)
    water_count = water.count_documents({
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

    dvi = (1.5 * water_count) + (0.8 * building_count)

    # ---- Healthcare Accessibility (HAI)
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

    hai = (
        1.2 * hospital_count
        + 0.3 * road_count
        - 0.5 * building_count
    )

    # ---- Composite Hospital Priority Score
    chps = (1.5 * dvi) - (1.2 * hai)

    results.append({
        "center": point,
        "DVI": round(dvi, 2),
        "HAI": round(hai, 2),
        "CHPS": round(chps, 2)
    })

# -----------------------------
# Sort by highest priority
# -----------------------------
results.sort(key=lambda x: x["CHPS"], reverse=True)

# -----------------------------
# Output
# -----------------------------
best = results[0]

print("\n🏥 Optimal Location for New Hospital:\n")
print(f"Center (lon,lat): {best['center']}")
print(f"Disaster Vulnerability Index (DVI): {best['DVI']}")
print(f"Healthcare Accessibility Index (HAI): {best['HAI']}")
print(f"Hospital Priority Score (CHPS): {best['CHPS']}")
