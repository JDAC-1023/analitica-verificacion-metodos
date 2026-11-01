"""Orquestador del motor estadístico.

Orden: limpieza → atípicos → normalidad → desempeño → criterios → consolidación.
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
from src.motor import atipicos, caracteristicas, criterios, desempeno, limpieza, normalidad
from src.motor import plantillas as P
from src.motor.configuracion import ConfiguracionAnalisis
from src.motor.contexto import Contexto
from src.motor.datos import construir, estructura
from src.motor.reglas import matriz
from src.motor.resultado import (APLICABLE, CONFORME, DATOS_INSUFICIENTES, INDETERMINADO, NO_APLICABLE, NO_CONFORME,
                                 NO_IMPLEMENTADO, SIN_EVALUACION, limpio)

VERSION_MOTOR = "1.0.0"
ETAPAS = [("limpieza", "Limpieza y estructura"), ("atipicos", "Valores atípicos y consistencia"),
          ("normalidad", "Normalidad"), ("desempeno", "Desempeño y evaluación")]


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
    salida = limpio(salida)
    salida["meta"]["huella_resultado"] = sha256_bytes(json_canonico({k: v for k, v in salida.items() if k != "meta"}).encode())
    return salida


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
    # desempeño
    partes, grupos = [], {}
    for x in res:
        if x.etapa != "desempeno" or x.estado != APLICABLE or not x.estimacion:
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
        car = {"sesgo": "Sesgo", "repetibilidad": "Repetibilidad", "precision_intermedia": "Precisión intermedia",
               "reproducibilidad": "Reproducibilidad"}.get(xs[0].caracteristica, nombre)
        metodos = ", ".join(r.split("(")[-1].rstrip(")") for r in rutas)
        partes.append(f"{car} ({nombre}; método: {metodos}) en {len(xs)} punto(s): {rango} {unidad} → "
                      + ", ".join(f"{k}: {v}" for k, v in decs.items()))
    no_ap = [f"{x.tecnica}: {x.motivos[0].rstrip('.')}" for x in res if x.etapa == "desempeno" and x.estado in (NO_APLICABLE, DATOS_INSUFICIENTES) and x.motivos]
    out["desempeno"] = ("; ".join(partes) + ". " if partes else "No hay estimaciones de desempeño. ") + \
        (("No calculado: " + "; ".join(no_ap) + ".") if no_ap else "")
    out["conclusion_final"] = final["texto"] + (" Observaciones: " + " ".join(final["avisos"]) if final["avisos"] else "")
    return out


ESTADOS_COLOR = {CONFORME: "green", NO_CONFORME: "red", INDETERMINADO: "orange", SIN_EVALUACION: "gray",
                 NO_IMPLEMENTADO: "gray", NO_APLICABLE: "gray", DATOS_INSUFICIENTES: "orange", APLICABLE: "blue"}
