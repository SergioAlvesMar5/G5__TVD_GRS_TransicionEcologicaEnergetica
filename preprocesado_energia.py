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

# ── Variables seleccionadas ─────────────────────────────────────
# Añadir/quitar tuplas actualiza la tabla de variables y la de nulos.
# Formato: (nombre_col_csv, tipo_ui, descripción_ui)
VARIABLES_INFO = [
    ("country",                    "cat.",             "País o territorio"),
    ("year",                       "num. (temporal)",  "Año de registro"),
    ("population",                 "num.",             "Población total"),
    ("gdp",                        "num. (USD)",       "PIB total"),
    ("primary_energy_consumption", "num. (TWh)",       "Consumo energía primaria"),
    ("energy_per_capita",          "num. (kWh/hab)",   "Consumo per cápita"),
    ("fossil_electricity",         "num. (TWh)",       "Electricidad fósil total"),
    ("fossil_share_elec",          "num. (%)",         "Cuota fósil en electricidad"),
    ("coal_electricity",           "num. (TWh)",       "Electricidad de carbón"),
    ("coal_share_elec",            "num. (%)",         "Cuota carbón"),
    ("oil_electricity",            "num. (TWh)",       "Electricidad de petróleo"),
    ("oil_share_elec",             "num. (%)",         "Cuota petróleo"),
    ("gas_electricity",            "num. (TWh)",       "Electricidad de gas"),
    ("gas_share_elec",             "num. (%)",         "Cuota gas"),
    ("low_carbon_electricity",     "num. (TWh)",       "Electricidad bajo carbono"),
    ("low_carbon_share_elec",      "num. (%)",         "Cuota bajo carbono (nuc+renov)"),
    ("nuclear_electricity",        "num. (TWh)",       "Electricidad nuclear"),
    ("nuclear_share_elec",         "num. (%)",         "Cuota nuclear"),
    ("renewables_electricity",     "num. (TWh)",       "Electricidad renovable"),
    ("renewables_share_elec",      "num. (%)",         "Cuota renovables"),
    ("coal_production",            "num. (TWh)",       "Producción de carbón"),
    ("oil_production",             "num. (TWh)",       "Producción de petróleo"),
    ("gas_production",             "num. (TWh)",       "Producción de gas"),
    ("carbon_intensity_elec",      "num. (gCO2/kWh)",  "Intensidad de carbono eléctrica"),
    ("greenhouse_gas_emissions",   "num. (MtCO2eq)",   "Emisiones GEI electricidad"),
]

# ── País de referencia para los 4 KPIs del encabezado ──────────
PAIS_REF       = "Spain"
PAIS_REF_LABEL = "España"
KPI_YEAR       = 2024         # año "actual" para los KPIs

# ── Países en el selector del gráfico principal ─────────────────
# Añade o quita entradas; el selector se actualiza automáticamente.
PAISES_VIZ = [
    "Spain", "Germany", "France", "United Kingdom", "United States",
    "China", "India", "Brazil", "Japan", "Portugal", "Italy", "Australia",
    "Norway", "Sweden", "Canada", "South Korea", "Mexico", "Argentina",
    "South Africa", "Poland",
]

# Etiquetas en español para cada país
PAISES_LABELS = {
    "Spain":"España","Germany":"Alemania","France":"Francia",
    "United Kingdom":"Reino Unido","United States":"EE.UU.",
    "China":"China","India":"India","Brazil":"Brasil","Japan":"Japón",
    "Portugal":"Portugal","Italy":"Italia","Australia":"Australia",
    "Norway":"Noruega","Sweden":"Suecia","Canada":"Canadá",
    "South Korea":"Corea del Sur","Mexico":"México","Argentina":"Argentina",
    "South Africa":"Sudáfrica","Poland":"Polonia",
}

# ── Países para la comparativa europea ─────────────────────────
PAISES_EUROPA = [
    "Spain","Germany","France","United Kingdom",
    "Portugal","Poland","Italy","Sweden","Norway",
]

# ── Países para la tendencia global (medianas por año) ──────────
PAISES_GLOBALES = [
    "United States","China","India","Germany","Japan","France",
    "United Kingdom","Brazil","Canada","Australia","Spain","Italy",
    "South Korea","Mexico","Russia","Indonesia","Turkey","Poland",
    "Saudi Arabia","Argentina",
]

# ── Texto de hallazgo por país (aparece bajo el gráfico principal)
HALLAZGOS = {
    "Spain":
        "España redujo su cuota fósil del 56% (2000) al 23% (2024) mientras las renovables "
        "escalaban del 16% al 57%. La intensidad de carbono cayó un 69%: de 471 a 146 gCO2/kWh.",
    "Germany":
        "Alemania abandonó la nuclear (0% en 2024 tras Fukushima) y amplió las renovables hasta el 59%. "
        "El carbón cayó del 52% al 21% en 25 años.",
    "France":
        "Francia mantiene una matriz ultrabaja en carbono gracias a la nuclear (~68%). "
        "Con 40 gCO2/kWh en 2024, es una de las electricidades más limpias del mundo.",
    "United Kingdom":
        "El RU eliminó casi por completo el carbón (31% a 1%) y alcanzó el 51% de renovables en 2024, "
        "reduciendo la intensidad de 522 a 217 gCO2/kWh.",
    "China":
        "China sigue dominada por el carbón (58% en 2024), aunque las renovables crecen del 17% al 34%. "
        "La intensidad de 555 gCO2/kWh sigue siendo muy elevada.",
    "India":
        "India tiene un mix dominado por el carbón (75%) con escasa variación. "
        "Su intensidad supera los 700 gCO2/kWh, la mayor de los grandes emisores.",
    "Poland":
        "Polonia: 54% de carbón en 2024 frente al 95% de 2000. "
        "Las renovables pasaron del 2% al 31%. La transición es lenta pero visible.",
    "Norway":
        "Noruega genera el 99% con renovables (principalmente hidroeléctrica), "
        "con ~30 gCO2/kWh, la intensidad más baja del dataset.",
    "Sweden":
        "Suecia combina nuclear (~29%) y renovables (~69%), logrando ~35 gCO2/kWh "
        "sin abandonar el átomo.",
    "United States":
        "EE.UU. sustituyó carbón por gas (30% a 43%), con renovables aún en el 24%. "
        "Intensidad: 608 a 384 gCO2/kWh — transición más lenta que en Europa.",
    "Brazil":
        "Brasil parte de una base renovable (89% en 2000 por hidroeléctrica). "
        "Las variaciones interanuales reflejan la dependencia de la pluviometría.",
    "Japan":
        "Tras Fukushima (2011) Japón desconectó toda su nuclear, disparando los fósiles al 88%. "
        "La lenta reactivación nuclear ha reducido la dependencia desde entonces.",
    "Portugal":
        "Portugal alcanzó el 85% de renovables en 2024, cerrando toda generación de carbón. "
        "Intensidad: 111 gCO2/kWh, referente europeo.",
    "Italy":
        "Italia: renovables del 18% al 50%, aunque el gas sigue dominando (47% en 2024).",
    "Australia":
        "Australia mantiene una matriz intensiva en carbón (45%), pero las renovables "
        "crecen del 8% (2000) al 35% (2024).",
    "Canada":
        "Canadá combina hidroeléctrica (~40%) y nuclear (~13%). "
        "Intensidad moderada: 185 gCO2/kWh. El carbón cayó del 19% al 4%.",
    "South Korea":
        "Corea del Sur: carbón 30% + gas 28%, renovables marginales (10%). 415 gCO2/kWh.",
    "Mexico":
        "México: gas domina (62%), renovables crecen (21%). Intensidad > 480 gCO2/kWh.",
    "Argentina":
        "Argentina: 65% gas + 34% renovables. Intensidad ~345 gCO2/kWh.",
    "South Africa":
        "Sudáfrica: 83% carbón en 2024, renovables apenas 12%. Intensidad: 717 gCO2/kWh.",
}


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


def limpiar(df):
    cols = ["iso_code"] + [v[0] for v in VARIABLES_INFO if v[0] in df.columns]
    df_c = df[[c for c in cols if c in df.columns]].copy()
    n0 = len(df_c)

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


def calcular(df_raw, df_c, stats):
    yr0, yr1 = stats["year_min_real"], KPI_YEAR
    m = CTX_META = {
        "nombre_dataset":     "Energy (Our World in Data)",
        "fuente":             "Our World in Data / GitHub",
        "url":                "https://github.com/owid/energy-data",
        "periodo_viz":        f"{yr0}-{stats['year_max_real']}",
        "year_min":           yr0, "year_max": stats["year_max_real"],
        "pais_ref":           PAIS_REF, "pais_ref_label": PAIS_REF_LABEL,
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
    r1 = df_c[(df_c["country"]==PAIS_REF)&(df_c["year"]==yr1)]
    r0 = df_c[(df_c["country"]==PAIS_REF)&(df_c["year"]==yr0)]
    def g(row, col, rnd=1):
        if row.empty or col not in row.columns: return None
        v = row[col].iloc[0]
        return round(float(v), rnd) if pd.notnull(v) else None
    fossil = g(r1,"fossil_share_elec"); renew = g(r1,"renewables_share_elec")
    ci1 = g(r1,"carbon_intensity_elec",0); ci0 = g(r0,"carbon_intensity_elec",0)
    ci_pct = round((ci1-ci0)/ci0*100,0) if ci1 and ci0 else None
    kpis = _clean([
        {"valor":f"{fossil:g}" if fossil is not None else "—","unidad":"%",
         "etiqueta":f"Cuota fósil {PAIS_REF_LABEL} {yr1}","color":"danger"},
        {"valor":f"{renew:g}"  if renew  is not None else "—","unidad":"%",
         "etiqueta":f"Cuota renovables {PAIS_REF_LABEL} {yr1}","color":"accent"},
        {"valor":f"{int(ci1):,}" if ci1 is not None else "—","unidad":" gCO₂/kWh",
         "etiqueta":f"Intensidad carbono {PAIS_REF_LABEL} {yr1}","color":"warn"},
        {"valor":f"{int(ci_pct):+}" if ci_pct is not None else "—","unidad":"%",
         "etiqueta":f"Variación intensidad {PAIS_REF_LABEL} {yr0}–{yr1}","color":"blue"},
    ])

    # Pasos de preprocesado (con cifras reales)
    yr_rng = f"year ≥ {YEAR_MIN}" + (f" y ≤ {YEAR_MAX}" if YEAR_MAX else "")
    pasos = [
        {"texto": f"Carga desde URL de GitHub o fichero local <code>owid-energy-data.csv</code>."},
        {"texto": f"Selección de <strong>{stats['cols_limpio']} variables clave</strong>: mix eléctrico, producción fósil, emisiones, PIB y población."},
        {"texto": f"Eliminación de <strong class=\'danger\'>{stats['n_sin_iso']:,} filas sin <code>iso_code</code></strong>: regiones agregadas como &ldquo;Europe&rdquo;, &ldquo;World&rdquo;, &ldquo;Asia&rdquo;..."},
        {"texto": f"Filtro temporal: solo <code>{yr_rng}</code>, eliminando <strong class=\'danger\'>{stats['n_sin_year']:,} registros históricos</strong> con cobertura insuficiente."},
        {"texto": f"Dataset limpio: <strong class=\'accent\'>{stats['n_limpio']:,} filas × {stats['cols_limpio']} columnas</strong> · {stats['paises']} países reales · {yr0}–{stats['year_max_real']}."},
    ]

    # Tendencia global
    df_m = df_c[df_c["country"].isin(PAISES_GLOBALES)]
    tendencia = _clean(df_m.groupby("year").agg(
        med_fossil=("fossil_share_elec","median"),
        med_renew=("renewables_share_elec","median"),
        med_nuclear=("nuclear_share_elec","median"),
        med_ci=("carbon_intensity_elec","median"),
        n_paises=("country","count"),
    ).reset_index().round(2).to_dict(orient="records"))

    # Cobertura temporal
    cobertura = _clean(df_c.groupby("year")
        .apply(lambda g: int(g["fossil_share_elec"].notnull().sum()))
        .reset_index(name="countries_with_data").to_dict(orient="records"))

    # Nulos antes vs después
    check = [v[0] for v in VARIABLES_INFO
             if v[0] in df_raw.columns and v[0] in df_c.columns
             and v[0] not in ("country","year")][:10]
    nulos = [{"variable":v,
              "antes":  round(df_raw[v].isnull().sum()/len(df_raw)*100,1),
              "despues":round(df_c[v].isnull().sum()/len(df_c)*100,1),
              "mejora": round((df_raw[v].isnull().sum()/len(df_raw) -
                               df_c[v].isnull().sum()/len(df_c))*100,1)}
             for v in check]

    # Comparativa europea
    comp_eur = []
    for pais in PAISES_EUROPA:
        r_yr0 = df_c[(df_c["country"]==pais)&(df_c["year"]==yr0)]
        r_yr1 = df_c[(df_c["country"]==pais)&(df_c["year"]==yr1)]
        if r_yr0.empty or r_yr1.empty: continue
        def gv(row,col):
            v = row[col].iloc[0]; return round(float(v),1) if pd.notnull(v) else None
        comp_eur.append(_clean({
            "country":pais, "label":PAISES_LABELS.get(pais,pais),
            "renew_yr0":gv(r_yr0,"renewables_share_elec"),
            "renew_yr1":gv(r_yr1,"renewables_share_elec"),
            "ci_yr0":   gv(r_yr0,"carbon_intensity_elec"),
            "ci_yr1":   gv(r_yr1,"carbon_intensity_elec"),
            "year0":yr0, "year1":yr1,
        }))

    # Datos visualización principal
    viz = {}
    for pais in PAISES_VIZ:
        sub = df_c[df_c["country"]==pais].dropna(
            subset=["fossil_share_elec","renewables_share_elec","nuclear_share_elec"])
        if sub.empty: continue
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
                "ci":        round(float(row["carbon_intensity_elec"]),1)
                             if pd.notnull(row.get("carbon_intensity_elec")) else None,
            }))
        viz[pais] = rows

    return {
        "meta":                m,
        "kpis":                kpis,
        "preprocesado_pasos":  pasos,
        "tendencia_global":    tendencia,
        "cobertura_anual":     cobertura,
        "nulos_variables":     nulos,
        "comparativa_europea": comp_eur,
        "variables":           [{"nombre":v[0],"tipo":v[1],"descripcion":v[2]}
                                 for v in VARIABLES_INFO],
        "paises_viz":          PAISES_VIZ,
        "paises_labels":       PAISES_LABELS,
        "hallazgos":           HALLAZGOS,
        "datos_viz":           viz,
    }


# ══════════════════════════════════════════════════════════════════
# SECCIÓN 3 · PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════

def main(ruta_csv=None, ruta_json=None):
    ruta_json = Path(ruta_json) if ruta_json else RUTA_SALIDA
    print("\n[1/3] Cargando dataset...")
    df_raw = cargar(ruta_csv)
    print("[2/3] Limpiando y filtrando...")
    df_c, stats = limpiar(df_raw)
    print("[3/3] Calculando métricas...")
    data = calcular(df_raw, df_c, stats)
    with open(ruta_json,"w",encoding="utf-8") as f:
        json.dump(data, f, separators=(",",":"), ensure_ascii=False)
    print(f"\n✓ Generado: {ruta_json}  ({ruta_json.stat().st_size/1024:.0f} kB)")
    print("  Abre dashboard_energia.html con Live Server para ver los cambios.")


if __name__ == "__main__":
    main(
        ruta_csv  = Path(sys.argv[1]) if len(sys.argv)>1 else None,
        ruta_json = Path(sys.argv[2]) if len(sys.argv)>2 else None,
    )
