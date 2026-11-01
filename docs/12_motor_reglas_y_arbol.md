# Motor · matriz de reglas y árbol de decisión

## Árbol de decisión

```mermaid
flowchart TD
  A["Conjunto preparado y APROBADO"] --> B["1 · Datos<br/>faltantes vs plan · réplicas por serie"]
  B --> C{"2 · ¿Hay datos atípicos?<br/>Grubbs por serie (n ≥ 3) · ISO 5725-2 tabla 5<br/>(interlab: Mandel → Cochran → Grubbs)"}
  C -- NO --> D
  C -- SÍ --> C1["Se señalan, NO se borran<br/>sensibilidad: se recalcula sin ellos"]
  C1 --> C2["Exclusión solo con causa técnica,<br/>responsable y versión 2"]
  C1 --> D{"3a · ¿Residuos normales?<br/>Shapiro-Wilk, α = 0,05<br/>(supuesto del ANOVA)"}
  D -- SÍ --> E{"4 · ¿Varianzas iguales?<br/>Bartlett"}
  E -- SÍ --> F1["5 · ANOVA factorial<br/>+ Tukey HSD"]
  E -- NO --> F2["5 · ANOVA de Welch<br/>+ Games-Howell"]
  D -- NO --> F3["5 · SIN ANOVA<br/>Kruskal-Wallis + Dunn-Holm<br/>(Fligner-Killeen solo informa)"]
  F1 & F2 & F3 --> G["¿Dónde están las diferencias y por qué?<br/>técnico · patrón · combinación"]
  C -- NO --> DS
  C1 --> DS{"3b · ¿Promedios de serie normales?<br/>Shapiro-Wilk (objeto del sesgo)"}
  DS -- SÍ --> S1["6 · Sesgo: t de Student + IC 95 %"]
  DS -- NO --> S2["6 · Sesgo: Wilcoxon (sin IC)"]
  D -- SÍ --> P1["7–8 · s_r y s_I con IC χ²<br/>(prueba F de s_I solo si varianzas iguales)"]
  D -- NO --> P2["7–8 · s_r y s_I solo estimación<br/>(sin prueba F ni IC χ²)"]
  G & S1 & S2 & P1 & P2 --> K{"¿Límite aprobado?"}
  K -- NO --> K0["Sin criterio"]
  K -- SÍ --> K1["Cumple / No cumple / Indeterminado<br/>por punto"]
  K1 --> V["Veredicto: SIRVE · SIRVE CON OBSERVACIONES · NO SIRVE<br/>+ qué implica y qué hacer"]
```

![Árbol de decisión](diagramas/arbol_decision.png)

### Secuencia y su fundamento

| Paso | Pregunta | Prueba | Si SÍ | Si NO | Fuente |
| --- | --- | --- | --- | --- | --- |
| 1 | ¿Están los datos planificados? | Conteo frente al plan; réplicas por serie | Seguir | Informar faltantes; no imputar | ISO 5725-2 §7.2 |
| 2 | ¿Hay datos atípicos? | Grubbs por serie (interlab: Mandel → Cochran → Grubbs) | Señalar; sensibilidad sin ellos; excluir solo con causa técnica y versión 2 | Seguir con todos | ISO 5725-2 §7.3; Grubbs (1969) |
| 3a | ¿Los residuos son normales? | Shapiro-Wilk | Paso 4 | **Sin ANOVA**: Kruskal-Wallis + Dunn-Holm; s_r y s_I sin prueba F ni IC χ² | Shapiro & Wilk (1965); Montgomery (2017) §3.4 |
| 3b | ¿Los promedios de serie son normales? | Shapiro-Wilk | Sesgo con t de Student e IC | Sesgo con Wilcoxon (simetría a revisar) | Eurachem §6.5; Wilcoxon (1945) |
| 4 | ¿Varianzas iguales? (solo si 3a = SÍ) | Bartlett | ANOVA factorial + Tukey HSD | ANOVA de Welch + Games-Howell | Bartlett (1937); Welch (1951); Tukey (1949); Games & Howell (1976) |
| 5 | ¿Influyen técnico, patrón o su combinación? | La de la ruta | Post hoc: dónde y cuánto; origen probable | El método es robusto a esos cambios | Montgomery (2017) cap. 3 y 5 |
| 6–8 | ¿Cumple el límite? | Estimación o IC frente al límite aprobado | Cumple | No cumple / indeterminado / sin criterio | ISO/IEC 17025 §7.8.6 |

## Matriz de reglas (RM-xx)

Generada desde `src/motor/reglas.py`; la misma tabla aparece en el anexo B del informe.

| Regla | Descripción | Origen | Referencia |
| --- | --- | --- | --- |
| RM-01 | Los datos originales no se modifican; el motor trabaja sobre una copia del conjunto preparado. | NORMA | ISO/IEC 17025:2017 §7.5 y §7.11 |
| RM-02 | No se imputan faltantes ni se reemplazan por cero; cada técnica comprueba su propia suficiencia. | COMPLEMENTARIA | Especificación §6 |
| RM-03 | El porcentaje de faltantes solo genera alerta si el laboratorio fija un umbral; no hay umbral universal. | CRITERIO_LAB | Especificación §6 |
| RM-04 | Cochran, Mandel y s_R solo en estudios interlaboratorio. | NORMA | ISO 5725-2:1994 §7.3 y §7.4 |
| RM-05 | Los técnicos u otras condiciones internas no se tratan como laboratorios. | NORMA | ISO 5725-1:1994 §3.18–3.20 |
| RM-06 | Las tablas críticas solo se aplican si la edición configurada es la implementada. | NORMA | ISO 5725-2:1994 |
| RM-07 | Cochran exige ≥ 2 celdas con réplicas; con n_ij distinto se usa el n mayoritario. | NORMA | ISO 5725-2:1994 §7.3.3 |
| RM-08 | Grubbs (norma) sobre medias de celda, p ≥ 3; doble p ≥ 4. | NORMA | ISO 5725-2:1994 §7.3.4 |
| RM-09 | Grubbs intralaboratorio solo sobre réplicas de una celda (n ≥ 3). | COMPLEMENTARIA | Grubbs (1969) |
| RM-10 | Ninguna exclusión sin motivo técnico, responsable, versión derivada y recálculo. | NORMA | ISO 5725-2:1994 §7.3.2 |
| RM-11 | El objeto de la normalidad depende del procedimiento. | COMPLEMENTARIA | Montgomery (2017) |
| RM-12 | p ≥ α se redacta «no se rechaza H0». | COMPLEMENTARIA | Especificación §11 |
| RM-13 | Ruta del sesgo: t / Wilcoxon / solo estimación. | COMPLEMENTARIA | Eurachem (2016) §6.5 |
| RM-14 | s_r: varianzas intracelda agrupadas. | NORMA | ISO 5725-2:1994 ec. 20 |
| RM-15 | s_I: ANOVA de efectos aleatorios; varianza entre negativa → 0. | COMPLEMENTARIA | Eurachem (2016) §6.6.4 |
| RM-16 | s_R² = s_L² + s_r²; s_L² negativo → 0. | NORMA | ISO 5725-2:1994 ec. 21–24 |
| RM-17 | Sin criterio aprobado completo → CALCULADO_SIN_EVALUACION. | NORMA | ISO/IEC 17025:2017 §7.8.6 |
| RM-18 | La no significación no demuestra equivalencia. | COMPLEMENTARIA | Especificación §9 |
| RM-19 | No se convierten unidades. | CRITERIO_LAB | Especificación §3 |
| RM-20 | Decisión inferencial, estimación y decisión metrológica separadas. | COMPLEMENTARIA | Especificación §9 |
| RM-21 | Ruta verificación / validación según el estado del método. | NORMA | Eurachem (2016) §4.2 |
| RM-22 | Dixon no implementado. | COMPLEMENTARIA | Dixon (1950) |
| RM-23 | Fuentes de variación por punto (técnico, patrón, interacción). | COMPLEMENTARIA | Montgomery (2017) |
| RM-24 | α = 0,05, 95 % y Shapiro-Wilk fijos; solo se configuran los límites. | COMPLEMENTARIA | Especificación del equipo |
| RM-25 | Cumple + normalidad rechazada → «cumple con observaciones». | COMPLEMENTARIA | Especificación del equipo |
| RM-26 | Normalidad → (solo si hay normalidad) Bartlett → ANOVA + Tukey o Welch + Games-Howell; sin normalidad nunca ANOVA: Kruskal-Wallis + Dunn-Holm (Fligner-Killeen solo informa); sin normalidad no se informan prueba F de s_I ni IC χ². | COMPLEMENTARIA | Montgomery (2017) cap. 3; Conover et al. (1981) |
| RM-27 | Atípicos: se señalan, se mide su efecto (sensibilidad) y la exclusión la decide una persona. | NORMA | ISO 5725-2:1994 §7.3.2 |
