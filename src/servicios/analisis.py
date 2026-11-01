"""Servicio del análisis estadístico: configurar, ejecutar, versionar y rediseñar.

Reglas de trazabilidad:
  - el análisis solo se ejecuta sobre un conjunto preparado APROBADO;
  - una versión ejecutada es inmutable; cualquier cambio crea la versión N+1
    con su versión padre, motivo y diferencias registrados en la bitácora;
  - una exclusión exige motivo y responsable y produce una versión derivada.
"""

from __future__ import annotations

from src.auditoria.huella import ahora_iso
from src.exportacion.lector_salida import cargar_conjunto
from src.modelos.estudio import Estudio
from src.motor.configuracion import ConfiguracionAnalisis, Exclusion, diferencias
from src.motor.motor import ejecutar
from src.persistencia.repositorio import Repositorio


class ErrorAnalisis(Exception):
    pass


def datos_de_preparacion(repo: Repositorio, codigo: str, prep_id: str) -> tuple[dict, Estudio, dict]:
    prep = repo.obtener_preparacion(codigo, prep_id)
    tablas = cargar_conjunto(repo.obtener_archivo_preparacion(codigo, prep_id, "conjunto_preparado.zip"))
    estudio, _ = repo.obtener_version(codigo, prep["version_diseno"])
    return tablas, estudio, prep


def siguiente_version(repo: Repositorio, codigo: str) -> int:
    vs = repo.listar_analisis(codigo)
    return (max(v["version"] for v in vs) + 1) if vs else 1


def nueva_configuracion(repo: Repositorio, codigo: str, prep_id: str, usuario: str) -> ConfiguracionAnalisis:
    return ConfiguracionAnalisis(codigo_estudio=codigo, version=siguiente_version(repo, codigo), preparacion_id=prep_id,
                                 elaborado_por=usuario, creado_en=ahora_iso())


def guardar_configuracion(repo: Repositorio, cfg: ConfiguracionAnalisis, usuario: str) -> None:
    repo.guardar_config_analisis(cfg.codigo_estudio, cfg.to_dict())
    repo.registrar_evento(cfg.codigo_estudio, usuario, "analisis_configurado", {"version": cfg.version})


def ejecutar_analisis(repo: Repositorio, cfg: ConfiguracionAnalisis, usuario: str) -> dict:
    if not cfg.preparacion_id:
        raise ErrorAnalisis("Elige el conjunto preparado que se va a analizar.")
    if not cfg.objeto_id:
        raise ErrorAnalisis("Elige el dato o resultado que se va a analizar.")
    tablas, estudio, prep = datos_de_preparacion(repo, cfg.codigo_estudio, cfg.preparacion_id)
    if not prep.get("aprobada"):
        raise ErrorAnalisis("El conjunto preparado no está aprobado: apruébalo en «Datos preparados» antes de analizar.")
    cfg.elaborado_por = cfg.elaborado_por or usuario
    guardar_configuracion(repo, cfg, usuario)
    meta = {"preparacion_id": prep["preparacion_id"], "carga_id": prep.get("carga_id"), "sha256_original": prep.get("sha256_original"),
            "archivo_original": prep.get("archivo_original"), "huella_diseno": prep.get("huella_diseno"),
            "conjunto_aprobado_por": prep.get("aprobada_por"), "ejecutado_por": usuario}
    resultado = ejecutar(tablas, estudio, cfg, meta)
    repo.guardar_resultado_analisis(cfg.codigo_estudio, cfg.version, resultado)
    repo.registrar_evento(cfg.codigo_estudio, usuario, "analisis_ejecutado",
                          {"version": cfg.version, "huella_resultado": resultado["meta"]["huella_resultado"],
                           "estado_final": resultado["conclusion_final"]["estado"]})
    return resultado


def derivar_version(repo: Repositorio, codigo: str, base: int, motivo: str, usuario: str,
                    cambios: dict | None = None, exclusiones: list[Exclusion] | None = None) -> ConfiguracionAnalisis:
    """Rediseño: clona la configuración de la versión `base` en una versión nueva (sin ejecutar)."""
    if not motivo.strip():
        raise ErrorAnalisis("Indica el motivo del cambio: queda en el historial.")
    anterior = ConfiguracionAnalisis.from_dict(repo.obtener_analisis(codigo, base)["config"])
    datos = anterior.to_dict()
    datos.update(cambios or {})
    nueva = ConfiguracionAnalisis.from_dict(datos)
    for x in exclusiones or []:
        if not x.motivo.strip() or not x.responsable.strip():
            raise ErrorAnalisis(f"La exclusión de {x.medicion_id} necesita motivo técnico y responsable.")
        x.fecha = x.fecha or ahora_iso()
        if x.medicion_id not in {e.medicion_id for e in nueva.exclusiones}:
            nueva.exclusiones.append(x)
    nueva.version = siguiente_version(repo, codigo)
    nueva.padre = base
    nueva.motivo_cambio = motivo.strip()
    nueva.creado_en = ahora_iso()
    nueva.elaborado_por = usuario or anterior.elaborado_por
    repo.guardar_config_analisis(codigo, nueva.to_dict())
    repo.registrar_evento(codigo, usuario, "analisis_version_derivada",
                          {"version": nueva.version, "padre": base, "motivo": nueva.motivo_cambio,
                           "cambios": diferencias(anterior, nueva)})
    return nueva


def historial(repo: Repositorio, codigo: str) -> list[dict]:
    """Versiones del análisis con sus diferencias respecto a la versión padre."""
    salida = []
    for v in repo.listar_analisis(codigo):
        fila = dict(v)
        if v["padre"]:
            a = ConfiguracionAnalisis.from_dict(repo.obtener_analisis(codigo, v["padre"])["config"])
            b = ConfiguracionAnalisis.from_dict(repo.obtener_analisis(codigo, v["version"])["config"])
            fila["cambios"] = diferencias(a, b)
        else:
            fila["cambios"] = []
        salida.append(fila)
    return salida


def bitacora_analisis(repo: Repositorio, codigo: str) -> list[dict]:
    acciones = {"analisis_configurado", "analisis_ejecutado", "analisis_version_derivada", "comentario_analisis",
                "informe_emitido", "conjunto_preparado", "conjunto_aprobado", "diseno_aprobado", "archivo_cargado",
                "estudio_clonado"}
    return [e for e in repo.leer_eventos(codigo) if e["accion"] in acciones]
