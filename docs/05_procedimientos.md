# Procedimientos: plantilla, ingesta, limpieza y transformación

## 1. Generación de la plantilla (X01)

**Condición previa:** el diseño está aprobado (P05). Si después se edita, vuelve a borrador y la plantilla se genera desde una versión aprobada.

1. Se calcula la huella SHA-256 del diseño, sin los metadatos de aprobación.
2. Se construye la especificación de columnas (`columnas_mediciones`). Siempre es la misma lista para el generador y para la ingesta.
3. Se crean las hojas:

| Hoja | Contenido | Quién la completa |
| --- | --- | --- |
| Instrucciones | Pasos de diligenciamiento y leyenda de colores | — |
| Mediciones | Una fila por medición planificada, ordenada por «Orden» y luego por ID | Gris: el sistema · morado: el usuario |
| Resultados_directos | Solo si hay resultados directos de ámbito distinto a «medición»: una fila por grupo | Gris: el sistema · Valor y Observaciones: el usuario |
| Estudio | Código, nombre, versión, huella, fecha, recursos y puntos | — |
| Definiciones | Datos a registrar y resultados de interés (indica cuáles se calcularán después) | — |
| `_control` (oculta) | Formato PLT-1.0, estudio, versión, huella, especificación de columnas | — |
| `_listas` (oculta) | Listas para las validaciones (técnicos, patrones, opciones) | — |

4. **Columnas de «Mediciones»:**
   - Sistema: ID medición, código y valor del punto, magnitud, unidad, repetición, condiciones que se comparan, técnico, patrón y equipo previstos, fecha y franja previstas, orden.
   - Usuario: un dato experimental por columna con su unidad entre corchetes (los obligatorios llevan «*»), las condiciones que solo se registran (D15), los resultados directos por medición, y Técnico que midió, Patrón usado, Fecha real, Hora real, Motivo del cambio y Observaciones (X03, X04, D16).
5. **Validaciones de celda** con estilo «advertencia» (avisan sin bloquear): número en los decimales, entero, fecha, Sí/No y listas de técnicos y patrones. Sin formatos de número que redondeen.
6. **Protección de hoja sin contraseña:** las celdas del sistema quedan bloqueadas y las del usuario libres. Se permite filtrar, ordenar y ajustar columnas.

## 2. Ingesta (X05, X06)

`servicios.flujo.cargar_archivo(repo, codigo, bytes, nombre, usuario, version_esperada)`:

| Paso | Qué ocurre | Regla si falla |
| --- | --- | --- |
| 1. Recibir | Se calcula el SHA-256 y se asigna `carga_id`. El original se guarda siempre, incluso si se rechaza | — |
| 2. Formato | openpyxl abre el libro | RC01 (rechazo) |
| 3. Hojas | Existen `_control` y «Mediciones» (y «Resultados_directos» si el diseño la exige) | RC02 |
| 4. Plantilla | formato_plantilla = PLT-1.0 | RC03 |
| 5. Estudio | codigo_estudio = estudio seleccionado | RC04 |
| 6. Versión | La versión existe, es la esperada y su huella coincide con la aprobada | RC05 |
| 7. Columnas | Cada encabezado esperado (con su unidad) está en la fila 1. Las columnas se ubican por encabezado, no por posición | RC06 (rechazo) / RC07 (columna extra: advierte) |
| 8. Lectura | Cada fila no vacía conserva su número de fila de Excel y sus valores sin interpretar | — |
| 9. Evaluación inicial | Reglas de registro con las transformaciones por defecto (TR01, TR03) | RC08–RC20 |
| 10. Historial | Si existe una carga anterior de la misma versión, se calculan las celdas que cambiaron (X08) | — |
| 11. Bitácora | Evento `archivo_cargado`, con usuario, huella y conteos | — |

## 3. Calidad, limpieza y transformación (X06, X07, X09)

`calidad.evaluador.evaluar(lectura, estudio_version, autorizadas, exclusiones)` es una función pura. Con las mismas entradas da el mismo resultado.

**Por cada fila de «Mediciones»:**

1. Sin ID → RC09 (excluida). Con un ID que no está en el plan → RC08 (excluida). ID repetido → RC10 (todas sus filas quedan pendientes).
2. Las celdas grises distintas del plan aprobado → RC13 (pendiente).
3. Si todos los datos y resultados directos están vacíos → RC14 (pendiente; un solo mensaje por medición).
4. Para cada celda del usuario:
   - vacía y obligatoria → RC15 (pendiente);
   - vacía y opcional → queda vacía (nunca cero);
   - se interpreta según su tipo con las transformaciones autorizadas; si no se puede → RC16 (pendiente, con pista sobre TR02 si se usó coma decimal);
   - técnico o patrón real fuera del catálogo → RC17 (pendiente; TR04 corrige solo mayúsculas si está autorizada);
   - hora con formato inválido → RC19 (advierte).
5. Técnico o patrón real distinto del previsto y sin motivo → RC18 (advierte).
6. Exclusión manual: solo con motivo. Se registra con el usuario.
7. Estado = excluido > pendiente > con_advertencia > normalizado > aceptado.

**Al final:** las mediciones planificadas que no aparecen → RC11; el número de filas distinto del planificado → RC12. Los conteos se concilian: recibidos = suma de estados.

**Preparación** (`preparar_conjunto`): repite la evaluación con las transformaciones que autorizó el usuario y sus exclusiones, y construye las tablas de salida, el ZIP y el informe de incidencias. Lo guarda todo con su manifiesto. La aprobación del conjunto (X07) es un paso separado, con usuario y fecha.

**Prohibido por diseño** (no existe código que lo haga): reemplazar faltantes por cero, imputar, redondear, convertir unidades, cambiar signos y eliminar observaciones por su comportamiento estadístico.
