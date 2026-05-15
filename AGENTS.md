# Contexto del repositorio para agentes

Este repositorio contiene un dashboard estático de visualización de datos sobre transición ecológica y energía para TVD, Tema 5. Es una aplicación sin framework ni build step: el HTML se sirve directamente y consume un JSON generado previamente.

El flujo principal es:

1. `owid-energy-data.csv` contiene el dataset bruto local de Our World in Data.
2. `preprocesado_energia.py` limpia, filtra, selecciona variables dinámicamente y genera estructuras derivadas.
3. `dashboard_data.json` es el contrato de datos generado para el frontend.
4. `index.html` carga ese JSON con `fetch()` y renderiza el dashboard con D3.

## Archivos

- `index.html`: aplicación completa en un solo HTML. Incluye CSS, navegación, secciones, carga de `dashboard_data.json` y funciones D3 de renderizado. Es el archivo de entrada para GitHub Pages.
- `preprocesado_energia.py`: script de preprocesado. Es el sitio preferente para cambiar años, país de referencia, tamaño de selecciones, reglas de selección de variables, métricas y estructuras del JSON.
- `dashboard_data.json`: salida generada. No editar a mano salvo para inspección puntual; se regenera con el script Python y debe subirse al repo porque GitHub Pages no ejecuta Python.
- `owid-energy-data.csv`: dataset local bruto, unas 23k filas y 130 columnas.
- `IMPLEMENTACION_VISUALIZACIONES.md`: explicación didáctica de las visualizaciones 2 y 3 y de las decisiones de codificación visual.
- `AGENTS.md`: este archivo, guía de contexto para agentes.

## Cómo ejecutar

Para regenerar datos:

```bash
python3 preprocesado_energia.py
```

También acepta rutas opcionales:

```bash
python3 preprocesado_energia.py ruta_entrada.csv ruta_salida.json
```

Para ver el dashboard en local, abrir `index.html` con Live Server o servir la carpeta con un servidor estático. Abrir el HTML directamente con `file://` puede fallar por la llamada `fetch('./dashboard_data.json')`.

```bash
python3 -m http.server 8000
```

Después abrir:

```text
http://127.0.0.1:8000/
```

Para verlo en GitHub Pages, configurar Pages con `main` y `/root`. Al existir `index.html` en la raíz, la URL del proyecto debería servir el dashboard directamente.

Dependencias del preprocesado:

```bash
pip install pandas numpy
```

El HTML usa D3 v7 desde CDN y fuentes de Google Fonts, así que necesita red para esos assets si no están cacheados.

## Flujo de datos

`preprocesado_energia.py`:

- Lee `owid-energy-data.csv` si existe; si no, intenta descargar el CSV desde GitHub de OWID.
- Detecta variables prioritarias de forma dinámica con `variables_disponibles()`, `columnas_prioritarias()` y `describir_variable()`.
- Conserva columnas base como `country`, `year`, `population`, `gdp`, `electricity_generation`, `carbon_intensity_elec` y patrones como `*_electricity`, `*_share_elec`, `*_production`, `*_consumption`, `*_change_pct` y `*_change_twh`.
- Elimina filas sin `iso_code`, porque suelen ser agregados regionales como `World`, `Europe`, `Asia` o `ASEAN`.
- Filtra años con `year >= YEAR_MIN`; actualmente `YEAR_MIN = 2000`.
- Elimina `iso_code` antes de exportar el dataset limpio.
- Selecciona países para la visualización principal por cobertura de datos y población mediante `paises_con_datos_viz()`.
- Calcula KPIs, pasos de preprocesado, tendencia global, cobertura anual, tabla de nulos, comparativa renovable, visualización economía-carbono, ranking de transición renovable y series por país.
- Escribe `dashboard_data.json` minificado con `json.dump(..., separators=(",", ":"), ensure_ascii=False)`.

## Contrato JSON

El JSON generado tiene estas claves de primer nivel:

- `meta`: metadatos del dataset, periodo, país de referencia, tamaños y timestamp.
- `kpis`: cuatro métricas del encabezado.
- `preprocesado_pasos`: textos HTML para la sección de cadena de preprocesado.
- `tendencia_global`: medianas anuales de fósiles, renovables, nuclear e intensidad de carbono para países con mayor población y cobertura suficiente.
- `cobertura_anual`: número de países con datos de cuota fósil por año.
- `nulos_variables`: comparación de porcentaje de nulos antes/después para las primeras variables seleccionadas.
- `comparativa_europea`: comparativa histórica de renovables e intensidad para países seleccionados dinámicamente. El nombre se mantiene por compatibilidad aunque ya no sea estrictamente europea.
- `scatter_economia_carbono`: datos de Visualización 2.
- `transicion_renovable`: datos de Visualización 3.
- `variables`: tabla de variables seleccionadas dinámicamente.
- `paises_viz`, `paises_labels`, `hallazgos`: selector, etiquetas y texto narrativo por país.
- `datos_viz`: series anuales por país para la visualización principal.

### `scatter_economia_carbono`

Estructura usada por Visualización 2:

- `year`: año activo por defecto; actualmente `2022`.
- `years`: lista de años seleccionables con cobertura suficiente; actualmente 23 años, de `2000` a `2022`.
- `por_year`: diccionario por año con puntos, número de países y correlaciones.
- `n_paises`: países válidos del año por defecto; actualmente `165`.
- `corr_gdp_ci`: correlación entre log10(PIB per cápita) e intensidad de carbono.
- `corr_low_carbon_ci`: correlación entre cuota baja en carbono e intensidad de carbono.
- `puntos`: países del año activo con PIB per cápita, población, intensidad, fósil, renovable, nuclear y cuota baja en carbono.

Visualización 2 no usa 2024 porque el CSV actual no tiene cobertura suficiente de `gdp` para ese año. Por eso el selector solo ofrece años con datos suficientes.

### `transicion_renovable`

Estructura usada por Visualización 3:

- `year0`: año inicial común; actualmente `2000`.
- `year1`: año final común; actualmente `2024`.
- `default_n`: número de países mostrados inicialmente; actualmente `12`.
- `n_total`: número total de países comparables; actualmente `192`.
- `tecnologias`: tecnologías renovables disponibles (`hydro`, `wind`, `solar`, `biofuel`, `other_renewables`).
- `paises`: ranking completo ordenado por `delta_renew`.

`delta_renew` se calcula como:

```text
delta_renew = renew_yr1 - renew_yr0
```

Es una diferencia en puntos porcentuales, no un crecimiento relativo. Ejemplo: pasar de 10% a 30% equivale a `+20 pp`, no a “+200%”.

## Configuración importante

Editar preferentemente la sección 1 de `preprocesado_energia.py`:

- `YEAR_MIN`, `YEAR_MAX`: rango temporal filtrado.
- `N_PAISES_VIZ`: tamaño del selector de la visualización principal.
- `N_PAISES_COMPARATIVA`: tamaño de la comparativa renovable de contexto.
- `N_PAISES_TENDENCIA`: países usados para la tendencia global.
- `N_PAISES_TRANSICION`: número por defecto del ranking de transición renovable.
- `MIN_PAISES_SCATTER`: cobertura mínima para que un año aparezca en Visualización 2.
- `PAIS_REF_PREFERIDO`: país preferido para KPIs, actualmente `Spain`.
- `KPI_YEAR`: año usado en KPIs y en el final común de Visualización 3, actualmente `2024`.

Ya no existe una lista fija `VARIABLES_INFO`, `PAISES_VIZ`, `PAISES_EUROPA`, `PAISES_GLOBALES` o `HALLAZGOS` como fuente principal. El script genera variables, países y hallazgos de forma dinámica. Si se reintroducen listas manuales, actualizar este documento y el contrato JSON.

## Frontend

`index.html` tiene estas secciones de navegación:

- `ctx`: Contexto y Dataset.
- `abs`: Abstracción de Tarea.
- `t1`: Visualización Principal.
- `t2`: Visualización 2 — Economía e Intensidad de Carbono.
- `t3`: Visualización 3 — Quién Acelera Renovables y Con Qué Tecnología.
- `cod`: Codificación Visual.

La navegación está ordenada como: Contexto y Dataset, Abstracción de Tarea, Visualización Principal, Visualización 2, Visualización 3 y Codificación Visual.

Dentro de `cod` hay un selector para elegir la codificación visual de `t1`, `t2` o `t3`. Las tres visualizaciones tienen explicación de codificación visual.

Funciones principales del script del HTML:

- `initDashboard(data)`: orquesta todo el renderizado inicial.
- `renderHeader`, `renderKPIs`, `renderFicha`, `renderPasos`, `renderVariables`: rellenan textos/tablas y selector de variables.
- `renderPreprocChart`, `renderCoverageChart`, `renderGlobalTrend`, `renderEurComp`: visualizaciones de contexto.
- `renderSelector`, `setView`, `renderChart`, `renderCIChart`: visualización principal por país.
- `initScatterControls`, `renderScatterEconomia`: controles y renderizado de Visualización 2.
- `initTransitionControls`, `renderTransitionRenewables`: controles y renderizado de Visualización 3.
- `setCodViz`: alterna el bloque visible dentro de Codificación Visual.
- `showSection`: cambio de pestañas y re-render de gráficos al entrar en secciones ocultas.

El gráfico principal usa dos modos:

- `detail`: `coal`, `oil`, `gas`, `nuclear`, `renewables`.
- `summary`: `fossil`, `nuclear`, `renewables`.

Visualización 2:

- Scatter/bubble chart.
- X: PIB per cápita en escala logarítmica.
- Y: `carbon_intensity_elec`.
- Tamaño: población.
- Color: cuota baja en carbono.
- Control: selector de año entre los años con cobertura suficiente.
- El eje X usa etiquetas abreviadas (`$1k`, `$10k`, `$100k`) para evitar solapamientos.

Visualización 3:

- Ranking horizontal con barras apiladas por tecnología renovable.
- Orden: `delta_renew` descendente.
- Longitud total: cuota renovable final.
- Línea vertical: cuota renovable inicial.
- Etiqueta: aumento acumulado en puntos porcentuales.
- Controles: selector de número de países del top y selector para añadir países concretos al ranking.

## Estado actual de los datos generados

Según `dashboard_data.json` actual:

- Periodo visual: `2000-2025`.
- País de referencia: `Spain`.
- Año KPI: `2024`.
- Dataset bruto: 23,377 filas, 130 columnas, 314 entidades.
- Dataset limpio: 5,549 filas, 83 columnas, 220 países.
- Filas sin `iso_code` eliminadas: 6,112.
- Registros históricos eliminados por filtro temporal: 11,716.
- Países en selector principal: 20.
- Visualización 2: año por defecto `2022`, 165 países válidos, 23 años seleccionables.
- Visualización 3: periodo `2000-2024`, 192 países comparables, 12 países mostrados por defecto.
- `dashboard_data.json` está minificado en una sola línea y pesa aproximadamente 1.1 MB.

KPIs actuales para Spain 2024:

- Cuota fósil: 23.3%.
- Cuota renovables: 57.3%.
- Intensidad de carbono: 146 gCO2/kWh.
- Variación de intensidad frente a 2000: -69%.

## Convenciones y precauciones

- Mantener el contrato entre `preprocesado_energia.py` e `index.html`: si se renombra una clave del JSON, actualizar los renderizadores correspondientes.
- Preferir cambios en el script Python para alterar datos, países, textos o métricas. Después regenerar `dashboard_data.json`.
- `dashboard_data.json` debe estar versionado y pusheado porque GitHub Pages no ejecuta `preprocesado_energia.py`.
- El JSON debe quedar minificado en una sola línea. Si aparece con decenas de miles de líneas, fue formateado con `python -m json.tool` u otra herramienta; regenerarlo con `python3 preprocesado_energia.py`.
- Para inspeccionar el JSON sin modificarlo, usar `python3 -m json.tool dashboard_data.json | less` o scripts de lectura que no escriban el archivo.
- Evitar editar el CSV bruto salvo que el usuario lo pida explícitamente.
- Si se actualiza el dataset desde la URL de OWID, las cifras pueden cambiar. Revisar KPIs, hallazgos automáticos, años disponibles de Visualización 2 y ranking de Visualización 3.
- El código mezcla español en la interfaz y nombres de columnas originales en inglés; conservar esta convención.
- Mantener las visualizaciones como D3 dentro de `index.html`; no introducir frameworks ni build step sin petición explícita.

## Checklist recomendado para cambios

Después de tocar `preprocesado_energia.py` o el contrato de datos:

```bash
python3 preprocesado_energia.py
python3 -m py_compile preprocesado_energia.py
python3 -m json.tool dashboard_data.json >/dev/null
```

Después de tocar JavaScript embebido en `index.html`, una comprobación útil es extraer el script y validar sintaxis con Node:

```bash
awk '/<script>/{flag=1;next}/<\/script>/{flag=0}flag' index.html > /tmp/dashboard-script.js
node --check /tmp/dashboard-script.js
```

Antes de terminar:

```bash
git diff --check
git status --short
```
