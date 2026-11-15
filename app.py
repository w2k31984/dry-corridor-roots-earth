"""Raíces Profundas — Detective de tendencias del sistema Tierra en el Corredor Seco."""
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from scipy.stats import t as student_t

from raices_profundas.places import COUNTRY_NAMES, landscape
from raices_profundas.stats import monthly_anomalies, season_series, seasonal_mann_kendall, trend_test
from raices_profundas.variables import LANDSCAPE_HINTS, SEASONS, SMAP, THEMES, VARIABLES

st.set_page_config(page_title="Raíces Profundas — Earth System Trend Detective", layout="wide")

ALPHA = 0.05
POWER_DEFAULT_START = 2001
DEMOS = {
    "drought2023": {"theme": "drought", "var": SMAP, "cell": "C0009", "season": "primera"},
    "warming": {"theme": "heat", "var": "T2M", "cell": "C0003", "season": "year",
                "period_power": (2001, 2025)},
    "contrast": {"theme": "heat", "var": "T2M_MAX", "cell": "C0023", "season": "postrera",
                 "period_power": (2001, 2025)},
}
CITIES = [
    ("Guatemala", 14.6349, -90.5069), ("Quetzaltenango", 14.8347, -91.5202),
    ("San Salvador", 13.6929, -89.2182), ("Santa Ana", 13.9945, -89.5597),
    ("Tegucigalpa", 14.0723, -87.1921), ("San Pedro Sula", 15.5042, -88.0374),
    ("Comayagua", 14.4553, -87.6424), ("Choluteca", 13.3007, -87.1908),
    ("San Miguel", 13.4833, -88.1833), ("Estelí", 13.0919, -86.3538),
]
EXTERNAL_TOOLS = [
    ("Giovanni (NASA GES DISC)", "https://giovanni.gsfc.nasa.gov/giovanni/"),
    ("AppEEARS (NASA LP DAAC)", "https://appeears.earthdatacloud.nasa.gov/"),
    ("Hydrology Data Rods (NASA)", "https://disc.gsfc.nasa.gov/information/tools?title=Hydrology%20Data%20Rods"),
    ("NASA POWER Data Access Viewer", "https://power.larc.nasa.gov/data-access-viewer/"),
    ("KNMI Climate Explorer", "https://climexp.knmi.nl/"),
]

# ---------------------------------------------------------------- idioma
query_lang = st.query_params.get("lang", "es")
lang_col, _ = st.columns([1, 4])
with lang_col:
    LANG = "en" if st.selectbox(
        "Language / Idioma", ["Español", "English"], index=1 if query_lang == "en" else 0,
    ) == "English" else "es"


def L(es: str, en: str) -> str:
    return en if LANG == "en" else es


# ---------------------------------------------------------------- datos
root = Path(__file__).resolve().parent
base = next((d for d in [root / "outputs", root / "data"]
             if (d / "smap_seasonal_timeseries.csv").exists()), root / "data")
data_dir = root / "data"
required = [base / "smap_seasonal_timeseries.csv", base / "smap_trends.geojson",
            base / "smap_projection.csv", base / "smap_projection.geojson",
            data_dir / "power_monthly.csv", data_dir / "cells.csv"]
if not all(path.exists() for path in required):
    st.info(L("No se encontraron resultados en data/ u outputs/. Ejecuta el pipeline "
              "(`raices-profundas --download-fao-roi`) y `python scripts/fetch_power.py`.",
              "No results found in data/ or outputs/. Run the pipeline "
              "(`raices-profundas --download-fao-roi`) and `python scripts/fetch_power.py`."))
    st.stop()


@st.cache_data
def load_data(data_version: tuple):
    smap = pd.read_csv(base / "smap_seasonal_timeseries.csv").rename(columns={"rootzone_moisture": "value"})
    grid = gpd.read_file(base / "smap_trends.geojson")
    projections = pd.read_csv(base / "smap_projection.csv")
    projection_grid = gpd.read_file(base / "smap_projection.geojson")
    power = pd.read_csv(data_dir / "power_monthly.csv")
    cells = pd.read_csv(data_dir / "cells.csv").set_index("cell_id")
    return smap, grid, projections, projection_grid, power, cells


data_version = tuple(path.stat().st_mtime for path in required)
smap, grid, projections, projection_grid, power, cells = load_data(data_version)
grid = grid[grid.cell_id.isin(cells.index)].reset_index(drop=True)


def cell_label(cell_id: str) -> str:
    row = cells.loc[cell_id]
    country = COUNTRY_NAMES[LANG].get(row.country, row.country)
    west = L("O", "W")
    near = L("cerca de", "near")
    return f"{cell_id} · {near} {row.place}, {country} ({row.lat:.2f}°N, {abs(row.lon):.2f}°{west})"


def landscape_key(elevation: float) -> str:
    return "low" if elevation < 300 else "mid" if elevation < 1000 else "high"


def var_name(var: str) -> str:
    return VARIABLES[var]["name"][LANG]


def season_values(var: str, cell_id: str, season: str, period) -> pd.DataFrame:
    if var == SMAP:
        data = smap[smap.cell_id == cell_id][["year", "value"]]
    else:
        monthly = power[(power.cell_id == cell_id) & (power.variable == var)]
        data = season_series(monthly, SEASONS[season]["months"])
    return data[data.year.between(*period)].sort_values("year")


@st.cache_data
def all_cell_trends(var: str, season: str, period, data_version: tuple) -> pd.DataFrame:
    rows = []
    for cell_id in grid.cell_id:
        series = season_values(var, cell_id, season, period)
        rows.append({"cell_id": cell_id, **trend_test(series.year, series.value)})
    table = pd.DataFrame(rows)
    table["sen_per_decade"] = table["sen_slope"] * 10
    table["significant"] = table["mk_p"] < ALPHA
    return table


# ---------------------------------------------------------------- estado / ejemplos
defaults = {"theme": "drought", "var": SMAP, "cell": "C0009", "season": "primera",
            "period_power": (POWER_DEFAULT_START, int(power.year.max())),
            "period_smap": (int(smap.year.min()), int(smap.year.max())), "demo": None}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


def run_demo(name: str) -> None:
    for key, value in DEMOS[name].items():
        st.session_state[key] = value
    st.session_state["demo"] = name


def select_from_map() -> None:
    points = st.session_state.get("trend_map", {}).get("selection", {}).get("points", [])
    for point in points:
        cell_id = point.get("location")
        if cell_id is None and point.get("customdata"):
            cell_id = point["customdata"][0]
        if cell_id is None and point.get("curve_number") == 0 and point.get("point_index") is not None:
            cell_id = grid.cell_id.iloc[point["point_index"]]
        if cell_id in cells.index:
            st.session_state["cell"] = cell_id
            return


# ---------------------------------------------------------------- encabezado
st.title("Raíces Profundas")
st.caption(L("Detective de tendencias del sistema Tierra en el Corredor Seco Centroamericano · "
             "NASA Space Apps 2026 — Be an Earth System Trend Detective!",
             "Earth system trend detective for the Central American Dry Corridor · "
             "NASA Space Apps 2026 — Be an Earth System Trend Detective!"))
with st.expander(L("¿Qué es el Corredor Seco y qué hace esta herramienta?",
                   "What is the Dry Corridor and what does this tool do?")):
    st.markdown(L(
        "El **Corredor Seco Centroamericano** es una franja que recorre el Pacífico de Guatemala, El Salvador, "
        "Honduras y Nicaragua. Lluvias erráticas, sequías recurrentes (como la **canícula**) y calor afectan a "
        "millones de pequeños agricultores.\n\n"
        "Esta herramienta te convierte en **detective de datos**: eliges **qué** variable investigar, "
        "**dónde** y **cuándo**, y la app responde con estadística: **qué está cambiando, dónde, cuánto, "
        "y si el cambio es significativo** (pendiente de Sen, Mann–Kendall, regresión lineal con prueba t e "
        "intervalos de confianza del 95%).",
        "The **Central American Dry Corridor** is a strip along the Pacific side of Guatemala, El Salvador, "
        "Honduras and Nicaragua. Erratic rainfall, recurrent droughts (like the mid-summer **canícula**) and "
        "heat affect millions of smallholder farmers.\n\n"
        "This tool turns you into a **data detective**: choose **what** variable to investigate, **where** and "
        "**when**, and the app answers with statistics: **what is changing, where, how much, and whether the "
        "change is significant** (Sen's slope, Mann–Kendall, linear regression with t-test and 95% "
        "confidence intervals)."))

tab_detective, tab_projection, tab_learn = st.tabs([
    L("Detective de tendencias", "Trend detective"),
    L("Proyección SMAP (exploratoria)", "SMAP projection (exploratory)"),
    L("Glosario, datos y métodos", "Glossary, data & methods"),
])

# ================================================================ DETECTIVE
with tab_detective:
    st.markdown(L("**¿Primera vez? Prueba un caso resuelto:**", "**First time? Try a solved case:**"))
    d1, d2, d3 = st.columns(3)
    d1.button(L("Caso 1 · La sequía de 2023 (El Niño)", "Case 1 · The 2023 drought (El Niño)"),
              on_click=run_demo, args=("drought2023",), width="stretch")
    d2.button(L("Caso 2 · ¿Se calienta el altiplano?", "Case 2 · Are the highlands warming?"),
              on_click=run_demo, args=("warming",), width="stretch")
    d3.button(L("Caso 3 · Misma variable, tendencias opuestas", "Case 3 · Same variable, opposite trends"),
              on_click=run_demo, args=("contrast",), width="stretch")
    demo_text = {
        "drought2023": L(
            "**Caso 1.** Mira la humedad del suelo SMAP cerca de San Salvador: 2023 (año El Niño) es uno de los "
            "valores más bajos. Pero **un año seco no es una tendencia**: revisa el p de Mann–Kendall y si el "
            "intervalo de confianza de la pendiente incluye el cero.",
            "**Case 1.** Look at SMAP soil moisture near San Salvador: 2023 (an El Niño year) is one of the lowest "
            "values. But **one dry year is not a trend**: check the Mann–Kendall p and whether the slope's "
            "confidence interval includes zero."),
        "warming": L(
            "**Caso 2.** Temperatura del aire (MERRA-2) cerca de Quetzaltenango, 2001–2025. La tendencia es "
            "positiva y significativa en ambas pruebas: es un cambio que difícilmente se explica por azar.",
            "**Case 2.** Air temperature (MERRA-2) near Quetzaltenango, 2001–2025. The trend is positive and "
            "significant in both tests: a change unlikely to be explained by chance."),
        "contrast": L(
            "**Caso 3.** Temperatura máxima en Postrera, 2001–2025. En el mapa, el altiplano occidental se calienta "
            "mientras el oriente de Honduras se enfría: **la misma variable puede tener tendencias opuestas** "
            "en distintas regiones. Haz clic en otras celdas del mapa para comparar.",
            "**Case 3.** Maximum temperature in the Postrera season, 2001–2025. On the map, the western highlands "
            "warm while eastern Honduras cools: **the same variable can trend in opposite directions** in different "
            "regions. Click other cells on the map to compare."),
    }
    demo = st.session_state["demo"]
    if demo and all(st.session_state.get(k) == v for k, v in DEMOS[demo].items()):
        st.info(demo_text[demo])

    st.divider()
    q1, q2, q3 = st.columns(3)
    with q1:
        st.markdown(L("**1 · ¿Qué quieres investigar?**", "**1 · What do you want to investigate?**"))
        theme = st.radio(L("Tema", "Topic"), list(THEMES), key="theme",
                         format_func=lambda k: THEMES[k][LANG], horizontal=True)
        options = [v for v, meta in VARIABLES.items() if theme in meta["themes"]]
        if st.session_state["var"] not in options:
            st.session_state["var"] = options[0]
        var = st.selectbox(L("Variable", "Variable"), options, key="var", format_func=var_name)
        meta = VARIABLES[var]
        st.caption(f"{meta['definition'][LANG]}  \n**{L('Fuente', 'Source')}:** {meta['source']} · "
                   f"**{L('Unidades', 'Units')}:** {meta['units']}")
    with q2:
        st.markdown(L("**2 · ¿Dónde?**", "**2 · Where?**"))
        cell = st.selectbox(L("Celda (~1°) — o haz clic en el mapa", "Cell (~1°) — or click on the map"),
                            list(grid.cell_id), key="cell", format_func=cell_label)
        elevation = float(cells.loc[cell, "elevation_m"])
        hints = [var_name(v) for v in LANDSCAPE_HINTS[landscape_key(elevation)]]
        st.caption(L(f"Paisaje: **{landscape(elevation, 'es')}** (~{elevation:.0f} m, elevación del modelo).  \n"
                     f"Pista del detective: aquí suele valer la pena revisar {', '.join(hints)}.",
                     f"Landscape: **{landscape(elevation, 'en')}** (~{elevation:.0f} m, model elevation).  \n"
                     f"Detective hint: here it is worth checking {', '.join(hints)}."))
    with q3:
        st.markdown(L("**3 · ¿Cuándo?**", "**3 · When?**"))
        if var == SMAP:
            st.selectbox(L("Temporada", "Season"), ["primera"], disabled=True,
                         format_func=lambda k: SEASONS[k][LANG])
            season = "primera"
            lo, hi = int(smap.year.min()), int(smap.year.max())
            period = st.slider(L("Periodo", "Period"), lo, hi, key="period_smap")
            st.caption(L("SMAP está disponible desde 2015 y aquí se resume como promedio de mayo–agosto.",
                         "SMAP is available since 2015 and is summarised here as the May–August mean."))
        else:
            season = st.selectbox(L("Temporada", "Season"), list(SEASONS), key="season",
                                  format_func=lambda k: SEASONS[k][LANG])
            lo, hi = int(power.year.min()), int(power.year.max())
            period = st.slider(L("Periodo", "Period"), lo, hi, key="period_power")
            if period[0] < 2001:
                st.warning(L("Antes de ~2001 los modelos de reanálisis como MERRA-2 asimilaban menos datos "
                             "satelitales: las tendencias largas pueden incluir artefactos. Compáralas con 2001–2025.",
                             "Before ~2001 reanalyses such as MERRA-2 assimilated fewer satellite data: long "
                             "trends may include artefacts. Compare with 2001–2025."))

    series = season_values(var, cell, season, period)
    result = trend_test(series.year, series.value)
    trends = all_cell_trends(var, season, period, data_version)
    units, dec = meta["units"], meta["decimals"]
    period_label = f"{SEASONS[season][LANG]}, {period[0]}–{period[1]}"

    st.divider()
    if result["n"] < 5 or np.isnan(result["sen_slope"]):
        st.warning(L("No hay suficientes años en este periodo para analizar una tendencia (mínimo 5).",
                     "Not enough years in this period to analyse a trend (minimum 5)."))
    else:
        sen_dec = result["sen_slope"] * 10
        span = series.year.iloc[-1] - series.year.iloc[0]
        total = result["sen_slope"] * span
        mean = series.value.mean()
        pct = 100 * total / mean if mean else np.nan
        sig_mk, sig_t = result["mk_p"] < ALPHA, result["ols_p"] < ALPHA
        direction = (L("aumenta", "increases") if sen_dec > 0 else L("disminuye", "decreases"))
        if sig_mk and sig_t:
            verdict = L("**Sí.** Ambas pruebas (Mann–Kendall y t) dan p < 0.05: es poco probable que sea azar.",
                        "**Yes.** Both tests (Mann–Kendall and t) give p < 0.05: unlikely to be chance.")
            box = st.success
        elif sig_mk or sig_t:
            verdict = L("**Probable.** Solo una de las dos pruebas da p < 0.05; trátalo con cautela.",
                        "**Likely.** Only one of the two tests gives p < 0.05; treat with caution.")
            box = st.warning
        else:
            verdict = L("**No.** p ≥ 0.05: el cambio puede ser variabilidad natural. Con más años de datos "
                        "podría volverse significativo.",
                        "**No.** p ≥ 0.05: the change may be natural variability. With more years of data it "
                        "could become significant.")
            box = st.info
        n_up = int(((trends.sen_slope > 0) & trends.significant).sum())
        n_down = int(((trends.sen_slope < 0) & trends.significant).sum())
        box(L(
            f"### Veredicto del detective\n"
            f"- **¿Qué cambia?** {var_name(var)} — {period_label}.\n"
            f"- **¿Dónde?** {cell_label(cell)}. En toda la región, {n_up} celdas suben y {n_down} bajan de forma "
            f"significativa.\n"
            f"- **¿Cuánto?** {direction} {abs(sen_dec):.{dec + 1}f} {units} por década "
            f"(IC 95%: {result['sen_low'] * 10:+.{dec + 1}f} a {result['sen_high'] * 10:+.{dec + 1}f}); "
            f"≈ {total:+.{dec}f} {units} en {span} años ({pct:+.0f}% del promedio).\n"
            f"- **¿Es significativo?** {verdict} (Mann–Kendall p = {result['mk_p']:.3f}; "
            f"prueba t p = {result['ols_p']:.3f}).",
            f"### Detective's verdict\n"
            f"- **What is changing?** {var_name(var)} — {period_label}.\n"
            f"- **Where?** {cell_label(cell)}. Across the region, {n_up} cells rise and {n_down} fall "
            f"significantly.\n"
            f"- **How much?** {direction} by {abs(sen_dec):.{dec + 1}f} {units} per decade "
            f"(95% CI: {result['sen_low'] * 10:+.{dec + 1}f} to {result['sen_high'] * 10:+.{dec + 1}f}); "
            f"≈ {total:+.{dec}f} {units} over {span} years ({pct:+.0f}% of the mean).\n"
            f"- **Is it significant?** {verdict} (Mann–Kendall p = {result['mk_p']:.3f}; "
            f"t-test p = {result['ols_p']:.3f})."))

        m1, m2, m3, m4 = st.columns(4)
        m1.metric(L("Pendiente de Sen / década", "Sen slope / decade"), f"{sen_dec:+.{dec + 1}f} {units}")
        m2.metric(L("Mann–Kendall p (τ)", "Mann–Kendall p (τ)"), f"{result['mk_p']:.3f}",
                  delta=f"τ = {result['mk_tau']:+.2f}", delta_color="off")
        m3.metric(L("Regresión lineal: prueba t p", "Linear regression: t-test p"), f"{result['ols_p']:.3f}",
                  delta=f"R² = {result['r2']:.2f}", delta_color="off")
        m4.metric(L("IC 95% pendiente OLS / década", "95% CI OLS slope / decade"),
                  f"{result['ols_low'] * 10:+.{dec + 1}f} … {result['ols_high'] * 10:+.{dec + 1}f}")

        x = series.year.to_numpy(dtype=float)
        y = series.value.to_numpy(dtype=float)
        n = len(x)
        resid = y - (result["ols_intercept"] + result["ols_slope"] * x)
        s_err = np.sqrt(np.sum(resid ** 2) / (n - 2))
        band = student_t.ppf(0.975, n - 2) * s_err * np.sqrt(1 / n + (x - x.mean()) ** 2 / np.sum((x - x.mean()) ** 2))
        ols_line = result["ols_intercept"] + result["ols_slope"] * x
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=ols_line + band, mode="lines", line={"width": 0},
                                 showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=x, y=ols_line - band, mode="lines", line={"width": 0}, fill="tonexty",
                                 fillcolor="rgba(255,127,14,0.18)",
                                 name=L("IC 95% de la recta OLS", "95% CI of OLS line")))
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=var_name(var), line={"color": "#1f77b4"}))
        fig.add_trace(go.Scatter(x=x, y=result["sen_intercept"] + result["sen_slope"] * x, mode="lines",
                                 line={"dash": "dash", "color": "#d62728"}, name=L("Tendencia de Sen", "Sen trend")))
        fig.add_trace(go.Scatter(x=x, y=ols_line, mode="lines", line={"dash": "dot", "color": "#ff7f0e"},
                                 name=L("Regresión lineal (OLS)", "Linear regression (OLS)")))
        fig.update_layout(title=f"{var_name(var)} — {cell} ({period_label})", xaxis_title=L("Año", "Year"),
                          yaxis_title=f"{var_name(var)} ({units})", legend={"orientation": "h", "y": -0.2})
        st.plotly_chart(fig, width="stretch")

    if var != SMAP:
        with st.expander(L("Ver serie mensual sin ciclo estacional (Mann–Kendall estacional)",
                           "Show monthly series with the seasonal cycle removed (seasonal Mann–Kendall)")):
            months = SEASONS[season]["months"]
            monthly = power[(power.cell_id == cell) & (power.variable == var) & power.month.isin(months)]
            season_year = monthly.year + ((months != sorted(months)) & (monthly.month >= months[0]))
            monthly = monthly[season_year.between(*period)]
            anomalies = monthly_anomalies(monthly)
            smk = seasonal_mann_kendall(monthly)
            afit = trend_test(anomalies.decimal_year, anomalies.anomaly)
            afig = px.scatter(anomalies, x="decimal_year", y="anomaly",
                              labels={"decimal_year": L("Año", "Year"),
                                      "anomaly": L(f"Anomalía ({units})", f"Anomaly ({units})")})
            if np.isfinite(afit["sen_slope"]):
                ax = np.array([anomalies.decimal_year.min(), anomalies.decimal_year.max()])
                afig.add_trace(go.Scatter(x=ax, y=afit["sen_intercept"] + afit["sen_slope"] * ax, mode="lines",
                                          line={"dash": "dash", "color": "#d62728"},
                                          name=L("Tendencia de Sen", "Sen trend")))
            st.plotly_chart(afig, width="stretch")
            st.caption(L(
                f"Cada punto es un mes menos el promedio de ese mes (se elimina el ciclo estacional). "
                f"Mann–Kendall estacional: p = {smk['smk_p']:.3f}; pendiente de Sen estacional = "
                f"{smk['seasonal_sen_slope'] * 10:+.{dec + 1}f} {units}/década.",
                f"Each point is one month minus that month's average (the seasonal cycle is removed). "
                f"Seasonal Mann–Kendall: p = {smk['smk_p']:.3f}; seasonal Sen slope = "
                f"{smk['seasonal_sen_slope'] * 10:+.{dec + 1}f} {units}/decade."))

    st.subheader(L("¿Dónde está cambiando? — mapa de tendencias", "Where is it changing? — trend map"))
    st.caption(L("Color: pendiente de Sen por década. Puntos negros: tendencia significativa (Mann–Kendall p < 0.05). "
                 "Punto amarillo: celda seleccionada. **Haz clic en una celda para investigarla.**",
                 "Colour: Sen slope per decade. Black dots: significant trend (Mann–Kendall p < 0.05). "
                 "Yellow dot: selected cell. **Click a cell to investigate it.**"))
    map_df = grid[["cell_id", "geometry"]].merge(trends, on="cell_id")
    map_df["label"] = map_df.cell_id.map(cell_label)
    slope_label = L(f"{units} / década", f"{units} / decade")
    map_fig = px.choropleth_map(
        map_df, geojson=map_df.__geo_interface__, locations="cell_id", featureidkey="properties.cell_id",
        color="sen_per_decade", color_continuous_midpoint=0,
        color_continuous_scale="RdBu" if meta["increase_is_wetter"] else "RdBu_r",
        hover_name="label", hover_data={"cell_id": False, "sen_per_decade": ":.3f", "mk_p": ":.3f", "n": True},
        labels={"sen_per_decade": slope_label, "mk_p": "Mann–Kendall p", "n": L("años", "years")},
        opacity=0.75)
    sig = map_df[map_df.significant]
    sig_cells = cells.loc[sig.cell_id]
    map_fig.add_trace(go.Scattermap(lat=sig_cells.lat, lon=sig_cells.lon, mode="markers",
                                    marker={"size": 9, "color": "black"}, customdata=sig_cells.index.to_numpy()[:, None],
                                    name="p < 0.05", hoverinfo="skip"))
    map_fig.add_trace(go.Scattermap(lat=[cells.loc[cell, "lat"]], lon=[cells.loc[cell, "lon"]], mode="markers",
                                    marker={"size": 15, "color": "yellow"}, customdata=[[cell]],
                                    name=L("Seleccionada", "Selected"), hoverinfo="skip"))
    minx, miny, maxx, maxy = grid.total_bounds
    map_fig.add_trace(go.Scattermap(lat=[c[1] for c in CITIES], lon=[c[2] for c in CITIES], mode="markers+text", marker={"size": 4, "color": "white"},
                                    text=[c[0] for c in CITIES], textfont={"size": 11, "color": "white"},
                                    textposition="top right", hoverinfo="skip", showlegend=False))
    map_fig.update_layout(map_style="satellite", map_center={"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2},
                          map_zoom=6, height=520, margin={"l": 0, "r": 0, "t": 0, "b": 0},
                          legend={"orientation": "h", "y": 1.02})
    st.plotly_chart(map_fig, width="stretch", key="trend_map", on_select=select_from_map,
                    selection_mode="points")

    with st.expander(L("Comparar regiones", "Compare regions")):
        others = st.multiselect(L("Añade celdas para comparar", "Add cells to compare"),
                                [c for c in grid.cell_id if c != cell], format_func=cell_label, max_selections=4)
        cfig = go.Figure()
        for cid in [cell, *others]:
            s = season_values(var, cid, season, period)
            cfig.add_trace(go.Scatter(x=s.year, y=s.value, mode="lines+markers", name=cid))
        cfig.update_layout(xaxis_title=L("Año", "Year"), yaxis_title=f"{var_name(var)} ({units})")
        st.plotly_chart(cfig, width="stretch")
        compare = trends[trends.cell_id.isin([cell, *others])].copy()
        compare.insert(1, L("lugar", "place"), compare.cell_id.map(cell_label))
        st.dataframe(compare[["cell_id", L("lugar", "place"), "n", "sen_per_decade", "sen_low", "sen_high",
                              "mk_tau", "mk_p", "ols_slope", "ols_p"]].round(4), hide_index=True,
                     width="stretch")

    dl1, dl2 = st.columns(2)
    dl1.download_button(L("Descargar esta serie (CSV)", "Download this series (CSV)"),
                        series.assign(cell_id=cell, variable=var, season=season).to_csv(index=False),
                        file_name=f"{var}_{cell}_{season}.csv", mime="text/csv")
    dl2.download_button(L("Descargar tendencias de todas las celdas (CSV)", "Download trends for all cells (CSV)"),
                        trends.assign(variable=var, season=season, start=period[0], end=period[1]).to_csv(index=False),
                        file_name=f"trends_{var}_{season}_{period[0]}_{period[1]}.csv", mime="text/csv")

# ================================================================ PROYECCIÓN
with tab_projection:
    st.markdown(L(
        "Extrapolación **exploratoria** de la tendencia de Sen de la humedad SMAP (mayo–agosto, 2015–2025) "
        "hasta 2030. No incluye escenarios climáticos ni es un pronóstico: con tendencias no significativas, "
        "la banda de incertidumbre es muy ancha.",
        "**Exploratory** extrapolation of the Sen trend of SMAP soil moisture (May–August, 2015–2025) to 2030. "
        "It includes no climate scenarios and is not a forecast: with non-significant trends the uncertainty "
        "band is very wide."))
    proj_cells = sorted(set(projections.cell_id))
    pcell = st.session_state["cell"] if st.session_state["cell"] in proj_cells else proj_cells[0]
    pcell = st.selectbox(L("Celda", "Cell"), proj_cells, index=proj_cells.index(pcell), format_func=cell_label)
    hist = smap[smap.cell_id == pcell].sort_values("year")
    cp = projections[projections.cell_id == pcell].sort_values("forecast_year")
    target = cp.iloc[-1]
    st.metric(L(f"Proyección {int(target.forecast_year)} (m³/m³)", f"Projection {int(target.forecast_year)} (m³/m³)"),
              f"{target.forecast_rootzone_moisture:.3f}",
              delta=f"{target.change_from_baseline:+.3f} vs. {int(target.baseline_year)}")
    pfig = go.Figure()
    pfig.add_trace(go.Scatter(x=hist.year, y=hist.value, mode="lines+markers", name=L("SMAP histórico", "Historical SMAP")))
    pfig.add_trace(go.Scatter(x=cp.forecast_year, y=cp.upper_95, mode="lines", line={"width": 0},
                              showlegend=False, hoverinfo="skip"))
    pfig.add_trace(go.Scatter(x=cp.forecast_year, y=cp.lower_95, mode="lines", line={"width": 0}, fill="tonexty",
                              fillcolor="rgba(255,127,14,0.18)", name=L("Intervalo de predicción 95%", "95% prediction interval")))
    pfig.add_trace(go.Scatter(x=cp.forecast_year, y=cp.forecast_rootzone_moisture, mode="lines+markers",
                              line={"dash": "dash"}, name=L("Extrapolación", "Extrapolation")))
    pfig.update_layout(xaxis_title=L("Año", "Year"), yaxis_title=L("Humedad (m³/m³)", "Moisture (m³/m³)"))
    st.plotly_chart(pfig, width="stretch")
    years = sorted(int(c.replace("change_", "")) for c in projection_grid.columns if c.startswith("change_"))
    map_year = st.selectbox(L("Año proyectado", "Projected year"), years, index=len(years) - 1)
    field = f"change_{map_year}"
    pmap = px.choropleth_map(projection_grid, geojson=projection_grid.__geo_interface__, locations="cell_id",
                             featureidkey="properties.cell_id", color=field, color_continuous_scale="RdBu",
                             color_continuous_midpoint=0, hover_name="cell_id",
                             labels={field: L("Cambio proyectado (m³/m³)", "Projected change (m³/m³)")})
    pmap.update_layout(map_style="satellite", map_center={"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2},
                       map_zoom=6, height=480, margin={"l": 0, "r": 0, "t": 0, "b": 0})
    st.plotly_chart(pmap, width="stretch")

# ================================================================ GLOSARIO / DATOS
with tab_learn:
    st.subheader(L("Variables", "Variables"))
    st.dataframe(pd.DataFrame([{
        L("Variable", "Variable"): meta_["name"][LANG], L("Qué significa", "What it means"): meta_["definition"][LANG],
        L("Unidades", "Units"): meta_["units"], L("Fuente", "Source"): meta_["source"],
    } for meta_ in VARIABLES.values()]), hide_index=True, width="stretch")

    st.subheader(L("Glosario del detective", "Detective's glossary"))
    st.markdown(L(
        "- **Tendencia:** cambio sostenido en una dirección (sube o baja) a lo largo de los años.\n"
        "- **Pendiente de Sen:** cuánto cambia la variable por año (aquí, por década). Es la mediana de las "
        "pendientes entre todos los pares de años, así que un año extremo no la distorsiona.\n"
        "- **Prueba de Mann–Kendall:** ¿los valores tienden a ser mayores (o menores) con el tiempo? No asume "
        "una línea recta ni datos normales.\n"
        "- **Mann–Kendall estacional:** compara cada mes solo con el mismo mes de otros años, para que el ciclo "
        "lluvioso/seco no se confunda con una tendencia.\n"
        "- **Regresión lineal y prueba t:** ajusta la mejor línea recta; la prueba t indica si su pendiente es "
        "distinta de cero.\n"
        "- **Valor p:** probabilidad de ver una tendencia así de fuerte solo por azar. **p < 0.05** = significativa.\n"
        "- **Intervalo de confianza del 95% (IC 95%):** rango de pendientes compatibles con los datos. Si incluye "
        "el 0, no podemos descartar que no haya tendencia.\n"
        "- **Anomalía:** diferencia entre un valor y el promedio normal de ese mes.\n"
        "- **Canícula:** periodo seco y caluroso a mitad de la época lluviosa (julio–agosto).\n"
        "- **Primera / Postrera:** las dos temporadas de siembra del Corredor Seco.",
        "- **Trend:** a sustained change in one direction (up or down) over the years.\n"
        "- **Sen's slope:** how much the variable changes per year (shown here per decade). It is the median of the "
        "slopes between all pairs of years, so one extreme year does not distort it.\n"
        "- **Mann–Kendall test:** do values tend to get larger (or smaller) over time? It assumes neither a "
        "straight line nor normally distributed data.\n"
        "- **Seasonal Mann–Kendall:** compares each month only with the same month in other years, so the wet/dry "
        "cycle is not mistaken for a trend.\n"
        "- **Linear regression and t-test:** fits the best straight line; the t-test says whether its slope "
        "differs from zero.\n"
        "- **p-value:** the probability of seeing a trend this strong by chance alone. **p < 0.05** = significant.\n"
        "- **95% confidence interval (95% CI):** the range of slopes compatible with the data. If it includes 0, "
        "we cannot rule out that there is no trend.\n"
        "- **Anomaly:** the difference between a value and the normal average for that month.\n"
        "- **Canícula:** a hot, dry spell in the middle of the rainy season (July–August).\n"
        "- **Primera / Postrera:** the two planting seasons of the Dry Corridor."))

    st.subheader(L("Datos y métodos", "Data & methods"))
    st.markdown(L(
        "- **Región:** delimitación FAO del Corredor Seco, dividida en celdas de ~1°.\n"
        "- **SMAP L4 (SPL4SMGP v008), `sm_rootzone`:** descargado con `earthaccess` y recortado con NASA Harmony; "
        "promedio de los píxeles de 9 km dentro de cada celda y de mayo–agosto de cada año (2015–2025).\n"
        "- **MERRA-2 vía NASA POWER (API mensual):** valores mensuales 1981–2025 en un punto representativo de "
        "cada celda (resolución nativa 0.5° × 0.625°).\n"
        "- **Estadística:** promedio por temporada y año → pendiente de Sen con IC 95%, prueba de Mann–Kendall, "
        "regresión lineal (OLS) con prueba t e IC 95%; Mann–Kendall estacional sobre las anomalías mensuales.\n"
        "- **Limitaciones:** tendencias lineales; las reanálisis pueden tener saltos por cambios en los sistemas "
        "de observación (sobre todo antes de 2001); las celdas son grandes y no representan una finca concreta.",
        "- **Region:** FAO Dry Corridor boundary, split into ~1° cells.\n"
        "- **SMAP L4 (SPL4SMGP v008), `sm_rootzone`:** downloaded with `earthaccess` and subset with NASA Harmony; "
        "mean of the 9 km pixels inside each cell and of May–August of each year (2015–2025).\n"
        "- **MERRA-2 via NASA POWER (monthly API):** monthly values 1981–2025 at a representative point of each "
        "cell (native resolution 0.5° × 0.625°).\n"
        "- **Statistics:** seasonal mean per year → Sen's slope with 95% CI, Mann–Kendall test, linear regression "
        "(OLS) with t-test and 95% CI; seasonal Mann–Kendall on monthly anomalies.\n"
        "- **Limitations:** linear trends only; reanalyses can have jumps from changes in observing systems "
        "(especially before 2001); cells are large and do not represent a specific farm."))
    st.markdown(L("**Explora más con herramientas de NASA y socios:**", "**Explore further with NASA and partner tools:**"))
    st.markdown("\n".join(f"- [{name}]({url})" for name, url in EXTERNAL_TOOLS))
    c1, c2, c3 = st.columns(3)
    c1.download_button("smap_seasonal_timeseries.csv", (base / "smap_seasonal_timeseries.csv").read_bytes(),
                       file_name="smap_seasonal_timeseries.csv", mime="text/csv")
    c2.download_button("power_monthly.csv", (data_dir / "power_monthly.csv").read_bytes(),
                       file_name="power_monthly.csv", mime="text/csv")
    c3.download_button("cells.csv", (data_dir / "cells.csv").read_bytes(), file_name="cells.csv", mime="text/csv")
