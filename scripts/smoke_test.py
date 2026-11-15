"""Corrida de humo: 1 año, 2 meses. Valida auth + pipeline sin esperar la corrida completa.

Uso: python scripts/smoke_test.py [--roi RUTA.geojson]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from raices_profundas.pipeline import run_pipeline  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roi", type=Path, help="GeoJSON del ROI (WGS84)")
    parser.add_argument("--download-fao-roi", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("outputs_smoke"))
    args = parser.parse_args()

    run_pipeline(
        roi=args.roi,
        download_fao=args.download_fao_roi,
        out=args.out,
        start_year=2024,
        end_year=2025,
        start_month=5,
        end_month=7,  # solo mayo y junio
        grid_degrees=1.0,  # grilla más gruesa = menos celdas = más rápido
        projection_end_year=2026,
        min_history=1,  # el smoke test solo tiene 1 año de datos
    )


if __name__ == "__main__":
    main()
