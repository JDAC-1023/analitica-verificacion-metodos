"""Genera la documentación técnica que se deriva directamente del código.

Ejecutar desde la raíz del proyecto:
    python -m herramientas.generar_documentacion

Produce (sobrescribe):
    docs/01_diccionario_datos.md  y  docs/01_diccionario_datos.csv
    docs/04_matriz_reglas_calidad.md  y  docs/04_matriz_reglas_calidad.csv
    docs/07_pruebas.md            (ejecuta pytest y registra el resultado real de cada prueba)
    docs/08_librerias.md          (versiones realmente instaladas)

Así la documentación no puede contradecir al código.
"""

from __future__ import annotations

import importlib
import inspect
import platform
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
DOCS = RAIZ / "docs"
sys.path.insert(0, str(RAIZ))

from src.calidad.reglas import REGLAS, REGLAS_EXCLUIDAS  # noqa: E402
from src.modelos import estudio as modelo  # noqa: E402
from src.transformaciones.catalogo import TRANSFORMACIONES  # noqa: E402


def _md(df: pd.DataFrame) -> str:
    df = df.fillna("").astype(str).map(lambda x: x.replace("|", "\\|").replace("\n", " "))
    cab = "| " + " | ".join(df.columns) + " |\n| " + " | ".join("---" for _ in df.columns) + " |\n"
    return cab + "\n".join("| " + " | ".join(fila) + " |" for fila in df.values.tolist()) + "\n"


# ------------------------------------------------------------------ diccionario
ENTIDADES = [
    ("Estudio", "Configuración y versión del estudio"), ("Magnitud", "Magnitud e intervalo de trabajo"),
    ("Punto", "Punto nominal de medición"), ("Recurso", "Técnico, patrón o equipo"),
    ("Factor", "Condición que se compara o se registra (factor experimental)"),
    ("Restriccion", "Combinación no permitida"), ("Variable", "Dato experimental que se registra"),
    ("ResultadoInteres", "Definición de un resultado de interés (no su valor)"),
    ("Criterio", "Criterio de evaluación vinculado a un resultado"),
    ("MedicionPlanificada", "Medición prevista en el plan aprobado"),
]
PATRON = re.compile(r"^\s{4}(\w+):\s*([^=#]+?)(?:\s*=\s*([^#]+?))?\s*(?:#\s*(.*))?$")


def diccionario() -> pd.DataFrame:
    filas = []
    for nombre, descripcion in ENTIDADES:
        clase = getattr(modelo, nombre)
        for linea in inspect.getsource(clase).splitlines():
            m = PATRON.match(linea)
            if not m or m.group(1) in ("def", "return"):
                continue
            campo, tipo, defecto, comentario = m.groups()
            if linea.strip().startswith(("def ", "@", "return")):
                continue
            codigos = ", ".join(dict.fromkeys(re.findall(r"\b[EDRVCPX]\d{2}(?:-[EDRVCPX]?\d{2})?\b", comentario or "")))
            filas.append({"Entidad": nombre, "Descripción de la entidad": descripcion, "Campo": campo, "Tipo": tipo.strip(),
                          "Valor por defecto": (defecto or "obligatorio al crear").strip(), "Campo(s) de la matriz": codigos,
                          "Nota": (comentario or "").strip()})
    dominios = [
        ("Estudio.tipo", modelo.TIPOS_ESTUDIO), ("Variable.tipo_dato", modelo.TIPOS_DATO),
        ("Variable.categoria", modelo.CATEGORIAS_VARIABLE), ("Factor.tipo_valor", modelo.TIPOS_VALOR_FACTOR),
        ("Factor.vinculo_recurso", modelo.VINCULOS_RECURSO), ("Factor.rol", modelo.ROLES_FACTOR),
        ("ResultadoInteres.origen", modelo.ORIGENES_RESULTADO), ("ResultadoInteres.ambito", modelo.AMBITOS_RESULTADO),
        ("ResultadoInteres.proposito", modelo.PROPOSITOS_RESULTADO), ("Estudio.estado", modelo.ESTADOS_DISENO),
    ]
    return pd.DataFrame(filas), pd.DataFrame([{"Campo": c, "Valores permitidos": ", ".join(v)} for c, v in dominios])


def escribir_diccionario() -> None:
    df, dominios = diccionario()
    df.to_csv(DOCS / "01_diccionario_datos.csv", index=False, encoding="utf-8-sig")
    texto = ["# Diccionario de datos · configuración del estudio\n",
             "> Generado automáticamente desde `src/modelos/estudio.py` por `herramientas/generar_documentacion.py`. "
             "No editar a mano: editar el modelo y volver a generar.\n",
             "La columna «Campo(s) de la matriz» vincula cada atributo con el campo de la *Matriz de parametrización v0.2*. "
             "El diccionario de la **salida para el motor** está en `09_salida_para_el_motor.md`.\n"]
    for entidad, grupo in df.groupby("Entidad", sort=False):
        texto.append(f"\n## {entidad}\n\n{grupo['Descripción de la entidad'].iloc[0]}.\n\n")
        texto.append(_md(grupo[["Campo", "Tipo", "Valor por defecto", "Campo(s) de la matriz", "Nota"]]))
    texto.append("\n## Dominios (listas cerradas)\n\n" + _md(dominios))
    (DOCS / "01_diccionario_datos.md").write_text("".join(texto), encoding="utf-8")


# ------------------------------------------------------------------ reglas
def escribir_reglas() -> None:
    df = pd.DataFrame([r.to_dict() for r in REGLAS.values()]).rename(columns={
        "codigo": "Código", "nombre": "Nombre", "descripcion": "Descripción", "aplica_a": "Aplica a", "condicion": "Condición evaluada",
        "tipo_incidencia": "Tipo de incidencia", "severidad": "Severidad", "tratamiento": "Tratamiento permitido",
        "mensaje": "Mensaje para el usuario", "conserva": "Información que se conserva", "prueba": "Prueba que lo demuestra"})
    df.to_csv(DOCS / "04_matriz_reglas_calidad.csv", index=False, encoding="utf-8-sig")
    trans = pd.DataFrame([t.to_dict() for t in TRANSFORMACIONES.values()]).rename(columns={
        "codigo": "Código", "nombre": "Nombre", "descripcion": "Descripción", "ejemplo": "Ejemplo", "por_defecto": "Autorizada por defecto"})
    texto = ["# Matriz de reglas de calidad de datos\n\n",
             "> Generada desde `src/calidad/reglas.py`. Cada regla tiene una prueba automatizada que demuestra su funcionamiento.\n\n",
             "Las reglas evalúan **calidad estructural** (formato, correspondencia con el diseño, completitud, tipos, identificadores). "
             "No evalúan estadísticamente los resultados.\n\n",
             "**Severidades:** `bloquea_archivo` rechaza el archivo completo · `excluye_registro` saca el registro del conjunto con motivo automático · "
             "`pendiente` deja el registro pendiente de corrección · `advertencia` conserva el registro e informa.\n\n",
             "## Reglas\n\n", _md(df),
             "\n## Transformaciones autorizables\n\nNinguna cambia el valor, el signo, las cifras ni la unidad. Cada aplicación se registra con la celda, "
             "el valor original y el valor interpretado.\n\n", _md(trans),
             "\n## Reglas que se decidió no implementar\n\n", _md(pd.DataFrame(REGLAS_EXCLUIDAS, columns=["Regla", "Motivo"])),
             "\n## Estados de un registro\n\n",
             _md(pd.DataFrame([
                 ("aceptado", "Superó todas las reglas sin transformaciones", "Sí"),
                 ("normalizado", "Superó las reglas tras una transformación autorizada", "Sí"),
                 ("con_advertencia", "Tiene advertencias, sin errores", "Sí"),
                 ("pendiente", "Tiene al menos un error de registro; requiere corrección", "No"),
                 ("excluido", "Excluido con motivo (automático o manual documentado)", "No"),
                 ("rechazado", "El archivo completo fue rechazado", "No"),
             ], columns=["Estado", "Significado", "¿Entra al conjunto preparado?"])),
             "\nPrecedencia: excluido > pendiente > con_advertencia > normalizado > aceptado. "
             "Conciliación: recibidos = aceptados + normalizados + con advertencia + pendientes + excluidos + rechazados.\n"]
    (DOCS / "04_matriz_reglas_calidad.md").write_text("".join(texto), encoding="utf-8")


# ------------------------------------------------------------------ librerías
LIBRERIAS = [
    ("streamlit", "Interfaz web", "interfaz/, app.py", "Tecnología definida por el proyecto; componentes nativos, temas y navegación multipágina."),
    ("pandas", "Tablas, lectura de CSV/Excel de planificación y construcción de la salida", "src/planificacion, src/exportacion", "Estándar para manipulación tabular en Python."),
    ("numpy", "Dependencia numérica de pandas", "(indirecta)", "Requerida por pandas."),
    ("openpyxl", "Generar y leer la plantilla Excel con estilos, validaciones, protección y hojas ocultas", "src/plantillas, src/ingesta", "Permite controlar celda a celda el libro .xlsx sin Excel instalado."),
    ("pyarrow", "Dependencia de Streamlit para mostrar tablas", "(indirecta)", "Requerida por Streamlit."),
    ("pytest", "Pruebas automatizadas", "tests/", "Estándar de pruebas en Python; usado también en GitHub Actions."),
]


def escribir_librerias() -> None:
    filas = []
    for nombre, proposito, componente, justificacion in LIBRERIAS:
        try:
            v = version(nombre)
        except PackageNotFoundError:
            v = "no instalada"
        filas.append({"Librería": nombre, "Versión instalada": v, "Propósito": proposito, "Componente": componente, "Justificación": justificacion})
    estandar = "json, hashlib (SHA-256), zipfile, dataclasses, datetime, pathlib, re, io"
    texto = ["# Librerías utilizadas\n\n",
             f"> Versiones leídas del entorno real con `importlib.metadata` el {datetime.now():%Y-%m-%d %H:%M} · Python {platform.python_version()} · {platform.system()}.\n\n",
             _md(pd.DataFrame(filas)),
             f"\nBiblioteca estándar de Python usada: {estandar}.\n\n",
             "No se añadieron dependencias nuevas respecto al entorno existente: `openpyxl` ya estaba instalado, pero faltaba en `requirements.txt` "
             "(se agregó, junto con su dependencia `et_xmlfile`). El archivo `requirements.txt` se convirtió de UTF-16 a UTF-8.\n"]
    (DOCS / "08_librerias.md").write_text("".join(texto), encoding="utf-8")


# ------------------------------------------------------------------ pruebas
def _docstring(nodeid: str) -> tuple[str, str]:
    archivo, _, nombre = nodeid.partition("::")
    nombre = nombre.split("[")[0]
    modulo = importlib.import_module(archivo.replace("/", ".").removesuffix(".py"))
    doc = inspect.getdoc(getattr(modulo, nombre)) or ""
    entrada = re.search(r"Entrada:\s*(.*?)(?:\n\s*Esperado:|$)", doc, re.S)
    esperado = re.search(r"Esperado:\s*(.*)$", doc, re.S)
    limpiar = lambda m: " ".join(m.group(1).split()) if m else ""  # noqa: E731
    return limpiar(entrada), limpiar(esperado)


def escribir_pruebas() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        xml = Path(tmp) / "resultado.xml"
        proceso = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", f"--junitxml={xml}"],
                                 cwd=RAIZ, capture_output=True, text=True)
        arbol = ET.parse(xml)
    filas = []
    for caso in arbol.iter("testcase"):
        archivo = caso.get("classname").replace(".", "/") + ".py"
        nodeid = f"{archivo}::{caso.get('name')}"
        fallo = caso.find("failure") if caso.find("failure") is not None else caso.find("error")
        omitida = caso.find("skipped") is not None
        resultado = "Fallida" if fallo is not None else ("Omitida" if omitida else "Aprobada")
        entrada, esperado = _docstring(nodeid)
        filas.append({"Prueba": f"`{caso.get('name')}`", "Archivo": archivo.split("/")[-1], "Entrada": entrada,
                      "Resultado esperado": esperado,
                      "Resultado obtenido": resultado + (f" — {fallo.get('message', '')[:200]}" if fallo is not None else ""),
                      "Tiempo (s)": f"{float(caso.get('time')):.3f}"})
    df = pd.DataFrame(filas)
    resumen = df["Resultado obtenido"].str.split(" —").str[0].value_counts().to_dict()
    texto = ["# Pruebas realizadas\n\n",
             f"> Generado ejecutando `pytest` el {datetime.now():%Y-%m-%d %H:%M} · Python {platform.python_version()} · "
             f"{platform.system()} · pytest {version('pytest')}. Resultado: {resumen}.\n\n",
             "Todas las pruebas usan **datos sintéticos** (estudio de ejemplo de 16 mediciones: 2 puntos × 2 técnicos × 2 días × 2 repeticiones). "
             "La «entrada» y el «resultado esperado» se toman del docstring de cada prueba; el «resultado obtenido» es el de esta ejecución.\n\n",
             _md(df),
             "\n## Cobertura de los casos solicitados\n\n",
             _md(pd.DataFrame([
                 ("Configuración y guardado de un estudio", "test_guardar_y_recuperar_estudio"),
                 ("Cantidades variables de técnicos, patrones, puntos y condiciones", "test_cantidades_variables_de_recursos_puntos_y_condiciones"),
                 ("Plantilla coherente con el diseño", "test_plantilla_coherente_con_el_diseno, test_metadatos_de_control_y_proteccion"),
                 ("Lectura correcta de la plantilla", "test_lectura_correcta, test_plantilla_reordenada_se_lee"),
                 ("Archivo incompleto", "test_hoja_mediciones_ausente_rechaza, test_archivo_no_excel_se_rechaza"),
                 ("Valores faltantes", "test_valores_faltantes_obligatorios"),
                 ("Tipos de dato incompatibles", "test_tipo_de_dato_incompatible"),
                 ("Identificadores desconocidos", "test_identificador_desconocido_se_excluye, test_fila_sin_identificador_se_excluye"),
                 ("Mediciones previstas ausentes", "test_medicion_planificada_ausente"),
                 ("Registros duplicados", "test_registros_duplicados_quedan_pendientes"),
                 ("Versiones incompatibles", "test_version_incompatible, test_archivo_de_otro_estudio, test_formato_de_plantilla_incompatible"),
                 ("Transformaciones permitidas", "test_transformaciones_permitidas"),
                 ("Exclusiones documentadas", "test_exclusion_documentada"),
                 ("Conservación del archivo original", "test_conservacion_del_archivo_original"),
                 ("Exportación del conjunto preparado", "test_exportacion_del_conjunto_preparado"),
                 ("Reproducibilidad de la salida", "test_reproducibilidad_de_la_salida, test_integridad_detecta_modificacion"),
                 ("Persistencia entre sesiones", "test_persistencia_entre_sesiones"),
             ], columns=["Caso solicitado", "Prueba(s)"])),
             "\n## Limitaciones de las pruebas\n\n"
             "- Las pruebas de interfaz (`test_interfaz.py`) comprueban que cada página se ejecuta sin errores y que se puede crear un estudio; "
             "no evalúan la apariencia. La apariencia se revisó con capturas reales (`10_capturas.md`).\n"
             "- La compatibilidad con Excel se comprobó leyendo y escribiendo los archivos con openpyxl; abrir la plantilla en Microsoft Excel "
             "para Windows debe verificarse manualmente (validaciones de celda, protección y listas).\n"
             "- No se probaron archivos reales del laboratorio: solo datos sintéticos.\n"]
    (DOCS / "07_pruebas.md").write_text("".join(texto), encoding="utf-8")
    print(proceso.stdout[-400:])
    return proceso.returncode


if __name__ == "__main__":
    DOCS.mkdir(exist_ok=True)
    escribir_diccionario()
    escribir_reglas()
    escribir_librerias()
    codigo = escribir_pruebas()
    print("Documentación generada en", DOCS)
    sys.exit(codigo)
