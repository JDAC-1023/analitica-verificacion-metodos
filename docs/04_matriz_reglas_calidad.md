# Matriz de reglas de calidad de datos

> Generada desde `src/calidad/reglas.py`. Cada regla tiene una prueba automatizada que demuestra su funcionamiento.

Las reglas evalúan **calidad estructural** (formato, correspondencia con el diseño, completitud, tipos, identificadores). No evalúan estadísticamente los resultados.

**Severidades:** `bloquea_archivo` rechaza el archivo completo · `excluye_registro` saca el registro del conjunto con motivo automático · `pendiente` deja el registro pendiente de corrección · `advertencia` conserva el registro e informa.

## Reglas

| Código | Nombre | Descripción | Aplica a | Condición evaluada | Tipo de incidencia | Severidad | Tratamiento permitido | Mensaje para el usuario | Información que se conserva | Prueba que lo demuestra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| RC01 | Archivo incompatible | El archivo no se puede abrir como libro de Excel (.xlsx). | Archivo | openpyxl no logra abrir el contenido recibido | Formato | bloquea_archivo | Rechazar el archivo; no se lee ningún registro. | El archivo «{archivo}» no es un Excel válido (.xlsx) y fue rechazado. Descarga de nuevo la plantilla y guárdala como .xlsx. | Archivo original, huella SHA-256, fecha y usuario de la carga. | tests/test_ingesta.py::test_archivo_no_excel_se_rechaza |
| RC02 | Hoja requerida ausente | Falta una hoja que la plantilla debe contener. | Archivo / hoja | Hoja «Mediciones», «_control» o «Resultados_directos» (si el diseño la exige) no existe | Estructura | bloquea_archivo | Rechazar el archivo. | Falta la hoja «{hoja}». El archivo fue rechazado porque no conserva la estructura de la plantilla. | Archivo original y lista de hojas encontradas. | tests/test_ingesta.py::test_hoja_mediciones_ausente_rechaza |
| RC03 | Plantilla no reconocida | El archivo no tiene los metadatos de control o el formato de plantilla no es compatible. | Archivo / _control | formato_plantilla ≠ PLT-1.0 o metadatos ilegibles | Versión de formato | bloquea_archivo | Rechazar el archivo. | El archivo no corresponde a una plantilla generada por esta aplicación (formato {valor}). | Archivo original y metadatos leídos. | tests/test_ingesta.py::test_formato_de_plantilla_incompatible |
| RC04 | Archivo de otro estudio | El código de estudio del archivo no coincide con el estudio seleccionado. | Archivo / _control | codigo_estudio del archivo ≠ estudio seleccionado | Identificación | bloquea_archivo | Rechazar el archivo. | Este archivo pertenece al estudio {valor}, no al estudio {esperado}. Fue rechazado. | Archivo original y código encontrado. | tests/test_ingesta.py::test_archivo_de_otro_estudio |
| RC05 | Versión del diseño incompatible | La versión del diseño del archivo no existe, no es la seleccionada o su huella no coincide con la versión aprobada. | Archivo / _control | version_diseno inexistente o distinta, o huella_diseno ≠ huella aprobada | Versión | bloquea_archivo | Rechazar el archivo. | El archivo corresponde a la versión {valor} del diseño, pero se esperaba la versión {esperado}. Fue rechazado para no mezclar diseños. | Archivo original, versión y huella encontradas. | tests/test_ingesta.py::test_version_incompatible |
| RC06 | Columnas o unidades inconsistentes | Falta una columna de la plantilla o su encabezado (incluida la unidad entre corchetes) fue modificado. | Hoja / encabezados | Encabezado esperado no encontrado en la fila 1 | Estructura / unidades | bloquea_archivo | Rechazar el archivo. | No se encontró la columna «{esperado}» en la hoja {hoja}. Si cambiaste un encabezado o una unidad, usa la plantilla original. | Archivo original y encabezados encontrados. | tests/test_ingesta.py::test_unidad_modificada_en_encabezado |
| RC07 | Columna no prevista | El archivo tiene una columna adicional que no forma parte de la plantilla. | Hoja / encabezados | Encabezado no previsto en la fila 1 | Estructura | advertencia | Ignorar la columna en la preparación; se conserva en el archivo original. | La columna «{valor}» de la hoja {hoja} no es parte de la plantilla y no se usará. Se conserva en el archivo original. | Nombre y posición de la columna. | tests/test_ingesta.py::test_columna_adicional_advierte |
| RC08 | Identificador desconocido | La fila tiene un identificador que no corresponde a ninguna medición o registro planificado. | Registro | ID no existe en el plan aprobado | Correspondencia | excluye_registro | Excluir del conjunto preparado con motivo automático. | La fila {fila} de la hoja {hoja} tiene el identificador «{valor}», que no está planificado. Se excluyó del conjunto preparado. | Fila completa original, ubicación y motivo. | tests/test_calidad.py::test_identificador_desconocido_se_excluye |
| RC09 | Fila sin identificador | La fila tiene datos pero no tiene identificador de medición. | Registro | ID vacío y al menos una celda con contenido | Correspondencia | excluye_registro | Excluir del conjunto preparado con motivo automático. | La fila {fila} de la hoja {hoja} tiene datos pero no tiene identificador. Se excluyó del conjunto preparado. | Fila completa original y ubicación. | tests/test_calidad.py::test_fila_sin_identificador_se_excluye |
| RC10 | Registro duplicado | El mismo identificador aparece en más de una fila. | Registro | ID repetido en la hoja | Duplicidad | pendiente | Dejar pendientes todas las filas con ese ID; no se elige ninguna automáticamente. | La medición {medicion} aparece {valor} veces (filas {esperado}). Se conservaron los originales y quedó pendiente de revisar. | Todas las filas originales duplicadas. | tests/test_calidad.py::test_registros_duplicados_quedan_pendientes |
| RC11 | Medición planificada ausente | Una medición del plan no aparece en el archivo. | Archivo / plan | ID planificado no encontrado | Completitud | advertencia | Informar; la medición no forma parte del conjunto preparado. | La medición planificada {medicion} no está en el archivo. | Lista de mediciones ausentes. | tests/test_calidad.py::test_medicion_planificada_ausente |
| RC12 | Cantidad de registros distinta de la planificada | El número de filas recibidas no coincide con el número de mediciones planificadas. | Archivo / plan | filas con ID ≠ mediciones planificadas | Completitud | advertencia | Informar. | Se recibieron {valor} filas y se planificaron {esperado} mediciones. | Conteos. | tests/test_calidad.py::test_medicion_planificada_ausente |
| RC13 | Planificación modificada | Una celda gris (completada por el sistema) no coincide con el plan aprobado. | Registro / celda | Valor de columna del sistema ≠ valor planificado | Cambio no autorizado | pendiente | Dejar pendiente; los cambios de ejecución se registran en las columnas «real» con su motivo. | La medición {medicion} tiene «{valor}» en {columna} ({celda}), pero el plan aprobado indica «{esperado}». El registro quedó pendiente. | Valor encontrado, valor planificado y ubicación. | tests/test_calidad.py::test_planificacion_modificada |
| RC14 | Medición sin datos | La medición no tiene ningún dato experimental registrado. | Registro | Todas las columnas de datos y resultados directos vacías | Completitud | pendiente | Dejar pendiente; no se imputa ni se reemplaza por cero. | La medición {medicion} (hoja {hoja}, fila {fila}) no tiene datos registrados. Quedó pendiente y no se incorporó al conjunto preparado. | Fila original. | tests/test_calidad.py::test_valores_faltantes_obligatorios |
| RC15 | Dato obligatorio faltante | Un dato marcado como obligatorio está vacío. | Registro / celda | Celda vacía en columna obligatoria | Completitud | pendiente | Dejar pendiente; no se imputa ni se reemplaza por cero. | La medición {medicion} tiene un valor obligatorio sin diligenciar («{columna}») en la hoja {hoja}, fila {fila} ({celda}). Este registro quedó pendiente y no se incorporó al conjunto preparado. | Ubicación de la celda vacía. | tests/test_calidad.py::test_valores_faltantes_obligatorios |
| RC16 | Valor no interpretable | El valor no corresponde al tipo de dato configurado y ninguna transformación autorizada permite interpretarlo. | Registro / celda | Tipo incompatible (texto en campo numérico, decimal en entero, fecha inválida…) | Tipo de dato | pendiente | Dejar pendiente; el valor original se conserva sin cambios. | La medición {medicion} tiene «{valor}» en «{columna}» ({celda}), que no es un {esperado} válido. El registro quedó pendiente. | Valor original y ubicación. | tests/test_calidad.py::test_tipo_de_dato_incompatible |
| RC17 | Recurso no registrado | El técnico o el patrón real no existe en el catálogo del estudio. | Registro / celda | Código no encontrado en el catálogo | Identificación | pendiente | Dejar pendiente. | La medición {medicion} indica «{valor}» en «{columna}» ({celda}), que no está en el catálogo del estudio. El registro quedó pendiente. | Valor original y ubicación. | tests/test_calidad.py::test_recurso_no_registrado |
| RC18 | Cambio sin motivo | El técnico o el patrón real es distinto del previsto y no se escribió el motivo del cambio (X03). | Registro | real ≠ previsto y motivo vacío | Desviación del plan | advertencia | Conservar el registro e informar. | En la medición {medicion} cambió {columna} (previsto «{esperado}», real «{valor}») sin motivo registrado. | Valores previsto y real. | tests/test_calidad.py::test_cambio_sin_motivo_advierte |
| RC19 | Hora no interpretable | La hora real no tiene el formato HH:MM. | Registro / celda | No coincide con HH:MM o HH:MM:SS | Formato | advertencia | Conservar el registro e informar. | La hora «{valor}» de la medición {medicion} ({celda}) no tiene el formato HH:MM. | Valor original. | tests/test_calidad.py::test_hora_invalida_advierte |
| RC20 | Resultado directo sin valor | Un registro de resultado agrupado no tiene valor. | Registro de resultado | Celda «Valor» vacía | Completitud | pendiente | Dejar pendiente; no se imputa. | El registro {medicion} («{columna}») de la hoja {hoja}, fila {fila}, no tiene valor. Quedó pendiente. | Ubicación. | tests/test_calidad.py::test_resultados_agrupados |

## Transformaciones autorizables

Ninguna cambia el valor, el signo, las cifras ni la unidad. Cada aplicación se registra con la celda, el valor original y el valor interpretado.

| Código | Nombre | Descripción | Ejemplo | Autorizada por defecto |
| --- | --- | --- | --- | --- |
| TR01 | Leer números escritos como texto | Interpreta como número un texto que ya está escrito con punto decimal (o una fecha ISO escrita como texto). El valor no cambia. | «20.013» (texto) → 20.013 | True |
| TR02 | Coma decimal → punto decimal | Interpreta «20,013» como 20.013. Solo para textos con una única coma y sin separador de miles. | «20,013» → 20.013 | False |
| TR03 | Quitar espacios al inicio y al final | Elimina espacios sobrantes alrededor de textos y códigos. | « T-01 » → «T-01» | True |
| TR04 | Unificar mayúsculas de códigos de recursos | Escribe el código de técnico o patrón como está en el catálogo cuando solo difiere en mayúsculas. | «t-01» → «T-01» | False |

## Reglas que se decidió no implementar

| Regla | Motivo |
| --- | --- |
| Valores extremos o atípicos | La identificación de atípicos es una decisión estadística del motor; aquí no se marca ni elimina ningún valor por ser extremo. |
| Coherencia entre unidades de variables | Las unidades se fijan en la configuración y viajan en el encabezado; no se convierten unidades sin una regla explícita. |
| Fecha real fuera del periodo planificado | No hay un criterio aprobado; se registra la fecha real sin evaluarla. |

## Estados de un registro

| Estado | Significado | ¿Entra al conjunto preparado? |
| --- | --- | --- |
| aceptado | Superó todas las reglas sin transformaciones | Sí |
| normalizado | Superó las reglas tras una transformación autorizada | Sí |
| con_advertencia | Tiene advertencias, sin errores | Sí |
| pendiente | Tiene al menos un error de registro; requiere corrección | No |
| excluido | Excluido con motivo (automático o manual documentado) | No |
| rechazado | El archivo completo fue rechazado | No |

Precedencia: excluido > pendiente > con_advertencia > normalizado > aceptado. Conciliación: recibidos = aceptados + normalizados + con advertencia + pendientes + excluidos + rechazados.
