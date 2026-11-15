"""Small Streamlit dashboard for outputs produced by the raices_profundas pipeline."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

STR = {
    "es": {
        "title": "Raíces Profundas",
        "caption": "Humedad de la zona radicular y señales de sequía agrícola en el Corredor Seco",
        "no_data": "No hay resultados en data/ ni outputs/. Ejecuta el pipeline (`raices-profundas --download-fao-roi`) para generarlos.",
        "no_common": "No hay celdas con datos históricos y proyección en común.",
        "cell": "Celda",
        "latest_moisture": "Humedad más reciente (m³/m³)",
        "change_first_last": "Cambio entre extremos (m³/m³)",
        "mk_p": "Tendencia Mann–Kendall p",
        "projection": "Proyección {year} (m³/m³)",
        "vs_baseline": "vs. {year}",
        "historical": "SMAP histórico",
        "pi95": "Intervalo de predicción 95%",
        "extrapolation": "Extrapolación 2015–2025",
        "x_axis": "Año",
        "y_axis": "Humedad (m³/m³)",
        "chart_title": "Historial SMAP y proyección — {cell}",
        "pi_caption": "{status}. La banda muestra un intervalo aproximado del 95% basado en la variabilidad histórica y la incertidumbre de la pendiente.",
        "trend_map": "Mapa de tendencias",
        "map_variable": "Variable del mapa",
        "projection_map": "Proyección espacial",
        "projection_year": "Año proyectado",
        "change_label": "Cambio proyectado (m³/m³)",
        "summary": "Resumen por celda",
        "footer": "La proyección extrapola la pendiente Sen de la serie estacional SMAP 2015–2025 hasta 2030; es exploratoria, no incluye escenarios climáticos y no representa una proyección causal ni un pronóstico para un cultivo específico.",
        "info_title": "¿Qué es el Corredor Seco Centroamericano?",
        "info": """El **Corredor Seco Centroamericano** es una franja árida que recorre el Pacífico de **Guatemala, El Salvador, Honduras, Nicaragua y Costa Rica**. Es una de las regiones más vulnerables del mundo al cambio climático: lluvias erráticas, sequías recurrentes y suelos degradados afectan a millones de pequeños agricultores.

**Qué muestra esta app** — humedad de la **zona radicular** (suelo entre ~0 y 100 cm de profundidad), medida por el satélite **SMAP (NASA)** cada ~3 días desde 2015. Los valores están en **m³/m³** (volumen de agua por volumen de suelo):

- **0.20–0.40** → suelo húmedo (lluvias recientes)
- **0.10–0.20** → suelo seco, estrés hídrico para cultivos de ciclo corto
- **< 0.10** → sequía severa

**Métricas del panel**:

| Métrica | Significado |
|---|---|
| Humedad más reciente | Promedio estacional (mayo–agosto) de la última celda/año disponible |
| Cambio entre extremos | Diferencia de humedad entre el primer y último año de la serie |
| Tendencia Mann–Kendall p | Prueba estadística: p < 0.05 indica tendencia significativa (subida/bajada) |
| Proyección | Extrapolación lineal de la tendencia hasta 2030 — exploratoria, no un pronóstico climático |
| Intervalo 95% | Banda de incertidumbre aproximada de la proyección |

**Mapas**: las cuadrículas (~1°) coloreadas muestran cada variable por celda sobre imagen satelital; las ciudades son referencias geográficas.""",
    },
    "en": {
        "title": "Deep Roots",
        "caption": "Root-zone soil moisture and agricultural drought signals in the Dry Corridor",
        "no_data": "No results found in data/ or outputs/. Run the pipeline (`raices-profundas --download-fao-roi`) to generate them.",
        "no_common": "No cells have both historical data and projections.",
        "cell": "Cell",
        "latest_moisture": "Latest moisture (m³/m³)",
        "change_first_last": "Change first→last (m³/m³)",
        "mk_p": "Mann–Kendall trend p",
        "projection": "Projection {year} (m³/m³)",
        "vs_baseline": "vs. {year}",
        "historical": "Historical SMAP",
        "pi95": "95% prediction interval",
        "extrapolation": "2015–2025 extrapolation",
        "x_axis": "Year",
        "y_axis": "Moisture (m³/m³)",
        "chart_title": "SMAP history and projection — {cell}",
        "pi_caption": "{status}. The band shows an approximate 95% interval based on historical variability and slope uncertainty.",
        "trend_map": "Trend map",
        "map_variable": "Map variable",
        "projection_map": "Spatial projection",
        "projection_year": "Projected year",
        "change_label": "Projected change (m³/m³)",
        "summary": "Per-cell summary",
        "footer": "The projection extrapolates the Sen slope of the SMAP 2015–2025 seasonal series up to 2030; it is exploratory, includes no climate scenarios, and is neither a causal projection nor a crop-specific forecast.",
        "info_title": "What is the Central American Dry Corridor?",
        "info": """The **Central American Dry Corridor** is an arid strip running along the Pacific coast of **Guatemala, El Salvador, Honduras, Nicaragua, and Costa Rica**. It is one of the world's most climate-vulnerable regions: erratic rainfall, recurrent droughts, and degraded soils affect millions of smallholder farmers.

**What this app shows** — **root-zone** soil moisture (soil roughly 0–100 cm deep), measured by NASA's **SMAP** satellite about every 3 days since 2015. Values are in **m³/m³** (water volume per soil volume):

- **0.20–0.40** → wet soil (recent rainfall)
- **0.10–0.20** → dry soil, water stress for short-cycle crops
- **< 0.10** → severe drought

**Panel metrics**:

| Metric | Meaning |
|---|---|
| Latest moisture | Seasonal average (May–August) for the latest available year/cell |
| Change first→last | Moisture difference between the first and last year of the series |
| Mann–Kendall trend p | Statistical test: p < 0.05 indicates a significant upward/downward trend |
| Projection | Linear extrapolation of the trend to 2030 — exploratory, not a climate forecast |
| 95% interval | Approximate uncertainty band for the projection |

**Maps**: the colored grid cells (~1°) show each variable per cell over satellite imagery; cities are geographic references.""",
    },
}


# Ciudades/poblados de referencia dentro y alrededor del Corredor Seco
CITIES = [
    ("Guatemala", 14.6349, -90.5069),
    ("Quetzaltenango", 14.8347, -91.5202),
    ("San Salvador", 13.6929, -89.2182),
    ("Santa Ana", 13.9945, -89.5597),
    ("Tegucigalpa", 14.0723, -87.1921),
    ("San Pedro Sula", 15.5042, -88.0374),
    ("Comayagua", 14.4553, -87.6424),
    ("Managua", 12.1140, -86.2362),
    ("León", 12.4360, -86.8783),
    ("San José", 9.9281, -84.0907),
]


def style_map(fig, grid):
    """Basemap satelital + nombres de ciudades de referencia."""
    minx, miny, maxx, maxy = grid.total_bounds
    center = {"lat": (miny + maxy) / 2, "lon": (minx + maxx) / 2}
    span = max(maxx - minx, maxy - miny)
    zoom = 8 if span <= 2 else 7 if span <= 5 else 6 if span <= 12 else 5
    fig.update_layout(map_style="satellite", map_center=center, map_zoom=zoom)
    fig.add_trace(go.Scattermap(
        lat=[c[1] for c in CITIES],
        lon=[c[2] for c in CITIES],
        mode="text",
        text=[c[0] for c in CITIES],
        textfont={"size": 11, "color": "white", "family": "Arial"},
        textposition="top right",
        hoverinfo="skip",
        showlegend=False,
    ))
    return fig


def t(key: str, **fmt) -> str:
    return STR[LANG][key].format(**fmt)


st.set_page_config(page_title="Raíces Profundas", layout="wide")

lang_col, _ = st.columns([1, 5])
with lang_col:
    LANG = "en" if st.selectbox("Language / Idioma", ["Español", "English"],
                                index=0, label_visibility="collapsed") == "English" else "es"

st.title(t("title"))
st.caption(t("caption"))
with st.expander(t("info_title")):
    st.markdown(t("info"))

# La app lee resultados precomputados: `data/` (versionada, usada en deploys)
# o `outputs/` (generada localmente por el pipeline).
root = Path(__file__).resolve().parent
candidates = [root / "outputs", root / "data"]  # outputs/ = corrida local fresca; data/ = snapshot versionado
base = next((d for d in candidates if (d / "smap_seasonal_timeseries.csv").exists()), candidates[0])
series_path = base / "smap_seasonal_timeseries.csv"
map_path = base / "smap_trends.geojson"
projection_path = base / "smap_projection.csv"
projection_map_path = base / "smap_projection.geojson"
if not all(path.exists() for path in [series_path, map_path, projection_path, projection_map_path]):
    st.info(t("no_data"))
    st.stop()


@st.cache_data
def load_outputs():
    return (
        pd.read_csv(series_path),
        gpd.read_file(map_path),
        pd.read_csv(projection_path),
        gpd.read_file(projection_map_path),
    )


series, grid, projections, projection_grid = load_outputs()
trends = pd.DataFrame(grid.drop(columns="geometry"))

cell_ids = sorted(set(series["cell_id"].unique()) & set(projections["cell_id"].unique()))
if not cell_ids:
    st.warning(t("no_common"))
    st.stop()
cell = st.selectbox(t("cell"), cell_ids)
selected = series[series.cell_id == cell].sort_values("year")
latest = selected.iloc[-1]["rootzone_moisture"]
trendrow = trends[trends.cell_id == cell].iloc[0]
cell_projection = projections[projections.cell_id == cell].sort_values("forecast_year")
target_projection = cell_projection.iloc[-1]

a, b, c, d = st.columns(4)
a.metric(t("latest_moisture"), f"{latest:.3f}")
b.metric(t("change_first_last"), f"{trendrow['moisture_change_first_last']:+.3f}")
c.metric(t("mk_p"), f"{trendrow['mk_p']:.3f}" if pd.notna(trendrow["mk_p"]) else "n/d")
d.metric(t("projection", year=int(target_projection['forecast_year'])),
         f"{target_projection['forecast_rootzone_moisture']:.3f}",
         delta=f"{target_projection['change_from_baseline']:+.3f} {t('vs_baseline', year=int(target_projection['baseline_year']))}")

fig = go.Figure()
fig.add_trace(go.Scatter(x=selected.year, y=selected.rootzone_moisture,
                         mode="lines+markers", name=t("historical")))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year, y=cell_projection.upper_95,
                         mode="lines", line={"width": 0}, showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year, y=cell_projection.lower_95,
                         mode="lines", line={"width": 0}, fill="tonexty",
                         fillcolor="rgba(255, 127, 14, 0.18)", name=t("pi95")))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year,
                         y=cell_projection.forecast_rootzone_moisture,
                         mode="lines+markers", line={"dash": "dash"},
                         name=t("extrapolation")))
fig.update_layout(xaxis_title=t("x_axis"), yaxis_title=t("y_axis"),
                  title=t("chart_title", cell=cell))
st.plotly_chart(fig, use_container_width=True)
status = target_projection['projection_status']
if LANG == "en":
    status = ("Significant trend" if "significativa" in status
              else "Exploratory extrapolation: trend not significant")
st.caption(t("pi_caption", status=status))

st.subheader(t("trend_map"))
field = st.selectbox(t("map_variable"), ["sen_slope_per_year", "mk_p", "classification"])
if field == "classification":
    map_fig = px.choropleth_map(grid, geojson=grid.__geo_interface__, locations="cell_id",
        featureidkey="properties.cell_id", color=field,
        hover_name="cell_id", hover_data=[field])
else:
    map_fig = px.choropleth_map(grid, geojson=grid.__geo_interface__, locations="cell_id",
        featureidkey="properties.cell_id", color=field, color_continuous_scale="RdYlBu",
        hover_name="cell_id",
        hover_data=["n_years", "mk_p", "moisture_change_first_last"])
st.plotly_chart(style_map(map_fig, grid), use_container_width=True)

st.subheader(t("projection_map"))
projection_years = sorted(int(column.replace("change_", "")) for column in projection_grid.columns
                          if column.startswith("change_"))
map_year = st.selectbox(t("projection_year"), projection_years, index=len(projection_years) - 1)
projection_field = f"change_{map_year}"
projection_fig = px.choropleth_map(
    projection_grid, geojson=projection_grid.__geo_interface__, locations="cell_id",
    featureidkey="properties.cell_id", color=projection_field,
    color_continuous_scale="RdYlBu",
    hover_name="cell_id", labels={projection_field: t("change_label")})
st.plotly_chart(style_map(projection_fig, projection_grid), use_container_width=True)

st.subheader(t("summary"))
st.dataframe(trends.drop(columns="geometry", errors="ignore"), use_container_width=True)
st.caption(t("footer"))
