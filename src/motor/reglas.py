"""Matriz de reglas del motor (RM-xx).

Cada decisión del árbol cita una regla. El origen separa lo que exige la norma
(NORMA), lo que es buena práctica estadística no exigida por la norma
(COMPLEMENTARIA) y lo que decide el laboratorio (CRITERIO_LAB).
"""

from __future__ import annotations

from src.motor.resultado import COMPLEMENTARIA, CRITERIO_LAB, NORMA

REGLAS = {
    "RM-01": ("Los datos originales no se modifican; el motor trabaja sobre una copia del conjunto preparado.", NORMA, "ISO/IEC 17025:2017 §7.5 y §7.11"),
    "RM-02": ("No se imputan faltantes ni se reemplazan por cero; cada técnica comprueba su propia suficiencia.", COMPLEMENTARIA, "Especificación §6"),
    "RM-03": ("El porcentaje de faltantes solo genera alerta si el laboratorio fija un umbral; no hay umbral universal.", CRITERIO_LAB, "Especificación §6"),
    "RM-04": ("Las pruebas de Cochran y Mandel y la estimación de s_R solo se aplican a estudios interlaboratorio.", NORMA, "ISO 5725-2:1994 §7.3 y §7.4"),
    "RM-05": ("Los técnicos u otras condiciones internas no se tratan como laboratorios.", NORMA, "ISO 5725-1:1994 §3.18–3.20"),
    "RM-06": ("Las tablas de valores críticos solo se aplican si la edición configurada es la implementada.", NORMA, "ISO 5725-2:1994"),
    "RM-07": ("Cochran exige al menos dos celdas con réplicas; si n_ij difiere se usa el n mayoritario y se deja constancia.", NORMA, "ISO 5725-2:1994 §7.3.3"),
    "RM-08": ("Grubbs (procedimiento de la norma) se aplica a medias de celda de un nivel con p ≥ 3; doble con p ≥ 4.", NORMA, "ISO 5725-2:1994 §7.3.4"),
    "RM-09": ("Grubbs intralaboratorio solo sobre réplicas de una misma celda con n ≥ 3; nunca sobre la mezcla de puntos o condiciones.", COMPLEMENTARIA, "Grubbs (1969)"),
    "RM-10": ("Ningún dato se excluye por resultado estadístico sin motivo técnico, responsable, versión derivada y recálculo.", NORMA, "ISO 5725-2:1994 §7.3.2; Especificación §8"),
    "RM-11": ("El objeto de la prueba de normalidad depende del procedimiento: unidades del sesgo o residuos dentro de celda.", COMPLEMENTARIA, "Montgomery (2017)"),
    "RM-12": ("Un valor p ≥ α se redacta como «no se rechaza H0», nunca como «se confirma».", COMPLEMENTARIA, "Especificación §11"),
    "RM-13": ("Sesgo: prueba t si no se rechaza normalidad y n ≥ 3; Wilcoxon si se rechaza (supuesto de simetría a revisar); solo estimación si n < 3.", COMPLEMENTARIA, "Eurachem (2016) §6.5"),
    "RM-14": ("Repetibilidad: varianzas intracelda agrupadas por grados de libertad.", NORMA, "ISO 5725-2:1994 ec. 20; Eurachem (2016) §6.6"),
    "RM-15": ("Precisión intermedia: ANOVA de un factor de efectos aleatorios; varianza entre grupos negativa se toma como 0.", COMPLEMENTARIA, "Eurachem (2016) §6.6.4 y anexo C"),
    "RM-16": ("Reproducibilidad: s_R² = s_L² + s_r²; s_L² negativo se toma como 0.", NORMA, "ISO 5725-2:1994 ec. 21–24 y §7.4.5.4"),
    "RM-17": ("Sin criterio aprobado, límite numérico y regla de decisión, el resultado queda CALCULADO_SIN_EVALUACION.", NORMA, "ISO/IEC 17025:2017 §7.1.3 y §7.8.6"),
    "RM-18": ("La no significación estadística no demuestra equivalencia ni conformidad.", COMPLEMENTARIA, "Especificación §9"),
    "RM-19": ("No se convierten unidades: un criterio con unidad distinta no se evalúa.", CRITERIO_LAB, "Especificación §3"),
    "RM-20": ("Decisión inferencial, estimación y decisión metrológica se informan por separado.", COMPLEMENTARIA, "Especificación §9"),
    "RM-21": ("Ruta verificación/validación según el estado del método: validado y sin modificaciones → verificación.", NORMA, "Eurachem (2016) §4.2; ISO/IEC 17025:2017 §7.2.1.5 y §7.2.2"),
    "RM-22": ("Dixon no se implementa: no se dispone de tablas críticas verificadas.", COMPLEMENTARIA, "Dixon (1950)"),
}


def regla(codigo: str) -> dict:
    d, o, r = REGLAS[codigo]
    return {"codigo": codigo, "descripcion": d, "origen": o, "referencia": r}


def matriz() -> list[dict]:
    return [regla(c) for c in REGLAS]
