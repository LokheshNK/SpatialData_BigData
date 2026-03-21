"""
Question 14: Optimal Hospital Location

Spatial Query Types Used:
  - $nearSphere  (NN — find distance to nearest existing hospital)
  - $geoWithin + $centerSphere  (range — count demand)
  - Combined gap score: high demand + far from existing = optimal site

Concept:
  For each candidate grid point:
    1. Count buildings within 2 km ($geoWithin) — population demand
    2. Find distance to nearest existing hospital ($nearSphere)
    3. Score = buildings × distance_to_nearest_hospital
       (high score = many people far from hospitals = best new site)

Visualization:
  - Candidate cells colored by opportunity score
  - Existing hospitals as red crosses
  - Top 3 recommended sites as large star markers with connecting lines
"""

from pymongo import MongoClient
import folium
import math
import numpy as np
from IPython.display import display

client    = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db        = client["bigdata_spatial"]
buildings = db.buildings
roads     = db.roads
pois      = db.pois_area

pois.create_index([("geometry", "2dsphere")])

GRID_RADIUS_KM  = 2
EARTH_RADIUS_KM = 6378.1
GRID_RADIUS_RAD = GRID_RADIUS_KM / EARTH_RADIUS_KM

HEALTHCARE = ["hospital", "clinic", "doctors", "health_centre"]
MAX_NN_DIST = 6000  # metres

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
    lon, lat = point

    # Step 1: demand via $geoWithin
    b = buildings.count_documents({
        "geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}
    })
    r = roads.count_documents({
        "geometry": {"$geoWithin": {"$centerSphere": [point, GRID_RADIUS_RAD]}}
    })

    # Step 2: nearest existing hospital via $nearSphere
    nearest = pois.find_one({
        "geometry": {
            "$nearSphere": {
                "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                "$maxDistance": MAX_NN_DIST
            }
        },
        "properties.amenity": {"$in": HEALTHCARE}
    })

    if nearest:
        h_lon, h_lat = get_centroid(nearest["geometry"]["coordinates"])
        dist_km      = haversine_km(lon, lat, h_lon, h_lat)
    else:
        dist_km = MAX_NN_DIST / 1000  # treat as max distance if none found

    # Step 3: opportunity score (high buildings × far from hospital = good site)
    score = round(b * dist_km * (1 + 0.1 * r), 2)

    results.append({
        "center":   point,
        "buildings": b,
        "roads":    r,
        "dist_to_nearest_hosp": round(dist_km, 3),
        "score":    score
    })

results.sort(key=lambda x: x["score"], reverse=True)
max_score = max(r["score"] for r in results) or 1

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

half = STEP / 2

def score_color(norm):
    if norm < 0.25: return "#E8F5E9"
    if norm < 0.50: return "#FFF9C4"
    if norm < 0.75: return "#FFB74D"
    return "#E53935"

for rec in results:
    lon, lat = rec["center"]
    norm     = rec["score"] / max_score
    color    = score_color(norm)
    bounds   = [[lat - half, lon - half], [lat + half, lon + half]]
    folium.Rectangle(
        bounds=bounds,
        fill=True,
        fill_color=color,
        fill_opacity=0.6,
        color=color,
        weight=0,
        popup=(
            f"<b>Opportunity Score: {rec['score']}</b><br>"
            f"Buildings: {rec['buildings']}<br>"
            f"Nearest hospital: {rec['dist_to_nearest_hosp']} km"
        )
    ).add_to(m)

# Existing hospital markers
existing_hospitals = list(pois.find(
    {"properties.amenity": {"$in": HEALTHCARE}},
    {"geometry.coordinates": 1, "properties.name": 1, "_id": 0}
).limit(30))

for hdoc in existing_hospitals:
    try:
        h_lon, h_lat = get_centroid(hdoc["geometry"]["coordinates"])
        if 76.85 <= h_lon <= 77.10 and 10.92 <= h_lat <= 11.15:
            icon_html = """<div style="font-size:16px;color:#B71C1C;">✚</div>"""
            folium.Marker(
                location=[h_lat, h_lon],
                popup=f"<b>Existing hospital</b><br>{hdoc.get('properties', {}).get('name', 'Unnamed')}",
                icon=folium.DivIcon(html=icon_html, icon_size=(20, 20), icon_anchor=(10, 10))
            ).add_to(m)
    except Exception:
        continue

# Top 3 recommended new hospital sites
medal_colors = ["#FFD700", "#C0C0C0", "#CD7F32"]
medal_labels = ["★ Best Site", "★ 2nd Best", "★ 3rd Best"]

for i, rec in enumerate(results[:3]):
    lat, lon = rec["center"][1], rec["center"][0]
    star_html = f"""
    <div style="background:{medal_colors[i]};color:#333;font-weight:bold;
                border-radius:8px;padding:4px 9px;font-size:11px;
                border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.4);
                white-space:nowrap;">
      {medal_labels[i]}
    </div>"""
    folium.Marker(
        location=[lat, lon],
        popup=(
            f"<b>Recommended Hospital Site #{i+1}</b><br>"
            f"Score: {rec['score']}<br>"
            f"Population (buildings): {rec['buildings']}<br>"
            f"Nearest hospital: {rec['dist_to_nearest_hosp']} km away"
        ),
        icon=folium.DivIcon(html=star_html, icon_size=(90, 26), icon_anchor=(45, 13))
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Optimal Hospital Location ($nearSphere gap)</b><br>
  <span style="color:#E53935">■</span> High opportunity (dark)<br>
  <span style="color:#E8F5E9;border:1px solid #ccc">■</span> Low opportunity<br>
  <span style="color:#B71C1C">✚</span> Existing hospitals<br>
  ★ = Top recommended sites
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Optimal Hospital Location ($nearSphere gap) computed successfully")
display(m)

print("\nTop 3 Recommended New Hospital Sites:")
for i, rec in enumerate(results[:3]):
    print(f"  #{i+1}: {rec['center']}  score={rec['score']}  "
          f"buildings={rec['buildings']}  dist_to_nearest={rec['dist_to_nearest_hosp']} km")
