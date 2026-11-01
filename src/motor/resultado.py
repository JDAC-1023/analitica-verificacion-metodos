"""Memoria de cálculo: estructuras serializables que devuelve cada módulo del motor (§10)."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any

# Estados de aplicabilidad / ejecución
APLICABLE = "APLICABLE"
NO_APLICABLE = "NO_APLICABLE"
PENDIENTE_MODELO = "PENDIENTE_MODELO"
NO_IMPLEMENTADO = "NO_IMPLEMENTADO"
DATOS_INSUFICIENTES = "DATOS_INSUFICIENTES"

# Estados metrológicos
CONFORME = "CONFORME"
NO_CONFORME = "NO_CONFORME"
INDETERMINADO = "INDETERMINADO"
SIN_EVALUACION = "CALCULADO_SIN_EVALUACION"

# Origen de la regla
NORMA = "NORMA"
COMPLEMENTARIA = "COMPLEMENTARIA"
CRITERIO_LAB = "CRITERIO_LAB"


def limpio(v: Any) -> Any:
    """Convierte NaN/inf y tipos NumPy en valores JSON."""
    if isinstance(v, dict):
        return {k: limpio(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [limpio(x) for x in v]
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@dataclass
class NodoDecision:
    """Un paso del árbol de decisiones: pregunta, respuesta y evidencia."""
    pregunta: str
    respuesta: str            # SI | NO | APLICABLE | NO_APLICABLE
    evidencia: str = ""
    regla: str = ""           # código de la regla (RM-xx)


@dataclass
class ResultadoAnalisis:
    analysis_id: str
    etapa: str                # limpieza | atipicos | normalidad | desempeno
    tecnica: str
    study_id: str
    version: int
    variable_id: str
    unidad: str
    agrupacion: str           # p. ej. "punto=PT-01"
    estado: str               # APLICABLE / NO_APLICABLE / …
    motivos: list[str] = field(default_factory=list)
    n: int = 0
    incluidas: list[str] = field(default_factory=list)
    excluidas: list[str] = field(default_factory=list)
    algoritmo: str = ""
    referencia: str = ""
    origen_regla: str = ""
    supuestos: list[dict] = field(default_factory=list)     # {supuesto, verificado, evidencia}
    hipotesis: dict = field(default_factory=dict)           # {H0, H1, lateralidad, alfa}
    formula: str = ""
    estadistico: dict = field(default_factory=dict)         # {simbolo, valor}
    gl: Any = None
    p_valor: float | None = None
    criticos: dict = field(default_factory=dict)
    ic: list | None = None
    estimacion: dict = field(default_factory=dict)          # {nombre, valor, unidad}
    decision_inferencial: str = ""
    requisito: dict = field(default_factory=dict)           # criterio aplicado y fuente
    decision_metrologica: str = ""
    tabla: list[dict] = field(default_factory=list)         # cálculos intermedios
    graficos: list[str] = field(default_factory=list)       # claves de gráficos
    limitaciones: list[str] = field(default_factory=list)
    texto: str = ""                                         # plantilla renderizada
    arbol: list[NodoDecision] = field(default_factory=list)
    caracteristica: str = ""                                # sesgo | repetibilidad | … (solo desempeño)
    punto_id: str = ""

    def to_dict(self) -> dict:
        return limpio(asdict(self))
