# Salida para el motor estadístico (formato SAL-1.0)

La página «Datos preparados» descarga un ZIP: `conjunto_preparado_<estudio>_<preparación>.zip`. Todos los CSV están en UTF-8 con BOM (Excel muestra bien las tildes) y separados por comas.

## Cómo leerlo desde Python

```python
from src.exportacion.lector_salida import cargar_conjunto, matriz_por_variable

datos = cargar_conjunto("conjunto_preparado_EST-0001_PREP-....zip")   # verifica las huellas SHA-256
obs = datos["observaciones_analisis"]        # DataFrame listo para analizar
datos["manifiesto"]["conteos"]               # recibidos, incluidos, pendientes, excluidos…
indicacion = matriz_por_variable(datos, "V-01")
indicacion.groupby(["punto_id", "grupo_comparable"])["valor_numerico"].describe()
```

También puedes ejecutar `python -m ejemplos.leer_salida <zip>`. Sin el paquete del proyecto, basta con `pandas.read_csv(..., encoding="utf-8-sig")` sobre cada archivo del ZIP.

## Archivos

| Archivo | Una fila es | Uso |
| --- | --- | --- |
| `observaciones_analisis.csv` | un dato experimental de una medición **incluida** | Vista principal: valores + contexto + una columna `factor:<nombre>` por condición |
| `mediciones.csv` | una medición incluida | Contexto: punto, repetición, grupo comparable, condición, recursos previstos y reales, fechas |
| `valores.csv` | un dato experimental (formato largo) | Datos normalizados, sin columnas rígidas |
| `niveles_factores.csv` | una condición de una medición | Factores y opciones (formato largo) |
| `resultados_valores.csv` | un valor de resultado de interés registrado directamente | Resultados de cualquier ámbito (medición o grupo) |
| `definiciones_variables.csv` | un dato configurado | Código, nombre, tipo, unidad, obligatoriedad |
| `definiciones_resultados.csv` | un resultado de interés configurado | Origen (directo o calculado), dependencias, referencia del cálculo, ámbito, ¿analizar?, ¿tiene criterio? |
| `criterios.csv` | un criterio | Fuente, versión, comparación y valor (texto, sin interpretar), aprobado |
| `factores.csv`, `puntos.csv`, `recursos.csv` | configuración | Catálogos del diseño |
| `registros_estado.csv` | **cada** registro recibido | Estado y motivo, incluidos pendientes y excluidos |
| `incidencias.csv`, `transformaciones.csv`, `exclusiones.csv` | un evento de calidad | Trazabilidad de la preparación |
| `estudio_version.json` | — | Diseño aprobado completo |
| `manifiesto.json` | — | Estudio, versión, huella, carga, SHA-256 del original, transformaciones autorizadas, exclusiones, conteos, huellas y filas por tabla |
| `observaciones_analisis.xlsx` | — | Copia en Excel para revisión o Minitab. No entra en la huella reproducible |

## Columnas principales

**Comunes:** `codigo_estudio`, `version_diseno`, `carga_id`.

| Columna | Significado |
| --- | --- |
| `medicion_id` | Identificador de la medición planificada (M0001…) |
| `punto_id`, `magnitud_id`, `magnitud`, `valor_nominal`, `unidad_punto` | Punto de medición |
| `repeticion` | Número de repetición dentro de su condición |
| `grupo_comparable` | Clave del grupo según D06, p. ej. `punto=PT-01` |
| `condicion` | Condición completa: punto · técnico · patrón · equipo · factor=nivel (separados por «\|») |
| `factor:<nombre>` | Opción de cada condición (solo en la vista de análisis) |
| `tecnico_previsto` / `tecnico_real`, `patron_previsto` / `patron_real` | Asignación planificada y la registrada |
| `variable_id`, `variable`, `categoria`, `tipo_dato`, `unidad` | Dato experimental |
| `valor_numerico` / `valor_texto` | Valor interpretado (número o texto, según el tipo). Vacío = no registrado; nunca cero |
| `valor_original` | Texto exacto de la celda original |
| `transformaciones` | Códigos aplicados a esa celda (p. ej. `TR02`) |
| `hoja`, `fila_excel`, `celda` | Ubicación exacta en el archivo original |
| `estado_calidad` | aceptado · normalizado · con_advertencia |
| `resultado_id`, `ambito`, `origen`, `registro_id`, `grupo`, `mediciones` | En `resultados_valores`: a qué resultado y a qué registro o grupo pertenece el valor |

## Garantías

- Solo entran las mediciones con estado aceptado, normalizado o con advertencia. Las demás están en `registros_estado.csv` con su motivo.
- Valores sin redondeo, sin cambio de signo y sin conversión de unidades.
- Reproducible: con la misma carga, las mismas transformaciones y las mismas exclusiones, los CSV son idénticos byte a byte (`manifiesto.json → huellas_archivos`).
- Los resultados **calculados** (p. ej. error) aún no tienen valores: el motor los calculará a partir de `definiciones_resultados.csv → dependencias`.
