"""Estudios con datos REALES del laboratorio (verificación DKD-R 5-7 en temperatura y humedad relativa).

Toma el libro Excel que entrega el laboratorio (una hoja por punto con Operador, Tiempo, Fecha, Corrección,
Inestabilidad e Inhomogeneidad, y una hoja «Precisión Intermedia» con su ANOVA y componentes de varianza) y lo lleva a
la base de datos de la aplicación por el MISMO flujo que un usuario:

  diseño (puntos, operadores, factor Tiempo, resultados directos) → aprobación → plantilla PLT-1.0 → diligenciamiento con
  los valores tal como vienen (sin redondear) → carga → calidad RC01–RC20 → preparación → aprobación → análisis.

No usa el esquema de otra forma: crea objetos con las mismas clases y el mismo repositorio que el resto de la aplicación.
No inventa límites de aceptación: el laboratorio no declara límites numéricos para s_r o s_I, así que el motor calcula
y deja el resultado «calculado sin evaluación». Los valores del informe se guardan aparte para el contraste.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

from src.modelos.estudio import Estudio, Factor, Magnitud, MedicionPlanificada, Punto, Recurso, ResultadoInteres
from src.motor.configuracion import CaracteristicaConfig, ObjetoAnalisis
from src.persistencia.repositorio import Repositorio
from src.plantillas.diligenciar import diligenciar_plantilla
from src.plantillas.generador import generar_plantilla
from src.servicios.analisis import ejecutar_analisis, nueva_configuracion
from src.servicios.flujo import aprobar_conjunto, cargar_archivo, preparar_conjunto

CARPETA_REALES = Path(__file__).resolve().parents[2] / "data" / "datos_reales"
ETIQUETA_REAL = "[datos reales v1]"
RESULTADOS = [("R-01", "Corrección"), ("R-02", "Inestabilidad"), ("R-03", "Inhomogeneidad")]
MAGNITUDES = {"temperatura": ("Temperatura", "°C", "IBC-T01", "Cámara climática (temperatura)"),
              "humedad": ("Humedad relativa", "%hr", "IBC-H01", "Cámara climática BINDER MKF 056 (A-04)")}


class ErrorDatosReales(Exception):
    pass


@dataclass
class LibroLaboratorio:
    magnitud: str                       # temperatura | humedad
    nombre_magnitud: str
    unidad: str
    datos: pd.DataFrame                 # punto, nominal, operador, tiempo, fecha, Corrección, Inestabilidad, Inhomogeneidad
    anova_lab: list[dict] = field(default_factory=list)          # ANOVA de dos factores del laboratorio (Corrección)
    componentes_lab: list[dict] = field(default_factory=list)    # MC y componentes de varianza del laboratorio
    advertencias: list[str] = field(default_factory=list)


def _nominal(nombre_hoja: str) -> tuple[float, str]:
    m = re.search(r"(-?\d+(?:[.,]\d+)?)\s*(C|HR)\s*$", nombre_hoja, re.I)
    if not m:
        raise ErrorDatosReales(f"No se reconoce el punto en la hoja «{nombre_hoja}» (se espera p. ej. Camara_-80C o Camara_10HR).")
    return float(m.group(1).replace(",", ".")), ("°C" if m.group(2).upper() == "C" else "%hr")


def leer_libro(contenido: bytes) -> LibroLaboratorio:
    """Lee el libro del laboratorio SIN modificar valores. Señala (no corrige) valores repetidos exactos."""
    wb = load_workbook(io.BytesIO(contenido), data_only=True)
    hojas = [ws for ws in wb.worksheets if ws.title.lower().startswith("camara")]
    if not hojas:
        raise ErrorDatosReales("El libro no tiene hojas «Camara_…» con los datos por punto.")
    filas = []
    unidades = set()
    for ws in hojas:
        nominal, unidad = _nominal(ws.title)
        unidades.add(unidad)
        enc = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
        req = ["Operador", "Tiempo", "Fecha", "Corrección", "Inestabilidad", "Inhomogeneidad"]
        falta = [r for r in req if r not in enc]
        if falta:
            raise ErrorDatosReales(f"Hoja «{ws.title}»: faltan columnas {falta}.")
        idx = {r: enc.index(r) for r in req}
        for fila in ws.iter_rows(min_row=2, values_only=True):
            if fila[idx["Operador"]] is None:
                continue
            filas.append({"hoja": ws.title, "nominal": nominal, "unidad": unidad,
                          "operador": str(fila[idx["Operador"]]).strip(), "tiempo": str(fila[idx["Tiempo"]]).strip(),
                          "fecha": fila[idx["Fecha"]].date().isoformat() if hasattr(fila[idx["Fecha"]], "date") else str(fila[idx["Fecha"]] or ""),
                          **{v: fila[idx[v]] for v in ("Corrección", "Inestabilidad", "Inhomogeneidad")}})
    if len(unidades) != 1:
        raise ErrorDatosReales(f"El libro mezcla unidades {sorted(unidades)}.")
    unidad = unidades.pop()
    magnitud = "temperatura" if unidad == "°C" else "humedad"
    df = pd.DataFrame(filas)
    libro = LibroLaboratorio(magnitud, MAGNITUDES[magnitud][0], unidad, df)
    # valores idénticos dentro de un mismo punto (posible copia): se informan, no se tocan
    for (hoja, op), g in df.groupby(["hoja", "operador"]):
        for var in ("Corrección", "Inestabilidad", "Inhomogeneidad"):
            rep = g[g.duplicated(var, keep=False)]
            if len(rep):
                libro.advertencias.append(f"{hoja} · {op} · {var}: valores idénticos en {', '.join(rep['tiempo'])} "
                                          f"({rep[var].iloc[0]!r}); se conservan tal como vienen.")
    if "Precisión Intermedia" in wb.sheetnames:
        libro.anova_lab, libro.componentes_lab = _hoja_precision(wb["Precisión Intermedia"])
    return libro


def _num(v):
    return float(v) if isinstance(v, (int, float)) else None


def _hoja_precision(ws) -> tuple[list[dict], list[dict]]:
    """ANOVA de dos factores sin réplica (Excel) y tabla de componentes de varianza, tal como las calculó el laboratorio."""
    filas = list(ws.iter_rows(values_only=True))
    anova, comp, punto = [], [], None
    for i, r in enumerate(filas):
        if r[0] and isinstance(r[0], str) and re.search(r"(°C|%hr)", r[0]) and r[1] == "OP":
            punto = r[0]
        if len(r) > 8 and r[8] in ("Filas", "Columnas", "Error") and punto:
            anova.append({"punto": punto, "fuente": {"Filas": "Operador", "Columnas": "Tiempo", "Error": "Residual"}[r[8]],
                          "sc": _num(r[9]), "gl": _num(r[10]), "mc": _num(r[11]), "F": _num(r[12]), "p": _num(r[13])})
        if r[0] == "Nivel" and r[1] == "MC Operador":
            for s in filas[i + 1:]:
                if not s[0] or not isinstance(s[1], (int, float)):
                    break
                comp.append({"punto": s[0], "mc_operador": s[1], "mc_tiempo": s[2], "mc_residual": s[3], "s2_operador": s[4],
                             "s2_tiempo": s[5], "s2_r": s[6], "s2_R": s[7], "u_lab": s[8]})
    return anova, comp


def construir_estudio(libro: LibroLaboratorio, codigo: str, nombre: str) -> tuple[Estudio, pd.DataFrame]:
    nom_mag, unidad, ibc_cod, ibc_nom = MAGNITUDES[libro.magnitud]
    mag = Magnitud("MAG-01", nom_mag, unidad)
    e = Estudio(codigo=codigo, nombre=nombre, tipo="Verificación", metodo="DKD-R 5-7:2025 Calibration of climatic chambers",
                version_metodo="Edición 01/2025, revisión 0", responsable="Laboratorio de calibración", magnitudes=[mag])
    nominales = sorted(libro.datos["nominal"].unique())
    e.puntos = [Punto(f"PT-{i:02d}", mag.id, float(v), unidad) for i, v in enumerate(nominales, start=1)]
    mag.intervalo_min, mag.intervalo_max = min(nominales), max(nominales)
    operadores = list(dict.fromkeys(libro.datos["operador"]))
    e.tecnicos = [Recurso(f"T-{i:02d}", op, "tecnico") for i, op in enumerate(operadores, start=1)]
    e.ibcs = [Recurso(ibc_cod, ibc_nom, "ibc", mag.id)]
    tiempos = sorted(libro.datos["tiempo"].unique())
    e.factores = [Factor("F-01", "Operador", "Persona que realiza la calibración", vinculo_recurso="tecnico"),
                  Factor("F-02", "Tiempo", "Momento de ejecución (T1 a T5)", niveles=tiempos)]
    e.resultados = [ResultadoInteres(rid, nom, unidad=unidad, origen="directo", ambito="medicion", analizar=True,
                                     referencia_calculo="Calculado por el laboratorio (P-LAB-11, F-LAB-15) y registrado tal como viene")
                    for rid, nom in RESULTADOS]
    e.repeticiones_por_condicion = 1
    cod_op = {op: f"T-{i:02d}" for i, op in enumerate(operadores, start=1)}
    pid = {v: f"PT-{i:02d}" for i, v in enumerate(nominales, start=1)}
    df = libro.datos.copy()
    df["medicion_id"] = [f"M{i:04d}" for i in range(1, len(df) + 1)]
    for _, r in df.iterrows():
        e.plan.append(MedicionPlanificada(medicion_id=r["medicion_id"], punto_id=pid[r["nominal"]],
                                          repeticion=int(re.sub(r"\D", "", r["tiempo"]) or 1),
                                          niveles={"F-02": r["tiempo"]}, tecnico=cod_op[r["operador"]],
                                          fecha_planificada=r["fecha"]))
    e.uso_previsto = (f"Datos reales de verificación del laboratorio ({nom_mag}). Se usan para contrastar el motor con el "
                      f"informe técnico del laboratorio. {ETIQUETA_REAL}")
    return e, df


def valores(df: pd.DataFrame) -> pd.DataFrame:
    salida = pd.DataFrame({"medicion_id": df["medicion_id"]}, dtype=object)
    for rid, nom in RESULTADOS:
        salida[f"res:{rid}"] = df[nom].astype(object)
    return salida


def configurar_objetos() -> list[ObjetoAnalisis]:
    """Lo que evalúa el laboratorio en su informe: repetibilidad y precisión intermedia de cada resultado, frente a
    Operador y Tiempo. El sesgo no aplica: la corrección es el resultado de la calibración del equipo, no un sesgo del
    método. Sin límites numéricos (el informe no los declara)."""
    cars = [CaracteristicaConfig("repetibilidad", "REQUERIDA"), CaracteristicaConfig("precision_intermedia", "REQUERIDA"),
            CaracteristicaConfig("sesgo", "NO_APLICABLE_JUSTIFICADA",
                                 "La corrección es el resultado de calibración del equipo, no un sesgo del método.")]
    return [ObjetoAnalisis("resultado_directo", rid, None, "ninguna", [], list(cars), []) for rid, _ in RESULTADOS]


def crear_estudio_real(repo: Repositorio, contenido: bytes, nombre_archivo: str, nombre: str, usuario: str,
                       factores: str = "operador") -> dict:
    """factores = «operador»: celdas por operador (los 5 tiempos son las réplicas de cada operador) — es la agrupación con
    la que el laboratorio aplica Bartlett. El efecto del Tiempo se contrasta aparte (ANOVA aditiva de dos factores)."""
    libro = leer_libro(contenido)
    base = repo.crear_estudio(nombre, usuario)
    e, df = construir_estudio(libro, base.codigo, nombre)
    e.creado_en = base.creado_en
    repo.guardar_estudio(e, usuario, f"Importado desde {nombre_archivo} (datos reales del laboratorio)")
    repo.aprobar_version(e, usuario)
    lleno = diligenciar_plantilla(generar_plantilla(e), valores(df))
    carga = cargar_archivo(repo, e.codigo, lleno, nombre_archivo, usuario)
    if carga["estado_archivo"] != "leido":
        raise ErrorDatosReales(f"La carga de {nombre_archivo} fue rechazada.")
    prep = preparar_conjunto(repo, e.codigo, carga["carga_id"], ["TR01", "TR03"], [], usuario)
    aprobar_conjunto(repo, e.codigo, prep["preparacion_id"], usuario)
    cfg = nueva_configuracion(repo, e.codigo, prep["preparacion_id"], usuario)
    cfg.metodo_validado = "si"
    cfg.factores_precision_intermedia = ["F-01"]          # celdas por operador: los 5 tiempos son sus réplicas
    cfg.factores_bloque = ["F-02"] if factores == "operador" else []   # Tiempo: efecto aditivo en fuentes de variación
    cfg.objetos = configurar_objetos()
    cfg.objeto_tipo, cfg.objeto_id = "resultado_directo", "R-01"
    cfg.motivo_cambio = "Datos reales del laboratorio; sin límites de aceptación declarados en el informe."
    r = ejecutar_analisis(repo, cfg, usuario)
    return {"codigo": e.codigo, "nombre": nombre, "magnitud": libro.magnitud, "mediciones": len(e.plan),
            "conteos": prep["conteos"], "analisis": r["conclusion_final"]["estado"], "advertencias": libro.advertencias}


def asegurar_estudios_reales(repo: Repositorio, usuario: str = "sistema") -> list[dict]:
    """Crea (una sola vez) los estudios con los libros que estén en data/datos_reales/."""
    existentes = {x["nombre"] for x in repo.listar_estudios()}
    salida = []
    for nombre, archivo in (("Datos reales · Temperatura", "data_temperatura.xlsx"),
                            ("Datos reales · Humedad relativa", "DATA_HUMEDAD.xlsx")):
        ruta = CARPETA_REALES / archivo
        if nombre in existentes or not ruta.exists():
            continue
        salida.append(crear_estudio_real(repo, ruta.read_bytes(), archivo, nombre, usuario))
    return salida
