# Librerías utilizadas

> Versiones leídas del entorno real con `importlib.metadata` el 2026-11-01 13:27 · Python 3.13.18 · Linux.

| Librería | Versión instalada | Propósito | Componente | Justificación |
| --- | --- | --- | --- | --- |
| streamlit | 1.66.1 | Interfaz web | interfaz/, app.py | Tecnología definida por el proyecto; componentes nativos, temas y navegación multipágina. |
| pandas | 3.1.0 | Tablas, lectura de CSV/Excel de planificación y construcción de la salida | src/planificacion, src/exportacion | Estándar para manipulación tabular en Python. |
| numpy | 2.5.4 | Dependencia numérica de pandas | (indirecta) | Requerida por pandas. |
| openpyxl | 3.1.5 | Generar y leer la plantilla Excel con estilos, validaciones, protección y hojas ocultas | src/plantillas, src/ingesta | Permite controlar celda a celda el libro .xlsx sin Excel instalado. |
| pyarrow | 26.0.0 | Dependencia de Streamlit para mostrar tablas | (indirecta) | Requerida por Streamlit. |
| pytest | 9.2.0 | Pruebas automatizadas | tests/ | Estándar de pruebas en Python; usado también en GitHub Actions. |

Biblioteca estándar de Python usada: json, hashlib (SHA-256), zipfile, dataclasses, datetime, pathlib, re, io.

No se añadieron dependencias nuevas respecto al entorno existente: `openpyxl` ya estaba instalado, pero faltaba en `requirements.txt` (se agregó, junto con su dependencia `et_xmlfile`). El archivo `requirements.txt` se convirtió de UTF-16 a UTF-8.
