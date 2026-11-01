"""Etapa de normalidad.

El objeto de la prueba depende del procedimiento que la usa (RM-11):
  - sesgo: las unidades independientes del nivel (medias de celda si hay varias
    celdas; observaciones si hay una sola);
  - precisión: los residuos dentro de celda (y_ijk − ȳ_ij) del nivel.

La redacción es siempre «se rechaza H0» o «no se rechaza H0» (RM-12).
"""

from __future__ import annotations

import warnings

import numpy as np
from scipy import stats

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.resultado import APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES, NO_APLICABLE

ETAPA = "normalidad"
NOMBRES = {"shapiro_wilk": "Shapiro-Wilk", "anderson_darling": "Anderson-Darling", "lilliefors": "Lilliefors"}
MINIMOS = {"shapiro_wilk": 3, "anderson_darling": 4, "lilliefors": 4}
RAZON = {
    "shapiro_wilk": "su potencia en muestras pequeñas y moderadas (Shapiro & Wilk, 1965; Royston, 1995)",
    "anderson_darling": "su sensibilidad en las colas (Anderson & Darling, 1954)",
    "lilliefors": "ser la versión de Kolmogorov-Smirnov con parámetros estimados (Lilliefors, 1967)",
}


def prueba(x: np.ndarray, metodo: str) -> dict:
    """Devuelve {simbolo, valor, p} de la prueba elegida."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if metodo == "shapiro_wilk":
            r = stats.shapiro(x)
            return {"simbolo": "W", "valor": float(r.statistic), "p": float(r.pvalue)}
        if metodo == "anderson_darling":
            r = stats.anderson(x, dist="norm", method="interpolate")
            return {"simbolo": "A²", "valor": float(r.statistic), "p": float(r.pvalue)}
        if metodo == "lilliefors":
            from statsmodels.stats.diagnostic import lilliefors
            d, p = lilliefors(x, dist="norm", pvalmethod="table")
            return {"simbolo": "D", "valor": float(d), "p": float(p)}
    raise ValueError(f"Prueba de normalidad desconocida: {metodo}")


def unidades_sesgo(g) -> tuple[np.ndarray, str]:
    celdas = g.groupby("celda")["valor"]
    if celdas.ngroups > 1:
        return celdas.mean().to_numpy(float), f"{celdas.ngroups} medias de celda"
    return g["valor"].to_numpy(float), f"{len(g)} observaciones de una sola celda"


def residuos(g) -> np.ndarray:
    n = g.groupby("celda")["valor"].transform("size")
    sub = g[n >= 2]
    return (sub["valor"] - sub.groupby("celda")["valor"].transform("mean")).to_numpy(float)


def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    metodo = cfg.prueba_normalidad
    objetos = []
    if cfg.activa("sesgo") and cfg.referencia_tipo != "ninguna":
        objetos.append("sesgo")
    if any(cfg.activa(c) for c in ("repetibilidad", "precision_intermedia", "reproducibilidad")):
        objetos.append("precision")
    ctx.decidir("¿Qué procedimientos necesitan un supuesto de normalidad?", ", ".join(objetos) or "ninguno",
                "Sesgo (prueba t) usa las unidades independientes; precisión (IC χ², ANOVA) usa los residuos dentro de celda.",
                "RM-11")
    if not objetos:
        ctx.nuevo(ETAPA, NOMBRES[metodo], "todos los niveles", NO_APLICABLE, origen_regla=COMPLEMENTARIA,
                  motivos=["Ninguna característica activa requiere el supuesto de normalidad."])
        return
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        for objeto in objetos:
            if objeto == "sesgo":
                x, desc = unidades_sesgo(g)
                obj_txt = f"las unidades independientes del sesgo ({desc})"
            else:
                x = residuos(g)
                desc = f"{len(x)} residuos dentro de celda"
                obj_txt = f"los residuos dentro de celda ({desc})"
            agr = f"nivel {punto} · objeto: {'unidades del sesgo' if objeto == 'sesgo' else 'residuos (precisión)'}"
            minimo = MINIMOS[metodo]
            if len(x) < minimo:
                ctx.normalidad[(objeto, punto_id)] = None
                ctx.nuevo(ETAPA, NOMBRES[metodo], agr, DATOS_INSUFICIENTES, n=len(x), origen_regla=COMPLEMENTARIA,
                          motivos=[f"{NOMBRES[metodo]} requiere al menos {minimo} valores; hay {len(x)}."])
                continue
            if np.allclose(x, x[0]):
                ctx.normalidad[(objeto, punto_id)] = None
                ctx.nuevo(ETAPA, NOMBRES[metodo], agr, DATOS_INSUFICIENTES, n=len(x), origen_regla=COMPLEMENTARIA,
                          motivos=["Los valores no presentan variación; la prueba no está definida."])
                continue
            r = prueba(x, metodo)
            rechaza = r["p"] < cfg.alfa
            ctx.normalidad[(objeto, punto_id)] = "rechaza" if rechaza else "no_rechaza"
            lim = []
            if len(x) < 8:
                lim.append("Con pocos valores la prueba tiene baja potencia: no rechazar H0 no es evidencia de normalidad.")
            if objeto == "precision":
                lim.append("Los residuos de una misma celda suman cero y no son estrictamente independientes.")
            ctx.nuevo(ETAPA, NOMBRES[metodo], agr, APLICABLE, n=len(x), origen_regla=COMPLEMENTARIA,
                      referencia=RAZON[metodo], algoritmo=f"{NOMBRES[metodo]} (SciPy / statsmodels)",
                      hipotesis={"H0": "los valores provienen de una distribución normal",
                                 "H1": "los valores no provienen de una distribución normal", "alfa": cfg.alfa},
                      estadistico={"simbolo": r["simbolo"], "valor": r["valor"]}, p_valor=r["p"],
                      decision_inferencial="Se rechaza H0" if rechaza else "No se rechaza H0",
                      graficos=[f"qq:{objeto}:{punto_id}"], limitaciones=lim,
                      tabla=[{"i": i + 1, "valor": float(v)} for i, v in enumerate(np.sort(x))],
                      texto=P.render(P.NORMALIDAD, objeto=obj_txt + f" del nivel {punto}", prueba=NOMBRES[metodo],
                                     razon=RAZON[metodo], H0="distribución normal", H1="distribución no normal",
                                     alfa=P.fmt(cfg.alfa), estadistico=f"{r['simbolo']}={P.fmt(r['valor'])}",
                                     p=P.fmt_p(r["p"]), decision="rechaza" if rechaza else "no rechaza",
                                     grafico="gráfico cuantil-cuantil adjunto"))
