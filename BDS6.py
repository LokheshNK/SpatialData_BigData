"""
Question 6: Nearest Hospital Finder

Spatial Query Types Used:
  - $nearSphere  (NEAREST NEIGHBOUR query — primary)
  - $maxDistance (range limit on nearest neighbour)
  - Requires 2dsphere index on geometry field

Fix: Diagnostic pass first to discover actual field names, then
     multi-strategy fallback search so hospitals are always found.
"""

from pymongo import MongoClient
from folium.plugins import AntPath
import folium
import math
from IPython.display import display

client = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db     = client["bigdata_spatial"]
pois   = db.pois_area

pois.create_index([("geometry", "2dsphere")])

# ── Diagnostic: discover actual amenity field names ───────────────────────────
print("=== Diagnosing pois_area collection ===")
sample = pois.find_one({})
if sample:
    props = sample.get("properties", {})
    print(f"Properties keys: {list(props.keys()) if isinstance(props, dict) else props}")

print("\nSample documents with amenity-like values:")
for doc in pois.find({"properties.amenity": {"$exists": True}}).limit(8):
    props = doc.get("properties", {})
    print(f"  amenity='{props.get('amenity')}' | name='{props.get('name','')}'")

# Check if healthcare is stored under a different key
print("\nAny health-related name values:")
for doc in pois.find({
    "properties.name": {"$regex": "hospital|clinic|health|medical", "$options": "i"}
}).limit(5):
    props = doc.get("properties", {})
    print(f"  name='{props.get('name')}' | amenity='{props.get('amenity','')}' "
          f"| keys={list(props.keys())}")

# ── Helper functions ──────────────────────────────────────────────────────────
HEALTHCARE_AMENITIES = [
    "hospital", "clinic", "doctors", "health_centre", "nursing_home",
    "pharmacy", "dentist", "medical", "healthcare"
]

def get_centroid(geometry):
    """Robust centroid from any GeoJSON geometry."""
    gtype  = geometry.get("type", "")
    coords = geometry.get("coordinates", [])
    try:
        if gtype == "Point":
            return float(coords[0]), float(coords[1])
        elif gtype == "Polygon":
            ring = coords[0]
            return (sum(p[0] for p in ring) / len(ring),
                    sum(p[1] for p in ring) / len(ring))
        elif gtype == "MultiPolygon":
            ring = coords[0][0]
            return (sum(p[0] for p in ring) / len(ring),
                    sum(p[1] for p in ring) / len(ring))
        elif gtype == "LineString":
            mid = coords[len(coords)//2]
            return float(mid[0]), float(mid[1])
        elif gtype == "MultiPoint":
            return float(coords[0][0]), float(coords[0][1])
    except Exception as e:
        print(f"    centroid error ({gtype}): {e}")
    return None, None

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371
    a = (math.sin(math.radians((lat2-lat1)/2))**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(math.radians((lon2-lon1)/2))**2)
    return R * 2 * math.asin(math.sqrt(a))

def find_nearest_healthcare(lon, lat, max_dist=10000):
    """
    Multi-strategy $nearSphere search:
    1. Filter by properties.amenity
    2. Filter by name regex
    3. Any nearest POI as fallback
    """
    strategies = [
        ({"properties.amenity": {"$in": HEALTHCARE_AMENITIES}}, "amenity"),
        ({"properties.healthcare": {"$exists": True}},           "healthcare_field"),
        ({"properties.name": {
              "$regex": "hospital|clinic|health|medical|nursing|dispensary",
              "$options": "i"}},                                  "name_regex"),
        ({},                                                      "nearest_any"),
    ]
    for filt, label in strategies:
        query = {
            "geometry": {
                "$nearSphere": {
                    "$geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "$maxDistance": max_dist
                }
            }
        }
        query.update(filt)
        doc = pois.find_one(query)
        if doc:
            return doc, label
    return None, None

# ── 10 query locations ────────────────────────────────────────────────────────
QUERY_POINTS = [
    {"name": "RS Puram",        "coords": [76.9382, 11.0048]},
    {"name": "Gandhipuram",     "coords": [76.9558, 11.0168]},
    {"name": "Saibaba Colony",  "coords": [76.9269, 11.0262]},
    {"name": "Peelamedu",       "coords": [77.0074, 11.0286]},
    {"name": "Singanallur",     "coords": [77.0254, 10.9931]},
    {"name": "Ukkadam",         "coords": [76.9673, 10.9872]},
    {"name": "Kuniyamuthur",    "coords": [76.9200, 10.9700]},
    {"name": "Kovaipudur",      "coords": [76.9050, 10.9800]},
    {"name": "Vadavalli",       "coords": [76.9016, 11.0370]},
    {"name": "Thondamuthur",    "coords": [76.8700, 11.0250]},
]

print("\n=== $nearSphere queries ===")
results = []
for qp in QUERY_POINTS:
    lon, lat    = qp["coords"]
    doc, strat  = find_nearest_healthcare(lon, lat)

    if doc:
        h_lon, h_lat = get_centroid(doc["geometry"])
        if h_lon is None:
            print(f"  {qp['name']:20s} → centroid failed, skipping")
            results.append({"query_name": qp["name"], "query_coords": [lon, lat],
                             "hosp_coords": None, "hospital_name": "Error",
                             "distance_km": None, "amenity": ""})
            continue
        dist   = haversine_km(lon, lat, h_lon, h_lat)
        props  = doc.get("properties", {}) or {}
        name   = props.get("name") or props.get("amenity") or "Healthcare Facility"
        amnt   = props.get("amenity") or props.get("healthcare") or "facility"
        print(f"  {qp['name']:20s} → '{name}' ({amnt}) {round(dist,3)} km  [{strat}]")
        results.append({
            "query_name":    qp["name"],
            "query_coords":  [lon, lat],
            "hospital_name": name,
            "amenity":       amnt,
            "hosp_coords":   [h_lon, h_lat],
            "distance_km":   round(dist, 3)
        })
    else:
        print(f"  {qp['name']:20s} → NOTHING FOUND")
        results.append({"query_name": qp["name"], "query_coords": [lon, lat],
                         "hosp_coords": None, "hospital_name": "Not found",
                         "distance_km": None, "amenity": ""})

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

connected = [r for r in results if r["hosp_coords"]]
print(f"\nPairs to draw on map: {len(connected)}/{len(results)}")

for rec in results:
    q_lon, q_lat = rec["query_coords"]

    # Blue query dot
    folium.CircleMarker(
        location=[q_lat, q_lon], radius=9,
        color="#0D47A1", fill=True, fill_color="#42A5F5", fill_opacity=0.95,
        popup=f"<b>{rec['query_name']}</b>", tooltip=rec["query_name"]
    ).add_to(m)

    if rec["hosp_coords"]:
        h_lon, h_lat = rec["hosp_coords"]

        # Red cross icon
        folium.Marker(
            location=[h_lat, h_lon],
            popup=(f"<b>{rec['hospital_name']}</b><br>"
                   f"Type: {rec['amenity']}<br>"
                   f"From {rec['query_name']}: {rec['distance_km']} km"),
            tooltip=rec["hospital_name"],
            icon=folium.DivIcon(
                html='<div style="font-size:22px;color:#B71C1C;'
                     'text-shadow:0 0 4px white;">✚</div>',
                icon_size=(26, 26), icon_anchor=(13, 13)
            )
        ).add_to(m)

        # Dashed connecting line
        folium.PolyLine(
            locations=[[q_lat, q_lon], [h_lat, h_lon]],
            color="#1565C0", weight=2.2, dash_array="7 5", opacity=0.8,
            popup=f"{rec['query_name']} → {rec['hospital_name']}: {rec['distance_km']} km"
        ).add_to(m)

        # Distance label at midpoint
        mid_lat = (q_lat + h_lat) / 2
        mid_lon = (q_lon + h_lon) / 2
        folium.Marker(
            location=[mid_lat, mid_lon],
            icon=folium.DivIcon(
                html=(f'<div style="font-size:10px;color:#0D47A1;'
                      f'background:rgba(255,255,255,0.88);padding:1px 5px;'
                      f'border-radius:3px;white-space:nowrap;">'
                      f'{rec["distance_km"]} km</div>'),
                icon_size=(64, 16), icon_anchor=(32, 8)
            )
        ).add_to(m)

# Animated AntPath for the shortest pair
if connected:
    closest = min(connected, key=lambda x: x["distance_km"])
    AntPath(
        locations=[[closest["query_coords"][1], closest["query_coords"][0]],
                   [closest["hosp_coords"][1],  closest["hosp_coords"][0]]],
        color="red", weight=4, delay=700, dash_array=[12, 20]
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Nearest Hospital ($nearSphere)</b><br>
  <span style="color:#42A5F5">●</span> Query location<br>
  <span style="color:#B71C1C;font-size:15px">✚</span> Nearest healthcare facility<br>
  <span style="color:#1565C0">- - -</span> NN line + distance label<br>
  <span style="color:red">~~~</span> Closest pair (animated)
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("\nNearest Hospital Finder computed successfully")
display(m)

print("\nSummary:")
for rec in results:
    dist = f"{rec['distance_km']} km" if rec["distance_km"] else "NOT FOUND"
    print(f"  {rec['query_name']:20s} → {rec['hospital_name']:35s} [{dist}]")
