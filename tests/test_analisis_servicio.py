"""Servicio de análisis: ejecución sobre el conjunto aprobado, inmutabilidad, versión 2, comentarios, clonación e informe PDF."""

import pytest
from pypdf import PdfReader

from src.informes.pdf import generar_informe
from src.motor.configuracion import CaracteristicaConfig, CriterioMotor, Exclusion, ReglaDerivacion
from src.persistencia.repositorio import ErrorRepositorio
from src.servicios.analisis import (ErrorAnalisis, bitacora_analisis, derivar_version, ejecutar_analisis, historial,
                                    nueva_configuracion)
from src.servicios.flujo import aprobar_conjunto, cargar_archivo, preparar_conjunto


@pytest.fixture
def preparado(repo, estudio_aprobado, archivo_completo):
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    return preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [], "ana")


def _cfg(repo, e, prep):
    cfg = nueva_configuracion(repo, e.codigo, prep["preparacion_id"], "ana")
    cfg.objeto_tipo, cfg.objeto_id = "derivado", "R-01"
    cfg.regla = ReglaDerivacion("diferencia", "V-01", "V-02", "Procedimiento PC-07 §5", True)
    cfg.metodo_validado = "si"
    cfg.factores_precision_intermedia = ["F-01", "F-02"]
    cfg.referencia_tipo = "objeto_es_diferencia"
    cfg.caracteristicas = [CaracteristicaConfig("sesgo", "REQUERIDA"), CaracteristicaConfig("repetibilidad", "REQUERIDA")]
    cfg.criterios = [CriterioMotor("CM-01", "sesgo", "abs_sesgo", "<=", 0.5, "°C", "estimacion", "PC-07", True)]
    return cfg


def test_no_analiza_conjunto_sin_aprobar(repo, estudio_aprobado, preparado):
    """Entrada: conjunto preparado sin aprobar. Esperado: ErrorAnalisis; no se guarda resultado."""
    with pytest.raises(ErrorAnalisis):
        ejecutar_analisis(repo, _cfg(repo, estudio_aprobado, preparado), "ana")


def test_flujo_completo_version2_comentarios_e_informe(repo, estudio_aprobado, preparado):
    """Entrada: conjunto aprobado; análisis v1 del error (V-01 − V-02, regla aprobada); comentario; v2 con exclusión; informe PDF.
    Esperado: v1 inmutable, v2 con padre v1 y diferencia «exclusiones», comentario guardado y bitácora con cada acción;
    el PDF se abre e incluye control, marco teórico, comentarios y referencias."""
    e = estudio_aprobado
    aprobar_conjunto(repo, e.codigo, preparado["preparacion_id"], "ana")
    cfg = _cfg(repo, e, preparado)
    r1 = ejecutar_analisis(repo, cfg, "ana")
    assert r1["objeto"]["unidad"] == "°C" and len(r1["datos"]) == 16
    assert r1["meta"]["sha256_original"] == preparado["sha256_original"]
    with pytest.raises(ErrorRepositorio):
        repo.guardar_config_analisis(e.codigo, cfg.to_dict())
    repo.agregar_comentario(e.codigo, 1, "atipicos", "Revisada la bitácora: sin eventos.", "Revisor")
    with pytest.raises(ErrorAnalisis):
        derivar_version(repo, e.codigo, 1, " ", "ana")
    with pytest.raises(ErrorAnalisis):
        derivar_version(repo, e.codigo, 1, "Exclusión", "ana", exclusiones=[Exclusion("M0001", "", "QA")])
    v2 = derivar_version(repo, e.codigo, 1, "Exclusión por falla registrada", "ana",
                         exclusiones=[Exclusion("M0001", "Falla de lectura en bitácora", "QA")])
    assert v2.version == 2 and v2.padre == 1
    r2 = ejecutar_analisis(repo, v2, "ana")
    assert len(r2["datos"]) == 15
    h = historial(repo, e.codigo)
    assert [c["campo"] for c in h[1]["cambios"]] == ["exclusiones"]
    acciones = [b["accion"] for b in bitacora_analisis(repo, e.codigo)]
    for a in ("analisis_ejecutado", "comentario_analisis", "analisis_version_derivada"):
        assert a in acciones
    guardado = repo.obtener_analisis(e.codigo, 1)
    estudio_v, _ = repo.obtener_version(e.codigo, 1)
    pdf = generar_informe(guardado["resultado"], guardado["config"], estudio_v, guardado["comentarios"], h,
                          bitacora_analisis(repo, e.codigo), {"fecha": "2026-11-01", "elaborado_por": "ana",
                                                              "revisado_por": "Juan David", "autorizado_por": "Dirección técnica"})
    nombre = repo.guardar_informe(e.codigo, 1, pdf, {"fecha": "2026-11-01", "emitido_por": "ana"})
    assert repo.obtener_informe(e.codigo, 1, nombre) == pdf and repo.listar_informes(e.codigo)
    texto = " ".join(p.extract_text() for p in PdfReader(__import__("io").BytesIO(pdf)).pages)
    for fragmento in ("Elaboró", "Revisó", "Autorizó", "Juan David", "Marco teórico", "Revisada la bitácora",
                      "Referencias", "Shapiro, S. S., & Wilk", "Página 1 de", "CONFORME"):
        assert fragmento in texto, fragmento


def test_clonar_estudio(repo, estudio_aprobado):
    """Entrada: «Clonar estudio» sobre un estudio aprobado. Esperado: estudio nuevo en borrador, mismo plan, con «derivado de»."""
    clon = repo.clonar_estudio(estudio_aprobado.codigo, "Rediseño", "ana")
    assert clon.codigo != estudio_aprobado.codigo and clon.estado == "borrador" and clon.version_diseno == 0
    assert clon.derivado_de == f"{estudio_aprobado.codigo} v1" and len(clon.plan) == len(estudio_aprobado.plan)
    assert repo.obtener_estudio(clon.codigo).nombre == "Rediseño"


def test_crear_estudios_de_prueba(repo):
    """Entrada: las 4 plantillas diligenciadas de data/estudios_prueba. Esperado: 4 estudios aprobados, 288 mediciones
    aceptadas cada uno, conjunto aprobado y análisis v1 de la corrección ejecutado sin criterios; volver a pulsar no duplica."""
    from src.servicios.estudios_prueba import crear_estudios_prueba
    creados = crear_estudios_prueba(repo, "ana")
    assert len(creados) == 4
    for x in creados:
        assert x["mediciones"] == 288 and x["conteos"]["aceptados"] == 288 and x["analisis"] == "CALCULADO_SIN_EVALUACION"
        r = repo.obtener_analisis(x["codigo"], 1)["resultado"]
        assert r["objeto"]["nombre"] == "Corrección" and len(r["datos"]) == 288
    assert all("omitido" in x for x in crear_estudios_prueba(repo, "ana"))
