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
