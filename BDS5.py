"""
🏪 Question 5: Commercial Hotspot Score (CHS)
📌 Problem Statement

Identify commercial hotspots in Coimbatore where business activity
is highest, making them ideal zones for retail, offices, or malls.

A commercial hotspot typically has:
- High concentration of commercial POIs (shops, banks, malls, offices)
- Good road connectivity
- Moderate building density (not purely residential)

🧠 Concept & Explanation

Commercial activity depends mainly on:
1. Presence of commercial services (POIs)
2. Accessibility (roads)
3. Built environment (buildings)

We define a Commercial Hotspot Score (CHS):

CHS = (0.6 × Commercial_POIs)
    + (0.25 × Road_Segments)
    + (0.15 × Buildings)

Why these weights?
- POIs dominate commercial importance
- Roads enable customer flow
- Buildings indicate usable infrastructure

Higher CHS ⇒ Stronger commercial hotspot
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
# Grid points (reuse same grid)
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
SEARCH_RADIUS_KM = 2
SEARCH_RADIUS_RAD = SEARCH_RADIUS_KM / EARTH_RADIUS_KM

results = []

# -----------------------------
# Compute Commercial Hotspot Score
# -----------------------------
for point in grid_points:

    commercial_pois = pois.count_documents({
        "properties.fclass": {
            "$in": [
                "mall",
                "supermarket",
                "bank",
                "shop",
                "commercial",
                "office"
            ]
        },
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

    chs = (
        0.6 * commercial_pois +
        0.25 * road_count +
        0.15 * building_count
    )

    results.append({
        "center": point,
        "commercial_pois": commercial_pois,
        "roads": road_count,
        "buildings": building_count,
        "CHS": round(chs, 2)
    })

# -----------------------------
# Sort by Commercial Importance
# -----------------------------
results.sort(key=lambda x: x["CHS"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🏪 Commercial Hotspot Score (Top Area):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Commercial POIs: {top['commercial_pois']}")
print(f"Road segments: {top['roads']}")
print(f"Buildings: {top['buildings']}")
print(f"Commercial Hotspot Score (CHS): {top['CHS']}")
