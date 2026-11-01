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
    "CONFORME_CON_OBSERVACIONES": ("Cumple con observaciones", "🟢", "green", "Cumple, con observaciones técnicas."),
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
    ("Réplicas por serie", "Revisa que cada serie (punto + técnico + patrón) tenga exactamente las lecturas planificadas."),
    ("Estructura", "Revisa cómo quedaron agrupados los datos: puntos, grupos de condiciones y repeticiones por grupo."),
    ("Exclusiones", "Lista los datos que una persona decidió dejar por fuera, con su motivo."),
    ("Mandel h", "Compara el promedio de cada laboratorio con el de los demás para ver si alguno se aleja."),
    ("Mandel k", "Compara la dispersión de cada laboratorio con la de los demás."),
    ("Mandel", "Compara laboratorios entre sí (promedios y dispersión)."),
    ("Cochran", "Busca si algún laboratorio tiene una dispersión mucho mayor que los demás."),
    ("Grubbs (réplicas)", "Busca un dato raro dentro de las repeticiones hechas en las mismas condiciones."),
    ("Grubbs", "Busca un laboratorio cuyo promedio sea raro frente a los demás."),
    ("Dixon", "Otra forma de buscar datos raros en grupos pequeños."),
    ("Homocedasticidad", "Solo si los datos son normales: revisa si las series tienen dispersiones parecidas (Bartlett) para elegir entre ANOVA clásico y ANOVA de Welch."),
    ("Shapiro", "Revisa si los datos tienen la forma de campana (distribución normal) que suponen varias pruebas."),
    ("Anderson", "Revisa si los datos tienen forma de campana, poniendo atención a los extremos."),
    ("Lilliefors", "Revisa si los datos tienen forma de campana."),
    ("Fuentes de variación", "Compara técnicos, patrones (y su combinación) para ver si el resultado depende de quién mide o con qué patrón."),
    ("Sesgo", "Mide cuánto se desvía, en promedio, el resultado respecto al valor de referencia."),
    ("Repetibilidad", "Mide cuánto varían los resultados al repetir la medición en las mismas condiciones."),
    ("Reproducibilidad intralaboratorio", "Mide cuánto varían los resultados dentro del laboratorio cuando cambian las condiciones (técnico, patrón, día). También se llama precisión intermedia."),
    ("Reproducibilidad interlaboratorio", "Mide cuánto varían los resultados entre laboratorios distintos."),
    ("Reproducibilidad", "Mide cuánto varían los resultados entre laboratorios distintos."),
    ("Suficiencia", "Revisa que haya datos para analizar."),
]


def que_hace(tecnica: str) -> str:
    return next((t for p, t in QUE_HACE if tecnica.startswith(p)), "")


def _por_que_no(r: dict) -> tuple[str, str]:
    """Explicación sencilla de por qué no se aplicó y qué haría falta."""
    m = " ".join(r.get("motivos") or [])
    tec = r["tecnica"]
    if "entre laboratorios necesita" in m:
        return ("La reproducibilidad entre laboratorios necesita varios laboratorios. La de tu laboratorio (cambiando técnico, "
                "patrón o día) sí se midió: mira «Reproducibilidad intralaboratorio».", "Nada: ya está evaluada dentro del laboratorio.")
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
    if tec.startswith("Réplicas por serie"):
        return r.get("texto", "")
    if tec.startswith("Estructura"):
        return f"Los datos se analizan en {e.get('valor')} punto(s) de medición."
    if tec.startswith("Exclusiones"):
        return f"Se dejaron por fuera {r['n']} dato(s) por decisión técnica documentada; el dato original se conserva."
    if r["etapa"] == "homocedasticidad":
        e2 = r.get("estimacion") or {}
        if "informativa" in r["tecnica"]:
            return (f"Los datos no son normales, así que no se usa ANOVA: la comparación va directo a Kruskal-Wallis. "
                    f"Como información, Fligner-Killeen da p = {fmt_p(r.get('p_valor'))}"
                    + (" (hay series más dispersas que otras)." if di == "Se rechaza H0" else " (dispersiones parecidas)."))
        if di == "Se rechaza H0":
            return (f"Las series NO tienen dispersiones parecidas (Bartlett, p = {fmt_p(r.get('p_valor'))}): la más dispersa es "
                    f"{e2.get('serie_max')} (s = {fmt(e2.get('s_max'))}). Por eso se compara con ANOVA de Welch.")
        return (f"Las series tienen dispersiones parecidas (Bartlett, p = {fmt_p(r.get('p_valor'))}); se compara con ANOVA clásico.")
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
    if tec.startswith("Fuentes de variación"):
        filas = [f for f in e.get("anova", []) if f.get("tipo") != "residual"]
        partes = []
        for f in filas:
            pct = (f" (explica {fmt(f['contribucion_pct'], 2)} % de la variación)" if f.get("contribucion_pct") is not None
                   else f" (tamaño del efecto ε² = {fmt(f['epsilon2'], 2)})" if f.get("epsilon2") is not None else "")
            partes.append(f"{f['fuente']}: {'SÍ influye' if f['influye'] else 'no se detecta influencia'}, p = {fmt_p(f['p'])}{pct}")
        return "; ".join(partes) + "." if partes else r.get("texto", "")
    if tec.startswith("Repetibilidad"):
        return f"Al repetir en las mismas condiciones, los resultados varían típicamente ± {fmt(e.get('valor'))} {u} (desviación estándar)."
    if tec.startswith("Reproducibilidad intralaboratorio"):
        return (f"Cuando cambian técnico, día o patrón, la variación típica es ± {fmt(e.get('valor'))} {u}; "
                f"de ella, ± {fmt(e.get('s_entre'))} {u} se debe al cambio de condiciones."
                + ("" if e.get("con_prueba_F", True) else " (Sin prueba F porque los supuestos no se cumplen; la influencia de cada condición "
                                                          "se evalúa en «Fuentes de variación».)"))
    if tec.startswith("Reproducibilidad interlaboratorio"):
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
    fv = [x for x in res if x.get("caracteristica") == "fuentes_variacion" and x["estado"] == "APLICABLE"]
    if fv:
        cuenta = {}
        for x in fv:
            for f in x["estimacion"].get("influyen", []):
                cuenta[f] = cuenta.get(f, 0) + 1
        salida.append("¿Depende de quién mide o del patrón? " + ("; ".join(f"{k}: influye en {v} de {len(fv)} punto(s)" for k, v in cuenta.items())
                                                              if cuenta else f"no: ninguna fuente fue significativa en los {len(fv)} punto(s)") + ".")
    nombres = {"sesgo": "Sesgo (desvío promedio)", "repetibilidad": "Repetibilidad", "precision_intermedia": "Reproducibilidad intralaboratorio",
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
    if r["etapa"] == "homocedasticidad":
        if "informativa" in r["tecnica"]:
            return "No decide (datos no normales)"
        return "Varianzas distintas → Welch" if di == "Se rechaza H0" else "Varianzas similares → ANOVA"
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
    if r["tecnica"].startswith("Fuentes de variación"):
        inf = (r.get("estimacion") or {}).get("influyen") or []
        return ("Influye: " + ", ".join(inf)) if inf else "Ninguna fuente influye"
    if r["tecnica"].startswith("Reproducibilidad intralaboratorio"):
        return "El cambio de condiciones influye" if di.startswith("Se rechaza") else "No se detecta efecto de las condiciones"
    return ""


def en_palabras(texto: str) -> str:
    """Reemplaza los códigos de estado por palabras en textos ya generados."""
    for a, b in (("CALCULADO_SIN_EVALUACION", "sin criterio"), ("NO_CONFORME", "no cumple"), ("INDETERMINADO", "no se puede decidir"),
                 ("CONFORME", "cumple"), ("NO_APLICABLE", "no corresponde"), ("DATOS_INSUFICIENTES", "faltan datos"),
                 ("NO_IMPLEMENTADO", "no disponible")):
        texto = texto.replace(a, b)
    return texto
