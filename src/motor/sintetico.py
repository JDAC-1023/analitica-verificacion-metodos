"""Tablas mínimas con el formato SAL-1.0 construidas desde un estudio y un
diccionario de valores. Se usa en pruebas, ejemplos y demostraciones; nunca
para datos reales (los reales vienen del conjunto preparado).
"""

from __future__ import annotations

import pandas as pd

from src.modelos.estudio import Estudio


def tablas_sinteticas(e: Estudio, valores: dict[str, dict[str, float | None]]) -> dict[str, pd.DataFrame]:
    """valores: {medicion_id: {variable_id: valor}}. Solo incluye las mediciones presentes."""
    med, niv, val = [], [], []
    for m in e.plan:
        if m.medicion_id not in valores:
            continue
        med.append({"medicion_id": m.medicion_id, "punto_id": m.punto_id, "repeticion": m.repeticion,
                    "tecnico_previsto": m.tecnico, "patron_previsto": m.patron, "equipo_previsto": m.equipo,
                    "tecnico_real": None, "patron_real": None})
        for f in e.factores:
            nivel = getattr(m, f.vinculo_recurso) if f.vinculo_recurso != "ninguno" else m.niveles.get(f.id)
            niv.append({"medicion_id": m.medicion_id, "factor_id": f.id, "factor": f.nombre, "nivel": nivel})
        for vid, x in valores[m.medicion_id].items():
            val.append({"medicion_id": m.medicion_id, "variable_id": vid, "valor_numerico": x})
    return {"mediciones": pd.DataFrame(med),
            "niveles_factores": pd.DataFrame(niv, columns=["medicion_id", "factor_id", "factor", "nivel"]),
            "valores": pd.DataFrame(val, columns=["medicion_id", "variable_id", "valor_numerico"]),
            "resultados_valores": pd.DataFrame(columns=["resultado_id", "registro_id", "valor"])}
