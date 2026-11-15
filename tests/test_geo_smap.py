import json

import pytest
from shapely.geometry import box

from raices_profundas.geo import load_roi, make_grid
from raices_profundas.smap import month_window, seasonal_months


def test_make_grid_covers_roi():
    roi = box(-88.5, 14.0, -88.0, 14.5)
    grid = make_grid(roi, step=0.5)
    assert len(grid) == 1
    assert grid.iloc[0]["cell_id"] == "C0000"
    assert grid.crs.to_epsg() == 4326


def test_make_grid_partial_cells():
    # ROI desplazado respecto a la grilla genera celdas parciales
    roi = box(-88.3, 14.2, -87.8, 14.7)
    grid = make_grid(roi, step=0.5)
    assert len(grid) >= 2
    assert all(cell.intersects(roi) for cell in grid.geometry)


def test_load_roi_feature_collection(tmp_path):
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {},
             "geometry": {"type": "Polygon", "coordinates": [[
                 [-88.5, 14.0], [-88.0, 14.0], [-88.0, 14.5],
                 [-88.5, 14.5], [-88.5, 14.0]]]}},
        ],
    }
    path = tmp_path / "roi.geojson"
    path.write_text(json.dumps(geojson))
    geometry = load_roi(path)
    assert not geometry.is_empty
    assert geometry.bounds == pytest.approx((-88.5, 14.0, -88.0, 14.5))


def test_load_roi_rejects_empty(tmp_path):
    path = tmp_path / "empty.geojson"
    path.write_text(json.dumps({"type": "FeatureCollection", "features": []}))
    with pytest.raises(ValueError):
        load_roi(path)


def test_seasonal_months_exclusive_end():
    assert list(seasonal_months(5, 9)) == [5, 6, 7, 8]


def test_seasonal_months_wraparound():
    assert list(seasonal_months(11, 2)) == [11, 12, 1]


def test_seasonal_months_rejects_invalid():
    with pytest.raises(ValueError):
        list(seasonal_months(0, 5))
    with pytest.raises(ValueError):
        list(seasonal_months(5, 13))


def test_month_window_december_rolls_over():
    start, end = month_window(2025, 12)
    assert start == __import__("datetime").datetime(2025, 12, 1)
    assert end == __import__("datetime").datetime(2026, 1, 1)
