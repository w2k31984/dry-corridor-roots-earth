"""Análisis estadístico: tendencias, proyección y clasificación climática."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, theilslopes


def trend_table(series: pd.DataFrame) -> pd.DataFrame:
    results = []
    annual = series.groupby(["cell_id", "year"], as_index=False)["rootzone_moisture"].mean()
    for cell_id, group in annual.groupby("cell_id"):
        group = group.sort_values("year")
        tau, p_value = kendalltau(group["year"], group["rootzone_moisture"])
        slope = theilslopes(group["rootzone_moisture"], group["year"]).slope if len(group) >= 3 else np.nan
        results.append({
            "cell_id": cell_id, "n_years": len(group), "mk_tau": tau, "mk_p": p_value,
            "sen_slope_per_year": slope,
            "moisture_change_first_last": group.iloc[-1]["rootzone_moisture"] - group.iloc[0]["rootzone_moisture"]
            if len(group) >= 2 else np.nan,
        })
    return pd.DataFrame(results)


def project_moisture(series: pd.DataFrame, end_year: int, min_history: int = 5) -> pd.DataFrame:
    """Extrapolate the historical Sen trend, with a conservative prediction interval."""
    annual = series.groupby(["cell_id", "year"], as_index=False)["rootzone_moisture"].mean()
    forecasts = []
    for cell_id, group in annual.groupby("cell_id"):
        group = group.dropna().sort_values("year")
        if len(group) < min_history:
            continue
        x = group["year"].to_numpy(dtype=float)
        y = group["rootzone_moisture"].to_numpy(dtype=float)
        fit = theilslopes(y, x, alpha=0.95)
        tau, p_value = kendalltau(x, y)
        baseline_year = int(x[-1])
        residuals = y - (fit.intercept + fit.slope * x)
        residual_sd = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
        slope_se = max(float(fit.high_slope - fit.low_slope) / (2 * 1.96), 0.0)

        for forecast_year in range(baseline_year + 1, end_year + 1):
            estimate = float(fit.intercept + fit.slope * forecast_year)
            distance = forecast_year - float(np.mean(x))
            prediction_se = np.sqrt(
                residual_sd**2 * (1 + 1 / len(x)) + (distance * slope_se) ** 2
            )
            half_width = 1.96 * prediction_se
            lower = float(np.clip(estimate - half_width, 0.0, 0.9))
            upper = float(np.clip(estimate + half_width, 0.0, 0.9))
            estimate = float(np.clip(estimate, 0.0, 0.9))
            forecasts.append({
                "cell_id": cell_id,
                "history_start_year": int(x[0]),
                "baseline_year": baseline_year,
                "forecast_year": forecast_year,
                "forecast_rootzone_moisture": estimate,
                "lower_95": lower,
                "upper_95": upper,
                "change_from_baseline": estimate - float(y[-1]),
                "sen_slope_per_year": float(fit.slope),
                "mk_tau": float(tau),
                "mk_p": float(p_value),
                "projection_status": "Tendencia significativa" if p_value < 0.05 else "Extrapolación exploratoria: tendencia no significativa",
            })
    return pd.DataFrame(forecasts)


def add_climate_classification(trends: pd.DataFrame, climate_path: Path | None) -> pd.DataFrame:
    if climate_path is None:
        trends["classification"] = "Humedad SMAP: ver tendencia"
        return trends
    climate = pd.read_csv(climate_path)
    required = {"cell_id", "precip_sen_slope", "precip_mk_p", "temp_sen_slope", "temp_mk_p"}
    if not required.issubset(climate.columns):
        raise ValueError(f"El CSV climático requiere: {', '.join(sorted(required))}")
    out = trends.merge(climate[list(required)], on="cell_id", how="left")
    drying = (out.sen_slope_per_year < 0) & (out.mk_p < 0.05)
    warming = (out.temp_sen_slope > 0) & (out.temp_mk_p < 0.05)
    drying_rain = (out.precip_sen_slope < 0) & (out.precip_mk_p < 0.05)
    stable_rain = out.precip_mk_p >= 0.05
    out["classification"] = "Sin señal conjunta clara"
    out.loc[drying & warming & drying_rain, "classification"] = "Señal conjunta de sequedad"
    out.loc[drying & warming & stable_rain, "classification"] = "Compatible con estrés por calor"
    return out
