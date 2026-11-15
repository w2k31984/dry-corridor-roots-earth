"""Small Streamlit dashboard for outputs produced by the raices_profundas pipeline."""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Raíces Profundas", layout="wide")
st.title("Raíces Profundas")
st.caption("Humedad de la zona radicular y señales de sequía agrícola en el Corredor Seco")

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
    st.info("No hay resultados en data/ ni outputs/. Ejecuta el pipeline "
            "(`raices-profundas --download-fao-roi`) para generarlos.")
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
    st.warning("No hay celdas con datos históricos y proyección en común.")
    st.stop()
cell = st.selectbox("Celda", cell_ids)
selected = series[series.cell_id == cell].sort_values("year")
latest = selected.iloc[-1]["rootzone_moisture"]
trendrow = trends[trends.cell_id == cell].iloc[0]
cell_projection = projections[projections.cell_id == cell].sort_values("forecast_year")
target_projection = cell_projection.iloc[-1]

a, b, c, d = st.columns(4)
a.metric("Humedad más reciente (m³/m³)", f"{latest:.3f}")
b.metric("Cambio entre extremos (m³/m³)", f"{trendrow['moisture_change_first_last']:+.3f}")
c.metric("Tendencia Mann–Kendall p", f"{trendrow['mk_p']:.3f}" if pd.notna(trendrow["mk_p"]) else "n/d")
d.metric(f"Proyección {int(target_projection['forecast_year'])} (m³/m³)", f"{target_projection['forecast_rootzone_moisture']:.3f}",
         delta=f"{target_projection['change_from_baseline']:+.3f} vs. {int(target_projection['baseline_year'])}")

fig = go.Figure()
fig.add_trace(go.Scatter(x=selected.year, y=selected.rootzone_moisture,
                         mode="lines+markers", name="SMAP histórico"))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year, y=cell_projection.upper_95,
                         mode="lines", line={"width": 0}, showlegend=False, hoverinfo="skip"))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year, y=cell_projection.lower_95,
                         mode="lines", line={"width": 0}, fill="tonexty",
                         fillcolor="rgba(255, 127, 14, 0.18)", name="Intervalo de predicción 95%"))
fig.add_trace(go.Scatter(x=cell_projection.forecast_year,
                         y=cell_projection.forecast_rootzone_moisture,
                         mode="lines+markers", line={"dash": "dash"},
                         name="Extrapolación 2015–2025"))
fig.update_layout(xaxis_title="Año", yaxis_title="Humedad (m³/m³)",
                  title=f"Historial SMAP y proyección — {cell}")
st.plotly_chart(fig, use_container_width=True)
st.caption(f"{target_projection['projection_status']}. La banda muestra un intervalo aproximado del 95% basado en la variabilidad histórica y la incertidumbre de la pendiente.")

st.subheader("Mapa de tendencias")
field = st.selectbox("Variable del mapa", ["sen_slope_per_year", "mk_p", "classification"])
if field == "classification":
    map_fig = px.choropleth_mapbox(grid, geojson=grid.__geo_interface__, locations="cell_id",
        featureidkey="properties.cell_id", color=field, mapbox_style="carto-positron", center={"lat": 13.5, "lon": -88}, zoom=5,
        opacity=0.65, hover_name="cell_id", hover_data=[field])
else:
    map_fig = px.choropleth_mapbox(grid, geojson=grid.__geo_interface__, locations="cell_id",
        featureidkey="properties.cell_id", color=field, color_continuous_scale="RdYlBu", mapbox_style="carto-positron",
        center={"lat": 13.5, "lon": -88}, zoom=5, opacity=0.65, hover_name="cell_id",
        hover_data=["n_years", "mk_p", "moisture_change_first_last"])
st.plotly_chart(map_fig, use_container_width=True)

st.subheader("Proyección espacial")
projection_years = sorted(int(column.replace("change_", "")) for column in projection_grid.columns
                          if column.startswith("change_"))
map_year = st.selectbox("Año proyectado", projection_years, index=len(projection_years) - 1)
projection_field = f"change_{map_year}"
projection_fig = px.choropleth_mapbox(
    projection_grid, geojson=projection_grid.__geo_interface__, locations="cell_id",
    featureidkey="properties.cell_id", color=projection_field,
    color_continuous_scale="RdYlBu", mapbox_style="carto-positron",
    center={"lat": 13.5, "lon": -88}, zoom=5, opacity=0.65,
    hover_name="cell_id", labels={projection_field: "Cambio proyectado (m³/m³)"})
st.plotly_chart(projection_fig, use_container_width=True)

st.subheader("Resumen por celda")
st.dataframe(trends.drop(columns="geometry", errors="ignore"), use_container_width=True)
st.caption("La proyección extrapola la pendiente Sen de la serie estacional SMAP 2015–2025 hasta 2030; es exploratoria, no incluye escenarios climáticos y no representa una proyección causal ni un pronóstico para un cultivo específico.")
