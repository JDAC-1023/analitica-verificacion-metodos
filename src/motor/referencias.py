"""Fundamentación teórica de cada técnica y referencias en formato APA 7.

Estos textos alimentan el marco teórico del informe. Solo se incluyen en el
informe las técnicas que el motor realmente ejecutó o evaluó.
"""

from __future__ import annotations

REFERENCIAS = {
    "iso5725_1": "International Organization for Standardization. (1994a). *Accuracy (trueness and precision) of measurement methods and results — Part 1: General principles and definitions* (ISO 5725-1:1994). ISO.",
    "iso5725_2": "International Organization for Standardization. (1994b). *Accuracy (trueness and precision) of measurement methods and results — Part 2: Basic method for the determination of repeatability and reproducibility of a standard measurement method* (ISO 5725-2:1994). ISO.",
    "iso17025": "International Organization for Standardization & International Electrotechnical Commission. (2017). *General requirements for the competence of testing and calibration laboratories* (ISO/IEC 17025:2017). ISO.",
    "eurachem": "Magnusson, B., & Örnemark, U. (Eds.). (2016). *La adecuación al uso de los métodos analíticos: Una guía de laboratorio para la validación de métodos y temas relacionados* (1.ª ed. en español, traducción de la 2.ª ed. inglesa de 2014). Eurachem.",
    "vim": "Joint Committee for Guides in Metrology. (2012). *Vocabulario Internacional de Metrología: Conceptos fundamentales y generales, y términos asociados (VIM)* (3.ª ed. en español). Centro Español de Metrología.",
    "ema_cenam": "Entidad Mexicana de Acreditación & Centro Nacional de Metrología. (2017). *Guía para la validación y la verificación de los procedimientos de examen cuantitativos empleados por el laboratorio clínico*. ema / CENAM.",
    "sae": "Servicio de Acreditación Ecuatoriano. (2025). *Guía para la validación y/o verificación de métodos de ensayo en laboratorios clínicos* (G DAL 03 R00). SAE.",
    "shapiro": "Shapiro, S. S., & Wilk, M. B. (1965). An analysis of variance test for normality (complete samples). *Biometrika, 52*(3–4), 591–611. https://doi.org/10.1093/biomet/52.3-4.591",
    "royston": "Royston, P. (1995). Remark AS R94: A remark on Algorithm AS 181: The W-test for normality. *Journal of the Royal Statistical Society: Series C (Applied Statistics), 44*(4), 547–551. https://doi.org/10.2307/2986146",
    "anderson": "Anderson, T. W., & Darling, D. A. (1954). A test of goodness of fit. *Journal of the American Statistical Association, 49*(268), 765–769. https://doi.org/10.1080/01621459.1954.10501232",
    "stephens": "Stephens, M. A. (1974). EDF statistics for goodness of fit and some comparisons. *Journal of the American Statistical Association, 69*(347), 730–737. https://doi.org/10.1080/01621459.1974.10480196",
    "lilliefors": "Lilliefors, H. W. (1967). On the Kolmogorov-Smirnov test for normality with mean and variance unknown. *Journal of the American Statistical Association, 62*(318), 399–402. https://doi.org/10.1080/01621459.1967.10482916",
    "grubbs1969": "Grubbs, F. E. (1969). Procedures for detecting outlying observations in samples. *Technometrics, 11*(1), 1–21. https://doi.org/10.1080/00401706.1969.10490657",
    "grubbs1972": "Grubbs, F. E., & Beck, G. (1972). Extension of sample sizes and percentage points for significance tests of outlying observations. *Technometrics, 14*(4), 847–854. https://doi.org/10.1080/00401706.1972.10488981",
    "cochran": "Cochran, W. G. (1941). The distribution of the largest of a set of estimated variances as a fraction of their total. *Annals of Eugenics, 11*(1), 47–52. https://doi.org/10.1111/j.1469-1809.1941.tb02271.x",
    "mandel": "Mandel, J. (1964). *The statistical analysis of experimental data*. Interscience Publishers.",
    "student": "Student. (1908). The probable error of a mean. *Biometrika, 6*(1), 1–25. https://doi.org/10.2307/2331554",
    "wilcoxon": "Wilcoxon, F. (1945). Individual comparisons by ranking methods. *Biometrics Bulletin, 1*(6), 80–83. https://doi.org/10.2307/3001968",
    "levene": "Levene, H. (1960). Robust tests for equality of variances. En I. Olkin (Ed.), *Contributions to probability and statistics* (pp. 278–292). Stanford University Press.",
    "brown_forsythe": "Brown, M. B., & Forsythe, A. B. (1974). Robust tests for the equality of variances. *Journal of the American Statistical Association, 69*(346), 364–367. https://doi.org/10.1080/01621459.1974.10482955",
    "satterthwaite": "Satterthwaite, F. E. (1946). An approximate distribution of estimates of variance components. *Biometrics Bulletin, 2*(6), 110–114. https://doi.org/10.2307/3002019",
    "bartlett": "Bartlett, M. S. (1937). Properties of sufficiency and statistical tests. *Proceedings of the Royal Society of London. Series A, 160*(901), 268–282. https://doi.org/10.1098/rspa.1937.0109",
    "welch": "Welch, B. L. (1951). On the comparison of several mean values: An alternative approach. *Biometrika, 38*(3–4), 330–336. https://doi.org/10.1093/biomet/38.3-4.330",
    "kruskal": "Kruskal, W. H., & Wallis, W. A. (1952). Use of ranks in one-criterion variance analysis. *Journal of the American Statistical Association, 47*(260), 583–621. https://doi.org/10.1080/01621459.1952.10483441",
    "dunn": "Dunn, O. J. (1964). Multiple comparisons using rank sums. *Technometrics, 6*(3), 241–252. https://doi.org/10.1080/00401706.1964.10490181",
    "games_howell": "Games, P. A., & Howell, J. F. (1976). Pairwise multiple comparison procedures with unequal n's and/or variances: A Monte Carlo study. *Journal of Educational Statistics, 1*(2), 113–125. https://doi.org/10.3102/10769986001002113",
    "tukey": "Tukey, J. W. (1949). Comparing individual means in the analysis of variance. *Biometrics, 5*(2), 99–114. https://doi.org/10.2307/3001913",
    "holm": "Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics, 6*(2), 65–70.",
    "conover": "Conover, W. J., Johnson, M. E., & Johnson, M. M. (1981). A comparative study of tests for homogeneity of variances, with applications to the outer continental shelf bidding data. *Technometrics, 23*(4), 351–361. https://doi.org/10.1080/00401706.1981.10487680",
    "montgomery": "Montgomery, D. C. (2017). *Design and analysis of experiments* (9.ª ed.). John Wiley & Sons.",
    "scipy": "Virtanen, P., Gommers, R., Oliphant, T. E., et al. (2020). SciPy 1.0: Fundamental algorithms for scientific computing in Python. *Nature Methods, 17*, 261–272. https://doi.org/10.1038/s41592-019-0686-2",
    "statsmodels": "Seabold, S., & Perktold, J. (2010). Statsmodels: Econometric and statistical modeling with Python. En *Proceedings of the 9th Python in Science Conference* (pp. 92–96). https://doi.org/10.25080/Majora-92bf1922-011",
}

FUNDAMENTOS = {
    "faltantes": {
        "titulo": "Examen de datos faltantes y estructura del diseño",
        "texto": ("Antes de aplicar cualquier procedimiento estadístico se cuantifican los resultados válidos por celda (n_ij), "
                  "los grupos comparables por nivel (p_j) y el número de niveles (q), tal como los define ISO 5725-2:1994 (§7.2). "
                  "El porcentaje de faltantes se calcula como faltantes/esperados × 100 a partir del plan aprobado. No se imputan "
                  "observaciones ni se reemplazan por cero, media o mediana: la suficiencia depende de cada técnica, que verifica sus "
                  "propios mínimos."),
        "refs": ["iso5725_2", "eurachem"],
    },
    "mandel": {
        "titulo": "Estadísticos de consistencia de Mandel (h y k)",
        "texto": ("El estadístico h compara la media de cada laboratorio con la media general del nivel en unidades de la desviación "
                  "estándar entre medias (ISO 5725-2:1994, ec. 6); k compara la desviación estándar intracelda con la desviación "
                  "agrupada del nivel (ec. 7). Son técnicas gráficas de consistencia: sus indicadores de las tablas 6 y 7 (1 % y 5 %) "
                  "orientan la revisión, no rechazan datos por sí mismos. Solo aplican en estudios interlaboratorio con p ≥ 3."),
        "refs": ["iso5725_2", "mandel"],
    },
    "cochran": {
        "titulo": "Prueba de Cochran",
        "texto": ("Contrasta si la mayor de p varianzas intracelda es excesiva respecto a su suma: C = s²_max / Σ s²_i (ISO 5725-2:1994, ec. 8). "
                  "Es una prueba unilateral de valor atípico en la variabilidad intralaboratorio que exige al menos dos varianzas comparables "
                  "obtenidas con el mismo número n de resultados por celda (§7.3.3.3) y una distribución aproximadamente normal. "
                  "Clasificación según §7.3.2.1: C ≤ crítico 5 % → correcto; entre 5 % y 1 % → rezagado (straggler, *); > 1 % → atípico (**)."),
        "refs": ["iso5725_2", "cochran"],
    },
    "grubbs": {
        "titulo": "Prueba de Grubbs (uno y dos valores extremos)",
        "texto": ("Para un extremo: G = (x_p − x̄)/s o (x̄ − x_1)/s (ISO 5725-2:1994, ec. 9–11). Para dos extremos: cociente de sumas de "
                  "cuadrados sin y con los dos valores (ec. 12–18). Supone una muestra univariada de valores independientes y aproximadamente "
                  "normales. En el procedimiento de la norma se aplica a las medias de celda de un nivel (§7.3.4.3). Fuera de ese contexto "
                  "se usa como técnica complementaria sobre réplicas independientes de una misma celda, nunca sobre la mezcla de puntos o condiciones."),
        "refs": ["iso5725_2", "grubbs1969", "grubbs1972"],
    },
    "shapiro_wilk": {
        "titulo": "Prueba de Shapiro-Wilk",
        "texto": ("Evalúa la hipótesis nula de que la muestra proviene de una población normal comparando los estadísticos de orden con "
                  "sus valores esperados bajo normalidad (estadístico W). Es de las pruebas con mayor potencia para muestras pequeñas y "
                  "moderadas; la implementación de SciPy usa el algoritmo de Royston, válido desde n = 3 (con advertencia sobre el valor p "
                  "para n > 5000). Un p ≥ α no demuestra normalidad: solo indica que no hay evidencia para rechazarla con esos datos."),
        "refs": ["shapiro", "royston", "scipy"],
    },
    "anderson_darling": {
        "titulo": "Prueba de Anderson-Darling",
        "texto": ("Estadístico A² basado en la función de distribución empírica, con mayor peso en las colas. Con media y varianza estimadas "
                  "se compara con valores críticos ajustados (Stephens, 1974) en lugar de un valor p convencional."),
        "refs": ["anderson", "stephens", "scipy"],
    },
    "lilliefors": {
        "titulo": "Prueba de Lilliefors",
        "texto": ("Versión de Kolmogorov-Smirnov para normalidad cuando la media y la varianza se estiman de la muestra. Se usa en lugar del "
                  "valor p convencional de K-S, que solo es válido con la distribución completamente especificada."),
        "refs": ["lilliefors", "statsmodels"],
    },
    "sesgo_t": {
        "titulo": "Sesgo y prueba t de una muestra",
        "texto": ("El sesgo se estima como b = ȳ − x_ref (Eurachem, 2016, §6.5.2). La prueba t de Student contrasta H0: μ = x_ref frente a "
                  "H1: μ ≠ x_ref con t = (ȳ − x_ref)/(s/√n) y n − 1 grados de libertad. Supone unidades independientes y aproximadamente "
                  "normales. Un resultado no significativo no demuestra veracidad ni equivalencia: la conformidad se decide contra el criterio técnico."),
        "refs": ["eurachem", "student", "iso5725_1"],
    },
    "sesgo_wilcoxon": {
        "titulo": "Sesgo y prueba de rangos con signo de Wilcoxon",
        "texto": ("Alternativa no paramétrica a la prueba t cuando se rechaza la normalidad. Contrasta que la mediana de las diferencias "
                  "y − x_ref es cero y supone una distribución simétrica de las diferencias. Ese supuesto de simetría no se demuestra con los "
                  "datos, por lo que el resultado requiere revisión técnica."),
        "refs": ["wilcoxon", "scipy"],
    },
    "repetibilidad": {
        "titulo": "Desviación estándar de repetibilidad",
        "texto": ("s_r se obtiene agrupando las varianzas intracelda ponderadas por sus grados de libertad: s_r² = Σ(n_ij − 1)s_ij² / Σ(n_ij − 1) "
                  "(ISO 5725-2:1994, ec. 20; Eurachem, 2016, §6.6). Su intervalo de confianza se basa en la distribución χ², que supone residuos normales."),
        "refs": ["iso5725_2", "eurachem"],
    },
    "precision_intermedia": {
        "titulo": "Reproducibilidad intralaboratorio (precisión intermedia) mediante ANOVA",
        "texto": ("Con un diseño de grupos (días, técnicos u otras condiciones cambiantes dentro del laboratorio) analizado mediante ANOVA "
                  "de un factor de efectos aleatorios, la repetibilidad es la precisión dentro del grupo y la precisión intermedia es la raíz de "
                  "la suma de las varianzas dentro y entre grupos (Eurachem, 2016, §6.6.4 y anexo C). Si la estimación de la varianza entre "
                  "grupos resulta negativa se toma como cero. La estimación puntual por componentes de varianza (momentos) no exige normalidad; "
                  "la prueba F del efecto entre grupos y el intervalo χ² (gl de Satterthwaite) sí, por lo que solo se informan con residuos "
                  "normales (y la prueba F, además, con varianzas iguales). "
                  "Mide la reproducibilidad dentro del laboratorio (ISO 5725-3 la llama precisión intermedia); la reproducibilidad entre "
                  "laboratorios de ISO 5725-2 es otra magnitud y exige un estudio interlaboratorio."),
        "refs": ["eurachem", "montgomery", "satterthwaite"],
    },
    "reproducibilidad": {
        "titulo": "Reproducibilidad interlaboratorio",
        "texto": ("Solo en estudios interlaboratorio: s_R² = s_L² + s_r², con s_L² = (s_d² − s_r²)/n̄ (ISO 5725-2:1994, ec. 21–24); "
                  "si s_L² resulta negativo se toma como cero (§7.4.5.4)."),
        "refs": ["iso5725_2"],
    },
    "homocedasticidad": {
        "titulo": "Igualdad de varianzas (homocedasticidad): Bartlett, solo con normalidad",
        "texto": ("El ANOVA exige dos supuestos en este orden: residuos normales y varianzas iguales entre grupos (Montgomery, 2017, §3.4). "
                  "Por eso la homocedasticidad solo se evalúa para decidir cuando los residuos son normales, con la prueba de Bartlett "
                  "(H0: todas las varianzas son iguales), que es la de mayor potencia bajo normalidad. Si no se rechaza H0 se usa el ANOVA "
                  "clásico; si se rechaza, el ANOVA de Welch, que no exige varianzas iguales. Si los residuos no son normales no se aplica "
                  "ningún ANOVA: se usa directamente Kruskal-Wallis, y la dispersión se describe con Fligner-Killeen (no paramétrica) "
                  "solo para interpretar si las diferencias son de posición o de forma."),
        "refs": ["bartlett", "conover", "montgomery"],
    },
    "posthoc": {
        "titulo": "Dónde están las diferencias: pruebas post hoc",
        "texto": ("Cuando un factor influye, se compara cada par de niveles para saber exactamente cuáles difieren, controlando el error por "
                  "comparaciones múltiples. La prueba depende de la ruta: Tukey HSD tras un ANOVA clásico (normalidad y varianzas iguales); "
                  "Games-Howell tras un ANOVA de Welch (normalidad con varianzas distintas); Dunn con ajuste de Holm tras Kruskal-Wallis "
                  "(datos no normales, sin ANOVA)."),
        "refs": ["tukey", "welch", "games_howell", "kruskal", "dunn", "holm"],
    },
    "fuentes_variacion": {
        "titulo": "Fuentes de variación: ANOVA factorial (técnico × patrón)",
        "texto": ("Para saber si el resultado depende de quién mide, de con qué patrón se mide o de la combinación de ambos, y SOLO si los "
                  "residuos son normales y las varianzas iguales, se ajusta en cada punto un modelo de análisis de varianza de efectos fijos "
                  "con los factores declarados y su interacción "
                  "(y = μ + αᵢ + βⱼ + (αβ)ᵢⱼ + ε). Cada estadístico F compara la variación atribuible a la fuente con la variación entre réplicas; "
                  "un valor p < α indica que la fuente cambia el resultado medio. La interacción solo es estimable si hay réplicas en cada "
                  "combinación. La contribución porcentual (SC de la fuente / SC total) muestra cuánta de la variación total explica cada fuente. "
                  "Con normalidad pero varianzas distintas se usa el ANOVA de Welch por factor; sin normalidad, la prueba de Kruskal-Wallis "
                  "por factor (rangos), con ε² = H/(N − 1) como tamaño del efecto."),
        "refs": ["montgomery", "welch", "kruskal", "eurachem", "statsmodels"],
    },
    "levene": {
        "titulo": "Homogeneidad de varianzas (Levene, centrado en la mediana)",
        "texto": ("Diagnóstico del supuesto de varianzas homogéneas del ANOVA, robusto frente a desviaciones de la normalidad "
                  "(variante de Brown y Forsythe). Se informa como evidencia; no excluye datos."),
        "refs": ["levene", "brown_forsythe", "scipy"],
    },
    "criterios": {
        "titulo": "Evaluación frente a criterios técnicos",
        "texto": ("La decisión metrológica es distinta de la inferencia estadística: un valor p no establece conformidad y la no "
                  "significación no demuestra equivalencia. El estado CONFORME o NO CONFORME solo se emite cuando existe un criterio "
                  "aprobado, con fuente y regla de decisión documentadas; en otro caso el resultado queda CALCULADO_SIN_EVALUACION "
                  "(ISO/IEC 17025:2017, 7.2 y 7.8.6)."),
        "refs": ["iso17025", "eurachem"],
    },
}

CITAS = {
    "iso5725_1": "ISO, 1994a", "iso5725_2": "ISO, 1994b", "iso17025": "ISO & IEC, 2017", "eurachem": "Magnusson & Örnemark, 2016",
    "vim": "JCGM, 2012", "ema_cenam": "ema & CENAM, 2017", "sae": "SAE, 2025", "shapiro": "Shapiro & Wilk, 1965",
    "royston": "Royston, 1995", "anderson": "Anderson & Darling, 1954", "stephens": "Stephens, 1974",
    "lilliefors": "Lilliefors, 1967", "grubbs1969": "Grubbs, 1969", "grubbs1972": "Grubbs & Beck, 1972",
    "cochran": "Cochran, 1941", "mandel": "Mandel, 1964", "student": "Student, 1908", "wilcoxon": "Wilcoxon, 1945",
    "levene": "Levene, 1960", "brown_forsythe": "Brown & Forsythe, 1974", "satterthwaite": "Satterthwaite, 1946",
    "montgomery": "Montgomery, 2017", "bartlett": "Bartlett, 1937", "welch": "Welch, 1951", "kruskal": "Kruskal & Wallis, 1952",
    "dunn": "Dunn, 1964", "games_howell": "Games & Howell, 1976", "tukey": "Tukey, 1949", "holm": "Holm, 1979", "conover": "Conover et al., 1981", "scipy": "Virtanen et al., 2020", "statsmodels": "Seabold & Perktold, 2010",
}
