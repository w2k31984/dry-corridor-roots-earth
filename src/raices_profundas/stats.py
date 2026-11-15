"""Análisis estadístico: tendencias, proyección y clasificación climática."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import kendalltau, linregress, norm, theilslopes
from scipy.stats import t as student_t


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


def trend_test(x, y, confidence: float = 0.95) -> dict:
    """Pendiente de Sen + Mann–Kendall y regresión lineal (OLS) con prueba t e IC.

    Devuelve un diccionario con NaN si hay menos de 3 observaciones válidas.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    out = {key: np.nan for key in [
        "sen_slope", "sen_low", "sen_high", "sen_intercept", "mk_tau", "mk_p",
        "ols_slope", "ols_intercept", "ols_low", "ols_high", "ols_p", "r2"]}
    out["n"] = int(len(x))
    if len(x) < 3 or np.ptp(y) == 0:
        return out
    sen = theilslopes(y, x, alpha=confidence)
    tau, mk_p = kendalltau(x, y)
    ols = linregress(x, y)
    t_crit = student_t.ppf(0.5 + confidence / 2, len(x) - 2)
    out.update({
        "sen_slope": float(sen.slope), "sen_low": float(sen.low_slope),
        "sen_high": float(sen.high_slope), "sen_intercept": float(sen.intercept),
        "mk_tau": float(tau), "mk_p": float(mk_p),
        "ols_slope": float(ols.slope), "ols_intercept": float(ols.intercept),
        "ols_low": float(ols.slope - t_crit * ols.stderr),
        "ols_high": float(ols.slope + t_crit * ols.stderr),
        "ols_p": float(ols.pvalue), "r2": float(ols.rvalue ** 2),
    })
    return out


def seasonal_mann_kendall(monthly: pd.DataFrame, value: str = "value") -> dict:
    """Prueba de Mann–Kendall estacional (Hirsch et al., 1982) sobre datos mensuales.

    Compara cada mes solo con el mismo mes de otros años, de modo que el ciclo
    estacional no se confunde con una tendencia. Incluye corrección por empates
    y la pendiente de Sen estacional (mediana de pendientes intra-mes, por año).
    """
    s_total, var_total, slopes = 0.0, 0.0, []
    for _, group in monthly.dropna(subset=[value]).groupby("month"):
        group = group.sort_values("year")
        years = group["year"].to_numpy(dtype=float)
        values = group[value].to_numpy(dtype=float)
        n = len(values)
        if n < 2:
            continue
        i, j = np.triu_indices(n, k=1)
        diffs = values[j] - values[i]
        s_total += float(np.sign(diffs).sum())
        _, counts = np.unique(values, return_counts=True)
        ties = float(np.sum(counts * (counts - 1) * (2 * counts + 5)))
        var_total += (n * (n - 1) * (2 * n + 5) - ties) / 18.0
        slopes.extend(diffs / (years[j] - years[i]))
    if var_total == 0:
        return {"smk_s": np.nan, "smk_z": np.nan, "smk_p": np.nan, "seasonal_sen_slope": np.nan}
    z = (s_total - np.sign(s_total)) / np.sqrt(var_total) if s_total != 0 else 0.0
    return {"smk_s": s_total, "smk_z": float(z), "smk_p": float(2 * norm.sf(abs(z))),
            "seasonal_sen_slope": float(np.median(slopes))}


def season_series(monthly: pd.DataFrame, months, value: str = "value") -> pd.DataFrame:
    """Promedio por año de los meses indicados.

    Si la temporada cruza el fin de año (p. ej. dic→abr), los meses previos al
    inicio de año se asignan al año siguiente. Solo se conservan años completos.
    """
    months = list(months)
    wraps = months != sorted(months)
    data = monthly[monthly["month"].isin(months)].dropna(subset=[value]).copy()
    if wraps:
        first = months[0]
        data["year"] = np.where(data["month"] >= first, data["year"] + 1, data["year"])
    grouped = data.groupby("year")[value].agg(["mean", "count"]).reset_index()
    grouped = grouped[grouped["count"] == len(months)]
    return grouped.rename(columns={"mean": value})[["year", value]]


def monthly_anomalies(monthly: pd.DataFrame, value: str = "value") -> pd.DataFrame:
    """Resta la climatología mensual (ciclo estacional) a cada valor."""
    out = monthly.copy()
    out["anomaly"] = out[value] - out.groupby("month")[value].transform("mean")
    out["decimal_year"] = out["year"] + (out["month"] - 0.5) / 12
    return out


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
