# Diccionario de campos de results/

| Archivo | Campo | Significado |
| --- | --- | --- |
| metricas_por_escenario.csv | escenario, estudio | Testeo (base sintética) y código del estudio en la base de datos |
| | resultado_evaluado | Corrección, Inestabilidad o Inhomogeneidad |
| | estado_resultado / estado_global | Conclusión del motor para ese resultado / para el análisis completo (el más desfavorable) |
| | rechazos_normalidad, revisiones_normalidad | Shapiro-Wilk con p ≤ 0,05 / revisiones aplicadas |
| | ruta_anova, ruta_welch, ruta_kruskal | Puntos en que el motor eligió cada ruta de comparación (RM-26) |
| | lecturas_senaladas | Lecturas marcadas por Grubbs (no se eliminan) |
| | sesgo_min/max, s_r_min/max, s_I_min/max | Rango de las estimaciones en los ocho puntos [°C] |
| metricas_por_particion.csv | punto | Punto nominal |
| | sesgo, s_r, s_I | Estimación del punto [unidad del resultado] |
| | decision_sesgo, decision_s_r, decision_s_I | CONFORME / NO_CONFORME / CALCULADO_SIN_EVALUACION frente al límite aprobado |
| | p_normalidad_residuos, p_normalidad_medias | Shapiro-Wilk de los residuos (supuesto del ANOVA) y de los promedios de serie (sesgo) |
| | ruta | Ruta de comparación de las fuentes de variación |
| | p_tecnico, p_patron, p_operador, p_tiempo | Valor p del factor en la ruta elegida |
| contraste_<magnitud>.csv | laboratorio | Valor impreso en el informe técnico del laboratorio |
| | reproduccion | Mismo procedimiento del laboratorio recalculado de forma independiente |
| | motor | Valor calculado por el motor sobre el conjunto aprobado en la base de datos |
| | dif_reproduccion, dif_motor | Diferencia absoluta con el valor del laboratorio |
| | decision_laboratorio, decision_motor, coincide_decision | Rechaza / no rechaza con α = 0,05 y si coinciden |
| componentes_varianza.csv | s2_operador, s2_tiempo, s2_r, u_lab | Componentes de varianza y aporte de precisión intermedia (fórmulas del informe) |
| experiments.csv | semilla | Réplica del estudio de estabilidad (herramientas/estabilidad.py) |
