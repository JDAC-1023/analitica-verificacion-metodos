"""Decisión metrológica: compara cada estimación con su criterio aprobado.

Sin criterio aprobado, límite numérico o regla de decisión → CALCULADO_SIN_EVALUACION (RM-17).
"""

from __future__ import annotations

import operator

from src.motor import plantillas as P
from src.motor.configuracion import CriterioMotor
from src.motor.contexto import Contexto
from src.motor.resultado import (APLICABLE, CONFORME, CRITERIO_LAB, INDETERMINADO, NO_CONFORME, SIN_EVALUACION)

OPS = {"<=": operator.le, "<": operator.lt, ">=": operator.ge, ">": operator.gt}


def buscar(ctx: Contexto, caracteristica: str, punto_id: str) -> list[CriterioMotor]:
    return [c for c in ctx.cfg.criterios if c.caracteristica == caracteristica and (not c.puntos or punto_id in c.puntos)]


def evaluar_valor(valor: float, ic, c: CriterioMotor, parametro: str) -> tuple[str, str]:
    op = OPS[c.operador]
    lim = float(c.limite)
    if c.regla_decision == "estimacion":
        v = abs(valor) if parametro == "abs_sesgo" else valor
        etiqueta = "|sesgo|" if parametro == "abs_sesgo" else parametro
        ok = op(v, lim)
        return (CONFORME if ok else NO_CONFORME), f"{etiqueta} = {P.fmt(v)} {c.operador} {P.fmt(lim)}: {'se cumple' if ok else 'no se cumple'}."
    # regla de intervalo
    if not ic or ic[0] is None:
        return SIN_EVALUACION, "La regla de intervalo requiere un intervalo de confianza y este resultado no lo tiene."
    a, b = float(ic[0]), float(ic[1])
    if parametro == "abs_sesgo":
        peor = max(abs(a), abs(b))
        mejor = 0.0 if a <= 0 <= b else min(abs(a), abs(b))
        a, b = mejor, peor
    if c.operador in ("<=", "<"):
        if op(b, lim):
            return CONFORME, f"Todo el intervalo [{P.fmt(a)}; {P.fmt(b)}] cumple {c.operador} {P.fmt(lim)}."
        if not op(a, lim):
            return NO_CONFORME, f"Todo el intervalo [{P.fmt(a)}; {P.fmt(b)}] incumple {c.operador} {P.fmt(lim)}."
    else:
        if op(a, lim):
            return CONFORME, f"Todo el intervalo [{P.fmt(a)}; {P.fmt(b)}] cumple {c.operador} {P.fmt(lim)}."
        if not op(b, lim):
            return NO_CONFORME, f"Todo el intervalo [{P.fmt(a)}; {P.fmt(b)}] incumple {c.operador} {P.fmt(lim)}."
    return INDETERMINADO, f"El intervalo [{P.fmt(a)}; {P.fmt(b)}] cruza el límite {P.fmt(lim)}."


def ejecutar(ctx: Contexto) -> None:
    for r in ctx.resultados:
        if r.etapa != "desempeno" or r.estado != APLICABLE or not r.estimacion or r.caracteristica == "fuentes_variacion":
            continue
        candidatos = buscar(ctx, r.caracteristica, r.punto_id)
        estado, motivo, req = SIN_EVALUACION, "No hay un criterio definido para esta característica y nivel.", {}
        for c in candidatos:
            req = {"criterio": c.id, "parametro": c.parametro, "operador": c.operador, "limite": c.limite, "unidad": c.unidad,
                   "regla_decision": c.regla_decision, "fuente": c.fuente, "aprobado": c.aprobado, "origen": CRITERIO_LAB}
            if not c.aprobado:
                motivo = f"El criterio {c.id} no está aprobado."
                continue
            if c.limite is None:
                motivo = f"El criterio {c.id} no tiene límite numérico."
                continue
            if c.regla_decision not in ("estimacion", "intervalo"):
                motivo = f"El criterio {c.id} no tiene una regla de decisión documentada."
                continue
            if not c.fuente.strip():
                motivo = f"El criterio {c.id} no declara su fuente."
                continue
            if c.unidad and ctx.obs.unidad and c.unidad.strip() != ctx.obs.unidad.strip():
                motivo = f"El criterio {c.id} está en «{c.unidad}» y el resultado en «{ctx.obs.unidad}»; no se convierten unidades (RM-19)."
                continue
            valor = r.estimacion["valor"]
            if valor is None:
                motivo = "La estimación no está disponible."
                continue
            estado, motivo = evaluar_valor(valor, r.ic, c, c.parametro)
            break
        r.requisito = req
        r.decision_metrologica = estado
        r.motivos = list(r.motivos) + ([f"Decisión metrológica: {motivo}"] if motivo else [])
        crit_txt = (f"{req['criterio']} ({req['parametro']} {req['operador']} {P.fmt(req['limite'])} {req.get('unidad') or ''}, "
                    f"regla «{req['regla_decision'] or 'sin regla'}», fuente: {req['fuente'] or 'sin fuente'})") if req else "ningún criterio"
        r.texto = r.texto.replace("{criterio}", crit_txt).replace("{estado}", f"{estado}. {motivo}")
        ctx.decidir(f"{r.tecnica} — {r.agrupacion}: ¿existe criterio aprobado con límite y regla de decisión?",
                    "SI" if estado != SIN_EVALUACION else "NO", motivo, "RM-17")
