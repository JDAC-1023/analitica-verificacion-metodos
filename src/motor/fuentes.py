"""Fuentes de variación: ANOVA factorial (técnico, patrón, día…) con interacciones.

Responde, por punto: ¿la variabilidad depende significativamente del técnico,
del patrón o de su combinación? La decisión es inferencial y automática (valor p
frente a α); no es un criterio de aceptación del método.

Secuencia (RM-26): normal + varianzas iguales → ANOVA factorial + Tukey; normal + varianzas distintas → Welch + Games-Howell;
no normal → Kruskal-Wallis + Dunn (NUNCA ANOVA sin normalidad).
Modelo de la ruta clásica (efectos fijos, sumas de cuadrados tipo II, statsmodels):
    y ~ C(A) + C(B) [+ C(C)] + interacciones de dos factores
Las interacciones solo se incluyen si cada combinación tiene ≥ 2 réplicas
(si no, el término no es estimable sin confundirse con el error).
"""

from __future__ import annotations

import itertools
import warnings

import numpy as np
import pandas as pd
from scipy import stats

from src.motor import plantillas as P
from src.motor.contexto import Contexto
from src.motor.datos import nombre_campo
from src.motor.resultado import APLICABLE, COMPLEMENTARIA, DATOS_INSUFICIENTES

ETAPA = "desempeno"
TECNICA = "Fuentes de variación (técnico, patrón)"


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


CAUSAS = {
    "Técnico": "la forma de medir de cada operador (tiempo de estabilización, posición del sensor, lectura, entrenamiento)",
    "Patrón": "el instrumento de referencia (calibración, deriva o corrección del certificado no aplicada)",
    "Día": "las condiciones de cada día (ambiente, estabilización del equipo, montaje)",
}


def causa(fuente: str) -> str:
    if "×" in fuente:
        return "una combinación específica de condiciones (por ejemplo, un técnico con un patrón concreto), no un factor solo"
    return CAUSAS.get(fuente, f"el cambio de «{fuente.lower()}»")


def _welch(grupos: list) -> tuple[float, float, float, float]:
    """ANOVA de una vía de Welch (varianzas distintas)."""
    k = len(grupos)
    n = np.array([len(g) for g in grupos], float)
    m = np.array([np.mean(g) for g in grupos])
    v = np.array([np.var(g, ddof=1) for g in grupos])
    w = n / v
    mw = (w * m).sum() / w.sum()
    a = (w * (m - mw) ** 2).sum() / (k - 1)
    tmp = (((1 - w / w.sum()) ** 2) / (n - 1)).sum()
    b = 1 + 2 * (k - 2) / (k ** 2 - 1) * tmp
    f = a / b
    gl2 = (k ** 2 - 1) / (3 * tmp)
    return float(f), float(k - 1), float(gl2), float(stats.f.sf(f, k - 1, gl2))


def _games_howell(datos: dict) -> list[dict]:
    salida = []
    claves = list(datos)
    k = len(claves)
    for a, b in itertools.combinations(claves, 2):
        xa, xb = np.asarray(datos[a]), np.asarray(datos[b])
        va, vb, na, nb = xa.var(ddof=1) / len(xa), xb.var(ddof=1) / len(xb), len(xa), len(xb)
        se = np.sqrt((va + vb) / 2)
        gl = (va + vb) ** 2 / (va ** 2 / (na - 1) + vb ** 2 / (nb - 1))
        q = abs(xa.mean() - xb.mean()) / se if se > 0 else np.inf
        p = float(stats.studentized_range.sf(q, k, gl)) if np.isfinite(q) else 0.0
        salida.append({"a": a, "b": b, "diferencia": float(xa.mean() - xb.mean()), "p": p})
    return salida


def _dunn(datos: dict) -> list[dict]:
    claves = list(datos)
    todos = np.concatenate([np.asarray(datos[c], float) for c in claves])
    rangos = stats.rankdata(todos)
    N = len(todos)
    _, cuenta = np.unique(todos, return_counts=True)
    ajuste = 1 - (cuenta ** 3 - cuenta).sum() / (N ** 3 - N)
    pos, medias_r, n = 0, {}, {}
    for c in claves:
        k = len(datos[c])
        medias_r[c], n[c] = rangos[pos:pos + k].mean(), k
        pos += k
    crudos = []
    for a, b in itertools.combinations(claves, 2):
        se = np.sqrt(N * (N + 1) / 12 * ajuste * (1 / n[a] + 1 / n[b]))
        z = (medias_r[a] - medias_r[b]) / se
        crudos.append({"a": a, "b": b, "diferencia": float(np.median(datos[a]) - np.median(datos[b])),
                       "p_crudo": float(2 * stats.norm.sf(abs(z)))})
    # Holm
    orden = sorted(range(len(crudos)), key=lambda i: crudos[i]["p_crudo"])
    m, previo = len(crudos), 0.0
    for rango_i, i in enumerate(orden):
        previo = max(previo, min(1.0, (m - rango_i) * crudos[i]["p_crudo"]))
        crudos[i]["p"] = previo
    return crudos


def _tukey(datos: dict, alfa: float) -> list[dict]:
    """Tukey HSD (Tukey-Kramer para grupos desiguales): q = |ȳa − ȳb| / √(MSE/2 · (1/na + 1/nb)), p con la distribución
    del rango estudentizado (k grupos, N − k gl). Se calcula solo el valor p de cada par; no hace falta el valor crítico
    (Tukey, 1949; Kramer, 1956)."""
    claves = list(datos)
    xs = [np.asarray(datos[c], float) for c in claves]
    k, N = len(xs), sum(len(x) for x in xs)
    gl = N - k
    mse = sum(((x - x.mean()) ** 2).sum() for x in xs) / gl if gl > 0 else np.nan
    salida = []
    for (ia, a), (ib, b) in itertools.combinations(enumerate(claves), 2):
        xa, xb = xs[ia], xs[ib]
        dif = float(xa.mean() - xb.mean())
        se = np.sqrt(mse / 2 * (1 / len(xa) + 1 / len(xb))) if gl > 0 else np.nan
        if not np.isfinite(se):
            p = None
        elif se == 0:
            p = 0.0 if dif != 0 else 1.0
        else:
            p = float(min(1.0, stats.studentized_range.sf(abs(dif) / se, k, gl)))
        salida.append({"a": a, "b": b, "diferencia": dif, "p": p})
    return salida


def ejecutar(ctx: Contexto) -> None:
    cfg = ctx.cfg
    factores = list(cfg.factores_precision_intermedia)
    if cfg.es_interlaboratorio or not factores:
        return
    columnas = {f"campo:{f}": nombre_campo(ctx.e, f) for f in factores}
    ctx.decidir("¿Se analizan las fuentes de variación (técnico, patrón, …)?", "SI",
                f"Factores declarados: {', '.join(columnas.values())}. La prueba se elige según normalidad y homocedasticidad.", "RM-23")
    for punto_id, g in ctx.niveles():
        punto = g["punto"].iloc[0]
        agr = f"nivel {punto}"
        activos = {c: n for c, n in columnas.items() if g[c].nunique() >= 2}
        gl_res = len(g) - int(np.prod([g[c].nunique() for c in activos])) if activos else 0
        if not activos or gl_res < 1:
            ctx.nuevo(ETAPA, TECNICA, agr, DATOS_INSUFICIENTES, caracteristica="fuentes_variacion", punto_id=punto_id, n=len(g),
                      origen_regla=COMPLEMENTARIA, motivos=["Se necesitan al menos 2 niveles de algún factor y réplicas dentro de cada combinación."])
            continue
        normal = ctx.normalidad.get(("precision", punto_id)) == "no_rechaza"
        homo = ctx.homocedasticidad.get(punto_id)
        if normal and homo != "rechaza":
            ruta, nombre_ruta = "anova", "ANOVA factorial clásico + Tukey HSD"
            motivo_ruta = "los residuos son normales y las varianzas son similares" + ("" if homo else " (homocedasticidad no evaluable)")
        elif normal:
            ruta, nombre_ruta = "welch", "ANOVA de Welch por factor + Games-Howell"
            motivo_ruta = "los residuos son normales pero las varianzas de las series son distintas"
        else:
            ruta, nombre_ruta = "kruskal", "Kruskal-Wallis por factor + Dunn (ajuste de Holm)"
            motivo_ruta = "los residuos no son normales"
        ctx.decidir(f"Fuentes {agr}: ¿qué prueba compara técnicos y patrones?", nombre_ruta, f"Porque {motivo_ruta}.", "RM-26")
        filas = []
        if ruta in ("anova", "welch"):
            a = anova_factorial(g, activos, cfg.alfa)          # solo con normalidad (supuesto del modelo lineal)
            r2, formula = a["r2"], a["formula"]
            for f in a["filas"]:
                if f["tipo"] == "residual":
                    filas.append({**f, "prueba": "—"})
                elif ruta == "anova":
                    filas.append({**f, "prueba": "ANOVA (F)"})
                elif f["tipo"] == "factor":                     # Welch: cada factor por separado; la interacción no se prueba
                    col = next(c for c, n in activos.items() if n == f["fuente"])
                    est, gl1, gl2, p = _welch([cg["valor"].to_numpy(float) for _, cg in g.groupby(col)])
                    filas.append({**f, "prueba": "Welch (F)", "F": est, "gl": f"{gl1:.0f}; {gl2:.1f}", "p": p, "influye": p < cfg.alfa})
            omitidas = a["omitidas"]
        else:                                                  # sin normalidad: ningún ANOVA
            r2, formula, omitidas = None, "Kruskal-Wallis por factor: H = 12/(N(N+1)) Σ R_i²/n_i − 3(N+1)", []
            n_tot = len(g)
            for col, nombre in activos.items():
                h = stats.kruskal(*[cg["valor"].to_numpy(float) for _, cg in g.groupby(col)])
                k = g[col].nunique()
                eps2 = float(h.statistic) / (n_tot - 1) if n_tot > 1 else None
                filas.append({"fuente": nombre, "tipo": "factor", "prueba": "Kruskal-Wallis (H)", "gl": k - 1, "SC": None, "CM": None,
                              "F": float(h.statistic), "p": float(h.pvalue), "eta2_parcial": None, "contribucion_pct": None,
                              "epsilon2": eps2, "influye": float(h.pvalue) < cfg.alfa})
        posthoc = []
        for f in filas:
            if not f.get("influye") or f["tipo"] != "factor":
                continue
            col = next(c for c, n in activos.items() if n == f["fuente"])
            datos = {str(k): cg["valor"].to_numpy(float) for k, cg in g.groupby(col)}
            pares = _tukey(datos, cfg.alfa) if ruta == "anova" else _games_howell(datos) if ruta == "welch" else _dunn(datos)
            metodo = {"anova": "Tukey HSD", "welch": "Games-Howell", "kruskal": "Dunn-Holm"}[ruta]
            for par in pares:
                posthoc.append({"factor": f["fuente"], "metodo": metodo, "comparacion": f"{par['a']} vs {par['b']}",
                                "diferencia": par["diferencia"], "p": par["p"], "significativa": par["p"] is not None and par["p"] < cfg.alfa})
        influyen = [f["fuente"] for f in filas if f.get("influye")]
        donde = [x for x in posthoc if x["significativa"]]
        ctxt = contexto_por_factor(g, activos)
        lim = []
        if omitidas and ruta == "anova":
            lim.append(f"Interacción no estimable (faltan réplicas en alguna combinación): {', '.join(omitidas)}.")
        if ruta != "anova" and len(activos) > 1:
            lim.append("Con esta ruta cada factor se compara por separado; la interacción no se prueba (se revisa en el gráfico de combinaciones).")
        if g.groupby(list(activos)).size().nunique() > 1 and ruta != "kruskal":
            lim.append("Diseño desbalanceado: la contribución porcentual usa sumas de cuadrados tipo II.")
        if ruta == "kruskal":
            lim.append("Sin normalidad no se aplica ANOVA: no hay descomposición en porcentajes de variación; el tamaño del efecto se "
                       "informa con ε² = H/(N − 1).")
        u = ctx.obs.unidad
        texto = (f"En el {agr} se compararon {', '.join(activos.values())} con {nombre_ruta}, porque {motivo_ruta}. "
                 + (f"Hay diferencias significativas por: {', '.join(influyen)}. " if influyen else
                    f"No hay diferencias significativas (p ≥ {P.fmt(cfg.alfa)}) entre {', '.join(activos.values()).lower()}. ")
                 + (" ".join(f"{x['factor']}: {x['comparacion']} difieren en {P.fmt(x['diferencia'])} {u} (p = {P.fmt_p(x['p'])})."
                             for x in donde[:6]))
                 + (" Origen probable: " + "; ".join(f"{fu} → {causa(fu)}" for fu in influyen) + "." if influyen else ""))
        ctx.nuevo(ETAPA, TECNICA, agr, APLICABLE, caracteristica="fuentes_variacion", punto_id=punto_id, n=int(len(g)),
                  incluidas=list(g["medicion_id"]), origen_regla=COMPLEMENTARIA,
                  referencia="Montgomery (2017) cap. 3 y 5; Welch (1951); Kruskal & Wallis (1952); Dunn (1964); Games & Howell (1976)",
                  algoritmo=nombre_ruta, formula=formula if ruta != "welch" else "ANOVA de Welch para cada factor por separado",
                  hipotesis={"H0": "la fuente no cambia el resultado", "H1": "la fuente cambia el resultado", "alfa": cfg.alfa},
                  estimacion={"nombre": "fuentes", "valor": None, "unidad": u, "anova": filas, "r2": r2, "contexto": ctxt,
                              "influyen": influyen, "ruta": ruta, "ruta_nombre": nombre_ruta, "motivo_ruta": motivo_ruta,
                              "posthoc": posthoc, "donde": donde, "causas": {fu: causa(fu) for fu in influyen}},
                  tabla=filas, graficos=[f"interaccion:{punto_id}"],
                  decision_inferencial=("Influyen: " + ", ".join(influyen)) if influyen else "Ninguna fuente significativa",
                  supuestos=[{"supuesto": "Normalidad de residuos", "verificado": normal, "evidencia": "Etapa de normalidad"},
                             {"supuesto": "Varianzas similares", "verificado": homo == "no_rechaza", "evidencia": "Etapa de homocedasticidad"}],
                  limitaciones=lim, texto=texto)
