"""Crea estudios completos a partir de plantillas YA diligenciadas (bases de prueba).

Para cada archivo:
  1. reconstruye el diseño desde las hojas «Estudio», «Definiciones», «Mediciones» y «_control»
     (mismos puntos, técnicos, patrones, IBC, condiciones, datos, resultados y plan, con los mismos ID);
  2. crea un estudio nuevo y aprueba su diseño;
  3. genera su plantilla y copia en ella los valores del archivo, sin modificarlos;
  4. carga, prepara y aprueba el conjunto de datos (queda listo para el motor);
  5. deja configurado y ejecutado el análisis v1 de la corrección SIN criterios
     (resultado «CALCULADO_SIN_EVALUACION»): los límites los define el laboratorio.

No inventa criterios ni fórmulas. Los archivos originales se conservan como cargas.
"""

from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from src.modelos.estudio import (Estudio, Factor, Magnitud, MedicionPlanificada, Punto, Recurso, ResultadoInteres,
                                 Variable)
from src.motor.configuracion import CaracteristicaConfig
from src.persistencia.repositorio import Repositorio
from src.plantillas.diligenciar import diligenciar_plantilla
from src.plantillas.generador import generar_plantilla
from src.servicios.analisis import ejecutar_analisis, nueva_configuracion
from src.servicios.flujo import aprobar_conjunto, cargar_archivo, preparar_conjunto

CARPETA_PRUEBAS = Path(__file__).resolve().parents[2] / "data" / "estudios_prueba"


class ErrorImportacion(Exception):
    pass


def _hoja_clave_valor(ws) -> dict:
    return {str(r[0]): r[1] for r in ws.iter_rows(values_only=True) if r and r[0] is not None}


def _recursos(texto: str, tipo: str) -> list[Recurso]:
    salida = []
    for parte in [p.strip() for p in str(texto or "").split(";") if p.strip()]:
        codigo, _, nombre = parte.partition(" ")
        salida.append(Recurso(codigo.strip(), nombre.strip(), tipo))
    return salida


def _ibc(texto: str, magnitud_id: str) -> list[Recurso]:
    if not texto:
        return []
    partes = [p.strip() for p in str(texto).split("·")]
    r = Recurso(partes[0], partes[1] if len(partes) > 1 else "", "ibc", magnitud_id)
    if len(partes) > 2:
        r.marca = partes[2]
    if len(partes) > 3:
        r.modelo = partes[3]
    for p in partes[4:]:
        if p.lower().startswith("serie"):
            r.serie = p[5:].strip()
        elif p.lower().startswith("resoluci"):
            r.resolucion = p.split(" ", 1)[1].strip() if " " in p else ""
    r.descripcion = r.nombre
    return r and [r]


def leer_definicion(contenido: bytes, codigo: str, nombre: str) -> tuple[Estudio, pd.DataFrame, list[dict]]:
    """Reconstruye el estudio y devuelve también la hoja de mediciones y sus columnas."""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    for hoja in ("Estudio", "Definiciones", "Mediciones", "_control"):
        if hoja not in wb.sheetnames:
            raise ErrorImportacion(f"Falta la hoja «{hoja}»: el archivo no es una plantilla de la aplicación.")
    info = _hoja_clave_valor(wb["Estudio"])
    control = _hoja_clave_valor(wb["_control"])
    columnas = json.loads(control["columnas_mediciones"])
    df = pd.read_excel(io.BytesIO(contenido), sheet_name="Mediciones", dtype=object)
    etiqueta = {c["clave"]: (c["etiqueta"] + (" *" if c["origen"] == "usuario" and c["obligatoria"] else "")) for c in columnas}
    col = lambda clave: df[etiqueta[clave]] if etiqueta.get(clave) in df.columns else None  # noqa: E731

    m = re.match(r"\s*(.+?)\s*\[(.+)\]\s*$", str(info.get("Magnitudes", "")))
    if not m:
        raise ErrorImportacion("No se pudo leer la magnitud (se espera «Nombre [unidad]»).")
    mag = Magnitud("MAG-01", m.group(1), m.group(2))
    e = Estudio(codigo=codigo, nombre=nombre, tipo=str(info.get("Tipo de estudio") or "Verificación"),
                metodo=str(info.get("Método") or ""), version_metodo=str(info.get("Versión del método") or ""),
                responsable=str(info.get("Responsable") or ""), magnitudes=[mag])
    puntos = df[[etiqueta["punto_id"], etiqueta["valor_nominal"], etiqueta["unidad_punto"]]].drop_duplicates()
    e.puntos = [Punto(str(r.iloc[0]), mag.id, float(r.iloc[1]), str(r.iloc[2])) for _, r in puntos.iterrows()]
    mag.intervalo_min, mag.intervalo_max = min(p.valor_nominal for p in e.puntos), max(p.valor_nominal for p in e.puntos)
    e.tecnicos = _recursos(info.get("Técnicos"), "tecnico")
    e.patrones = _recursos(info.get("Patrones"), "patron")
    for p in e.patrones:
        p.magnitud_id, p.descripcion = mag.id, p.nombre
    e.ibcs = _ibc(info.get("Equipo a evaluar (IBC)"), mag.id) or []

    # Definiciones: datos y resultados
    filas = list(wb["Definiciones"].iter_rows(values_only=True))
    i_res = next(i for i, r in enumerate(filas) if r[0] == "Resultados de interés")
    for r in filas[2:i_res]:
        if r[0]:
            e.variables.append(Variable(r[0], r[1], r[2] or "decimal", r[3] or "", r[4] == "Sí", r[5] or ""))
    for r in filas[i_res + 2:]:
        if r[0]:
            directo = str(r[3] or "").lower().startswith("lo registras")
            e.resultados.append(ResultadoInteres(r[0], r[1], unidad=r[2] or "", origen="directo" if directo else "calculado",
                                                 ambito=r[4] or "medicion",
                                                 dependencias=[x.strip() for x in str(r[5] or "").split(",") if x.strip()],
                                                 referencia_calculo=r[6] or "", analizar=str(r[7]).lower() == "sí"))

    # Condiciones: técnico y patrón (vinculados al catálogo) + factores con columna propia
    factores_col = [c for c in columnas if c["entidad"] == "factor"]
    usados = {c["ref_id"] for c in factores_col}
    libres = iter(f"F-{i:02d}" for i in range(1, 30) if f"F-{i:02d}" not in usados)
    e.factores = [Factor(next(libres), "Técnico", "Persona que realiza la medición", vinculo_recurso="tecnico"),
                  Factor(next(libres), "Patrón", "Patrón utilizado", vinculo_recurso="patron")]
    for c in factores_col:
        niveles = sorted({str(x) for x in col(c["clave"]).dropna()})
        e.factores.append(Factor(c["ref_id"], c["etiqueta"], niveles=niveles))
    e.factores.sort(key=lambda f: f.id)
    e.repeticiones_por_condicion = int(pd.to_numeric(col("repeticion")).max())

    # Plan: exactamente las mediciones del archivo
    for _, r in df.iterrows():
        e.plan.append(MedicionPlanificada(
            medicion_id=str(r[etiqueta["medicion_id"]]), punto_id=str(r[etiqueta["punto_id"]]),
            repeticion=int(r[etiqueta["repeticion"]]),
            niveles={c["ref_id"]: str(r[etiqueta[c["clave"]]]) for c in factores_col},
            tecnico=str(r[etiqueta["tecnico"]] or ""), patron=str(r[etiqueta["patron"]] or "")))
    return e, df, columnas


def valores_del_archivo(df: pd.DataFrame, columnas: list[dict]) -> pd.DataFrame:
    """Valores de las columnas del usuario, tal como están en el archivo (sin redondear ni convertir)."""
    salida = pd.DataFrame({"medicion_id": df["ID medición"].astype(str)}, dtype=object)
    for c in columnas:
        if c["origen"] != "usuario":
            continue
        nombre = c["etiqueta"] + (" *" if c["obligatoria"] else "")
        if nombre in df.columns:
            salida[c["clave"]] = df[nombre].astype(object).where(df[nombre].notna(), None)
    return salida


def crear_estudio_desde_archivo(repo: Repositorio, contenido: bytes, nombre_archivo: str, nombre: str, usuario: str,
                                ejecutar: bool = True, escenario: str = "") -> dict:
    base = repo.crear_estudio(nombre, usuario)
    e, df, columnas = leer_definicion(contenido, base.codigo, nombre)
    e.creado_en = base.creado_en
    e.uso_previsto = (f"Escenario: {escenario}. " if escenario else "") + \
        f"Datos sintéticos importados desde «{nombre_archivo}»; no válidos como resultados de calibración. {ETIQUETA}"
    repo.guardar_estudio(e, usuario, f"Importado desde {nombre_archivo}")
    repo.aprobar_version(e, usuario)
    lleno = diligenciar_plantilla(generar_plantilla(e), valores_del_archivo(df, columnas))
    carga = cargar_archivo(repo, e.codigo, lleno, nombre_archivo, usuario)
    if carga["estado_archivo"] != "leido":
        raise ErrorImportacion(f"La carga de {nombre_archivo} fue rechazada.")
    # Igual que un usuario: autoriza las transformaciones que solo cambian la forma de escribir (TR01–TR04).
    prep = preparar_conjunto(repo, e.codigo, carga["carga_id"], ["TR01", "TR02", "TR03", "TR04"], [], usuario)
    aprobar_conjunto(repo, e.codigo, prep["preparacion_id"], usuario)
    salida = {"codigo": e.codigo, "nombre": nombre, "mediciones": len(e.plan), "conteos": prep["conteos"], "analisis": None}

    correccion = next((r for r in e.resultados if r.nombre.lower().startswith("correcci") and r.origen == "directo"), None)
    if correccion is not None:
        cfg = nueva_configuracion(repo, e.codigo, prep["preparacion_id"], usuario)
        cfg.objeto_tipo, cfg.objeto_id = "resultado_directo", correccion.id
        cfg.metodo_validado = "si" if e.tipo.lower().startswith("verif") else "no"
        cfg.factores_precision_intermedia = [f.id for f in e.factores]
        cfg.referencia_tipo = "objeto_es_diferencia"
        cfg.caracteristicas = [CaracteristicaConfig("sesgo", "REQUERIDA"), CaracteristicaConfig("repetibilidad", "REQUERIDA"),
                               CaracteristicaConfig("precision_intermedia", "REQUERIDA")]
        cfg.criterios = criterios_de_prueba()
        cfg.motivo_cambio = ("Configuración inicial con los criterios de prueba de las bases sintéticas." if cfg.criterios
                             else "Configuración inicial sin criterios (los define el laboratorio).")
        if ejecutar:
            r = ejecutar_analisis(repo, cfg, usuario)
            salida["analisis"] = r["conclusion_final"]["estado"]
        else:
            repo.guardar_config_analisis(e.codigo, cfg.to_dict())
    return salida


ETIQUETA = "[bases v2]"


def criterios_de_prueba() -> list:
    """Criterios del archivo criterios_prueba.json (solo para las bases sintéticas)."""
    from src.motor.configuracion import CriterioMotor
    ruta = CARPETA_PRUEBAS / "criterios_prueba.json"
    if not ruta.exists():
        return []
    datos = json.loads(ruta.read_text(encoding="utf-8")).get("criterios", {})
    return [CriterioMotor(f"CP-{i:02d}", car, c["parametro"], "<=", float(c["limite"]), c["unidad"], "estimacion", c["fuente"], True)
            for i, (car, c) in enumerate(datos.items(), start=1)]


ESCENARIOS = {
    "01": "Datos normales · no cumple",
    "02": "Datos normales · cumple",
    "03": "Datos no normales · no cumple",
    "04": "Datos no normales · cumple",
}


def escenario(archivo: str) -> tuple[int, str]:
    """«01_Normal_No_Cumple_3_Variables.xlsx» → (1, «Datos normales · no cumple»)."""
    m = re.match(r"(?:[0-9a-f]{8}-)?(\d{2})_", Path(archivo).name)
    if not m:
        raise ErrorImportacion(f"El archivo «{archivo}» debe empezar por 01_, 02_, 03_ o 04_.")
    return int(m.group(1)), ESCENARIOS.get(m.group(1), Path(archivo).stem)


def archivos_de_prueba(carpeta: Path) -> list[Path]:
    """Un archivo por escenario. Si existe criterios_prueba.json, se usan exactamente los archivos que lista;
    así, copias viejas que hayan quedado en la carpeta (p. ej. «01_…_3_Variables.xlsx») no crean estudios duplicados."""
    indice = carpeta / "criterios_prueba.json"
    if indice.exists():
        nombres = list(json.loads(indice.read_text(encoding="utf-8")).get("escenarios", {}))
        elegidos = [carpeta / f"{n}.xlsx" for n in nombres if (carpeta / f"{n}.xlsx").exists()]
        if elegidos:
            return elegidos
    por_numero: dict[int, Path] = {}
    for a in sorted(carpeta.glob("*.xlsx")):
        try:
            n, _ = escenario(a.name)
        except ErrorImportacion:
            continue
        por_numero.setdefault(n, a)
    return [por_numero[n] for n in sorted(por_numero)]


def crear_estudios_prueba(repo: Repositorio, usuario: str, carpeta: Path | None = None) -> list[dict]:
    """Crea «Testeo 1» … «Testeo 4» desde data/estudios_prueba si aún no existen."""
    carpeta = Path(carpeta or CARPETA_PRUEBAS)
    archivos = archivos_de_prueba(carpeta)
    if not archivos:
        raise ErrorImportacion(f"No hay archivos .xlsx en {carpeta}.")
    existentes = {x["nombre"]: x["codigo"] for x in repo.listar_estudios()}
    salida = []
    for a in archivos:
        n, desc = escenario(a.name)
        nombre = f"Testeo {n}"
        if nombre in existentes:
            viejo = repo.obtener_estudio(existentes[nombre])
            if ETIQUETA in (viejo.uso_previsto or ""):
                salida.append({"nombre": nombre, "omitido": "ya existe"})
                continue
            # Testeo de una versión anterior de las bases: se conserva, renombrado (no se borra nada).
            viejo.nombre = f"{nombre} (bases anteriores)"
            repo.guardar_estudio(viejo, usuario, "Renombrado al cargar las bases de prueba nuevas")
        r = crear_estudio_desde_archivo(repo, a.read_bytes(), a.name, nombre, usuario, escenario=desc)
        salida.append(r)
    return salida


def asegurar_testeos(repo: Repositorio) -> list[dict]:
    """Se llama al abrir la aplicación: deja los 4 testeos en la base de datos local si faltan."""
    try:
        return [x for x in crear_estudios_prueba(repo, "sistema (carga inicial)") if "codigo" in x]
    except ErrorImportacion:
        return []
