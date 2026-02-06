"""
 Question 3: Flood Risk Index (FRI)
Problem Statement

Identify flood-prone urban regions in Coimbatore by analyzing proximity
of built infrastructure to water bodies.

Flood risk increases when:
- Many buildings are close to water bodies
- Roads are located near rivers, canals, or lakes

 Concept & Explanation

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

# =============================
# Flood Risk Index (FRI)
# Coimbatore | Google Colab
# =============================

# =====================================================
# Flood Risk Index (FRI)
# Proper Water-Buffer-Based Spatial Analysis
# Google Colab
# =====================================================

from pymongo import MongoClient
import folium
from IPython.display import display

# -----------------------------
# Helper: Safe geometry handler
# -----------------------------
def get_lat_lon(geometry):
    coords = geometry["coordinates"]

    if geometry["type"] == "Point":
        return coords[1], coords[0]

    if geometry["type"] == "Polygon":
        lon, lat = coords[0][0]
        return lat, lon

    if geometry["type"] == "MultiPolygon":
        lon, lat = coords[0][0][0]
        return lat, lon

    return None, None


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
# Parameters
# -----------------------------
BUFFER_KM = 1.5
EARTH_RADIUS_KM = 6378.1
BUFFER_RAD = BUFFER_KM / EARTH_RADIUS_KM

# -----------------------------
# Create Folium Map
# -----------------------------
m = folium.Map(
    location=[11.0168, 76.9558],
    zoom_start=12,
    tiles="cartodbpositron"
)

total_buildings_near = 0
total_roads_near = 0

# -----------------------------
# Process Each Water Body
# -----------------------------
for w in water.find():
    if "geometry" not in w:
        continue

    water_geom = w["geometry"]

    # ---- Plot Water Body ----
    folium.GeoJson(
        water_geom,
        style_function=lambda x: {
            "color": "blue",
            "weight": 2,
            "fillOpacity": 0.3
        }
    ).add_to(m)

    # ---- Buildings near this water body ----
    nearby_buildings = buildings.find({
        "geometry": {
            "$geoIntersects": {
                "$geometry": water_geom
            }
        }
    })

    for b in nearby_buildings:
        lat, lon = get_lat_lon(b["geometry"])
        if lat and lon:
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                color="red",
                fill=True,
                fill_opacity=0.7,
                popup="Building near water"
            ).add_to(m)
            total_buildings_near += 1

    # ---- Roads near this water body ----
    nearby_roads = roads.find({
        "geometry": {
            "$geoIntersects": {
                "$geometry": water_geom
            }
        }
    })

    for r in nearby_roads:
        if "geometry" in r:
            folium.GeoJson(
                r["geometry"],
                style_function=lambda x: {
                    "color": "orange",
                    "weight": 2
                }
            ).add_to(m)
            total_roads_near += 1

# -----------------------------
# Compute Flood Risk Index
# -----------------------------
FRI = round((0.7 * total_buildings_near) + (0.3 * total_roads_near), 2)

# -----------------------------
# Mark Flood Risk Summary
# -----------------------------
folium.Marker(
    location=[11.0168, 76.9558],
    popup=(
        f" Flood Risk Summary<br>"
        f"Buildings near water: {total_buildings_near}<br>"
        f"Roads near water: {total_roads_near}<br>"
        f"Flood Risk Index (FRI): {FRI}"
    ),
    icon=folium.Icon(color="blue", icon="tint")
).add_to(m)

# -----------------------------
# Display Map
# -----------------------------
print("Flood-prone buildings and roads correctly identified")
display(m)

# -----------------------------
# Console Output
# -----------------------------
print("\n Flood Risk Index (Corrected Results)\n")
print(f"Buildings near water: {total_buildings_near}")
print(f"Roads near water: {total_roads_near}")
print(f"Flood Risk Index (FRI): {FRI}")

