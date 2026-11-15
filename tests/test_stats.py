import numpy as np
import pandas as pd
import pytest

from raices_profundas.stats import project_moisture, trend_table


def make_series(cell_id="C0000", start=2015, end=2025, slope=-0.005, noise=0.0):
    rows = []
    rng = np.random.default_rng(42)
    for year in range(start, end + 1):
        value = 0.30 + slope * (year - start) + noise * rng.normal()
        rows.append({"cell_id": cell_id, "year": year, "month": 6,
                     "timestamp": f"{year}-06-01T00:00:00", "rootzone_moisture": value})
    return pd.DataFrame(rows)


def test_trend_table_detects_declining_trend():
    series = make_series()
    table = trend_table(series)
    row = table.iloc[0]
    assert row["cell_id"] == "C0000"
    assert row["n_years"] == 11
    assert row["mk_tau"] < 0
    assert row["mk_p"] < 0.05
    assert row["sen_slope_per_year"] < 0
    assert row["moisture_change_first_last"] < 0


def test_trend_table_multiple_cells():
    series = pd.concat([make_series("C0000"), make_series("C0001", slope=0.0)])
    table = trend_table(series)
    assert set(table["cell_id"]) == {"C0000", "C0001"}


def test_project_moisture_requires_min_history():
    series = make_series(end=2019)  # solo 5 años: justo en el mínimo
    forecasts = project_moisture(series, end_year=2022, min_history=5)
    assert not forecasts.empty
    assert forecasts["forecast_year"].max() == 2022

    short = make_series(end=2018)  # 4 años: por debajo del mínimo
    assert project_moisture(short, end_year=2022).empty


def test_project_moisture_bounds_and_columns():
    series = make_series(noise=0.01)
    forecasts = project_moisture(series, end_year=2030)
    assert {"cell_id", "forecast_year", "forecast_rootzone_moisture",
            "lower_95", "upper_95", "change_from_baseline",
            "sen_slope_per_year", "mk_p", "projection_status"} <= set(forecasts.columns)
    assert forecasts["forecast_rootzone_moisture"].between(0.0, 0.9).all()
    assert (forecasts["lower_95"] <= forecasts["upper_95"]).all()
    assert forecasts["forecast_year"].min() == 2026
