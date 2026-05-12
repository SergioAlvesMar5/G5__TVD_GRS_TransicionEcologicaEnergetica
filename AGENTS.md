# Contexto del repositorio para agentes

Este repositorio contiene un dashboard estático de visualización de datos sobre transición ecológica y energía para TVD, Tema 5. El flujo principal es:

1. `owid-energy-data.csv` contiene el dataset bruto de Our World in Data.
2. `preprocesado_energia.py` limpia, filtra y agrega los datos.
3. `dashboard_data.json` es el contrato de datos generado para el frontend.
4. `index.html` carga ese JSON con `fetch()` y renderiza el dashboard con D3.

## Archivos

- `index.html`: aplicación completa en un solo HTML. Incluye CSS, estructura de secciones, carga de `dashboard_data.json` y funciones D3 de renderizado. Es el archivo de entrada para GitHub Pages.
- `preprocesado_energia.py`: script de preprocesado. Es el sitio preferente para cambiar países, variables, textos de hallazgos, años y métricas.
- `dashboard_data.json`: salida generada. No conviene editarlo a mano salvo para inspección rápida; se regenera con el script Python.
- `owid-energy-data.csv`: dataset local bruto, unas 23k filas y 130 columnas.

## Cómo ejecutar

Para regenerar datos:

```bash
python preprocesado_energia.py
```

También acepta rutas opcionales:

```bash
python preprocesado_energia.py ruta_entrada.csv ruta_salida.json
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
- Selecciona `iso_code` más las variables listadas en `VARIABLES_INFO`.
- Elimina filas sin `iso_code`, porque suelen ser agregados regionales como `World`, `Europe` o `Asia`.
- Filtra años con `year >= YEAR_MIN`; actualmente `YEAR_MIN = 2000`.
- Elimina `iso_code` antes de exportar el dataset limpio.
- Calcula KPIs, pasos de preprocesado, tendencia global, cobertura anual, tabla de nulos, comparativa europea y series por país.
- Escribe `dashboard_data.json` minificado con `ensure_ascii=False`.

El JSON generado tiene estas claves de primer nivel:

- `meta`: metadatos del dataset, periodo, país de referencia, tamaños y timestamp.
- `kpis`: cuatro métricas del encabezado.
- `preprocesado_pasos`: textos HTML para la sección de cadena de preprocesado.
- `tendencia_global`: medianas anuales de fósiles, renovables, nuclear e intensidad de carbono para 20 economías.
- `cobertura_anual`: número de países con datos de cuota fósil por año.
- `nulos_variables`: comparación de porcentaje de nulos antes/después para las primeras variables seleccionadas.
- `comparativa_europea`: renovables e intensidad de carbono para países europeos en año inicial y KPI year.
- `variables`: tabla de variables seleccionadas.
- `paises_viz`, `paises_labels`, `hallazgos`: selector, etiquetas en español y texto narrativo por país.
- `datos_viz`: series anuales por país para el gráfico principal.

## Configuración importante

Editar preferentemente la sección 1 de `preprocesado_energia.py`:

- `YEAR_MIN`, `YEAR_MAX`: rango temporal filtrado.
- `VARIABLES_INFO`: columnas seleccionadas y textos que ve el dashboard.
- `PAIS_REF`, `PAIS_REF_LABEL`, `KPI_YEAR`: país/año usados en los KPIs.
- `PAISES_VIZ`: países del selector principal.
- `PAISES_LABELS`: etiquetas en español.
- `PAISES_EUROPA`: países de la comparativa europea.
- `PAISES_GLOBALES`: países usados para la tendencia global.
- `HALLAZGOS`: textos de hallazgo bajo la visualización principal.

Si se añade un país a `PAISES_VIZ`, conviene añadir también su etiqueta en `PAISES_LABELS` y su entrada en `HALLAZGOS`.

## Frontend

`index.html` tiene estas secciones de navegación:

- `ctx`: Contexto y Dataset.
- `abs`: Abstracción de Tarea.
- `t1`: Visualización Principal.
- `t2`: Visualización 2. Contenedor preparado y vacío; su contenido se añadirá posteriormente.
- `t3`: Visualización 3. Contenedor preparado y vacío; su contenido se añadirá posteriormente.
- `cod`: Codificación Visual.

La navegación actual está ordenada como: Contexto y Dataset, Abstracción de Tarea, Visualización Principal, Visualización 2, Visualización 3 y Codificación Visual.

Dentro de `cod` hay un selector para elegir la codificación visual de `t1`, `t2` o `t3`. Solo la codificación de la Visualización Principal tiene contenido actualmente; las entradas de Visualización 2 y Visualización 3 están preparadas pero vacías.

Funciones principales del script del HTML:

- `initDashboard(data)`: orquesta todo el renderizado inicial.
- `renderHeader`, `renderKPIs`, `renderFicha`, `renderPasos`, `renderVariables`: rellenan textos/tablas.
- `renderPreprocChart`, `renderCoverageChart`, `renderGlobalTrend`, `renderEurComp`: visualizaciones de contexto.
- `renderSelector`, `setView`, `renderChart`, `renderCIChart`: visualización principal por país.
- `setCodViz`: alterna el bloque visible dentro de Codificación Visual.
- `showSection`: cambio de pestañas.

El gráfico principal usa dos modos:

- `detail`: `coal`, `oil`, `gas`, `nuclear`, `renewables`.
- `summary`: `fossil`, `nuclear`, `renewables`.

## Estado actual de los datos generados

Según `dashboard_data.json` actual:

- Periodo visual: `2000-2025`.
- País de referencia: España.
- Año KPI: `2024`.
- Dataset bruto: 23,377 filas, 130 columnas, 314 entidades.
- Dataset limpio: 5,549 filas, 25 columnas, 220 países.
- Filas sin `iso_code` eliminadas: 6,112.
- Registros históricos eliminados por filtro temporal: 11,716.
- Países en selector principal: 20.

KPIs actuales para España 2024:

- Cuota fósil: 23.3%.
- Cuota renovables: 57.3%.
- Intensidad de carbono: 146 gCO2/kWh.
- Variación de intensidad frente a 2000: -69%.

## Convenciones y precauciones

- Mantener el contrato entre `preprocesado_energia.py` e `index.html`: si se renombra una clave del JSON, actualizar los renderizadores correspondientes.
- Preferir cambios en el script Python para alterar datos, países, textos o métricas. Después regenerar `dashboard_data.json`.
- El JSON está minificado en una sola línea; para inspeccionarlo usar `python -m json.tool dashboard_data.json`.
- Evitar editar el CSV bruto salvo que el usuario lo pida explícitamente.
- Si se actualiza el dataset desde la URL de OWID, las cifras pueden cambiar. Revisar especialmente hallazgos escritos a mano en `HALLAZGOS`.
- El código mezcla español en la interfaz y nombres de columnas originales en inglés; conservar esta convención.
- El dashboard es estático, sin framework ni build step.
