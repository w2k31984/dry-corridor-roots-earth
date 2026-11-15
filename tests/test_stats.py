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


from raices_profundas.stats import (monthly_anomalies, season_series,  # noqa: E402
                                    seasonal_mann_kendall, trend_test)


def make_monthly(start=1990, end=2019, slope=0.05, noise=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for year in range(start, end + 1):
        for month in range(1, 13):
            seasonal = 5 * np.sin(2 * np.pi * month / 12)
            rows.append({"year": year, "month": month,
                         "value": 20 + seasonal + slope * (year - start) + noise * rng.normal()})
    return pd.DataFrame(rows)


def test_trend_test_matches_known_linear_slope():
    x = np.arange(2000, 2020)
    result = trend_test(x, 0.3 * (x - 2000) + 1.0)
    assert result["n"] == 20
    assert result["sen_slope"] == pytest.approx(0.3)
    assert result["ols_slope"] == pytest.approx(0.3)
    assert result["mk_p"] < 0.001 and result["ols_p"] < 0.001
    assert result["sen_low"] <= result["sen_slope"] <= result["sen_high"]


def test_trend_test_no_trend_and_short_series():
    rng = np.random.default_rng(1)
    x = np.arange(2000, 2030)
    result = trend_test(x, rng.normal(size=30))
    assert result["mk_p"] > 0.05
    assert result["ols_low"] < 0 < result["ols_high"]
    assert np.isnan(trend_test([1, 2], [1, 2])["sen_slope"])


def test_seasonal_mann_kendall_ignores_seasonal_cycle():
    trending = seasonal_mann_kendall(make_monthly(slope=0.05, noise=0.2))
    assert trending["smk_p"] < 0.001
    assert trending["seasonal_sen_slope"] == pytest.approx(0.05, abs=0.01)
    flat = seasonal_mann_kendall(make_monthly(slope=0.0, noise=0.2))
    assert flat["smk_p"] > 0.01


def test_season_series_wraparound_keeps_complete_years():
    monthly = make_monthly(start=2000, end=2003, slope=0.0)
    season = season_series(monthly, [12, 1, 2])
    # dic-2000 + ene/feb-2001 → 2001, ..., dic-2002 + ene/feb-2003 → 2003; 2000 y 2004 incompletos
    assert season["year"].tolist() == [2001, 2002, 2003]
    may_aug = season_series(monthly, [5, 6, 7, 8])
    assert may_aug["year"].tolist() == [2000, 2001, 2002, 2003]


def test_monthly_anomalies_remove_climatology():
    anomalies = monthly_anomalies(make_monthly(slope=0.0))
    assert anomalies["anomaly"].abs().max() < 1e-9
    assert anomalies["decimal_year"].iloc[0] == pytest.approx(1990 + 0.5 / 12)
