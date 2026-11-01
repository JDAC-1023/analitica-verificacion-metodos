"""Reglas de calidad sobre registros."""

from src.plantillas.diligenciar import diligenciar_plantilla
from src.servicios.flujo import cargar_archivo
from tests.conftest import columna, editar_libro, resultados_completos, valores_completos


def _cargar(repo, e, contenido):
    return cargar_archivo(repo, e.codigo, contenido, "datos.xlsx", "ana")


def _reglas(c):
    return [i["regla"] for i in c["evaluacion_inicial"]["incidencias"]]


def _estado(c, rid):
    return next(r["estado"] for r in c["evaluacion_inicial"]["registros"] if r["registro_id"] == rid)


def test_valores_faltantes_obligatorios(repo, estudio_aprobado, plantilla):
    """Entrada: M0003 sin «Valor del patrón» (obligatorio); M0004 sin ningún dato; M0005 sin «Temperatura ambiente» (opcional).
    Esperado: M0003 pendiente por RC15 con fila y celda; M0004 pendiente por RC14; M0005 aceptada; nada se reemplaza por cero."""
    v = valores_completos(estudio_aprobado)
    v.loc[2, "V-02"] = None
    v.loc[3, ["V-01", "V-02", "V-03"]] = None
    v.loc[4, "V-03"] = None
    c = _cargar(repo, estudio_aprobado, diligenciar_plantilla(plantilla, v, resultados_completos()))
    inc = c["evaluacion_inicial"]["incidencias"]
    rc15 = next(i for i in inc if i["regla"] == "RC15")
    assert rc15["registro_id"] == "M0003" and rc15["fila"] == 4 and rc15["celda"] == "N4"
    assert "fila 4" in rc15["mensaje"] and "no se incorporó al conjunto preparado" in rc15["mensaje"]
    assert _estado(c, "M0003") == "pendiente" and _estado(c, "M0004") == "pendiente" and _estado(c, "M0005") == "aceptado"
    registro = next(r for r in c["evaluacion_inicial"]["registros"] if r["registro_id"] == "M0005")
    assert registro["valores"]["var:V-03"] is None
    assert c["conteos"]["pendientes"] == 2 and c["conteos"]["conciliado"]


def test_tipo_de_dato_incompatible(repo, estudio_aprobado, plantilla):
    """Entrada: «abc» en Indicación (decimal) de M0002 y «20,5» (coma decimal) en M0006.
    Esperado: ambos RC16 y pendientes con la configuración por defecto (TR02 no autorizada); el valor original se conserva."""
    v = valores_completos(estudio_aprobado)
    v.loc[1, "V-01"] = "abc"
    v.loc[5, "V-01"] = "20,5"
    c = _cargar(repo, estudio_aprobado, diligenciar_plantilla(plantilla, v, resultados_completos()))
    rc16 = [i for i in c["evaluacion_inicial"]["incidencias"] if i["regla"] == "RC16"]
    assert {i["registro_id"] for i in rc16} == {"M0002", "M0006"}
    assert "TR02" in next(i for i in rc16 if i["registro_id"] == "M0006")["mensaje"]
    registro = next(r for r in c["evaluacion_inicial"]["registros"] if r["registro_id"] == "M0002")
    assert registro["originales"]["var:V-01"] == "abc" and registro["estado"] == "pendiente"


def test_identificador_desconocido_se_excluye(repo, estudio_aprobado, archivo_completo):
    """Entrada: el ID de la última fila se cambia por «M9999».
    Esperado: RC08, la fila queda excluida con motivo y M0016 aparece como planificada ausente (RC11)."""
    def cambiar(wb):
        ws = wb["Mediciones"]
        ws.cell(row=ws.max_row, column=1, value="M9999")
    c = _cargar(repo, estudio_aprobado, editar_libro(archivo_completo, cambiar))
    assert {"RC08", "RC11"} <= set(_reglas(c))
    registro = next(r for r in c["evaluacion_inicial"]["registros"] if r["registro_id"] == "M9999")
    assert registro["estado"] == "excluido" and "no está planificado" in registro["motivo_estado"]


def test_fila_sin_identificador_se_excluye(repo, estudio_aprobado, archivo_completo):
    """Entrada: se agrega una fila con datos pero sin ID de medición.
    Esperado: RC09, la fila se excluye y los conteos siguen conciliados (17 recibidos)."""
    def agregar(wb):
        ws = wb["Mediciones"]
        ws.cell(row=ws.max_row + 1, column=columna(wb, "Indicación del equipo [°C]"), value=20.1)
    c = _cargar(repo, estudio_aprobado, editar_libro(archivo_completo, agregar))
    assert "RC09" in _reglas(c) and c["conteos"]["recibidos"] == 17 and c["conteos"]["excluidos"] == 1 and c["conteos"]["conciliado"]


def test_registros_duplicados_quedan_pendientes(repo, estudio_aprobado, archivo_completo):
    """Entrada: la fila de M0002 se copia al final (ID duplicado).
    Esperado: RC10 en ambas filas, ambas pendientes y ninguna elegida automáticamente."""
    def duplicar(wb):
        ws = wb["Mediciones"]
        destino = ws.max_row + 1
        for j in range(1, ws.max_column + 1):
            ws.cell(row=destino, column=j, value=ws.cell(row=3, column=j).value)
    c = _cargar(repo, estudio_aprobado, editar_libro(archivo_completo, duplicar))
    duplicados = [r for r in c["evaluacion_inicial"]["registros"] if r["registro_id"] == "M0002"]
    assert len(duplicados) == 2 and all(r["estado"] == "pendiente" for r in duplicados)
    assert _reglas(c).count("RC10") == 2


def test_medicion_planificada_ausente(repo, estudio_aprobado, archivo_completo):
    """Entrada: se borra la fila de M0016 (mediciones previstas ausentes).
    Esperado: RC11 para M0016 y RC12 (15 recibidas frente a 16 planificadas)."""
    c = _cargar(repo, estudio_aprobado, editar_libro(archivo_completo, lambda wb: wb["Mediciones"].delete_rows(17)))
    assert "RC11" in _reglas(c) and "RC12" in _reglas(c)
    assert c["conteos"]["planificados_ausentes"] == 1 and c["conteos"]["recibidos"] == 15


def test_planificacion_modificada(repo, estudio_aprobado, archivo_completo):
    """Entrada: se cambia el «Técnico previsto» de M0001 (celda gris) por T-02.
    Esperado: RC13 con valor encontrado y valor planificado; registro pendiente."""
    def cambiar(wb):
        wb["Mediciones"].cell(row=2, column=columna(wb, "Técnico previsto"), value="T-02")
    c = _cargar(repo, estudio_aprobado, editar_libro(archivo_completo, cambiar))
    rc13 = next(i for i in c["evaluacion_inicial"]["incidencias"] if i["regla"] == "RC13")
    assert rc13["valor"] == "T-02" and rc13["esperado"] == "T-01" and _estado(c, "M0001") == "pendiente"


def test_recurso_no_registrado(repo, estudio_aprobado, plantilla):
    """Entrada: «Técnico que midió» = T-09 (no existe) con motivo.
    Esperado: RC17 y registro pendiente."""
    v = valores_completos(estudio_aprobado)
    v["tecnico_real"] = None
    v["motivo_cambio"] = None
    v.loc[0, "tecnico_real"] = "T-09"
    v.loc[0, "motivo_cambio"] = "Reemplazo"
    c = _cargar(repo, estudio_aprobado, diligenciar_plantilla(plantilla, v, resultados_completos()))
    assert "RC17" in _reglas(c) and _estado(c, "M0001") == "pendiente"


def test_cambio_sin_motivo_advierte(repo, estudio_aprobado, plantilla):
    """Entrada: M0001 tenía previsto T-01 y la registró T-02 sin motivo.
    Esperado: RC18; el registro se conserva con advertencia e incluido en el conjunto."""
    v = valores_completos(estudio_aprobado)
    v["tecnico_real"] = None
    v.loc[0, "tecnico_real"] = "T-02"
    c = _cargar(repo, estudio_aprobado, diligenciar_plantilla(plantilla, v, resultados_completos()))
    assert "RC18" in _reglas(c) and _estado(c, "M0001") == "con_advertencia"


def test_hora_invalida_advierte(repo, estudio_aprobado, plantilla):
    """Entrada: «Hora real» = «9 y media».
    Esperado: RC19 como advertencia."""
    v = valores_completos(estudio_aprobado)
    v["hora_real"] = None
    v.loc[0, "hora_real"] = "9 y media"
    v.loc[1, "hora_real"] = "09:30"
    c = _cargar(repo, estudio_aprobado, diligenciar_plantilla(plantilla, v, resultados_completos()))
    assert _reglas(c) == ["RC19"] and _estado(c, "M0002") == "aceptado"


def test_resultados_agrupados(repo, estudio_aprobado, plantilla):
    """Entrada: inestabilidad del punto 1 sin valor y del punto 2 con texto «n/a».
    Esperado: RC20 y RC16 en la hoja Resultados_directos; ambos registros pendientes."""
    import pandas as pd
    res = pd.DataFrame({"registro_id": ["RD0002"], "valor": [None]})
    contenido = diligenciar_plantilla(plantilla, valores_completos(estudio_aprobado), res)
    contenido = editar_libro(contenido, lambda wb: wb["Resultados_directos"].cell(row=3, column=8, value="n/a"))
    c = _cargar(repo, estudio_aprobado, contenido)
    assert set(_reglas(c)) == {"RC20", "RC16"}
    assert c["evaluacion_inicial"]["conteos_resultados"]["pendientes"] == 2
