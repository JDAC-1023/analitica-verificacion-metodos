# Bases de prueba del motor (datos sintéticos)

Se cargan **solas** en la base de datos local al abrir la aplicación (Testeo 1–4), siguiendo exactamente el
mismo flujo que un usuario: crear estudio → diseño → aprobar → plantilla → diligenciar → cargar → calidad →
preparar (TR01–TR04 autorizadas) → aprobar datos → configurar y ejecutar el análisis.

| Estudio | Archivo | Escenario | Resultado esperado del motor |
| --- | --- | --- | --- |
| Testeo 1 | 01_Normal_No_Cumple.xlsx | normal · no cumple (sesgo ≈ 0,25 °C, efecto del técnico) | NO CUMPLE; el técnico influye |
| Testeo 2 | 02_Normal_Cumple.xlsx | normal · cumple | CUMPLE |
| Testeo 3 | 03_No_Normal_No_Cumple.xlsx | no normal · no cumple (ruido asimétrico grande) | NO CUMPLE |
| Testeo 4 | 04_No_Normal_Cumple.xlsx | no normal · cumple | CUMPLE CON OBSERVACIONES |

**Diseño:** 8 temperaturas × 3 técnicos × 2 patrones × **5 lecturas por serie** = 240 mediciones.

**Criterio de prueba** (`criterios_prueba.json`; no es un requisito del laboratorio): |sesgo| ≤ 0,10 °C · s_r ≤ 0,05 °C · s_I ≤ 0,08 °C.

**Errores sembrados** (para probar la limpieza): E1 número con coma (TR02) · E2 técnico « t-02 » (TR03+TR04) ·
E3 lectura obligatoria vacía (RC15, serie con 4 lecturas) · E4 hora «25:99» (RC19) · E5 lectura anómala de +10 s
en −20 °C · T-01 · P-01 (bases 01, 03, 04; la señala Grubbs).

Regenerar: `python -m herramientas.generar_bases_prueba`. Las bases anteriores (2 réplicas) quedan en
`version_anterior_2_replicas/` y no se cargan.
