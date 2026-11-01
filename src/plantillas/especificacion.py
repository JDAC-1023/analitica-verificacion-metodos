"""Especificación de columnas de la plantilla de captura.

La misma especificación la usan el generador (para escribir el Excel) y la
ingesta (para comprobar que el archivo cargado conserva su estructura). Así la
plantilla y la validación no pueden contradecirse.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.modelos.estudio import Estudio, ResultadoInteres
from src.planificacion.plan import condicion_de, etiqueta_punto, grupo_comparable

FORMATO_PLANTILLA = "PLT-1.0"
HOJA_INSTRUCCIONES = "Instrucciones"
HOJA_ESTUDIO = "Estudio"
HOJA_MEDICIONES = "Mediciones"
HOJA_RESULTADOS = "Resultados_directos"
HOJA_DEFINICIONES = "Definiciones"
HOJA_CONTROL = "_control"
HOJA_LISTAS = "_listas"

# Columnas de ejecución que completa el usuario (X03, X04, D16).
EJECUCION = [
    ("tecnico_real", "Técnico que midió", "texto", "Si es distinto del previsto, escribe el motivo del cambio."),
    ("patron_real", "Patrón usado", "texto", "Si es distinto del previsto, escribe el motivo del cambio."),
    ("fecha_real", "Fecha real", "fecha", "Fecha en que se hizo la medición."),
    ("hora_real", "Hora real", "texto", "Hora en formato HH:MM."),
    ("motivo_cambio", "Motivo del cambio", "texto", "Obligatorio si cambió el técnico o el patrón previsto."),
    ("observaciones", "Observaciones", "texto", "Incidencias o información relevante."),
]


@dataclass
class Columna:
    clave: str            # clave técnica estable (no cambia aunque cambie la etiqueta)
    etiqueta: str         # encabezado visible en Excel
    origen: str           # "sistema" (lo llena el sistema) | "usuario"
    tipo: str = "texto"   # decimal | entero | texto | fecha | si_no
    unidad: str = ""
    obligatoria: bool = False
    entidad: str = "medicion"     # medicion | variable | resultado | factor | ejecucion
    ref_id: str = ""              # id de variable, resultado o factor
    ayuda: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _etiqueta(nombre: str, unidad: str) -> str:
    return f"{nombre} [{unidad}]" if unidad else nombre


def columnas_mediciones(e: Estudio) -> list[Columna]:
    cols = [
        Columna("medicion_id", "ID medición", "sistema", obligatoria=True),
        Columna("punto_id", "Código del punto", "sistema"),
        Columna("magnitud", "Magnitud", "sistema"),
        Columna("valor_nominal", "Punto previsto", "sistema", tipo="decimal"),
        Columna("unidad_punto", "Unidad del punto", "sistema"),
        Columna("repeticion", "Repetición", "sistema", tipo="entero"),
    ]
    for f in e.factores_libres():
        if f.rol == "se_compara":
            cols.append(Columna(f"factor:{f.id}", _etiqueta(f.nombre, f.unidad), "sistema",
                                entidad="factor", ref_id=f.id))
    cols.append(Columna("tecnico", "Técnico previsto", "sistema"))
    cols.append(Columna("patron", "Patrón previsto", "sistema"))
    if e.equipos:
        cols.append(Columna("equipo", "Equipo previsto", "sistema"))
    cols += [
        Columna("fecha_planificada", "Fecha prevista", "sistema"),
        Columna("franja_planificada", "Franja prevista", "sistema"),
        Columna("orden", "Orden", "sistema", tipo="entero"),
    ]
    for v in e.variables:
        cols.append(Columna(f"var:{v.id}", _etiqueta(v.nombre, v.unidad), "usuario", tipo=v.tipo_dato,
                            unidad=v.unidad, obligatoria=v.obligatoria, entidad="variable", ref_id=v.id,
                            ayuda=v.descripcion))
    for f in e.factores_libres():
        if f.rol == "solo_se_registra":  # D15: se registra, no se compara
            cols.append(Columna(f"factor:{f.id}", _etiqueta(f.nombre, f.unidad), "usuario",
                                entidad="factor", ref_id=f.id, ayuda="Se registra como contexto; no se compara."))
    for r in e.resultados_directos_por_medicion():
        cols.append(Columna(f"res:{r.id}", _etiqueta(r.nombre, r.unidad), "usuario", tipo="decimal",
                            unidad=r.unidad, obligatoria=False, entidad="resultado", ref_id=r.id,
                            ayuda="Resultado de interés que se registra directamente."))
    for clave, etiqueta, tipo, ayuda in EJECUCION:
        cols.append(Columna(clave, etiqueta, "usuario", tipo=tipo, entidad="ejecucion", ayuda=ayuda))
    return cols


def columnas_resultados() -> list[Columna]:
    return [
        Columna("registro_id", "ID registro", "sistema", obligatoria=True),
        Columna("resultado_id", "Código del resultado", "sistema"),
        Columna("resultado", "Resultado", "sistema"),
        Columna("ambito", "¿A qué mediciones corresponde?", "sistema"),
        Columna("grupo", "Grupo", "sistema"),
        Columna("mediciones", "Mediciones del grupo", "sistema"),
        Columna("unidad", "Unidad", "sistema"),
        Columna("valor", "Valor", "usuario", tipo="decimal"),
        Columna("observaciones", "Observaciones", "usuario"),
    ]


def filas_resultados_agrupados(e: Estudio) -> list[dict]:
    """Una fila por cada grupo al que pertenece un resultado directo agrupado (V07).

    Interpretación provisional del ámbito (PD09 pendiente):
      serie     = repeticiones de una misma condición (mismo punto, recursos y niveles)
      punto     = todas las mediciones de un punto
      condicion = grupo comparable definido en D06
      estudio   = todo el estudio
      otro      = un registro que el usuario describe en «Observaciones»
    """
    filas: list[dict] = []
    contador = 0

    def agregar(r: ResultadoInteres, grupo: str, mediciones: list[str]):
        nonlocal contador
        contador += 1
        filas.append({
            "registro_id": f"RD{contador:04d}", "resultado_id": r.id, "resultado": r.nombre,
            "ambito": r.ambito, "grupo": grupo, "mediciones": ", ".join(mediciones), "unidad": r.unidad,
        })

    for r in e.resultados_directos_agrupados():
        if r.ambito in ("serie", "punto", "condicion"):
            grupos: dict[str, list[str]] = {}
            for m in e.plan:
                if r.ambito == "punto":
                    clave = etiqueta_punto(e, m.punto_id)
                elif r.ambito == "serie":
                    pid, tec, pat, eq, niveles = condicion_de(e, m)
                    partes = [etiqueta_punto(e, pid)] + [x for x in (tec, pat, eq) if x] + [v for _, v in niveles]
                    clave = " · ".join(partes)
                else:
                    clave = grupo_comparable(e, m)
                grupos.setdefault(clave, []).append(m.medicion_id)
            for clave, ids in grupos.items():
                agregar(r, clave, ids)
        elif r.ambito == "estudio":
            agregar(r, "Todo el estudio", [m.medicion_id for m in e.plan])
        else:
            agregar(r, "Definido por el usuario (describir en Observaciones)", [])
    return filas
