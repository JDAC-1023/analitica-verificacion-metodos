"""Persistencia de estudios, versiones, cargas y preparaciones.

`RepositorioLocal` guarda todo en archivos (JSON + archivos originales) dentro
de una carpeta local excluida de Git. Implementa el contrato `Repositorio`, de
modo que más adelante pueda escribirse un `RepositorioSupabase` con los mismos
métodos sin modificar la lógica de validación, ingesta ni preparación.

Estructura en disco:

    datos_locales/
      estudios/<codigo>/
        borrador.json               configuración editable
        versiones/v001.json         diseños aprobados (inmutables)
        eventos.jsonl               bitácora de auditoría (solo se agrega)
        cargas/<carga_id>/
          original.<ext>            archivo tal como se recibió (nunca se modifica)
          carga.json                lectura, incidencias y estado
        preparaciones/<prep_id>/
          preparacion.json          parámetros y conteos de la preparación
          conjunto_preparado.zip    salida para el motor estadístico
        analisis/v001/
          config.json               configuración del análisis (contrato del motor)
          resultado.json            memoria de cálculo completa (inmutable una vez ejecutado)
          comentarios.json          retroalimentación humana por etapa (solo se agrega)
          informe_<fecha>.pdf       informes técnicos emitidos
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Protocol

from src.auditoria.huella import ahora_iso, huella_diseno, json_canonico
from src.modelos.estudio import Estudio

CARPETA_POR_DEFECTO = Path(__file__).resolve().parents[2] / "datos_locales"


class ErrorRepositorio(Exception):
    """Error de persistencia comprensible para el usuario."""


class Repositorio(Protocol):  # contrato que también deberá cumplir Supabase
    def listar_estudios(self) -> list[dict[str, Any]]: ...
    def crear_estudio(self, nombre: str, usuario: str) -> Estudio: ...
    def obtener_estudio(self, codigo: str) -> Estudio: ...
    def guardar_estudio(self, estudio: Estudio, usuario: str, detalle: str = "") -> None: ...
    def aprobar_version(self, estudio: Estudio, usuario: str) -> int: ...
    def obtener_version(self, codigo: str, version: int) -> tuple[Estudio, str]: ...
    def listar_versiones(self, codigo: str) -> list[dict[str, Any]]: ...
    def registrar_evento(self, codigo: str, usuario: str, accion: str, detalle: Any = None) -> None: ...
    def leer_eventos(self, codigo: str) -> list[dict[str, Any]]: ...
    def guardar_carga(self, codigo: str, carga: dict[str, Any], original: bytes, extension: str) -> None: ...
    def listar_cargas(self, codigo: str) -> list[dict[str, Any]]: ...
    def obtener_carga(self, codigo: str, carga_id: str) -> dict[str, Any]: ...
    def obtener_original(self, codigo: str, carga_id: str) -> bytes: ...
    def guardar_preparacion(self, codigo: str, prep: dict[str, Any], archivos: dict[str, bytes]) -> None: ...
    def listar_preparaciones(self, codigo: str) -> list[dict[str, Any]]: ...
    def obtener_preparacion(self, codigo: str, prep_id: str) -> dict[str, Any]: ...
    def obtener_archivo_preparacion(self, codigo: str, prep_id: str, nombre: str) -> bytes: ...
    def actualizar_preparacion(self, codigo: str, prep: dict[str, Any]) -> None: ...
    def guardar_config_analisis(self, codigo: str, config: dict[str, Any]) -> None: ...
    def guardar_resultado_analisis(self, codigo: str, version: int, resultado: dict[str, Any]) -> None: ...
    def listar_analisis(self, codigo: str) -> list[dict[str, Any]]: ...
    def obtener_analisis(self, codigo: str, version: int) -> dict[str, Any]: ...
    def agregar_comentario(self, codigo: str, version: int, etapa: str, texto: str, usuario: str) -> dict[str, Any]: ...
    def guardar_informe(self, codigo: str, version: int, contenido: bytes, metadatos: dict[str, Any]) -> str: ...
    def listar_informes(self, codigo: str) -> list[dict[str, Any]]: ...
    def obtener_informe(self, codigo: str, version: int, nombre: str) -> bytes: ...
    def clonar_estudio(self, codigo: str, nombre: str, usuario: str) -> Estudio: ...


_SEGURO = re.compile(r"^[A-Za-z0-9_.-]+$")


def _seguro(valor: str) -> str:
    """Evita rutas maliciosas o inválidas en nombres de carpeta."""
    if not valor or not _SEGURO.match(valor) or valor in (".", ".."):
        raise ErrorRepositorio(f"Identificador no válido: {valor!r}")
    return valor


def _escribir_json(ruta: Path, datos: Any) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    os.replace(temporal, ruta)  # escritura atómica


def _leer_json(ruta: Path) -> Any:
    if not ruta.exists():
        raise ErrorRepositorio(f"No existe: {ruta.name}")
    return json.loads(ruta.read_text(encoding="utf-8"))


class RepositorioLocal:
    def __init__(self, carpeta: str | Path | None = None):
        self.raiz = Path(carpeta or os.environ.get("AVM_DATOS_DIR") or CARPETA_POR_DEFECTO)
        (self.raiz / "estudios").mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    def _dir(self, codigo: str) -> Path:
        return self.raiz / "estudios" / _seguro(codigo)

    # ------------------------------------------------------------------ estudios
    def listar_estudios(self) -> list[dict[str, Any]]:
        resumen = []
        for carpeta in sorted((self.raiz / "estudios").iterdir()):
            ruta = carpeta / "borrador.json"
            if not ruta.exists():
                continue
            e = Estudio.from_dict(_leer_json(ruta))
            resumen.append({
                "codigo": e.codigo, "nombre": e.nombre, "tipo": e.tipo, "metodo": e.metodo,
                "version_diseno": e.version_diseno, "estado": e.estado,
                "mediciones": len(e.plan), "actualizado_en": e.actualizado_en,
                "cargas": len(list((carpeta / "cargas").glob("*/carga.json"))),
            })
        return resumen

    def _siguiente_codigo(self) -> str:
        numeros = [int(p.name.split("-")[1]) for p in (self.raiz / "estudios").glob("EST-*")
                   if p.name.split("-")[1].isdigit()]
        return f"EST-{(max(numeros) + 1 if numeros else 1):04d}"

    def crear_estudio(self, nombre: str, usuario: str) -> Estudio:
        if not nombre.strip():
            raise ErrorRepositorio("El estudio necesita un nombre.")
        codigo = self._siguiente_codigo()  # E02: automático y único
        marca = ahora_iso()
        e = Estudio(codigo=codigo, nombre=nombre.strip(), creado_en=marca, actualizado_en=marca)
        _escribir_json(self._dir(codigo) / "borrador.json", e.to_dict())
        self.registrar_evento(codigo, usuario, "estudio_creado", {"nombre": e.nombre})
        return e

    def obtener_estudio(self, codigo: str) -> Estudio:
        return Estudio.from_dict(_leer_json(self._dir(codigo) / "borrador.json"))

    def guardar_estudio(self, estudio: Estudio, usuario: str, detalle: str = "") -> None:
        anterior = None
        ruta = self._dir(estudio.codigo) / "borrador.json"
        if ruta.exists():
            anterior = Estudio.from_dict(_leer_json(ruta))
        # Si había una versión aprobada y el diseño cambió, vuelve a borrador (PD13, provisional).
        if anterior and anterior.estado == "aprobado" and \
                huella_diseno(anterior.to_dict()) != huella_diseno(estudio.to_dict()):
            estudio.estado = "borrador"
        estudio.actualizado_en = ahora_iso()
        _escribir_json(ruta, estudio.to_dict())
        self.registrar_evento(estudio.codigo, usuario, "estudio_guardado", detalle or None)

    def aprobar_version(self, estudio: Estudio, usuario: str) -> int:
        """Congela el diseño actual como una nueva versión inmutable (P05)."""
        versiones = self.listar_versiones(estudio.codigo)
        huella = huella_diseno(estudio.to_dict())
        if versiones and versiones[-1]["huella_diseno"] == huella:
            estudio.version_diseno = versiones[-1]["version"]
        else:
            estudio.version_diseno = (versiones[-1]["version"] + 1) if versiones else 1
        estudio.estado = "aprobado"
        estudio.aprobado_por = usuario
        estudio.fecha_aprobacion = ahora_iso()
        estudio.actualizado_en = estudio.fecha_aprobacion
        ruta_version = self._dir(estudio.codigo) / "versiones" / f"v{estudio.version_diseno:03d}.json"
        if not ruta_version.exists():
            _escribir_json(ruta_version, {"huella_diseno": huella, "estudio": estudio.to_dict()})
        _escribir_json(self._dir(estudio.codigo) / "borrador.json", estudio.to_dict())
        self.registrar_evento(estudio.codigo, usuario, "diseno_aprobado",
                              {"version": estudio.version_diseno, "huella": huella})
        return estudio.version_diseno

    def obtener_version(self, codigo: str, version: int) -> tuple[Estudio, str]:
        datos = _leer_json(self._dir(codigo) / "versiones" / f"v{int(version):03d}.json")
        return Estudio.from_dict(datos["estudio"]), datos["huella_diseno"]

    def listar_versiones(self, codigo: str) -> list[dict[str, Any]]:
        salida = []
        for ruta in sorted((self._dir(codigo) / "versiones").glob("v*.json")):
            datos = _leer_json(ruta)
            e = datos["estudio"]
            salida.append({"version": e["version_diseno"], "huella_diseno": datos["huella_diseno"],
                           "aprobado_por": e.get("aprobado_por", ""), "fecha_aprobacion": e.get("fecha_aprobacion", ""),
                           "mediciones": len(e.get("plan", []))})
        return salida

    # ------------------------------------------------------------------ auditoría
    def registrar_evento(self, codigo: str, usuario: str, accion: str, detalle: Any = None) -> None:
        ruta = self._dir(codigo) / "eventos.jsonl"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        evento = {"fecha": ahora_iso(), "usuario": usuario or "sin identificar", "accion": accion, "detalle": detalle}
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json_canonico(evento) + "\n")

    def leer_eventos(self, codigo: str) -> list[dict[str, Any]]:
        ruta = self._dir(codigo) / "eventos.jsonl"
        if not ruta.exists():
            return []
        return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines() if l.strip()]

    # ------------------------------------------------------------------ cargas
    def guardar_carga(self, codigo: str, carga: dict[str, Any], original: bytes, extension: str) -> None:
        carpeta = self._dir(codigo) / "cargas" / _seguro(carga["carga_id"])
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta_original = carpeta / f"original.{_seguro(extension.lstrip('.').lower() or 'bin')}"
        if not ruta_original.exists():  # el original nunca se sobrescribe
            ruta_original.write_bytes(original)
        carga["archivo_guardado"] = ruta_original.name
        _escribir_json(carpeta / "carga.json", carga)

    def listar_cargas(self, codigo: str) -> list[dict[str, Any]]:
        salida = []
        for ruta in sorted((self._dir(codigo) / "cargas").glob("*/carga.json")):
            c = _leer_json(ruta)
            salida.append({k: c.get(k) for k in (
                "carga_id", "fecha", "usuario", "nombre_archivo", "version_diseno", "estado_archivo",
                "sha256", "conteos", "carga_anterior")})
        return sorted(salida, key=lambda c: c["fecha"] or "")

    def obtener_carga(self, codigo: str, carga_id: str) -> dict[str, Any]:
        return _leer_json(self._dir(codigo) / "cargas" / _seguro(carga_id) / "carga.json")

    def obtener_original(self, codigo: str, carga_id: str) -> bytes:
        carpeta = self._dir(codigo) / "cargas" / _seguro(carga_id)
        carga = _leer_json(carpeta / "carga.json")
        return (carpeta / carga["archivo_guardado"]).read_bytes()

    # ------------------------------------------------------------------ preparaciones
    def guardar_preparacion(self, codigo: str, prep: dict[str, Any], archivos: dict[str, bytes]) -> None:
        carpeta = self._dir(codigo) / "preparaciones" / _seguro(prep["preparacion_id"])
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, contenido in archivos.items():
            (carpeta / _seguro(nombre)).write_bytes(contenido)
        _escribir_json(carpeta / "preparacion.json", prep)

    def listar_preparaciones(self, codigo: str) -> list[dict[str, Any]]:
        salida = [_leer_json(r) for r in (self._dir(codigo) / "preparaciones").glob("*/preparacion.json")]
        return sorted(salida, key=lambda p: p.get("fecha", ""))

    def obtener_preparacion(self, codigo: str, prep_id: str) -> dict[str, Any]:
        return _leer_json(self._dir(codigo) / "preparaciones" / _seguro(prep_id) / "preparacion.json")

    def obtener_archivo_preparacion(self, codigo: str, prep_id: str, nombre: str) -> bytes:
        return (self._dir(codigo) / "preparaciones" / _seguro(prep_id) / _seguro(nombre)).read_bytes()

    def actualizar_preparacion(self, codigo: str, prep: dict[str, Any]) -> None:
        _escribir_json(self._dir(codigo) / "preparaciones" / _seguro(prep["preparacion_id"]) / "preparacion.json", prep)

    # ------------------------------------------------------------------ análisis estadístico
    def _dir_analisis(self, codigo: str, version: int) -> Path:
        return self._dir(codigo) / "analisis" / f"v{int(version):03d}"

    def guardar_config_analisis(self, codigo: str, config: dict[str, Any]) -> None:
        carpeta = self._dir_analisis(codigo, config["version"])
        if (carpeta / "resultado.json").exists():
            raise ErrorRepositorio(f"La versión {config['version']} del análisis ya se ejecutó y es inmutable: crea una nueva versión.")
        _escribir_json(carpeta / "config.json", config)

    def guardar_resultado_analisis(self, codigo: str, version: int, resultado: dict[str, Any]) -> None:
        carpeta = self._dir_analisis(codigo, version)
        if (carpeta / "resultado.json").exists():
            raise ErrorRepositorio(f"La versión {version} del análisis ya tiene resultado.")
        _escribir_json(carpeta / "resultado.json", resultado)

    def listar_analisis(self, codigo: str) -> list[dict[str, Any]]:
        salida = []
        for ruta in sorted((self._dir(codigo) / "analisis").glob("v*/config.json")):
            c = _leer_json(ruta)
            res = ruta.parent / "resultado.json"
            final = _leer_json(res).get("conclusion_final", {}) if res.exists() else {}
            salida.append({"version": c["version"], "padre": c.get("padre"), "motivo_cambio": c.get("motivo_cambio", ""),
                           "objeto": c.get("objeto_id", ""), "preparacion_id": c.get("preparacion_id", ""),
                           "creado_en": c.get("creado_en", ""), "elaborado_por": c.get("elaborado_por", ""),
                           "ejecutado": res.exists(), "estado_final": final.get("estado", "")})
        return salida

    def obtener_analisis(self, codigo: str, version: int) -> dict[str, Any]:
        carpeta = self._dir_analisis(codigo, version)
        res = carpeta / "resultado.json"
        com = carpeta / "comentarios.json"
        return {"config": _leer_json(carpeta / "config.json"),
                "resultado": _leer_json(res) if res.exists() else None,
                "comentarios": _leer_json(com) if com.exists() else []}

    def agregar_comentario(self, codigo: str, version: int, etapa: str, texto: str, usuario: str) -> dict[str, Any]:
        if not texto.strip():
            raise ErrorRepositorio("El comentario está vacío.")
        ruta = self._dir_analisis(codigo, version) / "comentarios.json"
        lista = _leer_json(ruta) if ruta.exists() else []
        item = {"id": f"COM-{len(lista) + 1:03d}", "etapa": etapa, "texto": texto.strip(),
                "usuario": usuario or "sin identificar", "fecha": ahora_iso()}
        lista.append(item)
        _escribir_json(ruta, lista)
        self.registrar_evento(codigo, usuario, "comentario_analisis", {"version": version, "etapa": etapa, "id": item["id"]})
        return item

    def guardar_informe(self, codigo: str, version: int, contenido: bytes, metadatos: dict[str, Any]) -> str:
        carpeta = self._dir_analisis(codigo, version)
        nombre = f"informe_{ahora_iso().replace(':', '').replace('-', '')[:15]}.pdf"
        (carpeta / nombre).write_bytes(contenido)
        _escribir_json(carpeta / (nombre + ".json"), {**metadatos, "archivo": nombre, "version": version})
        self.registrar_evento(codigo, metadatos.get("emitido_por", ""), "informe_emitido",
                              {"version": version, "archivo": nombre, "sha256": metadatos.get("sha256")})
        return nombre

    def listar_informes(self, codigo: str) -> list[dict[str, Any]]:
        return sorted((_leer_json(r) for r in (self._dir(codigo) / "analisis").glob("v*/informe_*.pdf.json")),
                      key=lambda x: x.get("fecha", ""))

    def obtener_informe(self, codigo: str, version: int, nombre: str) -> bytes:
        return (self._dir_analisis(codigo, version) / _seguro(nombre)).read_bytes()

    # ------------------------------------------------------------------ rediseño
    def clonar_estudio(self, codigo: str, nombre: str, usuario: str) -> Estudio:
        """Crea un estudio nuevo con el diseño del original, en borrador, sin cargas ni análisis."""
        original = self.obtener_estudio(codigo)
        nuevo = self.crear_estudio(nombre or f"{original.nombre} (versión 2)", usuario)
        datos = original.to_dict()
        datos.update({"codigo": nuevo.codigo, "nombre": nuevo.nombre, "estado": "borrador", "version_diseno": 0,
                      "aprobado_por": "", "fecha_aprobacion": "", "creado_en": nuevo.creado_en,
                      "derivado_de": f"{codigo} v{original.version_diseno}", "paso_asistente": 1})
        clon = Estudio.from_dict(datos)
        self.guardar_estudio(clon, usuario, f"Clonado desde {codigo}")
        self.registrar_evento(codigo, usuario, "estudio_clonado", {"nuevo": clon.codigo})
        return clon
