"""Exporta a CSV los resultados que el motor guarda en JSON (y conserva los JSON para la trazabilidad).

Crea, en un repositorio temporal y por el flujo normal de la aplicación, los cuatro escenarios oficiales (Testeo 1–4) y
los dos estudios con datos reales del laboratorio, y escribe en results/:

  tables/metricas_por_escenario.csv   una fila por escenario y resultado evaluado (estado, normalidad, rutas, rangos)
  tables/metricas_por_particion.csv   una fila por escenario × resultado × punto (estimaciones, p, decisiones)
  tables/contraste_<magnitud>.csv     laboratorio vs reproducción vs motor, prueba por prueba
  tables/contraste_resumen.csv        coincidencias de decisión y diferencias máximas
  tables/componentes_varianza.csv     precisión intermedia de la corrección (laboratorio vs reproducción vs motor)
  tables/motor_datos_reales.csv       atípicos señalados, ruta, factores que influyen y post hoc del motor
  figures/*.png                       gráficos del contraste
  json/<estudio>_resultado.json       memoria de cálculo original de cada análisis (sin modificar)
  diccionario_campos_resultados.md    significado de cada columna
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
os.environ.setdefault("AVM_SIN_TESTEOS", "1")

import pandas as pd  # noqa: E402

DICCIONARIO = """# Diccionario de campos de results/

| Archivo | Campo | Significado |
| --- | --- | --- |
| metricas_por_escenario.csv | escenario, estudio | Testeo (base sintética) y código del estudio en la base de datos |
| | resultado_evaluado | Corrección, Inestabilidad o Inhomogeneidad |
| | estado_resultado / estado_global | Conclusión del motor para ese resultado / para el análisis completo (el más desfavorable) |
| | rechazos_normalidad, revisiones_normalidad | Shapiro-Wilk con p ≤ 0,05 / revisiones aplicadas |
| | ruta_anova, ruta_welch, ruta_kruskal | Puntos en que el motor eligió cada ruta de comparación (RM-26) |
| | lecturas_senaladas | Lecturas marcadas por Grubbs (no se eliminan) |
| | sesgo_min/max, s_r_min/max, s_I_min/max | Rango de las estimaciones en los ocho puntos [°C] |
| metricas_por_particion.csv | punto | Punto nominal |
| | sesgo, s_r, s_I | Estimación del punto [unidad del resultado] |
| | decision_sesgo, decision_s_r, decision_s_I | CONFORME / NO_CONFORME / CALCULADO_SIN_EVALUACION frente al límite aprobado |
| | p_normalidad_residuos, p_normalidad_medias | Shapiro-Wilk de los residuos (supuesto del ANOVA) y de los promedios de serie (sesgo) |
| | ruta | Ruta de comparación de las fuentes de variación |
| | p_tecnico, p_patron, p_operador, p_tiempo | Valor p del factor en la ruta elegida |
| contraste_<magnitud>.csv | laboratorio | Valor impreso en el informe técnico del laboratorio |
| | reproduccion | Mismo procedimiento del laboratorio recalculado de forma independiente |
| | motor | Valor calculado por el motor sobre el conjunto aprobado en la base de datos |
| | dif_reproduccion, dif_motor | Diferencia absoluta con el valor del laboratorio |
| | decision_laboratorio, decision_motor, coincide_decision | Rechaza / no rechaza con α = 0,05 y si coinciden |
| componentes_varianza.csv | s2_operador, s2_tiempo, s2_r, u_lab | Componentes de varianza y aporte de precisión intermedia (fórmulas del informe) |
| experiments.csv | semilla | Réplica del estudio de estabilidad (herramientas/estabilidad.py) |
"""


def _valor(y):
    return (y.get("estimacion") or {}).get("valor")


def metricas(repo, codigo: str, escenario: str) -> tuple[list[dict], list[dict]]:
    from src.motor.multi import partes
    total = repo.obtener_analisis(codigo, 1)["resultado"]
    esc, part = [], []
    for p in partes(total):
        res = p["objeto"]["nombre"]
        porpunto: dict[str, dict] = {}
        for y in p["resultados"]:
            agr = y.get("agrupacion", "")
            if not agr.startswith("nivel "):
                continue
            pt = agr.split("·")[0].replace("nivel", "").strip()
            d = porpunto.setdefault(pt, {"escenario": escenario, "estudio": codigo, "resultado_evaluado": res, "punto": pt})
            car = y.get("caracteristica")
            if car in ("sesgo", "repetibilidad", "precision_intermedia") and y["estado"] == "APLICABLE":
                k = {"sesgo": "sesgo", "repetibilidad": "s_r", "precision_intermedia": "s_I"}[car]
                d[k], d[f"decision_{k}"] = _valor(y), y.get("decision_metrologica")
                if car == "sesgo":
                    d["p_sesgo"] = y.get("p_valor")
            elif y["etapa"] == "normalidad" and y["estado"] == "APLICABLE" and y["tecnica"] == "Shapiro-Wilk":
                d["p_normalidad_residuos" if "residuos" in agr else "p_normalidad_medias"] = y.get("p_valor")
            elif y["etapa"] == "homocedasticidad" and y["estado"] == "APLICABLE":
                d["prueba_varianzas"], d["p_varianzas"] = y["tecnica"], y.get("p_valor")
            elif car == "fuentes_variacion" and y["estado"] == "APLICABLE":
                est = y["estimacion"]
                d["ruta"] = est.get("ruta_nombre")
                for f in est.get("anova", []):
                    if f.get("tipo") == "factor":
                        d[f"p_{f['fuente'].lower().replace('é', 'e').replace('ó', 'o')}"] = f.get("p")
                d["factores_que_influyen"] = ", ".join(est.get("influyen", [])) or "ninguno"
        part.extend(porpunto.values())
        filas = list(porpunto.values())
        rutas = [y["estimacion"]["ruta"] for y in p["resultados"] if y.get("caracteristica") == "fuentes_variacion" and y["estado"] == "APLICABLE"]

        def rango(k):
            v = [f[k] for f in filas if f.get(k) is not None]
            return (min(v), max(v)) if v else (None, None)
        sm, sx = rango("sesgo")
        rm, rx = rango("s_r")
        im, ix = rango("s_I")
        esc.append({"escenario": escenario, "estudio": codigo, "resultado_evaluado": res,
                    "estado_resultado": p["conclusion_final"]["estado"], "estado_global": total["conclusion_final"]["estado"],
                    "rechazos_normalidad": sum(1 for y in p["resultados"] if y["etapa"] == "normalidad" and y.get("decision_inferencial") == "Se rechaza H0"),
                    "revisiones_normalidad": sum(1 for y in p["resultados"] if y["etapa"] == "normalidad" and y["estado"] == "APLICABLE"),
                    "ruta_anova": rutas.count("anova"), "ruta_welch": rutas.count("welch"), "ruta_kruskal": rutas.count("kruskal"),
                    "lecturas_senaladas": sum(1 for y in p["resultados"] if y["etapa"] == "atipicos" for t in y.get("tabla", [])
                                              if t.get("clasificacion") in ("rezagado (*)", "atípico (**)")),
                    "sesgo_min": sm, "sesgo_max": sx, "s_r_min": rm, "s_r_max": rx, "s_I_min": im, "s_I_max": ix})
    return esc, part


def main(salida: Path = RAIZ / "results") -> None:
    from src.contraste.laboratorio import contrastar, grafico_operadores, grafico_p
    from src.persistencia.repositorio import RepositorioLocal
    from src.servicios.estudios_prueba import crear_estudios_prueba
    from src.servicios.estudios_reales import CARPETA_REALES, asegurar_estudios_reales, leer_libro

    for sub in ("tables", "figures", "json"):
        (salida / sub).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AVM_DATOS_DIR"] = tmp
        repo = RepositorioLocal()
        sint = crear_estudios_prueba(repo, "exportacion")
        reales = asegurar_estudios_reales(repo, "exportacion")
        esc, part = [], []
        for x in sint:
            a, b = metricas(repo, x["codigo"], x["nombre"])
            esc += a
            part += b
            shutil.copy(Path(tmp) / "estudios" / x["codigo"] / "analisis" / "v001" / "resultado.json",
                        salida / "json" / f"{x['nombre'].replace(' ', '_')}_{x['codigo']}_resultado.json")
        for x in reales:
            a, b = metricas(repo, x["codigo"], x["nombre"])
            part += b
            shutil.copy(Path(tmp) / "estudios" / x["codigo"] / "analisis" / "v001" / "resultado.json",
                        salida / "json" / f"datos_reales_{x['magnitud']}_{x['codigo']}_resultado.json")
        pd.DataFrame(esc).to_csv(salida / "tables" / "metricas_por_escenario.csv", index=False, encoding="utf-8")
        pd.DataFrame(part).to_csv(salida / "tables" / "metricas_por_particion.csv", index=False, encoding="utf-8")

        resumen, comps, motor = [], [], []
        archivos = {"temperatura": "data_temperatura.xlsx", "humedad": "DATA_HUMEDAD.xlsx"}
        for x in reales:
            lib = leer_libro((CARPETA_REALES / archivos[x["magnitud"]]).read_bytes())
            t = contrastar(x["magnitud"], lib.datos, repo.obtener_analisis(x["codigo"], 1)["resultado"], lib.componentes_lab)
            t["comparacion"].to_csv(salida / "tables" / f"contraste_{x['magnitud']}.csv", index=False, encoding="utf-8")
            resumen.append(t["resumen"])
            comps.append(t["componentes"])
            motor.append(t["motor"])
            nombre = "temperatura" if x["magnitud"] == "temperatura" else "humedad relativa"
            (salida / "figures" / f"contraste_p_{x['magnitud']}.png").write_bytes(
                grafico_p(t["comparacion"], f"Valores p: informe vs motor · {nombre}"))
            for var in ("Corrección", "Inestabilidad", "Inhomogeneidad"):
                (salida / "figures" / f"operadores_{x['magnitud']}_{var.lower()[:5]}.png").write_bytes(
                    grafico_operadores(lib.datos, var, f"{var} por operador · {nombre}"))
            (salida / "tables" / f"advertencias_calidad_{x['magnitud']}.txt").write_text("\n".join(lib.advertencias) or "Sin advertencias.",
                                                                                         encoding="utf-8")
        pd.concat(resumen).to_csv(salida / "tables" / "contraste_resumen.csv", index=False, encoding="utf-8")
        pd.concat(comps).to_csv(salida / "tables" / "componentes_varianza.csv", index=False, encoding="utf-8")
        pd.concat(motor).to_csv(salida / "tables" / "motor_datos_reales.csv", index=False, encoding="utf-8")
    (salida / "diccionario_campos_resultados.md").write_text(DICCIONARIO, encoding="utf-8")
    print("Exportado en", salida)


if __name__ == "__main__":
    main()
