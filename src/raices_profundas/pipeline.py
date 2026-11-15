"""Orquestación del pipeline: ROI → grilla → serie SMAP → tendencias → proyección."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .geo import (
    count_coordinates,
    download_fao_roi,
    load_roi,
    make_grid,
    simplify_roi,
    write_geometry_geojson,
)
from .smap import get_smap_series
from .stats import add_climate_classification, project_moisture, trend_table


def run_pipeline(
    *,
    roi: Path | None,
    download_fao: bool,
    out: Path,
    climate_csv: Path | None = None,
    start_year: int = 2015,
    end_year: int = 2026,
    projection_end_year: int = 2030,
    start_month: int = 5,
    end_month: int = 9,
    grid_degrees: float = 1.0,
    min_history: int = 5,
    granule_stride: int = 1,
) -> dict[str, Path]:
    """Ejecuta el pipeline completo y devuelve las rutas de los archivos generados."""
    out.mkdir(parents=True, exist_ok=True)
    if roi is None and download_fao:
        roi = out / "corredor_seco_fao.geojson"
        download_fao_roi(roi)
    if roi is None:
        raise ValueError("Indica un ROI (roi=...) o activa download_fao=True")

    roi_geometry = load_roi(roi)
    roi_simplified = simplify_roi(roi_geometry)
    n_before, n_after = count_coordinates(roi_geometry), count_coordinates(roi_simplified)
    if n_after < n_before:
        print(f"ROI simplificado para Harmony: {n_before} → {n_after} vértices")
    roi_path = out / "roi_harmony.geojson"
    write_geometry_geojson(roi_simplified, roi_path)

    grid = make_grid(roi_simplified, grid_degrees)
    grid.to_file(out / "grid.geojson", driver="GeoJSON")

    series = get_smap_series(roi_path, grid, range(start_year, end_year),
                             start_month, end_month, out,
                             granule_stride=granule_stride)
    series.to_csv(out / "smap_observations.csv", index=False)

    annual = series.groupby(["cell_id", "year"], as_index=False)["rootzone_moisture"].mean()
    annual.to_csv(out / "smap_seasonal_timeseries.csv", index=False)

    trends = add_climate_classification(trend_table(series), climate_csv)
    result = grid.merge(trends, on="cell_id", how="left")
    result.to_file(out / "smap_trends.geojson", driver="GeoJSON")
    result.drop(columns="geometry").to_csv(out / "smap_trends.csv", index=False)

    projections = project_moisture(series, projection_end_year, min_history=min_history)
    if projections.empty:
        raise RuntimeError("No hay suficientes años por celda para generar proyecciones (se requieren al menos 5).")
    projections.to_csv(out / "smap_projection.csv", index=False)

    projection_wide = projections.pivot(index="cell_id", columns="forecast_year", values="change_from_baseline")
    projection_wide.columns = [f"change_{year}" for year in projection_wide.columns]
    projection_grid = grid.merge(projection_wide.reset_index(), on="cell_id", how="left")
    projection_grid.to_file(out / "smap_projection.geojson", driver="GeoJSON")

    outputs = {
        "grid": out / "grid.geojson",
        "observations": out / "smap_observations.csv",
        "timeseries": out / "smap_seasonal_timeseries.csv",
        "trends_geojson": out / "smap_trends.geojson",
        "trends_csv": out / "smap_trends.csv",
        "projection_csv": out / "smap_projection.csv",
        "projection_geojson": out / "smap_projection.geojson",
    }
    print(f"Resultados listos en {out.resolve()}")
    return outputs
