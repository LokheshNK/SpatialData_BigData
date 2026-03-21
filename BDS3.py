"""
Question 3: Commercial Hotspot Score (CHS)

Spatial Query Types Used:
  - $geoWithin + $centerSphere  (range query)
  - amenity field filter on POI collection

Visualization: folium.plugins.FastMarkerCluster — clusters commercial POIs
               so you can visually see where activity is densest
               + DivIcon custom markers for top hotspot zones
"""

from pymongo import MongoClient
from folium.plugins import FastMarkerCluster
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

COMMERCIAL_AMENITIES = [
    "restaurant", "cafe", "bank", "atm", "marketplace",
    "shop", "supermarket", "pharmacy", "fast_food", "bar"
]

results = []
for point in grid_points:
    comm = pois.count_documents({
        "geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}},
        "properties.amenity": {"$in": COMMERCIAL_AMENITIES}
    })
    r = roads.count_documents(    {"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    b = buildings.count_documents({"geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}})
    chs = round(0.5*comm + 0.3*r + 0.2*b, 2)
    results.append({"center": point, "commercial": comm, "roads": r, "buildings": b, "CHS": chs})

results.sort(key=lambda x: x["CHS"], reverse=True)

# ── Folium: Fetch individual commercial POI points for cluster layer ──────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

# Pull actual commercial POI coordinates from MongoDB for the cluster view
commercial_docs = pois.find(
    {"properties.amenity": {"$in": COMMERCIAL_AMENITIES}},
    {"geometry.coordinates": 1, "properties.amenity": 1, "_id": 0}
)

poi_points = []
for doc in commercial_docs:
    try:
        coords = doc["geometry"]["coordinates"]
        # Point geometry: [lon, lat]
        if isinstance(coords[0], (int, float)):
            poi_points.append([coords[1], coords[0]])
        # Polygon centroid: take first ring first point as rough centroid
        elif isinstance(coords[0], list):
            ring = coords[0]
            avg_lat = sum(p[1] for p in ring) / len(ring)
            avg_lon = sum(p[0] for p in ring) / len(ring)
            poi_points.append([avg_lat, avg_lon])
    except (KeyError, IndexError, TypeError):
        continue

if poi_points:
    FastMarkerCluster(poi_points).add_to(m)

# Top commercial hotspot zones as custom styled markers
for i, rec in enumerate(results[:5]):
    lat, lon = rec["center"][1], rec["center"][0]
    label = f"#{i+1}"
    icon_html = f"""
    <div style="background:#FF7700;color:white;font-weight:bold;
                border-radius:50%;width:28px;height:28px;
                display:flex;align-items:center;justify-content:center;
                font-size:12px;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3);">
      {label}
    </div>"""
    folium.Marker(
        location=[lat, lon],
        popup=f"<b>Commercial Hotspot {label}</b><br>CHS: {rec['CHS']}<br>Commercial POIs: {rec['commercial']}",
        icon=folium.DivIcon(html=icon_html, icon_size=(28, 28), icon_anchor=(14, 14))
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Commercial Hotspot Score</b><br>
  Clusters = actual commercial POIs<br>
  <span style="color:#FF7700;font-weight:bold">● #1–#5</span> = top hotspot zones
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Commercial Hotspot Score (MarkerCluster) computed successfully")
display(m)

print(f"\nTop Commercial Hotspot Zone:")
top = results[0]
print(f"  Center: {top['center']} | CHS: {top['CHS']}")
print(f"  Commercial POIs: {top['commercial']} | Roads: {top['roads']}")
print(f"\nTotal commercial POI points on map: {len(poi_points)}")
