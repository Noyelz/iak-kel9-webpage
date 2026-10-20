"""Peta choropleth jumlah penduduk; batas 38 provinsi, bukan kepadatan."""
from functools import lru_cache
import json
import math
from pathlib import Path

MAP_FILE = Path(__file__).parent / "static/dashboard/maps/indonesia-38-provinces.geojson"
# Nilai batas dalam jiwa; tetap sama untuk setiap tahun.
BINS = [
    (1_000_000, "< 1 juta", "#d1fae5"),
    (5_000_000, "1–<5 juta", "#a7f3d0"),
    (10_000_000, "5–<10 juta", "#34d399"),
    (20_000_000, "10–<20 juta", "#059669"),
    (math.inf, "≥ 20 juta", "#065f46"),
]
MISSING_COLOR = "#d1d5db"


def province_key(name):
    key = " ".join(name.casefold().split())
    return {"daerah istimewa yogyakarta": "di yogyakarta"}.get(key, key)


def population_color(people):
    if people is None:
        return MISSING_COLOR, "Data tidak tersedia"
    for upper, label, color in BINS:
        if people < upper:
            return color, label
    return BINS[-1][2], BINS[-1][1]


@lru_cache(maxsize=1)
def map_shapes():
    """Proyeksi Mercator ke SVG lokal. Ring bagian dalam dipertahankan."""
    geo = json.loads(MAP_FILE.read_text(encoding="utf-8-sig"))
    features = []
    for feature in geo["features"]:
        geometry = feature["geometry"]
        if geometry["type"] == "Polygon":
            polygons = [geometry["coordinates"]]
        elif geometry["type"] == "MultiPolygon":
            polygons = geometry["coordinates"]
        else:
            raise ValueError("Geometri provinsi harus Polygon/MultiPolygon")
        features.append((feature["properties"]["PROVINSI"], polygons))
    def mercator(point):
        lon, lat = point[:2]
        return math.radians(lon), -math.log(math.tan(math.pi/4+math.radians(lat)/2))
    points = [mercator(point) for _, polygons in features for polygon in polygons for ring in polygon for point in ring]
    min_x, max_x = min(p[0] for p in points), max(p[0] for p in points)
    min_y, max_y = min(p[1] for p in points), max(p[1] for p in points)
    width, height, pad = 960, 390, 18
    scale = min((width-2*pad)/(max_x-min_x), (height-2*pad)/(max_y-min_y))
    offset_x, offset_y = (width-(max_x-min_x)*scale)/2, (height-(max_y-min_y)*scale)/2
    result = []
    for name, polygons in features:
        rings = []
        for polygon in polygons:
            for ring in polygon:
                projected = [mercator(p) for p in ring]
                path = " ".join(f"{(x-min_x)*scale+offset_x:.2f},{(y-min_y)*scale+offset_y:.2f}" for x,y in projected)
                rings.append("M" + path + "Z")
        result.append({"name": name, "key": province_key(name), "path": " ".join(rings)})
    return result


def build_population_map(population, year):
    rows = {province_key(r["nama_provinsi"]): r for r in population if int(r["tahun"]) == year and not r["is_nasional"]}
    features, records = [], []
    for shape in map_shapes():
        row = rows.get(shape["key"], {})
        value = row.get("jumlah_penduduk_ribu")
        people = None if value is None else round(float(value)*1000)
        color, category = population_color(people)
        name = row.get("nama_provinsi", shape["name"])
        record = {"key": shape["key"], "name": name, "people": people, "color": color, "category": category}
        records.append(record)
        features.append({**shape, **record})
    records.sort(key=lambda r: r["name"])
    available = sum(r["people"] is not None for r in records)
    return {
        "year": year, "features": features,
        "legend": [{"label": label, "color": color} for _, label, color in BINS],
        "available": available, "missing": len(records)-available,
        "payload": {"year": year, "provinces": records},
    }
