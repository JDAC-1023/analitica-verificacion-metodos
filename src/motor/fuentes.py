"""Fuentes de variación: ANOVA factorial (técnico, patrón, día…) con interacciones.

Responde, por punto: ¿la variabilidad depende significativamente del técnico,
del patrón o de su combinación? La decisión es inferencial y automática (valor p
frente a α); no es un criterio de aceptación del método.

Modelo (efectos fijos, sumas de cuadrados tipo II, statsmodels):
    y ~ C(A) + C(B) [+ C(C)] + interacciones de dos factores
Las interacciones solo se incluyen si cada combinación tiene ≥ 2 réplicas
(si no, el término no es estimable sin confundirse con el error).
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.datos import nombre_campo
from src.motor.resultado import APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES

ETAPA = "desempeno"
TECNICA = "Fuentes de variación (ANOVA factorial)"


def contexto_por_factor(g: pd.DataFrame, columnas: dict[str, str]) -> dict:
    """Tablas descriptivas: medias por nivel de cada factor y cruce de los dos primeros."""
    salida = {"por_factor": {}, "cruce": None}
    for col, nombre in columnas.items():
        t = g.groupby(col)["valor"].agg(["count", "mean", "std"]).reset_index()
        salida["por_factor"][nombre] = [{"nivel": str(r[col]), "n": int(r["count"]), "media": float(r["mean"]),
                                         "s": None if pd.isna(r["std"]) else float(r["std"])} for _, r in t.iterrows()]
    cols = list(columnas)
    if len(cols) >= 2:
        cruce = g.pivot_table(index=cols[0], columns=cols[1], values="valor", aggfunc="mean")
        salida["cruce"] = {"filas": columnas[cols[0]], "columnas": columnas[cols[1]],
                           "niveles_columnas": [str(c) for c in cruce.columns],
                           "datos": [{"nivel": str(i), **{str(c): (None if pd.isna(v) else float(v)) for c, v in fila.items()}}
                                     for i, fila in cruce.iterrows()]}
    return salida


def anova_factorial(g: pd.DataFrame, columnas: dict[str, str], alfa: float) -> dict:
    from statsmodels.formula.api import ols
    from statsmodels.stats.anova import anova_lm

    alias = {col: f"f{i}" for i, col in enumerate(columnas)}
    d = g[["valor", *columnas]].rename(columns=alias).copy()
    for a in alias.values():
        d[a] = d[a].astype(str)
    activos = [a for a in alias.values() if d[a].nunique() >= 2]
    terminos = [f"C({a})" for a in activos]
    interacciones = []
    for a, b in itertools.combinations(activos, 2):
        n_comb = d.groupby([a, b]).size()
        completas = n_comb.reindex(pd.MultiIndex.from_product([d[a].unique(), d[b].unique()])).fillna(0)
        if (completas >= 2).all():
            interacciones.append(f"C({a}):C({b})")
    formula = "valor ~ " + " + ".join(terminos + interacciones)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        modelo = ols(formula, data=d).fit()
        tabla = anova_lm(modelo, typ=2)
    inverso = {v: columnas[k] for k, v in alias.items()}
    ss_total = float(((d["valor"] - d["valor"].mean()) ** 2).sum())
    ss_res = float(tabla.loc["Residual", "sum_sq"])
    filas = []
    for termino, f in tabla.iterrows():
        if termino == "Residual":
            continue
        partes = [inverso[x.strip()[2:-1]] for x in termino.split(":")]
        nombre = " × ".join(partes)
        p = None if pd.isna(f["PR(>F)"]) else float(f["PR(>F)"])
        filas.append({"fuente": nombre, "tipo": "interacción" if ":" in termino else "factor",
                      "gl": int(f["df"]), "SC": float(f["sum_sq"]), "CM": float(f["sum_sq"] / f["df"]),
                      "F": None if pd.isna(f["F"]) else float(f["F"]), "p": p,
                      "eta2_parcial": float(f["sum_sq"] / (f["sum_sq"] + ss_res)) if (f["sum_sq"] + ss_res) > 0 else None,
                      "contribucion_pct": float(f["sum_sq"] / ss_total * 100) if ss_total > 0 else None,
                      "influye": p is not None and p < alfa})
    filas.append({"fuente": "Residual (repetibilidad)", "tipo": "residual", "gl": int(tabla.loc["Residual", "df"]),
                  "SC": ss_res, "CM": ss_res / float(tabla.loc["Residual", "df"]), "F": None, "p": None, "eta2_parcial": None,
                  "contribucion_pct": ss_res / ss_total * 100 if ss_total > 0 else None, "influye": None})
    omitidas = [f"{inverso[a]} × {inverso[b]}" for a, b in itertools.combinations(activos, 2)
                if f"C({a}):C({b})" not in interacciones]
    return {"formula": formula.replace("valor", "y"), "filas": filas, "omitidas": omitidas, "n": int(len(d)),
            "r2": float(modelo.rsquared)}


def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    factores = list(cfg.factores_precision_intermedia)
    if cfg.es_interlaboratorio or not factores:
        return
    columnas = {f"campo:{f}": nombre_campo(ctx.e, f) for f in factores}
    ctx.decidir("¿Se analizan las fuentes de variación (técnico, patrón, …)?", "SI",
                f"Factores declarados: {', '.join(columnas.values())}. ANOVA factorial por punto, α = {P.fmt(cfg.alfa)}.", "RM-23")
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        activos = {c: n for c, n in columnas.items() if g[c].nunique() >= 2}
        gl_res = len(g) - int(np.prod([g[c].nunique() for c in activos])) if activos else 0
        if not activos or gl_res < 1:
            ctx.nuevo(ETAPA, TECNICA, agr, DATOS_INSUFICIENTES, caracteristica="fuentes_variacion", punto_id=punto_id, n=len(g),
                      origen_regla=COMPLEMENTARIA, motivos=["Se necesitan al menos 2 niveles de algún factor y réplicas dentro de cada combinación."])
            continue
        a = anova_factorial(g, activos, cfg.alfa)
        ctxt = contexto_por_factor(g, activos)
        influyen = [f["fuente"] for f in a["filas"] if f["influye"]]
        lim = []
        if a["omitidas"]:
            lim.append(f"Interacción no estimable (faltan réplicas en alguna combinación): {', '.join(a['omitidas'])}.")
        if g.groupby(list(activos)).size().nunique() > 1:
            lim.append("Diseño desbalanceado: se usan sumas de cuadrados tipo II.")
        lim.append("Supone residuos normales y varianzas similares entre combinaciones; ver la etapa de normalidad.")
        texto = (f"En el {agr} se compararon {', '.join(activos.values())} con un ANOVA factorial ({a['n']} resultados). "
                 + (f"Influyen significativamente (p < {P.fmt(cfg.alfa)}): {', '.join(influyen)}. " if influyen else
                    f"Ninguna fuente resultó significativa (p ≥ {P.fmt(cfg.alfa)}); esto no demuestra que no influyan. ")
                 + "La contribución de cada fuente a la variación total se informa en la tabla.")
        ctx.nuevo(ETAPA, TECNICA, agr, APLICABLE, caracteristica="fuentes_variacion", punto_id=punto_id, n=a["n"],
                  incluidas=list(g["medicion_id"]), origen_regla=COMPLEMENTARIA,
                  referencia="Montgomery (2017), cap. 5; Eurachem (2016) §6.6 y anexo C",
                  algoritmo="statsmodels OLS + anova_lm (tipo II)", formula=a["formula"],
                  hipotesis={"H0": "la fuente no cambia el resultado medio", "H1": "la fuente cambia el resultado medio",
                             "lateralidad": "unilateral (F)", "alfa": cfg.alfa},
                  estimacion={"nombre": "fuentes", "valor": None, "unidad": ctx.obs.unidad, "anova": a["filas"],
                              "r2": a["r2"], "contexto": ctxt, "influyen": influyen},
                  tabla=a["filas"], graficos=[f"interaccion:{punto_id}"],
                  decision_inferencial=("Influyen: " + ", ".join(influyen)) if influyen else "Ninguna fuente significativa",
                  limitaciones=lim, texto=texto)
