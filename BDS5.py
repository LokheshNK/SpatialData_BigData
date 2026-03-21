"""
Question 5: Smart City Infrastructure Priority Score (SCIPS)

Spatial Query Types Used:
  - $geoWithin + $centerSphere  (range query)
  - Multi-collection aggregation (buildings, POIs, roads, utilities)

Visualization:
  - DivIcon ranked markers for top priority zones
  - Bubble circles scaled by SCIPS score
  - MiniMap plugin for orientation
"""

from pymongo import MongoClient
from folium.plugins import MiniMap
import folium
import numpy as np
from IPython.display import display

client    = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db        = client["bigdata_spatial"]
buildings = db.buildings
roads     = db.roads
pois      = db.pois_area

GRID_RADIUS_KM  = 2
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

UTILITY_AMENITIES = [
    "school", "hospital", "post_office", "fuel", "library",
    "community_centre", "college", "university"
]

STEP = 0.025
min_lon, max_lon = 76.87, 77.03
min_lat, max_lat = 10.96, 11.09

grid_points = [
    [lon, lat]
    for lon in np.arange(min_lon, max_lon, STEP)
    for lat in np.arange(min_lat, max_lat, STEP)
]

results = []
for point in grid_points:
    b = buildings.count_documents({"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    p = pois.count_documents(     {"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    r = roads.count_documents(    {"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    u = pois.count_documents({
        "geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}},
        "properties.amenity": {"$in": UTILITY_AMENITIES}
    })
    scips = round((0.35*b + 0.35*p + 0.30*r) / (1 + 0.1*u), 2)
    results.append({"center": point, "buildings": b, "pois": p, "roads": r, "utilities": u, "SCIPS": scips})

results.sort(key=lambda x: x["SCIPS"], reverse=True)
max_scips = max(r["SCIPS"] for r in results) or 1

m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")
MiniMap(toggle_display=True).add_to(m)

# Bubble circles — size proportional to SCIPS
for rec in results:
    lon, lat = rec["center"]
    norm   = rec["SCIPS"] / max_scips
    radius = 400 + norm * 1800  # 400m–2200m bubble
    folium.Circle(
        location=[lat, lon],
        radius=radius,
        fill=True,
        fill_color="#5B4FCF",
        fill_opacity=0.15 + 0.5 * norm,
        color="#5B4FCF",
        weight=0.5,
        popup=(
            f"<b>SCIPS: {rec['SCIPS']}</b><br>"
            f"Buildings: {rec['buildings']}<br>"
            f"POIs: {rec['pois']}<br>"
            f"Utilities: {rec['utilities']}"
        )
    ).add_to(m)

# Top-5 priority zones: ranked DivIcon markers
colors = ["#E53935", "#E57C00", "#F4C430", "#2E7D32", "#1565C0"]
for i, rec in enumerate(results[:5]):
    lat, lon = rec["center"][1], rec["center"][0]
    icon_html = f"""
    <div style="background:{colors[i]};color:white;font-weight:bold;
                border-radius:8px;padding:4px 8px;white-space:nowrap;
                font-size:11px;border:2px solid white;
                box-shadow:0 2px 6px rgba(0,0,0,0.4);">
      Priority #{i+1}
    </div>"""
    folium.Marker(
        location=[lat, lon],
        popup=(
            f"<b>Smart City Priority #{i+1}</b><br>"
            f"SCIPS: {rec['SCIPS']}<br>"
            f"Buildings: {rec['buildings']}<br>"
            f"Existing Utilities: {rec['utilities']}"
        ),
        icon=folium.DivIcon(html=icon_html, icon_size=(80, 30), icon_anchor=(40, 15))
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Smart City Priority Score</b><br>
  Bubble size = priority score<br>
  <span style="color:#E53935">■</span> #1 highest priority<br>
  <span style="color:#1565C0">■</span> #5 priority
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Smart City Infrastructure Priority computed successfully")
display(m)

print("\nTop 5 Smart City Priority Zones:")
for i, rec in enumerate(results[:5]):
    print(f"  #{i+1}: {rec['center']} — SCIPS: {rec['SCIPS']} | Utilities: {rec['utilities']}")
