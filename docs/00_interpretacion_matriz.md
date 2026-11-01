# Interpretación de la matriz de parametrización (v0.2)

Fuente: `01_Matriz_Parametrizacion_Estudios_Actualizada.xlsx`, con sus 8 hojas: INICIO, Matriz de parametrización, Ficha de resultados, Lenguaje del usuario, Ejemplo - mediciones, Ejemplo - resultados, Flujo y relaciones y Pendientes de diseño.

## Lo que dice la matriz

- **60 campos en 10 etapas:** E01–E11 (estudio y alcance), R01–R05 (recursos), D03–D16 (diseño), V01–V10 (resultados de interés), C01–C03 (evaluación), P01–P05 (cronograma y aprobación), X01–X09 (plantilla y carga) y S01–S03 (análisis e informe). La numeración del diseño empieza en D03: no existen D01 ni D02.
- **La separación central:** dato experimental ≠ resultado de interés ≠ análisis estadístico ≠ criterio de evaluación. No existe una columna global «resultado».
- **La ficha de resultados** define *tipos* de resultado (nombre, propósito, unidad, origen directo o calculado, dependencias, referencia del cálculo, ámbito, análisis y criterio). No contiene valores ni fórmulas.
- **«Flujo y relaciones»** pide distinguir 9 componentes lógicos antes de normalizar: configuración, recursos y asignaciones, diseño y planificación, observación experimental, definición de resultado, valor de resultado, selección de análisis, criterio, e informe y auditoría.

## Cómo se clasificó cada campo

| Tipo de información | Campos | Dónde vive en el sistema |
| --- | --- | --- |
| Estudio | E01–E08 | `Estudio` (identificación) |
| Alcance | E09–E11 | `Magnitud`, `Punto` |
| Recurso | R01–R04 | `Recurso` (técnico, patrón, equipo) |
| Diseño | D03–D11, D15 | `Factor`, `Restriccion`, campos de diseño de `Estudio` |
| Medición (captura) | D12–D14, D16, X02–X04 | `Variable` (definición) y columnas del usuario en la plantilla (valores) |
| Resultado de interés | V01–V10 | `ResultadoInteres` (definición) y `resultados_valores` (valores directos) |
| Criterio | C01–C03 | `Criterio` (se registra, no se interpreta) |
| Planificación | P01–P04, D09, D10 | `MedicionPlanificada` |
| Aprobación técnica | P05, X07, C03, D08 | Aprobación del diseño (versión inmutable), aprobación del conjunto preparado, campo `aprobado` del criterio y unidad experimental (pendiente técnico) |
| Generado por el sistema | E02, V10, X01, X05, X06, X08, X09 | Código del estudio, IDs, plantilla, carga, reglas de calidad, historial, transformaciones |
| Análisis e informes | S01–S03 | «Análisis estadístico» (motor de reglas, ver `11`–`13`) e «Informes» (PDF) |

**Campos obligatorios, opcionales y condicionales.** Se tomó la columna «Cuándo se solicita» de la matriz:

- **Siempre:** son obligatorios para aprobar (E01, E03–E06, E08–E11, R01, R02, D07, D12, V01).
- **Cuando corresponda / Si aplica:** son opcionales (E07, R04, D05, D11, D13, D14, X04).
- **Por resultado o por criterio:** son condicionales. Por ejemplo, V05 y V06 solo aplican si el resultado es calculado. Si falta un condicional, se muestra una advertencia, no un bloqueo, porque la matriz los marca «Por definir» o «Pendiente técnico».

## Decisiones pendientes y cómo se resolvieron provisionalmente

Ninguna decisión pendiente se resolvió inventando un requisito metrológico. Donde había que elegir una estructura, se eligió la más extensible y se dejó registrada aquí para tu aprobación.

| Pendiente | Decisión provisional implementada | Cómo cambiarla |
| --- | --- | --- |
| PD01 obligatoriedad | Según «Cuándo se solicita» (ver arriba) | `src/configuracion/validacion_estudio.py` |
| PD02 varias magnitudes | Cada punto pertenece a una magnitud. Cada dato experimental tiene **una** unidad fija. Si dos magnitudes usan el mismo dato con unidades distintas, se definen dos datos («Indicación T», «Indicación HR») | Modelo `Variable`; no requiere migrar cargas |
| PD03 combinaciones | Plan explícito: editor fila por fila, importación CSV/Excel o generador que exige vista previa y confirmación. Nunca factorial automático | `src/planificacion/plan.py` |
| PD04 factor o metadato | Campo `rol` de la condición: «la cambiaré para comparar» o «solo la registraré» (D15) | `Factor.rol` |
| PD05 unidad experimental | Texto libre (D08). Se advierte si falta; no se usa en cálculos | — |
| PD06 compatibilidad patrón-punto | Solo **advierte** si el punto está fuera del intervalo útil del patrón o de su magnitud. Las prohibiciones explícitas van como restricciones D11 (bloquean) | `validar_plan` |
| PD07 directo o calculado | Por resultado (V04). Solo los directos tienen columna de captura | `ResultadoInteres.origen` |
| PD08 datos de origen | Se registran las dependencias (V05) y la referencia del procedimiento (V06), sin fórmula | — |
| PD09 ámbito | `serie` = repeticiones de una misma condición · `punto` = todas las mediciones del punto · `condicion` = grupo comparable de D06 · `estudio` = uno por estudio · `otro` = un registro que describe el usuario | `filas_resultados_agrupados` |
| PD10 selección para análisis | Casilla V08 por resultado; viaja en `definiciones_resultados.csv` | — |
| PD11 criterios | Se registran (fuente, versión, comparación, valor en texto, condiciones, aprobado) sin interpretarlos | — |
| PD12 resultados directos | Ámbito «medición»: columna propia en «Mediciones». Otros ámbitos: hoja «Resultados_directos» con un registro por grupo | `especificacion.py` |
| PD13 versiones | Aprobar congela una versión inmutable con huella SHA-256. Editar devuelve a borrador; aprobar otra vez crea vN+1. Cada carga queda vinculada a su versión y nunca se sobrescribe | `RepositorioLocal` |
| PD17 calidad | 20 reglas RC01–RC20 (ver `04_matriz_reglas_calidad.md`) | `src/calidad/reglas.py` |
| PD14, PD18, PD19 | Implementados en la versión 3–5: motor (`src/motor/`), escenarios de prueba (`data/estudios_prueba/`) e informe PDF | `11`–`13` |
| PD15 Supabase | Repositorio local con el mismo contrato (`Repositorio`). El esquema de Supabase se escribe cuando apruebes el modelo | `src/persistencia/` |
| PD16 validar lenguaje | Las preguntas de la hoja «Lenguaje del usuario» se usan tal cual en la interfaz. Falta validarlas con un usuario del laboratorio | — |

## Incompatibilidades o ambigüedades reales encontradas

1. **E08 «Responsable · Selección»:** no existe un catálogo de responsables en la matriz, así que se implementó como texto. Si se quiere una lista, hay que definir de dónde sale.
2. **R05 «Disponibilidad de recursos» (Por definir):** no se implementó calendario ni detección de solapamientos. Se indica en la interfaz.
3. **«Condición» en V07:** la palabra se usa también para los factores (D03). Se interpretó como *grupo comparable* (D06) para no confundirla con una sola condición experimental (ver PD09).
4. **Unidad única por dato (PD02):** la matriz pide «nombre, tipo y unidad» por dato (D12), lo cual es incompatible con un dato que cambie de unidad según la magnitud del punto. Se resolvió definiendo datos separados.
5. **D10 «Orden de ejecución» (Por definir):** se registra un orden manual. No se aleatoriza ni se genera cronograma.
6. **`app_modulo1.py`:** su funcionalidad (formulario de estudio y plantilla) quedó reemplazada por la nueva aplicación. Sus reglas se conservaron: no generar factorial automático y no crear una columna «resultado».
