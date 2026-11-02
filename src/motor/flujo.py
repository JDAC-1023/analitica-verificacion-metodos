"""Paso a paso del motor y conclusiones para el usuario final.

A partir del resultado guardado arma:
  - pasos(): el flujo condicional en orden (datos → atípicos → normalidad → homocedasticidad →
    comparación de condiciones → sesgo → repetibilidad → reproducibilidad), cada uno con
    «qué se hizo», «qué se encontró» y «por lo tanto, qué sigue»;
  - veredicto(): «tu método sirve / no sirve / sirve con observaciones»;
  - implicaciones(): qué significa para el método cada parámetro que no cumple y qué hacer;
  - mapa(): desempeño punto por punto (evolución a lo largo del intervalo).
Todo es determinista y se construye solo con valores calculados.
"""

from __future__ import annotations

from src.motor.plantillas import fmt, fmt_p

OK, ALERTA, FALLA, INFO = "ok", "alerta", "falla", "info"
NOMBRE = {"sesgo": "Sesgo (veracidad)", "repetibilidad": "Repetibilidad",
          "precision_intermedia": "Reproducibilidad intralaboratorio", "reproducibilidad": "Reproducibilidad interlaboratorio"}
DEC = {"CONFORME": "cumple", "NO_CONFORME": "no cumple", "INDETERMINADO": "no se puede decidir",
       "CALCULADO_SIN_EVALUACION": "sin criterio"}


def _p(r):
    return r["agrupacion"].replace("nivel ", "").split(" · ")[0]


def _res(resultado, etapa=None, pref=None, car=None, aplic=True):
    out = []
    for r in resultado["resultados"]:
        if etapa and r["etapa"] != etapa:
            continue
        if pref and not r["tecnica"].startswith(pref):
            continue
        if car and r.get("caracteristica") != car:
            continue
        if aplic and r["estado"] != "APLICABLE":
            continue
        out.append(r)
    return out


def _lista(xs, n=4):
    xs = list(xs)
    return ", ".join(xs[:n]) + (f" y {len(xs) - n} más" if len(xs) > n else "")


def pasos(resultado: dict) -> list[dict]:
    u = resultado["objeto"]["unidad"]
    salida = []

    # 1 · datos
    f = next(iter(_res(resultado, pref="Faltantes")), None)
    s = next(iter(_res(resultado, pref="Réplicas por serie")), None)
    if f:
        e = f["estimacion"]
        txt = f"Llegaron {f['n']} de {e['esperadas']} resultados planificados ({fmt(e['valor'], 3)} % faltantes); no se rellenó ninguno."
        if s and s["estimacion"]["valor"]:
            txt += " " + s["texto"]
        salida.append({"paso": "Datos", "estado": ALERTA if (e["faltantes"] or (s and s["estimacion"]["valor"])) else OK, "texto": txt,
                       "siguiente": "Con los datos válidos se buscan datos atípicos."})

    # 2 · atípicos
    sens = resultado.get("sensibilidad") or {}
    marcados = sens.get("marcados") or []
    grubbs = _res(resultado, etapa="atipicos")
    no_aplic = [r for r in resultado["resultados"] if r["etapa"] == "atipicos" and r["estado"] == "DATOS_INSUFICIENTES"]
    if not grubbs:
        salida.append({"paso": "¿Hay datos atípicos?", "estado": INFO,
                       "texto": "No se pudo buscar: " + (no_aplic[0]["motivos"][0] if no_aplic else "no hay series con 3 o más lecturas."),
                       "siguiente": "Se continúa con todos los datos hacia la normalidad."})
    elif not marcados:
        salida.append({"paso": "¿Hay datos atípicos?", "estado": OK,
                       "texto": f"NO. Se revisaron {len(grubbs)} series con la prueba de Grubbs y ninguna lectura es atípica.",
                       "siguiente": "Se continúa con todos los datos hacia la normalidad."})
    else:
        detalle = "; ".join(f"{m['medicion_id']} ({m['serie'].replace(' · Temperatura', '').replace('celda ', '')}, {m['clasificacion']})"
                            for m in marcados[:5])
        cambios = [c for c in sens.get("cambios", []) if c["cambia_decision"]]
        efecto = ("Si se quitaran, cambiaría: " + "; ".join(
            f"{NOMBRE[c['caracteristica']]} en {c['nivel'].split(' · ')[0]} pasa de «{DEC.get(c['decision_con'], c['decision_con'])}» "
            f"({fmt(c['valor_con'])}) a «{DEC.get(c['decision_sin'], c['decision_sin'])}» ({fmt(c['valor_sin'])})" for c in cambios[:4]) + "."
                  if cambios else "Quitarlos no cambiaría ninguna decisión: su efecto es pequeño.")
        salida.append({"paso": "¿Hay datos atípicos?", "estado": ALERTA,
                       "texto": f"SÍ: {len(marcados)} lectura(s): {detalle}. ¿Qué pasa con ellos? Se señalan, no se borran. {efecto}",
                       "siguiente": "Se continúa con todos los datos. Si se encuentra la causa técnica (bitácora), se excluyen en una versión 2 "
                                    "con motivo y responsable, y el motor recalcula."})

    # 3 · normalidad
    norm = _res(resultado, etapa="normalidad")
    if norm:
        rech = [r for r in norm if r["decision_inferencial"] == "Se rechaza H0"]
        if not rech:
            salida.append({"paso": "¿Los datos son normales?", "estado": OK,
                           "texto": f"SÍ. En las {len(norm)} revisiones (Shapiro-Wilk, α = 0,05) no se rechaza la normalidad.",
                           "siguiente": "Se puede seguir por la vía paramétrica: sesgo con t de Student y, antes de cualquier ANOVA, "
                                        "revisar la igualdad de varianzas (Bartlett)."})
        else:
            donde = _lista(sorted({_p(r) + (" (promedios)" if "sesgo" in r["agrupacion"] else " (lecturas)") for r in rech}))
            salida.append({"paso": "¿Los datos son normales?", "estado": ALERTA,
                           "texto": f"NO en {len(rech)} de {len(norm)} revisiones: {donde}. En el resto sí.",
                           "siguiente": "Donde no son normales NO se aplica ANOVA: se usan Wilcoxon (sesgo) y Kruskal-Wallis (técnicos y "
                                        "patrones), y no se calculan intervalos χ². Donde sí son normales se revisa la igualdad de varianzas."})

    # 4 · homocedasticidad (solo decide donde hubo normalidad)
    homo = _res(resultado, etapa="homocedasticidad")
    if homo:
        bart = [r for r in homo if "informativa" not in r["tecnica"]]
        info = [r for r in homo if "informativa" in r["tecnica"]]
        het = [r for r in bart if r["decision_inferencial"] == "Se rechaza H0"]
        partes = []
        if bart:
            partes.append(f"Donde los datos son normales ({_lista(_p(r) for r in bart)}) se aplicó Bartlett: "
                          + ("varianzas iguales en todos." if not het else
                             f"varianzas distintas en {_lista(_p(r) for r in het)} (la serie más dispersa: "
                             + "; ".join(f"{_p(r)} {r['estimacion']['serie_max']}" for r in het[:3]) + ")."))
        if info:
            partes.append(f"Donde no son normales ({_lista(_p(r) for r in info)}) no se evalúa para decidir: no se usará ANOVA.")
        sig = []
        ok_pts = [r for r in bart if r["decision_inferencial"] != "Se rechaza H0"]
        if ok_pts:
            sig.append(f"{_lista(_p(r) for r in ok_pts)} → ANOVA clásico + Tukey")
        if het:
            sig.append(f"{_lista(_p(r) for r in het)} → ANOVA de Welch + Games-Howell")
        if info:
            sig.append(f"{_lista(_p(r) for r in info)} → Kruskal-Wallis + Dunn")
        salida.append({"paso": "¿Las varianzas son iguales (homocedasticidad)?", "estado": ALERTA if het else OK,
                       "texto": " ".join(partes), "siguiente": "Por lo tanto: " + "; ".join(sig) + "."})

    # 5 · comparación de condiciones
    fv = _res(resultado, car="fuentes_variacion")
    if fv:
        rutas = {}
        for r in fv:
            rutas.setdefault(r["estimacion"]["ruta_nombre"], []).append(_p(r))
        txt_rutas = " · ".join(f"{k}: {_lista(v)}" for k, v in rutas.items())
        con = [r for r in fv if r["estimacion"]["influyen"]]
        if not con:
            salida.append({"paso": "¿El resultado depende del técnico o del patrón?", "estado": OK,
                           "texto": f"NO hay diferencias significativas en ningún punto. Pruebas usadas → {txt_rutas}.",
                           "siguiente": "El método es robusto frente a esos cambios. Se evalúa el desempeño."})
        else:
            det = []
            for r in con[:3]:
                d = r["estimacion"]["donde"]
                partes = [f"{x['comparacion']} ({fmt(x['diferencia'])} {u}, p = {fmt_p(x['p'])})" for x in d[:2]]
                det.append(f"{_p(r)} → {', '.join(r['estimacion']['influyen'])}" + (f": {'; '.join(partes)}" if partes else ""))
            causas = {}
            for r in con:
                causas.update(r["estimacion"].get("causas", {}))
            salida.append({"paso": "¿El resultado depende del técnico o del patrón?", "estado": ALERTA,
                           "texto": f"SÍ en {len(con)} de {len(fv)} puntos. Dónde: " + " | ".join(det)
                                    + (f" (y {len(con) - 3} punto(s) más)" if len(con) > 3 else "")
                                    + ". Por qué (origen probable): " + "; ".join(f"{k} → {v}" for k, v in causas.items())
                                    + ". El detalle por punto y la prueba usada en cada uno están en «Fuentes de variación».",
                           "siguiente": "Esa diferencia aumenta la reproducibilidad intralaboratorio. Se evalúa el desempeño."})

    # 6–8 · desempeño
    for car in ("sesgo", "repetibilidad", "precision_intermedia", "reproducibilidad"):
        rs = _res(resultado, etapa="desempeno", car=car)
        if not rs:
            continue
        vals = [r["estimacion"]["valor"] for r in rs]
        decs = {}
        for r in rs:
            decs.setdefault(DEC.get(r.get("decision_metrologica"), "—"), []).append(_p(r))
        rango = f"{fmt(min(vals))} a {fmt(max(vals))} {u}" if len(vals) > 1 else f"{fmt(vals[0])} {u}"
        metodo = ""
        if car == "sesgo":
            m = {}
            for r in rs:
                m.setdefault(r["tecnica"].split("(")[-1].rstrip(")"), []).append(_p(r))
            metodo = " Prueba: " + " · ".join(f"{k} en {_lista(v, 3)}" for k, v in m.items()) + "."
        estado = FALLA if "no cumple" in decs else ALERTA if ("no se puede decidir" in decs or "sin criterio" in decs) else OK
        partes = "; ".join(f"{k} en {_lista(v)}" for k, v in decs.items())
        sig = {FALLA: "No cumple: ver qué implica en las conclusiones.", ALERTA: "Revisar el criterio o la decisión.", OK: "Cumple."}[estado]
        salida.append({"paso": NOMBRE[car], "estado": estado, "texto": f"Valores de {rango} en {len(rs)} punto(s).{metodo} Frente al límite: {partes}.",
                       "siguiente": sig})
    v = veredicto(resultado)
    salida.append({"paso": "Veredicto", "estado": {"green": OK, "red": FALLA}.get(v["color"], ALERTA), "texto": v["texto"], "siguiente": ""})
    return salida


IMPLICA = {
    "sesgo": ("El método entrega resultados corridos: en promedio se aleja {rango} del valor de referencia en {puntos}, más de lo permitido. "
              "Usado tal cual, todos los resultados llevarán ese error sistemático.",
              "Aplicar la corrección hallada, verificar la calibración del patrón y del equipo, revisar el montaje y repetir la verificación."),
    "repetibilidad": ("Las lecturas repetidas en las mismas condiciones varían más de lo permitido en {puntos} ({rango}). El método no es estable "
                      "ni en las condiciones más favorables.",
                      "Revisar el tiempo de estabilización, la resolución del equipo y la posición del sensor; revisar los datos atípicos señalados."),
    "precision_intermedia": ("Al cambiar técnico, patrón o día, los resultados varían más de lo permitido en {puntos} ({rango}). El resultado depende "
                             "de quién mide o con qué se mide.",
                             "Ver en «fuentes de variación» qué condición origina la diferencia; estandarizar el procedimiento, reentrenar o revisar el patrón."),
    "reproducibilidad": ("Entre laboratorios los resultados varían más de lo permitido en {puntos} ({rango}).",
                         "Revisar la armonización del método entre laboratorios."),
}


def _veredicto_varios(resultado: dict) -> dict:
    """Varios resultados evaluados: el título es el del más desfavorable; el texto dice cómo quedó cada uno."""
    subs = resultado["objetos"]
    base = veredicto({**subs[0], "conclusion_final": {**subs[0]["conclusion_final"], "estado": resultado["conclusion_final"]["estado"]}})
    detalle = "; ".join(f"{x['objeto']['nombre']}: {veredicto(x)['titulo'].replace('TU MÉTODO ', '').lower()}" for x in subs)
    return {"titulo": base["titulo"], "color": base["color"],
            "texto": f"Se evaluaron {len(subs)} resultados, cada uno con todas sus pruebas por separado. {detalle}. "
                     "El veredicto del método es el del resultado más desfavorable."}


def implicaciones(resultado: dict) -> list[dict]:
    if resultado.get("multi"):
        return [{**i, "caracteristica": f"{x['objeto']['nombre']} · {i['caracteristica']}"}
                for x in resultado["objetos"] for i in implicaciones(x)]
    u = resultado["objeto"]["unidad"]
    sens = resultado.get("sensibilidad") or {}
    salida = []
    for car, (que, hacer) in IMPLICA.items():
        malos = [r for r in _res(resultado, etapa="desempeno", car=car) if r.get("decision_metrologica") == "NO_CONFORME"]
        if not malos:
            continue
        vals = [r["estimacion"]["valor"] for r in malos]
        rango = f"{fmt(min(vals))}–{fmt(max(vals))} {u}" if len(vals) > 1 else f"{fmt(vals[0])} {u}"
        nota = ""
        rescatables = [c for c in sens.get("cambios", []) if c["caracteristica"] == car and c["cambia_decision"]
                       and c["decision_sin"] == "CONFORME"]
        if rescatables:
            nota = (" Atención: en " + _lista(c["nivel"].split(" · ")[0] for c in rescatables) + " el incumplimiento se debe a dato(s) atípico(s); "
                    "si se confirma su causa técnica y se excluyen en una versión 2, cumpliría.")
        if car == "precision_intermedia":
            fv = [r for r in _res(resultado, car="fuentes_variacion") if r["estimacion"]["influyen"]]
            if fv:
                nota += " Origen detectado: " + "; ".join(f"{_p(r)} → {', '.join(r['estimacion']['influyen'])}" for r in fv[:4]) + "."
        salida.append({"caracteristica": NOMBRE[car], "puntos": [_p(r) for r in malos],
                       "que_implica": que.format(rango=rango, puntos=_lista(_p(r) for r in malos)) + nota, "que_hacer": hacer})
    return salida


def veredicto(resultado: dict) -> dict:
    if resultado.get("multi"):
        return _veredicto_varios(resultado)
    estado = resultado["conclusion_final"]["estado"]
    imps = implicaciones(resultado)
    if estado == "CONFORME":
        return {"titulo": "TU MÉTODO SIRVE", "color": "green",
                "texto": "Todos los parámetros evaluados cumplen sus límites en todo el intervalo. El método es adecuado para su uso previsto."}
    if estado == "CONFORME_CON_OBSERVACIONES":
        norm = _res(resultado, etapa="normalidad")
        rech = [r for r in norm if r["decision_inferencial"] == "Se rechaza H0"]
        obs = []
        if rech:
            obs.append(f"los datos no tienen forma de campana en {len(rech)} de {len(norm)} revisiones; allí se usaron pruebas no "
                       "paramétricas, lo que es válido pero debe quedar registrado")
        ruta = resultado.get("ruta", {}).get("avisos") or []
        obs += [a for a in ruta if "normalidad" not in a]
        return {"titulo": "TU MÉTODO SIRVE, CON OBSERVACIONES", "color": "green",
                "texto": "Todos los parámetros cumplen sus límites en todo el intervalo. Observaciones: " + "; ".join(obs) + "."}
    if estado == "NO_CONFORME":
        malos = ", ".join(i["caracteristica"] for i in imps)
        return {"titulo": "TU MÉTODO NO SIRVE (TODAVÍA)", "color": "red",
                "texto": f"No cumple en: {malos}. Antes de usarlo hay que corregir la causa y volver a verificar. Mira «qué implica» y «qué hacer»."}
    if estado == "INDETERMINADO":
        return {"titulo": "NO SE PUEDE DECIDIR", "color": "orange",
                "texto": "Algún resultado está tan cerca del límite que su intervalo de confianza lo cruza. Hacen falta más datos para decidir."}
    if estado == "CALCULADO_SIN_EVALUACION":
        return {"titulo": "FALTAN LOS LÍMITES DE ACEPTACIÓN", "color": "gray",
                "texto": "Los parámetros se calcularon, pero sin límites aprobados no se puede decir si el método sirve. Defínelos en «Configurar»."}
    return {"titulo": "NO SE PUEDE CONCLUIR", "color": "orange", "texto": resultado["conclusion_final"]["texto"]}


def mapa(resultado: dict) -> tuple[list[str], list[list[str]]]:
    """Desempeño punto por punto: valor y decisión de cada parámetro; también si depende de técnico/patrón."""
    cars = [c for c in ("sesgo", "repetibilidad", "precision_intermedia", "reproducibilidad") if _res(resultado, etapa="desempeno", car=c)]
    fv = {_p(r): r for r in _res(resultado, car="fuentes_variacion")}
    puntos = []
    for r in resultado["resultados"]:
        if r["etapa"] == "desempeno" and r["estado"] == "APLICABLE" and r.get("caracteristica") in cars and _p(r) not in puntos:
            puntos.append(_p(r))
    marca = {"CONFORME": "✔", "NO_CONFORME": "✘", "INDETERMINADO": "?", "CALCULADO_SIN_EVALUACION": "·"}
    cab = ["Punto"] + [NOMBRE[c] for c in cars] + (["¿Depende de…?"] if fv else [])
    filas = []
    for p in puntos:
        fila = [p]
        for c in cars:
            r = next((x for x in _res(resultado, etapa="desempeno", car=c) if _p(x) == p), None)
            fila.append("—" if not r else f"{marca.get(r.get('decision_metrologica'), '·')} {fmt(r['estimacion']['valor'], 3)}")
        if fv:
            inf = fv[p]["estimacion"]["influyen"] if p in fv else []
            fila.append(", ".join(inf) if inf else "no")
        filas.append(fila)
    return cab, filas
