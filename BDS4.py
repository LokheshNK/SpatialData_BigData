"""
Question 4: Traffic Congestion Risk Score (TCRS)

Spatial Query Types Used:
  - $geoWithin + $centerSphere  (range query)
  - Demand/capacity ratio model

Visualization: Choropleth rectangles (demand/capacity = white→yellow→red)
               + PolyLine overlay tracing the main road network
"""

from pymongo import MongoClient
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

STEP = 0.02
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
    tcrs = round((0.4*b + 0.4*p) / (1 + 0.2*r), 2)
    results.append({"center": point, "buildings": b, "pois": p, "roads": r, "TCRS": tcrs})

results.sort(key=lambda x: x["TCRS"], reverse=True)
max_tcrs = max(r["TCRS"] for r in results) or 1

def congestion_color(norm):
    """white → yellow → orange → red"""
    r_val = 255
    if norm < 0.5:
        g_val = 255
        b_val = int(255 * (1 - norm * 2))
    else:
        g_val = int(255 * (1 - (norm - 0.5) * 2))
        b_val = 0
    return "#{:02X}{:02X}{:02X}".format(r_val, g_val, b_val)

m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbdark_matter")

half = STEP / 2
for rec in results:
    lon, lat = rec["center"]
    norm     = rec["TCRS"] / max_tcrs
    color    = congestion_color(norm)
    bounds   = [[lat - half, lon - half], [lat + half, lon + half]]
    folium.Rectangle(
        bounds=bounds,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        color=color,
        weight=0,
        popup=(
            f"<b>Congestion Risk: {rec['TCRS']}</b><br>"
            f"Buildings: {rec['buildings']}<br>"
            f"POIs: {rec['pois']}<br>"
            f"Roads: {rec['roads']}"
        )
    ).add_to(m)

# Overlay a sample of road segments as thin white lines for context
road_docs = roads.find(
    {"geometry.type": "LineString"},
    {"geometry.coordinates": 1, "_id": 0}
).limit(300)

road_layer = folium.FeatureGroup(name="Road Network (sample)", show=True)
for doc in road_docs:
    try:
        coords = doc["geometry"]["coordinates"]
        latlngs = [[c[1], c[0]] for c in coords if len(c) >= 2]
        if len(latlngs) >= 2:
            folium.PolyLine(latlngs, color="white", weight=0.6, opacity=0.35).add_to(road_layer)
    except (KeyError, TypeError):
        continue
road_layer.add_to(m)

folium.LayerControl().add_to(m)

# Hotspot label for worst congestion
top = results[0]
folium.Marker(
    location=[top["center"][1], top["center"][0]],
    popup=f"<b>Worst Congestion Zone</b><br>TCRS: {top['TCRS']}",
    icon=folium.Icon(color="red", icon="exclamation-sign")
).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:#1a1a2e;color:white;
     padding:10px 14px;border-radius:8px;border:1px solid #555;font-size:12px;">
  <b>Traffic Congestion Risk</b><br>
  <span style="color:#FF0000">■</span> High risk<br>
  <span style="color:#FFA500">■</span> Medium risk<br>
  <span style="color:#FFFF00">■</span> Low risk
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Traffic Congestion Risk Score computed successfully")
display(m)

print(f"\nHighest Congestion Zone: {top['center']} — TCRS: {top['TCRS']}")
