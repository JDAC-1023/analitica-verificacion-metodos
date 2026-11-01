"""Transformaciones autorizables.

Ninguna transformación cambia el valor numérico registrado, su signo, sus
cifras ni su unidad. Solo se interpreta la forma en que el valor quedó
escrito. Cada aplicación queda registrada (celda, valor original, valor
resultante, transformación).

Prohibido por diseño (no existe ninguna transformación que lo haga):
reemplazar faltantes por cero, imputar, redondear, convertir unidades,
cambiar el signo de errores o correcciones, eliminar observaciones por su
comportamiento estadístico.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Transformacion:
    codigo: str
    nombre: str
    descripcion: str
    ejemplo: str
    por_defecto: bool

    def to_dict(self) -> dict:
        return asdict(self)


TRANSFORMACIONES: dict[str, Transformacion] = {t.codigo: t for t in [
    Transformacion("TR01", "Leer números escritos como texto",
                   "Interpreta como número un texto que ya está escrito con punto decimal (o una fecha ISO escrita como texto). El valor no cambia.",
                   "«20.013» (texto) → 20.013", True),
    Transformacion("TR02", "Coma decimal → punto decimal",
                   "Interpreta «20,013» como 20.013. Solo para textos con una única coma y sin separador de miles.",
                   "«20,013» → 20.013", False),
    Transformacion("TR03", "Quitar espacios al inicio y al final",
                   "Elimina espacios sobrantes alrededor de textos y códigos.",
                   "« T-01 » → «T-01»", True),
    Transformacion("TR04", "Unificar mayúsculas de códigos de recursos",
                   "Escribe el código de técnico o patrón como está en el catálogo cuando solo difiere en mayúsculas.",
                   "«t-01» → «T-01»", False),
]}


def autorizadas_por_defecto() -> list[str]:
    return [t.codigo for t in TRANSFORMACIONES.values() if t.por_defecto]
