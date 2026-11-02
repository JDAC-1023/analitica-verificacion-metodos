# Capturas de la aplicación

> Capturas reales tomadas el 2026-11-01 con la versión 5.1, en el navegador (Chromium, 1440 × 1000), sobre una base de datos
> recién creada: al abrir la aplicación se cargaron solos Testeo 1–4 (`data/estudios_prueba/`). Las pantallas del análisis
> corresponden al **Testeo 4** (datos no normales · cumple con observaciones), que muestra las tres rutas de comparación. Los datos son sintéticos.

## 1. Elegir el estudio y su panel

| Captura | Qué muestra |
| --- | --- |
| ![Inicio](capturas/01_inicio_tarjetas.png) | **Inicio · elegir estudio.** Buscador y una tarjeta por estudio con código, tipo, método, número de mediciones y etiquetas de estado (diseño, datos, veredicto). «Nuevo estudio» abre el asistente. Ya no hay selector en la barra lateral. |
| ![Panel resumen](capturas/02_panel_resumen.png) | **Panel del estudio · Resumen.** Encabezado del estudio, «Cambiar de estudio», banda de progreso, métricas, veredicto («Tu método no sirve (todavía)») con lo que implica cada incumplimiento, y el siguiente paso. |
| ![Panel configuración](capturas/02b_panel_configuracion.png) | **Panel · Configuración.** Ficha del estudio (puntos, IBC, técnicos, patrones, condiciones, lecturas por serie, datos y resultados) con acceso al asistente y al diseño. |
| ![Panel datos](capturas/02c_panel_datos.png) | **Panel · Datos.** Filas recibidas, que pasan al análisis, normalizadas, pendientes y con advertencia; accesos a Subir DB, Calidad y Datos preparados. |
| ![Panel resultados](capturas/02d_panel_resultados.png) | **Panel · Resultados.** Decisión por característica y gráficos de sesgo y precisión por punto. |
| ![Asistente](capturas/16_asistente.png) | **Asistente «Crear estudio».** Panel lateral paso a paso (14 pasos) con «Guardar y continuar»; reabre en el último paso guardado. |

## 2. Datos: carga, calidad y limpieza

| Captura | Qué muestra |
| --- | --- |
| ![Plantilla Excel](capturas/19_plantilla_excel.png) | **Plantilla Excel diligenciada (Testeo 3).** Gris: columnas del sistema; morado: columnas del usuario. En M0007 se ve el error sembrado «-80,048» (texto con coma decimal). Imagen generada con LibreOffice desde el archivo real. |
| ![Carga](capturas/06_carga.png) | **Subir DB.** Elección de versión y archivo, historial de cargas con SHA-256 y descarga del original. |
| ![Calidad](capturas/07_calidad.png) | **Calidad de datos.** Transformaciones autorizadas (TR01–TR04), exclusiones con motivo, conteos e incidencias (dato obligatorio vacío, hora no válida) con hoja, fila y celda. |
| ![Datos preparados](capturas/08_datos_preparados.png) | **Datos preparados.** Conjunto aprobado, conteos conciliados, trazabilidad y botón «Siguiente: Análisis estadístico». |
| ![Reporte de limpieza](capturas/08b_reporte_limpieza.png) | **Reporte de limpieza.** Los 7 pasos (recepción → aprobación), las 20 reglas aplicadas con sus hallazgos, las herramientas de limpieza autorizadas y cuántas veces se usaron, y lo que la limpieza nunca hace. Se descarga en PDF. |

## 3. Análisis estadístico

| Captura | Qué muestra |
| --- | --- |
| ![Configurar](capturas/09_analisis_configurar.png) | **Configurar · qué resultados se evalúan.** Varios resultados a la vez (Corrección, Inestabilidad, Inhomogeneidad); cada uno corre todas las pruebas por separado. La versión ejecutada queda bloqueada (inmutable). |
| ![Límites](capturas/09b_limites_reglas_fijas.png) | **Límites de aceptación y reglas fijas.** Lo único configurable son los límites (sesgo, repetibilidad, reproducibilidad intralaboratorio e interlaboratorio) con su fuente y aprobación. α = 0,05, 95 %, Shapiro-Wilk y tablas ISO son fijos (RM-24). |
| ![Vista previa](capturas/09c_vista_previa.png) | **Qué va a hacer el motor (en vivo).** Por etapa, cada prueba con «se aplicó / no corresponde / faltan datos» y el porqué en palabras sencillas. |
| ![Veredicto](capturas/10_resultados_veredicto.png) | **Veredicto por resultado evaluado.** Tabla con el veredicto de cada resultado (Corrección no sirve; Inestabilidad e Inhomogeneidad sirven) y selector «Ver resultados y conclusiones de:». |
| ![Resultado evaluado](capturas/10g_resultado_evaluado.png) | **Resultados · resultado evaluado.** Título «Resultado evaluado: Corrección (°C)», veredicto, qué implica cada parámetro que no cumple, qué hacer y desempeño punto por punto (✔/✘). |
| ![Paso a paso](capturas/10b_paso_a_paso.png) | **Paso a paso del motor.** Flujo condicional: datos → ¿atípicos? (y qué pasa con ellos) → ¿normales? → ¿varianzas iguales? → prueba elegida → sesgo → repetibilidad → reproducibilidad → veredicto, con «por lo tanto…» en cada paso. |
| ![Atípicos](capturas/10c_atipicos.png) | **Valores atípicos.** Cochran y Mandel «no corresponden» (un solo laboratorio, explicado); Grubbs por serie de 5 lecturas señala las lecturas atípicas, sin borrarlas. |
| ![Homocedasticidad](capturas/10d_homocedasticidad.png) | **Homocedasticidad.** Solo donde los residuos son normales se aplica Bartlett, que decide entre ANOVA clásico y ANOVA de Welch; donde no son normales no se aplica ningún ANOVA (ruta Kruskal-Wallis) y Fligner-Killeen solo informa. |
| ![Fuentes](capturas/10e_fuentes_variacion.png) | **Fuentes de variación.** Por punto, la prueba usada (ANOVA, Welch o Kruskal-Wallis), el valor p y el efecto (% de variación con ANOVA, ε² con Kruskal-Wallis) del técnico, el patrón y su combinación; medias por técnico y por patrón. |
| ![Dónde](capturas/10f_donde_diferencias.png) | **Dónde están las diferencias y por qué.** Comparaciones por pares (Tukey, Games-Howell o Dunn según la ruta), diferencia, p y origen probable. |
| ![Conclusiones](capturas/11_conclusiones.png) | **Conclusiones.** Conclusiones automáticas por etapa, veredicto, implicaciones, mapa por punto, evolución entre versiones y significado metrológico de cada parámetro; caja de comentarios. |
| ![Rediseño](capturas/12_rediseno.png) | **Rediseño / versión 2.** Versión derivada con motivo obligatorio y exclusiones con motivo técnico y responsable; clonación del estudio. |
| ![Informe PDF](capturas/13_informe_pdf.png) | **Informe PDF.** Fecha de emisión, elaboró, revisó y autorizó; el informe queda guardado con su SHA-256. |
| ![Historial](capturas/14_historial.png) | **Historial y bitácora.** Versiones del análisis con su padre y diferencias, y la bitácora de auditoría. |
| ![Informes](capturas/15_informes.png) | **Informes emitidos.** Lista con firmantes, SHA-256 y descarga. |

## 4. Árbol de decisión

![Árbol de decisión](diagramas/arbol_decision.png)

## 5. Informe técnico y reporte de limpieza (PDF)

| Captura | Qué muestra |
| --- | --- |
| ![Portada](capturas/17_pdf_portada.png) | **Portada.** Conclusión consolidada, datos de control y firmas (elaboró, revisó, autorizó). |
| ![Paso a paso PDF](capturas/17b_pdf_paso_a_paso.png) | **Resumen en lenguaje sencillo.** Veredicto y tabla «Paso a paso del motor» (qué se encontró → por lo tanto). |
| ![Fuentes PDF](capturas/17c_pdf_fuentes.png) | **Fuentes de variación en el informe.** Tabla por punto, dónde están las diferencias y medias por técnico y patrón. |
| ![Limpieza PDF](capturas/18_pdf_limpieza.png) | **Reporte de limpieza · portada y pasos.** |
| ![Reglas PDF](capturas/18b_pdf_limpieza_reglas.png) | **Reporte de limpieza · reglas y herramientas.** |
