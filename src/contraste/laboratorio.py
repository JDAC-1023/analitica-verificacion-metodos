"""Contraste entre el motor y los informes técnicos del laboratorio (datos reales de temperatura y humedad relativa).

Tres columnas por cada estadístico:
  • Laboratorio: lo que imprime el informe técnico (transcrito en data/datos_reales/valores_informe_*.json) o lo que
    trae su hoja «Precisión Intermedia».
  • Reproducción: el mismo procedimiento del laboratorio recalculado aquí, de forma independiente, desde los datos
    (Shapiro-Wilk sobre las 15 lecturas del punto, Bartlett por operador, ANOVA aditiva Operador + Tiempo y componentes
    de varianza con las fórmulas del informe).
  • Motor: lo que calculó el motor determinista a partir del conjunto cargado y aprobado en la base de datos.

La comparación es numérica (diferencia absoluta) y de decisión (rechaza / no rechaza con α = 0,05). No es una prueba de
equivalencia: dos procedimientos distintos pueden coincidir en la decisión con valores p diferentes, y eso se explica.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from src.motor.multi import partes

ALFA = 0.05
VARIABLES = ["Corrección", "Inestabilidad", "Inhomogeneidad"]
RAIZ = Path(__file__).resolve().parents[2]


def valores_informe(magnitud: str) -> dict:
    return json.loads((RAIZ / "data" / "datos_reales" / f"valores_informe_{magnitud}.json").read_text(encoding="utf-8"))


def _punto_txt(nominal: float, unidad: str) -> str:
    v = f"{nominal:g}"
    return f"{v} {unidad}"


# ------------------------------------------------------------------ reproducción independiente del procedimiento del laboratorio
def reproducir(datos: pd.DataFrame) -> pd.DataFrame:
    """Una fila por variable y punto con los estadísticos del procedimiento del laboratorio."""
    from statsmodels.formula.api import ols
    from statsmodels.stats.anova import anova_lm
    filas = []
    for (nominal, unidad), g in datos.groupby(["nominal", "unidad"], sort=True):
        for var in VARIABLES:
            x = g[var].to_numpy(float)
            w, pw = stats.shapiro(x)
            grupos = [gg[var].to_numpy(float) for _, gg in g.groupby("operador", sort=False)]
            b, pb = stats.bartlett(*grupos)
            d = pd.DataFrame({"y": x, "op": g["operador"].astype(str).to_numpy(), "t": g["tiempo"].astype(str).to_numpy()})
            tabla = anova_lm(ols("y ~ C(op) + C(t)", data=d).fit(), typ=2)
            mc = {k: tabla.loc[k, "sum_sq"] / tabla.loc[k, "df"] for k in tabla.index}
            a, bt = d["op"].nunique(), d["t"].nunique()
            s2o = max(0.0, (mc["C(op)"] - mc["Residual"]) / bt)
            s2t = max(0.0, (mc["C(t)"] - mc["Residual"]) / a)
            filas.append({"punto": _punto_txt(nominal, unidad), "variable": var, "n": len(x),
                          "shapiro_W": w, "shapiro_p": pw, "bartlett_op": b, "bartlett_p": pb,
                          "F_operador": tabla.loc["C(op)", "F"], "p_operador": tabla.loc["C(op)", "PR(>F)"],
                          "F_tiempo": tabla.loc["C(t)", "F"], "p_tiempo": tabla.loc["C(t)", "PR(>F)"],
                          "MC_operador": mc["C(op)"], "MC_tiempo": mc["C(t)"], "MC_residual": mc["Residual"],
                          "s2_operador": s2o, "s2_tiempo": s2t, "s2_r": mc["Residual"], "u_lab": float(np.sqrt(s2o + s2t))})
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ lo que calculó el motor (desde resultado.json)
def del_motor(resultado: dict) -> pd.DataFrame:
    filas = []
    for p in partes(resultado):
        var = p["objeto"]["nombre"]
        porpunto: dict[str, dict] = {}
        for y in p["resultados"]:
            punto = y.get("agrupacion", "")
            if not punto.startswith("nivel "):
                continue
            clave = punto.split("·")[0].replace("nivel", "").strip()
            d = porpunto.setdefault(clave, {"punto": clave, "variable": var, "atipicos_grubbs": 0, "grubbs_series": 0})
            if y["etapa"] == "atipicos" and y["tecnica"].startswith("Grubbs") and y["estado"] == "APLICABLE":
                d["grubbs_series"] += 1
                d["atipicos_grubbs"] += sum(1 for t in y.get("tabla", []) if t.get("clasificacion") in ("rezagado (*)", "atípico (**)"))
            elif y["etapa"] == "normalidad" and y["estado"] == "APLICABLE" and y["tecnica"] == "Shapiro-Wilk" \
                    and "residuos" in punto:
                d["motor_shapiro_residuos_W"] = (y.get("estadistico") or {}).get("valor")
                d["motor_shapiro_residuos_p"] = y.get("p_valor")
            elif y["etapa"] == "homocedasticidad" and y["estado"] == "APLICABLE":
                d["motor_bartlett"] = (y.get("estadistico") or {}).get("valor")
                d["motor_bartlett_p"] = y.get("p_valor")
                d["motor_homocedasticidad"] = y["tecnica"]
            elif y["caracteristica"] == "repetibilidad" and y["estado"] == "APLICABLE":
                d["motor_s_r"] = y["estimacion"]["valor"]
            elif y["caracteristica"] == "precision_intermedia" and y["estado"] == "APLICABLE":
                d["motor_s_I"] = y["estimacion"]["valor"]
            elif y["caracteristica"] == "fuentes_variacion" and y["estado"] == "APLICABLE":
                est = y["estimacion"]
                d["motor_ruta"] = est.get("ruta_nombre")
                for f in est.get("anova", []):
                    if f["fuente"] == "Operador":
                        d["motor_F_operador"], d["motor_p_operador"] = f.get("F"), f.get("p")
                    elif f["fuente"] == "Tiempo":
                        d["motor_F_tiempo"], d["motor_p_tiempo"] = f.get("F"), f.get("p")
                    elif f["tipo"] == "residual":
                        d["motor_MC_residual"] = f.get("CM")
                ph = est.get("posthoc") or []
                d["motor_posthoc"] = ("; ".join(f"{x['factor']} {x['comparacion']}: p = {x['p']:.4f}" + (" (significativa)" if x.get("significativa") else "")
                                                for x in ph) if ph else "no se ejecuta (ningún factor influye)")
                d["motor_posthoc_pares"] = sum(1 for x in ph if x.get("significativa"))
                d["motor_influyen"] = ", ".join(est.get("influyen", [])) or "ninguno"
        filas.extend(porpunto.values())
    return pd.DataFrame(filas)


# ------------------------------------------------------------------ tablas de contraste
def contrastar(magnitud: str, datos: pd.DataFrame, resultado: dict, componentes_lab: list[dict]) -> dict[str, pd.DataFrame]:
    inf = valores_informe(magnitud)
    rep = reproducir(datos)
    mot = del_motor(resultado)
    puntos = inf["puntos"]
    lab = []
    for var in VARIABLES:
        for i, pt in enumerate(puntos):
            sw, ba, an = inf["shapiro"][var][i], inf["bartlett_operador"][var][i], inf["anova"][var][i]
            lab.append({"punto": pt, "variable": var, "lab_shapiro_W": sw[0], "lab_shapiro_p": sw[1], "lab_bartlett": ba[0],
                        "lab_bartlett_p": ba[1], "lab_F_operador": an[0], "lab_p_operador": an[1], "lab_F_tiempo": an[2], "lab_p_tiempo": an[3]})
    lab = pd.DataFrame(lab)
    t = lab.merge(rep, on=["punto", "variable"], how="left").merge(mot, on=["punto", "variable"], how="left")

    def dec(p):
        return None if p is None or pd.isna(p) else ("rechaza" if p <= ALFA else "no rechaza")

    filas = []
    for _, r in t.iterrows():
        for prueba, cl, cr, cm, nota in [
            ("Shapiro-Wilk (W)", "lab_shapiro_W", "shapiro_W", None, ""),
            ("Shapiro-Wilk (p)", "lab_shapiro_p", "shapiro_p", "motor_shapiro_residuos_p",
             "El laboratorio prueba las 15 lecturas del punto; el motor prueba los residuos dentro de cada operador (RM-11)."),
            ("Bartlett por operador (p)", "lab_bartlett_p", "bartlett_p", "motor_bartlett_p", ""),
            ("ANOVA · Operador (F)", "lab_F_operador", "F_operador", "motor_F_operador", ""),
            ("ANOVA · Operador (p)", "lab_p_operador", "p_operador", "motor_p_operador", ""),
            ("ANOVA · Tiempo (F)", "lab_F_tiempo", "F_tiempo", "motor_F_tiempo", ""),
            ("ANOVA · Tiempo (p)", "lab_p_tiempo", "p_tiempo", "motor_p_tiempo", ""),
        ]:
            vl, vr = r[cl], r[cr]
            vm = r[cm] if cm and cm in r and not pd.isna(r[cm]) else None
            es_p = prueba.endswith("(p)")
            filas.append({"magnitud": magnitud, "punto": r["punto"], "variable": r["variable"], "prueba": prueba,
                          "laboratorio": vl, "reproduccion": vr, "motor": vm,
                          "dif_reproduccion": abs(vr - vl) if vr is not None else None,
                          "dif_motor": abs(vm - vl) if vm is not None else None,
                          "decision_laboratorio": dec(vl) if es_p else "", "decision_motor": dec(vm) if (es_p and vm is not None) else "",
                          "coincide_decision": (dec(vl) == dec(vm)) if (es_p and vm is not None) else None, "nota": nota})
    comparacion = pd.DataFrame(filas)

    # componentes de varianza (solo Corrección: el laboratorio solo estima precisión intermedia para ella)
    comp = []
    clab = {c["punto"]: c for c in componentes_lab}
    for _, r in t[t["variable"] == "Corrección"].iterrows():
        c = clab.get(r["punto"], {})
        mr = r.get("motor_MC_residual")
        comp.append({"magnitud": magnitud, "punto": r["punto"],
                     "lab_s2_operador": c.get("s2_operador"), "lab_s2_tiempo": c.get("s2_tiempo"), "lab_s2_r": c.get("s2_r"),
                     "lab_u_lab": c.get("u_lab"), "rep_s2_operador": r["s2_operador"], "rep_s2_tiempo": r["s2_tiempo"],
                     "rep_s2_r": r["s2_r"], "rep_u_lab": r["u_lab"], "motor_MC_residual": mr,
                     "motor_s_r": r.get("motor_s_r"), "motor_s_I": r.get("motor_s_I"),
                     "dif_u_lab": abs(r["u_lab"] - c["u_lab"]) if c.get("u_lab") is not None else None})
    componentes = pd.DataFrame(comp)

    resumen = (comparacion[comparacion["coincide_decision"].notna()]
               .groupby(["magnitud", "prueba"])
               .agg(comparaciones=("coincide_decision", "size"), coincidencias=("coincide_decision", "sum"),
                    dif_max_motor=("dif_motor", "max"), dif_max_reproduccion=("dif_reproduccion", "max")).reset_index())
    motor_detalle = t[["punto", "variable", "atipicos_grubbs", "grubbs_series", "motor_ruta", "motor_influyen",
                       "motor_posthoc", "motor_s_r", "motor_s_I"]].copy()
    motor_detalle.insert(0, "magnitud", magnitud)
    return {"comparacion": comparacion, "componentes": componentes, "resumen": resumen, "motor": motor_detalle}


def grafico_p(comparacion: pd.DataFrame, titulo: str) -> bytes:
    """Valores p del laboratorio frente a los del motor (ANOVA y Bartlett), con la diagonal y α = 0,05."""
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = comparacion[comparacion["prueba"].isin(["ANOVA · Operador (p)", "ANOVA · Tiempo (p)", "Bartlett por operador (p)",
                                                 "Shapiro-Wilk (p)"]) & comparacion["motor"].notna()]
    fig, ax = plt.subplots(figsize=(5.2, 4.6), dpi=150)
    marcas = {"ANOVA · Operador (p)": ("o", "#2a6fdb"), "ANOVA · Tiempo (p)": ("s", "#1b998b"),
              "Bartlett por operador (p)": ("^", "#e09f3e"), "Shapiro-Wilk (p)": ("D", "#9e2a2b")}
    for prueba, g in d.groupby("prueba"):
        m, c = marcas[prueba]
        ax.scatter(g["laboratorio"], g["motor"], marker=m, s=34, color=c, label=prueba.replace(" (p)", ""), edgecolor="white", linewidth=0.6)
    ax.plot([0, 1], [0, 1], color="#888", lw=0.8, ls="--")
    ax.axhline(ALFA, color="#c00", lw=0.6, ls=":")
    ax.axvline(ALFA, color="#c00", lw=0.6, ls=":")
    ax.set_xlim(0, 1.02)
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Valor p del informe del laboratorio")
    ax.set_ylabel("Valor p calculado por el motor")
    ax.set_title(titulo, fontsize=10)
    ax.legend(fontsize=7, loc="lower right", frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()


def grafico_operadores(datos: pd.DataFrame, variable: str, titulo: str) -> bytes:
    import io
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    puntos = sorted(datos["nominal"].unique())
    fig, axs = plt.subplots(1, len(puntos), figsize=(2.3 * len(puntos) + 0.6, 3.0), dpi=150, squeeze=False)
    for ax, nom in zip(axs[0], puntos):
        g = datos[datos["nominal"] == nom]
        ops = list(dict.fromkeys(g["operador"]))
        for i, op in enumerate(ops):
            y = g[g["operador"] == op][variable].to_numpy(float)
            ax.scatter(np.full(len(y), i) + np.linspace(-0.12, 0.12, len(y)), y, s=16, color="#2a6fdb", alpha=0.8)
            ax.hlines(y.mean(), i - 0.25, i + 0.25, color="#9e2a2b", lw=1.4)
        ax.set_xticks(range(len(ops)))
        ax.set_xticklabels(ops, fontsize=7)
        ax.set_title(f"{nom:g} {g['unidad'].iloc[0]}", fontsize=8)
        ax.tick_params(axis="y", labelsize=7)
        ax.grid(alpha=0.25, axis="y")
    axs[0][0].set_ylabel(f"{variable} [{datos['unidad'].iloc[0]}]", fontsize=8)
    fig.suptitle(titulo, fontsize=9)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()
