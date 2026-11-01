"""Tablas de contexto analítico: qué se compara en cada momento (técnicos, patrones, cruces).

Se construyen desde el resultado guardado; las usan la interfaz y el informe.
"""

from __future__ import annotations

from src.motor.plantillas import fmt, fmt_p

SIGNIFICADO = [
    ("Sesgo (b)", "Diferencia entre el promedio de las mediciones y el valor de referencia (aquí, la corrección promedio frente a 0).",
     "Indica si el método da, en promedio, resultados corridos. Un sesgo grande obliga a corregir o a declararlo en la incertidumbre.",
     "Eurachem (2016) §6.5; ISO 5725-1 §3.8"),
    ("Repetibilidad (s_r)", "Dispersión entre lecturas repetidas con el mismo técnico, el mismo patrón y en el mismo momento.",
     "Es la mejor precisión que puede dar el método. Si es grande, el método no es estable ni en las condiciones más favorables.",
     "ISO 5725-1 §3.13; ISO 5725-2 ec. 20"),
    ("Reproducibilidad intralaboratorio (s_I, precisión intermedia)", "Dispersión total cuando cambian condiciones dentro del laboratorio (técnico, patrón, día).",
     "Refleja la variación real de la rutina. Si es mucho mayor que s_r, alguna condición (quién mide o con qué patrón) pesa.",
     "Eurachem (2016) §6.6.4"),
    ("Reproducibilidad interlaboratorio (s_R)", "Dispersión entre laboratorios distintos que aplican el mismo método.",
     "Solo existe en estudios interlaboratorio; dentro de un laboratorio se usa la reproducibilidad intralaboratorio.", "ISO 5725-2 §7.4"),
    ("Fuentes de variación (ANOVA)", "Comparación de los resultados entre técnicos, entre patrones y su combinación.",
     "Dice si el método es sensible a quién mide o al patrón usado. Una fuente que «influye» debe controlarse o incluirse en la incertidumbre.",
     "Montgomery (2017) cap. 5"),
    ("Exactitud (precisión + veracidad)", "Cercanía de un resultado individual al valor verdadero; combina sesgo y precisión.",
     "Un método adecuado necesita sesgo pequeño y dispersión pequeña a la vez.", "ISO 5725-1 §3.6; VIM 2.13"),
    ("Intervalo de confianza 95 %", "Rango en el que, con 95 % de confianza, está el valor verdadero del parámetro.",
     "Si todo el intervalo está dentro del límite, el cumplimiento es robusto; si lo cruza, la decisión es incierta.", "—"),
    ("Valor p", "Probabilidad de observar una diferencia así de grande si en realidad no la hubiera.",
     "p < 0,05: la diferencia es estadísticamente real. p ≥ 0,05: no se detecta (no prueba que no exista).", "—"),
]

QUE_SE_COMPARA = {
    "limpieza": [["Resultados", "Cuántos llegaron frente a los planificados", "El plan aprobado del estudio"],
                 ["Series", "Lecturas válidas de cada serie (punto × técnico × patrón)", "Las lecturas planificadas por serie"]],
    "atipicos": [["Cada lectura", "Su distancia al promedio de su serie", "Las demás lecturas de la misma serie (mismo punto, técnico y patrón)"],
                 ["Laboratorios", "Promedios y dispersiones entre laboratorios", "Solo en estudios interlaboratorio"]],
    "normalidad": [["Unidades del sesgo", "La forma de la distribución de los promedios de serie", "Una distribución normal (campana)"],
                   ["Residuos", "La forma de las diferencias de cada lectura a su promedio de serie", "Una distribución normal (campana)"]],
    "desempeno": [["Sesgo", "Promedio de la corrección en cada punto", "El valor de referencia (0) y el límite de aceptación"],
                  ["Repetibilidad", "Dispersión dentro de cada serie", "El límite de repetibilidad"],
                  ["Reproducibilidad intralaboratorio", "Dispersión total al cambiar técnico y patrón", "El límite de reproducibilidad intralaboratorio"],
                  ["Fuentes de variación", "Promedios entre técnicos, entre patrones y su combinación", "La variación entre réplicas (prueba F)"]],
}

def _fv(resultado: dict) -> list[dict]:
    return [r for r in resultado["resultados"] if r.get("caracteristica") == "fuentes_variacion" and r["estado"] == "APLICABLE"]


def _punto(r: dict) -> str:
    return r["agrupacion"].replace("nivel ", "").split(" · ")[0]


def resumen_fuentes(resultado: dict) -> tuple[list[str], list[list[str]]]:
    """Encabezados y filas: por punto, p y % de contribución de cada fuente, y conclusión."""
    rs = _fv(resultado)
    if not rs:
        return [], []
    fuentes = []
    for r in rs:
        for f in r["estimacion"]["anova"]:
            if f["tipo"] != "residual" and f["fuente"] not in fuentes:
                fuentes.append(f["fuente"])
    cab = ["Punto", "Prueba usada"] + fuentes + ["Repetibilidad (residual)", "Conclusión"]
    filas = []
    for r in rs:
        m = {f["fuente"]: f for f in r["estimacion"]["anova"]}
        fila = [_punto(r), r["estimacion"].get("ruta_nombre", "")]
        for fu in fuentes:
            f = m.get(fu)
            if not f:
                fila.append("—")
            elif f.get("epsilon2") is not None:
                fila.append(f"p = {fmt_p(f['p'])} · ε² = {fmt(f['epsilon2'], 2)}" + (" ✱" if f["influye"] else ""))
            else:
                fila.append(f"p = {fmt_p(f['p'])} · {fmt(f['contribucion_pct'], 2)} %" + (" ✱" if f["influye"] else ""))
        res = m.get("Residual (repetibilidad)")
        fila.append(f"{fmt(res['contribucion_pct'], 2)} %" if res else "—")
        inf = r["estimacion"]["influyen"]
        fila.append(("Influye: " + ", ".join(inf)) if inf else "Ninguna influye")
        filas.append(fila)
    return cab, filas


def medias_por_factor(resultado: dict) -> dict[str, tuple[list[str], list[list[str]]]]:
    """Por cada factor: filas = puntos, columnas = niveles del factor (media de la corrección)."""
    rs = _fv(resultado)
    salida: dict[str, tuple[list[str], list[list[str]]]] = {}
    if not rs:
        return salida
    nombres = list(rs[0]["estimacion"]["contexto"]["por_factor"].keys())
    for nombre in nombres:
        niveles = []
        for r in rs:
            for x in r["estimacion"]["contexto"]["por_factor"].get(nombre, []):
                if x["nivel"] not in niveles:
                    niveles.append(x["nivel"])
        filas = []
        for r in rs:
            m = {x["nivel"]: x for x in r["estimacion"]["contexto"]["por_factor"].get(nombre, [])}
            medias = [m[n]["media"] for n in niveles if n in m]
            filas.append([_punto(r)] + [f"{fmt(m[n]['media'])} (s {fmt(m[n]['s'], 2)})" if n in m else "—" for n in niveles]
                         + [fmt(max(medias) - min(medias), 3) if len(medias) > 1 else "—"])
        salida[nombre] = (["Punto"] + niveles + ["Diferencia máx."], filas)
    return salida


def cruce(resultado: dict, punto_id: str | None = None) -> tuple[str, list[str], list[list[str]]] | None:
    """Tabla cruzada (p. ej. técnico × patrón) de medias para un punto."""
    rs = [r for r in _fv(resultado) if punto_id is None or r.get("punto_id") == punto_id]
    if not rs or not rs[0]["estimacion"]["contexto"].get("cruce"):
        return None
    c = rs[0]["estimacion"]["contexto"]["cruce"]
    cab = [f"{c['filas']} \\ {c['columnas']}"] + c["niveles_columnas"]
    filas = [[d["nivel"]] + [fmt(d.get(n)) for n in c["niveles_columnas"]] for d in c["datos"]]
    return _punto(rs[0]), cab, filas
