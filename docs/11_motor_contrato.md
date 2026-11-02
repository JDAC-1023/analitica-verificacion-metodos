# Motor estadístico · contrato de entrada y correspondencia con la matriz

> Motor determinista basado en reglas (sin aprendizaje automático). Código en `src/motor/`. Edición implementada: **ISO 5725-2:1994** (no 2025). Marco de adecuación al uso: Eurachem (2016).

## 1. Campos que la matriz v0.2 no tiene y el motor necesita

La matriz describe el diseño y la ingesta, pero no trae lo necesario para decidir sin inventar requisitos. El motor **pide** estos campos en la pantalla «Análisis estadístico» y los guarda en `analisis/vNNN/config.json`. Si faltan, el resultado queda `PENDIENTE`, `DATOS_INSUFICIENTES` o `CALCULADO_SIN_EVALUACION`; nunca se rellenan con valores por defecto.

| Campo nuevo | Para qué | Si falta |
| --- | --- | --- |
| `objetos[]` (tipo, id, regla, referencia, características y criterios de cada uno) | **Qué resultados se evalúan.** Con varios, el motor corre todas las pruebas por separado para cada uno y el veredicto global es el más desfavorable | No se ejecuta |
| `objeto_tipo`, `objeto_id` | Objeto único de versiones anteriores (se sigue leyendo; equivale a `objetos` con un elemento) | — |
| `regla` (a − b, referencia, aprobada) | Única derivación implementada; la matriz solo da dependencias (V05) y referencia (V06), no la fórmula | Error: el motor no inventa fórmulas |
| `metodo_validado`, `modificaciones`, `documentacion_previa` | Ruta verificación / validación (Eurachem §4.2) | Ruta «no determinable», aviso |
| `caracteristicas[]` (REQUERIDA / SELECCIONADA / NO_APLICABLE_JUSTIFICADA / PENDIENTE, justificación, fuente) | Qué se evalúa. El laboratorio decide | No se calcula desempeño |
| `es_interlaboratorio`, `factor_laboratorio` | Habilita Cochran, Mandel y s_R | Se tratan como intralaboratorio |
| `factores_precision_intermedia[]` | Forman las celdas (condiciones que cambian dentro del laboratorio) | Una sola celda por nivel; s_r con supuesto declarado |
| `referencia_tipo`, `referencias[]` (valor, u estándar, fuente por punto) | Sesgo | Sesgo NO_APLICABLE o DATOS_INSUFICIENTES |
| `criterios[]` (característica, parámetro, operador, límite, unidad, regla de decisión, fuente, aprobado, puntos) | Decisión metrológica. La matriz (C03) guarda el criterio como texto libre | `CALCULADO_SIN_EVALUACION` |
| `alfa`, `nivel_confianza`, `prueba_normalidad` | **Fijos** (0,05 / 95 % / Shapiro-Wilk, RM-24): la decisión de las pruebas de hipótesis no es configurable | — |
| `alerta_faltantes_pct` | Aviso opcional; **no** es criterio de aplicabilidad | Sin alerta |
| `version_normativa` | Si no es «ISO 5725-2:1994», no se usan las tablas implementadas | — |
| `exclusiones[]` (medición, motivo, responsable, fecha) | Solo en versiones derivadas | — |
| `elaborado_por`, `revisado_por`, `autorizado_por` | Bloque de control del informe | «pendiente» |

## 2. Etapas y técnicas

| Etapa | Técnica | Cuándo aplica | Origen |
| --- | --- | --- | --- |
| Limpieza | Faltantes global / por dato / por nivel / por celda frente al plan aprobado | Siempre | Complementaria |
| Limpieza | Estructura: q, p_j, n_ij, balance, gl | Siempre | Norma (ISO 5725-2 §7.2) |
| Atípicos | Mandel h, k (indicadores tablas 6–7) | Interlaboratorio, p ≥ 3 | Norma |
| Atípicos | Cochran (tabla 4) | Interlaboratorio, ≥ 2 celdas con n ≥ 2 | Norma |
| Atípicos | Grubbs simple y doble sobre medias de celda (tabla 5) | Interlaboratorio, p ≥ 3 (doble p ≥ 4) | Norma |
| Atípicos | Grubbs simple sobre réplicas de una celda | Intralaboratorio, n_ij ≥ 3 | Complementaria |
| Atípicos | Dixon | NO_IMPLEMENTADO (sin tablas verificadas) | — |
| Normalidad | Shapiro-Wilk (fijo) | Sobre promedios de serie (sesgo) y residuos dentro de celda (supuesto del ANOVA), por nivel | Complementaria |
| Homocedasticidad | Bartlett, **solo si los residuos son normales** (decide ANOVA o Welch); con datos no normales, Fligner-Killeen solo informativo | ≥ 2 series con ≥ 3 lecturas | Complementaria (RM-26) |
| Desempeño | Sesgo: t de Student / Wilcoxon / solo estimación | Según normalidad y n de unidades independientes | Complementaria (Eurachem §6.5) |
| Desempeño | Repetibilidad s_r (ec. 20); IC χ² solo con residuos normales | Al menos una celda con réplicas | Norma |
| Desempeño | Reproducibilidad intralaboratorio s_I (componentes de varianza); prueba F e IC χ² solo con residuos normales (F, además, con varianzas iguales) | ≥ 2 grupos, alguno con réplicas | Complementaria (Eurachem §6.6.4; ISO 5725-3) |
| Desempeño | Reproducibilidad s_R (ec. 19–24) | Solo interlaboratorio | Norma |
| Desempeño | Fuentes de variación (técnico, patrón, interacción): ANOVA + Tukey · Welch + Games-Howell · Kruskal-Wallis + Dunn-Holm según la ruta; nunca ANOVA sin normalidad | Intralaboratorio con factores declarados y réplicas | Complementaria (RM-23, RM-26) |
| Atípicos | Sensibilidad: recálculo sin los atípicos para mostrar qué decisión cambiaría (no es exclusión) | Si Grubbs señala lecturas | Norma (RM-27) |
| Limpieza | Réplicas por serie frente al plan | Siempre | Complementaria |
| Criterios | Estimación o intervalo frente al límite | Criterio aprobado completo | Criterio del laboratorio |

## 3. Tres decisiones separadas

Cada resultado guarda por separado:
1. **Decisión inferencial** («Se rechaza H0» / «No se rechaza H0 …», nunca «se confirma»).
2. **Estimación** (valor, IC, gl).
3. **Decisión metrológica** (CONFORME, NO_CONFORME, INDETERMINADO o CALCULADO_SIN_EVALUACION), solo frente a un criterio aprobado.

## 4. Trazabilidad campo → algoritmo → memoria de cálculo

| Entrada | Algoritmo | Dónde queda en `resultado.json` |
| --- | --- | --- |
| `valores.valor_numerico` / `resultados_valores.valor` | `datos.construir` (sin modificar valores) | `datos[]` |
| plan aprobado (D09) | `limpieza.tabla_faltantes` | resultado «Faltantes», `tabla` |
| `factores_precision_intermedia` / `factor_laboratorio` | celdas = combinación de niveles | `datos[].celda`, `estructura` |
| `alfa` | todas las pruebas | `hipotesis.alfa` |
| tablas ISO 4–7 | `tablas_iso.critico_*` | `criticos` + `origen` (tabla o fórmula) |
| `referencias` | `desempeno._sesgo` | `estimacion.referencia`, `u_ref` |
| `criterios` | `criterios.evaluar_valor` | `requisito`, `decision_metrologica`, `motivos` |
| todo | `motor.ejecutar` | `arbol[]` (pregunta, respuesta, evidencia, regla RM-xx), `meta.huella_resultado` |

Campos de la memoria (§10) por resultado: `analysis_id, etapa, tecnica, study_id, version, variable_id, unidad, agrupacion, estado, motivos, n, incluidas, excluidas, algoritmo, referencia, origen_regla, supuestos, hipotesis, formula, estadistico, gl, p_valor, criticos, ic, estimacion, decision_inferencial, requisito, decision_metrologica, tabla, graficos, limitaciones, texto, arbol`.

## 5. Verificación de las tablas transcritas

- Las tablas 4, 5, 6 y 7 se compararon entrada por entrada con su fórmula teórica (`test_tablas_transcritas_coinciden_con_formula`).
- Dos valores impresos difieren de la fórmula y **se conservan tal como están impresos**:
  - Tabla 4, Cochran p = 13, n = 6, 5 %: impreso 0,243; fórmula 0,246.
  - Tabla 7, Mandel k p = 24, n = 10, 5 %: impreso 1,38; fórmula 1,362.
- Fuera del rango de las tablas el valor se calcula por fórmula y se declara en `criticos.origen`.
- El anexo B.1 se reproduce: s_r y s_R de la tabla B.5 a tres decimales; con los estadísticos redondeados de B.2/B.3 se obtienen m̂ = 0,69044, s_r² = 0,0002322, s_r = 0,01524 y s_R = 0,02632; Cochran señala al laboratorio 5 en el nivel 3 como rezagado; Grubbs doble señala a los laboratorios 3 y 6 en el nivel 2.

## 6. Varios resultados evaluados

`multi.ejecutar_todos` llama a `motor.ejecutar` una vez por objeto con `cfg.para_objeto(o)`: lo común (conjunto, estructura, factores, reglas fijas, exclusiones) más lo propio del resultado. Ninguna decisión se comparte entre resultados. El `resultado.json` queda con `multi: true`, `objetos[]` (un resultado completo por objeto, con su huella) y `conclusion_final` combinada (orden NO_CONFORME → INDETERMINADO → INCOMPLETO → CALCULADO_SIN_EVALUACION → SIN_ALCANCE → CONFORME_CON_OBSERVACIONES → CONFORME). `multi.partes()` devuelve la lista de resultados (también para análisis antiguos de un solo objeto).

## 7. Límites conocidos de esta versión

- Solo derivación «a − b». Otras fórmulas requieren una regla aprobada nueva en código.
- Para estimar s_I los factores se combinan en un único factor; su efecto por separado se prueba en «Fuentes de variación».
- Sin IC para s_R.
- La prueba t de sesgo no incorpora u_ref (se informa aparte).
- Linealidad, LOD/LOQ, selectividad, robustez e incertidumbre: NO_IMPLEMENTADO (si se marcan como REQUERIDAS, la conclusión global queda INCOMPLETA).
- Las guías ema/CENAM (2017) y SAE G DAL 03 (2025) se citan como contexto de verificación clínica; sus protocolos específicos (p. ej. EP15) no están implementados.
