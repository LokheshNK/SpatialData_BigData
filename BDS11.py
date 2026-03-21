"""
Question 11: Flood-Building Intersection Analysis

Spatial Query Types Used:
  - $geoIntersects + $geometry  (INTERSECTION query — primary)
  - Cross-collection: water geometry intersected with buildings

Concept:
  Define flood-risk polygon zones around water bodies.
  Use $geoIntersects to find ALL buildings whose geometry intersects
  with the flood zone polygons. These are at-risk structures.

Visualization:
  - Flood zone polygon overlays
  - At-risk buildings highlighted as red markers
  - Safe buildings as gray dots (sample)
  - Count badge per flood zone
"""

from pymongo import MongoClient
import folium
import numpy as np
from IPython.display import display

client    = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db        = client["bigdata_spatial"]
buildings = db.buildings
water     = db.water

buildings.create_index([("geometry", "2dsphere")])

# ── Flood zone polygons (low-lying, near water) ──────────────────────────────
FLOOD_POLYGONS = [
    {
        "name":  "Noyyal River Floodplain",
        "coords": [
            [76.955, 11.018], [76.995, 11.018],
            [76.995, 11.005], [76.955, 11.005], [76.955, 11.018]
        ],
        "color": "#B71C1C"
    },
    {
        "name":  "Ukkadam Tank Overflow Zone",
        "coords": [
            [76.962, 10.988], [76.983, 10.988],
            [76.983, 10.972], [76.962, 10.972], [76.962, 10.988]
        ],
        "color": "#E53935"
    },
    {
        "name":  "Singanallur Lake Buffer",
        "coords": [
            [77.012, 10.996], [77.038, 10.996],
            [77.038, 10.978], [77.012, 10.978], [77.012, 10.996]
        ],
        "color": "#F57C00"
    },
]

results = []
for zone in FLOOD_POLYGONS:
    # $geoIntersects finds buildings that geometrically touch/overlap the flood zone
    intersect_query = {
        "geometry": {
            "$geoIntersects": {
                "$geometry": {
                    "type": "Polygon",
                    "coordinates": [zone["coords"]]
                }
            }
        }
    }

    at_risk_docs = list(buildings.find(
        intersect_query,
        {"geometry.coordinates": 1, "_id": 0}
    ).limit(200))

    # Also get the total count
    at_risk_count = buildings.count_documents(intersect_query)

    at_risk_points = []
    for doc in at_risk_docs:
        try:
            coords = doc["geometry"]["coordinates"]
            if isinstance(coords[0], list):
                ring  = coords[0]
                b_lon = sum(p[0] for p in ring) / len(ring)
                b_lat = sum(p[1] for p in ring) / len(ring)
            else:
                b_lon, b_lat = coords[0], coords[1]
            at_risk_points.append([b_lon, b_lat])
        except Exception:
            continue

    results.append({
        "name":       zone["name"],
        "coords":     zone["coords"],
        "color":      zone["color"],
        "count":      at_risk_count,
        "points":     at_risk_points
    })

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

for zone in results:
    latlngs = [[p[1], p[0]] for p in zone["coords"]]

    # Flood zone polygon
    folium.Polygon(
        locations=latlngs,
        fill=True,
        fill_color=zone["color"],
        fill_opacity=0.2,
        color=zone["color"],
        weight=2.5,
        popup=f"<b>{zone['name']}</b><br>Buildings at risk: <b>{zone['count']}</b>",
        tooltip=f"{zone['name']}: {zone['count']} buildings at risk"
    ).add_to(m)

    # Centroid label
    cent_lat = sum(p[1] for p in zone["coords"]) / len(zone["coords"])
    cent_lon = sum(p[0] for p in zone["coords"]) / len(zone["coords"])
    badge_html = f"""
    <div style="background:{zone['color']};color:white;font-weight:bold;
                border-radius:12px;padding:3px 8px;font-size:11px;
                white-space:nowrap;border:2px solid white;
                box-shadow:0 1px 4px rgba(0,0,0,0.3);">
      {zone['count']} buildings at risk
    </div>"""
    folium.Marker(
        location=[cent_lat, cent_lon],
        icon=folium.DivIcon(html=badge_html, icon_size=(150, 24), icon_anchor=(75, 12))
    ).add_to(m)

    # At-risk building markers
    for pt in zone["points"]:
        folium.CircleMarker(
            location=[pt[1], pt[0]],
            radius=3,
            color=zone["color"],
            fill=True,
            fill_color=zone["color"],
            fill_opacity=0.75,
            tooltip="At-risk building"
        ).add_to(m)

# Water body dots for context
water_docs = water.find({}, {"geometry.coordinates": 1, "_id": 0}).limit(80)
for doc in water_docs:
    try:
        coords = doc["geometry"]["coordinates"]
        if isinstance(coords[0], (int, float)):
            w_lon, w_lat = coords[0], coords[1]
        else:
            ring  = coords[0]
            w_lon = sum(p[0] for p in ring) / len(ring)
            w_lat = sum(p[1] for p in ring) / len(ring)
        if 76.85 <= w_lon <= 77.10 and 10.92 <= w_lat <= 11.15:
            folium.CircleMarker(
                location=[w_lat, w_lon],
                radius=5,
                color="#1565C0",
                fill=True,
                fill_color="#42A5F5",
                fill_opacity=0.8,
                tooltip="Water body"
            ).add_to(m)
    except Exception:
        continue

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Flood-Building Intersection ($geoIntersects)</b><br>
  Colored polygon = flood zone<br>
  Colored dots = buildings at risk ($geoIntersects)<br>
  <span style="color:#42A5F5">●</span> Water bodies
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Flood-Building Intersection ($geoIntersects) computed successfully")
display(m)

total = sum(z["count"] for z in results)
print(f"\nFlood Intersection Results:")
for z in results:
    print(f"  {z['name']:35s} | Buildings at risk: {z['count']}")
print(f"\n  TOTAL buildings intersecting flood zones: {total}")
