# Estado del desarrollo

Comprobado el 2026-11-01 con 86 pruebas automatizadas (todas aprobadas), pruebas de humo de cada página y recorrido real en navegador, incluida la carga de un archivo con errores sembrados.

## Terminado y comprobado

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
| 7 · Pruebas | 86 pruebas, también en GitHub Actions | `07_pruebas.md` |
| 8 · Documentación | Insumos técnicos en `docs/` (4 generados desde el código) | — |

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
| Cálculo de resultados derivados, motor estadístico (S01) | Fase posterior (PD08, PD14) |
| Informe técnico (S02, S03) | Fase posterior (PD19) |
| Validar el lenguaje con un usuario del laboratorio | PD16 |

## Para construir tus 4 conjuntos controlados

1. Configura el estudio con el diseño real de tus escenarios y apruébalo.
2. Descarga la plantilla, una sola vez.
3. Diligencia cuatro copias: a mano o por código con `src.plantillas.diligenciar.diligenciar_plantilla` (ver `ejemplos/flujo_completo.py`).
4. Carga cada archivo, revisa la calidad, prepara y aprueba cada conjunto.
5. El motor leerá cada ZIP con `cargar_conjunto()`.
