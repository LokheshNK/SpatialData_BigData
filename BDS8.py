"""
Question 8: Healthcare Accessibility Gap

Spatial Query Types Used:
  - $geoWithin + $centerSphere  (confirmed working from Q1-Q5)
  - Nearest-neighbour logic implemented manually:
      scan increasing radii until a healthcare POI is found
      smallest radius with a result = approximate nearest distance

Concept:
  For each grid point, expand search radius from 0.5 km → 1 km → 2 km → 4 km
  until at least one healthcare POI is found.
  The radius at first hit = accessibility distance for that zone.
  Draw lines from each grid point to the centroid of the found facility.
"""

from pymongo import MongoClient
import folium
import math
import numpy as np
from IPython.display import display

client = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db     = client["bigdata_spatial"]
pois   = db.pois_area

HEALTHCARE_AMENITIES = [
    "hospital", "clinic", "pharmacy", "doctors", "dentist",
    "health_centre", "nursing_home", "medical", "healthcare"
]

EARTH_R = 6378.1

def haversine_km(lon1, lat1, lon2, lat2):
    R = 6371.0
    a = (math.sin(math.radians((lat2 - lat1) / 2)) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(math.radians((lon2 - lon1) / 2)) ** 2)
    return R * 2 * math.asin(math.sqrt(a))

def get_centroid(geometry):
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
            mid = coords[len(coords) // 2]
            return float(mid[0]), float(mid[1])
    except Exception:
        pass
    return None, None

def find_healthcare_within_radius(lon, lat, radius_km):
    """Use $geoWithin $centerSphere — confirmed working."""
    rad = radius_km / EARTH_R

    # Try amenity filter first
    doc = pois.find_one({
        "geometry": {"$geoWithin": {"$centerSphere": [[lon, lat], rad]}},
        "properties.amenity": {"$in": HEALTHCARE_AMENITIES}
    })
    if doc:
        return doc

    # Try name regex
    doc = pois.find_one({
        "geometry": {"$geoWithin": {"$centerSphere": [[lon, lat], rad]}},
        "properties.name": {
            "$regex": "hospital|clinic|health|medical|nursing|pharmacy|dispensary",
            "$options": "i"
        }
    })
    if doc:
        return doc

    # Fallback: any POI within radius
    doc = pois.find_one({
        "geometry": {"$geoWithin": {"$centerSphere": [[lon, lat], rad]}}
    })
    return doc

def find_nearest_by_expanding_radius(lon, lat):
    """
    Nearest-neighbour approximation:
    Expand radius until we hit a healthcare POI.
    Returns (doc, approx_radius_km).
    """
    for r_km in [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]:
        doc = find_healthcare_within_radius(lon, lat, r_km)
        if doc:
            return doc, r_km
    return None, None

# ── Grid points ───────────────────────────────────────────────────────────────
STEP = 0.025
min_lon, max_lon = 76.88, 77.02
min_lat, max_lat = 10.97, 11.08

grid_points = [
    (round(lon, 4), round(lat, 4))
    for lon in np.arange(min_lon, max_lon, STEP)
    for lat in np.arange(min_lat, max_lat, STEP)
]

print(f"Grid points: {len(grid_points)}")

# Quick sanity check — does pois collection return anything at all?
print("\nSanity check — any POI near city centre:")
test = pois.find_one({
    "geometry": {"$geoWithin": {"$centerSphere": [[76.9558, 11.0168], 5.0 / EARTH_R]}}
})
if test:
    print(f"  YES — sample: {test.get('properties', {})}")
else:
    print("  NO POIs found even within 5 km of city centre — check collection!")

# ── Main loop ─────────────────────────────────────────────────────────────────
connections     = []
drawn_facilities = set()

for idx, (g_lon, g_lat) in enumerate(grid_points):
    doc, approx_r = find_nearest_by_expanding_radius(g_lon, g_lat)
    if doc:
        h_lon, h_lat = get_centroid(doc["geometry"])
        if h_lon is None:
            continue
        dist_km = haversine_km(g_lon, g_lat, h_lon, h_lat)
        props   = doc.get("properties", {}) or {}
        name    = props.get("name") or props.get("amenity") or "Healthcare"
        amenity = props.get("amenity") or "facility"
        connections.append({
            "g_lon": g_lon, "g_lat": g_lat,
            "h_lon": h_lon, "h_lat": h_lat,
            "dist_km": round(dist_km, 3),
            "facility": name, "amenity": amenity
        })
        drawn_facilities.add((round(h_lon, 3), round(h_lat, 3)))

    if (idx + 1) % 10 == 0:
        print(f"  {idx+1}/{len(grid_points)} done — connections so far: {len(connections)}")

print(f"\nTotal connections: {len(connections)}")
print(f"Unique facilities: {len(drawn_facilities)}")

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

def dist_color(km):
    if km < 0.5:  return "#1B5E20"
    if km < 1.0:  return "#43A047"
    if km < 2.0:  return "#FB8C00"
    if km < 3.0:  return "#E53935"
    return "#880E4F"

seen_fac = set()

for conn in connections:
    color = dist_color(conn["dist_km"])

    # Grid point dot
    folium.CircleMarker(
        location=[conn["g_lat"], conn["g_lon"]],
        radius=5, color=color, fill=True,
        fill_color=color, fill_opacity=0.9,
        tooltip=f"{conn['dist_km']} km to nearest clinic"
    ).add_to(m)

    # Line to facility
    folium.PolyLine(
        locations=[[conn["g_lat"], conn["g_lon"]],
                   [conn["h_lat"], conn["h_lon"]]],
        color=color, weight=2.2, opacity=0.75,
        popup=f"→ {conn['facility']}: {conn['dist_km']} km"
    ).add_to(m)

    # Distance label at midpoint
    mid_lat = (conn["g_lat"] + conn["h_lat"]) / 2
    mid_lon = (conn["g_lon"] + conn["h_lon"]) / 2
    folium.Marker(
        location=[mid_lat, mid_lon],
        icon=folium.DivIcon(
            html=(f'<div style="font-size:9px;color:{color};font-weight:bold;'
                  f'background:rgba(255,255,255,0.85);padding:1px 4px;'
                  f'border-radius:3px;white-space:nowrap;">'
                  f'{conn["dist_km"]} km</div>'),
            icon_size=(55, 14), icon_anchor=(27, 7)
        )
    ).add_to(m)

    # Healthcare facility marker (once per unique location)
    fkey = (round(conn["h_lon"], 3), round(conn["h_lat"], 3))
    if fkey not in seen_fac:
        seen_fac.add(fkey)
        folium.Marker(
            location=[conn["h_lat"], conn["h_lon"]],
            popup=f"<b>{conn['facility']}</b><br>{conn['amenity']}",
            tooltip=conn["facility"],
            icon=folium.Icon(color="red", icon="plus-sign", prefix="glyphicon")
        ).add_to(m)

# Worst gap highlight
if connections:
    worst = max(connections, key=lambda x: x["dist_km"])
    best  = min(connections, key=lambda x: x["dist_km"])
    avg   = round(sum(c["dist_km"] for c in connections) / len(connections), 3)

    folium.CircleMarker(
        location=[worst["g_lat"], worst["g_lon"]],
        radius=20, color="#880E4F", fill=True,
        fill_color="#880E4F", fill_opacity=0.2, weight=2.5,
        popup=(f"<b>Worst healthcare gap</b><br>"
               f"{worst['dist_km']} km to nearest facility"),
        tooltip="Worst gap zone"
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Healthcare Accessibility Gap ($geoWithin)</b><br>
  Dots + lines = grid point → nearest clinic<br>
  <span style="color:#1B5E20">■</span> &lt;500 m (excellent)<br>
  <span style="color:#43A047">■</span> 500 m – 1 km (good)<br>
  <span style="color:#FB8C00">■</span> 1 – 2 km (fair)<br>
  <span style="color:#E53935">■</span> 2 – 3 km (poor)<br>
  <span style="color:#880E4F">■</span> &gt;3 km (gap zone)<br>
  ✚ = healthcare facility
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("\nHealthcare Accessibility Gap computed successfully")
display(m)

if connections:
    print(f"\nStatistics:")
    print(f"  Grid points     : {len(grid_points)}")
    print(f"  Connections     : {len(connections)}")
    print(f"  Avg distance    : {avg} km")
    print(f"  Best access     : {best['dist_km']} km")
    print(f"  Worst gap       : {worst['dist_km']} km")
    print(f"  Unique facilities: {len(seen_fac)}")
