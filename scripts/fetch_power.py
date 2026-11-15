"""Descarga variables MERRA-2 (NASA POWER) para cada celda de la grilla.

Uso: python scripts/fetch_power.py [--start 1981] [--end 2025] [--out data]
Genera `power_monthly.csv` (cell_id, variable, year, month, value) y `cells.csv`
(cell_id, lat, lon, elevation_m, place, country). No requiere credenciales.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import geopandas as gpd

from raices_profundas.places import nearest_place
from raices_profundas.power import fetch_grid

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", type=Path, default=ROOT / "data" / "smap_trends.geojson")
    parser.add_argument("--start", type=int, default=1981)
    parser.add_argument("--end", type=int, default=2025)
    parser.add_argument("--out", type=Path, default=ROOT / "data")
    args = parser.parse_args()

    grid = gpd.read_file(args.grid)[["cell_id", "geometry"]]
    monthly, cells = fetch_grid(grid, args.start, args.end)
    places = cells.apply(lambda r: nearest_place(r.lat, r.lon)[:2], axis=1, result_type="expand")
    cells[["place", "country"]] = places
    args.out.mkdir(parents=True, exist_ok=True)
    monthly.dropna(subset=["value"]).round({"value": 4}).to_csv(args.out / "power_monthly.csv", index=False)
    cells.round({"lat": 4, "lon": 4, "elevation_m": 1}).to_csv(args.out / "cells.csv", index=False)
    print(f"Guardado en {args.out}: {len(monthly)} valores, {len(cells)} celdas")


if __name__ == "__main__":
    main()
