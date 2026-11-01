"""Motor estadístico: tablas ISO, reproducción del anexo B.1, 4 escenarios y casos adversos.

Cada prueba indica la entrada y el resultado esperado.
"""

import math

import numpy as np
import pandas as pd
import pytest

from src.motor import tablas_iso as T
from src.motor.atipicos import ATIPICO, CORRECTO, REZAGADO
from src.motor.configuracion import (CaracteristicaConfig, ConfiguracionAnalisis, CriterioMotor, Exclusion,
                                     ReferenciaNivel, ReglaDerivacion, diferencias)
from src.motor.datos import ErrorDatosMotor
from src.motor.desempeno import anova_un_factor, iso_reproducibilidad
from src.motor.motor import ejecutar
from src.motor.resultado import (APLICABLE, CONFORME, DATOS_INSUFICIENTES, INDETERMINADO, NO_APLICABLE, NO_CONFORME,
                                 NO_IMPLEMENTADO, SIN_EVALUACION)
from tests.motor_casos import cfg_intra, criterios_aprobados, estudio_intra, estudio_iso_b1


def _r(res, tecnica, contiene=""):
    return [x for x in res["resultados"] if x["tecnica"].startswith(tecnica) and contiene in x["agrupacion"]]


# ------------------------------------------------------------------ tablas ISO 5725-2:1994
def test_tablas_transcritas_coinciden_con_formula():
    """Entrada: todas las entradas de las tablas 4 (Cochran), 5 (Grubbs simple) y 6/7 (Mandel h).
    Esperado: el valor transcrito coincide con la fórmula teórica salvo Cochran p=13, n=6, 5 %: impreso 0,243 frente a
    0,246 por fórmula; se conserva el valor impreso y queda documentado (docs/11_motor_contrato.md)."""
    distintos = []
    for p, fila in T.COCHRAN.items():
        for n, (c1, c5) in fila.items():
            if c1 is None:
                continue
            for v, a in ((c1, 0.01), (c5, 0.05)):
                if abs(v - T.cochran_formula(p, n, a)) >= 0.0021:
                    distintos.append((p, n, a))
    assert distintos == [(13, 6, 0.05)]
    for p, (s1, s5, _, _) in T.GRUBBS.items():
        assert abs(s1 - T.grubbs_formula(p, 0.01)) < 0.0021 and abs(s5 - T.grubbs_formula(p, 0.05)) < 0.0021, p
    for nivel, alfa in ((1, 0.01), (5, 0.05)):
        for p, fila in T.MANDEL[nivel].items():
            assert abs(fila[0] - T.mandel_h_formula(p, alfa)) < 0.011, (nivel, p)


def test_tabla_mandel_k_y_errata_documentada():
    """Entrada: indicadores k de las tablas 6 y 7.
    Esperado: coinciden con la fórmula salvo k(p=24, n=10, 5 %), impreso 1,38 (fórmula 1,362), que se conserva tal cual."""
    distintos = []
    for nivel, alfa in ((1, 0.01), (5, 0.05)):
        for p, fila in T.MANDEL[nivel].items():
            for n in range(2, 11):
                if abs(fila[n - 1] - T.mandel_k_formula(p, n, alfa)) >= 0.011:
                    distintos.append((nivel, p, n))
    assert distintos == [(5, 24, 10)]
    assert T.indicador_mandel(24, 10, "k")["i5"] == 1.38


def test_valores_criticos_del_ejemplo_y_fuera_de_rango():
    """Entrada: p=8, n=3 (ejemplo B.1) y p=45 (fuera de tabla).
    Esperado: Cochran 0,516/0,615 y Grubbs 2,126/2,274, 0,1101/0,0563 de tabla; p=45 calculado por fórmula y declarado."""
    c = T.critico_cochran(8, 3)
    assert (c["c5"], c["c1"]) == (0.516, 0.615) and "tabla 4" in c["origen"]
    g = T.critico_grubbs(8)
    assert (g["simple5"], g["simple1"], g["doble5"], g["doble1"]) == (2.126, 2.274, 0.1101, 0.0563)
    fuera = T.critico_grubbs(45)
    assert "fórmula" in fuera["origen"] and fuera["doble5"] is None


# ------------------------------------------------------------------ anexo B.1
@pytest.fixture(scope="module")
def iso():
    e, t, cfg = estudio_iso_b1()
    return ejecutar(t, e, cfg)


def test_iso_b1_tabla_b5(iso):
    """Entrada: datos de la tabla B.1 (8 laboratorios, 4 niveles, n_ij desigual).
    Esperado: s_r y s_R de la tabla B.5 a tres decimales: 0,015/0,029/0,017/0,026 y 0,026/0,061/0,035/0,058."""
    sr = [round(x["estimacion"]["valor"], 3) for x in _r(iso, "Repetibilidad")]
    sR = [round(x["estimacion"]["valor"], 3) for x in _r(iso, "Reproducibilidad")]
    assert sr == [0.015, 0.029, 0.017, 0.026]
    assert sR == [0.026, 0.061, 0.035, 0.058]


def test_iso_b1_nivel1_desde_estadisticos_redondeados():
    """Entrada: medias y s de las tablas B.2 y B.3 (nivel 1), como hace la norma en B.1.6.
    Esperado: m̂ = 0,69044; s_r² = 0,0002322; s_L² ≈ 0,0004603; s_r = 0,01524; s_R = 0,02632."""
    c = pd.DataFrame({"n": [4, 3, 3, 3, 5, 3, 3, 3], "media": [0.708, 0.680, 0.667, 0.660, 0.690, 0.733, 0.703, 0.677],
                      "s": [0.005, 0.010, 0.021, 0.010, 0.019, 0.006, 0.012, 0.025]})
    r = iso_reproducibilidad(c)
    assert round(r["m"], 5) == 0.69044
    assert round(r["s_r2"], 7) == 0.0002322
    assert abs(r["s_L2"] - 0.0004603) < 5e-7
    assert round(r["s_r"], 5) == 0.01524 and round(r["s_R"], 5) == 0.02632


def test_iso_b1_cochran(iso):
    """Entrada: tabla B.1. Esperado: nivel 3, laboratorio 5 rezagado (C≈0,598 entre 0,516 y 0,615); niveles 1, 2 y 4 correctos
    con valores próximos a 0,347, 0,287 y 0,310 (la norma usa s redondeadas)."""
    co = _r(iso, "Cochran")
    valores = [x["estadistico"]["valor"] for x in co]
    for v, ref in zip(valores, (0.347, 0.287, 0.598, 0.310)):
        assert abs(v - ref) < 0.02
    assert "Lab 5 → rezagado" in co[2]["decision_inferencial"]
    assert all("correcto" in co[i]["decision_inferencial"] for i in (0, 1, 3))
    assert co[0]["criticos"]["5 %"] == 0.516 and co[0]["criticos"]["1 %"] == 0.615


def test_iso_b1_grubbs(iso):
    """Entrada: medias de celda de la tabla B.1. Esperado: estadísticos de la tabla B.4 y laboratorios 3 y 6 como par rezagado
    (doble alto) solo en el nivel 2."""
    ref = {0: (1.80, 1.24, 0.298, 0.539), 1: (2.09, 0.91, 0.108, 0.699), 2: (1.58, 1.67, 0.459, 0.378), 3: (2.09, 0.94, 0.132, 0.679)}
    gr = _r(iso, "Grubbs (medias")
    for i, (sa, sb, da, db) in ref.items():
        t = {f["prueba"]: f for f in gr[i]["tabla"]}
        assert abs(t["Simple, valor alto"]["G"] - sa) < 0.02 and abs(t["Simple, valor bajo"]["G"] - sb) < 0.02
        assert abs(t["Doble, dos altos"]["G"] - da) < 0.005 and abs(t["Doble, dos bajos"]["G"] - db) < 0.005
    doble = {i: {f["prueba"]: f for f in gr[i]["tabla"]}["Doble, dos altos"] for i in range(4)}
    assert doble[1]["clasificacion"] == REZAGADO and set(doble[1]["laboratorio"].split(" y ")) == {"Lab 3", "Lab 6"}
    assert all(doble[i]["clasificacion"] == CORRECTO for i in (0, 2, 3))


def test_iso_b1_sin_exclusion_automatica(iso):
    """Entrada: tabla B.1 con rezagados. Esperado: se analizan los 107 resultados; ninguno queda excluido."""
    assert len(iso["datos"]) == 107 and iso["excluidas"] == []


# ------------------------------------------------------------------ 4 escenarios
def _normales(media, sd, semilla):
    rng = np.random.default_rng(semilla)
    return {"PT-01": list(np.round(media + rng.normal(0, sd, 12), 5)), "PT-02": list(np.round(media + rng.normal(0, sd, 12), 5))}


ASIMETRICOS = [0.10, 0.10, 0.11, 0.10, 0.11, 0.10, 0.10, 0.11, 0.10, 0.10, 0.62, 0.95]


def _no_normales(cfg_kw):
    e, t = estudio_intra({"PT-01": ASIMETRICOS, "PT-02": list(reversed(ASIMETRICOS))})
    return e, t, dict(factores_precision_intermedia=[], caracteristicas=[CaracteristicaConfig("sesgo", "REQUERIDA"),
                                                                         CaracteristicaConfig("repetibilidad", "REQUERIDA")], **cfg_kw)


@pytest.mark.parametrize("limites,esperado", [((0.5, 0.3, 0.4), CONFORME), ((0.05, 0.3, 0.4), NO_CONFORME)])
def test_escenario_normal(limites, esperado):
    """Entrada: errores normales (media 0,1 °C, s 0,05 °C), 2 técnicos × 2 días × 3 réplicas por punto; criterio de |sesgo|
    0,5 (cumple) o 0,05 (no cumple). Esperado: no se rechaza normalidad, prueba t, y conclusión final CONFORME / NO_CONFORME."""
    e, t = estudio_intra(_normales(0.1, 0.05, 1))
    r = ejecutar(t, e, cfg_intra(e, criterios_aprobados(*limites)))
    assert all(x["decision_inferencial"] == "No se rechaza H0" for x in _r(r, "Shapiro"))
    sesgo = _r(r, "Sesgo (t")
    assert len(sesgo) == 2 and all(x["decision_metrologica"] == esperado for x in sesgo)
    assert r["conclusion_final"]["estado"] == esperado
    assert all(x["n"] == 4 for x in sesgo)  # unidades independientes = medias de celda, no 12 observaciones


@pytest.mark.parametrize("limite,esperado", [(0.5, CONFORME), (0.01, NO_CONFORME)])
def test_escenario_no_normal(limite, esperado):
    """Entrada: 12 valores asimétricos por punto en una sola celda; criterio de |sesgo| 0,5 (cumple) o 0,01 (no cumple).
    Esperado: se rechaza normalidad → Wilcoxon con advertencia de simetría; decisión por estimación CONFORME / NO_CONFORME."""
    e, t, kw = _no_normales({})
    crit = [CriterioMotor("CM-01", "sesgo", "abs_sesgo", "<=", limite, "°C", "estimacion", "PI-01", True),
            CriterioMotor("CM-02", "repetibilidad", "s_r", "<=", 1.0, "°C", "estimacion", "PI-01", True)]
    r = ejecutar(t, e, cfg_intra(e, crit, **kw))
    assert any(x["decision_inferencial"] == "Se rechaza H0" for x in _r(r, "Shapiro", "unidades"))
    w = _r(r, "Sesgo (Wilcoxon)")
    assert w and all("simetría" in " ".join(x["limitaciones"]) for x in w)
    assert all(x["decision_metrologica"] == esperado for x in w)
    rep = _r(r, "Repetibilidad")
    assert any("condiciones de repetibilidad" in " ".join(x["limitaciones"]) for x in rep)


# ------------------------------------------------------------------ casos adversos
def test_sin_criterio_calculado_sin_evaluacion():
    """Entrada: datos normales sin criterios. Esperado: todas las estimaciones CALCULADO_SIN_EVALUACION; sin conformidad global."""
    e, t = estudio_intra(_normales(0.0, 0.05, 2))
    r = ejecutar(t, e, cfg_intra(e, []))
    des = [x for x in r["resultados"] if x["etapa"] == "desempeno" and x["estado"] == APLICABLE and x["caracteristica"] != "fuentes_variacion"]
    assert des and all(x["decision_metrologica"] == SIN_EVALUACION for x in des)
    assert r["conclusion_final"]["estado"] == SIN_EVALUACION


def test_p_no_significativo_no_es_conformidad():
    """Entrada: sesgo no significativo (media 0) y criterio sin aprobar. Esperado: «No se rechaza H0 …» y decisión
    CALCULADO_SIN_EVALUACION, nunca CONFORME."""
    e, t = estudio_intra(_normales(0.0, 0.05, 3))
    crit = criterios_aprobados()
    for c in crit:
        c.aprobado = False
    r = ejecutar(t, e, cfg_intra(e, crit))
    s = _r(r, "Sesgo (t")[0]
    assert s["decision_inferencial"].startswith("No se rechaza H0") and "no demuestra" in s["decision_inferencial"]
    assert s["decision_metrologica"] == SIN_EVALUACION and "no está aprobado" in " ".join(s["motivos"])


def test_criterio_incompleto_o_unidad_distinta():
    """Entrada: criterio sin regla de decisión (sesgo) y criterio en mK (s_r). Esperado: ambos CALCULADO_SIN_EVALUACION con motivo."""
    e, t = estudio_intra(_normales(0.1, 0.05, 4))
    crit = [CriterioMotor("CM-01", "sesgo", "abs_sesgo", "<=", 0.5, "°C", "", "PI-01", True),
            CriterioMotor("CM-02", "repetibilidad", "s_r", "<=", 300, "mK", "estimacion", "PI-01", True)]
    r = ejecutar(t, e, cfg_intra(e, crit))
    assert "regla de decisión" in " ".join(_r(r, "Sesgo")[0]["motivos"])
    rep = _r(r, "Repetibilidad")[0]
    assert rep["decision_metrologica"] == SIN_EVALUACION and "no se convierten unidades" in " ".join(rep["motivos"])


def test_regla_intervalo_indeterminado():
    """Entrada: regla de intervalo con un límite de s_r dentro del IC. Esperado: INDETERMINADO."""
    e, t = estudio_intra(_normales(0.1, 0.05, 5))
    r0 = ejecutar(t, e, cfg_intra(e, []))
    ic = _r(r0, "Repetibilidad")[0]["ic"]
    lim = (ic[0] + ic[1]) / 2
    crit = [CriterioMotor("CM-02", "repetibilidad", "s_r", "<=", lim, "°C", "intervalo", "PI-01", True, puntos=["PT-01"])]
    r = ejecutar(t, e, cfg_intra(e, crit))
    assert _r(r, "Repetibilidad")[0]["decision_metrologica"] == INDETERMINADO
    assert _r(r, "Repetibilidad")[1]["decision_metrologica"] == SIN_EVALUACION  # el criterio solo aplica a PT-01


def test_faltantes_no_se_imputan_y_celda_n1():
    """Entrada: PT-01 con 5 faltantes, una celda queda con n=1. Esperado: faltantes informados por celda (sin imputar),
    Grubbs no se aplica a esa celda, la celda no aporta gl a s_r y el diseño se declara desbalanceado."""
    v = _normales(0.1, 0.05, 6)
    v["PT-01"][0] = v["PT-01"][1] = None          # celda T-01·Día 1 queda con n=1
    v["PT-01"][3] = v["PT-01"][4] = v["PT-01"][5] = None   # celda T-01·Día 2 vacía
    e, t = estudio_intra(v)
    r = ejecutar(t, e, cfg_intra(e, criterios_aprobados(), alerta_faltantes_pct=20))
    falt = _r(r, "Faltantes")[0]
    assert falt["estimacion"]["faltantes"] == 5 and len(r["datos"]) == 19
    assert falt["limitaciones"]  # alerta configurada por el laboratorio
    celdas = [x["agrupacion"] for x in _r(r, "Grubbs (réplicas)")]
    assert not any("T-01 · Día 1" in c and "20 °C" in c for c in celdas)
    rep = _r(r, "Repetibilidad", "20")[0]
    assert rep["gl"] == 2 * 2  # dos celdas con 3 réplicas; la de n=1 no aporta
    assert "desbalanceado" in r["conclusiones"]["limpieza"]


def test_sin_umbral_no_hay_alerta():
    """Entrada: faltantes sin umbral configurado. Esperado: solo se informa el porcentaje, sin alertas."""
    v = _normales(0.1, 0.05, 7)
    v["PT-02"][0] = None
    e, t = estudio_intra(v)
    r = ejecutar(t, e, cfg_intra(e, []))
    assert _r(r, "Faltantes")[0]["limitaciones"] == []


def test_intralaboratorio_no_aplica_cochran_ni_reproducibilidad():
    """Entrada: estudio con técnicos, no interlaboratorio, y reproducibilidad solicitada. Esperado: Cochran, Mandel y s_R
    NO_APLICABLE con el motivo «los técnicos no son laboratorios»."""
    e, t = estudio_intra(_normales(0.1, 0.05, 8))
    cfg = cfg_intra(e, [])
    cfg.caracteristicas.append(CaracteristicaConfig("reproducibilidad", "SELECCIONADA"))
    r = ejecutar(t, e, cfg)
    for tec in ("Cochran", "Mandel h y k", "Reproducibilidad interlaboratorio"):
        x = _r(r, tec)[0]
        assert x["estado"] == NO_APLICABLE
    assert "no son laboratorios" in _r(r, "Cochran")[0]["motivos"][0]
    assert "Reproducibilidad intralaboratorio" in _r(r, "Reproducibilidad interlaboratorio")[0]["motivos"][0]


def test_edicion_normativa_distinta():
    """Entrada: edición configurada «ISO 5725-2:2019» en el estudio interlaboratorio. Esperado: Mandel, Cochran y Grubbs
    NO_APLICABLE; no se usan las tablas de 1994."""
    e, t, cfg = estudio_iso_b1()
    cfg.version_normativa = "ISO 5725-2:2019"
    r = ejecutar(t, e, cfg)
    at = [x for x in r["resultados"] if x["etapa"] == "atipicos" and x["tecnica"] != "Dixon"]
    assert at and all(x["estado"] == NO_APLICABLE for x in at)


def test_exclusion_documentada_y_recalculo():
    """Entrada: versión 2 que excluye M0001 con motivo y responsable. Esperado: M0001 fuera de los datos y en «excluidas»,
    exclusión registrada en limpieza, n de la celda reducido y diferencias de configuración trazadas."""
    e, t = estudio_intra(_normales(0.1, 0.05, 9))
    v1 = cfg_intra(e, criterios_aprobados())
    v2 = ConfiguracionAnalisis.from_dict(v1.to_dict())
    v2.version, v2.padre, v2.motivo_cambio = 2, 1, "Exclusión por falla registrada en bitácora"
    v2.exclusiones = [Exclusion("M0001", "Falla de lectura registrada en bitácora", "Revisor QA", "2026-11-01")]
    r1, r2 = ejecutar(t, e, v1), ejecutar(t, e, v2)
    assert "M0001" not in {d["medicion_id"] for d in r2["datos"]} and r2["excluidas"][0]["medicion_id"] == "M0001"
    assert _r(r2, "Exclusiones")[0]["tabla"][0]["responsable"] == "Revisor QA"
    assert len(r2["datos"]) == len(r1["datos"]) - 1
    cambios = diferencias(v1, v2)
    assert [c["campo"] for c in cambios] == ["exclusiones"]


def test_derivado_requiere_regla_aprobada():
    """Entrada: objeto «derivado» sin regla aprobada. Esperado: error explícito; el motor no inventa fórmulas."""
    e, t = estudio_intra(_normales(0.1, 0.05, 10))
    cfg = cfg_intra(e, [], objeto_tipo="derivado", objeto_id="R-01", regla=ReglaDerivacion("diferencia", "V-01", "V-01", "", False))
    with pytest.raises(ErrorDatosMotor):
        ejecutar(t, e, cfg)


def test_sesgo_con_valor_de_referencia_y_pocos_datos():
    """Entrada: referencia por nivel (PT-01 = 0,1; PT-02 sin valor) y una sola celda de 2 observaciones en PT-01.
    Esperado: PT-01 solo estimación (n<3) y PT-02 DATOS_INSUFICIENTES por falta de referencia."""
    e, t = estudio_intra({"PT-01": [0.11, 0.12], "PT-02": [0.2, 0.21]}, tecnicos=("T-01",), dias=("Día 1",))
    cfg = cfg_intra(e, [], referencia="valor_por_nivel", factores_precision_intermedia=[],
                    referencias=[ReferenciaNivel("PT-01", 0.1, 0.002, "Certificado CC-01")])
    r = ejecutar(t, e, cfg)
    assert _r(r, "Sesgo (solo estimación)")[0]["estimacion"]["valor"] == pytest.approx(0.015)
    assert any(x["estado"] == DATOS_INSUFICIENTES and "referencia" in x["motivos"][0] for x in _r(r, "Sesgo", "40"))


def test_caracteristica_no_implementada_y_ruta():
    """Entrada: linealidad REQUERIDA; método validado con modificaciones pero estudio declarado como Verificación.
    Esperado: linealidad NO_IMPLEMENTADO, aviso de ruta (correspondería Validación) y conclusión global no conforme a la ligera."""
    e, t = estudio_intra(_normales(0.1, 0.05, 11))
    cfg = cfg_intra(e, criterios_aprobados(), modificaciones="Cambio de sensor")
    cfg.caracteristicas.append(CaracteristicaConfig("linealidad", "REQUERIDA"))
    r = ejecutar(t, e, cfg)
    lin = next(f for f in r["caracteristicas"] if f["codigo"] == "linealidad")
    assert lin["decision"] == NO_IMPLEMENTADO
    assert r["ruta"]["sugerida"] == "Validación" and r["ruta"]["avisos"]
    assert r["conclusion_final"]["estado"] == "INCOMPLETO"


def test_anova_varianza_entre_negativa_se_trunca():
    """Entrada: grupos con medias idénticas y dispersión interna. Esperado: s_b² bruto < 0 → s_b² = 0 y s_I = s_r."""
    c = pd.DataFrame({"celda": ["a", "b"], "n": [3, 3], "media": [1.0, 1.0], "s": [0.1, 0.1]})
    a = anova_un_factor(c)
    assert a["s_b2_bruto"] < 0 and a["s_b2"] == 0 and math.isclose(a["s_I2"], a["s_r2"])


def test_resultado_serializable_y_campos_memoria(iso):
    """Entrada: resultado del anexo B.1. Esperado: JSON serializable; cada resultado trae los campos §10 y un árbol de decisión."""
    import json
    json.dumps(iso)
    campos = {"analysis_id", "etapa", "tecnica", "study_id", "version", "variable_id", "unidad", "agrupacion", "estado",
              "n", "algoritmo", "referencia", "origen_regla", "supuestos", "hipotesis", "estadistico", "gl", "p_valor",
              "criticos", "ic", "estimacion", "decision_inferencial", "requisito", "decision_metrologica", "limitaciones", "texto"}
    assert all(campos <= set(x) for x in iso["resultados"])
    assert iso["arbol"] and all(n["regla"] for n in iso["arbol"])
    assert iso["meta"]["huella_resultado"]


def test_texto_nunca_confirma_normalidad(iso):
    """Entrada: todos los textos generados. Esperado: no aparece «se confirma»."""
    textos = " ".join(x["texto"] for x in iso["resultados"]) + " ".join(iso["conclusiones"].values())
    assert "se confirma" not in textos.lower()


def test_fuentes_de_variacion_detecta_tecnico():
    """Entrada: 2 técnicos × 2 días × 3 réplicas; el técnico T-02 mide 0,3 °C más. Esperado: «Técnico» influye (p < 0,05) con la mayor
    contribución, «Día» no; la prueba post hoc ubica la diferencia T-01 vs T-02 ≈ 0,3 °C y explica su origen probable (operador)."""
    base = [0.10, 0.11, 0.09]
    valores = {"PT-01": base * 2 + [x + 0.3 for x in base] * 2}   # orden: técnico × día × réplica
    e, t = estudio_intra(valores)
    r = ejecutar(t, e, cfg_intra(e, []))
    fv = _r(r, "Fuentes de variación")[0]
    assert fv["estado"] == APLICABLE and fv["estimacion"]["influyen"] == ["Técnico"]
    filas = {f["fuente"]: f for f in fv["estimacion"]["anova"]}
    assert {"Técnico", "Día"} <= set(filas)
    efecto = filas["Técnico"]["contribucion_pct"] if fv["estimacion"]["ruta"] != "kruskal" else filas["Técnico"]["epsilon2"] * 100
    assert efecto > 50
    donde = fv["estimacion"]["donde"]                 # dónde están las diferencias (prueba post hoc de la ruta elegida)
    assert len(donde) == 1 and donde[0]["comparacion"] in ("T-01 vs T-02", "T-02 vs T-01")
    assert abs(donde[0]["diferencia"]) == pytest.approx(0.3, abs=0.01)
    assert "operador" in fv["estimacion"]["causas"]["Técnico"]
    medias = {x["nivel"]: x["media"] for x in fv["estimacion"]["contexto"]["por_factor"]["Técnico"]}
    assert medias["T-02"] - medias["T-01"] == pytest.approx(0.3)
    assert fv["decision_metrologica"] == ""          # es inferencial: no se evalúa contra un criterio


def test_conforme_con_observaciones_si_no_normal():
    """Entrada: datos asimétricos que cumplen los límites. Esperado: «CONFORME_CON_OBSERVACIONES» con la observación de normalidad."""
    e, t, kw = _no_normales({})
    crit = [CriterioMotor("CM-01", "sesgo", "abs_sesgo", "<=", 0.5, "°C", "estimacion", "PI-01", True),
            CriterioMotor("CM-02", "repetibilidad", "s_r", "<=", 1.0, "°C", "estimacion", "PI-01", True)]
    r = ejecutar(t, e, cfg_intra(e, crit, **kw))
    assert r["conclusion_final"]["estado"] == "CONFORME_CON_OBSERVACIONES"
    assert any("normalidad" in a for a in r["conclusion_final"]["avisos"])


@pytest.mark.parametrize("asimetrico,ruta", [(False, "anova"), (True, "kruskal")])
def test_ruta_condicional_de_comparacion(asimetrico, ruta):
    """Entrada: 2 técnicos × 2 días × 5 réplicas con ruido normal o muy asimétrico. Esperado: con datos normales se aplica Bartlett y,
    con varianzas similares, ANOVA + Tukey; sin normalidad NO se aplica ningún ANOVA (ni F, ni Welch, ni prueba F de s_I, ni IC χ²):
    Kruskal-Wallis + Dunn, con Fligner-Killeen solo informativo."""
    from scipy import stats as st
    n = 20
    u = (np.arange(1, n + 1) - 0.375) / (n + 0.25)
    z = st.expon.ppf(u) - 1 if asimetrico else st.norm.ppf(u)
    rng = np.random.default_rng(3)
    valores = {"PT-01": list(np.round(0.1 + rng.permutation(z) * 0.02, 5))}
    e, t = estudio_intra(valores)
    r = ejecutar(t, e, cfg_intra(e, []))
    normal_res = _r(r, "Shapiro", "residuos")[0]["decision_inferencial"] == "No se rechaza H0"
    homo = _r(r, "Homocedasticidad")[0]
    assert homo["tecnica"] == ("Homocedasticidad (Bartlett)" if normal_res else "Homocedasticidad (Fligner-Killeen, informativa)")
    fv = _r(r, "Fuentes de variación")[0]
    pruebas = {f["prueba"] for f in fv["estimacion"]["anova"]}
    if not normal_res:                                   # sin normalidad: ningún ANOVA (ni F, ni Welch, ni % de variación)
        assert pruebas == {"Kruskal-Wallis (H)"} and fv["estimacion"]["r2"] is None
        assert all(f["contribucion_pct"] is None and f["epsilon2"] is not None for f in fv["estimacion"]["anova"])
        si = _r(r, "Reproducibilidad intralaboratorio")[0]
        assert si["p_valor"] is None and si["ic"] == [None, None] and not si["estimacion"]["con_prueba_F"]
        rep = _r(r, "Repetibilidad")[0]
        assert rep["ic"] == [None, None]
    if normal_res and homo["decision_inferencial"] == "No se rechaza H0":
        assert fv["estimacion"]["ruta"] == "anova"
    elif not normal_res:
        assert fv["estimacion"]["ruta"] == "kruskal"
    assert fv["estimacion"]["ruta"] == ruta
