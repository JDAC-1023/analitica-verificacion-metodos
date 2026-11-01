"""Datos sintéticos y utilidades compartidas por las pruebas."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import pandas as pd
import pytest
from openpyxl import load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("AVM_SIN_TESTEOS", "1")  # la carga inicial de los testeos se prueba aparte

from src.persistencia.repositorio import RepositorioLocal  # noqa: E402
from src.plantillas.diligenciar import diligenciar_plantilla  # noqa: E402
from src.plantillas.generador import generar_plantilla  # noqa: E402
from src.servicios.demo import construir_estudio_demo  # noqa: E402


@pytest.fixture
def repo(tmp_path):
    return RepositorioLocal(tmp_path / "datos")


@pytest.fixture
def estudio_aprobado(repo):
    """Estudio sintético de 16 mediciones (2 puntos × 2 técnicos × 2 días × 2 repeticiones), versión 1 aprobada."""
    base = repo.crear_estudio("Estudio sintético", "pruebas")
    e = construir_estudio_demo(base.codigo, base.nombre)
    repo.guardar_estudio(e, "pruebas")
    repo.aprobar_version(e, "pruebas")
    return e


@pytest.fixture
def plantilla(estudio_aprobado):
    return generar_plantilla(estudio_aprobado)


def valores_completos(e, desplazamiento: float = 0.0) -> pd.DataFrame:
    """Valores sintéticos para todas las mediciones (incluye negativos y muchas cifras)."""
    filas = []
    for i, m in enumerate(e.plan):
        filas.append({"medicion_id": m.medicion_id,
                      "V-01": round(20.0 + i * 0.0137 - 0.05 + desplazamiento, 6),
                      "V-02": 20.0 if m.punto_id == "PT-01" else 40.0,
                      "V-03": -1.234567890123 if i == 0 else 21.5})
    return pd.DataFrame(filas, dtype=object)


def resultados_completos() -> pd.DataFrame:
    return pd.DataFrame({"registro_id": ["RD0001", "RD0002"], "valor": [0.021, -0.013]})


@pytest.fixture
def archivo_completo(plantilla, estudio_aprobado):
    return diligenciar_plantilla(plantilla, valores_completos(estudio_aprobado), resultados_completos())


def editar_libro(contenido: bytes, funcion) -> bytes:
    """Abre el Excel, aplica `funcion(wb)` y devuelve los nuevos bytes (simula ediciones del usuario)."""
    wb = load_workbook(io.BytesIO(contenido))
    for ws in wb.worksheets:
        ws.protection.sheet = False
    funcion(wb)
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def columna(wb, etiqueta: str, hoja: str = "Mediciones") -> int:
    ws = wb[hoja]
    for j in range(1, ws.max_column + 1):
        valor = str(ws.cell(row=1, column=j).value or "")
        if valor == etiqueta or valor == etiqueta + " *":
            return j
    raise KeyError(etiqueta)
