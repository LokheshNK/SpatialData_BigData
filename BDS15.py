"""
Question 15: Disaster Risk Exposure Index (DREI)

Spatial Query Types Used:
  - $geoIntersects  (buildings intersecting flood polygon)
  - $nearSphere     (nearest emergency facility distance)
  - $geoWithin + $box  (bounding box for railway zones)
  - $geoWithin + $centerSphere  (circle range for density)
  - Composite multi-query scoring

Concept:
  Comprehensive disaster risk = Hazard Exposure + Vulnerability − Resilience
  - Hazard: buildings intersecting flood zones ($geoIntersects)
  - Vulnerability: distance to nearest emergency service ($nearSphere)
  - Density: total buildings within 2 km ($geoWithin)
  - Railway risk: features in bounding box ($geoWithin $box)

  DREI = (Intersecting_buildings × 0.4) + (dist_to_emergency × 10 × 0.3)
         + (total_buildings/100 × 0.2) + (railway_count × 0.1)

Visualization:
  - HeatMap layer for overall DREI intensity
  - Flood zone polygons with risk opacity
  - Emergency facility markers
  - Railway lines overlay
  - Layer control for toggling overlays
"""

from pymongo import MongoClient
from folium.plugins import HeatMap
import folium
import math
import numpy as np
from IPython.display import display

client    = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db        = client["bigdata_spatial"]
buildings = db.buildings
roads     = db.roads
water     = db.water
railways  = db.railways
pois      = db.pois_area

buildings.create_index([("geometry", "2dsphere")])
pois.create_index([("geometry", "2dsphere")])

EMERGENCY_AMENITIES = ["hospital", "police", "fire_station", "clinic"]

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371
    a = math.sin(math.radians((lat2-lat1)/2))**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(math.radians((lon2-lon1)/2))**2
    return R * 2 * math.asin(math.sqrt(a))

def get_centroid(coords):
    if isinstance(coords[0], (int, float)):
        return coords[0], coords[1]
    ring = coords[0]
    return sum(p[0] for p in ring) / len(ring), sum(p[1] for p in ring) / len(ring)

# Flood zone polygons for $geoIntersects
FLOOD_ZONES = [
    {"type": "Polygon", "coordinates": [[[76.955, 11.018],[76.995, 11.018],[76.995, 11.005],[76.955, 11.005],[76.955, 11.018]]]},
    {"type": "Polygon", "coordinates": [[[76.962, 10.988],[76.983, 10.988],[76.983, 10.972],[76.962, 10.972],[76.962, 10.988]]]},
    {"type": "Polygon", "coordinates": [[[77.012, 10.996],[77.038, 10.996],[77.038, 10.978],[77.012, 10.978],[77.012, 10.996]]]},
]

STEP = 0.025
min_lon, max_lon = 76.87, 77.03
min_lat, max_lat = 10.96, 11.09
GRID_RADIUS_RAD = 2 / 6378.1

grid_points = [
    [lon, lat]
    for lon in np.arange(min_lon, max_lon, STEP)
    for lat in np.arange(min_lat, max_lat, STEP)
]

results = []
for point in grid_points:
    lon, lat = point

    # 1. Buildings intersecting any flood zone ($geoIntersects)
    intersect_count = 0
    for fzone in FLOOD_ZONES:
        intersect_count += buildings.count_documents({
            "geometry": {
                "$geoIntersects": {"$geometry": fzone}
            }
        })

    # 2. Distance to nearest emergency service ($nearSphere)
    nearest_em = pois.find_one({
        "geometry": {
            "$nearSphere": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": 6000
            }
        },
        "properties.amenity": {"$in": EMERGENCY_AMENITIES}
    })
    if nearest_em:
        e_lon, e_lat = get_centroid(nearest_em["geometry"]["coordinates"])
        dist_em = haversine_km(lon, lat, e_lon, e_lat)
    else:
        dist_em = 6.0

    # 3. Total buildings in 2 km ($geoWithin circle)
    total_b = buildings.count_documents({
        "geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}
    })

    # 4. Railway features in bounding box ($geoWithin $box)
    box = [[lon - 0.015, lat - 0.015], [lon + 0.015, lat + 0.015]]
    rw_count = railways.count_documents({
        "geometry": {"$geoWithin": {"$box": box}}
    })

    drei = round(
        intersect_count * 0.4 +
        dist_em * 10 * 0.3 +
        (total_b / 100) * 0.2 +
        rw_count * 0.1,
        2
    )

    results.append({
        "center":     point,
        "intersect":  intersect_count,
        "dist_em":    round(dist_em, 3),
        "buildings":  total_b,
        "railways":   rw_count,
        "DREI":       drei
    })

results.sort(key=lambda x: x["DREI"], reverse=True)
max_drei = max(r["DREI"] for r in results) or 1

# ── Folium Map with Layer Control ─────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

# Layer 1: HeatMap of DREI
heatmap_layer = folium.FeatureGroup(name="DREI HeatMap", show=True)
heat_data = [[r["center"][1], r["center"][0], r["DREI"] / max_drei] for r in results]
HeatMap(
    heat_data, radius=22, blur=16, min_opacity=0.3,
    gradient={0.0: "blue", 0.4: "cyan", 0.7: "yellow", 1.0: "red"}
).add_to(heatmap_layer)
heatmap_layer.add_to(m)

# Layer 2: Flood zones
flood_layer = folium.FeatureGroup(name="Flood Zones", show=True)
zone_names = ["Noyyal Floodplain", "Ukkadam Tank Zone", "Singanallur Lake"]
for fzone, fname in zip(FLOOD_ZONES, zone_names):
    latlngs = [[c[1], c[0]] for c in fzone["coordinates"][0]]
    folium.Polygon(
        locations=latlngs,
        fill=True, fill_color="#1565C0", fill_opacity=0.25,
        color="#1565C0", weight=2,
        tooltip=fname
    ).add_to(flood_layer)
flood_layer.add_to(m)

# Layer 3: Emergency facilities
em_layer = folium.FeatureGroup(name="Emergency Facilities", show=True)
em_docs  = list(pois.find(
    {"properties.amenity": {"$in": EMERGENCY_AMENITIES}},
    {"geometry.coordinates": 1, "properties": 1, "_id": 0}
).limit(30))
for doc in em_docs:
    try:
        e_lon, e_lat = get_centroid(doc["geometry"]["coordinates"])
        if 76.85 <= e_lon <= 77.10 and 10.92 <= e_lat <= 11.15:
            amenity = doc.get("properties", {}).get("amenity", "")
            icon_map = {"hospital": "✚", "police": "🚔", "fire_station": "🔥"}
            icon_html = f"""<div style="font-size:14px;">{icon_map.get(amenity, "★")}</div>"""
            folium.Marker(
                location=[e_lat, e_lon],
                popup=f"{doc.get('properties', {}).get('name', amenity)}",
                icon=folium.DivIcon(html=icon_html, icon_size=(20, 20), icon_anchor=(10, 10))
            ).add_to(em_layer)
    except Exception:
        continue
em_layer.add_to(m)

# Layer 4: Railway lines
rail_layer = folium.FeatureGroup(name="Railway Lines", show=True)
rw_docs = railways.find(
    {"geometry.type": {"$in": ["LineString", "MultiLineString"]}},
    {"geometry": 1, "_id": 0}
).limit(100)
for rdoc in rw_docs:
    try:
        if rdoc["geometry"]["type"] == "LineString":
            segs = [rdoc["geometry"]["coordinates"]]
        else:
            segs = rdoc["geometry"]["coordinates"]
        for seg in segs:
            latlngs = [[c[1], c[0]] for c in seg if len(c) >= 2]
            if len(latlngs) >= 2:
                folium.PolyLine(latlngs, color="#FF6F00", weight=2.5, opacity=0.8).add_to(rail_layer)
    except Exception:
        continue
rail_layer.add_to(m)

# Top-3 highest risk zone markers
top3_layer = folium.FeatureGroup(name="Top 3 Risk Zones", show=True)
for i, rec in enumerate(results[:3]):
    lat, lon = rec["center"][1], rec["center"][0]
    risk_html = f"""
    <div style="background:#B71C1C;color:white;font-weight:bold;
                border-radius:50%;width:30px;height:30px;
                display:flex;align-items:center;justify-content:center;
                font-size:13px;border:2px solid white;
                box-shadow:0 2px 6px rgba(0,0,0,0.5);">
      R{i+1}
    </div>"""
    folium.Marker(
        location=[lat, lon],
        popup=(
            f"<b>Risk Zone #{i+1}</b><br>"
            f"DREI: {rec['DREI']}<br>"
            f"Buildings (flood): {rec['intersect']}<br>"
            f"Dist to emergency: {rec['dist_em']} km<br>"
            f"Total buildings: {rec['buildings']}"
        ),
        icon=folium.DivIcon(html=risk_html, icon_size=(30, 30), icon_anchor=(15, 15))
    ).add_to(top3_layer)
top3_layer.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:11px;">
  <b>Disaster Risk Exposure Index (DREI)</b><br>
  Combines 4 spatial query types:<br>
  • $geoIntersects (flood exposure)<br>
  • $nearSphere (emergency distance)<br>
  • $geoWithin $centerSphere (density)<br>
  • $geoWithin $box (railway risk)<br>
  <b>R1/R2/R3</b> = highest risk zones
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Disaster Risk Exposure Index (DREI) — multi-query — computed successfully")
display(m)

avg_drei = round(sum(r["DREI"] for r in results) / len(results), 2)
print(f"\nDREI Summary:")
print(f"  Max DREI : {results[0]['DREI']} @ {results[0]['center']}")
print(f"  Min DREI : {results[-1]['DREI']} @ {results[-1]['center']}")
print(f"  Avg DREI : {avg_drei}")
print(f"\nTop 3 Highest Risk Zones:")
for i, rec in enumerate(results[:3]):
    print(f"  #{i+1}: {rec['center']}  DREI={rec['DREI']}  "
          f"intersect={rec['intersect']}  dist_em={rec['dist_em']} km")
