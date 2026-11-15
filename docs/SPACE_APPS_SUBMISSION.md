# NASA Space Apps 2026 — submission draft

Team: **Ad Astra- Programming, Data Spatial & Planet Investigation**
Challenge: **Be An Earth System Trend Detective!**
Final project: https://raices-del-corredor.onrender.com/ · Code: https://github.com/w2k31984/dry-corridor-roots-earth
Project demo (7-slide deck): https://github.com/w2k31984/dry-corridor-roots-earth/blob/master/docs/demo/RaicesProfundas_SpaceApps2026_demo.pdf
Project demo (30-second video, English voice-over + subtitles): https://github.com/w2k31984/dry-corridor-roots-earth/raw/master/docs/demo/RaicesProfundas_SpaceApps2026_demo.mp4

## High-level summary

*Raíces Profundas* (Deep Roots) is a bilingual (ES/EN) trend-detective app for the Central American
Dry Corridor, where recurrent drought and heat threaten millions of smallholder farmers. Users choose
**what** to investigate (root-zone soil moisture from NASA SMAP L4, or precipitation, air temperature,
maximum temperature, soil wetness, humidity and evapotranspiration from NASA MERRA-2 via NASA POWER),
**where** (25 ~1° cells labelled by nearest town, coordinates and landscape type, or a click on the
map) and **when** (whole year, Primera, canícula, Postrera or dry season, any period 1981–2025). The
app answers four questions in a "detective's verdict" — what is changing, where, how much and whether
it is statistically significant — using Sen's slope with a 95% confidence interval, the Mann–Kendall
test, linear regression with a t-test and 95% CI, and a seasonal Mann–Kendall test on monthly
anomalies. A trend map highlights cells with significant change, so users can see that the same
variable can trend in opposite directions in different regions (e.g. maximum temperature warming in
the western highlands while cooling in eastern Honduras).

## Project details

- **Variables:** SMAP L4 `sm_rootzone` (SPL4SMGP v008, 2015–2025); MERRA-2 `PRECTOTCORR`, `T2M`,
  `T2M_MAX`, `GWETROOT`, `GWETTOP`, `RH2M`, `EVLAND` (monthly, 1981–2025).
- **Pipeline:** FAO Dry Corridor boundary → ~1° grid → SMAP subset with NASA Harmony/earthaccess and
  averaged per cell and season; MERRA-2 monthly series from the NASA POWER API at a representative
  point per cell.
- **Statistics:** seasonal means per year → Sen's slope (+95% CI), Mann–Kendall τ and p, OLS slope,
  t-test p, R², 95% CI; seasonal Mann–Kendall on anomalies with the seasonal cycle removed.
- **Learning aids:** three solved cases (2023 El Niño drought, highland warming, opposite regional
  trends), topic-based variable suggestions by landscape, plain-language glossary, CSV downloads and
  links to Giovanni, AppEEARS, Data Rods, NASA POWER and KNMI Climate Explorer.
- **Exploratory extra:** a clearly-labelled linear extrapolation of SMAP soil moisture to 2030.
- **Tools:** Python, pandas, GeoPandas, SciPy, Streamlit, Plotly, earthaccess, NASA Harmony, Render.

## NASA data

- SMAP L4 Global 3-hourly 9 km Surface and Root Zone Soil Moisture, SPL4SMGP v008 —
  https://nsidc.org/data/spl4smgp
- MERRA-2 via NASA POWER monthly API — https://power.larc.nasa.gov/
- NASA Harmony — https://harmony.earthdata.nasa.gov/ · earthaccess — https://earthaccess.readthedocs.io/

## Other references

- FAO Dry Corridor boundary (ArcGIS REST, WFL1).
- Mann (1945), Kendall (1975), Sen (1968), Hirsch et al. (1982) seasonal Kendall test.

## Use of artificial intelligence

*Review and adapt before submitting.* AI coding assistance (Devin, by Cognition) was used to help
write and refactor parts of the code (statistics module, NASA POWER client, Streamlit interface) and
documentation. All analysis choices, data sources and results were reviewed by the team. No
AI-generated images, video or audio are used.
