#!/usr/bin/env python3
"""
preprocesado_energia.py  ·  TVD — Tema 5: Transición Ecológica y Energía
=========================================================================
Flujo de trabajo con Live Server
---------------------------------
1. Edita las constantes de la SECCIÓN 1.
2. Ejecuta:  python preprocesado_energia.py
   → genera dashboard_data.json en el mismo directorio.
3. Con Live Server activo en VS Code el navegador se recarga solo
   y el dashboard muestra los datos actualizados.

Dependencias: pip install pandas numpy
"""

import json, sys, numpy as np, pandas as pd
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 1 · CONFIGURACIÓN  ← edita aquí para actualizar el dashboard
# ══════════════════════════════════════════════════════════════════

# Fuente de datos
URL_DATOS  = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"
RUTA_LOCAL = Path("owid-energy-data.csv")      # ruta al CSV local (mismo directorio)
RUTA_SALIDA = Path("dashboard_data.json")       # fichero que consume el dashboard

# ── Filtros de preprocesado ─────────────────────────────────────
YEAR_MIN = 2000    # solo registros con year >= YEAR_MIN
YEAR_MAX = None    # None = sin límite superior

# ── Selección dinámica ──────────────────────────────────────────
# El CSV decide qué variables y países entran; estos valores solo controlan tamaño.
N_PAISES_VIZ = 20
N_PAISES_COMPARATIVA = 9
N_PAISES_TENDENCIA = 20
N_PAISES_TRANSICION = 12
MIN_PAISES_SCATTER = 150
PAIS_REF_PREFERIDO = "Spain"
KPI_YEAR       = 2024         # año "actual" para los KPIs

# ══════════════════════════════════════════════════════════════════
# SECCIÓN 2 · LÓGICA DE PROCESADO (no es necesario editar aquí)
# ══════════════════════════════════════════════════════════════════

def _f(v):
    if isinstance(v, (np.float32, np.float64)): v = float(v)
    if isinstance(v, (np.int32, np.int64)):     return int(v)
    if isinstance(v, float) and (np.isnan(v) or np.isinf(v)): return None
    return v

def _clean(obj):
    if isinstance(obj, dict):  return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):  return [_clean(v) for v in obj]
    return _f(obj)


def _label_fuente(col):
    normalizaciones = (
        ("other_renewables", "otras renovables"),
        ("other_renewable_exc_biofuel", "otras renovables sin biocombustibles"),
        ("other_renewable", "otras renovables"),
        ("low_carbon", "bajo carbono"),
        ("renewables", "renovables"),
        ("biofuel", "biocombustibles"),
        ("fossil_fuel", "combustibles fósiles"),
        ("fossil", "fósil"),
        ("hydro", "hidroeléctrica"),
        ("nuclear", "nuclear"),
        ("solar", "solar"),
        ("coal", "carbón"),
        ("wind", "eólica"),
        ("oil", "petróleo"),
        ("gas", "gas"),
    )
    for key, label in normalizaciones:
        if col == key or col.startswith(f"{key}_"):
            return label
    return col.split("_", 1)[0].replace("_", " ")


def describir_variable(col):
    especiales = {
        "country": ("cat.", "País o territorio"),
        "year": ("num. (temporal)", "Año de registro"),
        "population": ("num.", "Población total"),
        "gdp": ("num. (USD)", "PIB total"),
        "primary_energy_consumption": ("num. (TWh)", "Consumo energía primaria"),
        "energy_per_capita": ("num. (kWh/hab)", "Consumo per cápita"),
        "electricity_generation": ("num. (TWh)", "Generación eléctrica total"),
        "electricity_demand": ("num. (TWh)", "Demanda eléctrica total"),
        "per_capita_electricity": ("num. (kWh/hab)", "Electricidad per cápita"),
        "carbon_intensity_elec": ("num. (gCO2/kWh)", "Intensidad de carbono eléctrica"),
        "greenhouse_gas_emissions": ("num. (MtCO2eq)", "Emisiones GEI electricidad"),
    }
    if col in especiales:
        return col, *especiales[col]

    fuente = _label_fuente(col)
    if col.endswith("_share_elec"):
        return col, "num. (%)", f"Cuota {fuente} en electricidad"
    if col.endswith("_share_energy"):
        return col, "num. (%)", f"Cuota {fuente} en energía"
    if col.endswith("_electricity"):
        return col, "num. (TWh)", f"Electricidad {fuente}"
    if col.endswith("_production"):
        return col, "num. (TWh)", f"Producción de {fuente}"
    if col.endswith("_consumption"):
        return col, "num. (TWh)", f"Consumo de {fuente}"
    if col.endswith("_per_capita"):
        return col, "num. (kWh/hab)", f"{fuente.capitalize()} per cápita"
    if col.endswith("_change_pct"):
        return col, "num. (%)", f"Variación porcentual de {fuente}"
    if col.endswith("_change_twh"):
        return col, "num. (TWh)", f"Variación absoluta de {fuente}"
    return col, "num.", col.replace("_", " ")


def columnas_prioritarias(df):
    base = (
        "country", "year", "population", "gdp",
        "primary_energy_consumption", "energy_per_capita",
        "electricity_generation", "electricity_demand", "per_capita_electricity",
        "carbon_intensity_elec", "greenhouse_gas_emissions",
    )
    sufijos_energia = (
        "_electricity", "_share_elec", "_production", "_consumption",
        "_change_pct", "_change_twh",
    )
    cols = [
        c for c in df.columns
        if c in base or c.endswith(sufijos_energia)
    ]
    return [c for c in cols if c != "iso_code"]


def variables_disponibles(df):
    return [describir_variable(c) for c in columnas_prioritarias(df)]


def cols_requeridas_viz(df):
    cols = [
        "fossil_share_elec",
        "renewables_share_elec",
        "nuclear_share_elec",
        "carbon_intensity_elec",
        "coal_share_elec",
        "oil_share_elec",
        "gas_share_elec",
    ]
    return [c for c in cols if c in df.columns]


def cols_tecnologias_renovables(df):
    excluidas = {
        "fossil_share_elec", "coal_share_elec", "oil_share_elec",
        "gas_share_elec", "nuclear_share_elec", "renewables_share_elec",
        "low_carbon_share_elec",
    }
    return [
        c for c in df.columns
        if c.endswith("_share_elec") and c not in excluidas
    ]


# Diccionario de traducciones de países al español
TRADUCCIONES_PAISES = {
    "Afghanistan": "Afganistán",
    "Albania": "Albania",
    "Algeria": "Argelia",
    "American Samoa": "Samoa Americana",
    "Angola": "Angola",
    "Antarctica": "Antártida",
    "Antigua and Barbuda": "Antigua y Barbuda",
    "Argentina": "Argentina",
    "Armenia": "Armenia",
    "Aruba": "Aruba",
    "Australia": "Australia",
    "Austria": "Austria",
    "Azerbaijan": "Azerbaiyán",
    "Bahamas": "Bahamas",
    "Bahrain": "Baréin",
    "Bangladesh": "Bangladesh",
    "Barbados": "Barbados",
    "Belarus": "Bielorrusia",
    "Belgium": "Bélgica",
    "Belize": "Belice",
    "Benin": "Benín",
    "Bermuda": "Bermudas",
    "Bhutan": "Bután",
    "Bolivia": "Bolivia",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Botswana": "Botsuana",
    "Brazil": "Brasil",
    "Brunei": "Brunéi",
    "Bulgaria": "Bulgaria",
    "Burkina Faso": "Burkina Faso",
    "Burundi": "Burundi",
    "Cambodia": "Camboya",
    "Cameroon": "Camerún",
    "Canada": "Canadá",
    "Cape Verde": "Cabo Verde",
    "Central African Republic": "República Centroafricana",
    "Chad": "Chad",
    "Chile": "Chile",
    "China": "China",
    "Colombia": "Colombia",
    "Comoros": "Comoras",
    "Congo": "Congo",
    "Costa Rica": "Costa Rica",
    "Croatia": "Croacia",
    "Cuba": "Cuba",
    "Cyprus": "Chipre",
    "Czech Republic": "República Checa",
    "Czechia": "República Checa",
    "Côte d'Ivoire": "Costa de Marfil",
    "Democratic Republic of Congo": "República Democrática del Congo",
    "Denmark": "Dinamarca",
    "Djibouti": "Yibuti",
    "Dominica": "Dominica",
    "Dominican Republic": "República Dominicana",
    "Ecuador": "Ecuador",
    "Egypt": "Egipto",
    "El Salvador": "El Salvador",
    "Equatorial Guinea": "Guinea Ecuatorial",
    "Eritrea": "Eritrea",
    "Estonia": "Estonia",
    "Ethiopia": "Etiopía",
    "Fiji": "Fiyi",
    "Finland": "Finlandia",
    "France": "Francia",
    "Gabon": "Gabón",
    "Gambia": "Gambia",
    "Georgia": "Georgia",
    "Germany": "Alemania",
    "Ghana": "Ghana",
    "Gibraltar": "Gibraltar",
    "Greece": "Grecia",
    "Grenada": "Granada",
    "Guadeloupe": "Guadalupe",
    "Guam": "Guam",
    "Guatemala": "Guatemala",
    "Guinea": "Guinea",
    "Guinea-Bissau": "Guinea-Bissau",
    "Guyana": "Guyana",
    "Haiti": "Haití",
    "Honduras": "Honduras",
    "Hong Kong": "Hong Kong",
    "Hungary": "Hungría",
    "Iceland": "Islandia",
    "India": "India",
    "Indonesia": "Indonesia",
    "Iran": "Irán",
    "Iraq": "Irak",
    "Ireland": "Irlanda",
    "Israel": "Israel",
    "Italy": "Italia",
    "Jamaica": "Jamaica",
    "Japan": "Japón",
    "Jordan": "Jordania",
    "Kazakhstan": "Kazajistán",
    "Kenya": "Kenia",
    "Kiribati": "Kiribati",
    "Kosovo": "Kosovo",
    "Kuwait": "Kuwait",
    "Kyrgyzstan": "Kirguistán",
    "Laos": "Laos",
    "Latvia": "Letonia",
    "Lebanon": "Líbano",
    "Lesotho": "Lesoto",
    "Liberia": "Liberia",
    "Libya": "Libia",
    "Liechtenstein": "Liechtenstein",
    "Lithuania": "Lituania",
    "Luxembourg": "Luxemburgo",
    "Macao": "Macao",
    "Madagascar": "Madagascar",
    "Malawi": "Malaui",
    "Malaysia": "Malasia",
    "Maldives": "Maldivas",
    "Mali": "Mali",
    "Malta": "Malta",
    "Martinique": "Martinica",
    "Mauritania": "Mauritania",
    "Mauritius": "Mauricio",
    "Mexico": "México",
    "Moldova": "Moldavia",
    "Monaco": "Mónaco",
    "Mongolia": "Mongolia",
    "Montenegro": "Montenegro",
    "Morocco": "Marruecos",
    "Mozambique": "Mozambique",
    "Myanmar": "Myanmar",
    "Namibia": "Namibia",
    "Nepal": "Nepal",
    "Netherlands": "Países Bajos",
    "New Zealand": "Nueva Zelanda",
    "Nicaragua": "Nicaragua",
    "Niger": "Níger",
    "Nigeria": "Nigeria",
    "North Korea": "Corea del Norte",
    "North Macedonia": "Macedonia del Norte",
    "Norway": "Noruega",
    "Oman": "Omán",
    "Pakistan": "Pakistán",
    "Palestine": "Palestina",
    "Panama": "Panamá",
    "Papua New Guinea": "Papúa Nueva Guinea",
    "Paraguay": "Paraguay",
    "Peru": "Perú",
    "Philippines": "Filipinas",
    "Poland": "Polonia",
    "Portugal": "Portugal",
    "Puerto Rico": "Puerto Rico",
    "Qatar": "Qatar",
    "Reunion": "Reunión",
    "Romania": "Rumania",
    "Russia": "Rusia",
    "Rwanda": "Ruanda",
    "Saint Kitts and Nevis": "San Cristóbal y Nieves",
    "Saint Lucia": "Santa Lucía",
    "Saint Vincent and the Grenadines": "San Vicente y las Granadinas",
    "Samoa": "Samoa",
    "San Marino": "San Marino",
    "Sao Tome and Principe": "Santo Tomé y Príncipe",
    "Saudi Arabia": "Arabia Saudita",
    "Senegal": "Senegal",
    "Serbia": "Serbia",
    "Seychelles": "Seychelles",
    "Sierra Leone": "Sierra Leona",
    "Singapore": "Singapur",
    "Slovakia": "Eslovaquia",
    "Slovenia": "Eslovenia",
    "Solomon Islands": "Islas Salomón",
    "Somalia": "Somalia",
    "South Africa": "Sudáfrica",
    "South Korea": "Corea del Sur",
    "South Sudan": "Sudán del Sur",
    "Spain": "España",
    "Sri Lanka": "Sri Lanka",
    "Sudan": "Sudán",
    "Suriname": "Surinam",
    "Sweden": "Suecia",
    "Switzerland": "Suiza",
    "Syria": "Siria",
    "Taiwan": "Taiwán",
    "Tajikistan": "Tayikistán",
    "Tanzania": "Tanzania",
    "Thailand": "Tailandia",
    "Timor-Leste": "Timor Oriental",
    "Togo": "Togo",
    "Tonga": "Tonga",
    "Trinidad and Tobago": "Trinidad y Tobago",
    "Tunisia": "Túnez",
    "Turkey": "Turquía",
    "Turkmenistan": "Turkmenistán",
    "Turks and Caicos Islands": "Islas Turcas y Caicos",
    "Uganda": "Uganda",
    "Ukraine": "Ucrania",
    "United Arab Emirates": "Emiratos Árabes Unidos",
    "United Kingdom": "Reino Unido",
    "United States": "Estados Unidos",
    "Uruguay": "Uruguay",
    "Uzbekistan": "Uzbekistán",
    "Vanuatu": "Vanuatu",
    "Vatican City": "Ciudad del Vaticano",
    "Venezuela": "Venezuela",
    "Vietnam": "Vietnam",
    "Virgin Islands": "Islas Vírgenes",
    "West Bank": "Cisjordania",
    "Western Sahara": "Sahara Occidental",
    "Yemen": "Yemen",
    "Zambia": "Zambia",
    "Zimbabwe": "Zimbabue",
}


def labels_paises(df):
    paises = sorted(df["country"].dropna().unique())
    return {pais: TRADUCCIONES_PAISES.get(pais, pais) for pais in paises}


def paises_con_datos_viz(df, n=N_PAISES_VIZ, priorizar_ref=True):
    requeridas = cols_requeridas_viz(df)
    if len(requeridas) < 7:
        return []
    sub = df.dropna(subset=requeridas)
    cobertura = sub.groupby("country").agg(
        n_years=("year", "nunique"),
        year_max=("year", "max"),
    ).reset_index()
    pop = (df.dropna(subset=["population"]).sort_values("year")
             .groupby("country").tail(1)[["country", "population"]])
    ranked = (cobertura.merge(pop, on="country", how="left")
              .fillna({"population": 0})
              .query("n_years >= 5")
              .sort_values(["population", "n_years"], ascending=[False, False]))
    paises = ranked["country"].head(n).tolist()
    if priorizar_ref and PAIS_REF_PREFERIDO in ranked["country"].values:
        paises = [p for p in paises if p != PAIS_REF_PREFERIDO]
        paises.insert(0, PAIS_REF_PREFERIDO)
        paises = paises[:n]
    return paises


def paises_comparativa(df, candidatos=None, n=N_PAISES_COMPARATIVA):
    requeridas = cols_requeridas_viz(df)
    sub = df.dropna(subset=requeridas)
    if candidatos is not None:
        sub = sub[sub["country"].isin(candidatos)]
    candidatos = []
    for pais, g in sub.groupby("country"):
        g = g.sort_values("year")
        if len(g) < 5:
            continue
        r0, r1 = g.iloc[0], g.iloc[-1]
        candidatos.append({
            "country": pais,
            "delta_renew": float(r1["renewables_share_elec"] - r0["renewables_share_elec"]),
        })
    if not candidatos:
        return []
    ranked = pd.DataFrame(candidatos).sort_values("delta_renew", ascending=False)
    return ranked["country"].head(n).tolist()


def _corr(x, y):
    x = pd.Series(x, dtype="float64")
    y = pd.Series(y, dtype="float64")
    mask = x.notnull() & y.notnull()
    if mask.sum() < 3:
        return None
    return round(float(x[mask].corr(y[mask])), 3)


def calcular_scatter_economia(df, labels):
    requeridas = [
        "country", "year", "population", "gdp", "carbon_intensity_elec",
        "renewables_share_elec", "nuclear_share_elec", "fossil_share_elec",
    ]
    if any(c not in df.columns for c in requeridas):
        return {"year": None, "years": [], "por_year": {}, "n_paises": 0, "corr_gdp_ci": None, "corr_low_carbon_ci": None, "puntos": []}

    sub = df[requeridas].copy()
    sub["gdp_per_capita"] = sub["gdp"] / sub["population"]
    sub = sub.dropna(subset=["gdp_per_capita", "population", "carbon_intensity_elec"])
    sub = sub[(sub["gdp_per_capita"] > 0) & (sub["population"] > 0)]
    if sub.empty:
        return {"year": None, "years": [], "por_year": {}, "n_paises": 0, "corr_gdp_ci": None, "corr_low_carbon_ci": None, "puntos": []}

    cobertura = sub.groupby("year")["country"].nunique()
    years_ok = cobertura[cobertura >= MIN_PAISES_SCATTER]
    years = [int(y) for y in (years_ok.index.tolist() if not years_ok.empty else [cobertura.idxmax()])]

    def pack_year(year):
        year_df = sub[sub["year"] == year].copy()
        year_df["low_carbon_share"] = year_df["renewables_share_elec"].fillna(0) + year_df["nuclear_share_elec"].fillna(0)
        year_df["log_gdp_pc"] = np.log10(year_df["gdp_per_capita"])
        year_df["dominant_group"] = np.select(
            [
                year_df["fossil_share_elec"] >= 60,
                year_df["renewables_share_elec"] >= year_df["nuclear_share_elec"],
            ],
            ["Fósil dominante", "Renovable dominante"],
            default="Nuclear relevante",
        )

        puntos = []
        for _, row in year_df.sort_values("population", ascending=False).iterrows():
            puntos.append(_clean({
                "country": row["country"],
                "label": labels.get(row["country"], row["country"]),
                "year": int(row["year"]),
                "gdp_per_capita": round(float(row["gdp_per_capita"]), 1),
                "population": int(row["population"]),
                "carbon_intensity": round(float(row["carbon_intensity_elec"]), 1),
                "renewables_share": round(float(row["renewables_share_elec"]), 1),
                "nuclear_share": round(float(row["nuclear_share_elec"]), 1),
                "fossil_share": round(float(row["fossil_share_elec"]), 1),
                "low_carbon_share": round(float(row["low_carbon_share"]), 1),
                "dominant_group": row["dominant_group"],
            }))

        return _clean({
            "year": int(year),
            "n_paises": len(puntos),
            "corr_gdp_ci": _corr(year_df["log_gdp_pc"], year_df["carbon_intensity_elec"]),
            "corr_low_carbon_ci": _corr(year_df["low_carbon_share"], year_df["carbon_intensity_elec"]),
            "puntos": puntos,
        })

    default_year = max(years)
    por_year = {str(y): pack_year(y) for y in years}
    years_meta = [
        {
            "year": y,
            "n_paises": por_year[str(y)]["n_paises"],
            "corr_gdp_ci": por_year[str(y)]["corr_gdp_ci"],
            "corr_low_carbon_ci": por_year[str(y)]["corr_low_carbon_ci"],
        }
        for y in years
    ]
    return _clean({
        **por_year[str(default_year)],
        "years": years_meta,
        "por_year": por_year,
    })


def calcular_transicion_renovable(df, labels, cols_renovables, year0=None, year1=KPI_YEAR, n=N_PAISES_TRANSICION):
    requeridas = ["country", "year", "renewables_share_elec", "carbon_intensity_elec"]
    if any(c not in df.columns for c in requeridas):
        return {"year0": None, "year1": None, "tecnologias": [], "paises": []}

    tech_labels = {
        "hydro": "Hidro",
        "wind": "Eólica",
        "solar": "Solar",
        "biofuel": "Bioenergía",
        "other_renewables": "Otras",
    }
    tech_order = ["hydro", "wind", "solar", "biofuel"]
    available = {c.replace("_share_elec", "") for c in cols_renovables}
    tech_keys = [t for t in tech_order if t in available]
    if "other_renewables" in available:
        tech_keys.append("other_renewables")

    rows = []
    year0 = int(year0 if year0 is not None else df["year"].min())
    for pais, g in df.dropna(subset=requeridas).groupby("country"):
        g = g.sort_values("year")
        if len(g) < 5:
            continue
        r0_match = g[g["year"] == year0]
        r1_match = g[g["year"] == year1]
        if r0_match.empty or r1_match.empty:
            continue
        r0, r1 = r0_match.iloc[0], r1_match.iloc[0]
        delta = float(r1["renewables_share_elec"] - r0["renewables_share_elec"])
        componentes = {}
        suma_base = 0.0
        for t in tech_keys:
            if t == "other_renewables":
                continue
            col = f"{t}_share_elec"
            val = float(r1[col]) if col in r1.index and pd.notnull(r1[col]) else 0.0
            componentes[t] = round(val, 1)
            suma_base += val
        if "other_renewables" in tech_keys:
            componentes["other_renewables"] = round(max(float(r1["renewables_share_elec"]) - suma_base, 0), 1)
        rows.append(_clean({
            "country": pais,
            "label": labels.get(pais, pais),
            "year0": int(r0["year"]),
            "year1": int(r1["year"]),
            "renew_yr0": round(float(r0["renewables_share_elec"]), 1),
            "renew_yr1": round(float(r1["renewables_share_elec"]), 1),
            "delta_renew": round(delta, 1),
            "ci_yr0": round(float(r0["carbon_intensity_elec"]), 1),
            "ci_yr1": round(float(r1["carbon_intensity_elec"]), 1),
            "delta_ci": round(float(r1["carbon_intensity_elec"] - r0["carbon_intensity_elec"]), 1),
            "componentes": componentes,
        }))

    rows = sorted(rows, key=lambda d: d["delta_renew"], reverse=True)
    tecnologias = [{"key": t, "label": tech_labels.get(t, t)} for t in tech_keys]
    return _clean({
        "year0": rows[0]["year0"] if rows else None,
        "year1": rows[0]["year1"] if rows else None,
        "default_n": min(n, len(rows)),
        "n_total": len(rows),
        "tecnologias": tecnologias,
        "paises": rows,
    })


def _fmt_pct(v):
    return f"{round(float(v))}%"


def _fmt_ci(v):
    return f"{round(float(v))} gCO2/kWh"


def _tendencia(delta):
    return "subió" if delta >= 0 else "bajó"


def generar_hallazgo(pais, rows):
    if not rows:
        return ""

    r0, r1 = rows[0], rows[-1]
    label = pais
    y0, y1 = r0["year"], r1["year"]

    fossil_delta = r1["fossil"] - r0["fossil"]
    renew_delta = r1["renewables"] - r0["renewables"]
    ci_delta = r1["ci"] - r0["ci"]
    ci_pct = (ci_delta / r0["ci"] * 100) if r0["ci"] else None

    fuentes_finales = {
        "carbón": r1["coal"],
        "petróleo": r1["oil"],
        "gas": r1["gas"],
        "nuclear": r1["nuclear"],
        "renovables": r1["renewables"],
    }
    fuente_top, valor_top = max(fuentes_finales.items(), key=lambda kv: kv[1])

    partes = [
        f"{label}: la cuota fósil {_tendencia(fossil_delta)} de {_fmt_pct(r0['fossil'])} ({y0}) "
        f"a {_fmt_pct(r1['fossil'])} ({y1}), mientras la cuota renovable {_tendencia(renew_delta)} "
        f"de {_fmt_pct(r0['renewables'])} a {_fmt_pct(r1['renewables'])}.",
        f"En {y1}, la fuente dominante es {fuente_top} ({_fmt_pct(valor_top)}).",
    ]
    if ci_pct is not None:
        partes.append(
            f"La intensidad de carbono {_tendencia(ci_delta)} un {abs(round(ci_pct))}%: "
            f"de {_fmt_ci(r0['ci'])} a {_fmt_ci(r1['ci'])}."
        )
    return " ".join(partes)


def cargar(ruta=None):
    ruta = Path(ruta) if ruta else RUTA_LOCAL
    if ruta.exists():
        print(f"  Cargando: {ruta}")
        df = pd.read_csv(ruta, low_memory=False)
    else:
        print(f"  Descargando desde GitHub...")
        df = pd.read_csv(URL_DATOS)
    print(f"  {df.shape[0]:,} filas × {df.shape[1]} columnas")
    return df


def limpiar(df, variables_info):
    cols = ["iso_code"] + [v[0] for v in variables_info if v[0] in df.columns]
    df_c = df[[c for c in cols if c in df.columns]].copy()
    n0 = len(df_c)

    # OWID deja iso_code vacío en regiones agregadas (World, Europe, Asia, ASEAN...).
    # No se usan para detectar países reales ni para alimentar visualizaciones.
    df_c = df_c[df_c["iso_code"].notnull()]
    n_iso = n0 - len(df_c)

    n2 = len(df_c)
    mask = df_c["year"] >= YEAR_MIN
    if YEAR_MAX: mask &= df_c["year"] <= YEAR_MAX
    df_c = df_c[mask]
    n_yr = n2 - len(df_c)

    if "iso_code" in df_c.columns:
        df_c = df_c.drop(columns=["iso_code"])

    stats = {
        "n_original":    n0,   "n_sin_iso":     n_iso,
        "n_sin_year":    n_yr, "n_limpio":      len(df_c),
        "cols_limpio":   df_c.shape[1],
        "paises":        int(df_c["country"].nunique()),
        "year_min_real": int(df_c["year"].min()),
        "year_max_real": int(df_c["year"].max()),
    }
    print(f"  -{n_iso:,} sin iso_code, -{n_yr:,} año<{YEAR_MIN}"
          f" → {len(df_c):,} filas, {stats['paises']} países")
    return df_c, stats


def calcular(df_raw, df_c, stats, variables_info):
    yr0, yr1 = stats["year_min_real"], KPI_YEAR
    paises_labels = labels_paises(df_c)
    paises_viz = paises_con_datos_viz(df_c)
    paises_tendencia = paises_con_datos_viz(
        df_c, n=N_PAISES_TENDENCIA, priorizar_ref=False
    )
    paises_comp = paises_comparativa(df_c, candidatos=paises_viz)
    pais_ref = (
        PAIS_REF_PREFERIDO if PAIS_REF_PREFERIDO in paises_viz
        else (paises_viz[0] if paises_viz else PAIS_REF_PREFERIDO)
    )
    pais_ref_label = paises_labels.get(pais_ref, pais_ref)
    cols_main_chart = cols_requeridas_viz(df_c)
    cols_renovables = cols_tecnologias_renovables(df_c)

    m = CTX_META = {
        "nombre_dataset":     "Energy (Our World in Data)",
        "fuente":             "Our World in Data / GitHub",
        "url":                "https://github.com/owid/energy-data",
        "periodo_viz":        f"{yr0}-{stats['year_max_real']}",
        "year_min":           yr0, "year_max": stats["year_max_real"],
        "pais_ref":           pais_ref, "pais_ref_label": pais_ref_label,
        "kpi_year":           yr1,
        "filas_original":     int(df_raw.shape[0]),
        "cols_original":      int(df_raw.shape[1]),
        "entidades_original": int(df_raw["country"].nunique()),
        "filas_limpias":      stats["n_limpio"],
        "cols_limpias":       stats["cols_limpio"],
        "paises_limpios":     stats["paises"],
        "n_sin_iso":          stats["n_sin_iso"],
        "n_sin_year":         stats["n_sin_year"],
        "timestamp":          datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # KPIs
    r1 = df_c[(df_c["country"]==pais_ref)&(df_c["year"]==yr1)]
    r0 = df_c[(df_c["country"]==pais_ref)&(df_c["year"]==yr0)]
    def g(row, col, rnd=1):
        if row.empty or col not in row.columns: return None
        v = row[col].iloc[0]
        return round(float(v), rnd) if pd.notnull(v) else None
    fossil = g(r1,"fossil_share_elec"); renew = g(r1,"renewables_share_elec")
    ci1 = g(r1,"carbon_intensity_elec",0); ci0 = g(r0,"carbon_intensity_elec",0)
    ci_pct = round((ci1-ci0)/ci0*100,0) if ci1 and ci0 else None
    kpis = _clean([
        {"valor":f"{fossil:g}" if fossil is not None else "—","unidad":"%",
         "etiqueta":f"Cuota fósil {pais_ref_label} {yr1}","color":"danger"},
        {"valor":f"{renew:g}"  if renew  is not None else "—","unidad":"%",
         "etiqueta":f"Cuota renovables {pais_ref_label} {yr1}","color":"accent"},
        {"valor":f"{int(ci1):,}" if ci1 is not None else "—","unidad":" gCO₂/kWh",
         "etiqueta":f"Intensidad carbono {pais_ref_label} {yr1}","color":"warn"},
        {"valor":f"{int(ci_pct):+}" if ci_pct is not None else "—","unidad":"%",
         "etiqueta":f"Variación intensidad {pais_ref_label} {yr0}–{yr1}","color":"blue"},
    ])

    # Pasos de preprocesado (con cifras reales)
    yr_rng = f"year ≥ {YEAR_MIN}" + (f" y ≤ {YEAR_MAX}" if YEAR_MAX else "")
    pasos = [
        {"texto": f"Carga desde URL de GitHub o fichero local <code>owid-energy-data.csv</code>."},
        {"texto": f"Detección dinámica de variables: columnas base más patrones <code>*_electricity</code>, <code>*_share_elec</code>, <code>*_production</code>, <code>*_consumption</code>, <code>*_change_pct</code> y <code>*_change_twh</code>. Resultado: <strong>{len(variables_info)} variables disponibles</strong>."},
        {"texto": f"Eliminación de <strong class=\'danger\'>{stats['n_sin_iso']:,} filas sin <code>iso_code</code></strong>; se descartan agregados como &ldquo;World&rdquo;, &ldquo;Europe&rdquo;, &ldquo;Asia&rdquo; o &ldquo;ASEAN&rdquo; y se conservan países reales."},
        {"texto": f"Filtro temporal: solo <code>{yr_rng}</code>, eliminando <strong class=\'danger\'>{stats['n_sin_year']:,} registros históricos</strong> con cobertura insuficiente."},
        {"texto": f"Selección dinámica para visualización: <strong>{len(paises_viz)} países</strong> con datos completos en cuotas fósil/renovable/nuclear, carbón/petróleo/gas e intensidad de carbono; país KPI: <code>{pais_ref}</code>."},
        {"texto": f"Construcción de vistas derivadas: mediana global con <strong>{len(paises_tendencia)} países</strong>, ranking renovable con <strong>{len(paises_comp)} países</strong>, hallazgos automáticos y series temporales por país."},
        {"texto": f"Dataset final: <strong class=\'accent\'>{stats['n_limpio']:,} filas × {stats['cols_limpio']} columnas</strong> · {stats['paises']} países reales · {yr0}–{stats['year_max_real']}."},
    ]

    # Tendencia global
    df_m = df_c[df_c["country"].isin(paises_tendencia)]
    tendencia = _clean(df_m.groupby("year").agg(
        med_fossil=("fossil_share_elec","median"),
        med_renew=("renewables_share_elec","median"),
        med_nuclear=("nuclear_share_elec","median"),
        med_ci=("carbon_intensity_elec","median"),
        n_paises=("country","count"),
    ).reset_index().round(2).to_dict(orient="records"))

    # Cobertura temporal
    cobertura = _clean(df_c.groupby("year")["fossil_share_elec"]
        .apply(lambda s: int(s.notnull().sum()))
        .reset_index(name="countries_with_data").to_dict(orient="records"))

    # Nulos antes vs después
    check = [v[0] for v in variables_info
             if v[0] in df_raw.columns and v[0] in df_c.columns
             and v[0] not in ("country","year")][:10]
    nulos = [{"variable":v,
              "antes":  round(df_raw[v].isnull().sum()/len(df_raw)*100,1),
              "despues":round(df_c[v].isnull().sum()/len(df_c)*100,1),
              "mejora": round((df_raw[v].isnull().sum()/len(df_raw) -
                               df_c[v].isnull().sum()/len(df_c))*100,1)}
             for v in check]

    # Comparativa de transición renovable
    comp_eur = []
    for pais in paises_comp:
        r_yr0 = df_c[(df_c["country"]==pais)&(df_c["year"]==yr0)]
        r_yr1 = df_c[(df_c["country"]==pais)&(df_c["year"]==yr1)]
        if r_yr0.empty or r_yr1.empty: continue
        def gv(row,col):
            v = row[col].iloc[0]; return round(float(v),1) if pd.notnull(v) else None
        comp_eur.append(_clean({
            "country":pais, "label":paises_labels.get(pais,pais),
            "renew_yr0":gv(r_yr0,"renewables_share_elec"),
            "renew_yr1":gv(r_yr1,"renewables_share_elec"),
            "ci_yr0":   gv(r_yr0,"carbon_intensity_elec"),
            "ci_yr1":   gv(r_yr1,"carbon_intensity_elec"),
            "year0":yr0, "year1":yr1,
        }))

    scatter_economia = calcular_scatter_economia(df_c, paises_labels)
    transicion_renovable = calcular_transicion_renovable(
        df_c, paises_labels, cols_renovables, year0=yr0, year1=yr1
    )
    pasos[5]["texto"] = (
        f"Construcción de vistas derivadas: mediana global con <strong>{len(paises_tendencia)} países</strong>, "
        f"scatter economía-carbono con <strong>{len(scatter_economia.get('years', []))} años seleccionables</strong> "
        f"y ranking renovable con <strong>{transicion_renovable.get('n_total', 0)} países comparables</strong>."
    )

    # Datos visualización principal
    viz = {}
    hallazgos = {}
    paises_viz_validos = []
    for pais in paises_viz:
        sub = df_c[df_c["country"]==pais].dropna(subset=cols_main_chart)
        if sub.empty: continue
        paises_viz_validos.append(pais)
        rows = []
        for _, row in sub.iterrows():
            def gv2(col,rnd=2):
                v=row.get(col); return round(float(v),rnd) if pd.notnull(v) else 0
            rows.append(_clean({
                "year":      int(row["year"]),
                "fossil":    gv2("fossil_share_elec"),
                "nuclear":   gv2("nuclear_share_elec"),
                "renewables":gv2("renewables_share_elec"),
                "coal":      gv2("coal_share_elec"),
                "oil":       gv2("oil_share_elec"),
                "gas":       gv2("gas_share_elec"),
                **{c.replace("_share_elec", ""): gv2(c) for c in cols_renovables},
                "ci":        round(float(row["carbon_intensity_elec"]),1),
            }))
        viz[pais] = rows
        hallazgos[pais] = generar_hallazgo(pais, rows)

    return {
        "meta":                m,
        "kpis":                kpis,
        "preprocesado_pasos":  pasos,
        "tendencia_global":    tendencia,
        "cobertura_anual":     cobertura,
        "nulos_variables":     nulos,
        "comparativa_europea": comp_eur,
        "scatter_economia_carbono": scatter_economia,
        "transicion_renovable": transicion_renovable,
        "variables":           [{"nombre":v[0],"tipo":v[1],"descripcion":v[2]}
                                 for v in variables_info],
        "paises_viz":          paises_viz_validos,
        "paises_labels":       paises_labels,
        "hallazgos":           hallazgos,
        "datos_viz":           viz,
    }


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3 · PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════

def main(ruta_csv=None, ruta_json=None):
    ruta_json = Path(ruta_json) if ruta_json else RUTA_SALIDA
    print("\n[1/3] Cargando dataset...")
    df_raw = cargar(ruta_csv)
    variables_info = variables_disponibles(df_raw)
    print(f"  {len(variables_info)} variables priorizadas disponibles")
    print("[2/3] Limpiando y filtrando...")
    df_c, stats = limpiar(df_raw, variables_info)
    print("[3/3] Calculando métricas...")
    data = calcular(df_raw, df_c, stats, variables_info)
    with open(ruta_json,"w",encoding="utf-8") as f:
        json.dump(data, f, separators=(",",":"), ensure_ascii=False)
    print(f"\n✓ Generado: {ruta_json}  ({ruta_json.stat().st_size/1024:.0f} kB)")
    print("  Abre index.html con Live Server para ver los cambios.")


if __name__ == "__main__":
    main(
        ruta_csv  = Path(sys.argv[1]) if len(sys.argv)>1 else None,
        ruta_json = Path(sys.argv[2]) if len(sys.argv)>2 else None,
    )
