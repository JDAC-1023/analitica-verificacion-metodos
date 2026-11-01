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
    for fragmento in ("Elaboró", "Revisó", "Autorizó", "Juan David", "Resumen en lenguaje sencillo", "Fundamento", "Revisada la bitácora",
                      "Referencias", "Shapiro, S. S., & Wilk", "Página 1 de", "CONFORME"):
        assert fragmento in texto, fragmento


def test_clonar_estudio(repo, estudio_aprobado):
    """Entrada: «Clonar estudio» sobre un estudio aprobado. Esperado: estudio nuevo en borrador, mismo plan, con «derivado de»."""
    clon = repo.clonar_estudio(estudio_aprobado.codigo, "Rediseño", "ana")
    assert clon.codigo != estudio_aprobado.codigo and clon.estado == "borrador" and clon.version_diseno == 0
    assert clon.derivado_de == f"{estudio_aprobado.codigo} v1" and len(clon.plan) == len(estudio_aprobado.plan)
    assert repo.obtener_estudio(clon.codigo).nombre == "Rediseño"


def test_crear_estudios_de_prueba(repo):
    """Entrada: las 4 bases sintéticas de data/estudios_prueba (8 temperaturas × 3 técnicos × 2 patrones × 5 lecturas, con errores
    sembrados). Esperado: Testeo 1–4 creados con el mismo flujo que un usuario; la limpieza normaliza 2 registros (TR02, TR03+TR04),
    deja 1 pendiente (dato vacío) y 1 con advertencia (hora); el motor da NO CUMPLE / CUMPLE / NO CUMPLE / CUMPLE CON OBSERVACIONES;
    detecta la lectura anómala sembrada (M0063), la serie incompleta y la influencia del técnico en el Testeo 1; no duplica al repetir."""
    from src.servicios.estudios_prueba import crear_estudios_prueba
    creados = crear_estudios_prueba(repo, "ana")
    assert [x["nombre"] for x in creados] == ["Testeo 1", "Testeo 2", "Testeo 3", "Testeo 4"]
    esperado = ["NO_CONFORME", "CONFORME", "NO_CONFORME", "CONFORME_CON_OBSERVACIONES"]
    for x, est in zip(creados, esperado):
        c = x["conteos"]
        assert x["mediciones"] == 240 and c["normalizados"] == 2 and c["pendientes"] == 1 and c["con_advertencia"] == 1
        assert x["analisis"] == est, (x["nombre"], x["analisis"])
        r = repo.obtener_analisis(x["codigo"], 1)["resultado"]
        assert r["objeto"]["nombre"] == "Corrección" and len(r["datos"]) == 239
        series = next(y for y in r["resultados"] if y["tecnica"].startswith("Réplicas por serie"))
        assert series["estimacion"]["valor"] == 1 and series["tabla"][0]["válidas"] == 4
    r1 = repo.obtener_analisis(creados[0]["codigo"], 1)["resultado"]
    marcadas = {t.get("medicion_id") for y in r1["resultados"] if y["etapa"] == "atipicos" for t in y["tabla"]
                if t.get("clasificacion") in ("rezagado (*)", "atípico (**)")}
    assert "M0063" in marcadas
    fv = [y for y in r1["resultados"] if y["caracteristica"] == "fuentes_variacion" and y["estado"] == "APLICABLE"]
    assert len(fv) == 8 and all("Técnico" in y["estimacion"]["influyen"] for y in fv)
    assert all("omitido" in x for x in crear_estudios_prueba(repo, "ana"))


def test_flujo_condicional_y_veredicto(repo):
    """Entrada: Testeo 1–4. Esperado: el paso a paso sigue el orden datos → atípicos → normalidad → homocedasticidad → comparación de
    condiciones → sesgo → repetibilidad → reproducibilidad intralaboratorio → veredicto; el veredicto dice si el método sirve; en el
    Testeo 1 el atípico sembrado explica el incumplimiento de repetibilidad en −20 °C (sensibilidad) y el técnico T-03 aparece como
    origen de las diferencias."""
    from src.motor import flujo
    from src.servicios.estudios_prueba import crear_estudios_prueba
    creados = crear_estudios_prueba(repo, "ana")
    titulos = []
    for x in creados:
        r = repo.obtener_analisis(x["codigo"], 1)["resultado"]
        pasos = [p["paso"] for p in flujo.pasos(r)]
        assert pasos == ["Datos", "¿Hay datos atípicos?", "¿Los datos son normales?", "¿Las varianzas son iguales (homocedasticidad)?",
                         "¿El resultado depende del técnico o del patrón?", "Sesgo (veracidad)", "Repetibilidad",
                         "Reproducibilidad intralaboratorio", "Veredicto"]
        titulos.append(flujo.veredicto(r)["titulo"])
    assert titulos == ["TU MÉTODO NO SIRVE (TODAVÍA)", "TU MÉTODO SIRVE", "TU MÉTODO NO SIRVE (TODAVÍA)", "TU MÉTODO SIRVE, CON OBSERVACIONES"]
    r1 = repo.obtener_analisis(creados[0]["codigo"], 1)["resultado"]
    cambio = [c for c in r1["sensibilidad"]["cambios"] if c["cambia_decision"]]
    assert cambio and cambio[0]["caracteristica"] == "repetibilidad" and cambio[0]["decision_sin"] == "CONFORME"
    imps = {i["caracteristica"]: i for i in flujo.implicaciones(r1)}
    assert "corridos" in imps["Sesgo (veracidad)"]["que_implica"] and "atípico" in imps["Repetibilidad"]["que_implica"]
    donde = [d for y in r1["resultados"] if y.get("caracteristica") == "fuentes_variacion" for d in y["estimacion"].get("donde", [])]
    assert donde and all(d["factor"] in ("Técnico", "Patrón") for d in donde) and any("T-03" in d["comparacion"] for d in donde)
