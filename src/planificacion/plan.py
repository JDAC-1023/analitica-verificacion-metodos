"""Planificación explícita de mediciones (D06, D07, D09, D10, D11, P02-P04).

Restricción fundamental: el sistema NO genera un diseño factorial completo por
haber configurado factores y niveles. El plan se construye:
  1. fila por fila (editor de la interfaz),
  2. importando una planificación estructurada (CSV/Excel), o
  3. con el generador de combinaciones, que es una opción explícita: el
     usuario elige qué cruzar, revisa la vista previa y confirma.
"""

from __future__ import annotations

import io
import itertools
from collections import Counter, defaultdict
from datetime import date

import pandas as pd

from src.modelos.estudio import Estudio, MedicionPlanificada

COL_ID = "Medición"
COL_PUNTO = "Punto"
COL_REP = "Repetición"
COL_TEC = "Técnico"
COL_PAT = "Patrón"
COL_EQ = "Equipo"
COL_FECHA = "Fecha prevista"
COL_FRANJA = "Franja prevista"
COL_ORDEN = "Orden"


# --------------------------------------------------------------------------
# Etiquetas legibles
# --------------------------------------------------------------------------
def etiqueta_punto(e: Estudio, punto_id: str) -> str:
    p = e.punto(punto_id)
    if p is None:
        return punto_id
    m = e.magnitud(p.magnitud_id)
    return f"{p.valor_nominal:g} {p.unidad} · {m.nombre if m else p.magnitud_id}"


def mapa_etiquetas_punto(e: Estudio) -> dict[str, str]:
    return {etiqueta_punto(e, p.id): p.id for p in e.puntos}


def columnas_factores(e: Estudio) -> list[tuple[str, str]]:
    """(factor_id, nombre visible) de los factores que tienen columna propia en el plan."""
    return [(f.id, f.nombre) for f in e.factores_libres()]


def valor_campo(e: Estudio, m: MedicionPlanificada, campo: str) -> str:
    """Valor de una medición para un campo de agrupación o restricción."""
    if campo == "punto":
        return m.punto_id
    if campo in ("tecnico", "patron", "equipo"):
        return getattr(m, campo)
    factor = next((f for f in e.factores if f.id == campo), None)
    if factor is not None and factor.vinculo_recurso != "ninguno":
        return getattr(m, factor.vinculo_recurso)
    return m.niveles.get(campo, "")


def grupo_comparable(e: Estudio, m: MedicionPlanificada) -> str:
    """Clave del grupo de mediciones comparables (D06)."""
    partes = []
    for campo in e.agrupacion:
        etiqueta = "punto" if campo == "punto" else campo
        partes.append(f"{etiqueta}={valor_campo(e, m, campo)}")
    return "|".join(partes)


def condicion_de(e: Estudio, m: MedicionPlanificada) -> tuple:
    """Condición experimental completa (sin repetición).

    Incluye punto, recursos asignados y niveles de todos los factores que se
    comparan. Dos filas con la misma condición y la misma repetición son
    duplicados. Mediciones en puntos distintos nunca comparten condición.
    """
    niveles = tuple(sorted((k, v) for k, v in m.niveles.items()
                           if any(f.id == k and f.rol == "se_compara" for f in e.factores)))
    return (m.punto_id, m.tecnico, m.patron, m.equipo, niveles)


# --------------------------------------------------------------------------
# Conversión plan <-> tabla editable
# --------------------------------------------------------------------------
def plan_a_dataframe(e: Estudio) -> pd.DataFrame:
    filas = []
    for m in e.plan:
        fila = {
            COL_ID: m.medicion_id,
            COL_PUNTO: etiqueta_punto(e, m.punto_id),
            COL_REP: m.repeticion,
            COL_TEC: m.tecnico or None,
            COL_PAT: m.patron or None,
        }
        if e.equipos:
            fila[COL_EQ] = m.equipo or None
        for fid, nombre in columnas_factores(e):
            fila[nombre] = m.niveles.get(fid) or None
        fila[COL_FECHA] = m.fecha_planificada or None
        fila[COL_FRANJA] = m.franja_planificada
        fila[COL_ORDEN] = m.orden
        filas.append(fila)
    columnas = [COL_ID, COL_PUNTO, COL_REP, COL_TEC, COL_PAT] + ([COL_EQ] if e.equipos else []) + \
        [n for _, n in columnas_factores(e)] + [COL_FECHA, COL_FRANJA, COL_ORDEN]
    df = pd.DataFrame(filas, columns=columnas)
    df[COL_REP] = pd.array(df[COL_REP], dtype="Int64")
    df[COL_ORDEN] = pd.array(df[COL_ORDEN], dtype="Int64")
    return df


def _texto(valor) -> str:
    if valor is None:
        return ""
    try:
        if pd.isna(valor):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    if isinstance(valor, (pd.Timestamp, date)):
        return valor.strftime("%Y-%m-%d")
    return str(valor).strip()


def _entero(valor) -> int | None:
    texto = _texto(valor)
    if not texto:
        return None
    try:
        numero = float(texto.replace(",", "."))
    except ValueError:
        return None
    return int(numero) if numero.is_integer() else None


def plan_desde_dataframe(e: Estudio, df: pd.DataFrame) -> tuple[list[MedicionPlanificada], list[str]]:
    """Convierte la tabla editada en mediciones planificadas.

    Devuelve (plan, errores de lectura). Las filas completamente vacías se
    ignoran. Los identificadores existentes se conservan; las filas nuevas
    reciben el siguiente identificador libre.
    """
    mapa = mapa_etiquetas_punto(e)
    por_valor = {}
    for p in e.puntos:
        por_valor.setdefault(f"{p.valor_nominal:g}", []).append(p.id)
    errores: list[str] = []
    plan: list[MedicionPlanificada] = []
    usados = {_texto(x) for x in df.get(COL_ID, pd.Series(dtype=object)) if _texto(x)}
    contador = 0

    def nuevo_id() -> str:
        nonlocal contador
        while True:
            contador += 1
            candidato = f"M{contador:04d}"
            if candidato not in usados:
                usados.add(candidato)
                return candidato

    for posicion, (_, fila) in enumerate(df.iterrows(), start=1):
        valores = {c: _texto(fila.get(c)) for c in df.columns}
        if not any(v for c, v in valores.items() if c != COL_ID):
            continue
        punto_txt = valores.get(COL_PUNTO, "")
        punto_id = mapa.get(punto_txt) or (punto_txt if e.punto(punto_txt) else "")
        if not punto_id and punto_txt in por_valor and len(por_valor[punto_txt]) == 1:
            punto_id = por_valor[punto_txt][0]
        if not punto_id:
            errores.append(f"Fila {posicion}: el punto «{punto_txt}» no corresponde a un punto configurado")
        repeticion = _entero(fila.get(COL_REP))
        if repeticion is None:
            errores.append(f"Fila {posicion}: la repetición debe ser un número entero")
        niveles = {}
        for fid, nombre in columnas_factores(e):
            if nombre in df.columns and valores.get(nombre):
                niveles[fid] = valores[nombre]
        plan.append(MedicionPlanificada(
            medicion_id=valores.get(COL_ID) or nuevo_id(),
            punto_id=punto_id,
            repeticion=repeticion or 0,
            niveles=niveles,
            tecnico=valores.get(COL_TEC, ""),
            patron=valores.get(COL_PAT, ""),
            equipo=valores.get(COL_EQ, ""),
            fecha_planificada=valores.get(COL_FECHA, ""),
            franja_planificada=valores.get(COL_FRANJA, ""),
            orden=_entero(fila.get(COL_ORDEN)),
        ))
    return plan, errores


def importar_plan(e: Estudio, contenido: bytes, nombre_archivo: str) -> tuple[list[MedicionPlanificada], list[str]]:
    """Importa una planificación estructurada (CSV o Excel) con las columnas del editor.

    La columna «Punto» acepta la etiqueta mostrada en la aplicación, el
    identificador del punto (PT-01) o el valor nominal cuando no es ambiguo.
    """
    try:
        if nombre_archivo.lower().endswith(".csv"):
            df = pd.read_csv(io.BytesIO(contenido), dtype=str, sep=None, engine="python")
        else:
            df = pd.read_excel(io.BytesIO(contenido), dtype=str)
    except Exception as exc:  # noqa: BLE001 - se informa al usuario
        return [], [f"No se pudo leer el archivo de planificación: {exc}"]
    df.columns = [str(c).strip() for c in df.columns]
    faltan = [c for c in (COL_PUNTO, COL_REP) if c not in df.columns]
    if faltan:
        return [], [f"Faltan columnas obligatorias en la planificación: {', '.join(faltan)}"]
    if COL_ID not in df.columns:
        df.insert(0, COL_ID, "")
    return plan_desde_dataframe(e, df)


# --------------------------------------------------------------------------
# Generador explícito de combinaciones (opcional, requiere confirmación)
# --------------------------------------------------------------------------
def generar_combinaciones(
    e: Estudio,
    puntos: list[str],
    cruzar: dict[str, list[str]],
    repeticiones: int,
    fijos: dict[str, str] | None = None,
) -> list[MedicionPlanificada]:
    """Genera las combinaciones que el usuario eligió de forma explícita.

    `cruzar` = {campo: niveles elegidos}, donde campo es 'tecnico', 'patron',
    'equipo' o el id de un factor libre. Solo se cruzan los campos indicados.
    `fijos` asigna un mismo valor a campos que no se cruzan.
    Los identificadores se asignan después de los ya existentes en el plan.
    """
    fijos = fijos or {}
    usados = {m.medicion_id for m in e.plan}
    claves = list(cruzar.keys())
    nuevas: list[MedicionPlanificada] = []
    numero = 0
    for punto_id in puntos:
        for combinacion in itertools.product(*[cruzar[k] for k in claves]) if claves else [()]:
            asignacion = dict(fijos)
            asignacion.update(dict(zip(claves, combinacion)))
            for rep in range(1, repeticiones + 1):
                while True:
                    numero += 1
                    mid = f"M{numero:04d}"
                    if mid not in usados:
                        usados.add(mid)
                        break
                nuevas.append(MedicionPlanificada(
                    medicion_id=mid,
                    punto_id=punto_id,
                    repeticion=rep,
                    niveles={k: v for k, v in asignacion.items() if k not in ("tecnico", "patron", "equipo")},
                    tecnico=asignacion.get("tecnico", ""),
                    patron=asignacion.get("patron", ""),
                    equipo=asignacion.get("equipo", ""),
                ))
    return nuevas


# --------------------------------------------------------------------------
# Validación del plan
# --------------------------------------------------------------------------
def validar_plan(e: Estudio) -> tuple[list[str], list[str]]:
    errores: list[str] = []
    advertencias: list[str] = []
    tecnicos = {r.codigo for r in e.tecnicos}
    patrones = {r.codigo: r for r in e.patrones}
    equipos = {r.codigo for r in e.equipos}

    ids = Counter(m.medicion_id for m in e.plan)
    for mid, n in ids.items():
        if n > 1:
            errores.append(f"El identificador {mid} está repetido en el plan")

    for m in e.plan:
        ref = m.medicion_id
        punto = e.punto(m.punto_id)
        if punto is None:
            errores.append(f"{ref}: el punto no existe en la configuración")
        if m.repeticion < 1:
            errores.append(f"{ref}: la repetición debe ser 1 o mayor")
        if m.tecnico and m.tecnico not in tecnicos:
            errores.append(f"{ref}: el técnico «{m.tecnico}» no está en el catálogo de técnicos")
        if m.patron and m.patron not in patrones:
            errores.append(f"{ref}: el patrón «{m.patron}» no está en el catálogo de patrones")
        if m.equipo and m.equipo not in equipos:
            errores.append(f"{ref}: el equipo «{m.equipo}» no está en el catálogo de equipos")
        for f in e.factores:
            if f.vinculo_recurso != "ninguno":
                if f.rol == "se_compara" and not getattr(m, f.vinculo_recurso):
                    errores.append(f"{ref}: falta asignar «{f.nombre}», que es una condición a comparar")
                continue
            valor = m.niveles.get(f.id, "")
            if not valor:
                if f.rol == "se_compara":
                    errores.append(f"{ref}: falta la opción de «{f.nombre}»")
                continue
            if valor not in f.niveles:
                errores.append(f"{ref}: «{valor}» no es una opción configurada de «{f.nombre}»")
        if m.fecha_planificada:
            try:
                date.fromisoformat(m.fecha_planificada)
            except ValueError:
                errores.append(f"{ref}: la fecha prevista debe tener el formato AAAA-MM-DD")
        # Compatibilidad patrón-punto (R03, D11). PD06 sigue pendiente: se advierte, no se bloquea.
        pat = patrones.get(m.patron)
        if pat and punto is not None:
            if pat.magnitud_id and pat.magnitud_id != punto.magnitud_id:
                advertencias.append(f"{ref}: el patrón {pat.codigo} no está registrado para la magnitud de este punto")
            elif pat.intervalo_min is not None and pat.intervalo_max is not None and not (
                pat.intervalo_min <= punto.valor_nominal <= pat.intervalo_max
            ):
                advertencias.append(f"{ref}: el punto {punto.valor_nominal:g} {punto.unidad} está fuera del intervalo útil del patrón {pat.codigo}")
        for r in e.restricciones:  # D11
            if valor_campo(e, m, r.campo_a) == r.valor_a and valor_campo(e, m, r.campo_b) == r.valor_b:
                errores.append(f"{ref}: combinación no permitida ({r.valor_a} con {r.valor_b}). {r.motivo}".strip())

    if e.tecnicos and any(not m.tecnico for m in e.plan):
        advertencias.append("Hay mediciones sin técnico asignado (P02)")
    if e.patrones and any(not m.patron for m in e.plan):
        advertencias.append("Hay mediciones sin patrón asignado (P03)")

    # Repeticiones: duplicadas y numeración por condición.
    por_condicion: dict[tuple, list[MedicionPlanificada]] = defaultdict(list)
    for m in e.plan:
        por_condicion[condicion_de(e, m)].append(m)
    for condicion, filas in por_condicion.items():
        reps = Counter(m.repeticion for m in filas)
        for rep, n in reps.items():
            if n > 1:
                ids_dup = ", ".join(m.medicion_id for m in filas if m.repeticion == rep)
                errores.append(f"La repetición {rep} aparece {n} veces para la misma condición ({ids_dup})")
        esperadas = set(range(1, len(set(reps)) + 1))
        if set(reps) != esperadas and all(r >= 1 for r in reps):
            advertencias.append(
                f"Repeticiones no consecutivas en {etiqueta_punto(e, condicion[0])}: {sorted(reps)}"
            )
    ordenes = [m.orden for m in e.plan if m.orden is not None]
    if len(ordenes) != len(set(ordenes)):
        advertencias.append("Hay órdenes de ejecución repetidos (D10)")
    return errores, advertencias


def resumen_plan(e: Estudio) -> dict[str, int]:
    return {
        "mediciones": len(e.plan),
        "puntos": len({m.punto_id for m in e.plan}),
        "condiciones": len({condicion_de(e, m) for m in e.plan}),
        "grupos_comparables": len({grupo_comparable(e, m) for m in e.plan}),
    }
