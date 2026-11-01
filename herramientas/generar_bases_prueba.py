"""Genera las 4 bases de prueba del motor (datos SINTÉTICOS) en data/estudios_prueba/.

Diseño (igual en las cuatro, como se ejecuta en el laboratorio):
    8 temperaturas × 3 técnicos × 2 patrones × 5 lecturas por serie = 240 mediciones.
    Una «serie» = un técnico con un patrón en una temperatura; tiene exactamente 5 lecturas planificadas.

Escenarios (criterio de prueba: |sesgo| ≤ 0,10 °C; s_r ≤ 0,05 °C; s_I ≤ 0,08 °C):
    01 · normal · no cumple      sesgo ≈ 0,25 °C y efecto del técnico
    02 · normal · cumple         sesgo ≈ 0,02 °C, dispersión 0,02 °C
    03 · no normal · no cumple   ruido asimétrico grande (s ≈ 0,07 °C) y sesgo ≈ 0,15 °C
    04 · no normal · cumple      ruido asimétrico pequeño (s ≈ 0,02 °C) → cumple con observaciones

El ruido «normal» usa cuantiles normales exactos y el «no normal» cuantiles exponenciales
(asimetría marcada), repartidos al azar con semilla fija: el escenario es reproducible.

Errores sembrados para probar la limpieza (en las cuatro bases):
    E1 · lectura del IBC escrita como texto con coma decimal         → TR02 (coma → punto)
    E2 · técnico escrito « t-02 » (espacios y minúscula)              → TR03 + TR04
    E3 · lectura del IBC vacía (dato obligatorio)                    → RC15, registro pendiente (serie con 4 lecturas)
    E4 · hora real «25:99»                                           → RC19, solo avisa
    E5 · (bases 01, 03 y 04) una lectura anómala (+10 s) en una serie → la detecta Grubbs; no se borra sola

Uso:  python -m herramientas.generar_bases_prueba
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.modelos.estudio import (Estudio, Factor, Magnitud, MedicionPlanificada, Punto, Recurso, ResultadoInteres,
                                 Variable)
from src.plantillas.diligenciar import diligenciar_plantilla
from src.plantillas.generador import generar_plantilla

CARPETA = Path(__file__).resolve().parents[1] / "data" / "estudios_prueba"
PUNTOS = [-80, -40, -20, 0, 10, 25, 50, 150]
TECNICOS = [("T-01", "Santiago"), ("T-02", "Andrés"), ("T-03", "Brandon")]
PATRONES = [("P-01", "Juego de dataloggers 1"), ("P-02", "Juego de dataloggers 2")]
REPLICAS = 5
CRITERIOS = {"sesgo": ("abs_sesgo", 0.10), "repetibilidad": ("s_r", 0.05), "precision_intermedia": ("s_I", 0.08)}
FUENTE = "Criterio de prueba del prototipo (datos sintéticos; no es un requisito del laboratorio)"

ESCENARIOS = {
    "01_Normal_No_Cumple": dict(normal=True, sesgo=0.25, s=0.025, tec=(-0.03, 0.0, 0.04), pat=(0.004, -0.004), anomalo=True, semilla=11),
    "02_Normal_Cumple": dict(normal=True, sesgo=0.02, s=0.02, tec=(0.0, 0.0, 0.0), pat=(0.0, 0.0), anomalo=False, semilla=106),
    "03_No_Normal_No_Cumple": dict(normal=False, sesgo=0.15, s=0.07, tec=(-0.02, 0.0, 0.02), pat=(0.01, -0.01), anomalo=True, semilla=33),
    "04_No_Normal_Cumple": dict(normal=False, sesgo=0.02, s=0.02, tec=(-0.004, 0.0, 0.004), pat=(0.002, -0.002), anomalo=True, semilla=44),
}


def estudio_base() -> Estudio:
    e = Estudio(codigo="EST-PRUEBA", nombre="Caracterización de medios isotermos en temperatura", tipo="Verificación",
                metodo="Comparación directa", version_metodo="3", responsable="Juan David Ahumada",
                uso_previsto="Datos sintéticos para probar el motor de limpieza y validación.")
    e.magnitudes = [Magnitud("MAG-01", "Temperatura", "°C", -80, 150)]
    e.puntos = [Punto(f"PT-{i:02d}", "MAG-01", float(v), "°C") for i, v in enumerate(PUNTOS, start=1)]
    e.tecnicos = [Recurso(c, n, "tecnico") for c, n in TECNICOS]
    e.patrones = [Recurso(c, n, "patron", "MAG-01", -90, 200, descripcion=n) for c, n in PATRONES]
    e.ibcs = [Recurso("IBC-01", "Cámara A-03", "ibc", "MAG-01", -80, 150, descripcion="Cámara climática", marca="BINDER",
                      modelo="KBF ECO 240", serie="PRUEBA123", resolucion="0.01")]
    e.factores = [Factor("F-01", "Técnico", "Persona que realiza la medición", vinculo_recurso="tecnico"),
                  Factor("F-02", "Patrón", "Patrón utilizado", vinculo_recurso="patron")]
    e.repeticiones_por_condicion = REPLICAS
    e.variables = [Variable("V-01", "Indicación del IBC", "decimal", "°C", True, "Lectura del equipo a evaluar"),
                   Variable("V-02", "Valor del patrón", "decimal", "°C", True, "Lectura del patrón")]
    e.resultados = [ResultadoInteres("R-01", "Corrección", unidad="°C", origen="directo", ambito="medicion"),
                    ResultadoInteres("R-02", "Inestabilidad", unidad="°C", origen="directo", ambito="medicion"),
                    ResultadoInteres("R-03", "Inhomogeneidad", unidad="°C", origen="directo", ambito="medicion")]
    k = 0
    for i, _ in enumerate(PUNTOS, start=1):
        for t, _n in TECNICOS:
            for p, _m in PATRONES:
                for r in range(1, REPLICAS + 1):
                    k += 1
                    e.plan.append(MedicionPlanificada(f"M{k:04d}", f"PT-{i:02d}", r, tecnico=t, patron=p))
    e.estado, e.version_diseno = "aprobado", 1
    return e


def ruido(n: int, normal: bool, s: float, rng) -> np.ndarray:
    u = (np.arange(1, n + 1) - 0.375) / (n + 0.25)
    if normal:
        z = stats.norm.ppf(u)
    else:
        z = stats.expon.ppf(u) - 1.0         # media 0, desviación 1, muy asimétrico
    z = (z - z.mean()) / z.std(ddof=1)
    return rng.permutation(z) * s


def valores(e: Estudio, p: dict) -> pd.DataFrame:
    rng = np.random.default_rng(p["semilla"])
    tec = dict(zip([t for t, _ in TECNICOS], p["tec"]))
    pat = dict(zip([c for c, _ in PATRONES], p["pat"]))
    filas = []
    por_punto = {}
    for m in e.plan:
        por_punto.setdefault(m.punto_id, []).append(m)
    for pid, ms in por_punto.items():
        nominal = e.punto(pid).valor_nominal
        sesgo_punto = p["sesgo"] + rng.normal(0, 0.003)
        eps = ruido(len(ms), p["normal"], p["s"], rng)
        for m, err in zip(ms, eps):
            patron = round(nominal + rng.normal(0, 0.004), 3)
            correccion = sesgo_punto + tec[m.tecnico] + pat[m.patron] + err
            filas.append({"medicion_id": m.medicion_id, "var:V-01": round(patron - correccion, 3), "var:V-02": patron,
                          "res:R-01": round(patron - round(patron - correccion, 3), 3),
                          "res:R-02": round(abs(rng.normal(0.03, 0.008)), 3), "res:R-03": round(abs(rng.normal(0.04, 0.01)), 3),
                          "tecnico_real": m.tecnico, "patron_real": m.patron, "hora_real": None,
                          "observaciones": "DATOS SINTÉTICOS — PRUEBA DE MOTOR; NO VÁLIDOS COMO RESULTADOS DE CALIBRACIÓN"})
    return pd.DataFrame(filas, dtype=object)


def sembrar_errores(df: pd.DataFrame, anomalo: bool, magnitud: float = 0.15) -> list[dict]:
    """Modifica df en el lugar y devuelve la lista de errores sembrados (para el LEEME y las pruebas)."""
    idx = {mid: i for i, mid in enumerate(df["medicion_id"])}
    errores = []
    i = idx["M0007"]
    df.at[i, "var:V-01"] = str(df.at[i, "var:V-01"]).replace(".", ",")
    errores.append({"id": "E1", "medicion": "M0007", "que": "Lectura del IBC escrita como texto con coma decimal", "espera": "TR02 la normaliza"})
    i = idx["M0044"]
    df.at[i, "tecnico_real"] = f" {df.at[i, 'tecnico_real'].lower()} "
    errores.append({"id": "E2", "medicion": "M0044", "que": "Técnico escrito con espacios y minúscula", "espera": "TR03 + TR04 lo normalizan"})
    i = idx["M0093"]
    df.at[i, "var:V-01"] = None
    errores.append({"id": "E3", "medicion": "M0093", "que": "Lectura del IBC vacía (obligatoria)", "espera": "RC15: queda pendiente; la serie queda con 4 lecturas"})
    i = idx["M0120"]
    df.at[i, "hora_real"] = "25:99"
    errores.append({"id": "E4", "medicion": "M0120", "que": "Hora real no válida «25:99»", "espera": "RC19: solo avisa"})
    if anomalo:
        i = idx["M0063"]                     # −20 °C · T-01 · P-01 · lectura 3
        corr = float(df.at[i, "res:R-01"]) + magnitud
        df.at[i, "res:R-01"] = round(corr, 3)
        df.at[i, "var:V-01"] = round(float(df.at[i, "var:V-02"]) - corr, 3)
        errores.append({"id": "E5", "medicion": "M0063", "que": f"Lectura anómala (+{magnitud:.2f} °C) en la serie −20 °C · T-01 · P-01".replace(".", ","),
                        "espera": "Grubbs la señala; no se borra automáticamente"})
    return errores


def main() -> None:
    CARPETA.mkdir(parents=True, exist_ok=True)
    anterior = CARPETA / "version_anterior_2_replicas"
    viejos = [f for f in CARPETA.glob("*.xlsx")]
    if viejos:
        anterior.mkdir(exist_ok=True)
        for f in viejos:
            shutil.move(str(f), anterior / f.name)
    e = estudio_base()
    plantilla = generar_plantilla(e)
    registro = {"diseno": f"{len(PUNTOS)} temperaturas × {len(TECNICOS)} técnicos × {len(PATRONES)} patrones × {REPLICAS} lecturas",
                "criterios": {k: {"parametro": v[0], "limite": v[1], "unidad": "°C", "fuente": FUENTE} for k, v in CRITERIOS.items()},
                "escenarios": {}}
    for nombre, p in ESCENARIOS.items():
        df = valores(e, p)
        errores = sembrar_errores(df, p["anomalo"], round(10 * p["s"], 2))
        (CARPETA / f"{nombre}.xlsx").write_bytes(diligenciar_plantilla(plantilla, df))
        registro["escenarios"][nombre] = {"errores": errores, **{k: v for k, v in p.items() if k != "semilla"}}
        print(f"{nombre}.xlsx · {len(df)} mediciones · {len(errores)} errores sembrados")
    (CARPETA / "criterios_prueba.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
