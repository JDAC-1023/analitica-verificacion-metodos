# Pruebas realizadas

> Generado ejecutando `pytest` el 2026-11-01 13:27 · Python 3.13.18 · Linux · pytest 9.2.0. Resultado: {'Aprobada': 86}.

Todas las pruebas usan **datos sintéticos** (estudio de ejemplo de 16 mediciones: 2 puntos × 2 técnicos × 2 días × 2 repeticiones). La «entrada» y el «resultado esperado» se toman del docstring de cada prueba; el «resultado obtenido» es el de esta ejecución.

| Prueba | Archivo | Entrada | Resultado esperado | Resultado obtenido | Tiempo (s) |
| --- | --- | --- | --- | --- | --- |
| `test_valores_faltantes_obligatorios` | test_calidad.py | M0003 sin «Valor del patrón» (obligatorio); M0004 sin ningún dato; M0005 sin «Temperatura ambiente» (opcional). | M0003 pendiente por RC15 con fila y celda; M0004 pendiente por RC14; M0005 aceptada; nada se reemplaza por cero. | Aprobada | 0.120 |
| `test_tipo_de_dato_incompatible` | test_calidad.py | «abc» en Indicación (decimal) de M0002 y «20,5» (coma decimal) en M0006. | ambos RC16 y pendientes con la configuración por defecto (TR02 no autorizada); el valor original se conserva. | Aprobada | 0.109 |
| `test_identificador_desconocido_se_excluye` | test_calidad.py | el ID de la última fila se cambia por «M9999». | RC08, la fila queda excluida con motivo y M0016 aparece como planificada ausente (RC11). | Aprobada | 0.131 |
| `test_fila_sin_identificador_se_excluye` | test_calidad.py | se agrega una fila con datos pero sin ID de medición. | RC09, la fila se excluye y los conteos siguen conciliados (17 recibidos). | Aprobada | 0.125 |
| `test_registros_duplicados_quedan_pendientes` | test_calidad.py | la fila de M0002 se copia al final (ID duplicado). | RC10 en ambas filas, ambas pendientes y ninguna elegida automáticamente. | Aprobada | 0.184 |
| `test_medicion_planificada_ausente` | test_calidad.py | se borra la fila de M0016 (mediciones previstas ausentes). | RC11 para M0016 y RC12 (15 recibidas frente a 16 planificadas). | Aprobada | 0.126 |
| `test_planificacion_modificada` | test_calidad.py | se cambia el «Técnico previsto» de M0001 (celda gris) por T-02. | RC13 con valor encontrado y valor planificado; registro pendiente. | Aprobada | 0.135 |
| `test_recurso_no_registrado` | test_calidad.py | «Técnico que midió» = T-09 (no existe) con motivo. | RC17 y registro pendiente. | Aprobada | 0.106 |
| `test_cambio_sin_motivo_advierte` | test_calidad.py | M0001 tenía previsto T-01 y la registró T-02 sin motivo. | RC18; el registro se conserva con advertencia e incluido en el conjunto. | Aprobada | 0.103 |
| `test_hora_invalida_advierte` | test_calidad.py | «Hora real» = «9 y media». | RC19 como advertencia. | Aprobada | 0.112 |
| `test_resultados_agrupados` | test_calidad.py | inestabilidad del punto 1 sin valor y del punto 2 con texto «n/a». | RC20 y RC16 en la hoja Resultados_directos; ambos registros pendientes. | Aprobada | 0.131 |
| `test_guardar_y_recuperar_estudio` | test_configuracion.py | estudio creado, configurado con el ejemplo y guardado. | al leerlo de nuevo conserva identificación, recursos, factores, variables, resultados y plan; el código es automático (EST-0001). | Aprobada | 0.003 |
| `test_persistencia_entre_sesiones` | test_configuracion.py | un estudio guardado con una instancia del repositorio; se crea otra instancia sobre la misma carpeta. | la segunda instancia (otra sesión) lista y lee el estudio y su versión aprobada. | Aprobada | 0.004 |
| `test_cantidades_variables_de_recursos_puntos_y_condiciones` | test_configuracion.py | 3 técnicos, 1 patrón, 2 equipos, 5 puntos y 3 condiciones (una numérica). | la configuración es válida sin asumir dos técnicos ni dos patrones. | Aprobada | 0.001 |
| `test_no_se_genera_factorial_automaticamente` | test_configuracion.py | estudio con factores y niveles configurados pero sin filas de plan. | el plan sigue vacío y la revisión exige planificar explícitamente las mediciones. | Aprobada | 0.001 |
| `test_generador_explicito_solo_cruza_lo_elegido` | test_configuracion.py | generador con 2 puntos, cruzando solo «Día» y con técnico fijo T-01. | 2 × 2 × 2 = 8 mediciones; el técnico no se cruza. | Aprobada | 0.001 |
| `test_puntos_distintos_no_son_repeticiones_y_duplicados_se_detectan` | test_configuracion.py | plan con la repetición 1 en dos puntos distintos (válido) y luego una repetición 1 duplicada en la misma condición. | el primer caso no genera error; el segundo informa la repetición duplicada. | Aprobada | 0.001 |
| `test_restriccion_de_combinacion_bloquea` | test_configuracion.py | restricción «T-02 no puede usar P-01» (D11). | las filas que la violan aparecen como error. | Aprobada | 0.001 |
| `test_patron_fuera_de_intervalo_advierte` | test_configuracion.py | patrón con intervalo útil 0–30 °C y un punto de 40 °C. | advertencia de compatibilidad (PD06 pendiente: no bloquea). | Aprobada | 0.001 |
| `test_tabla_editable_ida_y_vuelta` | test_configuracion.py | plan convertido a la tabla del editor y de vuelta. | se obtiene exactamente el mismo plan. | Aprobada | 0.007 |
| `test_importar_plan_csv` | test_configuracion.py | CSV con columnas Punto, Repetición, Técnico, Patrón, Día (sin IDs). | se crean mediciones con IDs nuevos y sin errores de lectura. | Aprobada | 0.005 |
| `test_validaciones_de_configuracion_incompleta` | test_configuracion.py | estudio vacío y un resultado con el mismo nombre que un dato registrado. | la revisión lista lo que falta por etapa y no permite aprobar. | Aprobada | 0.001 |
| `test_versiones_del_diseno` | test_configuracion.py | diseño aprobado (v1), luego modificado (otro punto) y aprobado de nuevo. | al modificar vuelve a borrador; la nueva aprobación crea v2 y v1 se conserva intacta. | Aprobada | 0.007 |
| `test_entorno_preparado` | test_healthcheck.py |  |  | Aprobada | 0.000 |
| `test_lectura_correcta` | test_ingesta.py | plantilla diligenciada completa (16 mediciones y 2 resultados agrupados). | archivo leído, 16 recibidos, 16 aceptados, conteos conciliados, sin incidencias. | Aprobada | 0.105 |
| `test_conservacion_del_archivo_original` | test_ingesta.py | archivo cargado. | el original se guarda byte a byte; su SHA-256 coincide; queda un evento de auditoría con usuario y huella. | Aprobada | 0.150 |
| `test_archivo_no_excel_se_rechaza` | test_ingesta.py | un archivo de texto con extensión .xlsx. | rechazado por RC01 y el original igualmente conservado. | Aprobada | 0.005 |
| `test_hoja_mediciones_ausente_rechaza` | test_ingesta.py | archivo sin la hoja Mediciones (archivo incompleto). | rechazado por RC02. | Aprobada | 0.172 |
| `test_formato_de_plantilla_incompatible` | test_ingesta.py | _control con formato_plantilla = PLT-0.9. | rechazado por RC03. | Aprobada | 0.139 |
| `test_archivo_de_otro_estudio` | test_ingesta.py | archivo del estudio EST-0001 cargado en otro estudio. | rechazado por RC04. | Aprobada | 0.116 |
| `test_version_incompatible` | test_ingesta.py | plantilla de la versión 1; el diseño se modifica y se aprueba la versión 2; se carga esperando la versión 2. | rechazado por RC05. Además, una huella alterada también se rechaza. | Aprobada | 0.139 |
| `test_unidad_modificada_en_encabezado` | test_ingesta.py | el encabezado «Indicación del equipo [°C]» se cambia a «Indicación del equipo [K]». | rechazado por RC06 (campos o unidades inconsistentes). | Aprobada | 0.135 |
| `test_columna_adicional_advierte` | test_ingesta.py | el usuario agrega una columna «Notas extra». | el archivo se lee, se informa RC07 y los registros se aceptan. | Aprobada | 0.145 |
| `test_plantilla_reordenada_se_lee` | test_ingesta.py | el usuario ordena las filas de Mediciones de forma descendente. | las mediciones se identifican por su ID y no por su posición: 16 aceptadas. | Aprobada | 0.208 |
| `test_pagina_sin_errores[inicio]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.507 |
| `test_pagina_sin_errores[asistente]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.317 |
| `test_pagina_sin_errores[estudios]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.357 |
| `test_pagina_sin_errores[diseno]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.402 |
| `test_pagina_sin_errores[plantillas]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.554 |
| `test_pagina_sin_errores[carga]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.387 |
| `test_pagina_sin_errores[calidad]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.343 |
| `test_pagina_sin_errores[datos]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.307 |
| `test_pagina_sin_errores[analisis]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.317 |
| `test_pagina_sin_errores[informes]` | test_interfaz.py | estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo. | la página se ejecuta sin excepciones. | Aprobada | 0.409 |
| `test_crear_estudio_desde_la_interfaz` | test_interfaz.py | aplicación vacía; el usuario escribe su nombre y crea un estudio desde la página Estudios. | el estudio queda guardado (EST-0001) y seleccionado como estudio activo. | Aprobada | 0.214 |
| `test_pasos_del_asistente[False-1]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.319 |
| `test_pasos_del_asistente[False-2]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.334 |
| `test_pasos_del_asistente[False-3]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.394 |
| `test_pasos_del_asistente[False-4]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.314 |
| `test_pasos_del_asistente[False-5]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.339 |
| `test_pasos_del_asistente[False-6]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.364 |
| `test_pasos_del_asistente[False-7]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.313 |
| `test_pasos_del_asistente[False-8]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.289 |
| `test_pasos_del_asistente[False-9]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.313 |
| `test_pasos_del_asistente[False-10]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.356 |
| `test_pasos_del_asistente[False-11]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.321 |
| `test_pasos_del_asistente[False-12]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.341 |
| `test_pasos_del_asistente[False-13]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.512 |
| `test_pasos_del_asistente[False-14]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.328 |
| `test_pasos_del_asistente[True-1]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.363 |
| `test_pasos_del_asistente[True-2]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.302 |
| `test_pasos_del_asistente[True-3]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.328 |
| `test_pasos_del_asistente[True-4]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.390 |
| `test_pasos_del_asistente[True-5]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.374 |
| `test_pasos_del_asistente[True-6]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.306 |
| `test_pasos_del_asistente[True-7]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.313 |
| `test_pasos_del_asistente[True-8]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.276 |
| `test_pasos_del_asistente[True-9]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.300 |
| `test_pasos_del_asistente[True-10]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.312 |
| `test_pasos_del_asistente[True-11]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.315 |
| `test_pasos_del_asistente[True-12]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.417 |
| `test_pasos_del_asistente[True-13]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.314 |
| `test_pasos_del_asistente[True-14]` | test_interfaz.py | asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío. | cada paso se dibuja sin errores. | Aprobada | 0.306 |
| `test_asistente_avanza_y_guarda` | test_interfaz.py | estudio nuevo; en el paso 1 se escribe el nombre y se pulsa «Guardar y continuar»; en el paso 2 se pulsa sin completar el método. | el paso 1 se guarda y avanza al 2; en el 2 aparece el error y no avanza. | Aprobada | 0.329 |
| `test_plantilla_coherente_con_el_diseno` | test_plantilla.py | diseño aprobado de 16 mediciones con 3 datos, 1 resultado calculado y 1 resultado directo por punto. | hoja Mediciones con 16 filas en el orden del plan; columnas de datos con unidad; sin columna «Resultado»; el resultado calculado no tiene columna; hoja Resultados_directos con un registro por punto. | Aprobada | 0.075 |
| `test_metadatos_de_control_y_proteccion` | test_plantilla.py | plantilla generada. | _control oculta con estudio, versión, huella y columnas; hojas protegidas; celdas del usuario desbloqueadas; lista de selección para el técnico real. | Aprobada | 0.075 |
| `test_columna_para_resultado_directo_por_medicion` | test_plantilla.py | se agrega un resultado directo de ámbito «medición» y se aprueba una nueva versión. | la plantilla incluye una columna propia para ese resultado en Mediciones. | Aprobada | 0.087 |
| `test_transformaciones_permitidas` | test_preparacion.py | «20,5» con coma decimal y « 20.25 » (texto con espacios) en Indicación; preparación con TR01, TR02 y TR03. | ambos registros normalizados; valores 20.5 y 20.25; se conservan el original y la transformación aplicada. | Aprobada | 0.212 |
| `test_exclusion_documentada` | test_preparacion.py | exclusión manual de M0007 con motivo; luego un intento sin motivo. | M0007 fuera del conjunto y listada en exclusiones.csv con su motivo; sin motivo se rechaza la preparación. | Aprobada | 0.220 |
| `test_valores_sin_redondeo_ni_cambio_de_signo` | test_preparacion.py | valores con 12 decimales y negativos (−1.234567890123). | el conjunto preparado conserva exactamente el valor y el signo; los faltantes opcionales quedan vacíos, no en cero. | Aprobada | 0.319 |
| `test_exportacion_del_conjunto_preparado` | test_preparacion.py | preparación de un archivo completo. | ZIP con las tablas documentadas; 16 mediciones; 48 valores (16 × 3 datos); manifiesto con conteos y huellas; la vista de análisis tiene una columna por condición. | Aprobada | 0.214 |
| `test_reproducibilidad_de_la_salida` | test_preparacion.py | la misma carga se prepara dos veces con los mismos parámetros. | las huellas SHA-256 de todos los CSV son idénticas (salida reproducible). | Aprobada | 0.248 |
| `test_integridad_detecta_modificacion` | test_preparacion.py | se altera valores.csv dentro del ZIP preparado. | la lectura con verificación detecta que el conjunto fue modificado. | Aprobada | 0.190 |
| `test_segunda_carga_registra_cambios` | test_preparacion.py | primera carga con M0003 sin valor del patrón; segunda carga corregida. | la segunda carga referencia a la primera, lista la celda que cambió y no borra la primera carga. | Aprobada | 0.148 |
| `test_aprobacion_del_conjunto` | test_preparacion.py | conjunto preparado aprobado por «ana». | queda marcado como aprobado con usuario y fecha, y se registra el evento. | Aprobada | 0.175 |
| `test_archivo_rechazado_no_se_prepara` | test_preparacion.py | carga rechazada (archivo no Excel). | la preparación se niega con un mensaje claro. | Aprobada | 0.004 |

## Cobertura de los casos solicitados

| Caso solicitado | Prueba(s) |
| --- | --- |
| Configuración y guardado de un estudio | test_guardar_y_recuperar_estudio |
| Cantidades variables de técnicos, patrones, puntos y condiciones | test_cantidades_variables_de_recursos_puntos_y_condiciones |
| Plantilla coherente con el diseño | test_plantilla_coherente_con_el_diseno, test_metadatos_de_control_y_proteccion |
| Lectura correcta de la plantilla | test_lectura_correcta, test_plantilla_reordenada_se_lee |
| Archivo incompleto | test_hoja_mediciones_ausente_rechaza, test_archivo_no_excel_se_rechaza |
| Valores faltantes | test_valores_faltantes_obligatorios |
| Tipos de dato incompatibles | test_tipo_de_dato_incompatible |
| Identificadores desconocidos | test_identificador_desconocido_se_excluye, test_fila_sin_identificador_se_excluye |
| Mediciones previstas ausentes | test_medicion_planificada_ausente |
| Registros duplicados | test_registros_duplicados_quedan_pendientes |
| Versiones incompatibles | test_version_incompatible, test_archivo_de_otro_estudio, test_formato_de_plantilla_incompatible |
| Transformaciones permitidas | test_transformaciones_permitidas |
| Exclusiones documentadas | test_exclusion_documentada |
| Conservación del archivo original | test_conservacion_del_archivo_original |
| Exportación del conjunto preparado | test_exportacion_del_conjunto_preparado |
| Reproducibilidad de la salida | test_reproducibilidad_de_la_salida, test_integridad_detecta_modificacion |
| Persistencia entre sesiones | test_persistencia_entre_sesiones |

## Limitaciones de las pruebas

- Las pruebas de interfaz (`test_interfaz.py`) comprueban que cada página se ejecuta sin errores y que se puede crear un estudio; no evalúan la apariencia. La apariencia se revisó con capturas reales (`10_capturas.md`).
- La compatibilidad con Excel se comprobó leyendo y escribiendo los archivos con openpyxl; abrir la plantilla en Microsoft Excel para Windows debe verificarse manualmente (validaciones de celda, protección y listas).
- No se probaron archivos reales del laboratorio: solo datos sintéticos.
