"""Estabilidad de las decisiones del motor frente a la semilla del generador sintético.

Para cada escenario (mismos parámetros que las bases oficiales: sesgo, dispersión, efectos, forma del residuo, errores
sembrados) se generan R réplicas que solo cambian la semilla. Cada réplica recorre el flujo completo de la aplicación
(estudio → plantilla → carga → calidad → preparación → análisis de los tres resultados) en un repositorio temporal.

Semillas: 2001 … 2000+R para la corrección (el generador usa semilla + 1000, es decir 3001 … 3000+R, para inestabilidad
e inhomogeneidad). Se eligen así porque: (1) no coinciden con las oficiales (11, 106, 33, 44) ni con sus derivadas
(1011, 1106, 1033, 1044); (2) son consecutivas y fijas, de modo que cualquiera puede repetir el estudio; (3) son las
mismas para los cuatro escenarios (diseño pareado: las diferencias entre escenarios no se deben a semillas distintas).

Salidas en results/: experiments.csv (una fila por réplica y resultado evaluado), tables/estabilidad_por_escenario.csv
y los resúmenes que usa el documento.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("AVM_SIN_TESTEOS", "1")

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ESPERADO = {"01_Normal_No_Cumple": "NO_CONFORME", "02_Normal_Cumple": "CONFORME",
            "03_No_Normal_No_Cumple": "NO_CONFORME", "04_No_Normal_Cumple": "CONFORME_CON_OBSERVACIONES"}
CUMPLE = {"CONFORME": "cumple", "CONFORME_CON_OBSERVACIONES": "cumple", "NO_CONFORME": "no cumple"}


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (max(0.0, c - h), min(1.0, c + h))


def una_replica(nombre: str, semilla: int, carpeta: Path) -> list[dict]:
    from herramientas import generar_bases_prueba as g
    from src.motor.multi import partes
    from src.persistencia.repositorio import RepositorioLocal
    from src.plantillas.diligenciar import diligenciar_plantilla
    from src.plantillas.generador import generar_plantilla
    from src.servicios.estudios_prueba import crear_estudio_desde_archivo

    p = dict(g.ESCENARIOS[nombre], semilla=semilla)
    e = g.estudio_base()
    df = g.valores(e, p)
    g.sembrar_errores(df, p["anomalo"], round(10 * p["s"], 2))
    contenido = diligenciar_plantilla(generar_plantilla(e), df)
    os.environ["AVM_DATOS_DIR"] = str(carpeta)
    repo = RepositorioLocal()
    x = crear_estudio_desde_archivo(repo, contenido, f"{nombre}_s{semilla}.xlsx", f"{nombre} s{semilla}", "estabilidad",
                                    escenario=nombre)
    total = repo.obtener_analisis(x["codigo"], 1)["resultado"]
    filas = []
    for parte in partes(total):
        res = parte["objeto"]["nombre"]
        normal_rech = sum(1 for y in parte["resultados"] if y["etapa"] == "normalidad" and y.get("decision_inferencial") == "Se rechaza H0")
        normal_tot = sum(1 for y in parte["resultados"] if y["etapa"] == "normalidad" and y["estado"] == "APLICABLE")
        rutas = [y["estimacion"]["ruta"] for y in parte["resultados"] if y["caracteristica"] == "fuentes_variacion" and y["estado"] == "APLICABLE"]
        atip = sum(1 for y in parte["resultados"] if y["etapa"] == "atipicos" for t in y.get("tabla", [])
                   if t.get("clasificacion") in ("rezagado (*)", "atípico (**)"))
        falla = sorted({c["caracteristica"] for c in parte["caracteristicas"] if c.get("decision") == "NO_CONFORME"})
        filas.append({"escenario": nombre, "semilla": semilla, "resultado_evaluado": res,
                      "estado_resultado": parte["conclusion_final"]["estado"], "estado_global": total["conclusion_final"]["estado"],
                      "esperado_global": ESPERADO[nombre], "rechazos_normalidad": normal_rech, "revisiones_normalidad": normal_tot,
                      "ruta_anova": rutas.count("anova"), "ruta_welch": rutas.count("welch"), "ruta_kruskal": rutas.count("kruskal"),
                      "lecturas_senaladas": atip, "caracteristicas_no_conformes": ", ".join(falla),
                      "mediciones": x["mediciones"], "normalizados": x["conteos"]["normalizados"], "pendientes": x["conteos"]["pendientes"]})
    return filas


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, default=20)
    ap.add_argument("--inicio", type=int, default=2001)
    ap.add_argument("--salida", default=str(RAIZ / "results"))
    a = ap.parse_args()
    salida = Path(a.salida)
    (salida / "tables").mkdir(parents=True, exist_ok=True)
    semillas = list(range(a.inicio, a.inicio + a.replicas))
    filas, t0 = [], time.time()
    with tempfile.TemporaryDirectory() as tmp:
        for nombre in ESPERADO:
            for s in semillas:
                filas += una_replica(nombre, s, Path(tmp) / f"{nombre}_{s}")
            print(f"{nombre}: {len(semillas)} réplicas · {time.time() - t0:.0f} s", flush=True)
    exp = pd.DataFrame(filas)
    exp.to_csv(salida / "experiments.csv", index=False, encoding="utf-8")
    glob = exp.drop_duplicates(["escenario", "semilla"])
    resumen = []
    for nombre, g in glob.groupby("escenario", sort=False):
        n = len(g)
        k_exacto = int((g["estado_global"] == g["esperado_global"]).sum())
        k_cumple = int((g["estado_global"].map(CUMPLE) == CUMPLE[ESPERADO[nombre]]).sum())
        moda = g["estado_global"].mode().iloc[0]
        lo, hi = wilson(k_exacto, n)
        lo2, hi2 = wilson(k_cumple, n)
        resumen.append({"escenario": nombre, "replicas": n, "esperado": ESPERADO[nombre],
                        "coincide_estado_exacto": k_exacto, "proporcion_exacta": k_exacto / n, "ic95_inf": lo, "ic95_sup": hi,
                        "coincide_cumple_no_cumple": k_cumple, "proporcion_cumple": k_cumple / n, "ic95_inf_cumple": lo2,
                        "ic95_sup_cumple": hi2, "estado_modal": moda, "estados_observados": json.dumps(g["estado_global"].value_counts().to_dict(),
                                                                                                     ensure_ascii=False)})
    pd.DataFrame(resumen).to_csv(salida / "tables" / "estabilidad_por_escenario.csv", index=False, encoding="utf-8")
    por_res = (exp.groupby(["escenario", "resultado_evaluado", "estado_resultado"]).size().rename("replicas").reset_index())
    por_res.to_csv(salida / "tables" / "estabilidad_por_resultado.csv", index=False, encoding="utf-8")
    print(pd.DataFrame(resumen)[["escenario", "replicas", "coincide_estado_exacto", "coincide_cumple_no_cumple", "estados_observados"]].to_string())


if __name__ == "__main__":
    main()
