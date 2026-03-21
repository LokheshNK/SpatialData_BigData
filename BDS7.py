"""
Question 7: Emergency Response Distance Analysis

Spatial Query Types Used:
  - $nearSphere  (NEAREST NEIGHBOUR — returns sorted by distance)
  - $maxDistance (range cutoff on NN query)
  - 2dsphere index required

Concept:
  Find the 3 nearest emergency facilities (hospital, police, fire station)
  for each of 8 sample districts in Coimbatore.
  Classify coverage: <1 km = excellent, 1–3 km = good, >3 km = poor.

Visualization:
  - Concentric rings (1 km, 3 km) around each emergency facility
  - Color-coded coverage zones (green/orange/red)
  - Emergency facility icons
"""

from pymongo import MongoClient
import folium
import math
from IPython.display import display

client = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db     = client["bigdata_spatial"]
pois   = db.pois_area

pois.create_index([("geometry", "2dsphere")])

DISTRICTS = [
    {"name": "Gandhipuram",   "coords": [76.9558, 11.0168]},
    {"name": "RS Puram",      "coords": [76.9382, 11.0048]},
    {"name": "Peelamedu",     "coords": [77.0074, 11.0286]},
    {"name": "Singanallur",   "coords": [77.0254, 10.9931]},
    {"name": "Saibaba Colony","coords": [76.9269, 11.0262]},
    {"name": "Ukkadam",       "coords": [76.9673, 10.9872]},
    {"name": "Vadavalli",     "coords": [76.9016, 11.0370]},
    {"name": "Kuniyamuthur",  "coords": [76.9200, 10.9700]},
]

EMERGENCY_AMENITIES = ["hospital", "police", "fire_station", "clinic", "ambulance_station"]

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371
    a = math.sin(math.radians((lat2-lat1)/2))**2 + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(math.radians((lon2-lon1)/2))**2
    return R * 2 * math.asin(math.sqrt(a))

results = []
for district in DISTRICTS:
    lon, lat = district["coords"]
    # $nearSphere returns documents sorted nearest-first
    nearest_docs = list(pois.find(
        {
            "geometry": {
                "$nearSphere": {
                    "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "$maxDistance": 5000
                }
            },
            "properties.amenity": {"$in": EMERGENCY_AMENITIES}
        }
    ).limit(3))

    facilities = []
    for doc in nearest_docs:
        coords = doc["geometry"]["coordinates"]
        if isinstance(coords[0], (int, float)):
            f_lon, f_lat = coords[0], coords[1]
        else:
            ring = coords[0]
            f_lon = sum(p[0] for p in ring) / len(ring)
            f_lat = sum(p[1] for p in ring) / len(ring)
        dist = haversine_km(lon, lat, f_lon, f_lat)
        facilities.append({
            "name":    doc.get("properties", {}).get("name", "Unnamed"),
            "amenity": doc.get("properties", {}).get("amenity", ""),
            "coords":  [f_lon, f_lat],
            "dist_km": round(dist, 3)
        })

    min_dist = facilities[0]["dist_km"] if facilities else 999
    coverage = "excellent" if min_dist < 1 else ("good" if min_dist < 3 else "poor")

    results.append({
        "district":   district["name"],
        "coords":     [lon, lat],
        "facilities": facilities,
        "min_dist":   min_dist,
        "coverage":   coverage
    })

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

COVERAGE_COLORS = {"excellent": "green", "good": "orange", "poor": "red"}
AMENITY_ICONS   = {"hospital": "✚", "police": "🚔", "fire_station": "🔥", "clinic": "✚"}

for rec in results:
    lon, lat  = rec["coords"]
    col       = COVERAGE_COLORS[rec["coverage"]]

    # District marker
    icon_html = f"""
    <div style="background:{col};color:white;font-size:11px;font-weight:bold;
                border-radius:6px;padding:3px 7px;white-space:nowrap;
                border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.3);">
      {rec['district']}
    </div>"""
    folium.Marker(
        location=[lat, lon],
        popup=(
            f"<b>{rec['district']}</b><br>"
            f"Coverage: <b>{rec['coverage'].upper()}</b><br>"
            f"Nearest facility: {rec['min_dist']} km"
        ),
        icon=folium.DivIcon(html=icon_html, icon_size=(110, 28), icon_anchor=(55, 14))
    ).add_to(m)

    # Concentric rings: 1 km (green), 3 km (orange)
    for radius_m, ring_color, ring_label in [(1000, "green", "1 km"), (3000, "orange", "3 km")]:
        folium.Circle(
            location=[lat, lon],
            radius=radius_m,
            fill=False,
            color=ring_color,
            weight=1.2,
            dash_array="5 5",
            opacity=0.5,
            tooltip=f"{rec['district']}: {ring_label} coverage ring"
        ).add_to(m)

    # Emergency facility markers + lines
    for fac in rec["facilities"]:
        f_lon, f_lat = fac["coords"]
        icon_char    = AMENITY_ICONS.get(fac["amenity"], "★")
        fac_html     = f"""<div style="font-size:16px;">{icon_char}</div>"""
        folium.Marker(
            location=[f_lat, f_lon],
            popup=f"<b>{fac['name']}</b> ({fac['amenity']})<br>{fac['dist_km']} km from {rec['district']}",
            icon=folium.DivIcon(html=fac_html, icon_size=(20, 20), icon_anchor=(10, 10))
        ).add_to(m)

        folium.PolyLine(
            locations=[[lat, lon], [f_lat, f_lon]],
            color=col,
            weight=1.5,
            opacity=0.6
        ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Emergency Response Distance ($nearSphere)</b><br>
  <span style="color:green">■</span> Excellent (&lt;1 km)<br>
  <span style="color:orange">■</span> Good (1–3 km)<br>
  <span style="color:red">■</span> Poor (&gt;3 km)<br>
  Rings: 1 km / 3 km coverage thresholds
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Emergency Response Distance ($nearSphere) computed successfully")
display(m)

print("\nEmergency Coverage Summary:")
for rec in results:
    print(f"  {rec['district']:20s} | Coverage: {rec['coverage']:9s} | Nearest: {rec['min_dist']} km")
