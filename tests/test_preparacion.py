"""Transformaciones, exclusiones, exportación, reproducibilidad y aprobación."""

import io
import json
import zipfile

import pytest

from src.exportacion.lector_salida import ErrorConjunto, cargar_conjunto
from src.plantillas.diligenciar import diligenciar_plantilla
from src.servicios.flujo import ErrorFlujo, aprobar_conjunto, cargar_archivo, preparar_conjunto
from tests.conftest import resultados_completos, valores_completos


def _zip(repo, e, prep):
    return repo.obtener_archivo_preparacion(e.codigo, prep["preparacion_id"], "conjunto_preparado.zip")


def test_transformaciones_permitidas(repo, estudio_aprobado, plantilla):
    """Entrada: «20,5» con coma decimal y « 20.25 » (texto con espacios) en Indicación; preparación con TR01, TR02 y TR03.
    Esperado: ambos registros normalizados; valores 20.5 y 20.25; se conservan el original y la transformación aplicada."""
    v = valores_completos(estudio_aprobado)
    v.loc[0, "V-01"] = "20,5"
    v.loc[1, "V-01"] = " 20.25 "
    c = cargar_archivo(repo, estudio_aprobado.codigo, diligenciar_plantilla(plantilla, v, resultados_completos()), "t.xlsx", "ana")
    assert c["conteos"]["pendientes"] == 1  # «20,5» sin TR02 autorizada
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01", "TR02", "TR03"], [], "ana")
    datos = cargar_conjunto(_zip(repo, estudio_aprobado, prep))
    val = datos["valores"].set_index(["medicion_id", "variable_id"])
    assert val.loc[("M0001", "V-01"), "valor_numerico"] == 20.5 and val.loc[("M0001", "V-01"), "valor_original"] == "20,5"
    assert val.loc[("M0001", "V-01"), "transformaciones"] == "TR02"
    assert val.loc[("M0002", "V-01"), "valor_numerico"] == 20.25 and "TR01" in val.loc[("M0002", "V-01"), "transformaciones"]
    assert prep["conteos"]["normalizados"] == 2 and len(datos["transformaciones"]) >= 2


def test_exclusion_documentada(repo, estudio_aprobado, archivo_completo):
    """Entrada: exclusión manual de M0007 con motivo; luego un intento sin motivo.
    Esperado: M0007 fuera del conjunto y listada en exclusiones.csv con su motivo; sin motivo se rechaza la preparación."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    exclusion = [{"registro_id": "M0007", "motivo": "Falla del sensor anotada en bitácora", "usuario": "ana"}]
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], exclusion, "ana")
    datos = cargar_conjunto(_zip(repo, estudio_aprobado, prep))
    assert "M0007" not in set(datos["mediciones"]["medicion_id"])
    fila = datos["exclusiones"].iloc[0]
    assert fila["registro_id"] == "M0007" and fila["origen"] == "manual" and "Falla del sensor" in fila["motivo"]
    assert prep["conteos"]["excluidos"] == 1 and prep["conteos"]["conciliado"]
    with pytest.raises(ErrorFlujo):
        preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [{"registro_id": "M0008", "motivo": " "}], "ana")


def test_valores_sin_redondeo_ni_cambio_de_signo(repo, estudio_aprobado, archivo_completo):
    """Entrada: valores con 12 decimales y negativos (−1.234567890123).
    Esperado: el conjunto preparado conserva exactamente el valor y el signo; los faltantes opcionales quedan vacíos, no en cero."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [], "ana")
    datos = cargar_conjunto(_zip(repo, estudio_aprobado, prep))
    val = datos["valores"].set_index(["medicion_id", "variable_id"])
    assert val.loc[("M0001", "V-03"), "valor_numerico"] == -1.234567890123
    assert (datos["resultados_valores"]["valor"] == [0.021, -0.013]).all()


def test_exportacion_del_conjunto_preparado(repo, estudio_aprobado, archivo_completo):
    """Entrada: preparación de un archivo completo.
    Esperado: ZIP con las tablas documentadas; 16 mediciones; 48 valores (16 × 3 datos); manifiesto con conteos y huellas;
    la vista de análisis tiene una columna por condición."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [], "ana")
    datos = cargar_conjunto(_zip(repo, estudio_aprobado, prep))
    esperadas = {"observaciones_analisis", "mediciones", "valores", "niveles_factores", "resultados_valores",
                 "definiciones_variables", "definiciones_resultados", "criterios", "factores", "puntos", "recursos",
                 "registros_estado", "incidencias", "transformaciones", "exclusiones"}
    assert esperadas <= set(datos)
    assert len(datos["mediciones"]) == 16 and len(datos["valores"]) == 48
    assert {"factor:Técnico", "factor:Día"} <= set(datos["observaciones_analisis"].columns)
    assert datos["manifiesto"]["conteos"]["incluidos_en_preparado"] == 16
    assert datos["manifiesto"]["sha256_original"] == c["sha256"]
    assert set(datos["definiciones_resultados"]["id"]) == {"R-01", "R-02"}


def test_reproducibilidad_de_la_salida(repo, estudio_aprobado, archivo_completo):
    """Entrada: la misma carga se prepara dos veces con los mismos parámetros.
    Esperado: las huellas SHA-256 de todos los CSV son idénticas (salida reproducible)."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    p1 = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01", "TR03"], [], "ana")
    p2 = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR03", "TR01"], [], "ana")
    assert p1["preparacion_id"] != p2["preparacion_id"]
    assert p1["huellas_archivos"] == p2["huellas_archivos"]


def test_integridad_detecta_modificacion(repo, estudio_aprobado, archivo_completo):
    """Entrada: se altera valores.csv dentro del ZIP preparado.
    Esperado: la lectura con verificación detecta que el conjunto fue modificado."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [], "ana")
    original = zipfile.ZipFile(io.BytesIO(_zip(repo, estudio_aprobado, prep)))
    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w") as z:
        for nombre in original.namelist():
            contenido = original.read(nombre)
            z.writestr(nombre, contenido.replace(b"20.0", b"21.0") if nombre == "valores.csv" else contenido)
    with pytest.raises(ErrorConjunto):
        cargar_conjunto(salida.getvalue())


def test_segunda_carga_registra_cambios(repo, estudio_aprobado, plantilla):
    """Entrada: primera carga con M0003 sin valor del patrón; segunda carga corregida.
    Esperado: la segunda carga referencia a la primera, lista la celda que cambió y no borra la primera carga."""
    v = valores_completos(estudio_aprobado)
    v.loc[2, "V-02"] = None
    c1 = cargar_archivo(repo, estudio_aprobado.codigo, diligenciar_plantilla(plantilla, v, resultados_completos()), "v1.xlsx", "ana")
    c2 = cargar_archivo(repo, estudio_aprobado.codigo, diligenciar_plantilla(plantilla, valores_completos(estudio_aprobado), resultados_completos()), "v2.xlsx", "ana")
    assert c2["carga_anterior"] == c1["carga_id"]
    assert c2["cambios_vs_anterior"] == [{"hoja": "Mediciones", "registro_id": "M0003", "columna": "var:V-02", "antes": "", "despues": "20"}]
    assert len(repo.listar_cargas(estudio_aprobado.codigo)) == 2


def test_aprobacion_del_conjunto(repo, estudio_aprobado, archivo_completo):
    """Entrada: conjunto preparado aprobado por «ana».
    Esperado: queda marcado como aprobado con usuario y fecha, y se registra el evento."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "x.xlsx", "ana")
    prep = preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], ["TR01"], [], "ana")
    aprobado = aprobar_conjunto(repo, estudio_aprobado.codigo, prep["preparacion_id"], "ana")
    assert aprobado["aprobada"] and aprobado["aprobada_por"] == "ana"
    assert repo.leer_eventos(estudio_aprobado.codigo)[-1]["accion"] == "conjunto_aprobado"


def test_archivo_rechazado_no_se_prepara(repo, estudio_aprobado):
    """Entrada: carga rechazada (archivo no Excel).
    Esperado: la preparación se niega con un mensaje claro."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, b"no", "x.xlsx", "ana")
    with pytest.raises(ErrorFlujo):
        preparar_conjunto(repo, estudio_aprobado.codigo, c["carga_id"], [], [], "ana")
