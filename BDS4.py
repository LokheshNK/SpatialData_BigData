"""
🚑 Question 4: Emergency Service Coverage Index (ESCI)
📌 Problem Statement

Evaluate how well different regions of Coimbatore are covered
by emergency services such as hospitals, clinics, and major roads.

A region is considered well-covered if:
- Hospitals are nearby (fast medical response)
- Roads are dense (quick accessibility)

🧠 Concept & Explanation

Emergency response efficiency depends on:
- Availability of healthcare facilities
- Accessibility via road networks

We define an Emergency Service Coverage Index (ESCI):

ESCI = (0.6 × Hospitals) + (0.4 × Road_Segments)

Why these weights?
- Hospitals are the primary factor → higher weight
- Roads support access → secondary but important

Higher ESCI ⇒ Better emergency preparedness
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

# -----------------------------
# Grid points (same as earlier)
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
# Compute ESCI
# -----------------------------
for point in grid_points:

    hospital_count = pois.count_documents({
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

    esci = (0.6 * hospital_count) + (0.4 * road_count)

    results.append({
        "center": point,
        "hospitals": hospital_count,
        "roads": road_count,
        "ESCI": round(esci, 2)
    })

# -----------------------------
# Sort by Emergency Coverage
# -----------------------------
results.sort(key=lambda x: x["ESCI"], reverse=True)

# -----------------------------
# Output
# -----------------------------
print("\n🚑 Emergency Service Coverage Index (Top Area):\n")

top = results[0]
print(f"Center (lon,lat): {top['center']}")
print(f"Hospitals: {top['hospitals']}")
print(f"Road segments: {top['roads']}")
print(f"Emergency Service Coverage Index (ESCI): {top['ESCI']}")
