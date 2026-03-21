"""
Question 13: POI Density by District (Aggregation Pipeline + $geoNear)

Spatial Query Types Used:
  - $geoNear aggregation stage  (AGGREGATION PIPELINE with spatial)
  - $group + $count (aggregation)
  - $bucket (distance banding)

Concept:
  Use MongoDB's $geoNear aggregation stage to compute distances from a
  reference point, then group POIs by distance band to build a
  density-by-distance profile. Repeat for 5 district centres.

Visualization:
  - Bubble map: circle size = POI count within 2 km of each district
  - Distance band rings around each district
  - Bar-style tooltips showing category breakdown
"""

from pymongo import MongoClient
import folium
import numpy as np
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
]

DISTANCE_BANDS = [500, 1000, 2000]  # metres

results = []
for district in DISTRICTS:
    lon, lat = district["coords"]

    # $geoNear aggregation pipeline
    pipeline = [
        {
            "$geoNear": {
                "near":          {"type": "Point", "coordinates": [lon, lat]},
                "distanceField": "dist_m",
                "maxDistance":   2000,  # 2 km
                "spherical":     True
            }
        },
        {
            "$bucket": {
                "groupBy": "$dist_m",
                "boundaries": [0, 500, 1000, 2000],
                "default": "beyond_2km",
                "output": {"count": {"$sum": 1}}
            }
        }
    ]

    band_result = list(pois.aggregate(pipeline))

    # Also get total count within 2 km
    total = pois.count_documents({
        "geometry": {
            "$geoWithin": {
                "$centerSphere": [[lon, lat], 2 / 6378.1]
            }
        }
    })

    # Amenity breakdown via separate $geoNear + $group pipeline
    category_pipeline = [
        {
            "$geoNear": {
                "near":          {"type": "Point", "coordinates": [lon, lat]},
                "distanceField": "dist_m",
                "maxDistance":   2000,
                "spherical":     True
            }
        },
        {
            "$group": {
                "_id":   "$properties.amenity",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_categories = list(pois.aggregate(category_pipeline))

    results.append({
        "name":           district["name"],
        "coords":         [lon, lat],
        "total_pois":     total,
        "bands":          band_result,
        "top_categories": top_categories
    })

results.sort(key=lambda x: x["total_pois"], reverse=True)
max_poi = max(r["total_pois"] for r in results) or 1

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

BUBBLE_COLORS = ["#E53935", "#F57C00", "#FBC02D", "#388E3C", "#1565C0", "#6A1B9A", "#00838F"]

for i, rec in enumerate(results):
    lon, lat    = rec["coords"]
    norm        = rec["total_pois"] / max_poi
    bubble_r    = 300 + norm * 1700  # 300 m to 2000 m
    color       = BUBBLE_COLORS[i % len(BUBBLE_COLORS)]

    # Band rings (500m, 1km, 2km)
    for band_m, opacity in [(2000, 0.08), (1000, 0.12), (500, 0.18)]:
        folium.Circle(
            location=[lat, lon],
            radius=band_m,
            fill=True,
            fill_color=color,
            fill_opacity=opacity,
            color=color,
            weight=0.8,
            opacity=0.4
        ).add_to(m)

    # Build popup text
    cats_text = "<br>".join(
        f"&nbsp;&nbsp;{c['_id'] or 'unknown'}: {c['count']}"
        for c in rec["top_categories"]
    )
    bands_text = "<br>".join(
        f"&nbsp;&nbsp;0–{b['_id']+500 if isinstance(b['_id'], int) else '∞'}m: {b['count']} POIs"
        for b in rec["bands"] if isinstance(b.get("_id"), int)
    )

    folium.Circle(
        location=[lat, lon],
        radius=bubble_r,
        fill=True,
        fill_color=color,
        fill_opacity=0.65,
        color=color,
        weight=1.5,
        popup=(
            f"<b>{rec['name']}</b><br>"
            f"Total POIs (2 km): <b>{rec['total_pois']}</b><br><br>"
            f"<b>By distance:</b><br>{bands_text}<br><br>"
            f"<b>Top categories:</b><br>{cats_text}"
        ),
        tooltip=f"{rec['name']}: {rec['total_pois']} POIs"
    ).add_to(m)

    # District label
    label_html = f"""
    <div style="font-size:11px;font-weight:bold;color:{color};
                background:rgba(255,255,255,0.9);padding:2px 6px;
                border-radius:4px;white-space:nowrap;">
      {rec['name']}<br>
      <span style="font-weight:normal">{rec['total_pois']} POIs</span>
    </div>"""
    folium.Marker(
        location=[lat + 0.008, lon],
        icon=folium.DivIcon(html=label_html, icon_size=(110, 36), icon_anchor=(55, 18))
    ).add_to(m)

legend_html = """
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>POI Density ($geoNear aggregation)</b><br>
  Bubble size = POI count within 2 km<br>
  Rings = 500 m / 1 km / 2 km bands
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("POI Density by District ($geoNear aggregation) computed successfully")
display(m)

print("\nPOI Density Ranking:")
for i, rec in enumerate(results):
    print(f"  #{i+1}: {rec['name']:20s} — {rec['total_pois']} POIs within 2 km")
    if rec["top_categories"]:
        top = rec["top_categories"][0]
        print(f"        Top category: {top['_id']} ({top['count']})")
