"""Ramificación verificación / validación y estado de cada característica.

Eurachem (2016) §4.2: un método validado que se adopta sin modificaciones se
verifica; un método nuevo, modificado o fuera de su alcance se valida. El motor
no decide qué características exige el laboratorio: las lee de la
configuración y señala las que están REQUERIDAS pero no implementadas.
"""

from __future__ import annotations

from src.motor.configuracion import CARACTERISTICAS
from src.motor.contexto import Contexto
from src.motor.resultado import (APLICABLE, CONFORME, DATOS_INSUFICIENTES, INDETERMINADO, NO_APLICABLE, NO_CONFORME,
                                 NO_IMPLEMENTADO, PENDIENTE_MODELO, SIN_EVALUACION)


def ruta(ctx: Contexto) -> dict:
    cfg, e = ctx.cfg, ctx.e
    if cfg.metodo_validado == "si" and not cfg.modificaciones.strip():
        sugerida = "Verificación"
    elif cfg.metodo_validado == "no" or cfg.modificaciones.strip():
        sugerida = "Validación"
    else:
        sugerida = None
    declarada = e.tipo
    coincide = sugerida is None or sugerida.lower() == (declarada or "").lower()
    ctx.decidir("¿El método está validado y se usa sin modificaciones?",
                {"si": "SI", "no": "NO", "": "SIN DATO"}[cfg.metodo_validado or ""] + (" (con modificaciones)" if cfg.modificaciones.strip() else ""),
                f"Ruta sugerida: {sugerida or 'no determinable'}; declarada en el estudio: {declarada}.", "RM-21")
    avisos = []
    if sugerida is None:
        avisos.append("No se indicó si el método está validado: la ruta verificación/validación queda PENDIENTE.")
    elif not coincide:
        avisos.append(f"El estudio está declarado como «{declarada}», pero según el estado del método correspondería «{sugerida}». "
                      "Requiere revisión técnica.")
    return {"declarada": declarada, "sugerida": sugerida, "coincide": coincide, "avisos": avisos,
            "documentacion_previa": cfg.documentacion_previa, "modificaciones": cfg.modificaciones}


def consolidar(ctx: Contexto) -> list[dict]:
    """Estado por característica: configurado, implementado, ejecución y decisión metrológica agregada."""
    salida = []
    for codigo, (nombre, implementada, ref) in CARACTERISTICAS.items():
        conf = ctx.cfg.caracteristica(codigo)
        estado_conf = conf.estado if conf else "PENDIENTE"
        res = [r for r in ctx.resultados if r.etapa == "desempeno" and r.caracteristica == codigo]
        if estado_conf == "NO_APLICABLE_JUSTIFICADA":
            ejec, decision = NO_APLICABLE, NO_APLICABLE
        elif estado_conf not in ("REQUERIDA", "SELECCIONADA"):
            ejec, decision = "NO_SOLICITADA" if estado_conf != "PENDIENTE" else "PENDIENTE", "—"
        elif not implementada:
            ejec, decision = NO_IMPLEMENTADO, NO_IMPLEMENTADO
        else:
            aplic = [r for r in res if r.estado == APLICABLE]
            if not aplic:
                ejec = res[0].estado if res else DATOS_INSUFICIENTES
                decision = ejec
            else:
                ejec = APLICABLE
                decs = [r.decision_metrologica for r in aplic]
                faltan = [r for r in res if r.estado != APLICABLE]
                if NO_CONFORME in decs:
                    decision = NO_CONFORME
                elif INDETERMINADO in decs:
                    decision = INDETERMINADO
                elif all(d == CONFORME for d in decs) and not faltan:
                    decision = CONFORME
                elif SIN_EVALUACION in decs:
                    decision = SIN_EVALUACION
                else:
                    decision = PENDIENTE_MODELO
        salida.append({"codigo": codigo, "caracteristica": nombre, "estado_configurado": estado_conf,
                       "justificacion": conf.justificacion if conf else "", "fuente": conf.fuente if conf else "",
                       "implementada": implementada, "referencia": ref, "ejecucion": ejec, "decision": decision,
                       "niveles": [{"nivel": r.agrupacion, "tecnica": r.tecnica, "estado": r.estado,
                                    "valor": (r.estimacion or {}).get("valor"), "decision": r.decision_metrologica or "—"} for r in res]})
    return salida


def conclusion_global(ctx: Contexto, filas: list[dict], info_ruta: dict) -> dict:
    requeridas = [f for f in filas if f["estado_configurado"] == "REQUERIDA"]
    activas = [f for f in filas if f["estado_configurado"] in ("REQUERIDA", "SELECCIONADA")]
    tipo = info_ruta["sugerida"] or info_ruta["declarada"]
    base = requeridas or activas
    if not base:
        estado, texto = "SIN_ALCANCE", "No se configuraron características requeridas ni seleccionadas: no hay conclusión de desempeño."
    elif any(f["decision"] == NO_CONFORME for f in base):
        nc = ", ".join(f["caracteristica"] for f in base if f["decision"] == NO_CONFORME)
        estado, texto = NO_CONFORME, f"El método NO CUMPLE en: {nc}."
    elif all(f["decision"] == CONFORME for f in base):
        estado = CONFORME
        texto = (f"Todas las características {'requeridas' if requeridas else 'seleccionadas'} cumplen sus criterios aprobados "
                 f"en todos los niveles evaluados.")
    elif any(f["decision"] == INDETERMINADO for f in base):
        estado, texto = INDETERMINADO, "Al menos una característica tiene un intervalo que cruza el límite: la decisión es indeterminada."
    elif any(f["decision"] in (NO_IMPLEMENTADO, DATOS_INSUFICIENTES, "PENDIENTE", PENDIENTE_MODELO) for f in base):
        pend = ", ".join(f"{f['caracteristica']} ({f['decision']})" for f in base
                         if f["decision"] in (NO_IMPLEMENTADO, DATOS_INSUFICIENTES, "PENDIENTE", PENDIENTE_MODELO))
        estado, texto = "INCOMPLETO", f"No es posible concluir: características sin resultado evaluable — {pend}."
    else:
        estado = SIN_EVALUACION
        texto = "Los resultados se calcularon, pero no todos tienen un criterio aprobado: no se emite conformidad."
    avisos = list(info_ruta["avisos"])
    no_normal = [r.agrupacion for r in ctx.resultados if r.etapa == "normalidad" and r.decision_inferencial == "Se rechaza H0"]
    if no_normal:
        avisos.append(f"Se rechazó la normalidad en {len(no_normal)} revisión(es) ({'; '.join(no_normal[:3])}"
                      f"{'…' if len(no_normal) > 3 else ''}); allí se usaron métodos no paramétricos o se declara como limitación (RM-25).")
    if avisos and estado == CONFORME:
        estado = "CONFORME_CON_OBSERVACIONES"
        texto = texto.rstrip(".") + ", con observaciones."
    info_ruta = {**info_ruta, "avisos": avisos}
    return {"tipo": tipo, "estado": estado, "texto": f"{tipo or 'Estudio'}: {texto}", "avisos": info_ruta["avisos"],
            "marco": "ISO 5725-1/-2:1994 (precisión y veracidad) y Eurachem (2016) (adecuación al uso)"}
