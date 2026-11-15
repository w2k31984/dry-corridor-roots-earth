# Raíces Profundas — Corredor Seco

Análisis de humedad de la zona radicular (SMAP L4, `sm_rootzone`) y señales de
sequía agrícola en el Corredor Seco Centroamericano, usando datos de NASA
Earthdata y Harmony, con un dashboard en Streamlit.

## Estructura del proyecto

```
├── pyproject.toml          # Empaquetado, dependencias y entry point `raices-profundas`
├── render.yaml             # Configuración de despliegue en Render
├── app.py                  # Dashboard Streamlit
├── root_project.py         # Shim de compatibilidad → raices_profundas.cli
├── test.py                 # Prueba de autenticación con Earthdata Login
├── scripts/smoke_test.py   # Corrida corta de validación (1 año, 2 meses)
├── src/raices_profundas/   # Paquete principal
│   ├── config.py           # Constantes (capa FAO, variable SMAP)
│   ├── geo.py              # ROI, grilla de análisis, descarga FAO
│   ├── smap.py             # earthaccess + Harmony, reducción de GeoTIFFs
│   ├── stats.py            # Tendencias, proyección y clasificación
│   ├── pipeline.py         # Orquestación del pipeline
│   └── cli.py              # Argumentos de línea de comandos
├── tests/                  # Tests unitarios (pytest, sin red)
└── outputs/                # Resultados generados (no se versiona)
```

## Requisitos

- Python 3.12
- Credenciales de Earthdata Login en `.env`:

  ```
  EARTHDATA_USERNAME=tu_usuario
  EARTHDATA_PASSWORD=tu_password
  ```

  Consigue una cuenta gratuita en <https://urs.earthdata.nasa.gov>.

- Dependencias (definidas en `pyproject.toml`; también hay `.env.example` como
  plantilla):

  ```bash
  pip install -e ".[dev]"   # instala el paquete + pytest para tests
  ```

### Tests unitarios

```bash
pytest
```

Cubren la lógica pura (grilla, estacionalidad, tendencias, proyección) sin
necesidad de red ni credenciales.

## Uso

### 1. Verificar autenticación

```bash
python test.py
```

Debe imprimir `Autenticado: True`.

### 2. Ejecutar el pipeline

Opción A — descargar la delimitación FAO del Corredor Seco automáticamente:

```bash
raices-profundas --download-fao-roi
```

Opción B — usar un GeoJSON propio del área de estudio (WGS84):

```bash
raices-profundas --roi ruta/al/roi.geojson
```

(`python root_project.py ...` sigue funcionando como alias.)

Argumentos útiles:

| Argumento | Default | Descripción |
|---|---|---|
| `--start-year` / `--end-year` | 2015 / 2026 | Rango de años (final exclusivo) |
| `--start-month` / `--end-month` | 5 / 9 | Meses de la temporada seca (final exclusivo, 1–12) |
| `--grid-degrees` | 1.0 | Resolución de la grilla en grados |
| `--granule-stride` | 1 | Descarga 1 de cada N granulos por mes (p. ej. 3 ≈ 1 obs/día) |
| `--projection-end-year` | 2030 | Último año de proyección |
| `--climate-csv` | — | CSV con tendencias climáticas por `cell_id` |
| `--out` | `outputs` | Directorio de salida |

Corrida más ligera (menos granulos y menos años):

```bash
raices-profundas --granule-stride 3 --grid-degrees 1.0 --start-year 2018
```

El pipeline:

1. Descarga (o lee) el polígono ROI y genera una grilla de celdas.
2. Busca granulos SMAP L4 (`SPL4SMGP`, versión 008) por año/mes vía
   `earthaccess`.
3. Lanza jobs de Harmony para recortar cada mes al ROI y a la variable
   `Geophysical_Data/sm_rootzone`, y descarga los GeoTIFFs.
4. Promedia los píxeles de cada GeoTIFF por celda (`reduce_tiff`).
5. Calcula tendencias por celda: tau y p de Mann–Kendall, pendiente de Sen
   (`theilslopes`) y cambio entre el primer y último año.
6. Extrapola la tendencia de Sen hasta `--projection-end-year` con un intervalo
   de predicción aproximado del 95%.
7. Si se pasa `--climate-csv`, clasifica cada celda según señales conjuntas de
   sequedad del suelo y estrés por calor.

### 3. Explorar en el dashboard

```bash
streamlit run app.py
```

La app lee los archivos de `outputs/` y muestra:

- Serie histórica SMAP por celda con la proyección y su banda de incertidumbre.
- Mapas de tendencias (pendiente Sen, p de Mann–Kendall, clasificación).
- Mapa de cambio proyectado por año.
- Tabla resumen por celda.

Si `outputs/` no existe, la app muestra un aviso para ejecutar el pipeline.

## Salidas generadas (`outputs/`)

| Archivo | Contenido |
|---|---|
| `grid.geojson` | Grilla de celdas de análisis |
| `corredor_seco_fao.geojson` | ROI descargado de la FAO (si aplica) |
| `granules/` | GeoTIFFs subset por Harmony, por año-mes |
| `smap_observations.csv` | Observaciones por celda, año, mes y timestamp |
| `smap_seasonal_timeseries.csv` | Promedio estacional por celda y año |
| `smap_trends.csv` / `.geojson` | Tendencias y clasificación por celda |
| `smap_projection.csv` / `.geojson` | Proyecciones por celda y año |

## Notas y limitaciones

- La proyección es una extrapolación lineal de la pendiente de Sen de la serie
  estacional; es exploratoria, no incluye escenarios climáticos ni pretende ser
  un pronóstico causal.
- La corrida completa (2015–2025, temporada seca) implica ~55 jobs de Harmony;
  requiere conexión estable y credenciales Earthdata válidas.
- `render.yaml` permite desplegar el dashboard en Render, pero la app depende de
  los archivos de `outputs/`; en un despliegue limpio habrá que generar o subir
  esos datos previamente.
- Licencia de datos SMAP: ver los términos de NASA Earthdata. La delimitación
  FAO del Corredor Seco es pública (ArcGIS REST, WFL1).

## Monitoreo y reanudación

La corrida completa (~55 jobs de Harmony, uno por año-mes) tarda varias horas.
El proceso puede correrse en background y los resultados parciales se conservan
en `outputs/granules/AAAA-MM/`:

```bash
ls outputs/granules/ | wc -l   # 55 = todos los meses descargados
ls outputs/                    # los CSV/GeoJSON finales aparecen al terminar
```

Si el proceso se interrumpe, los meses ya descargados no se pierden. Volver a
ejecutar el mismo comando reenvía los jobs de Harmony (no hay caché de jobs),
pero `overwrite=False` evita volver a descargar los GeoTIFFs existentes.

---

# English version

# Deep Roots — Dry Corridor

Analysis of root-zone soil moisture (SMAP L4, `sm_rootzone`) and agricultural
drought signals in the Central American Dry Corridor, using NASA Earthdata and
Harmony data, with a Streamlit dashboard.

## Project structure

```
├── pyproject.toml          # Packaging, dependencies and `raices-profundas` entry point
├── render.yaml             # Render deployment configuration
├── app.py                  # Streamlit dashboard
├── root_project.py         # Compatibility shim → raices_profundas.cli
├── test.py                 # Earthdata Login authentication check
├── scripts/smoke_test.py   # Short validation run (1 year, 2 months)
├── src/raices_profundas/   # Main package
│   ├── config.py           # Constants (FAO layer, SMAP variable)
│   ├── geo.py              # ROI, analysis grid, FAO download
│   ├── smap.py             # earthaccess + Harmony, GeoTIFF reduction
│   ├── stats.py            # Trends, projection and classification
│   ├── pipeline.py         # Pipeline orchestration
│   └── cli.py              # Command-line arguments
├── tests/                  # Unit tests (pytest, no network)
└── outputs/                # Generated results (not versioned)
```

## Requirements

- Python 3.12
- Earthdata Login credentials in `.env`:

  ```
  EARTHDATA_USERNAME=your_username
  EARTHDATA_PASSWORD=your_password
  ```

  Get a free account at <https://urs.earthdata.nasa.gov>.

- Dependencies (defined in `pyproject.toml`; `.env.example` is provided as a
  template):

  ```bash
  pip install -e ".[dev]"   # installs the package + pytest for tests
  ```

### Unit tests

```bash
pytest
```

They cover the pure logic (grid, seasonality, trends, projection) with no
network or credentials required.

## Usage

### 1. Verify authentication

```bash
python test.py
```

It should print `Autenticado: True`.

### 2. Run the pipeline

Option A — download the FAO Dry Corridor boundary automatically:

```bash
raices-profundas --download-fao-roi
```

Option B — use your own study-area GeoJSON (WGS84):

```bash
raices-profundas --roi path/to/roi.geojson
```

(`python root_project.py ...` still works as an alias.)

Useful arguments:

| Argument | Default | Description |
|---|---|---|
| `--start-year` / `--end-year` | 2015 / 2026 | Year range (end exclusive) |
| `--start-month` / `--end-month` | 5 / 9 | Dry-season months (end exclusive, 1–12) |
| `--grid-degrees` | 1.0 | Grid resolution in degrees |
| `--granule-stride` | 1 | Downloads 1 of every N granules per month (e.g. 3 ≈ 1 obs/day) |
| `--projection-end-year` | 2030 | Last projection year |
| `--climate-csv` | — | CSV with climate trends per `cell_id` |
| `--out` | `outputs` | Output directory |

Lighter run (fewer granules and fewer years):

```bash
raices-profundas --granule-stride 3 --grid-degrees 1.0 --start-year 2018
```

The pipeline:

1. Downloads (or reads) the ROI polygon and builds a grid of cells.
2. Searches SMAP L4 granules (`SPL4SMGP`, version 008) by year/month via
   `earthaccess`.
3. Submits Harmony jobs to subset each month to the ROI and the
   `Geophysical_Data/sm_rootzone` variable, then downloads the GeoTIFFs.
4. Averages each GeoTIFF's pixels per cell (`reduce_tiff`).
5. Computes per-cell trends: Mann–Kendall tau and p, Sen slope
   (`theilslopes`) and first-to-last change.
6. Extrapolates the Sen trend up to `--projection-end-year` with an
   approximate 95% prediction interval.
7. If `--climate-csv` is given, classifies each cell based on joint soil-
   drying and heat-stress signals.

### 3. Explore the dashboard

```bash
streamlit run app.py
```

The app reads the files in `outputs/` and shows:

- Per-cell SMAP historical series with the projection and its uncertainty band.
- Trend maps (Sen slope, Mann–Kendall p, classification).
- Projected-change map by year.
- Per-cell summary table.

If `outputs/` does not exist, the app shows a notice to run the pipeline.

## Generated outputs (`outputs/`)

| File | Content |
|---|---|
| `grid.geojson` | Analysis grid cells |
| `corredor_seco_fao.geojson` | FAO ROI download (if applicable) |
| `granules/` | Harmony-subset GeoTIFFs, by year-month |
| `smap_observations.csv` | Observations per cell, year, month and timestamp |
| `smap_seasonal_timeseries.csv` | Seasonal average per cell and year |
| `smap_trends.csv` / `.geojson` | Trends and classification per cell |
| `smap_projection.csv` / `.geojson` | Projections per cell and year |

## Notes and limitations

- The projection is a linear extrapolation of the Sen slope of the seasonal
  series; it is exploratory, includes no climate scenarios, and is not a
  causal forecast.
- A full run (2015–2025, dry season) involves ~55 Harmony jobs; it requires a
  stable connection and valid Earthdata credentials.
- `render.yaml` deploys the dashboard to Render, but the app depends on the
  files in `outputs/`; on a clean deployment those data must be generated or
  uploaded beforehand.
- SMAP data license: see the NASA Earthdata terms. The FAO Dry Corridor
  boundary is public (ArcGIS REST, WFL1).

## Monitoring and resume

A full run (~55 Harmony jobs, one per year-month) takes several hours. It can
run in the background and partial results are kept in
`outputs/granules/YYYY-MM/`:

```bash
ls outputs/granules/ | wc -l   # 55 = all months downloaded
ls outputs/                    # final CSV/GeoJSON files appear at the end
```

If the process is interrupted, already-downloaded months are not lost.
Re-running the same command resubmits the Harmony jobs (there is no job
cache), but `overwrite=False` avoids re-downloading existing GeoTIFFs.
