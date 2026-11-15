"""Acceso a datos SMAP vía earthaccess + Harmony y reducción de GeoTIFFs."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import earthaccess
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from harmony import CapabilitiesRequest, Client, Collection, Request
from rasterio.features import rasterize

from .config import VARIABLE
from .geo import load_roi


def seasonal_months(start_month: int, end_month: int):
    """Meses en [start_month, end_month), con wraparound (p. ej. 11→2 da 11, 12, 1)."""
    if not (1 <= start_month <= 12 and 1 <= end_month <= 12):
        raise ValueError("Los meses deben estar entre 1 y 12")
    month = start_month
    while month != end_month:
        yield month
        month = month % 12 + 1


def month_window(year: int, month: int):
    start = datetime(year, month, 1)
    end = datetime(year + (month == 12), month % 12 + 1, 1)
    return start, end


def get_capability_id(client: Client) -> str:
    result = client.submit(CapabilitiesRequest(short_name="SPL4SMGP"))
    capabilities = json.loads(result) if isinstance(result, str) else result
    collection_id = capabilities.get("conceptId")
    if not collection_id:
        raise RuntimeError(f"Harmony no devolvió conceptId para SPL4SMGP: {capabilities}")
    return collection_id


def reduce_tiff(path: Path, grid: gpd.GeoDataFrame):
    """Promedia los píxeles válidos de un GeoTIFF por celda de la grilla."""
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError(f"El GeoTIFF no trae CRS: {path.name}")
        if src.crs.to_epsg() != 4326:
            grid_in_crs = grid.to_crs(src.crs)
        else:
            grid_in_crs = grid
        data = src.read(1, masked=True)
        labels = rasterize(
            ((geom, idx + 1) for idx, geom in enumerate(grid_in_crs.geometry)),
            out_shape=data.shape,
            transform=src.transform,
            fill=0,
            all_touched=False,
            dtype="int32",
        )
    values = np.asarray(data.filled(np.nan), dtype="float64")
    valid = (labels > 0) & np.isfinite(values)
    sums = np.bincount(labels[valid], weights=values[valid], minlength=len(grid) + 1)
    counts = np.bincount(labels[valid], minlength=len(grid) + 1)
    return [(grid.iloc[i - 1].cell_id, sums[i] / counts[i])
            for i in range(1, len(counts)) if counts[i] > 0]


def timestamp_from_name(path: Path):
    match = re.search(r"(20\d{6}T\d{6})", path.name)
    if not match:
        return None
    return datetime.strptime(match.group(1), "%Y%m%dT%H%M%S")


def get_smap_series(roi_path: Path, grid: gpd.GeoDataFrame, years, start_month, end_month, output: Path,
                    granule_stride: int = 1):
    earthaccess.login()
    token = earthaccess.get_edl_token()
    client = Client(token=token) if token else Client()
    collection = Collection(id=get_capability_id(client))
    bounds = load_roi(roi_path).bounds
    results = []
    processed = 0

    for year in years:
        for month in seasonal_months(start_month, end_month):
            start, stop = month_window(year, month)
            discovery = earthaccess.search_data(
                short_name="SPL4SMGP", version="008",
                bounding_box=bounds, temporal=(start.isoformat(), stop.isoformat()), count=500,
            )
            if not discovery:
                print(f"Sin granules para {year}-{month:02d}; se omite.")
                continue
            request = Request(
                collection=collection,
                temporal={"start": start, "stop": stop},
                shape=str(roi_path),
                variables=[VARIABLE],
                crs="EPSG:4326",
                format="image/tiff",
                max_results=300,
                ignore_errors=True,
            )
            job_id = client.submit(request)
            if isinstance(job_id, str):
                client.wait_for_processing(job_id, show_progress=True)
            month_dir = output / "granules" / f"{year}-{month:02d}"
            month_dir.mkdir(parents=True, exist_ok=True)
            if granule_stride > 1:
                # Descarga solo 1 de cada N granulos (~uniforme en el tiempo) para
                # reducir volumen; el promedio mensual apenas cambia.
                urls = list(client.result_urls(job_id))
                urls.sort(key=lambda u: timestamp_from_name(Path(u)) or datetime.min)
                selected = urls[::granule_stride]
                futures = [client.download(url, directory=str(month_dir)) for url in selected]
            else:
                futures = client.download_all(job_id, directory=str(month_dir), overwrite=False)
            files = [Path(future.result()) for future in futures]
            for tif in files:
                timestamp = timestamp_from_name(tif)
                if timestamp is None:
                    print(f"No pude leer fecha del nombre; se omite: {tif.name}")
                    continue
                for cell_id, value in reduce_tiff(tif, grid):
                    results.append({"cell_id": cell_id, "year": year, "month": month,
                                    "timestamp": timestamp.isoformat(), "rootzone_moisture": value})
            processed += len(files)
            print(f"{year}-{month:02d}: {len(files)} archivos subset descargados.")
    if not results:
        raise RuntimeError("No se generaron observaciones. Revisa autenticación NASA, ROI, fechas y respuesta Harmony.")
    print(f"Total de archivos procesados: {processed}")
    return pd.DataFrame(results)
