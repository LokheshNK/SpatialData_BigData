"""
Question 2: Road Accessibility Score (RAS)

Spatial Query Types Used:
  - $geoWithin + $centerSphere  (range query)
  - Ratio-based spatial model

Visualization: folium.plugins.HeatMap — hot=good access, cool=underserved
               + CircleMarkers for top/bottom zones
"""

from pymongo import MongoClient
from folium.plugins import HeatMap
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
    r = roads.count_documents(    {"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    b = buildings.count_documents({"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    p = pois.count_documents(     {"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    ras = round((r * 0.6) / (1 + 0.2*b + 0.2*p), 4)
    results.append({"center": point, "roads": r, "buildings": b, "pois": p, "RAS": ras})

results.sort(key=lambda x: x["RAS"], reverse=True)
max_ras = max(r["RAS"] for r in results) or 1

m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

heat_data = [[rec["center"][1], rec["center"][0], rec["RAS"] / max_ras] for rec in results]
HeatMap(
    heat_data, radius=25, blur=18, min_opacity=0.25,
    gradient={0.0: "blue", 0.4: "cyan", 0.7: "lime", 1.0: "red"}
).add_to(m)

for rec in results[:5]:
    folium.CircleMarker(
        location=[rec["center"][1], rec["center"][0]],
        radius=6, color="darkblue", fill=True, fill_color="deepskyblue", fill_opacity=0.9,
        popup=f"<b>High Accessibility</b><br>RAS: {rec['RAS']}<br>Roads: {rec['roads']}"
    ).add_to(m)

for rec in results[-5:]:
    folium.CircleMarker(
        location=[rec["center"][1], rec["center"][0]],
        radius=6, color="darkred", fill=True, fill_color="tomato", fill_opacity=0.9,
        popup=f"<b>Underserved Zone</b><br>RAS: {rec['RAS']}<br>Buildings: {rec['buildings']}"
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Road Accessibility Score</b><br>
  <span style="color:red">■</span> High RAS (well-connected)<br>
  <span style="color:blue">■</span> Low RAS (underserved)<br>
  <span style="color:deepskyblue">●</span> Top-5 accessible<br>
  <span style="color:tomato">●</span> Top-5 underserved
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Road Accessibility Score computed successfully")
display(m)

print(f"\nBest Accessible Zone  — RAS: {results[0]['RAS']}  @ {results[0]['center']}")
print(f"Most Underserved Zone — RAS: {results[-1]['RAS']} @ {results[-1]['center']}")
