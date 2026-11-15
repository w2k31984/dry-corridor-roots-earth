"""Nombres legibles para las celdas: localidad de referencia más cercana."""
from __future__ import annotations

import math

PLACES = [
    ("Tapachula", "MX", 14.906, -92.263),
    ("Retalhuleu", "GT", 14.537, -91.677),
    ("Mazatenango", "GT", 14.534, -91.503),
    ("Quetzaltenango", "GT", 14.835, -91.520),
    ("Huehuetenango", "GT", 15.319, -91.470),
    ("San Marcos", "GT", 14.966, -91.795),
    ("Escuintla", "GT", 14.305, -90.785),
    ("Ciudad de Guatemala", "GT", 14.635, -90.507),
    ("Salamá", "GT", 15.103, -90.316),
    ("Chiquimula", "GT", 14.800, -89.545),
    ("Zacapa", "GT", 14.972, -89.530),
    ("Jutiapa", "GT", 14.292, -89.896),
    ("El Progreso", "GT", 14.851, -90.068),
    ("Cobán", "GT", 15.470, -90.371),
    ("Ahuachapán", "SV", 13.921, -89.845),
    ("Santa Ana", "SV", 13.994, -89.560),
    ("San Salvador", "SV", 13.693, -89.218),
    ("Chalatenango", "SV", 14.034, -88.939),
    ("San Vicente", "SV", 13.641, -88.785),
    ("San Miguel", "SV", 13.481, -88.178),
    ("La Unión", "SV", 13.337, -87.844),
    ("Santa Rosa de Copán", "HN", 14.767, -88.779),
    ("Gracias", "HN", 14.588, -88.582),
    ("La Esperanza", "HN", 14.311, -88.177),
    ("Santa Bárbara", "HN", 14.919, -88.236),
    ("San Pedro Sula", "HN", 15.504, -88.025),
    ("Comayagua", "HN", 14.455, -87.642),
    ("Tegucigalpa", "HN", 14.072, -87.192),
    ("Choluteca", "HN", 13.301, -87.191),
    ("Nacaome", "HN", 13.531, -87.488),
    ("Yuscarán", "HN", 13.944, -86.851),
    ("Danlí", "HN", 14.032, -86.583),
    ("Juticalpa", "HN", 14.665, -86.219),
    ("Catacamas", "HN", 14.848, -85.894),
    ("Danlí", "HN", 14.031, -86.583),
    ("Campamento", "HN", 14.553, -86.660),
    ("Ocotal", "NI", 13.632, -86.476),
    ("Yoro", "HN", 15.138, -87.128),
    ("Ocotal", "NI", 13.632, -86.476),
    ("Somoto", "NI", 13.481, -86.583),
    ("Estelí", "NI", 13.092, -86.354),
    ("Chinandega", "NI", 12.629, -87.131),
    ("León", "NI", 12.436, -86.878),
    ("Managua", "NI", 12.114, -86.236),
    ("Jalapa", "NI", 13.917, -86.124),
]

COUNTRY_NAMES = {
    "es": {"MX": "México", "GT": "Guatemala", "SV": "El Salvador", "HN": "Honduras", "NI": "Nicaragua"},
    "en": {"MX": "Mexico", "GT": "Guatemala", "SV": "El Salvador", "HN": "Honduras", "NI": "Nicaragua"},
}


def _distance_km(lat1, lon1, lat2, lon2) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi, dlmb = phi2 - phi1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def nearest_place(lat: float, lon: float) -> tuple[str, str, float]:
    """(localidad, código de país, distancia en km) más cercana al punto."""
    name, country, plat, plon = min(PLACES, key=lambda p: _distance_km(lat, lon, p[2], p[3]))
    return name, country, _distance_km(lat, lon, plat, plon)


def landscape(elevation_m: float, lang: str = "es") -> str:
    """Tipo de paisaje aproximado según la elevación."""
    labels = {
        "es": ("planicie costera / baja", "zona media de ladera", "altiplano / montaña"),
        "en": ("coastal / lowland plain", "mid-elevation hillside", "highlands / mountains"),
    }[lang]
    if elevation_m < 300:
        return labels[0]
    if elevation_m < 1000:
        return labels[1]
    return labels[2]
