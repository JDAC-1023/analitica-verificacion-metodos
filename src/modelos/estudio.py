"""Modelo de datos de la configuración de un estudio.

Cada clase corresponde a un grupo de campos de la matriz de parametrización
(v0.2). El código de campo de la matriz se indica en el comentario de cada
atributo para conservar la trazabilidad matriz -> código.

Principios:
- Datos experimentales (D12-D14) y resultados de interés (V01-V10) son
  entidades distintas.
- No existe una columna global llamada «resultado».
- No se fijan fórmulas, criterios ni umbrales por defecto.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any

# --------------------------------------------------------------------------
# Catálogos cerrados (dominios). Se mantienen aquí para que la interfaz,
# la plantilla y la validación usen exactamente los mismos valores.
# --------------------------------------------------------------------------
TIPOS_ESTUDIO = ["Verificación", "Validación"]                       # E03
TIPOS_DATO = ["decimal", "entero", "texto", "fecha", "si_no"]        # D12/D13
CATEGORIAS_VARIABLE = ["lectura", "dato_del_metodo", "ambiental"]    # D12/D13/D14
TIPOS_VALOR_FACTOR = ["categorico", "numerico"]                      # D04
VINCULOS_RECURSO = ["ninguno", "tecnico", "patron", "equipo"]        # D03 + R01/R02/R04
ROLES_FACTOR = ["se_compara", "solo_se_registra"]                    # D15
ORIGENES_RESULTADO = ["directo", "calculado"]                        # V04
AMBITOS_RESULTADO = ["medicion", "serie", "punto", "condicion", "estudio", "otro"]  # V07
PROPOSITOS_RESULTADO = ["exigido_por_el_metodo", "objetivo_del_estudio"]          # V02
ESTADOS_DISENO = ["borrador", "aprobado"]                            # P05


def _desde_dict(clase, datos: dict[str, Any]):
    """Construye una dataclass ignorando claves desconocidas.

    Permite leer estudios guardados con versiones anteriores del modelo.
    """
    nombres = {f.name for f in fields(clase)}
    return clase(**{k: v for k, v in (datos or {}).items() if k in nombres})


@dataclass
class Magnitud:  # E09, E10
    id: str                      # MAG-01, generado
    nombre: str                  # E09
    unidad: str                  # E09
    intervalo_min: float | None = None   # E10
    intervalo_max: float | None = None   # E10


@dataclass
class Punto:  # E11
    id: str                      # PT-01, generado
    magnitud_id: str
    valor_nominal: float
    unidad: str


@dataclass
class Recurso:  # R01, R02, R03, R04 y equipo a evaluar (IBC)
    codigo: str                  # T-01, P-01, EQ-01, IBC-01 (lo escribe el usuario)
    nombre: str = ""
    tipo: str = "tecnico"        # tecnico | patron | equipo | ibc
    magnitud_id: str = ""        # R03 (patrones e IBC)
    intervalo_min: float | None = None  # R03 intervalo útil del patrón / intervalo del IBC
    intervalo_max: float | None = None
    descripcion: str = ""
    marca: str = ""              # patrón / IBC
    modelo: str = ""             # patrón / IBC
    serie: str = ""              # patrón / IBC
    resolucion: str = ""         # IBC (texto: se registra tal como figura en el equipo)
    certificado: str = ""        # patrón: certificado de calibración vigente


@dataclass
class Factor:  # D03, D04, D15
    id: str                      # F-01, generado
    nombre: str                  # D03
    descripcion: str = ""
    tipo_valor: str = "categorico"     # D04
    unidad: str = ""
    niveles: list[str] = field(default_factory=list)   # D04
    vinculo_recurso: str = "ninguno"   # si el factor es técnico/patrón/equipo, sus niveles vienen del catálogo
    rol: str = "se_compara"            # D15: se cambia para comparar o solo se registra


@dataclass
class Variable:  # D12, D13, D14
    id: str                      # V-01, generado (clave técnica estable)
    nombre: str
    tipo_dato: str = "decimal"
    unidad: str = ""
    obligatoria: bool = True
    descripcion: str = ""
    categoria: str = "lectura"


@dataclass
class ResultadoInteres:  # V01 - V10
    id: str                      # V10: R-01, generado
    nombre: str                  # V01
    proposito: str = "exigido_por_el_metodo"   # V02
    referencia_proposito: str = ""             # V02
    unidad: str = ""                           # V03 ("" = no aplica)
    origen: str = "calculado"                  # V04
    dependencias: list[str] = field(default_factory=list)   # V05: ids de variables u otros resultados
    referencia_calculo: str = ""               # V06: referencia/versión del procedimiento (no fórmula)
    ambito: str = "medicion"                   # V07
    analizar: bool = False                     # V08
    tiene_criterio: bool = False               # V09


@dataclass
class Criterio:  # C01, C02, C03
    id: str                      # C-01, generado
    resultado_id: str            # C01
    descripcion: str = ""        # C01
    fuente: str = ""             # C02
    version_fuente: str = ""     # C02
    operador: str = ""           # C03 (libre; no se impone)
    valor: str = ""              # C03 (texto: no se interpreta en esta fase)
    unidad: str = ""             # C03
    condiciones: str = ""        # C03
    aprobado: bool = False       # se aprueba antes de analizar


@dataclass
class Restriccion:  # D11
    campo_a: str                 # p. ej. "patron" o "F-02"
    valor_a: str
    campo_b: str
    valor_b: str
    motivo: str = ""


@dataclass
class MedicionPlanificada:  # D09, D07, P02, P03, P04, D10
    medicion_id: str             # M0001, generado
    punto_id: str
    repeticion: int
    niveles: dict[str, str] = field(default_factory=dict)   # factor_id -> nivel (solo factores sin vínculo a recurso)
    tecnico: str = ""            # P02
    patron: str = ""             # P03
    equipo: str = ""             # R04
    fecha_planificada: str = ""  # P04 / D16 (ISO yyyy-mm-dd)
    franja_planificada: str = "" # P04
    orden: int | None = None     # D10


@dataclass
class Estudio:
    # 1 · Estudio
    codigo: str                          # E02 (automático)
    nombre: str                          # E01
    tipo: str = "Verificación"           # E03
    metodo: str = ""                     # E04
    version_metodo: str = ""             # E05
    uso_previsto: str = ""               # E06
    documento_referencia: str = ""       # E07
    responsable: str = ""                # E08
    # 2 · Alcance
    magnitudes: list[Magnitud] = field(default_factory=list)   # E09, E10
    puntos: list[Punto] = field(default_factory=list)          # E11
    # 3 · Recursos
    tecnicos: list[Recurso] = field(default_factory=list)      # R01
    patrones: list[Recurso] = field(default_factory=list)      # R02, R03
    equipos: list[Recurso] = field(default_factory=list)       # R04
    ibcs: list[Recurso] = field(default_factory=list)          # Equipo a evaluar (IBC); agregado a solicitud del equipo
    # 4 · Diseño
    factores: list[Factor] = field(default_factory=list)       # D03, D04, D15
    condiciones_controladas: str = ""    # D05
    agrupacion: list[str] = field(default_factory=lambda: ["punto"])  # D06: claves que forman grupos comparables
    repeticiones_por_condicion: int = 2  # D07 (valor por defecto del planificador, editable por fila)
    unidad_experimental: str = ""        # D08 (pendiente técnico)
    restricciones: list[Restriccion] = field(default_factory=list)   # D11
    variables: list[Variable] = field(default_factory=list)          # D12-D14
    # 5 · Resultados de interés y 6 · Evaluación
    resultados: list[ResultadoInteres] = field(default_factory=list)   # V01-V10
    criterios: list[Criterio] = field(default_factory=list)            # C01-C03
    # 7 · Cronograma
    periodo_inicio: str = ""             # P01
    periodo_fin: str = ""                # P01
    plan: list[MedicionPlanificada] = field(default_factory=list)      # D09, D10, P02-P04
    # Control de versiones del diseño (P05)
    version_diseno: int = 0              # P05 · 0 = nunca aprobado
    estado: str = "borrador"             # P05 · borrador | aprobado
    aprobado_por: str = ""               # P05
    fecha_aprobacion: str = ""           # P05
    creado_en: str = ""
    actualizado_en: str = ""
    paso_asistente: int = 1              # último paso abierto del asistente de creación (no forma parte del diseño)

    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, datos: dict[str, Any]) -> "Estudio":
        base = _desde_dict(cls, datos)
        base.magnitudes = [_desde_dict(Magnitud, x) for x in datos.get("magnitudes", [])]
        base.puntos = [_desde_dict(Punto, x) for x in datos.get("puntos", [])]
        base.tecnicos = [_desde_dict(Recurso, x) for x in datos.get("tecnicos", [])]
        base.patrones = [_desde_dict(Recurso, x) for x in datos.get("patrones", [])]
        base.equipos = [_desde_dict(Recurso, x) for x in datos.get("equipos", [])]
        base.ibcs = [_desde_dict(Recurso, x) for x in datos.get("ibcs", [])]
        base.factores = [_desde_dict(Factor, x) for x in datos.get("factores", [])]
        base.restricciones = [_desde_dict(Restriccion, x) for x in datos.get("restricciones", [])]
        base.variables = [_desde_dict(Variable, x) for x in datos.get("variables", [])]
        base.resultados = [_desde_dict(ResultadoInteres, x) for x in datos.get("resultados", [])]
        base.criterios = [_desde_dict(Criterio, x) for x in datos.get("criterios", [])]
        base.plan = [_desde_dict(MedicionPlanificada, x) for x in datos.get("plan", [])]
        return base

    # ------------------------------------------------------------------
    # Búsquedas de apoyo
    # ------------------------------------------------------------------
    def magnitud(self, magnitud_id: str) -> Magnitud | None:
        return next((m for m in self.magnitudes if m.id == magnitud_id), None)

    def punto(self, punto_id: str) -> Punto | None:
        return next((p for p in self.puntos if p.id == punto_id), None)

    def factores_libres(self) -> list[Factor]:
        """Factores cuyos niveles no provienen de un catálogo de recursos."""
        return [f for f in self.factores if f.vinculo_recurso == "ninguno"]

    def resultados_directos_por_medicion(self) -> list[ResultadoInteres]:
        return [r for r in self.resultados if r.origen == "directo" and r.ambito == "medicion"]

    def resultados_directos_agrupados(self) -> list[ResultadoInteres]:
        return [r for r in self.resultados if r.origen == "directo" and r.ambito != "medicion"]


def siguiente_id(prefijo: str, existentes: list[str], ancho: int = 2) -> str:
    """Genera el siguiente identificador libre: MAG-01, MAG-02..."""
    numeros = []
    for valor in existentes:
        if valor.startswith(prefijo + "-"):
            try:
                numeros.append(int(valor.split("-")[-1]))
            except ValueError:
                pass
    return f"{prefijo}-{(max(numeros) + 1 if numeros else 1):0{ancho}d}"
