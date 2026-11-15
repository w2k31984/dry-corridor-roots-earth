"""Catálogo de variables disponibles en el dashboard, con definiciones simples."""
from __future__ import annotations

SMAP = "smap_rootzone"

THEMES = {
    "drought": {"es": "Sequía y suelo", "en": "Drought & soil"},
    "rain": {"es": "Lluvia", "en": "Rainfall"},
    "heat": {"es": "Calor", "en": "Heat"},
    "water": {"es": "Agua en el aire y evaporación", "en": "Air moisture & evaporation"},
}

VARIABLES = {
    SMAP: {
        "themes": ["drought"],
        "source": "NASA SMAP L4 (SPL4SMGP v008)",
        "units": "m³/m³", "decimals": 3, "increase_is_wetter": True,
        "name": {"es": "Humedad del suelo en la zona radicular (SMAP)",
                 "en": "Root-zone soil moisture (SMAP)"},
        "definition": {
            "es": "Agua disponible en los primeros ~100 cm de suelo, donde están las raíces de los cultivos. "
                  "Valores bajos (< 0.20 m³/m³) indican estrés hídrico. Estimada por el satélite SMAP "
                  "combinado con un modelo de superficie terrestre.",
            "en": "Water held in the top ~100 cm of soil, where crop roots live. Low values (< 0.20 m³/m³) "
                  "mean water stress. Estimated from the SMAP satellite combined with a land-surface model.",
        },
    },
    "GWETROOT": {
        "themes": ["drought"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "0–1", "decimals": 3, "increase_is_wetter": True,
        "name": {"es": "Humedad relativa del suelo – raíces (MERRA-2)",
                 "en": "Root-zone soil wetness (MERRA-2)"},
        "definition": {
            "es": "Qué tan lleno de agua está el suelo de las raíces: 0 = completamente seco, 1 = saturado. "
                  "Calculado por el modelo global MERRA-2.",
            "en": "How full of water the root-zone soil is: 0 = completely dry, 1 = saturated. "
                  "Computed by the MERRA-2 global model.",
        },
    },
    "GWETTOP": {
        "themes": ["drought"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "0–1", "decimals": 3, "increase_is_wetter": True,
        "name": {"es": "Humedad del suelo superficial (MERRA-2)",
                 "en": "Surface soil wetness (MERRA-2)"},
        "definition": {
            "es": "Humedad de los primeros ~5 cm de suelo (0 = seco, 1 = saturado). Responde rápido a la "
                  "lluvia y al sol; útil para detectar sequías cortas como la canícula.",
            "en": "Wetness of the top ~5 cm of soil (0 = dry, 1 = saturated). Reacts quickly to rain and "
                  "sun; useful for short droughts such as the mid-summer drought (canícula).",
        },
    },
    "PRECTOTCORR": {
        "themes": ["rain", "drought"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "mm/día", "decimals": 2, "increase_is_wetter": True,
        "name": {"es": "Precipitación (MERRA-2 corregida)", "en": "Precipitation (MERRA-2, bias-corrected)"},
        "definition": {
            "es": "Lluvia promedio por día, en milímetros. 1 mm = 1 litro de agua por metro cuadrado.",
            "en": "Average rainfall per day, in millimetres. 1 mm = 1 litre of water per square metre.",
        },
    },
    "T2M": {
        "themes": ["heat"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "°C", "decimals": 2, "increase_is_wetter": False,
        "name": {"es": "Temperatura del aire a 2 m", "en": "Air temperature at 2 m"},
        "definition": {
            "es": "Temperatura media del aire a la altura de una persona (2 m sobre el suelo).",
            "en": "Average air temperature at about human height (2 m above the ground).",
        },
    },
    "T2M_MAX": {
        "themes": ["heat"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "°C", "decimals": 2, "increase_is_wetter": False,
        "name": {"es": "Temperatura máxima del aire a 2 m", "en": "Maximum air temperature at 2 m"},
        "definition": {
            "es": "La temperatura más alta registrada en el mes (a 2 m). Indica olas de calor que dañan cultivos.",
            "en": "The highest temperature of the month (at 2 m). Signals heat waves that damage crops.",
        },
    },
    "RH2M": {
        "themes": ["water"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "%", "decimals": 1, "increase_is_wetter": True,
        "name": {"es": "Humedad relativa del aire a 2 m", "en": "Relative humidity at 2 m"},
        "definition": {
            "es": "Cuánto vapor de agua tiene el aire comparado con el máximo posible a esa temperatura (0–100%).",
            "en": "How much water vapour the air holds compared with the maximum possible at that temperature (0–100%).",
        },
    },
    "EVLAND": {
        "themes": ["water", "drought"],
        "source": "NASA MERRA-2 (vía NASA POWER)",
        "units": "mm/día", "decimals": 2, "increase_is_wetter": False,
        "name": {"es": "Evaporación desde el suelo y las plantas", "en": "Land evaporation"},
        "definition": {
            "es": "Agua que pasa del suelo y la vegetación a la atmósfera cada día. Más evaporación con poca "
                  "lluvia seca el suelo más rápido.",
            "en": "Water moving from soil and vegetation into the atmosphere each day. More evaporation with "
                  "little rain dries soils faster.",
        },
    },
}

SEASONS = {
    "year": {"months": list(range(1, 13)), "es": "Año completo (ene–dic)", "en": "Whole year (Jan–Dec)"},
    "primera": {"months": [5, 6, 7, 8], "es": "Primera (may–ago)", "en": "Primera season (May–Aug)"},
    "canicula": {"months": [7, 8], "es": "Canícula (jul–ago)", "en": "Mid-summer drought (Jul–Aug)"},
    "postrera": {"months": [9, 10, 11], "es": "Postrera (sep–nov)", "en": "Postrera season (Sep–Nov)"},
    "dry": {"months": [12, 1, 2, 3, 4], "es": "Estación seca (dic–abr)", "en": "Dry season (Dec–Apr)"},
}

# Sugerencias por tipo de paisaje (regla simple basada en la elevación)
LANDSCAPE_HINTS = {
    "low": ["T2M_MAX", "PRECTOTCORR", "GWETROOT"],
    "mid": ["GWETROOT", "PRECTOTCORR", "EVLAND"],
    "high": ["T2M", "RH2M", "GWETTOP"],
}
