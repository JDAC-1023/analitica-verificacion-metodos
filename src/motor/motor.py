"""Orquestador del motor estadístico.

Orden: limpieza → atípicos → normalidad → homocedasticidad → desempeño (pruebas según la ruta) → criterios → consolidación.
Devuelve un diccionario serializable con los resultados por etapa, el árbol de
decisiones, las conclusiones preliminares automáticas y los datos usados.
"""

from __future__ import annotations

import platform

import numpy as np
import pandas as pd
import scipy

from src.auditoria.huella import ahora_iso, json_canonico, sha256_bytes
from src.modelos.estudio import Estudio
from src.motor import atipicos, caracteristicas, criterios, desempeno, limpieza, normalidad, supuestos
from src.motor import plantillas as P
from src.motor.configuracion import ConfiguracionAnalisis
from src.motor.contexto import Contexto
from src.motor.datos import construir, estructura
from src.motor.reglas import matriz
from src.motor.resultado import (APLICABLE, CONFORME, DATOS_INSUFICIENTES, INDETERMINADO, NO_APLICABLE, NO_CONFORME,
                                 NO_IMPLEMENTADO, SIN_EVALUACION, limpio)

VERSION_MOTOR = "1.0.0"
ETAPAS = [("limpieza", "Limpieza y estructura"), ("atipicos", "Valores atípicos y consistencia"),
          ("normalidad", "Normalidad"), ("homocedasticidad", "Homocedasticidad (igualdad de varianzas)"),
          ("desempeno", "Desempeño y evaluación")]


def ejecutar(tablas: dict, e: Estudio, cfg: ConfiguracionAnalisis, meta: dict | None = None) -> dict:
    obs = construir(tablas, e, cfg)
    ctx = Contexto(e=e, cfg=cfg, obs=obs, est=estructura(obs))
    info_ruta = caracteristicas.ruta(ctx)
    limpieza.ejecutar(ctx, tablas)
    if len(obs.df) == 0:
        ctx.nuevo("limpieza", "Suficiencia", "global", DATOS_INSUFICIENTES, motivos=["No hay observaciones válidas del objeto."])
    else:
        atipicos.ejecutar(ctx)
        normalidad.ejecutar(ctx)
        supuestos.ejecutar(ctx)
        desempeno.ejecutar(ctx)
        criterios.ejecutar(ctx)
    filas = caracteristicas.consolidar(ctx)
    final = caracteristicas.conclusion_global(ctx, filas, info_ruta)
    datos = obs.df[["medicion_id", "punto_id", "punto", "celda", "valor"]].to_dict("records")
    salida = {
        "meta": {"estudio": e.codigo, "nombre_estudio": e.nombre, "version_diseno": e.version_diseno,
                 "version_analisis": cfg.version, "ejecutado_en": ahora_iso(), "motor": VERSION_MOTOR,
                 "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                 "scipy": scipy.__version__, "edicion_normativa_implementada": "ISO 5725-2:1994",
                 "edicion_configurada": cfg.version_normativa, **(meta or {})},
        "objeto": {"tipo": cfg.objeto_tipo, "id": cfg.objeto_id, "nombre": obs.nombre_objeto,
                   "descripcion": obs.descripcion_objeto, "unidad": obs.unidad},
        "estructura": ctx.est,
        "ruta": info_ruta,
        "resultados": [r.to_dict() for r in ctx.resultados],
        "arbol": [vars(n) for n in ctx.arbol],
        "caracteristicas": filas,
        "conclusion_final": final,
        "conclusiones": conclusiones_por_etapa(ctx, final),
        "datos": datos,
        "excluidas": obs.excluidas[["medicion_id", "punto_id", "celda", "valor", "motivo"]].to_dict("records")
        if len(obs.excluidas) else [],
        "reglas": matriz(),
    }
    if not (meta or {}).get("sensibilidad") and not (meta or {}).get("vista_previa") and len(obs.df):
        salida["sensibilidad"] = sensibilidad(tablas, e, cfg, ctx, salida)
    salida = limpio(salida)
    salida["meta"]["huella_resultado"] = sha256_bytes(json_canonico({k: v for k, v in salida.items() if k != "meta"}).encode())
    return salida


def sensibilidad(tablas: dict, e: Estudio, cfg: ConfiguracionAnalisis, ctx: Contexto, salida: dict) -> dict | None:
    """¿Qué pasa con los atípicos? Se recalcula SIN ellos solo para comparar (no es una exclusión) (RM-27)."""
    marcados = []
    for r in ctx.resultados:
        if r.etapa != "atipicos" or r.estado != APLICABLE:
            continue
        for f in r.tabla:
            if f.get("medicion_id") and f.get("clasificacion") in (atipicos.REZAGADO, atipicos.ATIPICO):
                marcados.append({"medicion_id": f["medicion_id"], "serie": r.agrupacion.replace("nivel ", ""),
                                 "clasificacion": f["clasificacion"], "valor": f.get("valor"), "G": f.get("G")})
    if not marcados:
        ctx.decidir("¿Hay datos atípicos?", "NO", "Ninguna lectura fue señalada: se continúa con todos los datos.", "RM-27")
        return {"marcados": [], "cambios": [], "cambia_conclusion": False}
    ya = {x.medicion_id for x in cfg.exclusiones}
    nuevos = [m for m in marcados if m["medicion_id"] not in ya]
    from src.motor.configuracion import Exclusion
    cfg2 = ConfiguracionAnalisis.from_dict(cfg.to_dict())
    cfg2.exclusiones = list(cfg.exclusiones) + [Exclusion(m["medicion_id"], "Análisis de sensibilidad (no es una exclusión)", "motor",
                                                          origen="sensibilidad") for m in nuevos]
    sin = ejecutar(tablas, e, cfg2, {"sensibilidad": True})
    def mapa(res):
        return {(f["codigo"], n["nivel"]): n for f in res["caracteristicas"] for n in f["niveles"]}
    con_m, sin_m = mapa(salida), mapa(sin)
    cambios = []
    for clave, n in con_m.items():
        m = sin_m.get(clave)
        if not m or n["valor"] is None or m["valor"] is None:
            continue
        if n["decision"] != m["decision"] or abs(n["valor"] - m["valor"]) > 1e-12:
            cambios.append({"caracteristica": clave[0], "nivel": clave[1].replace("nivel ", ""), "valor_con": n["valor"],
                            "valor_sin": m["valor"], "decision_con": n["decision"], "decision_sin": m["decision"],
                            "cambia_decision": n["decision"] != m["decision"]})
    cambia = sin["conclusion_final"]["estado"] != salida["conclusion_final"]["estado"]
    ctx.decidir("¿Hay datos atípicos?", "SI",
                f"{len(marcados)} lectura(s) señalada(s). Sin ellas, {sum(c['cambia_decision'] for c in cambios)} decisión(es) cambiaría(n)"
                f"{' y la conclusión global pasaría a ' + sin['conclusion_final']['estado'] if cambia else '; la conclusión global no cambia'}. "
                "Se continúa con todos los datos: excluir requiere causa técnica, responsable y versión nueva.", "RM-27")
    return {"marcados": marcados, "cambios": cambios, "cambia_conclusion": cambia,
            "conclusion_sin": sin["conclusion_final"]["estado"]}


def _cuenta(res, etapa):
    r = [x for x in res if x.etapa == etapa]
    return r, sum(x.estado == APLICABLE for x in r)


def conclusiones_por_etapa(ctx: Contexto, final: dict) -> dict:
    """Conclusiones técnicas preliminares, deterministas, por etapa."""
    res = ctx.resultados
    out = {}
    # limpieza
    lim = [r for r in res if r.etapa == "limpieza" and r.tecnica == "Faltantes respecto al plan"]
    if lim:
        est = lim[0].estimacion
        txt = (f"Se dispone de {lim[0].n} resultados válidos de {est['esperadas']} planificados "
               f"({P.fmt(est['valor'], 3)} % de faltantes). ")
        txt += ("Hay alertas de faltantes según el umbral del laboratorio: " + "; ".join(lim[0].limitaciones) + ". ") if lim[0].limitaciones else ""
        txt += f"{len(ctx.obs.excluidas)} medición(es) excluida(s) con motivo documentado. " if len(ctx.obs.excluidas) else ""
        desb = [d["punto"] for d in ctx.est["niveles"].values() if not d["balanceado"]]
        txt += f"Diseño desbalanceado en: {', '.join(desb)}. " if desb else "Diseño balanceado en todos los niveles. "
        out["limpieza"] = txt + "No se imputó ningún dato."
    # atípicos
    r, n = _cuenta(res, "atipicos")
    hall = []
    for x in r:
        if x.estado != APLICABLE:
            continue
        for f in x.tabla:
            c = f.get("clasificacion", "")
            if c in (atipicos.REZAGADO, atipicos.ATIPICO):
                quien = f.get("laboratorio") or f.get("medicion_id")
                hall.append(f"{x.tecnica} en {x.agrupacion}: {quien} → {c}")
    if n == 0:
        out["atipicos"] = "No fue posible aplicar pruebas de atípicos con los datos disponibles: " + \
            "; ".join(sorted({m.rstrip(".") for x in r for m in x.motivos})[:3]) + "."
    elif hall:
        out["atipicos"] = (f"Se aplicaron {n} prueba(s). Valores señalados para revisión técnica: " + "; ".join(hall) +
                           ". Ningún dato se excluyó automáticamente; cualquier exclusión requiere motivo técnico, "
                           "responsable y una nueva versión del análisis.")
    else:
        out["atipicos"] = f"Se aplicaron {n} prueba(s) y ningún valor se clasificó como rezagado o atípico."
    # normalidad
    r, n = _cuenta(res, "normalidad")
    rech = [x.agrupacion for x in r if x.decision_inferencial == "Se rechaza H0"]
    if n == 0:
        out["normalidad"] = "No se evaluó la normalidad: " + "; ".join(sorted({m.rstrip(".") for x in r for m in x.motivos})[:2]) + "."
    else:
        out["normalidad"] = (f"Se evaluaron {n} objeto(s). " + (f"Se rechaza H0 de normalidad en: {'; '.join(rech)}. "
                             "Los procedimientos afectados usan alternativas o lo declaran como limitación. " if rech else
                             "En ningún caso se rechaza H0 de normalidad (esto no demuestra normalidad). "))
    # homocedasticidad (solo decide donde hubo normalidad)
    r, n = _cuenta(res, "homocedasticidad")
    bart = [x for x in r if x.estado == APLICABLE and "informativa" not in x.tecnica]
    info = [x for x in r if x.estado == APLICABLE and "informativa" in x.tecnica]
    pt = lambda xs: ", ".join(x.agrupacion.replace("nivel ", "").split(" · ")[0] for x in xs)  # noqa: E731
    if n == 0:
        out["homocedasticidad"] = "No se evaluó la igualdad de varianzas: " + "; ".join(sorted({m.rstrip(".") for x in r for m in x.motivos})[:2]) + "."
    else:
        het = [x for x in bart if x.decision_inferencial == "Se rechaza H0"]
        homo = [x for x in bart if x.decision_inferencial != "Se rechaza H0"]
        partes = []
        if homo:
            partes.append(f"Datos normales y varianzas iguales (Bartlett) en {pt(homo)} → ANOVA clásico + Tukey.")
        if het:
            partes.append(f"Datos normales pero varianzas distintas (Bartlett) en {pt(het)} → ANOVA de Welch + Games-Howell.")
        if info:
            partes.append(f"Datos no normales en {pt(info)} → no se aplica ANOVA; Kruskal-Wallis + Dunn (Fligner-Killeen solo informa).")
        out["homocedasticidad"] = " ".join(partes)
    # desempeño
    partes, grupos = [], {}
    for x in res:
        if x.etapa != "desempeno" or x.estado != APLICABLE or not x.estimacion or x.caracteristica == "fuentes_variacion":
            continue
        grupos.setdefault((x.caracteristica, x.estimacion["nombre"]), []).append(x)
    for (_, nombre), xs in grupos.items():
        unidad = xs[0].estimacion.get("unidad") or ""
        vals = [x.estimacion["valor"] for x in xs]
        decs = {}
        for x in xs:
            decs[x.decision_metrologica or "—"] = decs.get(x.decision_metrologica or "—", 0) + 1
        rutas = sorted({x.tecnica for x in xs})
        rango = P.fmt(vals[0]) if len(vals) == 1 else f"de {P.fmt(min(vals))} a {P.fmt(max(vals))}"
        car = {"sesgo": "Sesgo", "repetibilidad": "Repetibilidad", "precision_intermedia": "Reproducibilidad intralaboratorio",
               "reproducibilidad": "Reproducibilidad interlaboratorio"}.get(xs[0].caracteristica, nombre)
        metodos = ", ".join(r.split("(")[-1].rstrip(")") for r in rutas)
        partes.append(f"{car} ({nombre}; método: {metodos}) en {len(xs)} punto(s): {rango} {unidad} → "
                      + ", ".join(f"{k}: {v}" for k, v in decs.items()))
    fv = [x for x in res if x.caracteristica == "fuentes_variacion" and x.estado == APLICABLE]
    if fv:
        cuenta = {}
        for x in fv:
            for f in x.estimacion["influyen"]:
                cuenta[f] = cuenta.get(f, 0) + 1
        partes.append("Fuentes de variación (ANOVA): " + ("; ".join(f"{k} influye en {v} de {len(fv)} punto(s)" for k, v in cuenta.items())
                                                          if cuenta else f"ninguna fuente significativa en los {len(fv)} punto(s)"))
    no_ap = [f"{x.tecnica}: {x.motivos[0].rstrip('.')}" for x in res if x.etapa == "desempeno" and x.estado in (NO_APLICABLE, DATOS_INSUFICIENTES) and x.motivos]
    out["desempeno"] = ("; ".join(partes) + ". " if partes else "No hay estimaciones de desempeño. ") + \
        (("No calculado: " + "; ".join(no_ap) + ".") if no_ap else "")
    out["conclusion_final"] = final["texto"] + (" Observaciones: " + " ".join(final["avisos"]) if final["avisos"] else "")
    return out


ESTADOS_COLOR = {CONFORME: "green", NO_CONFORME: "red", INDETERMINADO: "orange", SIN_EVALUACION: "gray",
                 NO_IMPLEMENTADO: "gray", NO_APLICABLE: "gray", DATOS_INSUFICIENTES: "orange", APLICABLE: "blue"}
