"""Comprobación de completitud y coherencia de la configuración del estudio.

Devuelve, por etapa, lo que falta para continuar. Estas comprobaciones son
estructurales: no evalúan la idoneidad metrológica ni estadística del diseño.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.modelos.estudio import Estudio


@dataclass
class EstadoEtapa:
    clave: str
    titulo: str
    obligatoria: bool
    faltantes: list[str] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return not self.faltantes


def _duplicados(valores: list[str]) -> list[str]:
    vistos, dup = set(), set()
    for v in valores:
        clave = v.strip().casefold()
        if clave in vistos:
            dup.add(v)
        vistos.add(clave)
    return sorted(dup)


def revisar_identificacion(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("identificacion", "Identificación del estudio", True)
    for valor, etiqueta in [
        (e.nombre, "Nombre del estudio (E01)"),
        (e.tipo, "Tipo de estudio (E03)"),
        (e.metodo, "Método que vas a evaluar (E04)"),
        (e.version_metodo, "Versión del método (E05)"),
        (e.uso_previsto, "¿Para qué necesitas comprobarlo? (E06)"),
        (e.responsable, "Responsable del estudio (E08)"),
    ]:
        if not str(valor or "").strip():
            est.faltantes.append(etiqueta)
    return est


def revisar_alcance(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("alcance", "Magnitudes y puntos", True)
    if not e.magnitudes:
        est.faltantes.append("Al menos una magnitud con su unidad (E09)")
    for m in e.magnitudes:
        if not m.nombre.strip() or not m.unidad.strip():
            est.faltantes.append(f"Nombre y unidad de la magnitud {m.id}")
        if m.intervalo_min is None or m.intervalo_max is None:
            est.faltantes.append(f"Intervalo de trabajo de «{m.nombre or m.id}» (E10)")
        elif m.intervalo_min > m.intervalo_max:
            est.faltantes.append(f"El intervalo de «{m.nombre}» tiene el mínimo mayor que el máximo")
    if e.magnitudes and not e.puntos:
        est.faltantes.append("Al menos un punto de medición (E11)")
    for p in e.puntos:
        m = e.magnitud(p.magnitud_id)
        if m is None:
            est.faltantes.append(f"El punto {p.id} no está asociado a una magnitud existente")
            continue
        if m.intervalo_min is not None and m.intervalo_max is not None and not (m.intervalo_min <= p.valor_nominal <= m.intervalo_max):
            est.advertencias.append(
                f"El punto {p.valor_nominal} {p.unidad} está fuera del intervalo declarado para «{m.nombre}»"
            )
    claves = [f"{p.magnitud_id}|{p.valor_nominal}" for p in e.puntos]
    if len(set(claves)) != len(claves):
        est.faltantes.append("Hay puntos repetidos para la misma magnitud")
    return est


def revisar_recursos(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("recursos", "Equipo a evaluar, técnicos y patrones", True)
    if not e.tecnicos:
        est.faltantes.append("Al menos un técnico que pueda medir (R01)")
    if not e.patrones:
        est.faltantes.append("Al menos un patrón (R02)")
    if not e.ibcs:
        est.faltantes.append("El equipo a evaluar (IBC)")
    for i in e.ibcs:
        if not i.descripcion.strip():
            est.faltantes.append(f"Descripción del equipo a evaluar {i.codigo}")
    if len(e.ibcs) > 1:
        est.advertencias.append("Hay varios equipos a evaluar: agrega la condición «Equipo a evaluar» si cada medición usa uno distinto")
    for grupo, nombre in [(e.tecnicos, "técnicos"), (e.patrones, "patrones"), (e.equipos, "equipos"), (e.ibcs, "equipos a evaluar")]:
        if any(not r.codigo.strip() for r in grupo):
            est.faltantes.append(f"Hay {nombre} sin código")
        dup = _duplicados([r.codigo for r in grupo])
        if dup:
            est.faltantes.append(f"Códigos de {nombre} repetidos: {', '.join(dup)}")
    for p in e.patrones:  # R03
        if not p.magnitud_id:
            est.advertencias.append(f"El patrón {p.codigo} no tiene magnitud asociada (R03)")
        if p.intervalo_min is None or p.intervalo_max is None:
            est.advertencias.append(f"El patrón {p.codigo} no tiene intervalo útil registrado (R03)")
    return est


def revisar_condiciones(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("condiciones", "Condiciones a comparar", True)
    dup = _duplicados([f.nombre for f in e.factores])
    if dup:
        est.faltantes.append(f"Condiciones con nombre repetido: {', '.join(dup)}")
    for f in e.factores:
        if not f.nombre.strip():
            est.faltantes.append(f"La condición {f.id} no tiene nombre")
        if f.vinculo_recurso == "ninguno":
            if not f.niveles:
                est.faltantes.append(f"Opciones de «{f.nombre}» (D04)")
            if _duplicados(f.niveles):
                est.faltantes.append(f"Opciones repetidas en «{f.nombre}»")
            if f.tipo_valor == "numerico":
                for n in f.niveles:
                    try:
                        float(str(n).replace(",", "."))
                    except ValueError:
                        est.faltantes.append(f"«{f.nombre}» es numérica pero la opción «{n}» no es un número")
    vinculos = [f.vinculo_recurso for f in e.factores if f.vinculo_recurso != "ninguno"]
    if len(vinculos) != len(set(vinculos)):
        est.faltantes.append("Dos condiciones están vinculadas al mismo catálogo de recursos")
    if e.repeticiones_por_condicion < 1:
        est.faltantes.append("El número de repeticiones debe ser al menos 1 (D07)")
    if not e.unidad_experimental.strip():
        est.advertencias.append("Falta describir qué cuenta como una repetición independiente (D08, pendiente técnico)")
    validas = {"punto", "tecnico", "patron", "equipo"} | {f.id for f in e.factores}
    if any(a not in validas for a in e.agrupacion):
        est.faltantes.append("La agrupación de mediciones comparables usa una condición que ya no existe (D06)")
    if "punto" not in e.agrupacion:
        est.advertencias.append(
            "La agrupación no incluye el punto de medición: se compararían puntos distintos entre sí (D06)"
        )
    return est


def revisar_variables(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("variables", "Datos que registrarás", True)
    if not e.variables:
        est.faltantes.append("Al menos un dato a registrar en cada medición (D12)")
    dup = _duplicados([v.nombre for v in e.variables])
    if dup:
        est.faltantes.append(f"Datos con nombre repetido: {', '.join(dup)}")
    for v in e.variables:
        if not v.nombre.strip():
            est.faltantes.append(f"El dato {v.id} no tiene nombre")
        if v.tipo_dato in ("decimal", "entero") and not v.unidad.strip():
            est.advertencias.append(f"«{v.nombre}» es numérico y no tiene unidad")
    return est


def revisar_resultados(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("resultados", "Resultados de interés", True)
    if not e.resultados:
        est.faltantes.append("Al menos un resultado de interés (V01)")
    nombres_variables = {v.nombre.casefold() for v in e.variables}
    dup = _duplicados([r.nombre for r in e.resultados])
    if dup:
        est.faltantes.append(f"Resultados con nombre repetido: {', '.join(dup)}")
    ids_validos = {v.id for v in e.variables} | {r.id for r in e.resultados}
    for r in e.resultados:
        if r.nombre.casefold() in nombres_variables:
            est.faltantes.append(f"«{r.nombre}» tiene el mismo nombre que un dato registrado; deben distinguirse")
        if r.origen == "calculado":
            if not r.dependencias:
                est.advertencias.append(f"«{r.nombre}» es calculado pero no tiene datos de origen (V05, por definir)")
            if not r.referencia_calculo.strip():
                est.advertencias.append(f"«{r.nombre}» no tiene referencia del procedimiento de cálculo (V06, pendiente técnico)")
        if any(d not in ids_validos for d in r.dependencias):
            est.faltantes.append(f"«{r.nombre}» depende de un dato o resultado que ya no existe")
        if r.id in r.dependencias:
            est.faltantes.append(f"«{r.nombre}» no puede depender de sí mismo")
    if e.resultados and not any(r.analizar for r in e.resultados):
        est.advertencias.append("Ningún resultado está marcado para análisis estadístico (V08)")
    return est


def revisar_criterios(e: Estudio) -> EstadoEtapa:
    est = EstadoEtapa("criterios", "Criterios de evaluación", False)
    ids = {r.id for r in e.resultados}
    for c in e.criterios:
        if c.resultado_id not in ids:
            est.faltantes.append(f"El criterio {c.id} apunta a un resultado inexistente")
        if not c.fuente.strip():
            est.advertencias.append(f"El criterio {c.id} no tiene fuente (C02)")
        if not c.aprobado:
            est.advertencias.append(f"El criterio {c.id} aún no está aprobado; debe aprobarse antes de analizar")
    for r in e.resultados:
        if r.tiene_criterio and not any(c.resultado_id == r.id for c in e.criterios):
            est.advertencias.append(f"«{r.nombre}» indica que tiene criterio pero no se ha relacionado ninguno (V09)")
    return est


def revisar_plan(e: Estudio) -> EstadoEtapa:
    from src.planificacion.plan import validar_plan  # import local para evitar ciclos

    est = EstadoEtapa("plan", "Mediciones planificadas", True)
    if not e.plan:
        est.faltantes.append("Al menos una medición planificada (D09)")
        return est
    errores, advertencias = validar_plan(e)
    est.faltantes.extend(errores)
    est.advertencias.extend(advertencias)
    return est


def revisar_estudio(e: Estudio) -> list[EstadoEtapa]:
    return [
        revisar_identificacion(e),
        revisar_alcance(e),
        revisar_recursos(e),
        revisar_condiciones(e),
        revisar_variables(e),
        revisar_resultados(e),
        revisar_criterios(e),
        revisar_plan(e),
    ]


def listo_para_aprobar(e: Estudio) -> tuple[bool, list[str]]:
    # Las etapas opcionales (criterios) solo generan «faltantes» ante una
    # incoherencia real (p. ej., un criterio sin resultado), así que también bloquean.
    faltantes = [f"{et.titulo}: {f}" for et in revisar_estudio(e) for f in et.faltantes]
    return (not faltantes, faltantes)
