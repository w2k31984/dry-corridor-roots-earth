"""Descarga de variables mensuales MERRA-2 vía la API de NASA POWER (sin credenciales)."""
from __future__ import annotations

import json
import time
from urllib.parse import urlencode
from urllib.request import urlopen

import geopandas as gpd
import numpy as np
import pandas as pd

POWER_MONTHLY_URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
POWER_PARAMETERS = ["PRECTOTCORR", "T2M", "T2M_MAX", "GWETROOT", "GWETTOP", "RH2M", "EVLAND"]


def fetch_point(lat: float, lon: float, start_year: int, end_year: int,
                parameters=POWER_PARAMETERS, retries: int = 3) -> tuple[pd.DataFrame, float]:
    """Serie mensual de un punto. Devuelve (DataFrame largo, elevación en m)."""
    query = urlencode({
        "parameters": ",".join(parameters), "community": "AG",
        "latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}",
        "start": start_year, "end": end_year, "format": "JSON",
    })
    for attempt in range(retries):
        try:
            with urlopen(f"{POWER_MONTHLY_URL}?{query}", timeout=120) as response:
                payload = json.load(response)
            break
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    fill = payload.get("header", {}).get("fill_value", -999.0)
    rows = []
    for variable, values in payload["properties"]["parameter"].items():
        for key, value in values.items():
            month = int(key[4:])
            if month == 13:  # promedio anual calculado por POWER
                continue
            rows.append({"year": int(key[:4]), "month": month, "variable": variable,
                         "value": np.nan if value == fill else float(value)})
    elevation = float(payload["geometry"]["coordinates"][2])
    return pd.DataFrame(rows), elevation


def fetch_grid(grid: gpd.GeoDataFrame, start_year: int, end_year: int,
               parameters=POWER_PARAMETERS) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Descarga POWER en el punto representativo de cada celda.

    Devuelve (observaciones mensuales, metadatos de celda con lat/lon/elevación).
    """
    points = grid.geometry.representative_point()
    frames, cells = [], []
    for cell_id, point in zip(grid["cell_id"], points):
        data, elevation = fetch_point(point.y, point.x, start_year, end_year, parameters)
        frames.append(data.assign(cell_id=cell_id))
        cells.append({"cell_id": cell_id, "lat": point.y, "lon": point.x, "elevation_m": elevation})
        print(f"{cell_id}: {len(data)} valores")
    monthly = pd.concat(frames, ignore_index=True)[["cell_id", "variable", "year", "month", "value"]]
    return monthly, pd.DataFrame(cells)
