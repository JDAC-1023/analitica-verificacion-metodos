"""Estudios y datos para las pruebas del motor."""

from __future__ import annotations

from src.modelos.estudio import Estudio, Factor, Magnitud, MedicionPlanificada, Punto, Recurso, Variable
from src.motor.configuracion import CaracteristicaConfig, ConfiguracionAnalisis, CriterioMotor, ReferenciaNivel
from src.motor.sintetico import tablas_sinteticas

# ISO 5725-2:1994, anexo B.1, tabla B.1 (azufre en carbón, % m/m). Filas: réplicas; columnas: niveles 1–4.
ISO_B1 = {
    1: [(0.71, 1.20, 1.68, 3.26), (0.71, 1.18, 1.70, 3.26), (0.70, 1.23, 1.68, 3.20), (0.71, 1.21, 1.69, 3.24)],
    2: [(0.69, 1.22, 1.64, 3.20), (0.67, 1.21, 1.64, 3.20), (0.68, 1.22, 1.65, 3.20)],
    3: [(0.66, 1.28, 1.61, 3.37), (0.65, 1.31, 1.61, 3.36), (0.69, 1.30, 1.62, 3.38)],
    4: [(0.67, 1.23, 1.68, 3.16), (0.65, 1.18, 1.66, 3.22), (0.66, 1.20, 1.66, 3.23)],
    5: [(0.70, 1.31, 1.64, 3.20), (0.69, 1.22, 1.67, 3.19), (0.66, 1.22, 1.60, 3.18), (0.71, 1.24, 1.66, 3.27),
        (0.69, None, 1.68, 3.24)],
    6: [(0.73, 1.39, 1.70, 3.27), (0.74, 1.36, 1.73, 3.31), (0.73, 1.37, 1.73, 3.29)],
    7: [(0.71, 1.20, 1.69, 3.27), (0.71, 1.26, 1.70, 3.24), (0.69, 1.26, 1.68, 3.23)],
    8: [(0.70, 1.24, 1.67, 3.25), (0.65, 1.22, 1.68, 3.26), (0.68, 1.30, 1.67, 3.26)],
}


def estudio_iso_b1():
    e = Estudio(codigo="EST-ISO", nombre="ISO 5725-2 anexo B.1", tipo="Validación")
    e.magnitudes = [Magnitud("MAG-01", "Contenido de azufre", "% m/m")]
    e.puntos = [Punto(f"PT-0{j}", "MAG-01", j, "% m/m") for j in range(1, 5)]
    e.factores = [Factor("F-01", "Laboratorio", niveles=[f"Lab {i}" for i in range(1, 9)])]
    e.variables = [Variable("V-01", "Contenido de azufre", unidad="% m/m")]
    valores, k = {}, 0
    for lab, filas in ISO_B1.items():
        for rep, fila in enumerate(filas, start=1):
            for j, x in enumerate(fila, start=1):
                if x is None:
                    continue
                k += 1
                mid = f"M{k:04d}"
                e.plan.append(MedicionPlanificada(mid, f"PT-0{j}", rep, niveles={"F-01": f"Lab {lab}"}))
                valores[mid] = {"V-01": x}
    cfg = ConfiguracionAnalisis(codigo_estudio=e.codigo, objeto_tipo="variable", objeto_id="V-01",
                                es_interlaboratorio=True, factor_laboratorio="F-01", metodo_validado="no",
                                caracteristicas=[CaracteristicaConfig("repetibilidad", "REQUERIDA"),
                                                 CaracteristicaConfig("reproducibilidad", "REQUERIDA")])
    return e, tablas_sinteticas(e, valores), cfg


def estudio_intra(valores_por_punto: dict[str, list[float]], tecnicos=("T-01", "T-02"), dias=("Día 1", "Día 2"),
                  tipo="Verificación"):
    """Intralaboratorio: valores en orden técnico × día × repetición para cada punto."""
    e = Estudio(codigo="EST-T", nombre="Sintético intralaboratorio", tipo=tipo)
    e.magnitudes = [Magnitud("MAG-01", "Temperatura", "°C")]
    e.puntos = [Punto(pid, "MAG-01", float(i * 20), "°C") for i, pid in enumerate(valores_por_punto, start=1)]
    e.tecnicos = [Recurso(t, f"Técnico {t}") for t in tecnicos]
    e.factores = [Factor("F-01", "Técnico", vinculo_recurso="tecnico", niveles=list(tecnicos)),
                  Factor("F-02", "Día", niveles=list(dias))]
    e.variables = [Variable("V-01", "Error de indicación", unidad="°C")]
    valores, k = {}, 0
    for pid, xs in valores_por_punto.items():
        reps = len(xs) // (len(tecnicos) * len(dias))
        it = iter(xs)
        for t in tecnicos:
            for d in dias:
                for r in range(1, reps + 1):
                    k += 1
                    mid = f"M{k:04d}"
                    e.plan.append(MedicionPlanificada(mid, pid, r, niveles={"F-02": d}, tecnico=t))
                    x = next(it)
                    if x is not None:
                        valores[mid] = {"V-01": x}
    return e, tablas_sinteticas(e, valores)


def cfg_intra(e, criterios=None, referencia="objeto_es_diferencia", **kw):
    base = dict(codigo_estudio=e.codigo, objeto_tipo="variable", objeto_id="V-01", metodo_validado="si",
                factores_precision_intermedia=["F-01", "F-02"], referencia_tipo=referencia,
                caracteristicas=[CaracteristicaConfig("sesgo", "REQUERIDA"), CaracteristicaConfig("repetibilidad", "REQUERIDA"),
                                 CaracteristicaConfig("precision_intermedia", "REQUERIDA")],
                criterios=criterios or [])
    base.update(kw)
    return ConfiguracionAnalisis(**base)


def criterios_aprobados(lim_sesgo=0.5, lim_sr=0.3, lim_sI=0.4, regla="estimacion"):
    return [CriterioMotor("CM-01", "sesgo", "abs_sesgo", "<=", lim_sesgo, "°C", regla, "Procedimiento interno PI-01", True),
            CriterioMotor("CM-02", "repetibilidad", "s_r", "<=", lim_sr, "°C", regla, "Procedimiento interno PI-01", True),
            CriterioMotor("CM-03", "precision_intermedia", "s_I", "<=", lim_sI, "°C", regla, "Procedimiento interno PI-01", True)]


__all__ = ["ISO_B1", "estudio_iso_b1", "estudio_intra", "cfg_intra", "criterios_aprobados", "ReferenciaNivel"]
