"""
Question 12: Road–Water Crossing Risk

Spatial Query Types Used:
  - $geoIntersects + $geometry  (INTERSECTION — cross-collection)
  - Road LineStrings intersected against water Polygon geometries
  - 2dsphere index on both collections

Concept:
  Find road segments that geometrically intersect with water body polygons.
  These represent bridges, fords, or flood-vulnerable road sections.
  High concentration of crossings = infrastructure flood risk zone.

Visualization:
  - Water body polygons in blue
  - All road segments in light gray
  - Intersecting roads (at-risk crossings) highlighted in red/orange
  - Intersection point markers with warning icons
"""

from pymongo import MongoClient
import folium
import numpy as np
from IPython.display import display

client = MongoClient("mongodb+srv://loki:NKVL1183@cluster0.mmcwtwu.mongodb.net/")
db     = client["bigdata_spatial"]
roads  = db.roads
water  = db.water

roads.create_index([("geometry", "2dsphere")])
water.create_index([("geometry", "2dsphere")])

# ── Pull water body polygons from DB ─────────────────────────────────────────
water_docs = list(water.find(
    {"geometry.type": {"$in": ["Polygon", "MultiPolygon"]}},
    {"geometry": 1, "_id": 1}
).limit(50))

print(f"Water polygons found: {len(water_docs)}")

# ── For each water polygon, find roads that intersect it ─────────────────────
crossing_roads = []
checked_road_ids = set()

for wdoc in water_docs:
    intersecting = roads.find(
        {
            "geometry": {
                "$geoIntersects": {
                    "$geometry": wdoc["geometry"]  # $geoIntersects query
                }
            }
        },
        {"geometry": 1, "_id": 1}
    ).limit(20)

    for rdoc in intersecting:
        rid = str(rdoc["_id"])
        if rid not in checked_road_ids:
            checked_road_ids.add(rid)
            crossing_roads.append({
                "road_geometry": rdoc["geometry"],
                "water_id":      str(wdoc["_id"])
            })

print(f"Road segments intersecting water: {len(crossing_roads)}")

# ── Folium Map ────────────────────────────────────────────────────────────────
m = folium.Map(location=[11.0168, 76.9558], zoom_start=12, tiles="cartodbpositron")

# Draw water polygons
for wdoc in water_docs:
    try:
        geo_type = wdoc["geometry"]["type"]
        if geo_type == "Polygon":
            polys = [wdoc["geometry"]["coordinates"]]
        else:
            polys = wdoc["geometry"]["coordinates"]
        for poly in polys:
            latlngs = [[c[1], c[0]] for c in poly[0] if len(c) >= 2]
            if len(latlngs) >= 3:
                folium.Polygon(
                    locations=latlngs,
                    fill=True,
                    fill_color="#1565C0",
                    fill_opacity=0.45,
                    color="#1565C0",
                    weight=1.5
                ).add_to(m)
    except Exception:
        continue

# Draw a sample of non-crossing roads (light gray for context)
sample_roads = roads.find(
    {"geometry.type": "LineString"},
    {"geometry.coordinates": 1, "_id": 0}
).limit(200)
for rdoc in sample_roads:
    try:
        latlngs = [[c[1], c[0]] for c in rdoc["geometry"]["coordinates"] if len(c) >= 2]
        if len(latlngs) >= 2:
            folium.PolyLine(latlngs, color="#BBBBBB", weight=0.7, opacity=0.4).add_to(m)
    except Exception:
        continue

# Draw intersecting roads + approximate crossing markers
for cr in crossing_roads:
    geo  = cr["road_geometry"]
    gtype = geo["type"]
    if gtype == "LineString":
        segs = [geo["coordinates"]]
    elif gtype == "MultiLineString":
        segs = geo["coordinates"]
    else:
        continue

    for seg in segs:
        latlngs = [[c[1], c[0]] for c in seg if len(c) >= 2]
        if len(latlngs) >= 2:
            folium.PolyLine(
                latlngs,
                color="#E53935",
                weight=3,
                opacity=0.85,
                tooltip="Road-water crossing (flood risk)"
            ).add_to(m)

            # Place a warning marker at the midpoint of the segment
            mid_idx = len(latlngs) // 2
            mid_lat, mid_lon = latlngs[mid_idx]
            warn_html = """
            <div style="font-size:14px;background:rgba(255,255,255,0.9);
                        border-radius:50%;width:20px;height:20px;
                        display:flex;align-items:center;justify-content:center;
                        border:1.5px solid #E53935;">⚠</div>"""
            folium.Marker(
                location=[mid_lat, mid_lon],
                popup="Road–water crossing: flood vulnerability point",
                icon=folium.DivIcon(html=warn_html, icon_size=(22, 22), icon_anchor=(11, 11))
            ).add_to(m)

legend_html = f"""
<div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
     padding:10px 14px;border-radius:8px;border:1px solid #ccc;font-size:12px;">
  <b>Road–Water Intersection ($geoIntersects)</b><br>
  <span style="color:#1565C0">■</span> Water bodies<br>
  <span style="color:#BBBBBB">■</span> Regular roads<br>
  <span style="color:#E53935">■</span> At-risk crossings ({len(crossing_roads)})<br>
  ⚠ = crossing vulnerability point
</div>"""
m.get_root().html.add_child(folium.Element(legend_html))

print("Road–Water Crossing Risk ($geoIntersects) computed successfully")
display(m)
print(f"\nTotal road-water crossings found: {len(crossing_roads)}")
print(f"Water polygons analyzed: {len(water_docs)}")
