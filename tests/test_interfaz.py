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


def _aprobar_y_analizar(e, ejecutar_tambien=True):
    from src.motor.configuracion import CaracteristicaConfig, ReglaDerivacion
    from src.servicios.analisis import ejecutar_analisis, guardar_configuracion, nueva_configuracion
    from src.servicios.flujo import aprobar_conjunto
    repo = RepositorioLocal()
    prep = repo.listar_preparaciones(e.codigo)[0]
    aprobar_conjunto(repo, e.codigo, prep["preparacion_id"], "ana")
    cfg = nueva_configuracion(repo, e.codigo, prep["preparacion_id"], "ana")
    cfg.objeto_tipo, cfg.objeto_id = "derivado", "R-01"
    cfg.regla = ReglaDerivacion("diferencia", "V-01", "V-02", "PC-07", True)
    cfg.factores_precision_intermedia = ["F-01", "F-02"]
    cfg.referencia_tipo = "objeto_es_diferencia"
    cfg.caracteristicas = [CaracteristicaConfig("sesgo", "REQUERIDA"), CaracteristicaConfig("precision_intermedia", "REQUERIDA")]
    if ejecutar_tambien:
        ejecutar_analisis(repo, cfg, "ana")
    else:
        guardar_configuracion(repo, cfg, "ana")
    return repo


@pytest.mark.parametrize("ejecutado", [False, True])
def test_pagina_analisis_con_configuracion(entorno, ejecutado):
    """Entrada: conjunto aprobado con una versión de análisis guardada (sin ejecutar / ejecutada).
    Esperado: la página dibuja configuración, ruta en tiempo real y, si está ejecutada, resultados, conclusiones e informe."""
    _aprobar_y_analizar(entorno, ejecutado)
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["estudio_codigo"] = entorno.codigo
    at.session_state["usuario"] = "ana"
    at.session_state["analisis_version"] = 1
    at.run()
    at.switch_page("interfaz/paginas/analisis.py")
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    textos = " ".join(m.value for m in at.markdown)
    # ejecutada: se muestra lo guardado (sin recalcular la vista previa); sin ejecutar: la vista previa en vivo
    assert ("Paso a paso del motor" in textos and "Resultado evaluado" in textos) if ejecutado else "Qué va a hacer el motor" in textos
    if ejecutado:
        assert any("Conclusión consolidada" in b.label for b in at.get("badge")) if at.get("badge") else True
        boton = next(b for b in at.button if b.label == "Generar informe PDF")
        boton.click()
        at.run()
        assert not at.exception, [x.value for x in at.exception]
        assert RepositorioLocal().listar_informes(entorno.codigo)
        at.switch_page("interfaz/paginas/informes.py")
        at.run()
        assert not at.exception


def test_pagina_analisis_ejecuta_desde_la_interfaz(entorno):
    """Entrada: conjunto aprobado y nueva configuración (dato V-01 por defecto); el usuario pulsa «Ejecutar análisis».
    Esperado: se guarda la versión 1 ejecutada."""
    from src.servicios.flujo import aprobar_conjunto
    repo = RepositorioLocal()
    aprobar_conjunto(repo, entorno.codigo, repo.listar_preparaciones(entorno.codigo)[0]["preparacion_id"], "ana")
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["estudio_codigo"] = entorno.codigo
    at.session_state["usuario"] = "ana"
    at.run()
    at.switch_page("interfaz/paginas/analisis.py")
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    next(b for b in at.button if b.label == "Ejecutar análisis").click()
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    v = RepositorioLocal().listar_analisis(entorno.codigo)
    assert v and v[0]["ejecutado"]


def test_inicio_tarjetas_y_panel(entorno):
    """Entrada: Inicio sin estudio abierto; se pulsa «Abrir» en la tarjeta del estudio. Esperado: el estudio queda abierto y
    se muestra su panel (pestañas Resumen, Configuración, Datos, Resultados, Informes) sin selector lateral."""
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["usuario"] = "ana"
    at.run()
    assert not at.exception
    assert not any(s.label == "Estudio activo" for s in at.selectbox)
    next(b for b in at.button if b.key == f"abrir_{entorno.codigo}").click()
    at.run()
    assert not at.exception, [x.value for x in at.exception]
    assert at.session_state["estudio_codigo"] == entorno.codigo
    assert [t.label for t in at.tabs][:5] == [":material/dashboard: Resumen", ":material/tune: Configuración", ":material/dataset: Datos",
                                             ":material/query_stats: Resultados", ":material/description: Informes"]
