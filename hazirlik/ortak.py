"""Ortak ızgara ve yardımcılar — İzmir besi çiftliği yer seçimi."""
import json
from pathlib import Path

import numpy as np
from pyproj import Transformer
from rasterio.transform import from_origin
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, shape
from shapely.ops import polygonize, unary_union, transform as shp_transform

KOK = Path(__file__).parent
HAM = KOK / "ham"
ARA = KOK / "ara"
ARA.mkdir(exist_ok=True)

CRS = "EPSG:32635"           # UTM 35N, metre
HUCRE = 50                   # m
TO_UTM = Transformer.from_crs("EPSG:4326", CRS, always_xy=True).transform
TO_WGS = Transformer.from_crs(CRS, "EPSG:4326", always_xy=True).transform


def osm(ad):
    return json.loads((HAM / f"{ad}.json").read_text(encoding="utf-8"))["elements"]


def yol_geom(e):
    """Overpass 'out geom' öğesini shapely geometriye çevirir (WGS84)."""
    if e["type"] == "node":
        return Point(e["lon"], e["lat"])
    if e["type"] == "way":
        pts = [(p["lon"], p["lat"]) for p in e.get("geometry", [])]
        if len(pts) < 2:
            return None
        if pts[0] == pts[-1] and len(pts) >= 4 and _alan_mi(e):
            return Polygon(pts)
        return LineString(pts)
    if e["type"] == "relation":
        cizgiler = []
        for m in e.get("members", []):
            g = m.get("geometry")
            if g and len(g) >= 2:
                cizgiler.append(LineString([(p["lon"], p["lat"]) for p in g]))
        if not cizgiler:
            return None
        polys = list(polygonize(unary_union(cizgiler)))
        return unary_union(polys) if polys else None
    return None


def _alan_mi(e):
    t = e.get("tags", {})
    return any(k in t for k in ("landuse", "natural", "power", "building", "area")) and t.get("natural") != "coastline"


def izmir_siniri():
    rel = [e for e in osm("sinir") if e["type"] == "relation"][0]
    return yol_geom(rel)


def utm(g):
    return shp_transform(TO_UTM, g)


def wgs(g):
    return shp_transform(TO_WGS, g)


def izgara(sinir_utm):
    minx, miny, maxx, maxy = sinir_utm.bounds
    minx, miny = np.floor(minx / HUCRE) * HUCRE - 500, np.floor(miny / HUCRE) * HUCRE - 500
    maxx, maxy = np.ceil(maxx / HUCRE) * HUCRE + 500, np.ceil(maxy / HUCRE) * HUCRE + 500
    w = int((maxx - minx) / HUCRE)
    h = int((maxy - miny) / HUCRE)
    return from_origin(minx, maxy, HUCRE, HUCRE), (h, w)
