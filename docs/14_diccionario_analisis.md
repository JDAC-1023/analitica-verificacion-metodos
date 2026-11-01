# Diccionario de datos · análisis estadístico

> Generado automáticamente desde `src/motor/configuracion.py` y `src/motor/resultado.py` por `herramientas/generar_documentacion.py`. No editar a mano.

Archivos por versión de análisis: `datos_locales/estudios/<código>/analisis/vNNN/` → `config.json` (entrada), `resultado.json` (memoria de cálculo, inmutable), `comentarios.json` (retroalimentación por etapa, solo se agrega), `informe_<fecha>.pdf` + `.pdf.json` (informes emitidos con SHA-256).

Claves de primer nivel de `resultado.json`: `meta`, `objeto`, `estructura`, `ruta`, `resultados`, `arbol`, `caracteristicas`, `conclusion_final`, `conclusiones`, `datos`, `excluidas`, `reglas`, `sensibilidad`.

## ConfiguracionAnalisis

Configuración de una versión del análisis (analisis/vNNN/config.json).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| codigo_estudio | str | obligatorio |  |
| version | int | 1 |  |
| padre | int \| None | None |  |
| motivo_cambio | str | "" |  |
| preparacion_id | str | "" |  |
| objeto_tipo | str | "variable" | variable \| resultado_directo \| derivado |
| objeto_id | str | "" | V-xx o R-xx |
| regla | ReglaDerivacion \| None | None |  |
| metodo_validado | str | "" | "si" \| "no" \| "" (desconocido) |
| modificaciones | str | "" |  |
| documentacion_previa | str | "" |  |
| caracteristicas | list[CaracteristicaConfig] | field(default_factory=list) |  |
| es_interlaboratorio | bool | False |  |
| factor_laboratorio | str | "" | "tecnico" \| "patron" \| id de factor (solo si es interlaboratorio) |
| factores_precision_intermedia | list[str] | field(default_factory=list) |  |
| referencia_tipo | str | "ninguna" | ninguna \| valor_por_nivel \| objeto_es_diferencia |
| referencias | list[ReferenciaNivel] | field(default_factory=list) |  |
| alfa | float | 0.05 |  |
| nivel_confianza | float | 0.95 |  |
| prueba_normalidad | str | "shapiro_wilk" |  |
| alerta_faltantes_pct | float \| None | None | alerta configurable; no es criterio de aplicabilidad |
| version_normativa | str | "ISO 5725-2:1994" |  |
| exclusiones | list[Exclusion] | field(default_factory=list) |  |
| criterios | list[CriterioMotor] | field(default_factory=list) |  |
| elaborado_por | str | "" |  |
| revisado_por | str | "" |  |
| autorizado_por | str | "" |  |
| creado_en | str | "" |  |

## CaracteristicaConfig

Estado de cada característica de desempeño.

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| codigo | str | obligatorio |  |
| estado | str | "PENDIENTE" |  |
| justificacion | str | "" |  |
| fuente | str | "" |  |

## ReferenciaNivel

Valor de referencia por punto (para el sesgo).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| punto_id | str | obligatorio |  |
| valor | float \| None | None |  |
| incertidumbre | float \| None | None | incertidumbre estándar u_ref |
| fuente | str | "" |  |

## CriterioMotor

Límite de aceptación estructurado.

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| id | str | obligatorio |  |
| caracteristica | str | obligatorio |  |
| parametro | str | obligatorio |  |
| operador | str | "<=" |  |
| limite | float \| None | None |  |
| unidad | str | "" |  |
| regla_decision | str | "" | vacío = sin regla documentada → sin evaluación |
| fuente | str | "" |  |
| aprobado | bool | False |  |
| puntos | list[str] | field(default_factory=list) | vacío = todos los puntos |
| criterio_estudio_id | str | "" | vínculo opcional con C-xx de la matriz |

## Exclusion

Exclusión documentada (solo en versiones derivadas).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| medicion_id | str | obligatorio |  |
| motivo | str | obligatorio |  |
| responsable | str | obligatorio |  |
| fecha | str | "" |  |
| origen | str | "revision_atipicos" |  |

## ReglaDerivacion

Regla aprobada para un resultado calculado (a − b).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| tipo | str | "diferencia" | diferencia: a − b (la única implementada) |
| a | str | "" | id de variable |
| b | str | "" |  |
| referencia | str | "" | documento/procedimiento que la aprueba |
| aprobada | bool | False |  |

## ResultadoAnalisis

Memoria de cálculo de cada prueba (lista «resultados» de resultado.json).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| analysis_id | str | obligatorio |  |
| etapa | str | obligatorio | limpieza \| atipicos \| normalidad \| desempeno |
| tecnica | str | obligatorio |  |
| study_id | str | obligatorio |  |
| version | int | obligatorio |  |
| variable_id | str | obligatorio |  |
| unidad | str | obligatorio |  |
| agrupacion | str | obligatorio | p. ej. "punto=PT-01" |
| estado | str | obligatorio | APLICABLE / NO_APLICABLE / … |
| motivos | list[str] | field(default_factory=list) |  |
| n | int | 0 |  |
| incluidas | list[str] | field(default_factory=list) |  |
| excluidas | list[str] | field(default_factory=list) |  |
| algoritmo | str | "" |  |
| referencia | str | "" |  |
| origen_regla | str | "" |  |
| supuestos | list[dict] | field(default_factory=list) | {supuesto, verificado, evidencia} |
| hipotesis | dict | field(default_factory=dict) | {H0, H1, lateralidad, alfa} |
| formula | str | "" |  |
| estadistico | dict | field(default_factory=dict) | {simbolo, valor} |
| gl | Any | None |  |
| p_valor | float \| None | None |  |
| criticos | dict | field(default_factory=dict) |  |
| ic | list \| None | None |  |
| estimacion | dict | field(default_factory=dict) | {nombre, valor, unidad} |
| decision_inferencial | str | "" |  |
| requisito | dict | field(default_factory=dict) | criterio aplicado y fuente |
| decision_metrologica | str | "" |  |
| tabla | list[dict] | field(default_factory=list) | cálculos intermedios |
| graficos | list[str] | field(default_factory=list) | claves de gráficos |
| limitaciones | list[str] | field(default_factory=list) |  |
| texto | str | "" | plantilla renderizada |
| arbol | list[NodoDecision] | field(default_factory=list) |  |
| caracteristica | str | "" | sesgo \| repetibilidad \| … (solo desempeño) |
| punto_id | str | "" |  |

## NodoDecision

Paso del árbol de decisiones (lista «arbol» de resultado.json).

| Campo | Tipo | Valor por defecto | Nota |
| --- | --- | --- | --- |
| pregunta | str | obligatorio |  |
| respuesta | str | obligatorio | SI \| NO \| APLICABLE \| NO_APLICABLE |
| evidencia | str | "" |  |
| regla | str | "" | código de la regla (RM-xx) |

## Dominios

| Campo | Valores |
| --- | --- |
| Estado de aplicabilidad | APLICABLE, NO_APLICABLE, DATOS_INSUFICIENTES, NO_IMPLEMENTADO, PENDIENTE_MODELO |
| Decisión metrológica | CONFORME, NO_CONFORME, INDETERMINADO, CALCULADO_SIN_EVALUACION |
| Conclusión global | CONFORME, CONFORME_CON_OBSERVACIONES, NO_CONFORME, INDETERMINADO, INCOMPLETO, CALCULADO_SIN_EVALUACION, SIN_ALCANCE |
| Origen de la regla | NORMA, COMPLEMENTARIA, CRITERIO_LAB |
| Etapas | limpieza, atipicos, normalidad, homocedasticidad, desempeno |
| Ruta de comparación | anova (ANOVA + Tukey), welch (Welch + Games-Howell), kruskal (Kruskal-Wallis + Dunn-Holm) |
| Características | sesgo, repetibilidad, precision_intermedia, reproducibilidad, linealidad, lod_loq, selectividad, robustez, incertidumbre |
| Estado de característica | REQUERIDA, SELECCIONADA, NO_APLICABLE_JUSTIFICADA, PENDIENTE |

## Reglas del motor (RM-xx)

| codigo | descripcion | origen | referencia |
| --- | --- | --- | --- |
| RM-01 | Los datos originales no se modifican; el motor trabaja sobre una copia del conjunto preparado. | NORMA | ISO/IEC 17025:2017 §7.5 y §7.11 |
| RM-02 | No se imputan faltantes ni se reemplazan por cero; cada técnica comprueba su propia suficiencia. | COMPLEMENTARIA | Especificación §6 |
| RM-03 | El porcentaje de faltantes solo genera alerta si el laboratorio fija un umbral; no hay umbral universal. | CRITERIO_LAB | Especificación §6 |
| RM-04 | Las pruebas de Cochran y Mandel y la estimación de s_R solo se aplican a estudios interlaboratorio. | NORMA | ISO 5725-2:1994 §7.3 y §7.4 |
| RM-05 | Los técnicos u otras condiciones internas no se tratan como laboratorios. | NORMA | ISO 5725-1:1994 §3.18–3.20 |
| RM-06 | Las tablas de valores críticos solo se aplican si la edición configurada es la implementada. | NORMA | ISO 5725-2:1994 |
| RM-07 | Cochran exige al menos dos celdas con réplicas; si n_ij difiere se usa el n mayoritario y se deja constancia. | NORMA | ISO 5725-2:1994 §7.3.3 |
| RM-08 | Grubbs (procedimiento de la norma) se aplica a medias de celda de un nivel con p ≥ 3; doble con p ≥ 4. | NORMA | ISO 5725-2:1994 §7.3.4 |
| RM-09 | Grubbs intralaboratorio solo sobre réplicas de una misma celda con n ≥ 3; nunca sobre la mezcla de puntos o condiciones. | COMPLEMENTARIA | Grubbs (1969) |
| RM-10 | Ningún dato se excluye por resultado estadístico sin motivo técnico, responsable, versión derivada y recálculo. | NORMA | ISO 5725-2:1994 §7.3.2; Especificación §8 |
| RM-11 | El objeto de la prueba de normalidad depende del procedimiento: unidades del sesgo o residuos dentro de celda. | COMPLEMENTARIA | Montgomery (2017) |
| RM-12 | Un valor p ≥ α se redacta como «no se rechaza H0», nunca como «se confirma». | COMPLEMENTARIA | Especificación §11 |
| RM-13 | Sesgo: prueba t si no se rechaza normalidad y n ≥ 3; Wilcoxon si se rechaza (supuesto de simetría a revisar); solo estimación si n < 3. | COMPLEMENTARIA | Eurachem (2016) §6.5 |
| RM-14 | Repetibilidad: varianzas intracelda agrupadas por grados de libertad. | NORMA | ISO 5725-2:1994 ec. 20; Eurachem (2016) §6.6 |
| RM-15 | Reproducibilidad intralaboratorio (precisión intermedia): ANOVA de un factor de efectos aleatorios; varianza entre grupos negativa se toma como 0. | COMPLEMENTARIA | Eurachem (2016) §6.6.4 y anexo C |
| RM-16 | Reproducibilidad: s_R² = s_L² + s_r²; s_L² negativo se toma como 0. | NORMA | ISO 5725-2:1994 ec. 21–24 y §7.4.5.4 |
| RM-17 | Sin criterio aprobado, límite numérico y regla de decisión, el resultado queda CALCULADO_SIN_EVALUACION. | NORMA | ISO/IEC 17025:2017 §7.1.3 y §7.8.6 |
| RM-18 | La no significación estadística no demuestra equivalencia ni conformidad. | COMPLEMENTARIA | Especificación §9 |
| RM-19 | No se convierten unidades: un criterio con unidad distinta no se evalúa. | CRITERIO_LAB | Especificación §3 |
| RM-20 | Decisión inferencial, estimación y decisión metrológica se informan por separado. | COMPLEMENTARIA | Especificación §9 |
| RM-21 | Ruta verificación/validación según el estado del método: validado y sin modificaciones → verificación. | NORMA | Eurachem (2016) §4.2; ISO/IEC 17025:2017 §7.2.1.5 y §7.2.2 |
| RM-22 | Dixon no se implementa: no se dispone de tablas críticas verificadas. | COMPLEMENTARIA | Dixon (1950) |
| RM-23 | Fuentes de variación: ANOVA factorial por punto (técnico, patrón, …) con interacciones solo si hay réplicas en cada combinación; la influencia se decide por el valor p. | COMPLEMENTARIA | Montgomery (2017) cap. 5 |
| RM-24 | α = 0,05, confianza 95 % y Shapiro-Wilk son fijos: la decisión de las pruebas de hipótesis no es configurable; solo se configuran los límites de aceptación. | COMPLEMENTARIA | Especificación del equipo (2026-11-01) |
| RM-25 | Si el método cumple pero se rechazó la normalidad en alguna revisión, la conclusión es «cumple con observaciones». | COMPLEMENTARIA | Especificación del equipo (2026-11-01) |
| RM-26 | Secuencia: normalidad (Shapiro-Wilk) → solo con normalidad, Bartlett → varianzas iguales: ANOVA + Tukey; varianzas distintas: Welch + Games-Howell. Sin normalidad no se aplica ningún ANOVA: Kruskal-Wallis + Dunn-Holm (Fligner-Killeen solo informa). Sin normalidad tampoco se informan prueba F de s_I ni intervalos χ². | COMPLEMENTARIA | Montgomery (2017) cap. 3; Conover et al. (1981) |
| RM-27 | Si se detectan atípicos, se señalan, se calcula el efecto de excluirlos (sensibilidad) y la exclusión definitiva la decide una persona en una versión nueva. | NORMA | ISO 5725-2:1994 §7.3.2 |
