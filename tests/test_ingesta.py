"""Lectura, identificación y conservación del archivo original."""

from src.auditoria.huella import sha256_bytes
from src.modelos.estudio import Punto
from src.plantillas.generador import generar_plantilla
from src.servicios.flujo import cargar_archivo
from tests.conftest import columna, editar_libro


def _reglas(carga):
    return [i["regla"] for i in carga["evaluacion_inicial"]["incidencias"]]


def test_lectura_correcta(repo, estudio_aprobado, archivo_completo):
    """Entrada: plantilla diligenciada completa (16 mediciones y 2 resultados agrupados).
    Esperado: archivo leído, 16 recibidos, 16 aceptados, conteos conciliados, sin incidencias."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "completo.xlsx", "ana")
    assert c["estado_archivo"] == "leido" and _reglas(c) == []
    assert c["conteos"]["recibidos"] == 16 and c["conteos"]["aceptados"] == 16 and c["conteos"]["conciliado"]
    assert c["evaluacion_inicial"]["conteos_resultados"]["aceptados"] == 2


def test_conservacion_del_archivo_original(repo, estudio_aprobado, archivo_completo):
    """Entrada: archivo cargado.
    Esperado: el original se guarda byte a byte; su SHA-256 coincide; queda un evento de auditoría con usuario y huella."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, archivo_completo, "completo.xlsx", "ana")
    original = repo.obtener_original(estudio_aprobado.codigo, c["carga_id"])
    assert original == archivo_completo and c["sha256"] == sha256_bytes(archivo_completo)
    evento = repo.leer_eventos(estudio_aprobado.codigo)[-1]
    assert evento["accion"] == "archivo_cargado" and evento["usuario"] == "ana" and evento["detalle"]["sha256"] == c["sha256"]


def test_archivo_no_excel_se_rechaza(repo, estudio_aprobado):
    """Entrada: un archivo de texto con extensión .xlsx.
    Esperado: rechazado por RC01 y el original igualmente conservado."""
    c = cargar_archivo(repo, estudio_aprobado.codigo, b"esto no es excel", "falso.xlsx", "ana")
    assert c["estado_archivo"] == "rechazado" and _reglas(c) == ["RC01"]
    assert repo.obtener_original(estudio_aprobado.codigo, c["carga_id"]) == b"esto no es excel"


def test_hoja_mediciones_ausente_rechaza(repo, estudio_aprobado, archivo_completo):
    """Entrada: archivo sin la hoja Mediciones (archivo incompleto).
    Esperado: rechazado por RC02."""
    roto = editar_libro(archivo_completo, lambda wb: wb.remove(wb["Mediciones"]))
    c = cargar_archivo(repo, estudio_aprobado.codigo, roto, "incompleto.xlsx", "ana")
    assert c["estado_archivo"] == "rechazado" and _reglas(c) == ["RC02"]


def test_formato_de_plantilla_incompatible(repo, estudio_aprobado, archivo_completo):
    """Entrada: _control con formato_plantilla = PLT-0.9.
    Esperado: rechazado por RC03."""
    roto = editar_libro(archivo_completo, lambda wb: wb["_control"].cell(row=1, column=2, value="PLT-0.9"))
    assert _reglas(cargar_archivo(repo, estudio_aprobado.codigo, roto, "x.xlsx", "ana")) == ["RC03"]


def test_archivo_de_otro_estudio(repo, estudio_aprobado, archivo_completo):
    """Entrada: archivo del estudio EST-0001 cargado en otro estudio.
    Esperado: rechazado por RC04."""
    otro = repo.crear_estudio("Otro", "ana")
    c = cargar_archivo(repo, otro.codigo, archivo_completo, "x.xlsx", "ana")
    assert c["estado_archivo"] == "rechazado" and _reglas(c) == ["RC04"]


def test_version_incompatible(repo, estudio_aprobado, archivo_completo):
    """Entrada: plantilla de la versión 1; el diseño se modifica y se aprueba la versión 2; se carga esperando la versión 2.
    Esperado: rechazado por RC05. Además, una huella alterada también se rechaza."""
    e = estudio_aprobado
    e.puntos.append(Punto("PT-03", "MAG-01", 60.0, "°C"))
    repo.guardar_estudio(e, "ana")
    repo.aprobar_version(e, "ana")
    c = cargar_archivo(repo, e.codigo, archivo_completo, "v1.xlsx", "ana", version_esperada=2)
    assert c["estado_archivo"] == "rechazado" and _reglas(c) == ["RC05"]
    alterado = editar_libro(archivo_completo, lambda wb: wb["_control"].cell(row=4, column=2, value="0" * 64))
    assert _reglas(cargar_archivo(repo, e.codigo, alterado, "h.xlsx", "ana")) == ["RC05"]


def test_unidad_modificada_en_encabezado(repo, estudio_aprobado, archivo_completo):
    """Entrada: el encabezado «Indicación del equipo [°C]» se cambia a «Indicación del equipo [K]».
    Esperado: rechazado por RC06 (campos o unidades inconsistentes)."""
    def cambiar(wb):
        j = columna(wb, "Indicación del equipo [°C]")
        wb["Mediciones"].cell(row=1, column=j, value="Indicación del equipo [K] *")
    c = cargar_archivo(repo, estudio_aprobado.codigo, editar_libro(archivo_completo, cambiar), "u.xlsx", "ana")
    assert c["estado_archivo"] == "rechazado" and "RC06" in _reglas(c)


def test_columna_adicional_advierte(repo, estudio_aprobado, archivo_completo):
    """Entrada: el usuario agrega una columna «Notas extra».
    Esperado: el archivo se lee, se informa RC07 y los registros se aceptan."""
    def agregar(wb):
        ws = wb["Mediciones"]
        ws.cell(row=1, column=ws.max_column + 1, value="Notas extra")
        ws.cell(row=2, column=ws.max_column, value="algo")
    c = cargar_archivo(repo, estudio_aprobado.codigo, editar_libro(archivo_completo, agregar), "e.xlsx", "ana")
    assert c["estado_archivo"] == "leido" and _reglas(c) == ["RC07"] and c["conteos"]["aceptados"] == 16


def test_plantilla_reordenada_se_lee(repo, estudio_aprobado, archivo_completo):
    """Entrada: el usuario ordena las filas de Mediciones de forma descendente.
    Esperado: las mediciones se identifican por su ID y no por su posición: 16 aceptadas."""
    def invertir(wb):
        ws = wb["Mediciones"]
        filas = [[c.value for c in fila] for fila in ws.iter_rows(min_row=2)]
        for i, valores in enumerate(reversed(filas), start=2):
            for j, v in enumerate(valores, start=1):
                ws.cell(row=i, column=j, value=v)
    c = cargar_archivo(repo, estudio_aprobado.codigo, editar_libro(archivo_completo, invertir), "r.xlsx", "ana")
    assert c["conteos"]["aceptados"] == 16
