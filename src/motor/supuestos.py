"""Etapa de homocedasticidad (igualdad de varianzas entre series), después de la normalidad.

Secuencia (RM-26), por punto, sobre los residuos del modelo de celdas:
  1. Normalidad (etapa anterior, Shapiro-Wilk).
  2. Solo si hay normalidad → prueba de Bartlett (Bartlett, 1937; Montgomery, 2017 §3.4.1). Su resultado decide:
       varianzas iguales → ANOVA + Tukey HSD;   varianzas distintas → ANOVA de Welch + Games-Howell.
  3. Sin normalidad NO se aplica ANOVA (ni clásico ni de Welch): se va directo a Kruskal-Wallis + Dunn.
     La dispersión se describe con Fligner-Killeen (no paramétrica) solo para interpretar; no decide la ruta.
Se exige al menos 2 series con 3 o más lecturas cada una.
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
                prueba, simbolo, ref = "Bartlett", "K²", "Bartlett (1937); Montgomery (2017) §3.4.1"
            else:
                r = stats.fligner(*grupos.values())
                prueba, simbolo, ref = "Fligner-Killeen, informativa", "X²", "Conover, Johnson & Johnson (1981)"
        p = float(r.pvalue)
        rechaza = p < cfg.alfa
        # Solo con normalidad el resultado decide la ruta; sin normalidad la ruta ya es no paramétrica.
        ctx.homocedasticidad[punto_id] = ("rechaza" if rechaza else "no_rechaza") if normal else None
        s = {c: float(v.std(ddof=1)) for c, v in grupos.items()}
        ctx.decidir(f"Homocedasticidad {agr}: ¿las series tienen varianzas similares?",
                    ("NO" if rechaza else "SI") if normal else "NO DECIDE",
                    (f"Bartlett (datos normales): {simbolo} = {P.fmt(float(r.statistic))}, p = {P.fmt_p(p)} → "
                     + ("ANOVA de Welch." if rechaza else "ANOVA clásico.")) if normal else
                    (f"Datos no normales: no se aplica ANOVA; ruta Kruskal-Wallis. Fligner-Killeen (informativo): p = {P.fmt_p(p)}."), "RM-26")
        ctx.nuevo(ETAPA, f"Homocedasticidad ({prueba})", agr, APLICABLE, punto_id=punto_id, n=int(sum(len(v) for v in grupos.values())),
                  origen_regla=COMPLEMENTARIA, referencia=ref,
                  hipotesis={"H0": "todas las series tienen la misma varianza", "H1": "al menos una serie tiene distinta varianza",
                             "alfa": cfg.alfa},
                  estadistico={"simbolo": simbolo, "valor": float(r.statistic)}, gl=len(grupos) - 1, p_valor=p,
                  decision_inferencial="Se rechaza H0" if rechaza else "No se rechaza H0",
                  motivos=[] if normal else ["Informativa: con datos no normales esta prueba no decide la ruta (RM-26)."],
                  supuestos=[{"supuesto": "Normalidad de los residuos", "verificado": normal,
                              "evidencia": "Bartlett si son normales (decide la ruta); Fligner-Killeen si no (solo informa)"}],
                  tabla=[{"serie": c, "n": int(len(v)), "s": s[c]} for c, v in grupos.items()],
                  estimacion={"nombre": "razon_s", "valor": max(s.values()) / min(s.values()) if min(s.values()) > 0 else None,
                              "unidad": "", "s_max": max(s.values()), "s_min": min(s.values()),
                              "serie_max": max(s, key=s.get), "serie_min": min(s, key=s.get)},
                  texto=((f"Como los residuos son normales, se compararon las varianzas de {len(grupos)} series del {agr} con la prueba de "
                          f"Bartlett. {simbolo} = {P.fmt(float(r.statistic))}, p = {P.fmt_p(p)}: se {'rechaza' if rechaza else 'no rechaza'} H0, "
                          f"por lo tanto la comparación de condiciones usa {'ANOVA de Welch' if rechaza else 'ANOVA clásico'}. ") if normal else
                         (f"Los residuos del {agr} no son normales: no se aplica ANOVA y la comparación usa Kruskal-Wallis. La dispersión de las "
                          f"{len(grupos)} series se describe con Fligner-Killeen (p = {P.fmt_p(p)}) solo para interpretar: "
                          + ("hay series más dispersas que otras, por lo que Kruskal-Wallis compara distribuciones, no solo medianas. "
                             if rechaza else "las dispersiones son parecidas, por lo que Kruskal-Wallis compara medianas. "))
                         + (f"La serie más dispersa es {max(s, key=s.get)} (s = {P.fmt(max(s.values()))}) y la menos dispersa "
                            f"{min(s, key=s.get)} (s = {P.fmt(min(s.values()))})." if rechaza else "")))
