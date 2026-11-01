"""Generación de la plantilla Excel parametrizada."""

import io
import json

from openpyxl import load_workbook

from src.plantillas.especificacion import columnas_mediciones


def test_plantilla_coherente_con_el_diseno(plantilla, estudio_aprobado):
    """Entrada: diseño aprobado de 16 mediciones con 3 datos, 1 resultado calculado y 1 resultado directo por punto.
    Esperado: hoja Mediciones con 16 filas en el orden del plan; columnas de datos con unidad; sin columna «Resultado»;
    el resultado calculado no tiene columna; hoja Resultados_directos con un registro por punto."""
    wb = load_workbook(io.BytesIO(plantilla))
    assert {"Instrucciones", "Mediciones", "Resultados_directos", "Estudio", "Definiciones", "_control", "_listas"} <= set(wb.sheetnames)
    ws = wb["Mediciones"]
    encabezados = [c.value for c in ws[1]]
    assert ws.max_row == 17
    assert [ws.cell(row=i, column=1).value for i in range(2, 18)] == [m.medicion_id for m in estudio_aprobado.plan]
    assert "Indicación del equipo [°C] *" in encabezados and "Temperatura ambiente [°C]" in encabezados
    assert not any(str(h).strip().lower() == "resultado" for h in encabezados)
    assert not any("Error" in str(h) for h in encabezados)
    wr = wb["Resultados_directos"]
    assert wr.max_row == 3 and wr.cell(row=2, column=3).value == "Inestabilidad"


def test_metadatos_de_control_y_proteccion(plantilla, estudio_aprobado):
    """Entrada: plantilla generada.
    Esperado: _control oculta con estudio, versión, huella y columnas; hojas protegidas; celdas del usuario desbloqueadas;
    lista de selección para el técnico real."""
    wb = load_workbook(io.BytesIO(plantilla))
    wc = wb["_control"]
    control = {wc.cell(row=i, column=1).value: wc.cell(row=i, column=2).value for i in range(1, wc.max_row + 1)}
    assert wc.sheet_state == "hidden" and control["codigo_estudio"] == estudio_aprobado.codigo
    assert control["version_diseno"] == 1 and len(control["huella_diseno"]) == 64
    assert len(json.loads(control["columnas_mediciones"])) == len(columnas_mediciones(estudio_aprobado))
    ws = wb["Mediciones"]
    assert ws.protection.sheet
    usuario = [j for j, h in enumerate(ws[1], start=1) if "Indicación" in str(h.value)][0]
    assert ws.cell(row=2, column=1).protection.locked and not ws.cell(row=2, column=usuario).protection.locked
    assert any("_listas" in dv.formula1 for dv in ws.data_validations.dataValidation if dv.formula1)


def test_columna_para_resultado_directo_por_medicion(repo, estudio_aprobado):
    """Entrada: se agrega un resultado directo de ámbito «medición» y se aprueba una nueva versión.
    Esperado: la plantilla incluye una columna propia para ese resultado en Mediciones."""
    from src.modelos.estudio import ResultadoInteres
    from src.plantillas.generador import generar_plantilla
    e = estudio_aprobado
    e.resultados.append(ResultadoInteres("R-03", "Corrección registrada", unidad="°C", origen="directo", ambito="medicion"))
    repo.guardar_estudio(e, "pruebas")
    repo.aprobar_version(e, "pruebas")
    ws = load_workbook(io.BytesIO(generar_plantilla(e)))["Mediciones"]
    assert "Corrección registrada [°C]" in [c.value for c in ws[1]]
