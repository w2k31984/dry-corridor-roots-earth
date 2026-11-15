"""Utilidades geoespaciales: ROI, grilla de análisis y descarga FAO."""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import geopandas as gpd
import numpy as np
from shapely.geometry import box, mapping, shape
from shapely.ops import unary_union

from .config import FAO_CORRIDOR_LAYER


def download_fao_roi(path: Path) -> None:
    query = urlencode({"where": "1=1", "outFields": "*", "outSR": "4326", "f": "geojson"})
    with urlopen(f"{FAO_CORRIDOR_LAYER}?{query}", timeout=60) as response:
        geojson = json.load(response)
    if geojson.get("error") or not geojson.get("features"):
        raise RuntimeError(f"No se pudo obtener el polígono FAO: {geojson.get('error', 'respuesta vacía')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(geojson), encoding="utf-8")


def load_roi(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("type") == "FeatureCollection":
        geometry = unary_union([shape(feature["geometry"]) for feature in data["features"]])
    else:
        geometry = shape(data["geometry"] if data.get("type") == "Feature" else data)
    if geometry.is_empty:
        raise ValueError("El GeoJSON no contiene geometría.")
    return geometry


def make_grid(roi, step: float) -> gpd.GeoDataFrame:
    minx, miny, maxx, maxy = roi.bounds
    rows, cell_number = [], 0
    x = np.floor(minx / step) * step
    while x < maxx:
        y = np.floor(miny / step) * step
        while y < maxy:
            cell = box(x, y, x + step, y + step).intersection(roi)
            if not cell.is_empty and cell.area > 0:
                rows.append({"cell_id": f"C{cell_number:04d}", "geometry": cell})
                cell_number += 1
            y += step
        x += step
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def count_coordinates(geometry) -> int:
    if geometry.geom_type in ("Point", "LineString"):
        return len(geometry.coords)
    if geometry.geom_type == "Polygon":
        return sum(len(ring.coords) for ring in [geometry.exterior, *geometry.interiors])
    return sum(count_coordinates(part) for part in geometry.geoms)


def simplify_roi(geometry, max_points: int = 4500, start_tolerance: float = 0.005):
    """Simplifica el ROI hasta quedar bajo el límite de puntos de Harmony (5000)."""
    simplified = geometry
    tolerance = start_tolerance
    while count_coordinates(simplified) > max_points and tolerance <= 1.0:
        simplified = geometry.simplify(tolerance, preserve_topology=True)
        tolerance *= 2
    return simplified


def write_geometry_geojson(geometry, path: Path) -> None:
    feature = {"type": "Feature", "properties": {}, "geometry": mapping(geometry)}
    payload = {"type": "FeatureCollection", "features": [feature]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
