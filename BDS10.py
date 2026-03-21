"""
Question 10: Railway Buffer Zone Analysis

Spatial Query Types Used:
  - $geoWithin + $box  (BOUNDING BOX range query — axis-aligned rectangle)
  - $geoWithin + $centerSphere  (circle range for comparison)
  - Cross-collection: railways + buildings + pois

Concept:
  Define bounding boxes (buffers) around key railway stations/lines.
  Count buildings and POIs inside each bounding box.
  Identify which railway corridor has the highest development pressure.

Visualization:
  - Rectangle overlays for each bounding box buffer
  - Railway line segments drawn as PolyLines
  - Heatmap of building density around railway corridors
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
railways  = db.railways

# ── Bounding boxes around railway corridors in Coimbatore ────────────────────
# $box format: [[min_lon, min_lat], [max_lon, max_lat]]
RAILWAY_BUFFERS = [
    {
        "name":   "Coimbatore Junction Corridor",
        "box":    [[76.940, 11.000], [76.975, 11.025]],
        "color":  "#8B0000"
    },
    {
        "name":   "Podanur Junction Zone",
        "box":    [[76.955, 10.975], [76.995, 11.000]],
        "color":  "#C62828"
    },
    {
        "name":   "Irugur - Peelamedu Rail Buffer",
        "box":    [[77.000, 11.010], [77.045, 11.040]],
        "color":  "#E64A19"
    },
    {
        "name":   "North Railway Approach",
        "box":    [[76.950, 11.025], [76.980, 11.060]],
        "color":  "#AD1457"
    },
    {
        "name":   "Singanallur Rail Fringe",
        "box":    [[77.015, 10.978], [77.050, 11.005]],
        "color":  "#6A1B9A"
    },
]

results = []
for buf in RAILWAY_BUFFERS:
    box = buf["box"]

    # $geoWithin $box — axis-aligned bounding box query
    box_query = {
        "geometry": {
            "$geoWithin": {
                "$box": box  # [[min_lon, min_lat], [max_lon, max_lat]]
            }
        }
    }

    b = buildings.count_documents(box_query)
    r = roads.count_documents(box_query)
    p = pois.count_documents(box_query)
    rw = railways.count_documents(box_query)

    # Width and height in degrees (approx metres)
    width_km  = abs(box[1][0] - box[0][0]) * 111
    height_km = abs(box[1][1] - box[0][1]) * 111
    area_km2  = round(width_km * height_km, 2)

    pressure = round((0.5*b + 0.3*p + 0.2*r) / max(area_km2, 0.01), 2)

    results.append({
        "name":        buf["name"],
        "box":         box,
        "color":       buf["color"],
        "buildings":   b,
        "roads":       r,
        "pois":        p,
        "railways":    rw,
        "area_km2":    area_km2,
        "pressure":    pressure
    })

results.sort(key=lambda x: x["pressure"], reverse=True)

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbdark_matter")

# Draw bounding box rectangles
for rec in results:
    box    = rec["box"]
    # Folium Rectangle bounds: [[min_lat, min_lon], [max_lat, max_lon]]
    bounds = [[box[0][1], box[0][0]], [box[1][1], box[1][0]]]
    folium.Rectangle(
        bounds=bounds,
        fill=True,
        fill_color=rec["color"],
        fill_opacity=0.25,
        color=rec["color"],
        weight=2,
        dash_array="6 3",
        popup=(
            f"<b>{rec['name']}</b><br>"
            f"Development Pressure: <b>{rec['pressure']}</b>/km²<br>"
            f"Buildings: {rec['buildings']}<br>"
            f"POIs: {rec['pois']}<br>"
            f"Roads: {rec['roads']}<br>"
            f"Area: {rec['area_km2']} km²"
        ),
        tooltip=f"{rec['name']}: pressure={rec['pressure']}/km²"
    ).add_to(m)

    # Pressure label
    cent_lat = (box[0][1] + box[1][1]) / 2
    cent_lon = (box[0][0] + box[1][0]) / 2
    label_html = f"""
    <div style="font-size:10px;font-weight:bold;color:{rec['color']};
                background:rgba(0,0,0,0.7);padding:2px 5px;
                border-radius:4px;white-space:nowrap;">
      {rec['pressure']}/km²
    </div>"""
    folium.Marker(
        location=[cent_lat, cent_lon],
        icon=folium.DivIcon(html=label_html, icon_size=(80, 20), icon_anchor=(40, 10))
    ).add_to(m)

# Draw actual railway line segments from DB
railway_docs = railways.find(
    {"geometry.type": {"$in": ["LineString", "MultiLineString"]}},
    {"geometry": 1, "_id": 0}
).limit(200)

for doc in railway_docs:
    try:
        geo_type = doc["geometry"]["type"]
        if geo_type == "LineString":
            coords_list = [doc["geometry"]["coordinates"]]
        else:
            coords_list = doc["geometry"]["coordinates"]
        for coords in coords_list:
            latlngs = [[c[1], c[0]] for c in coords if len(c) >= 2]
            if len(latlngs) >= 2:
                folium.PolyLine(
                    latlngs, color="#FFD700", weight=2.5, opacity=0.9
                ).add_to(m)
    except Exception:
        continue

# Heatmap of buildings in buffer zones
bldg_heat = []
for rec in results:
    box   = rec["box"]
    # Grab up to 50 building centroids in this box
    docs  = buildings.find(
        {"geometry": {"$geoWithin": {"$box": box}}},
        {"geometry.coordinates": 1, "_id": 0}
    ).limit(50)
    for doc in docs:
        try:
            coords = doc["geometry"]["coordinates"]
            if isinstance(coords[0], list):
                ring  = coords[0]
                b_lon = sum(p[0] for p in ring) / len(ring)
                b_lat = sum(p[1] for p in ring) / len(ring)
            else:
                b_lon, b_lat = coords[0], coords[1]
            bldg_heat.append([b_lat, b_lon, 1])
        except Exception:
            continue

if bldg_heat:
    HeatMap(bldg_heat, radius=12, blur=10, min_opacity=0.3,
            gradient={0.0: "blue", 0.5: "lime", 1.0: "red"}).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:#1a1a2e;color:white;
     padding:10px 14px;border-radius:8px;border:1px solid #555;font-size:12px;">
  <b>Railway Buffer Zone ($geoWithin $box)</b><br>
  <span style="color:#FFD700">━━</span> Railway lines<br>
  Dashed boxes = $box bounding queries<br>
  Numbers = development pressure/km²<br>
  Heatmap = building density
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Railway Buffer Zone Analysis ($geoWithin $box) computed successfully")
display(m)

print("\nRailway Buffer Zone — Development Pressure Ranking:")
for i, rec in enumerate(results):
    print(f"  #{i+1}: {rec['name']:40s} | Pressure: {rec['pressure']:6.2f}/km² | Buildings: {rec['buildings']}")
