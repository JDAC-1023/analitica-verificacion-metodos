"""Etapa de homocedasticidad (igualdad de varianzas entre series), después de la normalidad.

Regla (RM-26), por punto:
  - si los residuos de ese punto son compatibles con la normal → prueba de Bartlett (más potente con datos normales);
  - si no lo son, o no se pudo evaluar → prueba de Levene centrada en la mediana (Brown-Forsythe), robusta.
Se exige al menos 2 series con 3 o más lecturas cada una.

El resultado decide la ruta de la comparación de técnicos y patrones (fuentes.py):
  normal + varianzas iguales → ANOVA clásico + Tukey;
  normal + varianzas distintas → ANOVA de Welch + Games-Howell;
  no normal → Kruskal-Wallis + Dunn.
"""

from __future__ import annotations

import warnings

from scipy import stats

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.resultado import APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES, NO_APLICABLE

ETAPA = "homocedasticidad"


def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    if not (cfg.factores_precision_intermedia or cfg.es_interlaboratorio):
        ctx.nuevo(ETAPA, "Homocedasticidad", "todos los niveles", NO_APLICABLE, origen_regla=COMPLEMENTARIA,
                  motivos=["No se declararon condiciones que cambian: hay una sola serie por punto y no hay varianzas que comparar."])
        return
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        grupos = {c: cg["valor"].to_numpy(float) for c, cg in g.groupby("celda") if len(cg) >= 3}
        if len(grupos) < 2:
            ctx.homocedasticidad[punto_id] = None
            ctx.nuevo(ETAPA, "Homocedasticidad", agr, DATOS_INSUFICIENTES, punto_id=punto_id, origen_regla=COMPLEMENTARIA,
                      motivos=["Se necesitan al menos 2 series con 3 o más lecturas para comparar varianzas."])
            continue
        normal = ctx.normalidad.get(("precision", punto_id)) == "no_rechaza"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if normal:
                r = stats.bartlett(*grupos.values())
                prueba, simbolo, ref = "Bartlett", "K²", "Bartlett (1937); Montgomery (2017) §3.4"
            else:
                r = stats.levene(*grupos.values(), center="median")
                prueba, simbolo, ref = "Levene (mediana)", "W", "Levene (1960); Brown & Forsythe (1974)"
        p = float(r.pvalue)
        rechaza = p < cfg.alfa
        ctx.homocedasticidad[punto_id] = "rechaza" if rechaza else "no_rechaza"
        s = {c: float(v.std(ddof=1)) for c, v in grupos.items()}
        ctx.decidir(f"Homocedasticidad {agr}: ¿las series tienen varianzas similares?", "NO" if rechaza else "SI",
                    f"{prueba} ({'datos normales' if normal else 'datos no normales o no evaluables'}): {simbolo} = {P.fmt(float(r.statistic))}, "
                    f"p = {P.fmt_p(p)}.", "RM-26")
        ctx.nuevo(ETAPA, f"Homocedasticidad ({prueba})", agr, APLICABLE, punto_id=punto_id, n=int(sum(len(v) for v in grupos.values())),
                  origen_regla=COMPLEMENTARIA, referencia=ref,
                  hipotesis={"H0": "todas las series tienen la misma varianza", "H1": "al menos una serie tiene distinta varianza",
                             "alfa": cfg.alfa},
                  estadistico={"simbolo": simbolo, "valor": float(r.statistic)}, gl=len(grupos) - 1, p_valor=p,
                  decision_inferencial="Se rechaza H0" if rechaza else "No se rechaza H0",
                  supuestos=[{"supuesto": "Normalidad de los residuos (elige la prueba)", "verificado": normal,
                              "evidencia": "Bartlett si son normales; Levene si no"}],
                  tabla=[{"serie": c, "n": int(len(v)), "s": s[c]} for c, v in grupos.items()],
                  estimacion={"nombre": "razon_s", "valor": max(s.values()) / min(s.values()) if min(s.values()) > 0 else None,
                              "unidad": "", "s_max": max(s.values()), "s_min": min(s.values()),
                              "serie_max": max(s, key=s.get), "serie_min": min(s, key=s.get)},
                  texto=(f"Se compararon las varianzas de {len(grupos)} series del {agr} con la prueba de {prueba}, elegida porque los "
                         f"residuos {'son compatibles con la normal' if normal else 'no son normales (o no se pudo evaluar)'}. "
                         f"{simbolo} = {P.fmt(float(r.statistic))}, p = {P.fmt_p(p)}: se {'rechaza' if rechaza else 'no rechaza'} H0. "
                         + (f"La serie más dispersa es {max(s, key=s.get)} (s = {P.fmt(max(s.values()))}) y la menos dispersa "
                            f"{min(s, key=s.get)} (s = {P.fmt(min(s.values()))})." if rechaza else "")))
