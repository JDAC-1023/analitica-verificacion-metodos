"""Etapa de valores atípicos y consistencia.

- Interlaboratorio (ISO 5725-2:1994 §7.3): Mandel h y k, Cochran, Grubbs simple y
  doble sobre medias de celda.
- Intralaboratorio: Grubbs simple complementario sobre réplicas de cada celda
  (n ≥ 3). Nunca se aplica a la mezcla de puntos o condiciones.

Ninguna prueba excluye datos: solo clasifica. Las exclusiones las decide una
persona con motivo técnico y generan una versión derivada (RM-10).
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from src.motor import plantillas as P
from src.motor import tablas_iso as T
from src.motor.contexto import Contexto
from src.motor.resultado import (APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES, NO_APLICABLE, NO_IMPLEMENTADO, NORMA)

ETAPA = "atipicos"
CORRECTO, REZAGADO, ATIPICO = "correcto", "rezagado (*)", "atípico (**)"


def clasificar_mayor(valor, c5, c1):
    if valor is None or c5 is None:
        return "sin valor crítico"
    if valor > c1:
        return ATIPICO
    if valor > c5:
        return REZAGADO
    return CORRECTO


def clasificar_menor(valor, c5, c1):
    """Grubbs doble: un cociente PEQUEÑO indica valores extremos."""
    if valor is None or c5 is None:
        return "sin valor crítico"
    if valor < c1:
        return ATIPICO
    if valor < c5:
        return REZAGADO
    return CORRECTO


# ------------------------------------------------------------------ estadísticos puros
def mandel_h(medias: np.ndarray) -> np.ndarray:
    """ISO 5725-2:1994 ec. 6."""
    m = medias.mean()
    s = medias.std(ddof=1)
    return (medias - m) / s if s > 0 else np.full_like(medias, np.nan)


def mandel_k(s: np.ndarray) -> np.ndarray:
    """ISO 5725-2:1994 ec. 7."""
    total = np.sum(s ** 2)
    return s * np.sqrt(len(s)) / np.sqrt(total) if total > 0 else np.full_like(s, np.nan)


def cochran(s: np.ndarray) -> float | None:
    """ISO 5725-2:1994 ec. 8."""
    total = np.sum(s ** 2)
    return float(np.max(s ** 2) / total) if total > 0 else None


def grubbs_simple(x: np.ndarray) -> dict:
    """ISO 5725-2:1994 ec. 9–11 (valor más alto y más bajo)."""
    x = np.sort(x)
    m, s = x.mean(), x.std(ddof=1)
    if s == 0:
        return {"alto": None, "bajo": None}
    return {"alto": float((x[-1] - m) / s), "bajo": float((m - x[0]) / s)}


def grubbs_doble(x: np.ndarray) -> dict:
    """ISO 5725-2:1994 ec. 12–18 (dos más altos y dos más bajos)."""
    x = np.sort(x)
    s0 = np.sum((x - x.mean()) ** 2)
    if s0 == 0 or len(x) < 4:
        return {"alto": None, "bajo": None}
    sin_altos = x[:-2]
    sin_bajos = x[2:]
    return {"alto": float(np.sum((sin_altos - sin_altos.mean()) ** 2) / s0),
            "bajo": float(np.sum((sin_bajos - sin_bajos.mean()) ** 2) / s0)}


# ------------------------------------------------------------------ etapa
def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    edicion_ok = cfg.version_normativa.strip() == T.EDICION
    ctx.decidir("¿El estudio es interlaboratorio (ISO 5725-2)?", "SI" if cfg.es_interlaboratorio else "NO",
                f"Configuración: es_interlaboratorio={cfg.es_interlaboratorio}, factor laboratorio="
                f"«{cfg.factor_laboratorio or '—'}».", "RM-04")
    ctx.decidir("¿La edición normativa configurada coincide con la implementada?", "SI" if edicion_ok else "NO",
                f"Configurada: {cfg.version_normativa}; implementada: {T.EDICION}.", "RM-06")
    if cfg.es_interlaboratorio:
        if not edicion_ok:
            for tec in ("Mandel h", "Mandel k", "Cochran", "Grubbs"):
                ctx.nuevo(ETAPA, tec, "todos los niveles", NO_APLICABLE, origen_regla=NORMA,
                          motivos=[f"La edición configurada ({cfg.version_normativa}) no es la implementada ({T.EDICION}); "
                                   "no se aplican sus tablas de valores críticos."])
            return
        _interlaboratorio(ctx)
    else:
        for tec in ("Cochran", "Mandel h y k", "Grubbs sobre medias de laboratorio"):
            ctx.nuevo(ETAPA, tec, "todos los niveles", NO_APLICABLE, origen_regla=NORMA, referencia="ISO 5725-2:1994 §7.3",
                      motivos=["El estudio no es interlaboratorio: los técnicos o condiciones internas no son laboratorios (RM-04, RM-05)."])
        _intralaboratorio(ctx, edicion_ok)
    ctx.nuevo(ETAPA, "Dixon", "todos los niveles", NO_IMPLEMENTADO, origen_regla=COMPLEMENTARIA,
              motivos=["No se dispone de tablas críticas verificadas de Dixon en esta versión; no se inventan valores (RM-22)."])


def _interlaboratorio(ctx: Contexto) -> None:
    for punto_id, g in ctx.niveles():
        c = ctx.celdas(g)
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        p = len(c)
        con_s = c[c["n"] >= 2]
        n_mayor = Counter(con_s["n"]).most_common(1)[0][0] if len(con_s) else None
        # ---------------- Mandel h
        if p >= 3:
            h = mandel_h(c["media"].to_numpy())
            ind = T.indicador_mandel(p, None, "h")
            tabla = [{"laboratorio": r.celda, "n": int(r.n), "media": r.media, "h": float(hv),
                      "clasificacion": clasificar_mayor(abs(hv), ind["i5"], ind["i1"])} for r, hv in zip(c.itertuples(), h)]
            ctx.nuevo(ETAPA, "Mandel h", agr, APLICABLE, n=int(len(g)), origen_regla=NORMA,
                      referencia="ISO 5725-2:1994 §7.3.1, ec. 6, tabla 6", algoritmo="h_i = (ȳ_i − ȳ)/s(ȳ_i)",
                      formula="h_ij = (ȳ_ij − ȳ_j) / √[Σ(ȳ_ij − ȳ_j)²/(p−1)]",
                      criticos={"1 %": ind["i1"], "5 %": ind["i5"], "origen": ind["origen"]}, tabla=tabla,
                      graficos=[f"mandel_h:{punto_id}"],
                      supuestos=[{"supuesto": "p ≥ 3 laboratorios", "verificado": True, "evidencia": f"p={p}"}],
                      decision_inferencial="Técnica gráfica: orienta la revisión, no rechaza datos.",
                      texto=f"Se calcularon los estadísticos h de Mandel para {p} laboratorios en el {agr}; "
                            f"indicadores {P.fmt(ind['i5'])} (5 %) y {P.fmt(ind['i1'])} (1 %).")
        else:
            ctx.nuevo(ETAPA, "Mandel h", agr, DATOS_INSUFICIENTES, origen_regla=NORMA, motivos=[f"p={p} < 3 laboratorios."])
        # ---------------- Mandel k y Cochran
        if len(con_s) >= 2:
            s = con_s["s"].to_numpy()
            ind = T.indicador_mandel(len(con_s), n_mayor, "k")
            k = mandel_k(s)
            tabla = [{"laboratorio": r.celda, "n": int(r.n), "s": r.s, "k": float(kv),
                      "clasificacion": clasificar_mayor(kv, ind["i5"], ind["i1"])} for r, kv in zip(con_s.itertuples(), k)]
            ctx.nuevo(ETAPA, "Mandel k", agr, APLICABLE if len(con_s) >= 3 else DATOS_INSUFICIENTES, n=int(len(g)),
                      origen_regla=NORMA, referencia="ISO 5725-2:1994 §7.3.1, ec. 7, tabla 6",
                      formula="k_ij = s_ij √p / √Σ s_ij²", criticos={"1 %": ind["i1"], "5 %": ind["i5"], "origen": ind["origen"]},
                      tabla=tabla, graficos=[f"mandel_k:{punto_id}"],
                      motivos=[] if len(con_s) >= 3 else ["Mandel k requiere p ≥ 3 celdas con réplicas para sus indicadores."],
                      decision_inferencial="Técnica gráfica: orienta la revisión, no rechaza datos.")
            C = cochran(s)
            crit = T.critico_cochran(len(con_s), n_mayor)
            lim = []
            if con_s["n"].nunique() > 1:
                lim.append(f"n_ij distinto entre laboratorios ({sorted(con_s['n'].unique().tolist())}); se usó el n mayoritario "
                           f"n={n_mayor} para el valor crítico (ISO 5725-2:1994 §7.3.3.3).")
            if (c["n"] < 2).any():
                lim.append("Celdas con un solo resultado no intervienen en Cochran.")
            if C is None:
                ctx.nuevo(ETAPA, "Cochran", agr, DATOS_INSUFICIENTES, origen_regla=NORMA, motivos=["Todas las varianzas son cero."])
            else:
                idx = int(np.argmax(s ** 2))
                clas = clasificar_mayor(C, crit["c5"], crit["c1"])
                ctx.nuevo(ETAPA, "Cochran", agr, APLICABLE, n=int(con_s["n"].sum()), origen_regla=NORMA,
                          referencia="ISO 5725-2:1994 §7.3.3, ec. 8, tabla 4", formula="C = s²_max / Σ s²_i",
                          hipotesis={"H0": "la mayor varianza intralaboratorio es compatible con las demás",
                                     "H1": "la mayor varianza es excesiva", "lateralidad": "unilateral superior"},
                          estadistico={"simbolo": "C", "valor": C}, gl={"p": len(con_s), "n": n_mayor},
                          criticos={"5 %": crit["c5"], "1 %": crit["c1"], "origen": crit["origen"]},
                          tabla=[{"laboratorio": r.celda, "n": int(r.n), "s": r.s, "s2": r.s ** 2} for r in con_s.itertuples()],
                          decision_inferencial=f"Laboratorio con mayor varianza: {con_s.iloc[idx]['celda']} → {clas}.",
                          supuestos=[{"supuesto": "Normalidad aproximada dentro de celda", "verificado": False,
                                      "evidencia": "Ver etapa de normalidad (residuos)."},
                                     {"supuesto": "Mismo n por celda", "verificado": con_s["n"].nunique() == 1,
                                      "evidencia": f"n_ij={con_s['n'].tolist()}"}],
                          limitaciones=lim,
                          texto=P.render(P.ATIPICOS, prueba="la prueba de Cochran", n=len(con_s), variable=ctx.obs.nombre_objeto,
                                         agrupacion=agr, referencia="ISO 5725-2:1994", supuestos="p ≥ 2 celdas con réplicas",
                                         simbolo="C", valor=P.fmt(C), critico_o_p=f"los críticos {P.fmt(crit['c5'])} (5 %) y {P.fmt(crit['c1'])} (1 %)",
                                         clasificacion=clas, accion="sin exclusión automática", responsable="revisión técnica pendiente"))
        else:
            ctx.nuevo(ETAPA, "Cochran", agr, DATOS_INSUFICIENTES, origen_regla=NORMA,
                      motivos=["Se necesitan al menos dos laboratorios con n ≥ 2 (RM-07)."])
        # ---------------- Grubbs sobre medias de celda
        _grubbs_medias(ctx, c, punto_id, agr)


def _grubbs_medias(ctx: Contexto, c, punto_id, agr) -> None:
    p = len(c)
    if p < 3:
        ctx.nuevo(ETAPA, "Grubbs (medias de laboratorio)", agr, DATOS_INSUFICIENTES, origen_regla=NORMA,
                  motivos=[f"p={p} < 3 (RM-08)."])
        return
    x = c["media"].to_numpy()
    orden = c.sort_values("media")
    crit = T.critico_grubbs(p)
    gs = grubbs_simple(x)
    gd = grubbs_doble(x) if p >= 4 else {"alto": None, "bajo": None}
    tabla = [
        {"prueba": "Simple, valor alto", "laboratorio": orden.iloc[-1]["celda"], "G": gs["alto"],
         "clasificacion": clasificar_mayor(gs["alto"], crit["simple5"], crit["simple1"])},
        {"prueba": "Simple, valor bajo", "laboratorio": orden.iloc[0]["celda"], "G": gs["bajo"],
         "clasificacion": clasificar_mayor(gs["bajo"], crit["simple5"], crit["simple1"])},
    ]
    if p >= 4:
        tabla += [
            {"prueba": "Doble, dos altos", "laboratorio": " y ".join(orden.iloc[-2:]["celda"]), "G": gd["alto"],
             "clasificacion": clasificar_menor(gd["alto"], crit["doble5"], crit["doble1"])},
            {"prueba": "Doble, dos bajos", "laboratorio": " y ".join(orden.iloc[:2]["celda"]), "G": gd["bajo"],
             "clasificacion": clasificar_menor(gd["bajo"], crit["doble5"], crit["doble1"])},
        ]
    hallazgos = [f"{t['prueba']}: {t['laboratorio']} → {t['clasificacion']}" for t in tabla
                 if t["clasificacion"] not in (CORRECTO, "sin valor crítico")]
    ctx.nuevo(ETAPA, "Grubbs (medias de laboratorio)", agr, APLICABLE, n=p, origen_regla=NORMA,
              referencia="ISO 5725-2:1994 §7.3.4, ec. 9–18, tabla 5",
              formula="G_p = (x_p − x̄)/s ; G = s²_{p−1,p} / s²_0",
              hipotesis={"H0": "las medias de laboratorio provienen de la misma población normal",
                         "H1": "el valor (o par) extremo no pertenece a esa población", "lateralidad": "bilateral por extremo"},
              criticos={"simple 5 %": crit["simple5"], "simple 1 %": crit["simple1"], "doble 5 %": crit["doble5"],
                        "doble 1 %": crit["doble1"], "origen": crit["origen"]},
              tabla=tabla, decision_inferencial="; ".join(hallazgos) or "Ningún valor rezagado ni atípico.",
              supuestos=[{"supuesto": "Medias independientes y aproximadamente normales", "verificado": False,
                          "evidencia": "Supuesto de la norma; ver diagnóstico gráfico."}],
              limitaciones=[] if p >= 4 else ["Grubbs doble requiere p ≥ 4."],
              texto=f"Se aplicó la prueba de Grubbs a las {p} medias de laboratorio del {agr}. "
                    + ("; ".join(hallazgos) if hallazgos else "Ninguna media se clasificó como rezagada o atípica.")
                    + ". Sin exclusión automática; el dato original permanece conservado.")


def _intralaboratorio(ctx: Contexto, edicion_ok: bool) -> None:
    alguna = False
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        for celda, cg in g.groupby("celda", sort=True):
            x = cg["valor"].to_numpy(float)
            agr = f"nivel {punto} · celda {celda}"
            if len(x) < 3:
                continue
            alguna = True
            if not edicion_ok:
                ctx.nuevo(ETAPA, "Grubbs (réplicas)", agr, NO_APLICABLE, origen_regla=COMPLEMENTARIA,
                          motivos=["Edición normativa distinta de la implementada: no se usan sus tablas (RM-06)."])
                continue
            gs = grubbs_simple(x)
            if gs["alto"] is None:
                ctx.nuevo(ETAPA, "Grubbs (réplicas)", agr, DATOS_INSUFICIENTES, n=len(x), origen_regla=COMPLEMENTARIA,
                          motivos=["Las réplicas no presentan variación (s = 0)."])
                continue
            crit = T.critico_grubbs(len(x))
            orden = cg.sort_values("valor")
            filas = [{"extremo": "alto", "medicion_id": orden.iloc[-1]["medicion_id"], "valor": float(orden.iloc[-1]["valor"]),
                      "G": gs["alto"], "clasificacion": clasificar_mayor(gs["alto"], crit["simple5"], crit["simple1"])},
                     {"extremo": "bajo", "medicion_id": orden.iloc[0]["medicion_id"], "valor": float(orden.iloc[0]["valor"]),
                      "G": gs["bajo"], "clasificacion": clasificar_mayor(gs["bajo"], crit["simple5"], crit["simple1"])}]
            gmax = max(filas, key=lambda f: f["G"])
            ctx.nuevo(ETAPA, "Grubbs (réplicas)", agr, APLICABLE, n=len(x), incluidas=list(cg["medicion_id"]),
                      origen_regla=COMPLEMENTARIA, referencia="Grubbs (1969); valores críticos ISO 5725-2:1994 tabla 5",
                      formula="G = máx|x_i − x̄| / s", estadistico={"simbolo": "G", "valor": gmax["G"]},
                      criticos={"5 %": crit["simple5"], "1 %": crit["simple1"], "origen": crit["origen"]},
                      hipotesis={"H0": "no hay valores atípicos entre las réplicas", "H1": "el valor extremo es atípico",
                                 "lateralidad": "bilateral"},
                      supuestos=[{"supuesto": "Réplicas independientes de una misma celda", "verificado": True,
                                  "evidencia": "Se agrupó por nivel y celda (RM-09)."},
                                 {"supuesto": "Normalidad aproximada", "verificado": False, "evidencia": "Ver etapa de normalidad."}],
                      tabla=filas, decision_inferencial=f"{gmax['medicion_id']} → {gmax['clasificacion']}",
                      limitaciones=(["Con n = 3 los valores críticos al 5 % y al 1 % coinciden (1,155): la prueba apenas discrimina."]
                                    if len(x) == 3 else ["Con n pequeño la prueba tiene baja potencia."] if len(x) < 7 else []),
                      texto=P.render(P.ATIPICOS, prueba="la prueba de Grubbs para un valor extremo", n=len(x),
                                     variable=ctx.obs.nombre_objeto, agrupacion=agr, referencia="tabla 5 de ISO 5725-2:1994",
                                     supuestos="réplicas independientes de una misma celda", simbolo="G", valor=P.fmt(gmax["G"]),
                                     critico_o_p=f"{P.fmt(crit['simple5'])} (5 %) y {P.fmt(crit['simple1'])} (1 %)",
                                     clasificacion=gmax["clasificacion"], accion="sin exclusión automática",
                                     responsable="revisión técnica pendiente"))
    if not alguna:
        ctx.nuevo(ETAPA, "Grubbs (réplicas)", "todas las celdas", DATOS_INSUFICIENTES, origen_regla=COMPLEMENTARIA,
                  motivos=["Ninguna celda tiene n ≥ 3 réplicas; no se aplica Grubbs a la mezcla de condiciones (RM-09)."])
