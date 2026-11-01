"""Servicios del flujo de datos: carga, preparación y aprobación.

La interfaz Streamlit solo llama estas funciones. Todas pueden usarse desde
Python sin abrir la aplicación (ver ejemplos/flujo_completo.py).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.auditoria.huella import ahora_iso, sha256_bytes
from src.calidad.evaluador import evaluar
from src.exportacion.salidas import construir_tablas, empaquetar, informe_incidencias_xlsx
from src.ingesta.lector import leer_plantilla, texto_original
from src.persistencia.repositorio import Repositorio
from src.transformaciones.catalogo import TRANSFORMACIONES, autorizadas_por_defecto


class ErrorFlujo(Exception):
    pass


def _diferencias(anterior: dict, actual: dict) -> list[dict]:
    """Celdas que cambiaron entre dos cargas de la misma versión (X08)."""
    def indice(carga):
        salida = {}
        for hoja, filas in (("Mediciones", carga["lectura"].get("filas_mediciones", [])),
                            ("Resultados_directos", carga["lectura"].get("filas_resultados", []))):
            clave_id = "medicion_id" if hoja == "Mediciones" else "registro_id"
            for f in filas:
                rid = texto_original(f["valores"].get(clave_id)).strip()
                for clave, valor in f["valores"].items():
                    salida[(hoja, rid, clave)] = texto_original(valor)
        return salida
    a, b = indice(anterior), indice(actual)
    cambios = []
    for clave in sorted(set(a) | set(b)):
        if a.get(clave, "") != b.get(clave, ""):
            cambios.append({"hoja": clave[0], "registro_id": clave[1], "columna": clave[2],
                            "antes": a.get(clave, ""), "despues": b.get(clave, "")})
    return cambios


def cargar_archivo(repo: Repositorio, codigo: str, contenido: bytes, nombre_archivo: str, usuario: str,
                   version_esperada: int | None = None) -> dict:
    """Recibe, conserva, identifica, lee y evalúa un archivo diligenciado."""
    sha = sha256_bytes(contenido)
    fecha = ahora_iso()
    carga_id = f"CARGA-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}-{sha[:8]}"
    lectura, estudio = leer_plantilla(contenido, nombre_archivo, codigo, version_esperada, repo.obtener_version)
    lectura_dict = lectura.to_dict()
    evaluacion = evaluar(lectura_dict, estudio, autorizadas_por_defecto()) if estudio else evaluar(lectura_dict, None, [])
    anteriores = [c for c in repo.listar_cargas(codigo)
                  if c["version_diseno"] == lectura.version_diseno and c["estado_archivo"] == "leido"]
    carga = {
        "carga_id": carga_id, "codigo_estudio": codigo, "fecha": fecha, "usuario": usuario or "sin identificar",
        "nombre_archivo": nombre_archivo, "sha256": sha, "tamano_bytes": len(contenido),
        "version_diseno": lectura.version_diseno, "estado_archivo": lectura.estado_archivo,
        "lectura": lectura_dict, "evaluacion_inicial": evaluacion, "conteos": evaluacion["conteos"],
        "carga_anterior": anteriores[-1]["carga_id"] if anteriores else None, "cambios_vs_anterior": [],
    }
    if anteriores and lectura.estado_archivo == "leido":
        carga["cambios_vs_anterior"] = _diferencias(repo.obtener_carga(codigo, anteriores[-1]["carga_id"]), carga)
    repo.guardar_carga(codigo, carga, contenido, Path(nombre_archivo).suffix or ".xlsx")
    repo.registrar_evento(codigo, usuario, "archivo_cargado", {
        "carga_id": carga_id, "archivo": nombre_archivo, "sha256": sha, "estado": lectura.estado_archivo,
        "conteos": evaluacion["conteos"]})
    return carga


def evaluar_carga(repo: Repositorio, codigo: str, carga_id: str, autorizadas: list[str], exclusiones: list[dict]) -> dict:
    carga = repo.obtener_carga(codigo, carga_id)
    estudio = None
    if carga["estado_archivo"] == "leido":
        estudio, _ = repo.obtener_version(codigo, carga["version_diseno"])
    return evaluar(carga["lectura"], estudio, autorizadas, exclusiones)


def preparar_conjunto(repo: Repositorio, codigo: str, carga_id: str, autorizadas: list[str],
                      exclusiones: list[dict], usuario: str) -> dict:
    """Aplica las transformaciones autorizadas y las exclusiones documentadas y genera la salida."""
    desconocidas = [t for t in autorizadas if t not in TRANSFORMACIONES]
    if desconocidas:
        raise ErrorFlujo(f"Transformaciones no reconocidas: {desconocidas}")
    for x in exclusiones:
        if not str(x.get("motivo", "")).strip():
            raise ErrorFlujo(f"La exclusión de {x.get('registro_id')} necesita un motivo verificable.")
    carga = repo.obtener_carga(codigo, carga_id)
    if carga["estado_archivo"] != "leido":
        raise ErrorFlujo("El archivo de esta carga fue rechazado: no se puede preparar.")
    estudio, huella = repo.obtener_version(codigo, carga["version_diseno"])
    evaluacion = evaluar(carga["lectura"], estudio, autorizadas, exclusiones)
    tablas = construir_tablas(evaluacion, estudio, carga)
    fecha = ahora_iso()
    prep_id = f"PREP-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:17]}"
    manifiesto_base = {
        "preparacion_id": prep_id, "fecha": fecha, "usuario": usuario or "sin identificar",
        "codigo_estudio": codigo, "version_diseno": estudio.version_diseno, "huella_diseno": huella,
        "carga_id": carga_id, "archivo_original": carga["nombre_archivo"], "sha256_original": carga["sha256"],
        "transformaciones_autorizadas": sorted(autorizadas), "exclusiones_manuales": exclusiones,
        "conteos": evaluacion["conteos"], "conteos_resultados": evaluacion.get("conteos_resultados", {}),
    }
    paquete, manifiesto = empaquetar(tablas, estudio, manifiesto_base)
    prep = {**manifiesto, "aprobada": False, "aprobada_por": "", "fecha_aprobacion": ""}
    repo.guardar_preparacion(codigo, prep, {
        "conjunto_preparado.zip": paquete,
        "informe_incidencias.xlsx": informe_incidencias_xlsx(evaluacion, carga),
    })
    repo.registrar_evento(codigo, usuario, "conjunto_preparado", {
        "preparacion_id": prep_id, "carga_id": carga_id, "autorizadas": sorted(autorizadas),
        "exclusiones": len(exclusiones), "conteos": evaluacion["conteos"]})
    return prep


def aprobar_conjunto(repo: Repositorio, codigo: str, prep_id: str, usuario: str) -> dict:
    """X07: confirma que el conjunto queda listo para el motor estadístico."""
    if not (usuario or "").strip():
        raise ErrorFlujo("Indica quién aprueba el conjunto de datos.")
    prep = repo.obtener_preparacion(codigo, prep_id)
    if prep["conteos"]["incluidos_en_preparado"] == 0:
        raise ErrorFlujo("El conjunto no tiene registros incluidos; no puede aprobarse.")
    prep.update({"aprobada": True, "aprobada_por": usuario, "fecha_aprobacion": ahora_iso()})
    repo.actualizar_preparacion(codigo, prep)
    repo.registrar_evento(codigo, usuario, "conjunto_aprobado", {"preparacion_id": prep_id})
    return prep
