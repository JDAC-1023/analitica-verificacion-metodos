"""Traducción a lenguaje sencillo de los resultados del motor.

Cada resultado técnico se acompaña de: qué hace la prueba, qué pasó (o por qué
no se aplicó) y, si hace falta, qué se necesitaría. Los textos se construyen
solo con los valores calculados; no cambian ninguna decisión.
"""

from __future__ import annotations

from src.motor.plantillas import fmt, fmt_p

ESTADO = {
    "APLICABLE": ("Se aplicó", "✅", "green"),
    "NO_APLICABLE": ("No corresponde", "⚪", "gray"),
    "DATOS_INSUFICIENTES": ("Faltan datos", "🟠", "orange"),
    "NO_IMPLEMENTADO": ("No disponible aún", "⚫", "gray"),
    "PENDIENTE_MODELO": ("Pendiente", "⚪", "gray"),
}
DECISION = {
    "CONFORME": ("Cumple", "🟢", "green", "El resultado cumple el criterio de aceptación aprobado."),
    "NO_CONFORME": ("No cumple", "🔴", "red", "El resultado no cumple el criterio de aceptación aprobado."),
    "INDETERMINADO": ("No se puede decidir", "🟡", "orange",
                      "El margen de incertidumbre del resultado cruza el límite: con estos datos no se puede afirmar que cumpla ni que no cumpla."),
    "CALCULADO_SIN_EVALUACION": ("Sin criterio", "⚪", "gray",
                                 "Se calculó, pero no hay un criterio de aceptación aprobado para decir si cumple."),
}
GLOBAL = {
    "CONFORME": ("CUMPLE", "green"), "CONFORME_CON_OBSERVACIONES": ("CUMPLE CON OBSERVACIONES", "green"),
    "NO_CONFORME": ("NO CUMPLE", "red"), "INDETERMINADO": ("NO SE PUEDE DECIDIR", "orange"),
    "INCOMPLETO": ("INCOMPLETO", "orange"), "CALCULADO_SIN_EVALUACION": ("CALCULADO, SIN CRITERIO", "gray"),
    "SIN_ALCANCE": ("SIN CARACTERÍSTICAS SELECCIONADAS", "gray"),
}

QUE_HACE = [
    ("Faltantes", "Cuenta cuántos resultados se esperaban según el plan y cuántos llegaron."),
    ("Estructura", "Revisa cómo quedaron agrupados los datos: puntos, grupos de condiciones y repeticiones por grupo."),
    ("Exclusiones", "Lista los datos que una persona decidió dejar por fuera, con su motivo."),
    ("Mandel h", "Compara el promedio de cada laboratorio con el de los demás para ver si alguno se aleja."),
    ("Mandel k", "Compara la dispersión de cada laboratorio con la de los demás."),
    ("Mandel", "Compara laboratorios entre sí (promedios y dispersión)."),
    ("Cochran", "Busca si algún laboratorio tiene una dispersión mucho mayor que los demás."),
    ("Grubbs (réplicas)", "Busca un dato raro dentro de las repeticiones hechas en las mismas condiciones."),
    ("Grubbs", "Busca un laboratorio cuyo promedio sea raro frente a los demás."),
    ("Dixon", "Otra forma de buscar datos raros en grupos pequeños."),
    ("Shapiro", "Revisa si los datos tienen la forma de campana (distribución normal) que suponen varias pruebas."),
    ("Anderson", "Revisa si los datos tienen forma de campana, poniendo atención a los extremos."),
    ("Lilliefors", "Revisa si los datos tienen forma de campana."),
    ("Sesgo", "Mide cuánto se desvía, en promedio, el resultado respecto al valor de referencia."),
    ("Repetibilidad", "Mide cuánto varían los resultados al repetir la medición en las mismas condiciones."),
    ("Precisión intermedia", "Mide cuánto varían los resultados cuando cambian condiciones del laboratorio (técnico, día, patrón)."),
    ("Reproducibilidad", "Mide cuánto varían los resultados entre laboratorios distintos."),
    ("Suficiencia", "Revisa que haya datos para analizar."),
]


def que_hace(tecnica: str) -> str:
    return next((t for p, t in QUE_HACE if tecnica.startswith(p)), "")


def _por_que_no(r: dict) -> tuple[str, str]:
    """Explicación sencilla de por qué no se aplicó y qué haría falta."""
    m = " ".join(r.get("motivos") or [])
    tec = r["tecnica"]
    if "no es interlaboratorio" in m or "no son laboratorios" in m:
        return ("Esta prueba es para comparar laboratorios distintos. Tu estudio se hizo en un solo laboratorio "
                "(cambiar de técnico no es cambiar de laboratorio), así que no corresponde usarla.",
                "Nada: es lo correcto para un estudio de un solo laboratorio.")
    if "n ≥ 3" in m or "Ninguna celda tiene n" in m:
        return ("Para buscar un dato raro hace falta tener al menos 3 repeticiones en exactamente las mismas condiciones. "
                "En tu diseño cada grupo tiene menos de 3, y mezclar grupos distintos daría conclusiones falsas.",
                "Si quieres esta revisión, planifica 3 o más repeticiones por combinación de condiciones.")
    if "Dixon" in tec:
        return ("No se cuenta todavía con las tablas oficiales verificadas de esta prueba; preferimos no usar valores inventados.",
                "Nada por ahora: los datos raros se revisan con Grubbs cuando hay suficientes repeticiones.")
    if "edición" in m:
        return ("La norma configurada es de una edición distinta a la que está programada (ISO 5725-2:1994). "
                "Para no mezclar ediciones, no se usan sus tablas.", "Corrige la edición en la configuración si fue un error.")
    if "referencia" in m:
        return ("Para medir el sesgo hay que saber cuál es el valor correcto (valor de referencia), y no se indicó.",
                "Indica el valor de referencia de cada punto, o marca que el dato ya es una diferencia (error o corrección).")
    if "requiere al menos" in m or "Se necesita al menos" in m or "Se necesitan" in m or "p=" in m:
        return ("Hay muy pocos datos para que esta prueba sea confiable. " + (r.get("motivos") or [""])[0],
                "Agrega más datos en este punto o grupo.")
    if "no presentan variación" in m or "sin variación" in m or "s = 0" in m:
        return ("Todos los valores son iguales; la prueba no se puede calcular cuando no hay variación.", "Revisa que los datos estén bien registrados.")
    if "Ninguna característica" in m:
        return ("No se pidió ninguna característica que necesite esta revisión.", "")
    if "factores" in m or "condiciones" in m:
        return ("No se indicó qué condiciones cambian en el laboratorio (técnico, día…), así que no se puede separar su efecto.",
                "En «Configurar», elige las condiciones que cambian.")
    if r["estado"] == "NO_IMPLEMENTADO":
        return ("Esta parte todavía no está programada en el motor.", "")
    return (m or "No se aplicó.", "")


def _resultado(r: dict) -> str:
    tec, e, u = r["tecnica"], r.get("estimacion") or {}, r.get("unidad") or ""
    di = r.get("decision_inferencial") or ""
    if tec.startswith("Faltantes"):
        return (f"Llegaron {r['n']} de {e.get('esperadas')} resultados esperados ({fmt(e.get('valor'), 3)} % faltantes). "
                "No se inventó ni se rellenó ningún dato.")
    if tec.startswith("Estructura"):
        return f"Los datos se analizan en {e.get('valor')} punto(s) de medición."
    if tec.startswith("Exclusiones"):
        return f"Se dejaron por fuera {r['n']} dato(s) por decisión técnica documentada; el dato original se conserva."
    if r["etapa"] == "normalidad":
        if di == "Se rechaza H0":
            return (f"Los datos NO tienen forma de campana (p = {fmt_p(r.get('p_valor'))}). "
                    "Por eso, donde hace falta, el motor usa métodos que no dependen de esa forma.")
        return (f"No hay evidencia de que los datos se alejen de la forma de campana (p = {fmt_p(r.get('p_valor'))}). "
                "Esto permite usar las pruebas habituales; no prueba que sean perfectamente normales.")
    if r["etapa"] == "atipicos":
        raros = [f.get("laboratorio") or f.get("medicion_id") for f in r.get("tabla", [])
                 if f.get("clasificacion") in ("rezagado (*)", "atípico (**)")]
        if raros:
            return (f"Se señalaron para revisión: {', '.join(map(str, raros))}. No se borró nada automáticamente; "
                    "una persona debe revisar si hay una causa técnica.")
        return "No se encontró ningún dato raro."
    if tec.startswith("Sesgo"):
        txt = f"En promedio, el resultado se desvía {fmt(e.get('valor'))} {u} del valor de referencia"
        if r.get("ic") and r["ic"][0] is not None:
            txt += f" (con 95 % de confianza, entre {fmt(r['ic'][0])} y {fmt(r['ic'][1])} {u})"
        txt += ". "
        if "Wilcoxon" in tec:
            txt += "Como los datos no tienen forma de campana, se usó una prueba basada en rangos (Wilcoxon). "
        if di.startswith("Se rechaza"):
            txt += "La desviación es estadísticamente distinta de cero."
        elif di.startswith("No se rechaza"):
            txt += "No se detecta una desviación distinta de cero (eso no prueba que no exista)."
        return txt
    if tec.startswith("Repetibilidad"):
        return f"Al repetir en las mismas condiciones, los resultados varían típicamente ± {fmt(e.get('valor'))} {u} (desviación estándar)."
    if tec.startswith("Precisión intermedia"):
        return (f"Cuando cambian técnico, día o patrón, la variación típica es ± {fmt(e.get('valor'))} {u}; "
                f"de ella, ± {fmt(e.get('s_entre'))} {u} se debe al cambio de condiciones.")
    if tec.startswith("Reproducibilidad"):
        return f"Entre laboratorios, la variación típica es ± {fmt(e.get('valor'))} {u}."
    return r.get("texto", "")


def explicar(r: dict) -> dict:
    estado_txt, icono, color = ESTADO.get(r["estado"], (r["estado"], "•", "gray"))
    salida = {"estado": estado_txt, "icono": icono, "color": color, "que_hace": que_hace(r["tecnica"]),
              "explicacion": "", "que_hacer": "", "decision": "", "decision_icono": "", "decision_color": ""}
    if r["estado"] == "APLICABLE":
        salida["explicacion"] = _resultado(r)
        if r.get("decision_metrologica"):
            d = DECISION.get(r["decision_metrologica"])
            if d:
                salida.update(decision=d[0], decision_icono=d[1], decision_color=d[2])
                salida["explicacion"] += " " + d[3]
    else:
        salida["explicacion"], salida["que_hacer"] = _por_que_no(r)
    return salida


def resumen_global(resultado: dict) -> dict:
    final = resultado["conclusion_final"]
    etiqueta, color = GLOBAL.get(final["estado"], (final["estado"], "gray"))
    return {"etiqueta": etiqueta, "color": color, "texto": final["texto"]}


def hallazgos(resultado: dict) -> list[str]:
    """Lo que encontró el análisis, en frases cortas para cualquier lector."""
    res = resultado["resultados"]
    u = resultado["objeto"]["unidad"]
    salida = []
    f = next((x for x in res if x["tecnica"].startswith("Faltantes")), None)
    if f:
        e = f["estimacion"]
        salida.append(f"Datos: llegaron {f['n']} de {e['esperadas']} resultados esperados ({fmt(e['valor'], 3)} % faltantes); "
                      "no se rellenó ni se borró ningún dato.")
    at = [x for x in res if x["etapa"] == "atipicos" and x["estado"] == "APLICABLE"]
    raros = [g for x in at for g in [t.get("laboratorio") or t.get("medicion_id") for t in x.get("tabla", [])
                                     if t.get("clasificacion") in ("rezagado (*)", "atípico (**)")]]
    if not at:
        motivo = next((explicar(x)["explicacion"] for x in res if x["etapa"] == "atipicos" and x["estado"] == "DATOS_INSUFICIENTES"), "")
        salida.append("Datos raros: no se pudo buscar. " + motivo.split(".")[0] + ".")
    elif raros:
        salida.append(f"Datos raros: se señalaron {len(raros)} para revisión ({', '.join(map(str, raros[:6]))}). Ninguno se borró.")
    else:
        salida.append("Datos raros: no se encontró ninguno.")
    no = [x for x in res if x["etapa"] == "normalidad" and x["decision_inferencial"] == "Se rechaza H0"]
    n_norm = sum(1 for x in res if x["etapa"] == "normalidad" and x["estado"] == "APLICABLE")
    if n_norm:
        salida.append("Forma de campana: " + (f"en {len(no)} de {n_norm} revisiones los datos no tienen forma de campana; "
                                               "allí se usaron métodos que no dependen de ella." if no else
                                               "no hay evidencia en contra en ninguna revisión."))
    nombres = {"sesgo": "Sesgo (desvío promedio)", "repetibilidad": "Repetibilidad", "precision_intermedia": "Precisión intermedia",
               "reproducibilidad": "Reproducibilidad"}
    for car in ("sesgo", "repetibilidad", "precision_intermedia", "reproducibilidad"):
        xs = [x for x in res if x["etapa"] == "desempeno" and x["caracteristica"] == car and x["estado"] == "APLICABLE"]
        if not xs:
            continue
        vals = [x["estimacion"]["valor"] for x in xs]
        decs = {}
        for x in xs:
            d = DECISION.get(x.get("decision_metrologica"), ("—",))[0]
            decs[d] = decs.get(d, 0) + 1
        rango = fmt(vals[0]) if len(vals) == 1 else f"entre {fmt(min(vals))} y {fmt(max(vals))}"
        salida.append(f"{nombres[car]}: {rango} {u} en {len(xs)} punto(s) → " + ", ".join(f"{k} en {v}" for k, v in decs.items()) + ".")
    return salida


def corto(r: dict) -> str:
    """Significado en pocas palabras de un resultado aplicado (para tablas)."""
    di = r.get("decision_inferencial") or ""
    if r["etapa"] == "normalidad":
        return "No tiene forma de campana" if di == "Se rechaza H0" else "Compatible con campana"
    if r["etapa"] == "atipicos":
        raros = [t for t in r.get("tabla", []) if t.get("clasificacion") in ("rezagado (*)", "atípico (**)")]
        return f"{len(raros)} dato(s) para revisar" if raros else "Sin datos raros"
    if r["tecnica"].startswith("Sesgo"):
        if di.startswith("Se rechaza"):
            return "Desvío distinto de cero"
        if di.startswith("No se rechaza"):
            return "No se detecta desvío"
        return "Solo estimación"
    if r["tecnica"].startswith("Precisión intermedia"):
        return "El cambio de condiciones influye" if di.startswith("Se rechaza") else "No se detecta efecto de las condiciones"
    return ""


def en_palabras(texto: str) -> str:
    """Reemplaza los códigos de estado por palabras en textos ya generados."""
    for a, b in (("CALCULADO_SIN_EVALUACION", "sin criterio"), ("NO_CONFORME", "no cumple"), ("INDETERMINADO", "no se puede decidir"),
                 ("CONFORME", "cumple"), ("NO_APLICABLE", "no corresponde"), ("DATOS_INSUFICIENTES", "faltan datos"),
                 ("NO_IMPLEMENTADO", "no disponible")):
        texto = texto.replace(a, b)
    return texto
