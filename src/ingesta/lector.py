"""Lectura e identificación de la plantilla diligenciada (X05).

Pasos 2 a 6 de la ingesta: verificar formato, identificar el estudio,
comprobar versión y huella del diseño, verificar hojas y columnas, y leer los
registros conservando su ubicación original. No interpreta ni corrige
valores: eso lo hace el evaluador de calidad.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Callable

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from src.calidad.incidencias import Incidencia, crear
from src.modelos.estudio import Estudio
from src.plantillas.especificacion import (
    FORMATO_PLANTILLA, HOJA_CONTROL, HOJA_MEDICIONES, HOJA_RESULTADOS, columnas_mediciones,
    columnas_resultados, filas_resultados_agrupados,
)


def a_json(valor: Any) -> Any:
    """Representa el valor de una celda sin perder información y apto para JSON."""
    if isinstance(valor, datetime):
        return {"__fecha_hora__": valor.isoformat()}
    if isinstance(valor, date):
        return {"__fecha__": valor.isoformat()}
    if isinstance(valor, time):
        return {"__hora__": valor.isoformat()}
    if isinstance(valor, (int, float, str, bool)) or valor is None:
        return valor
    return str(valor)


def texto_original(valor: Any) -> str:
    """Forma textual del valor original, para mensajes y trazabilidad."""
    if valor is None:
        return ""
    if isinstance(valor, dict):
        return next(iter(valor.values()))
    if isinstance(valor, float):
        return repr(valor)
    return str(valor)


def _limpiar_encabezado(valor: Any) -> str:
    texto = str(valor or "").strip()
    return texto[:-2].strip() if texto.endswith(" *") else texto


@dataclass
class Lectura:
    nombre_archivo: str
    estado_archivo: str = "leido"           # leido | rechazado
    incidencias: list[Incidencia] = field(default_factory=list)
    control: dict[str, Any] = field(default_factory=dict)
    version_diseno: int | None = None
    hojas: list[str] = field(default_factory=list)
    filas_mediciones: list[dict] = field(default_factory=list)   # {fila, valores{clave: raw}, extras{etiqueta: raw}}
    filas_resultados: list[dict] = field(default_factory=list)
    posiciones_mediciones: dict[str, str] = field(default_factory=dict)  # clave -> letra
    posiciones_resultados: dict[str, str] = field(default_factory=dict)

    def rechazar(self, incidencia: Incidencia) -> "Lectura":
        self.incidencias.append(incidencia)
        self.estado_archivo = "rechazado"
        return self

    def to_dict(self) -> dict:
        d = dict(self.__dict__)
        d["incidencias"] = [i.to_dict() for i in self.incidencias]
        return d


def _leer_hoja(ws, columnas, hoja: str, lectura: Lectura) -> tuple[list[dict], dict[str, str], bool]:
    """Ubica las columnas por su encabezado y lee las filas no vacías."""
    encabezados = {}
    for j in range(1, ws.max_column + 1):
        etiqueta = _limpiar_encabezado(ws.cell(row=1, column=j).value)
        if etiqueta:
            encabezados.setdefault(etiqueta, j)
    posiciones: dict[str, int] = {}
    valida = True
    for col in columnas:
        if col.etiqueta in encabezados:
            posiciones[col.clave] = encabezados[col.etiqueta]
        else:
            lectura.rechazar(crear("RC06", hoja=hoja, esperado=col.etiqueta, columna=col.etiqueta))
            valida = False
    esperadas = {c.etiqueta for c in columnas}
    extras = {e: j for e, j in encabezados.items() if e not in esperadas}
    for etiqueta, j in extras.items():
        lectura.incidencias.append(crear("RC07", hoja=hoja, valor=etiqueta, columna=etiqueta,
                                         celda=f"{get_column_letter(j)}1", fila=1))
    filas = []
    if valida:
        for i in range(2, ws.max_row + 1):
            valores = {clave: a_json(ws.cell(row=i, column=j).value) for clave, j in posiciones.items()}
            adicionales = {e: a_json(ws.cell(row=i, column=j).value) for e, j in extras.items()}
            if all(v in (None, "") for v in valores.values()) and all(v in (None, "") for v in adicionales.values()):
                continue
            filas.append({"fila": i, "valores": valores, "extras": adicionales})
    return filas, {k: get_column_letter(j) for k, j in posiciones.items()}, valida


def leer_plantilla(
    contenido: bytes,
    nombre_archivo: str,
    codigo_esperado: str,
    version_esperada: int | None,
    obtener_version: Callable[[str, int], tuple[Estudio, str]],
) -> tuple[Lectura, Estudio | None]:
    """Devuelve la lectura y el estudio de la versión de diseño correspondiente."""
    lectura = Lectura(nombre_archivo=nombre_archivo)
    try:
        wb = load_workbook(io.BytesIO(contenido), data_only=True, read_only=False)
    except Exception:  # noqa: BLE001 - cualquier fallo de lectura es «archivo incompatible»
        return lectura.rechazar(crear("RC01", archivo=nombre_archivo)), None
    lectura.hojas = list(wb.sheetnames)

    for hoja in (HOJA_CONTROL, HOJA_MEDICIONES):
        if hoja not in wb.sheetnames:
            return lectura.rechazar(crear("RC02", hoja=hoja)), None

    ws = wb[HOJA_CONTROL]
    control = {str(ws.cell(row=i, column=1).value): ws.cell(row=i, column=2).value for i in range(1, ws.max_row + 1)}
    lectura.control = {k: v for k, v in control.items() if not str(k).startswith("columnas_")}
    if control.get("formato_plantilla") != FORMATO_PLANTILLA:
        return lectura.rechazar(crear("RC03", valor=control.get("formato_plantilla") or "desconocido")), None
    if control.get("codigo_estudio") != codigo_esperado:
        return lectura.rechazar(crear("RC04", valor=control.get("codigo_estudio"), esperado=codigo_esperado)), None

    try:
        version = int(control.get("version_diseno"))
    except (TypeError, ValueError):
        return lectura.rechazar(crear("RC05", valor=control.get("version_diseno"), esperado=version_esperada or "aprobada")), None
    lectura.version_diseno = version
    if version_esperada is not None and version != version_esperada:
        return lectura.rechazar(crear("RC05", valor=version, esperado=version_esperada)), None
    try:
        estudio, huella = obtener_version(codigo_esperado, version)
    except Exception:  # noqa: BLE001 - versión inexistente
        return lectura.rechazar(crear("RC05", valor=version, esperado="una versión aprobada existente")), None
    if control.get("huella_diseno") != huella:
        return lectura.rechazar(crear("RC05", valor=f"{version} (huella distinta)", esperado=f"{version} con la huella aprobada")), None

    filas, posiciones, _ = _leer_hoja(wb[HOJA_MEDICIONES], columnas_mediciones(estudio), HOJA_MEDICIONES, lectura)
    lectura.filas_mediciones, lectura.posiciones_mediciones = filas, posiciones

    if filas_resultados_agrupados(estudio):
        if HOJA_RESULTADOS not in wb.sheetnames:
            return lectura.rechazar(crear("RC02", hoja=HOJA_RESULTADOS)), estudio
        filas_r, pos_r, _ = _leer_hoja(wb[HOJA_RESULTADOS], columnas_resultados(), HOJA_RESULTADOS, lectura)
        lectura.filas_resultados, lectura.posiciones_resultados = filas_r, pos_r
    return lectura, estudio
