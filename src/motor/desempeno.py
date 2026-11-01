"""Etapa de desempeño: sesgo, repetibilidad, precisión intermedia y reproducibilidad.

Cada resultado deja separadas la estimación, la decisión inferencial y la
decisión metrológica (esta última la completa criterios.py) (RM-20).
"""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy import stats

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.datos import nombre_campo
from src.motor.normalidad import unidades_sesgo
from src.motor.resultado import (APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES, NO_APLICABLE, NORMA)

ETAPA = "desempeno"


def ic_desviacion(s2: float, gl: float, confianza: float) -> list:
    """IC para una desviación estándar con la distribución χ² (supone normalidad)."""
    if gl is None or gl <= 0 or s2 is None:
        return [None, None]
    a = 1 - confianza
    return [math.sqrt(gl * s2 / stats.chi2.ppf(1 - a / 2, gl)), math.sqrt(gl * s2 / stats.chi2.ppf(a / 2, gl))]


def varianza_agrupada(c) -> tuple[float | None, int]:
    """ISO 5725-2:1994 ec. 20: s_r² = Σ(n_ij−1)s_ij² / Σ(n_ij−1)."""
    sub = c[c["n"] >= 2]
    gl = int((sub["n"] - 1).sum())
    if gl == 0:
        return None, 0
    return float(((sub["n"] - 1) * sub["s"] ** 2).sum() / gl), gl


def anova_un_factor(c) -> dict:
    """ANOVA de un factor de efectos aleatorios con grupos posiblemente desbalanceados."""
    n = c["n"].to_numpy(float)
    medias = c["media"].to_numpy(float)
    N, p = n.sum(), len(n)
    gran = float((n * medias).sum() / N)
    ssb = float((n * (medias - gran) ** 2).sum())
    s = np.nan_to_num(c["s"].to_numpy(float))
    ssw = float(((n - 1) * s ** 2).sum())
    glb, glw = p - 1, N - p
    msb, msw = ssb / glb, ssw / glw
    n0 = (N - (n ** 2).sum() / N) / (p - 1)
    sb2_bruto = (msb - msw) / n0
    sb2 = max(0.0, sb2_bruto)
    sI2 = msw + sb2
    if sb2 > 0:
        a, b = msb / n0, msw * (1 - 1 / n0)
        gl_sI = (a + b) ** 2 / (a ** 2 / glb + b ** 2 / glw)
    else:
        gl_sI = glw
    F = msb / msw if msw > 0 else None
    pF = float(stats.f.sf(F, glb, glw)) if F is not None else None
    return {"N": int(N), "p": p, "media_general": gran, "SSB": ssb, "SSW": ssw, "gl_entre": glb, "gl_dentro": int(glw),
            "MSB": msb, "MSW": msw, "n0": n0, "s_b2_bruto": sb2_bruto, "s_b2": sb2, "s_r2": msw, "s_I2": sI2,
            "gl_sI": gl_sI, "F": F, "p_F": pF}


def iso_reproducibilidad(c) -> dict:
    """ISO 5725-2:1994 ec. 19–24 para un nivel."""
    n = c["n"].to_numpy(float)
    y = c["media"].to_numpy(float)
    p = len(n)
    T1, T2 = n.sum(), (n ** 2).sum()
    m = float((n * y).sum() / T1)
    sr2, gl = varianza_agrupada(c)
    sd2 = float((n * (y - m) ** 2).sum() / (p - 1))
    nbar = (T1 - T2 / T1) / (p - 1)
    sL2_bruto = (sd2 - (sr2 or 0.0)) / nbar
    sL2 = max(0.0, sL2_bruto)
    sR2 = sL2 + (sr2 or 0.0)
    return {"p": p, "m": m, "s_r2": sr2, "gl_r": gl, "s_d2": sd2, "n_barra": nbar, "s_L2_bruto": sL2_bruto,
            "s_L2": sL2, "s_R2": sR2, "s_r": math.sqrt(sr2) if sr2 is not None else None, "s_L": math.sqrt(sL2),
            "s_R": math.sqrt(sR2)}


def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    activas = [c for c in ("sesgo", "repetibilidad", "precision_intermedia", "reproducibilidad") if cfg.activa(c)]
    ctx.decidir("¿Qué características de desempeño están seleccionadas o son requeridas?", ", ".join(activas) or "ninguna",
                "Se calculan solo las características activas en la configuración.", "RM-21")
    if "sesgo" in activas:
        _sesgo(ctx)
    if "repetibilidad" in activas:
        _repetibilidad(ctx)
    if "precision_intermedia" in activas:
        _precision_intermedia(ctx)
        from src.motor import fuentes
        fuentes.ejecutar(ctx)
    if "reproducibilidad" in activas:
        _reproducibilidad(ctx)


# ------------------------------------------------------------------ sesgo
def _referencia(ctx: Contexto, punto_id: str):
    cfg = ctx.cfg
    if cfg.referencia_tipo == "objeto_es_diferencia":
        return 0.0, None, "el objeto ya es una diferencia frente a la referencia (valor de referencia 0)"
    ref = next((r for r in cfg.referencias if r.punto_id == punto_id), None)
    if ref is None or ref.valor is None:
        return None, None, ""
    return float(ref.valor), ref.incertidumbre, ref.fuente or "sin fuente declarada"


def _sesgo(ctx: Contexto) -> None:
    cfg = ctx.cfg
    if cfg.referencia_tipo == "ninguna":
        ctx.nuevo(ETAPA, "Sesgo", "todos los niveles", NO_APLICABLE, caracteristica="sesgo", origen_regla=COMPLEMENTARIA,
                  motivos=["No hay valor de referencia configurado: el sesgo no puede estimarse."])
        return
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        xref, uref, fuente = _referencia(ctx, punto_id)
        if xref is None:
            ctx.nuevo(ETAPA, "Sesgo", agr, DATOS_INSUFICIENTES, caracteristica="sesgo", punto_id=punto_id,
                      origen_regla=COMPLEMENTARIA, motivos=[f"Falta el valor de referencia del nivel {punto}."])
            continue
        x, desc = unidades_sesgo(g)
        n = len(x)
        if n < 2:
            ctx.nuevo(ETAPA, "Sesgo", agr, DATOS_INSUFICIENTES, caracteristica="sesgo", punto_id=punto_id, n=n,
                      origen_regla=COMPLEMENTARIA, motivos=["Se necesita al menos 2 unidades independientes para estimar sesgo y dispersión."])
            continue
        d = x - xref
        b = float(d.mean())
        s = float(x.std(ddof=1))
        normal = ctx.normalidad.get(("sesgo", punto_id))
        base = dict(caracteristica="sesgo", punto_id=punto_id, n=n, incluidas=list(g["medicion_id"]),
                    estimacion={"nombre": "sesgo", "valor": b, "unidad": ctx.obs.unidad, "media": float(x.mean()),
                                "referencia": xref, "u_ref": uref, "s": s, "mediana_diferencias": float(np.median(d)),
                                "sesgo_relativo_pct": (b / xref * 100) if xref else None},
                    hipotesis={"H0": f"μ = {P.fmt(xref)}", "H1": f"μ ≠ {P.fmt(xref)}", "lateralidad": "bilateral", "alfa": cfg.alfa},
                    graficos=[f"puntos:{punto_id}"],
                    tabla=[{"unidad": i + 1, "valor": float(v), "diferencia": float(v - xref)} for i, v in enumerate(x)])
        lim = [f"Unidades analizadas: {desc}."]
        if uref is None:
            lim.append("No se declaró la incertidumbre del valor de referencia.")
        else:
            lim.append("La prueba de hipótesis no incorpora u_ref; la incertidumbre del valor de referencia se informa aparte.")
        if n < 3:
            ctx.decidir(f"Sesgo {agr}: ¿hay al menos 3 unidades para contrastar?", "NO", f"n={n}", "RM-13")
            ctx.nuevo(ETAPA, "Sesgo (solo estimación)", agr, APLICABLE, origen_regla=COMPLEMENTARIA, referencia="Eurachem (2016) §6.5",
                      formula="b = ȳ − x_ref", motivos=["n < 3: se informa la estimación sin prueba de hipótesis."],
                      decision_inferencial="No evaluada (datos insuficientes para contrastar).", limitaciones=lim, **base)
            continue
        if normal == "rechaza":
            ctx.decidir(f"Sesgo {agr}: ¿se rechazó la normalidad de las unidades?", "SI", "→ Wilcoxon de rangos con signo", "RM-13")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                if np.allclose(d, 0):
                    w, pv = None, None
                else:
                    r = stats.wilcoxon(d)
                    w, pv = float(r.statistic), float(r.pvalue)
            lim.append("Supuesto de simetría de las diferencias — requiere revisión técnica.")
            dec = "—" if pv is None else ("Se rechaza H0 (mediana de diferencias ≠ 0)" if pv < cfg.alfa else "No se rechaza H0")
            ctx.nuevo(ETAPA, "Sesgo (Wilcoxon)", agr, APLICABLE, origen_regla=COMPLEMENTARIA,
                      referencia="Wilcoxon (1945); Eurachem (2016) §6.5", formula="W = suma de rangos con signo de (y − x_ref)",
                      estadistico={"simbolo": "W", "valor": w}, p_valor=pv, ic=None, decision_inferencial=dec,
                      supuestos=[{"supuesto": "Diferencias simétricas", "verificado": False, "evidencia": "Requiere revisión técnica"}],
                      limitaciones=lim,
                      texto=P.render(P.SESGO, variable=ctx.obs.nombre_objeto, referencia=f"{P.fmt(xref)} ({fuente})", sesgo=P.fmt(b),
                                     unidad=ctx.obs.unidad, u_ref=P.fmt(uref), H0="mediana de diferencias = 0", H1="≠ 0",
                                     prueba="la prueba de rangos con signo de Wilcoxon", estadistico=f"W={P.fmt(w)}", gl="no aplica",
                                     p=P.fmt_p(pv), ic="no calculado", criterio="{criterio}", estado_metrologico="{estado}"),
                      **base)
            continue
        ctx.decidir(f"Sesgo {agr}: ¿se rechazó la normalidad de las unidades?",
                    "NO" if normal == "no_rechaza" else "NO EVALUADA",
                    "→ prueba t de una muestra" + ("" if normal else " (normalidad no evaluable: se deja como limitación)"), "RM-13")
        if normal is None:
            lim.append("No fue posible evaluar la normalidad de las unidades; la prueba t se basa en un supuesto no verificado.")
        se = s / math.sqrt(n)
        gl = n - 1
        if se == 0:
            t, pv, ic = None, None, [b, b]
            lim.append("Sin dispersión entre unidades: el estadístico t no está definido.")
        else:
            t = b / se
            pv = float(2 * stats.t.sf(abs(t), gl))
            tc = stats.t.ppf(1 - (1 - cfg.nivel_confianza) / 2, gl)
            ic = [b - tc * se, b + tc * se]
        dec = "—" if pv is None else ("Se rechaza H0: el sesgo es estadísticamente distinto de cero" if pv < cfg.alfa
                                      else "No se rechaza H0 (esto no demuestra ausencia de sesgo, RM-18)")
        ctx.nuevo(ETAPA, "Sesgo (t de Student)", agr, APLICABLE, origen_regla=COMPLEMENTARIA,
                  referencia="Student (1908); Eurachem (2016) §6.5", formula="t = (ȳ − x_ref)/(s/√n), gl = n − 1",
                  estadistico={"simbolo": "t", "valor": t}, gl=gl, p_valor=pv, ic=ic, decision_inferencial=dec,
                  supuestos=[{"supuesto": "Unidades independientes", "verificado": True, "evidencia": desc},
                             {"supuesto": "Normalidad de las unidades", "verificado": normal == "no_rechaza",
                              "evidencia": {"no_rechaza": "No se rechaza H0", "rechaza": "Se rechaza H0", None: "No evaluable"}[normal]}],
                  limitaciones=lim,
                  texto=P.render(P.SESGO, variable=ctx.obs.nombre_objeto, referencia=f"{P.fmt(xref)} ({fuente})", sesgo=P.fmt(b),
                                 unidad=ctx.obs.unidad, u_ref=P.fmt(uref), H0=f"H0: μ = {P.fmt(xref)}", H1=f"H1: μ ≠ {P.fmt(xref)}",
                                 prueba="la prueba t de una muestra", estadistico=f"t={P.fmt(t)}", gl=gl, p=P.fmt_p(pv),
                                 ic=P.ic_txt(ic, ctx.obs.unidad), criterio="{criterio}", estado_metrologico="{estado}"),
                  **base)


# ------------------------------------------------------------------ precisión
def _repetibilidad(ctx: Contexto) -> None:
    cfg = ctx.cfg
    sin_factores = not cfg.factores_precision_intermedia and not cfg.es_interlaboratorio
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        c = ctx.celdas(g)
        s2, gl = varianza_agrupada(c)
        if s2 is None:
            ctx.nuevo(ETAPA, "Repetibilidad", agr, DATOS_INSUFICIENTES, caracteristica="repetibilidad", punto_id=punto_id,
                      n=len(g), origen_regla=NORMA, motivos=["Ninguna celda tiene 2 o más réplicas (gl = 0)."])
            continue
        sr = math.sqrt(s2)
        ic = ic_desviacion(s2, gl, cfg.nivel_confianza)
        lim = []
        if sin_factores:
            lim.append("No se declararon condiciones cambiantes: se asume que todas las observaciones del nivel se obtuvieron "
                       "en condiciones de repetibilidad (declaración del laboratorio).")
        if (c["n"] < 2).any():
            lim.append(f"{int((c['n'] < 2).sum())} celda(s) con un solo resultado no aportan grados de libertad.")
        normal = ctx.normalidad.get(("precision", punto_id))
        if normal != "no_rechaza":
            ic = [None, None]
            lim.append("No se informa intervalo de confianza: el IC basado en χ² exige residuos normales y "
                       + ("se rechazó la normalidad." if normal == "rechaza" else "la normalidad no fue evaluable.")
                       + " La estimación puntual (varianzas agrupadas) no depende de ese supuesto.")
        condiciones = "repetibilidad dentro de " + (f"cada combinación de {', '.join(nombre_campo(ctx.e, f) for f in cfg.factores_precision_intermedia)}"
                                                     if cfg.factores_precision_intermedia else "cada laboratorio" if cfg.es_interlaboratorio else "el nivel")
        ctx.nuevo(ETAPA, "Repetibilidad (s_r)", agr, APLICABLE, caracteristica="repetibilidad", punto_id=punto_id,
                  n=len(g), incluidas=list(g["medicion_id"]), origen_regla=NORMA,
                  referencia="ISO 5725-2:1994 ec. 20; Eurachem (2016) §6.6", formula="s_r² = Σ(n_ij−1)s_ij² / Σ(n_ij−1)",
                  gl=gl, ic=ic, estimacion={"nombre": "s_r", "valor": sr, "unidad": ctx.obs.unidad, "s_r2": s2,
                                            "r_limite_95": 2.8 * sr},
                  tabla=[{"celda": r.celda, "n": int(r.n), "media": r.media, "s": r.s} for r in c.itertuples()],
                  decision_inferencial="No aplica (estimación).", limitaciones=lim, graficos=[f"puntos:{punto_id}"],
                  texto=P.render(P.PRECISION, tipo_precision="la desviación estándar de repetibilidad", variable=ctx.obs.nombre_objeto,
                                 nivel=punto, n=len(g), condiciones=condiciones, estimacion=f"s_r={P.fmt(sr)}", unidad=ctx.obs.unidad,
                                 ic=P.ic_txt(ic, ctx.obs.unidad), gl=gl, procedimiento="varianzas intracelda agrupadas (ISO 5725-2 ec. 20)",
                                 criterio="{criterio}", decision="{estado}"))


def _precision_intermedia(ctx: Contexto) -> None:
    cfg = ctx.cfg
    if not cfg.factores_precision_intermedia:
        ctx.nuevo(ETAPA, "Reproducibilidad intralaboratorio", "todos los niveles", DATOS_INSUFICIENTES, caracteristica="precision_intermedia",
                  origen_regla=COMPLEMENTARIA, motivos=["No se declararon los factores que cambian (día, técnico…)."])
        return
    nombres = ", ".join(nombre_campo(ctx.e, f) for f in cfg.factores_precision_intermedia)
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        c = ctx.celdas(g)
        if len(c) < 2 or int((c["n"] - 1).sum()) < 1:
            ctx.nuevo(ETAPA, "Reproducibilidad intralaboratorio", agr, DATOS_INSUFICIENTES, caracteristica="precision_intermedia",
                      punto_id=punto_id, n=len(g), origen_regla=COMPLEMENTARIA,
                      motivos=[f"Se necesitan ≥ 2 grupos de {nombres} y al menos un grupo con réplicas (grupos={len(c)})."])
            continue
        a = anova_un_factor(c)
        sI = math.sqrt(a["s_I2"])
        normal = ctx.normalidad.get(("precision", punto_id))
        homo = ctx.homocedasticidad.get(punto_id)
        con_prueba = normal == "no_rechaza" and homo != "rechaza"
        ic = ic_desviacion(a["s_I2"], a["gl_sI"], cfg.nivel_confianza) if normal == "no_rechaza" else [None, None]
        lim = []
        if len(cfg.factores_precision_intermedia) > 1:
            lim.append(f"Los factores ({nombres}) se combinaron en un único factor de agrupación para estimar s_I; su efecto por separado "
                       "se evalúa en «Fuentes de variación».")
        if a["s_b2_bruto"] < 0:
            lim.append("La varianza entre grupos estimada fue negativa y se tomó como 0 (RM-15).")
        if c["n"].nunique() > 1:
            lim.append(f"Diseño desbalanceado (n por grupo: {c['n'].tolist()}); se usó n0 = {P.fmt(a['n0'])}.")
        if len(c) < 4:
            lim.append(f"Solo {len(c)} grupos: la varianza entre grupos se estima con pocos grados de libertad.")
        if normal != "no_rechaza":
            lim.append("Datos no normales: s_I se informa como estimación por componentes de varianza (momentos), sin prueba F ni "
                       "intervalo χ², porque ambos exigen normalidad.")
        elif homo == "rechaza":
            lim.append("Varianzas distintas entre grupos: no se informa la prueba F clásica; la influencia de las condiciones se evalúa "
                       "con ANOVA de Welch en «Fuentes de variación».")
        if con_prueba:
            dec = ("Se rechaza H0: las condiciones aportan variación" if a["p_F"] is not None and a["p_F"] < cfg.alfa
                   else "No se rechaza H0 (no demuestra ausencia de efecto)")
        else:
            dec = "Sin prueba F (supuestos no cumplidos); ver «Fuentes de variación»"
        ctx.nuevo(ETAPA, "Reproducibilidad intralaboratorio (s_I)", agr, APLICABLE, caracteristica="precision_intermedia",
                  punto_id=punto_id, n=len(g), incluidas=list(g["medicion_id"]), origen_regla=COMPLEMENTARIA,
                  referencia="ISO 5725-3:1994; Eurachem (2016) §6.6.4 y anexo C; Satterthwaite (1946)",
                  algoritmo="Componentes de varianza (cuadrados medios de un factor)",
                  formula="s_b² = máx(0, (CM_entre − CM_dentro)/n0); s_I² = CM_dentro + s_b²",
                  gl=a["gl_sI"] if normal == "no_rechaza" else None, ic=ic,
                  estadistico={"simbolo": "F", "valor": a["F"]} if con_prueba else {}, p_valor=a["p_F"] if con_prueba else None,
                  hipotesis={"H0": "σ²_entre = 0", "H1": "σ²_entre > 0", "lateralidad": "unilateral", "alfa": cfg.alfa} if con_prueba else {},
                  supuestos=[{"supuesto": "Normalidad de residuos", "verificado": normal == "no_rechaza", "evidencia": "Etapa de normalidad"},
                             {"supuesto": "Varianzas similares", "verificado": homo == "no_rechaza", "evidencia": "Etapa de homocedasticidad"}],
                  estimacion={"nombre": "s_I", "valor": sI, "unidad": ctx.obs.unidad, "s_r": math.sqrt(a["s_r2"]),
                              "s_entre": math.sqrt(a["s_b2"]), "anova": a, "con_prueba_F": con_prueba},
                  decision_inferencial=dec,
                  tabla=[{"grupo": r.celda, "n": int(r.n), "media": r.media, "s": r.s} for r in c.itertuples()],
                  limitaciones=lim, graficos=[f"puntos:{punto_id}"],
                  texto=P.render(P.PRECISION, tipo_precision="la reproducibilidad intralaboratorio (precisión intermedia)", variable=ctx.obs.nombre_objeto, nivel=punto,
                                 n=len(g), condiciones=f"cambiando {nombres}", estimacion=f"s_I={P.fmt(sI)}", unidad=ctx.obs.unidad,
                                 ic=P.ic_txt(ic, ctx.obs.unidad), gl=P.fmt(a["gl_sI"], 3) if normal == "no_rechaza" else "no aplica",
                                 procedimiento="componentes de varianza" + (" con prueba F" if con_prueba else " (sin prueba F: supuestos no cumplidos)"),
                                 criterio="{criterio}", decision="{estado}"))


def _reproducibilidad(ctx: Contexto) -> None:
    cfg = ctx.cfg
    if not cfg.es_interlaboratorio:
        ctx.nuevo(ETAPA, "Reproducibilidad interlaboratorio (s_R)", "todos los niveles", NO_APLICABLE, caracteristica="reproducibilidad",
                  origen_regla=NORMA, referencia="ISO 5725-1:1994 §3.18; ISO 5725-3",
                  motivos=["La reproducibilidad entre laboratorios necesita varios laboratorios. La reproducibilidad dentro de tu "
                           "laboratorio (cambiando técnico, patrón o día) sí se mide: está en «Reproducibilidad intralaboratorio "
                           "(precisión intermedia)» (RM-05)."])
        return
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        c = ctx.celdas(g)
        if len(c) < 2 or varianza_agrupada(c)[0] is None:
            ctx.nuevo(ETAPA, "Reproducibilidad interlaboratorio (s_R)", agr, DATOS_INSUFICIENTES, caracteristica="reproducibilidad",
                      punto_id=punto_id, origen_regla=NORMA, motivos=["Se necesitan ≥ 2 laboratorios y réplicas dentro de laboratorio."])
            continue
        r = iso_reproducibilidad(c)
        lim = ["El IC de s_R no se calcula en esta versión (ISO 5725-1:1994 §6 da aproximaciones)."]
        if r["s_L2_bruto"] < 0:
            lim.append("s_L² resultó negativo y se tomó como 0 (ISO 5725-2:1994 §7.4.5.4).")
        if r["p"] < 8:
            lim.append(f"ISO 5725-1 recomienda un número suficiente de laboratorios; aquí p={r['p']}.")
        ctx.nuevo(ETAPA, "Reproducibilidad interlaboratorio (s_R)", agr, APLICABLE, caracteristica="reproducibilidad", punto_id=punto_id,
                  n=len(g), incluidas=list(g["medicion_id"]), origen_regla=NORMA, referencia="ISO 5725-2:1994 ec. 19–24",
                  formula="m̂ = Σn ȳ/Σn; s_d² = Σn(ȳ − m̂)²/(p−1); s_L² = (s_d² − s_r²)/n̄; s_R² = s_L² + s_r²",
                  gl=r["gl_r"], estimacion={"nombre": "s_R", "valor": r["s_R"], "unidad": ctx.obs.unidad, **r},
                  tabla=[{"laboratorio": x.celda, "n": int(x.n), "media": x.media, "s": x.s} for x in c.itertuples()],
                  decision_inferencial="No aplica (estimación).", limitaciones=lim, graficos=[f"puntos:{punto_id}"],
                  texto=P.render(P.PRECISION, tipo_precision="la desviación estándar de reproducibilidad", variable=ctx.obs.nombre_objeto,
                                 nivel=punto, n=len(g), condiciones=f"{r['p']} laboratorios", estimacion=f"s_R={P.fmt(r['s_R'])} "
                                 f"(s_r={P.fmt(r['s_r'])}, s_L={P.fmt(r['s_L'])}, m̂={P.fmt(r['m'])})", unidad=ctx.obs.unidad,
                                 ic="no calculado", gl=r["gl_r"], procedimiento="ISO 5725-2:1994 §7.4",
                                 criterio="{criterio}", decision="{estado}"))
