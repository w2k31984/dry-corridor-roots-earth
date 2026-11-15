"""Reanuda el pipeline tras una interrupción: procesa desde disco los meses
cuyo directorio granules/AAAA-MM/ ya tiene GeoTIFFs y solo envía a Harmony
los meses faltantes. Luego genera las mismas salidas que run_pipeline.

Uso: python scripts/resume_pipeline.py [--out outputs]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402

from raices_profundas.smap import get_smap_series  # noqa: E402
from raices_profundas.stats import (  # noqa: E402
    add_climate_classification,
    project_moisture,
    trend_table,
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    parser.add_argument("--climate-csv", type=Path)
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2026)
    parser.add_argument("--projection-end-year", type=int, default=2030)
    parser.add_argument("--start-month", type=int, default=5)
    parser.add_argument("--end-month", type=int, default=9)
    parser.add_argument("--granule-stride", type=int, default=3)
    args = parser.parse_args()

    out = args.out
    roi_path = out / "roi_harmony.geojson"
    grid = gpd.read_file(out / "grid.geojson")

    series = get_smap_series(
        roi_path, grid, range(args.start_year, args.end_year),
        args.start_month, args.end_month, out,
        granule_stride=args.granule_stride, process_local=True,
    )
    series.to_csv(out / "smap_observations.csv", index=False)

    annual = series.groupby(["cell_id", "year"], as_index=False)["rootzone_moisture"].mean()
    annual.to_csv(out / "smap_seasonal_timeseries.csv", index=False)

    trends = add_climate_classification(trend_table(series), args.climate_csv)
    result = grid.merge(trends, on="cell_id", how="left")
    result.to_file(out / "smap_trends.geojson", driver="GeoJSON")
    result.drop(columns="geometry").to_csv(out / "smap_trends.csv", index=False)

    projections = project_moisture(series, args.projection_end_year)
    if projections.empty:
        raise RuntimeError("No hay suficientes años por celda para generar proyecciones.")
    projections.to_csv(out / "smap_projection.csv", index=False)

    projection_wide = projections.pivot(index="cell_id", columns="forecast_year", values="change_from_baseline")
    projection_wide.columns = [f"change_{year}" for year in projection_wide.columns]
    projection_grid = grid.merge(projection_wide.reset_index(), on="cell_id", how="left")
    projection_grid.to_file(out / "smap_projection.geojson", driver="GeoJSON")
    print(f"Resultados listos en {out.resolve()}")


if __name__ == "__main__":
    main()
