"""Huellas digitales (SHA-256) y marcas de tiempo para la trazabilidad."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any


def sha256_bytes(contenido: bytes) -> str:
    return hashlib.sha256(contenido).hexdigest()


def json_canonico(datos: Any) -> str:
    """JSON determinista: mismas entradas -> mismo texto -> misma huella."""
    return json.dumps(datos, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def sha256_json(datos: Any) -> str:
    return sha256_bytes(json_canonico(datos).encode("utf-8"))


def ahora_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# Campos de la configuración que NO forman parte del diseño experimental
# y por eso no cambian la huella del diseño.
CAMPOS_FUERA_DE_HUELLA = {"estado", "aprobado_por", "fecha_aprobacion", "creado_en", "actualizado_en", "version_diseno", "paso_asistente"}


def huella_diseno(estudio_dict: dict[str, Any]) -> str:
    """Huella del contenido del diseño (sin metadatos de aprobación).

    Se imprime en la plantilla y se compara al cargar el archivo, para
    comprobar que corresponde exactamente al diseño que la originó.
    """
    contenido = {k: v for k, v in estudio_dict.items() if k not in CAMPOS_FUERA_DE_HUELLA}
    return sha256_json(contenido)
