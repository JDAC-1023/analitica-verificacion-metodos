"""Datos reales del laboratorio: carga a la base de datos por el flujo normal, procesamiento con el motor y contraste
con los informes técnicos (temperatura y humedad relativa)."""

import pytest

from src.contraste.laboratorio import contrastar, reproducir
from src.motor.multi import partes
from src.servicios.estudios_reales import (CARPETA_REALES, ErrorDatosReales, asegurar_estudios_reales, crear_estudio_real,
                                           leer_libro)

ARCH = {"temperatura": "data_temperatura.xlsx", "humedad": "DATA_HUMEDAD.xlsx"}


@pytest.fixture(scope="module")
def reales(tmp_path_factory):
    import os
    from src.persistencia.repositorio import RepositorioLocal
    anterior = os.environ.get("AVM_DATOS_DIR")
    os.environ["AVM_DATOS_DIR"] = str(tmp_path_factory.mktemp("reales"))
    repo = RepositorioLocal()
    creados = asegurar_estudios_reales(repo, "ana")
    yield repo, {x["magnitud"]: x for x in creados}
    if anterior is None:
        os.environ.pop("AVM_DATOS_DIR", None)
    else:
        os.environ["AVM_DATOS_DIR"] = anterior


def test_libros_se_leen_sin_modificar(reales):
    """Entrada: los dos libros del laboratorio. Esperado: 45 lecturas (3 puntos × 3 operadores × 5 tiempos) por magnitud,
    valores idénticos al Excel (sin redondeo) y los valores repetidos de humedad señalados como advertencia, no corregidos."""
    import openpyxl
    for mag, arch in ARCH.items():
        lib = leer_libro((CARPETA_REALES / arch).read_bytes())
        assert len(lib.datos) == 45 and lib.datos["nominal"].nunique() == 3 and lib.datos["operador"].nunique() == 3
        ws = openpyxl.load_workbook(CARPETA_REALES / arch, data_only=True).worksheets[0]
        assert lib.datos["Corrección"].iloc[0] == ws.cell(2, 4).value
        assert len(lib.anova_lab) == 9 and len(lib.componentes_lab) == 3
    hum = leer_libro((CARPETA_REALES / ARCH["humedad"]).read_bytes())
    assert any("Camara_95HR · Brandon · Corrección" in a and "T3, T4, T5" in a for a in hum.advertencias)


def test_carga_real_por_el_flujo_de_la_base_de_datos(reales):
    """Entrada: estudios creados desde los libros. Esperado: diseño aprobado, carga leída, 45 registros aceptados e
    incluidos, conjunto aprobado y análisis guardado con los tres resultados; sin límites → CALCULADO_SIN_EVALUACION."""
    repo, creados = reales
    for mag, x in creados.items():
        assert x["mediciones"] == 45 and x["conteos"]["incluidos_en_preparado"] == 45 and x["conteos"]["excluidos"] == 0
        total = repo.obtener_analisis(x["codigo"], 1)["resultado"]
        assert [p["objeto"]["nombre"] for p in partes(total)] == ["Corrección", "Inestabilidad", "Inhomogeneidad"]
        assert total["conclusion_final"]["estado"] == "CALCULADO_SIN_EVALUACION"
        assert repo.obtener_estudio(x["codigo"]).estado == "aprobado"


def test_motor_reproduce_el_informe(reales):
    """Entrada: resultado del motor y valores impresos en los informes. Esperado: ANOVA Operador + Tiempo igual al
    informe (|Δp| < 1e-6), Bartlett por operador igual (|Δp| < 1e-4), las 36 decisiones por magnitud coinciden y u_lab
    de la precisión intermedia es idéntica a la hoja del laboratorio."""
    repo, creados = reales
    for mag, x in creados.items():
        lib = leer_libro((CARPETA_REALES / ARCH[mag]).read_bytes())
        t = contrastar(mag, lib.datos, repo.obtener_analisis(x["codigo"], 1)["resultado"], lib.componentes_lab)
        c = t["comparacion"]
        an = c[c["prueba"].str.startswith("ANOVA") & c["prueba"].str.endswith("(p)")]
        assert an["dif_motor"].max() < 1e-6
        assert c[c["prueba"] == "Bartlett por operador (p)"]["dif_motor"].max() < 1e-4
        assert int(t["resumen"]["comparaciones"].sum()) == 36 and int(t["resumen"]["coincidencias"].sum()) == 36
        assert t["componentes"]["dif_u_lab"].max() < 1e-12


def test_inhomogeneidad_50hr_operador_significativo_sin_pares(reales):
    """Entrada: humedad, inhomogeneidad a 50 %hr. Esperado: como en el informe, el ANOVA marca al operador (p ≈ 0,0439)
    pero Tukey no encuentra ningún par de operadores distinto."""
    repo, creados = reales
    total = repo.obtener_analisis(creados["humedad"]["codigo"], 1)["resultado"]
    inh = next(p for p in partes(total) if p["objeto"]["nombre"] == "Inhomogeneidad")
    fv = next(y for y in inh["resultados"] if y["caracteristica"] == "fuentes_variacion" and "50 %hr" in y["agrupacion"])
    op = next(f for f in fv["estimacion"]["anova"] if f["fuente"] == "Operador")
    assert abs(op["p"] - 0.043862) < 1e-6 and op["influye"]
    assert fv["estimacion"]["posthoc"] and not any(x["significativa"] for x in fv["estimacion"]["posthoc"])


def test_reproduccion_independiente_coincide_con_informe():
    """Entrada: datos de humedad. Esperado: Shapiro-Wilk sobre las 15 lecturas reproduce W y p del informe a 4 decimales."""
    lib = leer_libro((CARPETA_REALES / ARCH["humedad"]).read_bytes())
    rep = reproducir(lib.datos)
    fila = rep[(rep["punto"] == "10 %hr") & (rep["variable"] == "Corrección")].iloc[0]
    assert round(fila["shapiro_W"], 4) == 0.8963 and round(fila["shapiro_p"], 4) == 0.0836


def test_libro_invalido_se_rechaza(tmp_path):
    """Entrada: libro sin hojas «Camara_…». Esperado: ErrorDatosReales con mensaje claro (no se crea nada)."""
    import io
    from openpyxl import Workbook
    wb = Workbook()
    buf = io.BytesIO()
    wb.save(buf)
    with pytest.raises(ErrorDatosReales):
        leer_libro(buf.getvalue())


def test_no_duplica_estudios_reales(reales):
    """Entrada: segunda llamada a asegurar_estudios_reales. Esperado: no crea estudios nuevos."""
    repo, _ = reales
    assert asegurar_estudios_reales(repo, "ana") == []


def test_pagina_contraste(reales):
    """Entrada: página «Contraste con datos reales». Esperado: se abre sin errores y muestra datos, motor y comparación."""
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "app.py"), default_timeout=180)
    at.session_state["usuario"] = "ana"
    at.run()
    at.switch_page("interfaz/paginas/contraste.py")
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    textos = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "Conjunto de datos" in textos and "RESULTADOS GENERADOS POR EL SISTEMA" in textos


def test_estabilidad_intervalo_wilson():
    """Entrada: 30 de 30 y 0 de 30. Esperado: intervalos de Wilson [0,886; 1] y [0; 0,114] (95 %)."""
    from herramientas.estabilidad import wilson
    lo, hi = wilson(30, 30)
    assert round(lo, 3) == 0.886 and hi == 1.0
    lo, hi = wilson(0, 30)
    assert lo == 0.0 and round(hi, 3) == 0.114
