"""
Question 9: Flood Risk Index (FRI)

Spatial Query Types Used:
  - $geoWithin + $geometry (POLYGON range query — not just circles)
  - $geoWithin + $centerSphere  (circle range query for comparison)
  - Multi-collection count within polygons

Concept:
  Define 5 flood-risk polygons (low-lying areas near water bodies in Coimbatore).
  Count buildings, roads, and water features within each polygon using $geoWithin.
  Score each polygon as a flood risk zone.

Visualization:
  - Colored GeoJSON polygon overlays (flood zones)
  - Water body points as blue markers
  - Buildings within high-risk zones highlighted in red
"""

from pymongo import MongoClient
import folium
import numpy as np
from IPython.display import display

client    = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db        = client["bigdata_spatial"]
buildings = db.buildings
roads     = db.roads
water     = db.water

# ── Define flood-risk polygon zones (hand-crafted around low-lying areas) ────
FLOOD_ZONES = [
    {
        "name": "Noyyal Riverbank North",
        "risk_category": "High",
        "polygon": [
            [76.960, 11.030], [76.990, 11.030],
            [76.990, 11.010], [76.960, 11.010], [76.960, 11.030]
        ]
    },
    {
        "name": "Ukkadam Lake Buffer",
        "risk_category": "High",
        "polygon": [
            [76.960, 10.990], [76.985, 10.990],
            [76.985, 10.970], [76.960, 10.970], [76.960, 10.990]
        ]
    },
    {
        "name": "Singanallur Tank Zone",
        "risk_category": "Medium",
        "polygon": [
            [77.010, 10.998], [77.040, 10.998],
            [77.040, 10.975], [77.010, 10.975], [77.010, 10.998]
        ]
    },
    {
        "name": "Krishnampathi Area",
        "risk_category": "Medium",
        "polygon": [
            [76.940, 11.055], [76.970, 11.055],
            [76.970, 11.040], [76.940, 11.040], [76.940, 11.055]
        ]
    },
    {
        "name": "Kovaipudur Lowlands",
        "risk_category": "Low",
        "polygon": [
            [76.895, 10.975], [76.920, 10.975],
            [76.920, 10.960], [76.895, 10.960], [76.895, 10.975]
        ]
    },
]

RISK_COLORS = {"High": "#D32F2F", "Medium": "#F57C00", "Low": "#388E3C"}

results = []
for zone in FLOOD_ZONES:
    poly_coords = zone["polygon"]

    geo_query = {
        "geometry": {
            "$geoWithin": {
                "$geometry": {
                    "type": "Polygon",
                    "coordinates": [poly_coords]  # $geoWithin polygon query
                }
            }
        }
    }

    b = buildings.count_documents(geo_query)
    r = roads.count_documents(geo_query)
    w = water.count_documents(geo_query)

    fri = round(0.5*w + 0.3*b + 0.2*r, 2)
    results.append({
        "name":     zone["name"],
        "risk":     zone["risk_category"],
        "polygon":  poly_coords,
        "buildings": b, "roads": r, "water": w,
        "FRI":      fri
    })

results.sort(key=lambda x: x["FRI"], reverse=True)

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

for zone in results:
    color    = RISK_COLORS[zone["risk"]]
    # Convert polygon to [[lat,lon]] for folium
    latlngs  = [[p[1], p[0]] for p in zone["polygon"]]

    folium.Polygon(
        locations=latlngs,
        fill=True,
        fill_color=color,
        fill_opacity=0.45,
        color=color,
        weight=2.5,
        popup=(
            f"<b>{zone['name']}</b><br>"
            f"Risk Level: <b>{zone['risk']}</b><br>"
            f"FRI: {zone['FRI']}<br>"
            f"Water Bodies: {zone['water']}<br>"
            f"Buildings: {zone['buildings']}<br>"
            f"Roads: {zone['roads']}"
        ),
        tooltip=f"{zone['name']} — {zone['risk']} Risk"
    ).add_to(m)

    # Zone label at centroid
    cent_lat = sum(p[1] for p in zone["polygon"]) / len(zone["polygon"])
    cent_lon = sum(p[0] for p in zone["polygon"]) / len(zone["polygon"])
    label_html = f"""
    <div style="font-size:10px;font-weight:bold;color:{color};
                background:rgba(255,255,255,0.85);padding:2px 5px;
                border-radius:4px;white-space:nowrap;">
      {zone['name'].split()[0]}
    </div>"""
    folium.Marker(
        location=[cent_lat, cent_lon],
        icon=folium.DivIcon(html=label_html, icon_size=(90, 20), icon_anchor=(45, 10))
    ).add_to(m)

# Water body points from DB
water_docs = water.find(
    {
        "geometry.coordinates.0.0": {
            "$elemMatch": {"$gte": 76.85}
        }
    },
    {"geometry": 1, "_id": 0}
).limit(100)

for doc in water_docs:
    try:
        coords = doc["geometry"]["coordinates"]
        if isinstance(coords[0], (int, float)):
            w_lon, w_lat = coords[0], coords[1]
        else:
            ring  = coords[0]
            w_lon = sum(p[0] for p in ring) / len(ring)
            w_lat = sum(p[1] for p in ring) / len(ring)
        folium.CircleMarker(
            location=[w_lat, w_lon],
            radius=4,
            color="#1565C0",
            fill=True,
            fill_color="#42A5F5",
            fill_opacity=0.7,
            tooltip="Water body"
        ).add_to(m)
    except Exception:
        continue

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Flood Risk Index ($geoWithin polygon)</b><br>
  <span style="color:#D32F2F">■</span> High risk zone<br>
  <span style="color:#F57C00">■</span> Medium risk zone<br>
  <span style="color:#388E3C">■</span> Low risk zone<br>
  <span style="color:#42A5F5">●</span> Water bodies
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Flood Risk Index ($geoWithin polygon) computed successfully")
display(m)

print("\nFlood Risk Zone Results:")
for z in results:
    print(f"  {z['name']:35s} | Risk: {z['risk']:6s} | FRI: {z['FRI']:6.2f} | "
          f"Water: {z['water']} | Buildings: {z['buildings']}")
