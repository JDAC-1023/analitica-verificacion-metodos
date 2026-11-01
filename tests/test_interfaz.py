"""Pruebas de humo de la interfaz: cada página se ejecuta sin errores con datos sintéticos."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.persistencia.repositorio import RepositorioLocal
from src.servicios.demo import construir_estudio_demo
from src.servicios.flujo import cargar_archivo, preparar_conjunto
from src.plantillas.diligenciar import diligenciar_plantilla
from src.plantillas.generador import generar_plantilla
from tests.conftest import resultados_completos, valores_completos

APP = str(Path(__file__).resolve().parents[1] / "app.py")
PAGINAS = ["inicio", "asistente", "estudios", "diseno", "plantillas", "carga", "calidad", "datos", "analisis", "informes"]


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    monkeypatch.setenv("AVM_DATOS_DIR", str(tmp_path / "datos"))
    repo = RepositorioLocal()
    e = construir_estudio_demo(repo.crear_estudio("Demo", "ana").codigo, "Demo")
    repo.guardar_estudio(e, "ana")
    repo.aprobar_version(e, "ana")
    contenido = diligenciar_plantilla(generar_plantilla(e), valores_completos(e), resultados_completos())
    c = cargar_archivo(repo, e.codigo, contenido, "datos.xlsx", "ana")
    preparar_conjunto(repo, e.codigo, c["carga_id"], ["TR01"], [], "ana")
    from interfaz.comun import repositorio
    repositorio.clear()
    return e


@pytest.mark.parametrize("pagina", PAGINAS)
def test_pagina_sin_errores(entorno, pagina):
    """Entrada: estudio sintético aprobado, con una carga y un conjunto preparado; se abre cada página con el estudio activo.
    Esperado: la página se ejecuta sin excepciones."""
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["estudio_codigo"] = entorno.codigo
    at.session_state["usuario"] = "ana"
    at.run()
    if pagina != "inicio":
        at.switch_page(f"interfaz/paginas/{pagina}.py")
        at.run()
    assert not at.exception, [x.value for x in at.exception]


def test_crear_estudio_desde_la_interfaz(tmp_path, monkeypatch):
    """Entrada: aplicación vacía; el usuario escribe su nombre y crea un estudio desde la página Estudios.
    Esperado: el estudio queda guardado (EST-0001) y seleccionado como estudio activo."""
    monkeypatch.setenv("AVM_DATOS_DIR", str(tmp_path / "vacio"))
    from interfaz.comun import repositorio
    repositorio.clear()
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["usuario"] = "ana"
    at.run()
    at.switch_page("interfaz/paginas/estudios.py")
    at.run()
    next(t for t in at.text_input if t.label == "Nombre del estudio").input("Estudio creado en la interfaz")
    at.button[0].click()
    at.run()
    assert not at.exception
    assert at.session_state["estudio_codigo"] == "EST-0001"
    assert RepositorioLocal(tmp_path / "vacio").obtener_estudio("EST-0001").nombre == "Estudio creado en la interfaz"


@pytest.mark.parametrize("paso", range(1, 15))
@pytest.mark.parametrize("vacio", [False, True])
def test_pasos_del_asistente(entorno, tmp_path, monkeypatch, paso, vacio):
    """Entrada: asistente abierto en cada uno de sus 14 pasos, con un estudio completo (aprobado, con carga) y con un estudio recién creado y vacío.
    Esperado: cada paso se dibuja sin errores."""
    repo = RepositorioLocal()
    if vacio:
        e = repo.crear_estudio("Vacío", "ana")
    else:
        e = repo.obtener_estudio(entorno.codigo)
    e.paso_asistente = paso
    repo.guardar_estudio(e, "ana")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["estudio_codigo"] = e.codigo
    at.session_state["usuario"] = "ana"
    at.run()
    at.switch_page("interfaz/paginas/asistente.py")
    at.run()
    assert not at.exception, [x.value for x in at.exception]


def test_asistente_avanza_y_guarda(entorno):
    """Entrada: estudio nuevo; en el paso 1 se escribe el nombre y se pulsa «Guardar y continuar»; en el paso 2 se pulsa sin completar el método.
    Esperado: el paso 1 se guarda y avanza al 2; en el 2 aparece el error y no avanza."""
    repo = RepositorioLocal()
    e = repo.crear_estudio("Inicial", "ana")
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["estudio_codigo"] = e.codigo
    at.session_state["usuario"] = "ana"
    at.run()
    at.switch_page("interfaz/paginas/asistente.py")
    at.run()
    next(t for t in at.text_input if t.label.startswith("¿Cómo vas a identificar")).input("Estudio de prueba del asistente")
    next(b for b in at.button if b.label == "Guardar y continuar").click()
    at.run()
    guardado = repo.obtener_estudio(e.codigo)
    assert guardado.nombre == "Estudio de prueba del asistente" and guardado.paso_asistente == 2
    next(b for b in at.button if b.label == "Guardar y continuar").click()
    at.run()
    assert any("Completa" in x.value for x in at.error)
    assert repo.obtener_estudio(e.codigo).paso_asistente == 2
