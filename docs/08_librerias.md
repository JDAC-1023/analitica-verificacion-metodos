# Librerías utilizadas

> Versiones leídas del entorno real con `importlib.metadata` el 2026-11-01 18:46 · Python 3.13.18 · Linux.

| Librería | Versión instalada | Propósito | Componente | Justificación |
| --- | --- | --- | --- | --- |
| streamlit | 1.66.1 | Interfaz web | interfaz/, app.py | Tecnología definida por el proyecto; componentes nativos, temas y navegación multipágina. |
| pandas | 3.1.0 | Tablas, lectura de CSV/Excel de planificación y construcción de la salida | src/planificacion, src/exportacion | Estándar para manipulación tabular en Python. |
| numpy | 2.5.4 | Dependencia numérica de pandas | (indirecta) | Requerida por pandas. |
| openpyxl | 3.1.5 | Generar y leer la plantilla Excel con estilos, validaciones, protección y hojas ocultas | src/plantillas, src/ingesta | Permite controlar celda a celda el libro .xlsx sin Excel instalado. |
| pyarrow | 26.0.0 | Dependencia de Streamlit para mostrar tablas | (indirecta) | Requerida por Streamlit. |
| pytest | 9.2.0 | Pruebas automatizadas | tests/ | Estándar de pruebas en Python; usado también en GitHub Actions. |
| scipy | 1.18.1 | Distribuciones t, F, χ² y rango estudentizado; Shapiro-Wilk, Wilcoxon, Bartlett, Fligner-Killeen, Kruskal-Wallis | src/motor | Implementaciones de referencia revisadas por pares (Virtanen et al., 2020). |
| statsmodels | 0.15.0 | ANOVA factorial tipo II, Tukey HSD y Lilliefors | src/motor/fuentes.py, src/motor/normalidad.py | Implementaciones de referencia del modelo lineal (Seabold & Perktold, 2010). |
| matplotlib | 3.11.2 | Gráficos de diagnóstico (Q-Q, Mandel h/k, puntos por celda) y fuente DejaVu para el PDF | src/motor/graficos.py, src/informes | Genera PNG sin servidor gráfico; trae fuentes con símbolos ², σ, χ, ≤. |
| reportlab | 5.1.0 | Informe técnico en PDF | src/informes/pdf.py | Solicitado por el equipo; control total de tablas, saltos de página y numeración. |
| pypdf | 6.21.4 | Leer el PDF generado en las pruebas | tests/ | Comprueba el contenido real del informe. |

Biblioteca estándar de Python usada: json, hashlib (SHA-256), zipfile, dataclasses, datetime, pathlib, re, io.

Dependencias agregadas para el motor y el informe: scipy, statsmodels, matplotlib, reportlab y pypdf (con sus dependencias fijadas en `requirements.txt`). `wrapt` se fija en 2.5.2 porque `formulaic` admite versiones preliminares y pip instalaría una de desarrollo. La instalación limpia se comprobó en un entorno nuevo (`pip check` sin conflictos).
