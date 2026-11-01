"""Incidencias de calidad: estructura y redacción de mensajes."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from src.calidad.reglas import REGLAS


@dataclass
class Incidencia:
    regla: str                  # código RCxx
    severidad: str
    mensaje: str
    hoja: str = ""
    fila: int | None = None     # fila de Excel (1 = encabezado)
    columna: str = ""           # encabezado visible
    celda: str = ""             # p. ej. "J18"
    registro_id: str = ""       # medición o registro de resultado
    valor: str = ""             # valor original (texto)
    esperado: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class _Seguro(dict):
    def __missing__(self, clave):  # deja la llave visible si falta un dato
        return "{" + clave + "}"


def crear(regla: str, **datos) -> Incidencia:
    r = REGLAS[regla]
    campos = {k: ("" if v is None else v) for k, v in datos.items()}
    texto = r.mensaje.format_map(_Seguro(
        archivo=campos.get("archivo", ""), hoja=campos.get("hoja", ""), fila=campos.get("fila", ""),
        columna=campos.get("columna", ""), celda=campos.get("celda", ""), medicion=campos.get("registro_id", ""),
        valor=campos.get("valor", ""), esperado=campos.get("esperado", ""),
    ))
    return Incidencia(
        regla=regla, severidad=r.severidad, mensaje=texto, hoja=campos.get("hoja", ""),
        fila=datos.get("fila"), columna=campos.get("columna", ""), celda=campos.get("celda", ""),
        registro_id=campos.get("registro_id", ""), valor=str(campos.get("valor", "")),
        esperado=str(campos.get("esperado", "")),
    )
