"""Gráficos de diagnóstico (PNG) generados a partir del resultado guardado.

Se generan desde `resultado.json` (datos + memoria de cálculo), de modo que el
informe puede reconstruirse sin volver a ejecutar el motor.
"""

from __future__ import annotations

import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402

SERIE = "#2a78d6"
ACENTO = "#eb6834"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
REJILLA = "#e4e3df"


def _estilo(ax, titulo, ylabel=""):
    ax.set_title(titulo, fontsize=9, color=TINTA, loc="left")
    ax.set_ylabel(ylabel, fontsize=8, color=TINTA_2)
    ax.tick_params(labelsize=7, colors=TINTA_2)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(REJILLA)
    ax.grid(axis="y", color=REJILLA, linewidth=0.6)
    ax.set_axisbelow(True)


def _png(fig) -> bytes:
    buf = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()


def puntos(resultado: dict, punto_id: str) -> bytes | None:
    datos = [d for d in resultado["datos"] if d["punto_id"] == punto_id]
    if not datos:
        return None
    celdas = sorted({d["celda"] for d in datos})
    fig, ax = plt.subplots(figsize=(6.4, 2.6))
    for i, c in enumerate(celdas):
        v = np.array([d["valor"] for d in datos if d["celda"] == c])
        jitter = np.linspace(-0.12, 0.12, len(v)) if len(v) > 1 else [0]
        ax.scatter(i + np.asarray(jitter), v, s=18, color=SERIE, alpha=0.85, edgecolor="white", linewidth=0.6, zorder=3)
        ax.hlines(v.mean(), i - 0.25, i + 0.25, color=TINTA, linewidth=1.4, zorder=4)
    ref = next((r["estimacion"].get("referencia") for r in resultado["resultados"]
                if r["etapa"] == "desempeno" and r.get("punto_id") == punto_id and r["caracteristica"] == "sesgo"
                and r.get("estimacion")), None)
    if ref is not None:
        ax.axhline(ref, color=ACENTO, linewidth=1, linestyle="--")
        ax.annotate("referencia", (len(celdas) - 0.5, ref), fontsize=7, color=TINTA_2, va="bottom", ha="right")
    ax.set_xticks(range(len(celdas)), celdas, rotation=20 if len(celdas) > 4 else 0, ha="right" if len(celdas) > 4 else "center")
    _estilo(ax, f"Resultados por celda — {datos[0]['punto']} (línea: media de celda)", resultado["objeto"]["unidad"])
    return _png(fig)


def qq(resultado: dict, objeto: str, punto_id: str) -> bytes | None:
    r = next((x for x in resultado["resultados"] if x["etapa"] == "normalidad" and f"qq:{objeto}:{punto_id}" in x["graficos"]), None)
    if r is None or not r["tabla"]:
        return None
    v = np.array([f["valor"] for f in r["tabla"]])
    (teo, ord_), (pend, inter, _) = stats.probplot(v, dist="norm")
    fig, ax = plt.subplots(figsize=(3.4, 2.8))
    ax.scatter(teo, ord_, s=16, color=SERIE, edgecolor="white", linewidth=0.6, zorder=3)
    ax.plot(teo, pend * np.asarray(teo) + inter, color=TINTA_2, linewidth=1)
    ax.set_xlabel("Cuantil normal teórico", fontsize=8, color=TINTA_2)
    _estilo(ax, f"Q-Q · {r['agrupacion'].split(' · objeto')[0]}", "Valor ordenado")
    return _png(fig)


def mandel(resultado: dict, punto_id: str, cual: str) -> bytes | None:
    r = next((x for x in resultado["resultados"] if f"mandel_{cual}:{punto_id}" in x["graficos"]), None)
    if r is None or not r["tabla"]:
        return None
    labs = [f["laboratorio"] for f in r["tabla"]]
    vals = [f[cual] for f in r["tabla"]]
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    ax.bar(range(len(labs)), vals, width=0.55, color=SERIE, zorder=3)
    for clave, estilo in (("5 %", ":"), ("1 %", "--")):
        lim = r["criticos"].get(clave)
        if lim is None:
            continue
        ax.axhline(lim, color=TINTA_2, linewidth=0.9, linestyle=estilo)
        ax.annotate(f"indicador {clave}", (len(labs) - 0.5, lim), fontsize=6.5, color=TINTA_2, va="bottom", ha="right")
        if cual == "h":
            ax.axhline(-lim, color=TINTA_2, linewidth=0.9, linestyle=estilo)
    ax.axhline(0, color=TINTA, linewidth=0.6)
    ax.set_xticks(range(len(labs)), labs, fontsize=7)
    _estilo(ax, f"Estadístico {cual} de Mandel — {r['agrupacion']}", cual)
    return _png(fig)


def generar(resultado: dict) -> dict[str, bytes]:
    """Todas las figuras referidas en los resultados: {clave: png}."""
    salida = {}
    for r in resultado["resultados"]:
        for clave in r.get("graficos", []):
            if clave in salida:
                continue
            partes = clave.split(":")
            if partes[0] == "puntos":
                png = puntos(resultado, partes[1])
            elif partes[0] == "qq":
                png = qq(resultado, partes[1], partes[2])
            elif partes[0] in ("mandel_h", "mandel_k"):
                png = mandel(resultado, partes[1], partes[0][-1])
            else:
                png = None
            if png:
                salida[clave] = png
    return salida


# ------------------------------------------------------------------ figuras de resumen (informe)
def _niveles(resultado):
    vistos = {}
    for d in resultado["datos"]:
        vistos.setdefault(d["punto_id"], d["punto"])
    return list(vistos.items())


def _corto(etiqueta: str) -> str:
    return etiqueta.split(" · ")[0]


def resumen_sesgo(resultado: dict, limite: float | None = None) -> bytes | None:
    filas = [r for r in resultado["resultados"] if r["etapa"] == "desempeno" and r["caracteristica"] == "sesgo"
             and r["estado"] == "APLICABLE" and r.get("estimacion")]
    if not filas:
        return None
    etiquetas = [_corto(r["agrupacion"].replace("nivel ", "")) for r in filas]
    vals = [r["estimacion"]["valor"] for r in filas]
    fig, ax = plt.subplots(figsize=(6.6, 2.7))
    x = np.arange(len(filas))
    for i, r in enumerate(filas):
        ic = r.get("ic")
        if ic and ic[0] is not None:
            ax.vlines(i, ic[0], ic[1], color=SERIE, linewidth=2, zorder=2)
    ax.scatter(x, vals, s=36, color=SERIE, edgecolor="white", linewidth=1.2, zorder=3)
    ax.axhline(0, color=TINTA_2, linewidth=0.8)
    if limite is not None:
        ax.axhspan(-limite, limite, color="#1baf7a", alpha=0.08, zorder=0)
        for s in (-1, 1):
            ax.axhline(s * limite, color="#1baf7a", linewidth=1, linestyle="--")
        ax.annotate(f"límite ±{limite:g}", (len(filas) - 0.6, limite), fontsize=7, color=TINTA_2, va="bottom", ha="right")
    ax.set_xticks(x, etiquetas, fontsize=7)
    _estilo(ax, "Sesgo por punto (punto = estimación · barra = intervalo de confianza 95 %)", resultado["objeto"]["unidad"])
    return _png(fig)


def resumen_precision(resultado: dict) -> bytes | None:
    series = {}
    for r in resultado["resultados"]:
        if r["etapa"] == "desempeno" and r["estado"] == "APLICABLE" and r["caracteristica"] in ("repetibilidad", "precision_intermedia", "reproducibilidad"):
            series.setdefault(r["caracteristica"], []).append((_corto(r["agrupacion"].replace("nivel ", "")), r["estimacion"]["valor"]))
    if not series:
        return None
    nombres = {"repetibilidad": "Repetibilidad s_r", "precision_intermedia": "Reproducibilidad intralab. s_I", "reproducibilidad": "Reproducibilidad interlab. s_R"}
    colores = [SERIE, ACENTO, "#1baf7a"]
    etiquetas = [e for e, _ in next(iter(series.values()))]
    fig, ax = plt.subplots(figsize=(6.6, 2.7))
    ancho = 0.8 / len(series)
    x = np.arange(len(etiquetas))
    for k, (car, pares) in enumerate(series.items()):
        mapa = dict(pares)
        ax.bar(x + (k - (len(series) - 1) / 2) * ancho, [mapa.get(e, 0) for e in etiquetas], width=ancho * 0.92,
               color=colores[k % 3], label=nombres[car], zorder=3)
    ax.set_xticks(x, etiquetas, fontsize=7)
    ax.legend(fontsize=7, frameon=False, loc="upper left", ncols=len(series))
    _estilo(ax, "Precisión por punto (desviación estándar)", resultado["objeto"]["unidad"])
    ax.set_ylim(0, ax.get_ylim()[1] * 1.18)
    return _png(fig)


def puntos_grid(resultado: dict) -> bytes | None:
    niveles = _niveles(resultado)
    if not niveles:
        return None
    cols = 4 if len(niveles) > 4 else len(niveles)
    filas = int(np.ceil(len(niveles) / cols))
    fig, axs = plt.subplots(filas, cols, figsize=(6.8, 1.75 * filas + 0.3), squeeze=False)
    for ax in axs.flat:
        ax.set_visible(False)
    for ax, (pid, et) in zip(axs.flat, niveles):
        ax.set_visible(True)
        datos = [d for d in resultado["datos"] if d["punto_id"] == pid]
        celdas = sorted({d["celda"] for d in datos})
        for i, c in enumerate(celdas):
            v = np.array([d["valor"] for d in datos if d["celda"] == c])
            ax.scatter(np.full(len(v), i), v, s=7, color=SERIE, alpha=0.8, zorder=3)
        ax.set_xticks([])
        _estilo(ax, _corto(et))
        ax.title.set_fontsize(7.5)
        ax.tick_params(labelsize=6)
    fig.suptitle("Resultados por grupo de condiciones en cada punto (cada columna de puntos = un grupo)", fontsize=8, color=TINTA, x=0.01, ha="left")
    return _png(fig)


def qq_grid(resultado: dict, objeto: str) -> bytes | None:
    rs = [r for r in resultado["resultados"] if r["etapa"] == "normalidad" and r["estado"] == "APLICABLE"
          and any(g.startswith(f"qq:{objeto}:") for g in r["graficos"])]
    if not rs:
        return None
    cols = 4 if len(rs) > 4 else len(rs)
    filas = int(np.ceil(len(rs) / cols))
    fig, axs = plt.subplots(filas, cols, figsize=(6.8, 1.75 * filas + 0.3), squeeze=False)
    for ax in axs.flat:
        ax.set_visible(False)
    for ax, r in zip(axs.flat, rs):
        ax.set_visible(True)
        v = np.array([f["valor"] for f in r["tabla"]])
        (teo, ord_), (pend, inter, _) = stats.probplot(v, dist="norm")
        color = ACENTO if r["decision_inferencial"] == "Se rechaza H0" else SERIE
        ax.scatter(teo, ord_, s=7, color=color, zorder=3)
        ax.plot(teo, pend * np.asarray(teo) + inter, color=TINTA_2, linewidth=0.8)
        _estilo(ax, f"{_corto(r['agrupacion'].replace('nivel ', ''))} · p={r['p_valor']:.3f}")
        ax.title.set_fontsize(7.5)
        ax.tick_params(labelsize=6)
    nombre = "unidades del sesgo" if objeto == "sesgo" else "residuos (precisión)"
    fig.suptitle(f"Gráficos cuantil-cuantil: {nombre}. Naranja = se rechaza la normalidad", fontsize=8, color=TINTA, x=0.01, ha="left")
    return _png(fig)


def interaccion_grid(resultado: dict) -> bytes | None:
    """Medias por combinación de factores en cada punto (líneas paralelas = sin interacción)."""
    rs = [r for r in resultado["resultados"] if r.get("caracteristica") == "fuentes_variacion" and r["estado"] == "APLICABLE"]
    if not rs:
        return None
    n = len(rs)
    cols = min(4, n)
    filas = int(np.ceil(n / cols))
    fig, ejes = plt.subplots(filas, cols, figsize=(6.6, 1.75 * filas + 0.5), squeeze=False)
    paleta = [SERIE, ACENTO, "#1baf7a", "#eda100", "#6250d6"]
    leyenda = None
    for k, r in enumerate(rs):
        ax = ejes[k // cols][k % cols]
        ctx = r["estimacion"]["contexto"]
        cruce = ctx.get("cruce")
        if cruce:
            xs = cruce["niveles_columnas"]
            for i, fila in enumerate(cruce["datos"]):
                ax.plot(range(len(xs)), [fila.get(c) for c in xs], marker="o", ms=3.5, lw=1.4, color=paleta[i % len(paleta)],
                        label=fila["nivel"])
            ax.set_xticks(range(len(xs)), xs, fontsize=6)
            leyenda = (cruce["filas"], cruce["columnas"])
        else:
            nombre, niveles = next(iter(ctx["por_factor"].items()))
            ax.plot(range(len(niveles)), [x["media"] for x in niveles], marker="o", ms=3.5, lw=1.4, color=SERIE)
            ax.set_xticks(range(len(niveles)), [x["nivel"] for x in niveles], fontsize=6)
        inf = r["estimacion"].get("influyen") or []
        _estilo(ax, _corto(r["agrupacion"].replace("nivel ", "")) + ("\ninfluye: " + ", ".join(inf) if inf else "\nninguna influye"), "")
        ax.title.set_fontsize(6.5)
        ax.tick_params(labelsize=6)
    for k in range(n, filas * cols):
        ejes[k // cols][k % cols].axis("off")
    if leyenda:
        h, l = ejes[0][0].get_legend_handles_labels()
        fig.legend(h, l, loc="upper center", ncols=min(6, len(l)), fontsize=6.5, frameon=False,
                   title=f"Líneas = {leyenda[0]} · eje x = {leyenda[1]}", title_fontsize=6.5)
        fig.subplots_adjust(top=0.82)
    buf = io.BytesIO()
    fig.tight_layout(rect=(0, 0, 1, 0.88 if leyenda else 1))
    fig.savefig(buf, format="png", dpi=160)
    plt.close(fig)
    return buf.getvalue()
