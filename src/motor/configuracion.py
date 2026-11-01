"""Contrato de entrada del motor: configuración del análisis.

La matriz de parametrización v0.2 no contiene varios datos que el motor
necesita para decidir sin inventar requisitos metrológicos. Este contrato los
pide de forma explícita; los vacíos quedan como PENDIENTE y el motor no
emite conformidad con información faltante (ver docs/11_motor_contrato.md).

Campos que la matriz no define y este contrato agrega:
  - características de desempeño exigidas y su estado (REQUERIDA, SELECCIONADA…)
  - objeto del análisis y, si es un resultado calculado, la regla aprobada
  - estructura del diseño: si es interlaboratorio (ISO 5725-2) y qué factor es
    «laboratorio»; factores de precisión intermedia
  - valor de referencia por punto y su incertidumbre estándar (para sesgo)
  - criterios estructurados: parámetro, operador, límite, regla de decisión,
    fuente y aprobación
  - α configurable, prueba de normalidad, edición normativa
  - exclusiones con motivo y responsable; revisor y autorizador
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

ESTADOS_CARACTERISTICA = ["REQUERIDA", "SELECCIONADA", "NO_APLICABLE_JUSTIFICADA", "PENDIENTE"]
CARACTERISTICAS = {
    # código: (nombre, implementada en esta versión, referencia)
    "sesgo": ("Veracidad / sesgo", True, "Eurachem (2016) §6.5; ISO 5725-1:1994 §3.8"),
    "repetibilidad": ("Precisión en condiciones de repetibilidad", True, "Eurachem (2016) §6.6; ISO 5725-1:1994 §3.13"),
    "precision_intermedia": ("Reproducibilidad intralaboratorio (precisión intermedia)", True, "Eurachem (2016) §6.6.3–6.6.4 y anexo C; ISO 5725-3"),
    "reproducibilidad": ("Reproducibilidad interlaboratorio", True, "ISO 5725-2:1994 §7.4"),
    "linealidad": ("Linealidad / intervalo de trabajo", False, "Eurachem (2016) §6.3"),
    "lod_loq": ("Límites de detección y cuantificación", False, "Eurachem (2016) §6.2"),
    "selectividad": ("Selectividad", False, "Eurachem (2016) §6.1"),
    "robustez": ("Robustez", False, "Eurachem (2016) §6.8"),
    "incertidumbre": ("Incertidumbre de medida", False, "Eurachem (2016) §6.7"),
}
PARAMETROS = {
    "sesgo": ["sesgo", "abs_sesgo"],
    "repetibilidad": ["s_r"],
    "precision_intermedia": ["s_I"],
    "reproducibilidad": ["s_R"],
}
OPERADORES = ["<=", "<", ">=", ">"]
REGLAS_DECISION = {
    "estimacion": "Se compara la estimación puntual con el límite",
    "intervalo": "Conforme solo si todo el intervalo de confianza cumple el límite; indeterminado si lo cruza",
}
PRUEBAS_NORMALIDAD = ["shapiro_wilk", "anderson_darling", "lilliefors"]


def _desde(clase, datos):
    nombres = {f.name for f in fields(clase)}
    return clase(**{k: v for k, v in (datos or {}).items() if k in nombres})


@dataclass
class CaracteristicaConfig:
    codigo: str
    estado: str = "PENDIENTE"
    justificacion: str = ""
    fuente: str = ""


@dataclass
class ReferenciaNivel:
    punto_id: str
    valor: float | None = None
    incertidumbre: float | None = None   # incertidumbre estándar u_ref
    fuente: str = ""


@dataclass
class CriterioMotor:
    id: str
    caracteristica: str
    parametro: str
    operador: str = "<="
    limite: float | None = None
    unidad: str = ""
    regla_decision: str = ""             # vacío = sin regla documentada → sin evaluación
    fuente: str = ""
    aprobado: bool = False
    puntos: list[str] = field(default_factory=list)   # vacío = todos los puntos
    criterio_estudio_id: str = ""        # vínculo opcional con C-xx de la matriz


@dataclass
class Exclusion:
    medicion_id: str
    motivo: str
    responsable: str
    fecha: str = ""
    origen: str = "revision_atipicos"


@dataclass
class ReglaDerivacion:
    """Regla aprobada para obtener el valor analizado a partir de datos registrados."""
    tipo: str = "diferencia"             # diferencia: a − b (la única implementada)
    a: str = ""                          # id de variable
    b: str = ""
    referencia: str = ""                 # documento/procedimiento que la aprueba
    aprobada: bool = False


@dataclass
class ConfiguracionAnalisis:
    codigo_estudio: str
    version: int = 1
    padre: int | None = None
    motivo_cambio: str = ""
    preparacion_id: str = ""
    # objeto del análisis
    objeto_tipo: str = "variable"        # variable | resultado_directo | derivado
    objeto_id: str = ""                  # V-xx o R-xx
    regla: ReglaDerivacion | None = None
    # contexto del método (ramificación verificación / validación)
    metodo_validado: str = ""            # "si" | "no" | "" (desconocido)
    modificaciones: str = ""
    documentacion_previa: str = ""
    caracteristicas: list[CaracteristicaConfig] = field(default_factory=list)
    # diseño
    es_interlaboratorio: bool = False
    factor_laboratorio: str = ""         # "tecnico" | "patron" | id de factor (solo si es interlaboratorio)
    factores_precision_intermedia: list[str] = field(default_factory=list)
    # sesgo
    referencia_tipo: str = "ninguna"     # ninguna | valor_por_nivel | objeto_es_diferencia
    referencias: list[ReferenciaNivel] = field(default_factory=list)
    # estadística
    alfa: float = 0.05
    nivel_confianza: float = 0.95
    prueba_normalidad: str = "shapiro_wilk"
    alerta_faltantes_pct: float | None = None   # alerta configurable; no es criterio de aplicabilidad
    version_normativa: str = "ISO 5725-2:1994"
    exclusiones: list[Exclusion] = field(default_factory=list)
    criterios: list[CriterioMotor] = field(default_factory=list)
    # control del informe
    elaborado_por: str = ""
    revisado_por: str = ""
    autorizado_por: str = ""
    creado_en: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ConfiguracionAnalisis":
        c = _desde(cls, d)
        c.regla = _desde(ReglaDerivacion, d["regla"]) if d.get("regla") else None
        c.caracteristicas = [_desde(CaracteristicaConfig, x) for x in d.get("caracteristicas", [])]
        c.referencias = [_desde(ReferenciaNivel, x) for x in d.get("referencias", [])]
        c.exclusiones = [_desde(Exclusion, x) for x in d.get("exclusiones", [])]
        c.criterios = [_desde(CriterioMotor, x) for x in d.get("criterios", [])]
        return c

    def caracteristica(self, codigo: str) -> CaracteristicaConfig | None:
        return next((c for c in self.caracteristicas if c.codigo == codigo), None)

    def activa(self, codigo: str) -> bool:
        c = self.caracteristica(codigo)
        return c is not None and c.estado in ("REQUERIDA", "SELECCIONADA")


def diferencias(anterior: ConfiguracionAnalisis, nueva: ConfiguracionAnalisis) -> list[dict]:
    """Cambios entre dos versiones de configuración (historial de cambios)."""
    a, b = anterior.to_dict(), nueva.to_dict()
    ignorar = {"version", "padre", "motivo_cambio", "creado_en"}
    return [{"campo": k, "antes": a.get(k), "despues": b.get(k)}
            for k in sorted(set(a) | set(b)) if k not in ignorar and a.get(k) != b.get(k)]
