# Implementacion de las visualizaciones 2 y 3

Este documento explica los cambios hechos en el dashboard y el motivo de cada decision.

## Resumen de lo implementado

Se han completado las dos secciones vacias del dashboard:

- **Visualizacion 2:** relacion entre PIB per capita e intensidad de carbono electrica.
- **Visualizacion 3:** ranking de paises que mas han aumentado su cuota renovable y desglose de tecnologias renovables.

Tambien se han anadido dos apartados nuevos dentro de **Codificacion Visual**, uno para cada visualizacion, siguiendo el formato que ya existia para la visualizacion principal.

## Cambios en `preprocesado_energia.py`

El frontend no calcula todos los datos desde el CSV directamente. Primero el script Python genera `dashboard_data.json`, y el HTML solo consume ese JSON. Por eso las dos nuevas visualizaciones empiezan en el preprocesado.

### Datos para la Visualizacion 2

Se ha anadido la clave:

```json
"scatter_economia_carbono"
```

Incluye:

- `year`: ano elegido por defecto para el grafico.
- `years`: lista de anos seleccionables, siempre con cobertura suficiente.
- `por_year`: datos completos agrupados por ano.
- `n_paises`: numero de paises con datos validos en el ano activo.
- `corr_gdp_ci`: correlacion entre PIB per capita e intensidad de carbono en el ano activo.
- `corr_low_carbon_ci`: correlacion entre cuota baja en carbono e intensidad en el ano activo.
- `puntos`: lista de paises del ano activo con PIB per capita, poblacion, intensidad, cuota fosil, cuota renovable, nuclear y cuota baja en carbono.

El ano por defecto sigue siendo **2022**, porque es el ultimo ano con buena cobertura de PIB, poblacion e intensidad de carbono. Ahora, ademas, el usuario puede cambiar a otros anos disponibles desde un selector.

### Datos para la Visualizacion 3

Se ha anadido la clave:

```json
"transicion_renovable"
```

Incluye:

- `year0` y `year1`: periodo comun comparado, actualmente 2000-2024.
- `default_n`: numero de paises que se muestran inicialmente.
- `n_total`: numero total de paises comparables.
- `tecnologias`: tecnologias renovables disponibles.
- `paises`: ranking completo de paises ordenados por aumento de cuota renovable.

Para cada pais se guardan:

- cuota renovable inicial y final;
- aumento en puntos porcentuales;
- intensidad de carbono inicial y final;
- desglose final por hidro, eolica, solar, bioenergia y otras renovables.

Se usa un periodo comun para todos los paises, evitando mezclar paises con datos hasta 2025 con otros que solo llegan a 2024.

## Cambios en `index.html`

### Visualizacion 2

Se ha creado un diagrama de dispersion con burbujas:

- **Eje X:** PIB per capita en escala logaritmica.
- **Eje Y:** intensidad de carbono electrica.
- **Tamano del circulo:** poblacion del pais.
- **Color:** cuota de electricidad baja en carbono.
- **Selector:** ano de comparacion, limitado a anos con suficientes datos.

El objetivo es comprobar si los paises mas ricos tienen electricidad mas limpia. El resultado muestra que la relacion PIB-intensidad es debil, mientras que la cuota baja en carbono se asocia mucho mas claramente con menor intensidad.

Tambien se ha ajustado el eje X para que no se superpongan las etiquetas: en lugar de mostrar cantidades largas en dolares, se usan marcas abreviadas como `$1k`, `$10k` o `$100k`.

### Visualizacion 3

Se ha creado un ranking de barras horizontales apiladas:

- Los paises se ordenan por aumento de cuota renovable.
- Cada barra muestra la composicion renovable final.
- Una linea blanca marca la cuota renovable inicial.
- La etiqueta final muestra el aumento acumulado en puntos porcentuales.
- Un selector permite elegir cuantos paises del top se muestran.
- Otro control permite anadir un pais concreto al ranking para compararlo con el top aunque no aparezca entre los primeros.

Esto permite ver no solo quien crece mas, sino tambien **con que tecnologia**: hidro, eolica, solar, bioenergia u otras.