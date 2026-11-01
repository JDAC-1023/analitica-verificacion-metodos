"""Diligenciamiento programático de una plantilla generada.

Sirve para construir conjuntos de datos sintéticos (por ejemplo, los cuatro
escenarios controlados) sin copiar valores a mano: se parte de la plantilla
descargada y se escriben los valores en las columnas del usuario.

Ejemplo:
    import pandas as pd
    from src.plantillas.diligenciar import diligenciar_plantilla
    valores = pd.DataFrame({"medicion_id": ["M0001", "M0002"], "V-01": [20.013, 20.011]})
    nuevo = diligenciar_plantilla(open("plantilla.xlsx", "rb").read(), valores)
    open("escenario_1.xlsx", "wb").write(nuevo)

Las columnas de `valores` pueden nombrarse con el código del dato (V-01), el
código de un resultado directo (R-02), la clave técnica (var:V-01) o el
encabezado visible del Excel. Las columnas grises del sistema no se modifican.
"""

from __future__ import annotations

import io
import json
import math

import pandas as pd
from openpyxl import load_workbook

from src.plantillas.especificacion import HOJA_CONTROL, HOJA_MEDICIONES, HOJA_RESULTADOS


class ErrorDiligenciamiento(Exception):
    pass


def _control(wb) -> dict:
    ws = wb[HOJA_CONTROL]
    return {ws.cell(row=i, column=1).value: ws.cell(row=i, column=2).value for i in range(1, ws.max_row + 1)}


def _vacio(valor) -> bool:
    return valor is None or (isinstance(valor, float) and math.isnan(valor)) or (valor is pd.NA)


def diligenciar_plantilla(plantilla: bytes, valores: pd.DataFrame, resultados_agrupados: pd.DataFrame | None = None) -> bytes:
    wb = load_workbook(io.BytesIO(plantilla))
    control = _control(wb)
    columnas = json.loads(control["columnas_mediciones"])
    alias: dict[str, int] = {}
    for j, c in enumerate(columnas, start=1):
        if c["origen"] != "usuario":
            continue
        for nombre in (c["clave"], c["etiqueta"], c["ref_id"]):
            if nombre:
                alias[nombre] = j
    if "medicion_id" not in valores.columns:
        raise ErrorDiligenciamiento("El DataFrame de valores necesita la columna «medicion_id».")
    desconocidas = [c for c in valores.columns if c != "medicion_id" and c not in alias]
    if desconocidas:
        raise ErrorDiligenciamiento(f"Columnas que no existen en la plantilla: {desconocidas}")

    ws = wb[HOJA_MEDICIONES]
    filas = {ws.cell(row=i, column=1).value: i for i in range(2, ws.max_row + 1)}
    for _, fila in valores.iterrows():
        i = filas.get(fila["medicion_id"])
        if i is None:
            raise ErrorDiligenciamiento(f"La medición {fila['medicion_id']} no está en la plantilla.")
        for nombre, valor in fila.items():
            if nombre == "medicion_id" or _vacio(valor):
                continue
            ws.cell(row=i, column=alias[nombre], value=valor.item() if hasattr(valor, "item") else valor)

    if resultados_agrupados is not None and len(resultados_agrupados):
        if HOJA_RESULTADOS not in wb.sheetnames:
            raise ErrorDiligenciamiento("Esta plantilla no tiene hoja de resultados agrupados.")
        wr = wb[HOJA_RESULTADOS]
        encabezados = [c.value for c in wr[1]]
        col_valor = encabezados.index("Valor") + 1
        col_obs = encabezados.index("Observaciones") + 1
        filas_r = {wr.cell(row=i, column=1).value: i for i in range(2, wr.max_row + 1)}
        for _, fila in resultados_agrupados.iterrows():
            i = filas_r.get(fila["registro_id"])
            if i is None:
                raise ErrorDiligenciamiento(f"El registro {fila['registro_id']} no está en la plantilla.")
            if "valor" in fila and not _vacio(fila["valor"]):
                wr.cell(row=i, column=col_valor, value=float(fila["valor"]))
            if "observaciones" in fila and not _vacio(fila["observaciones"]):
                wr.cell(row=i, column=col_obs, value=str(fila["observaciones"]))

    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()
