"""Generación de la plantilla Excel de captura a partir de un diseño aprobado (X01).

- Columnas grises con candado: las completa el sistema (planificación).
- Columnas blancas: las completa el usuario (datos experimentales, resultados
  directos y ejecución real).
- Hojas ocultas `_control` y `_listas`: metadatos para verificar en la carga
  que el archivo corresponde al estudio, a la versión y a la huella del diseño.
"""

from __future__ import annotations

import io
import json

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter, quote_sheetname
from openpyxl.worksheet.datavalidation import DataValidation

from src.auditoria.huella import ahora_iso, huella_diseno
from src.modelos.estudio import Estudio
from src.planificacion.plan import etiqueta_punto
from src.plantillas.especificacion import (
    FORMATO_PLANTILLA, HOJA_CONTROL, HOJA_DEFINICIONES, HOJA_ESTUDIO, HOJA_INSTRUCCIONES, HOJA_LISTAS,
    HOJA_MEDICIONES, HOJA_RESULTADOS, columnas_mediciones, columnas_resultados, filas_resultados_agrupados,
)


class ErrorPlantilla(Exception):
    pass


# Paleta (coherente con la interfaz)
TINTA = "1E1B4B"
SISTEMA_ENC = "334155"
SISTEMA_CELDA = "EEF1F6"
USUARIO_ENC = "6D5BD0"
USUARIO_CELDA = "FFFFFF"
OBLIGATORIO_ENC = "4C3BB0"
BORDE = Side(style="thin", color="D5D9E2")

FUENTE_ENC = Font(bold=True, color="FFFFFF")
ALINEADO = Alignment(vertical="center", wrap_text=True)


def _valor_sistema(e: Estudio, m, clave: str):
    p = e.punto(m.punto_id)
    mag = e.magnitud(p.magnitud_id) if p else None
    if clave == "medicion_id":
        return m.medicion_id
    if clave == "punto_id":
        return m.punto_id
    if clave == "magnitud":
        return mag.nombre if mag else ""
    if clave == "valor_nominal":
        return p.valor_nominal if p else None
    if clave == "unidad_punto":
        return p.unidad if p else ""
    if clave == "repeticion":
        return m.repeticion
    if clave.startswith("factor:"):
        return m.niveles.get(clave.split(":", 1)[1], "")
    if clave == "orden":
        return m.orden
    return getattr(m, clave, "")


def _encabezado(ws, columnas):
    for j, col in enumerate(columnas, start=1):
        celda = ws.cell(row=1, column=j, value=col.etiqueta + (" *" if col.obligatoria and col.origen == "usuario" else ""))
        color = SISTEMA_ENC if col.origen == "sistema" else (OBLIGATORIO_ENC if col.obligatoria else USUARIO_ENC)
        celda.fill = PatternFill("solid", fgColor=color)
        celda.font = FUENTE_ENC
        celda.alignment = ALINEADO
        celda.border = Border(top=BORDE, bottom=BORDE, left=BORDE, right=BORDE)
        ws.column_dimensions[get_column_letter(j)].width = min(max(len(col.etiqueta) + 4, 14), 40)
    ws.row_dimensions[1].height = 34


def _celdas(ws, columnas, n_filas):
    from openpyxl.styles import Protection
    for j, col in enumerate(columnas, start=1):
        for i in range(2, n_filas + 2):
            celda = ws.cell(row=i, column=j)
            celda.border = Border(top=BORDE, bottom=BORDE, left=BORDE, right=BORDE)
            if col.origen == "sistema":
                celda.fill = PatternFill("solid", fgColor=SISTEMA_CELDA)
                celda.protection = Protection(locked=True)
            else:
                celda.fill = PatternFill("solid", fgColor=USUARIO_CELDA)
                celda.protection = Protection(locked=False)
                if col.tipo == "fecha":
                    celda.number_format = "yyyy-mm-dd"


def _proteger(ws):
    # Protección sin contraseña: evita cambios accidentales en la estructura,
    # pero no impide trabajar. Se permite ajustar el ancho de columnas y filtrar.
    ws.protection.sheet = True
    ws.protection.formatColumns = False
    ws.protection.formatRows = False
    ws.protection.autoFilter = False
    ws.protection.sort = False


def _validaciones(ws, columnas, n_filas, listas: dict[str, str]):
    if n_filas == 0:
        return
    for j, col in enumerate(columnas, start=1):
        if col.origen != "usuario":
            continue
        rango = f"{get_column_letter(j)}2:{get_column_letter(j)}{n_filas + 1}"
        dv = None
        if col.tipo == "decimal":
            dv = DataValidation(type="decimal", operator="between", formula1="-1E+300", formula2="1E+300")
            dv.error = "Escribe un número. Usa el separador decimal configurado en tu Excel."
        elif col.tipo == "entero":
            dv = DataValidation(type="whole", operator="between", formula1="-2147483647", formula2="2147483647")
            dv.error = "Escribe un número entero."
        elif col.tipo == "fecha":
            dv = DataValidation(type="date", operator="greaterThan", formula1="1")
            dv.error = "Escribe una fecha válida (AAAA-MM-DD)."
        elif col.tipo == "si_no":
            dv = DataValidation(type="list", formula1='"Sí,No"')
            dv.error = "Selecciona Sí o No."
        elif col.clave in listas:
            dv = DataValidation(type="list", formula1=listas[col.clave])
            dv.error = "Selecciona un valor de la lista."
        if dv is not None:
            # Estilo «advertencia»: avisa sin bloquear; la carga valida de nuevo.
            dv.errorStyle = "warning"
            dv.errorTitle = "Valor no esperado"
            dv.showErrorMessage = True
            dv.allow_blank = True
            if col.ayuda:
                dv.prompt = col.ayuda[:250]
                dv.showInputMessage = True
            ws.add_data_validation(dv)
            dv.add(rango)


def generar_plantilla(e: Estudio) -> bytes:
    """Devuelve el Excel (bytes). Exige un diseño aprobado y sin cambios pendientes."""
    if e.estado != "aprobado" or e.version_diseno < 1:
        raise ErrorPlantilla("La plantilla solo se genera desde un diseño aprobado (P05).")
    if not e.plan:
        raise ErrorPlantilla("El diseño aprobado no tiene mediciones planificadas.")

    huella = huella_diseno(e.to_dict())
    generado = ahora_iso()
    cols_med = columnas_mediciones(e)
    cols_res = columnas_resultados()
    filas_res = filas_resultados_agrupados(e)

    wb = Workbook()
    # ------------------------------------------------------------- Instrucciones
    ws = wb.active
    ws.title = HOJA_INSTRUCCIONES
    textos = [
        ("Plantilla de registro de mediciones", True),
        (f"Estudio {e.codigo} · {e.nombre} · versión del diseño {e.version_diseno}", False),
        ("", False),
        ("Cómo diligenciar", True),
        ("1. Registra los datos en la hoja «Mediciones». Cada fila es una medición planificada.", False),
        ("2. Las columnas grises las completó el sistema: no las cambies.", False),
        ("3. Las columnas moradas son para ti. Las marcadas con * son obligatorias.", False),
        ("4. Escribe los valores tal como los registraste: sin redondear y sin cambiar unidades ni signos.", False),
        ("5. Si un dato no se tomó, deja la celda vacía. No escribas cero ni valores estimados.", False),
        ("6. Si cambió el técnico o el patrón previsto, regístralo y escribe el motivo del cambio.", False),
        ("7. No agregues, borres ni reordenes columnas u hojas. Puedes ordenar o filtrar filas.", False),
        ("8. Si la plantilla incluye «Resultados_directos», registra allí los resultados que corresponden a un grupo de mediciones.", False),
        ("9. Guarda el archivo en formato .xlsx y cárgalo en la aplicación en el mismo estudio.", False),
        ("", False),
        ("Colores", True),
        ("Gris: completa el sistema · Morado: completas tú · Morado oscuro con *: obligatorio", False),
        ("", False),
        ("Los resultados calculados (si existen) no tienen columna: los calculará el sistema en una fase posterior.", False),
    ]
    for i, (texto, negrita) in enumerate(textos, start=1):
        c = ws.cell(row=i, column=1, value=texto)
        c.font = Font(bold=negrita, size=14 if i == 1 else 11, color=TINTA)
    ws.column_dimensions["A"].width = 120
    _proteger(ws)

    # ------------------------------------------------------------- Estudio
    ws = wb.create_sheet(HOJA_ESTUDIO)
    filas = [
        ("Código del estudio", e.codigo), ("Nombre", e.nombre), ("Tipo de estudio", e.tipo),
        ("Método", e.metodo), ("Versión del método", e.version_metodo), ("Responsable", e.responsable),
        ("Versión del diseño", e.version_diseno), ("Huella del diseño", huella),
        ("Formato de plantilla", FORMATO_PLANTILLA), ("Generada el", generado),
        ("Mediciones planificadas", len(e.plan)),
        ("Magnitudes", "; ".join(f"{m.nombre} [{m.unidad}]" for m in e.magnitudes)),
        ("Puntos", "; ".join(etiqueta_punto(e, p.id) for p in e.puntos)),
        ("Técnicos", "; ".join(f"{t.codigo} {t.nombre}".strip() for t in e.tecnicos)),
        ("Patrones", "; ".join(f"{p.codigo} {p.descripcion or p.nombre}".strip() for p in e.patrones)),
        ("Equipo a evaluar (IBC)", "; ".join(
            " · ".join(x for x in (i.codigo, i.descripcion, i.marca, i.modelo, f"serie {i.serie}" if i.serie else "",
                                   f"resolución {i.resolucion}" if i.resolucion else "") if x) for i in e.ibcs)),
    ]
    for i, (k, v) in enumerate(filas, start=1):
        ws.cell(row=i, column=1, value=k).font = Font(bold=True, color=TINTA)
        ws.cell(row=i, column=2, value=v)
    ws.column_dimensions["A"].width = 28
    ws.column_dimensions["B"].width = 90
    _proteger(ws)

    # ------------------------------------------------------------- Listas (oculta)
    wl = wb.create_sheet(HOJA_LISTAS)
    listas: dict[str, str] = {}
    columna_lista = 0

    def lista(clave: str, valores: list[str]):
        nonlocal columna_lista
        if not valores:
            return
        columna_lista += 1
        letra = get_column_letter(columna_lista)
        wl.cell(row=1, column=columna_lista, value=clave)
        for i, v in enumerate(valores, start=2):
            wl.cell(row=i, column=columna_lista, value=v)
        listas[clave] = f"{quote_sheetname(HOJA_LISTAS)}!${letra}$2:${letra}${len(valores) + 1}"

    lista("tecnico_real", [t.codigo for t in e.tecnicos])
    lista("patron_real", [p.codigo for p in e.patrones])
    for f in e.factores_libres():
        if f.rol == "solo_se_registra":
            lista(f"factor:{f.id}", list(f.niveles))
    wl.sheet_state = "hidden"

    # ------------------------------------------------------------- Mediciones
    ws = wb.create_sheet(HOJA_MEDICIONES, index=1)
    _encabezado(ws, cols_med)
    plan = sorted(e.plan, key=lambda m: (m.orden if m.orden is not None else 10**9, m.medicion_id))
    for i, m in enumerate(plan, start=2):
        for j, col in enumerate(cols_med, start=1):
            if col.origen == "sistema":
                ws.cell(row=i, column=j, value=_valor_sistema(e, m, col.clave))
    _celdas(ws, cols_med, len(plan))
    _validaciones(ws, cols_med, len(plan), listas)
    primera_usuario = next(j for j, c in enumerate(cols_med, start=1) if c.origen == "usuario")
    ws.freeze_panes = ws.cell(row=2, column=min(primera_usuario, 3))
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols_med))}{len(plan) + 1}"
    _proteger(ws)

    # ------------------------------------------------------------- Resultados directos agrupados
    if filas_res:
        ws = wb.create_sheet(HOJA_RESULTADOS, index=2)
        _encabezado(ws, cols_res)
        for i, fila in enumerate(filas_res, start=2):
            for j, col in enumerate(cols_res, start=1):
                if col.origen == "sistema":
                    ws.cell(row=i, column=j, value=fila.get(col.clave, ""))
        _celdas(ws, cols_res, len(filas_res))
        _validaciones(ws, cols_res, len(filas_res), {})
        ws.freeze_panes = "B2"
        _proteger(ws)

    # ------------------------------------------------------------- Definiciones (informativa)
    ws = wb.create_sheet(HOJA_DEFINICIONES)
    ws.append(["Datos que se registran"])
    ws.append(["Código", "Nombre", "Tipo", "Unidad", "Obligatorio", "Descripción"])
    for v in e.variables:
        ws.append([v.id, v.nombre, v.tipo_dato, v.unidad, "Sí" if v.obligatoria else "No", v.descripcion])
    ws.append([])
    ws.append(["Resultados de interés"])
    ws.append(["Código", "Nombre", "Unidad", "¿Cómo se obtiene?", "¿A qué mediciones corresponde?",
               "Depende de", "Referencia del cálculo", "¿Se analizará?"])
    for r in e.resultados:
        ws.append([r.id, r.nombre, r.unidad, "Lo registras tú" if r.origen == "directo" else "Lo calculará el sistema (fase posterior)",
                   r.ambito, ", ".join(r.dependencias), r.referencia_calculo, "Sí" if r.analizar else "No"])
    for fila in ws.iter_rows():
        if fila[0].value in ("Datos que se registran", "Resultados de interés", "Código"):
            for c in fila:
                c.font = Font(bold=True, color=TINTA)
    for letra, ancho in zip("ABCDEFGH", (10, 28, 22, 12, 26, 20, 30, 14)):
        ws.column_dimensions[letra].width = ancho
    _proteger(ws)

    # ------------------------------------------------------------- Control (oculta)
    wc = wb.create_sheet(HOJA_CONTROL)
    control = {
        "formato_plantilla": FORMATO_PLANTILLA,
        "codigo_estudio": e.codigo,
        "version_diseno": e.version_diseno,
        "huella_diseno": huella,
        "generado_en": generado,
        "mediciones_planificadas": len(plan),
        "columnas_mediciones": json.dumps([c.to_dict() for c in cols_med], ensure_ascii=False),
        "columnas_resultados": json.dumps([c.to_dict() for c in cols_res], ensure_ascii=False) if filas_res else "",
        # Los registros agrupados se reconstruyen desde la versión del diseño
        # (son deterministas); aquí solo se guarda su número.
        "registros_resultados": len(filas_res),
    }
    for i, (k, v) in enumerate(control.items(), start=1):
        wc.cell(row=i, column=1, value=k)
        wc.cell(row=i, column=2, value=v)
    wc.sheet_state = "hidden"
    _proteger(wc)

    wb.active = 1
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


def nombre_archivo_plantilla(e: Estudio) -> str:
    return f"plantilla_{e.codigo}_v{e.version_diseno}.xlsx"
