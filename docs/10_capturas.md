# Capturas de la aplicación

Son capturas reales de la aplicación en ejecución (`streamlit run app.py`), tomadas automáticamente con Chromium/Playwright a 1440 px de ancho y con datos **sintéticos**. En el entorno donde se tomaron no estaba disponible la fuente web «Plus Jakarta Sans», así que se ve la fuente sans-serif de respaldo. En tu equipo, con internet, se carga la fuente del tema.

| Captura | Qué muestra |
| --- | --- |
| ![Asistente · magnitudes](capturas/asistente_04_magnitudes.png) | **Asistente «Crear estudio» (panel lateral) · Magnitudes.** Se abre con el botón «Crear estudio». Muestra el paso actual con barra de progreso y salto a cualquier paso. Pregunta cuántas magnitudes intervienen y, para cada una, nombre, unidad e intervalo de trabajo. Cada «Guardar y continuar» guarda el borrador. |
| ![Asistente · IBC](capturas/asistente_06_ibc.png) | **Asistente · Equipo a evaluar (IBC).** Código, descripción, marca, modelo, serie, magnitud, resolución e intervalo. |
| ![Asistente · patrones](capturas/asistente_08_patrones.png) | **Asistente · Patrones.** Cuántos son y la descripción de cada uno (identificación, certificado, magnitud e intervalo útil). |
| ![Asistente · resultados](capturas/asistente_11_resultados.png) | **Asistente · Resultados de interés.** Interruptor por resultado (error, corrección, inestabilidad, inhomogeneidad u otro), con su origen, ámbito y dependencias. |
| ![Asistente · mediciones](capturas/asistente_13_mediciones.png) | **Asistente · Mediciones.** Combinación explícita con su conteo (2 puntos × 2 técnicos × 2 repeticiones = 8), vista previa y confirmación obligatoria. |
| ![Asistente · plantilla](capturas/asistente_15_plantilla_generada.png) | **Asistente · Generar plantilla.** Resumen, faltantes y advertencias, aprobación del diseño, descarga del Excel y botón «Siguiente: Subir DB». |
| ![Asistente · subir](capturas/asistente_16_subir_resultado.png) | **Asistente · Subir DB.** Resultado de la carga de la plantilla diligenciada, con un dato obligatorio vacío detectado en su fila y celda. |
| ![Inicio](capturas/01_inicio.png) | **Inicio.** Encabezado, banda de progreso del estudio activo (pasos completados en verde, paso actual en violeta), métricas generales, lista de estudios, accesos rápidos y creación de un estudio de ejemplo. |
| ![Estudios](capturas/02_estudios.png) | **Estudios.** Creación (el código EST-0001 es automático, E02) e identificación (E01–E08) con preguntas sencillas. El término técnico aparece en la ayuda. Pestañas de magnitudes y puntos, recursos y bitácora. |
| ![Diseño](capturas/03_diseno.png) | **Diseño · Condiciones.** Sugerencias (técnico, patrón, día…), una tarjeta por condición con su rol (comparar o solo registrar, D15) y sus opciones. Las condiciones vinculadas toman sus opciones del catálogo de recursos. |
| ![Resultados](capturas/03b_resultados.png) | **Diseño · Resultados de interés.** Cada resultado indica si se escribe o se calcula (V04), su ámbito (V07), sus dependencias (V05), la referencia del cálculo (V06) y si se analiza (V08) o tiene criterio (V09). No se piden fórmulas. |
| ![Plan](capturas/03c_plan.png) | **Diseño · Mediciones planificadas.** Métricas del plan, generador opcional con vista previa y confirmación, importación CSV/Excel y editor fila por fila con listas desplegables. |
| ![Aprobación](capturas/03d_aprobacion.png) | **Diseño · Revisión y aprobación (P05).** Progreso por sección, faltantes y advertencias. La aprobación congela una versión inmutable. |
| ![Plantillas](capturas/04_plantillas.png) | **Plantillas.** Selección de la versión, resumen de columnas (quién completa cada una, cuáles son obligatorias), registros de resultados agrupados, instrucciones y descarga. |
| ![Carga](capturas/05_carga.png) | **Carga de datos.** Elección de la versión y del archivo. Resultado con mensajes agregados, conteos conciliados, cambios frente a la carga anterior (X08), historial con SHA-256 y descarga del original. El archivo de la captura tiene errores sembrados. |
| ![Calidad](capturas/06_calidad.png) | **Calidad de datos.** Interruptores de transformaciones autorizadas, exclusiones con motivo, conteos que se recalculan y tabla de incidencias con regla, tratamiento, mensaje, hoja, fila y celda. |
| ![Datos](capturas/07_datos.png) | **Datos preparados.** Estado de aprobación (X07), conteos, trazabilidad (carga, SHA-256, versión, huella, transformaciones), descargas (ZIP e informe de incidencias), vista previa de cada tabla y ejemplo de lectura desde Python. |
| ![Análisis](capturas/08_analisis.png) | **Análisis estadístico.** Sección reservada: explica qué recibirá el motor y qué no hace esta versión, sin simular cálculos. |
| ![Plantilla Excel](capturas/09_plantilla_excel.png) | **Plantilla Excel (hoja «Mediciones»), diligenciada con errores sembrados.** Gris: columnas del sistema, bloqueadas. Morado oscuro con «*»: datos obligatorios. Morado: columnas del usuario. Se ve el texto «abc» en una celda numérica (M0004) y un valor del patrón vacío (M0010); la carga detecta ambos con su fila y celda. Imagen generada con LibreOffice a partir del archivo real. |

