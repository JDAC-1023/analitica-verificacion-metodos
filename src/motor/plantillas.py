"""Plantillas de texto de la memoria de cálculo (§11 de la especificación).

Los textos se rellenan solo con valores calculados. Nunca afirman normalidad,
igualdad ni conformidad a partir de un valor p.
"""

from __future__ import annotations


def fmt(x, cifras: int = 4) -> str:
    if x is None:
        return "—"
    if isinstance(x, (int,)) and not isinstance(x, bool):
        return str(x)
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if v == 0:
        return "0"
    return f"{v:.{cifras}g}".replace(".", ",")


def fmt_p(p) -> str:
    if p is None:
        return "—"
    return "< 0,0001" if p < 0.0001 else fmt(p, 3)


ATIPICOS = ("Se aplicó {prueba} a {n} observaciones de {variable} en {agrupacion}, con referencia {referencia}. "
            "Se verificaron {supuestos}. El estadístico {simbolo}={valor} se comparó con {critico_o_p}. "
            "El resultado se clasificó como {clasificacion}. Tratamiento: {accion}, autorizado por {responsable}. "
            "El dato original permanece conservado.")

NORMALIDAD = ("Se examinó {objeto} mediante {prueba}, seleccionada por {razon}. H0: {H0}. H1: {H1}. "
              "Para α={alfa} se obtuvo {estadistico}, p={p}. Se {decision} H0. Diagnóstico gráfico: {grafico}. "
              "Esta conclusión no prueba normalidad ni suficiencia metrológica.")

SESGO = ("La estimación de sesgo de {variable} frente a {referencia} fue {sesgo} {unidad}; incertidumbre de referencia {u_ref}. "
         "Se contrastó {H0} frente a {H1} mediante {prueba}; resultado {estadistico}, gl={gl}, p={p}, IC={ic}. "
         "La evaluación respecto a {criterio} tiene estado {estado_metrologico}.")

PRECISION = ("Se estimó {tipo_precision} para {variable}, nivel {nivel}, con {n} resultados y condiciones {condiciones}. "
             "Se obtuvo {estimacion} {unidad}, IC={ic}, grados de libertad {gl}. El procedimiento fue {procedimiento}; "
             "evaluación respecto a {criterio}: {decision}.")


def render(plantilla: str, **valores) -> str:
    return plantilla.format(**{k: ("—" if v is None or v == "" else v) for k, v in valores.items()})


def ic_txt(ic, unidad: str = "") -> str:
    if not ic or ic[0] is None:
        return "no calculado"
    return f"[{fmt(ic[0])}; {fmt(ic[1])}]" + (f" {unidad}" if unidad else "")
