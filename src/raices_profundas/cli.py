"""Línea de comandos del pipeline de Raíces Profundas."""
from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from .pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="raices-profundas",
        description="Analiza humedad radicular SMAP L4 en el Corredor Seco con NASA Earthdata + Harmony.",
    )
    parser.add_argument("--roi", type=Path, help="GeoJSON del área de estudio (WGS84)")
    parser.add_argument("--download-fao-roi", action="store_true",
                        help="Descarga la delimitación FAO 2012 pública")
    parser.add_argument("--out", type=Path, default=Path("outputs"))
    parser.add_argument("--climate-csv", type=Path,
                        help="Tendencias climáticas armonizadas por cell_id")
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2026,
                        help="Año final exclusivo; 2026 incluye 2015–2025")
    parser.add_argument("--projection-end-year", type=int, default=2030,
                        help="Último año de proyección")
    parser.add_argument("--start-month", type=int, default=5)
    parser.add_argument("--end-month", type=int, default=9,
                        help="Mes final exclusivo")
    parser.add_argument("--grid-degrees", type=float, default=1.0)
    parser.add_argument("--granule-stride", type=int, default=1,
                        help="Descarga 1 de cada N granulos por mes (p. ej. 3 ≈ 1 obs/día)")
    return parser


def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not (1 <= args.start_month <= 12 and 1 <= args.end_month <= 12):
        parser.error("--start-month y --end-month deben estar entre 1 y 12")
    if args.start_month == args.end_month:
        parser.error("--start-month y --end-month no pueden ser iguales (el mes final es exclusivo)")
    if args.granule_stride < 1:
        parser.error("--granule-stride debe ser >= 1")
    run_pipeline(
        roi=args.roi,
        download_fao=args.download_fao_roi,
        out=args.out,
        climate_csv=args.climate_csv,
        start_year=args.start_year,
        end_year=args.end_year,
        projection_end_year=args.projection_end_year,
        start_month=args.start_month,
        end_month=args.end_month,
        grid_degrees=args.grid_degrees,
        granule_stride=args.granule_stride,
    )


if __name__ == "__main__":
    main()
