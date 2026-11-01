"""Lectura del conjunto preparado desde Python (entrada del motor estadístico).

    from src.exportacion.lector_salida import cargar_conjunto
    datos = cargar_conjunto("conjunto_preparado_EST-0001.zip")
    obs = datos["observaciones_analisis"]           # DataFrame
    print(datos["manifiesto"]["conteos"])
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pandas as pd

from src.auditoria.huella import sha256_bytes


class ErrorConjunto(Exception):
    pass


def cargar_conjunto(origen: str | Path | bytes, verificar: bool = True) -> dict:
    """Devuelve un diccionario {nombre_tabla: DataFrame} + 'manifiesto' + 'estudio'.

    Si `verificar` es True, comprueba que la huella SHA-256 de cada CSV
    coincide con la registrada en el manifiesto (integridad del conjunto).
    """
    contenido = origen if isinstance(origen, bytes) else Path(origen).read_bytes()
    datos: dict = {}
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        manifiesto = json.loads(z.read("manifiesto.json"))
        for nombre in z.namelist():
            bruto = z.read(nombre)
            if verificar and nombre in manifiesto["huellas_archivos"] and sha256_bytes(bruto) != manifiesto["huellas_archivos"][nombre]:
                raise ErrorConjunto(f"El archivo {nombre} no coincide con su huella: el conjunto fue modificado.")
            if nombre.endswith(".csv"):
                datos[nombre[:-4]] = pd.read_csv(io.BytesIO(bruto), encoding="utf-8-sig", keep_default_na=True)
        datos["estudio"] = json.loads(z.read("estudio_version.json"))
    datos["manifiesto"] = manifiesto
    return datos


def matriz_por_variable(datos: dict, variable_id: str) -> pd.DataFrame:
    """Filtra la vista de análisis para un dato experimental concreto."""
    obs = datos["observaciones_analisis"]
    return obs[obs["variable_id"] == variable_id].reset_index(drop=True)
