"""Etapa de limpieza: faltantes, estructura del diseño y exclusiones documentadas.

No imputa ni elimina por comportamiento estadístico (RM-02). El porcentaje de
faltantes solo genera alerta si el laboratorio configuró un umbral (RM-03).
"""

from __future__ import annotations

import pandas as pd

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.resultado import APLICABLE, COMPLEMENTARIA, CRITERIO_LAB, NORMA

ETAPA = "limpieza"


def tabla_faltantes(ctx: Contexto) -> pd.DataFrame:
    obs = ctx.obs
    observadas = obs.df.groupby(["punto_id", "celda"]).size().rename("observadas").reset_index()
    t = obs.esperadas.merge(observadas, on=["punto_id", "celda"], how="outer").fillna(0)
    excl = obs.excluidas.groupby(["punto_id", "celda"]).size().rename("excluidas").reset_index() if len(obs.excluidas) else \
        pd.DataFrame(columns=["punto_id", "celda", "excluidas"])
    t = t.merge(excl, on=["punto_id", "celda"], how="left").fillna(0)
    for c in ("esperadas", "observadas", "excluidas"):
        t[c] = t[c].astype(int)
    t["faltantes"] = (t["esperadas"] - t["observadas"] - t["excluidas"]).clip(lower=0)
    t["pct_faltantes"] = (t["faltantes"] / t["esperadas"].where(t["esperadas"] > 0) * 100).round(2)
    return t


def ejecutar(ctx: Contexto, tablas: dict) -> None:
    cfg, obs = ctx.cfg, ctx.obs
    t = tabla_faltantes(ctx)
    esperadas, faltantes = int(t["esperadas"].sum()), int(t["faltantes"].sum())
    pct = faltantes / esperadas * 100 if esperadas else 0.0
    por_nivel = t.groupby("punto_id")[["esperadas", "faltantes"]].sum()
    por_nivel["pct"] = (por_nivel["faltantes"] / por_nivel["esperadas"] * 100).round(2)
    # por variable (todas las variables numéricas del conjunto, sobre las mediciones del plan)
    vals = tablas.get("valores")
    por_variable = []
    if vals is not None:
        total = len(ctx.e.plan)
        for v in ctx.e.variables:
            if v.tipo_dato not in ("decimal", "entero"):
                continue
            n = int(vals[(vals["variable_id"] == v.id) & vals["valor_numerico"].notna()]["medicion_id"].nunique())
            por_variable.append({"variable": f"{v.id} · {v.nombre}", "esperadas": total, "con_valor": n,
                                 "pct_faltantes": round((total - n) / total * 100, 2) if total else None})
    alertas = []
    if cfg.alerta_faltantes_pct is not None:
        for _, f in t.iterrows():
            if f["pct_faltantes"] is not None and f["pct_faltantes"] > cfg.alerta_faltantes_pct:
                alertas.append(f"Celda {f['celda']} del nivel {f['punto_id']}: {f['pct_faltantes']} % > {cfg.alerta_faltantes_pct} %")
    ctx.decidir("¿Hay faltantes respecto al plan aprobado?", "SI" if faltantes else "NO",
                f"{faltantes} de {esperadas} ({P.fmt(pct, 3)} %). No se imputan.", "RM-02")
    ctx.decidir("¿El laboratorio fijó un umbral de alerta de faltantes?",
                "SI" if cfg.alerta_faltantes_pct is not None else "NO",
                f"Umbral: {cfg.alerta_faltantes_pct} %" if cfg.alerta_faltantes_pct is not None else "Sin umbral: solo se informa.", "RM-03")
    ctx.nuevo(ETAPA, "Faltantes respecto al plan", "global, por variable, por nivel y por celda", APLICABLE,
              n=int(len(obs.df)), incluidas=list(obs.df["medicion_id"]), excluidas=list(obs.excluidas["medicion_id"]),
              origen_regla=CRITERIO_LAB if alertas else COMPLEMENTARIA, referencia="ISO 5725-2:1994 §7.2; Especificación §6",
              formula="% faltantes = faltantes / esperadas × 100",
              estimacion={"nombre": "pct_faltantes_global", "valor": pct, "unidad": "%", "esperadas": esperadas, "faltantes": faltantes,
                          "por_nivel": por_nivel.reset_index().to_dict("records"), "por_variable": por_variable},
              tabla=t.to_dict("records"), limitaciones=alertas,
              decision_inferencial="No aplica.",
              texto=f"Se esperaban {esperadas} resultados de «{obs.nombre_objeto}» según el plan; hay {len(obs.df)} válidos, "
                    f"{len(obs.excluidas)} excluidos con motivo y {faltantes} faltantes ({P.fmt(pct, 3)} %). "
                    "Los faltantes no se imputan; cada técnica verifica su propia suficiencia.")
    # réplicas por serie frente al plan (cada serie debe tener exactamente las lecturas planificadas)
    dif = t[t["observadas"] != t["esperadas"]]
    nombre_p = {pid: d["punto"] for pid, d in ctx.est["niveles"].items()}
    filas_s = [{"punto": nombre_p.get(f["punto_id"], f["punto_id"]), "serie": f["celda"], "planificadas": int(f["esperadas"]),
                "válidas": int(f["observadas"]), "excluidas": int(f["excluidas"]),
                "estado": "incompleta" if f["observadas"] < f["esperadas"] else "con lecturas de más"} for _, f in dif.iterrows()]
    ctx.decidir("¿Cada serie tiene exactamente las lecturas planificadas?", "SI" if not filas_s else "NO",
                f"{len(t)} series revisadas; {len(filas_s)} difieren del plan.", "RM-02")
    ctx.nuevo(ETAPA, "Réplicas por serie frente al plan", "por serie (punto × condiciones)", APLICABLE, n=int(len(t)),
              origen_regla=COMPLEMENTARIA, referencia="ISO 5725-2:1994 §7.2.8 (n_ij); plan aprobado del estudio",
              estimacion={"nombre": "series_distintas_al_plan", "valor": len(filas_s), "unidad": "series", "series": int(len(t))},
              tabla=filas_s, decision_inferencial="No aplica.",
              limitaciones=[f"{len(filas_s)} serie(s) no tienen el número planificado de lecturas; se analizan con las que hay."] if filas_s else [],
              texto=(f"Se revisaron {len(t)} series. " + (f"{len(filas_s)} serie(s) sin el número planificado de lecturas: "
                     + "; ".join(f"{f['punto'].split(' · ')[0]} · {f['serie']}: {f['válidas']} de {f['planificadas']}" for f in filas_s[:6]) + "."
                     if filas_s else "Todas tienen exactamente las lecturas planificadas.")))
    # estructura
    filas = [{"nivel": d["punto"], "p_j": d["p_j"], "n_ij": ", ".join(f"{k}: {v}" for k, v in d["n_ij"].items()),
              "N_j": d["N_j"], "balanceado": "sí" if d["balanceado"] else "no", "gl_dentro": d["gl_dentro"]}
             for d in ctx.est["niveles"].values()]
    ctx.nuevo(ETAPA, "Estructura del diseño", "por nivel", APLICABLE, n=int(len(obs.df)), origen_regla=NORMA,
              referencia="ISO 5725-2:1994 §7.2.1", estimacion={"nombre": "q", "valor": ctx.est["q"], "unidad": "niveles"},
              tabla=filas, decision_inferencial="No aplica.",
              texto=f"El objeto se analiza en {ctx.est['q']} nivel(es). Las celdas se forman por: "
                    f"{'laboratorio' if cfg.es_interlaboratorio else ', '.join(cfg.factores_precision_intermedia) or 'una sola celda por nivel'}.")
    # exclusiones
    if len(obs.excluidas):
        ex = [{"medicion_id": x.medicion_id, "motivo": x.motivo, "responsable": x.responsable, "fecha": x.fecha, "origen": x.origen}
              for x in cfg.exclusiones]
        ctx.decidir("¿Hay exclusiones documentadas en esta versión?", "SI",
                    f"{len(ex)} exclusión(es) con motivo y responsable; los datos originales se conservan.", "RM-10")
        ctx.nuevo(ETAPA, "Exclusiones documentadas", "versión del análisis", APLICABLE, n=len(ex), origen_regla=NORMA,
                  excluidas=[x["medicion_id"] for x in ex], tabla=ex, referencia="ISO 5725-2:1994 §7.3.2",
                  decision_inferencial="No aplica.",
                  texto=f"Esta versión excluye {len(ex)} medición(es) por decisión técnica documentada. "
                        "El dato original permanece en el conjunto preparado.")
    for tr in obs.trazas:
        ctx.decidir("Construcción del objeto", "INFO", tr, "RM-01")
