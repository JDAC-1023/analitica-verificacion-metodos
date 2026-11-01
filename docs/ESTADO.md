# Estado del desarrollo

Comprobado el 2026-11-01 con 126 pruebas automatizadas (todas aprobadas), pruebas de humo de cada página, instalación limpia en un entorno nuevo y recorrido real en navegador (incluidos el análisis y la emisión del PDF).

## Terminado y comprobado

**Motor estadístico (nuevo):** determinista, por reglas RM-01…RM-22. Etapas: limpieza (faltantes vs plan, estructura n_ij), atípicos (ISO 5725-2:1994: Mandel, Cochran, Grubbs solo interlaboratorio; Grubbs por celda intralaboratorio), normalidad (objeto según el procedimiento), desempeño (sesgo t/Wilcoxon, s_r, s_I por ANOVA, s_R interlaboratorio) y evaluación frente a criterios aprobados. Reproduce el anexo B.1 de la norma. Cada decisión queda en un árbol pregunta → respuesta → evidencia → regla, visible en tiempo real mientras se configura.

**Conclusiones, comentarios, versión 2 e informe (nuevo):** conclusiones automáticas por etapa; comentarios por etapa guardados con usuario y fecha; versiones derivadas inmutables con motivo y diferencias; exclusión con motivo y responsable; clonar estudio; informe PDF con control (fecha, elaboró, revisó, autorizó), marco teórico APA, resultados, gráficos, comentarios, bitácora, referencias y anexos. Ver `11`–`13` en docs.

**Asistente «Crear estudio»:** es un panel lateral flotante que también se puede abrir a pantalla completa. Guía en 14 pasos con «Guardar y continuar»: estudio y tipo (verificación o validación) → método → magnitudes → puntos → equipo a evaluar (IBC) → técnicos → patrones → condiciones → datos a registrar → resultados de interés → criterios → mediciones → generar plantilla → subir DB. Cada paso se guarda como borrador y el asistente reabre donde quedaste. Se comprobó con un recorrido completo en el navegador y con pruebas automáticas de cada paso.

| Etapa | Funcionalidad | Cómo se comprobó |
| --- | --- | --- |
| 1 · Diseño | Interpretación de la matriz, modelo, diccionario, arquitectura | `00`–`03` en docs |
| 2 · Configuración | Estudio (E01–E08), magnitudes y puntos (E09–E11), recursos en cantidad variable (R01–R04), condiciones con rol y opciones (D03–D06, D15), repeticiones (D07), unidad experimental (D08), restricciones (D11), datos a registrar (D12–D14), resultados de interés (V01–V10), criterios sin valores por defecto (C01–C03) | test_configuracion, test_interfaz |
| 2 · Planificación | Editor fila por fila, importación CSV/Excel y generador explícito con vista previa y confirmación. Valida repeticiones (los puntos distintos nunca son repeticiones), recursos, restricciones y compatibilidad patrón-punto (advierte) | test_configuracion |
| 2 · Versiones | Aprobación (P05) que congela versiones inmutables con huella. Editar devuelve a borrador | test_versiones_del_diseno |
| 3 · Plantilla | Excel parametrizado: hojas, colores por origen, validaciones de celda, protección, metadatos ocultos, resultados agrupados en hoja propia, sin columna «resultado» | test_plantilla + revisión visual con LibreOffice |
| 4 · Ingesta | Conservación del original y su SHA-256. Identificación de estudio, versión y huella. Columnas por encabezado (tolera reordenar filas). Historial de cargas con diferencias | test_ingesta |
| 5 · Calidad | 20 reglas, estados por registro, conteos conciliados, mensajes con hoja, fila y celda, 4 transformaciones autorizables, exclusiones con motivo, informe de incidencias en Excel | test_calidad, test_preparacion |
| 6 · Exportación | ZIP SAL-1.0 con tablas normalizadas, manifiesto con huellas, salida reproducible byte a byte, lector Python que verifica integridad, aprobación del conjunto (X07) | test_preparacion, ejemplos/ |
| 7 · Pruebas | 126 pruebas, también en GitHub Actions | `07_pruebas.md` |
| 9 · Motor | Etapas, reglas, tablas ISO verificadas contra fórmula, anexo B.1, 4 escenarios y casos adversos | test_motor |
| 10 · Informe | Versionado, comentarios, clonación, PDF leído en la prueba | test_analisis_servicio, test_interfaz |
| 8 · Documentación | Insumos técnicos en `docs/` (4 generados desde el código) | — |

**Testeos, limpieza y lenguaje sencillo (3.2):** Testeo 1–4 se crean solos al abrir la app desde `data/estudios_prueba/` (una vez por carpeta de datos). Reporte de limpieza en pantalla y en PDF: pasos, 20 reglas con sus hallazgos, transformaciones autorizadas y aplicadas, exclusiones, lo que nunca se hace y herramientas. Cada prueba explica en palabras sencillas qué hace y por qué se aplicó o no (`src/motor/lenguaje.py`). Informe PDF con portada, resumen para todos, gráficos de resumen y tablas con color.

**Versión 4.0:** selección de estudios con tarjetas en Inicio y panel integrado; bases de prueba con 5 lecturas por serie y errores sembrados (240 mediciones, 4 escenarios con su resultado esperado comprobado en `test_crear_estudios_de_prueba`); ANOVA factorial de fuentes de variación (técnico, patrón, interacción) con contribución porcentual, medias por factor y gráfico de combinaciones; revisión de réplicas por serie frente al plan; parámetros de las pruebas de hipótesis fijos (RM-24) y solo límites de aceptación configurables; «cumple con observaciones» cuando se rechaza la normalidad (RM-25); informe con tabla de significado metrológico y «qué se compara» en cada etapa.

**Versión 5.1 (árbol corregido):** con datos no normales ya no se aplica ningún ANOVA: ni ANOVA clásico, ni de Welch, ni prueba F de s_I, ni intervalos χ²; la comparación va directo a Kruskal-Wallis + Dunn-Holm y la homocedasticidad (Bartlett) solo se evalúa —y solo decide— cuando hay normalidad (Fligner-Killeen queda como dato informativo). Árbol en `diagramas/arbol_decision.png`.

**Versión 5.0 (flujo condicional):** el motor sigue un flujo paso a paso determinista: datos → ¿atípicos? (si sí, sensibilidad: qué cambiaría sin ellos) → ¿normalidad? → ¿homocedasticidad? (Bartlett, solo con normalidad) → prueba según la ruta (ANOVA + Tukey, Welch + Games-Howell o Kruskal-Wallis + Dunn) con el lugar exacto de cada diferencia y su origen probable → sesgo (t o Wilcoxon) → repetibilidad → reproducibilidad intralaboratorio → veredicto «tu método sirve / no sirve / sirve con observaciones», con qué implica cada incumplimiento y qué hacer, y el desempeño punto por punto. La reproducibilidad intralaboratorio (precisión intermedia) se mide y evalúa; la interlaboratorio solo con varios laboratorios.

## Funciona con limitaciones conocidas

- **Persistencia local** (archivos en `datos_locales/`). Sirve entre sesiones y reinicios en el mismo equipo. **No** se comparte entre Jessica y Juan David ni sobrevive en Streamlit Community Cloud (su disco se borra al reiniciar). Por eso Supabase es el siguiente paso de infraestructura.
- **Sin autenticación:** el usuario se identifica escribiendo su nombre, que queda en la bitácora.
- **Varias magnitudes con el mismo dato:** cada dato tiene una unidad fija (PD02). Ver `00_interpretacion_matriz.md`.
- **Excel:** probado con openpyxl y LibreOffice. Falta abrir la plantilla en Microsoft Excel para Windows y confirmar las validaciones, la protección y las listas.
- La fuente tipográfica del tema se descarga de Google Fonts. Sin internet se usa una fuente sans-serif.

## Pendiente (delimitado, no simulado)

| Pendiente | Motivo |
| --- | --- |
| Adaptador Supabase (`RepositorioSupabase`) | Requiere aprobar el modelo (PD15) y crear el proyecto. El contrato `Repositorio` ya define los métodos |
| R05 disponibilidad y cronograma automático (D10) | «Por definir» en la matriz |
| Otras derivaciones además de «a − b» | Requieren la fórmula aprobada por el laboratorio (PD08) |
| Linealidad, LOD/LOQ, selectividad, robustez, incertidumbre | NO_IMPLEMENTADO en el motor; se informan así si se marcan como requeridas |
| IC de s_R; separación de componentes con varios factores de precisión intermedia | Limitación declarada en cada resultado |
| Firma electrónica del informe | Hoy: nombres y líneas de firma en el PDF, huella SHA-256 en la bitácora |
| Validar el lenguaje con un usuario del laboratorio | PD16 |

## Para construir tus 4 conjuntos controlados

1. Configura el estudio con el diseño real de tus escenarios y apruébalo.
2. Descarga la plantilla, una sola vez.
3. Diligencia cuatro copias: a mano o por código con `src.plantillas.diligenciar.diligenciar_plantilla` (ver `ejemplos/flujo_completo.py`).
4. Carga cada archivo, revisa la calidad, prepara y aprueba cada conjunto.
5. En **Análisis estadístico** configura el objeto, las características, la referencia y los criterios, ejecuta y emite el informe.
