"""Asistente «Crear estudio»: preguntas paso a paso hasta generar la plantilla y subir los datos.

Se usa en dos lugares con el mismo código:
  - como panel lateral flotante (st.dialog a la derecha), y
  - como página completa («Crear / continuar estudio»).

Cada «Siguiente» guarda el borrador en el repositorio, así que nada se pierde
al cerrar el panel o cambiar de página: el asistente reabre en el último paso.
Las preguntas siguen el texto sencillo de la matriz de parametrización.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from interfaz.comun import ETIQUETA_ESTADO, metricas_conteos, repositorio, usuario
from src.calidad.evaluador import resumen_mensajes
from src.configuracion.validacion_estudio import listo_para_aprobar, revisar_estudio
from src.modelos.estudio import (
    AMBITOS_RESULTADO, CATEGORIAS_VARIABLE, TIPOS_DATO, Criterio, Estudio, Factor, Magnitud, Punto, Recurso,
    ResultadoInteres, Variable, siguiente_id,
)
from src.planificacion.plan import etiqueta_punto, generar_combinaciones, plan_a_dataframe
from src.plantillas.generador import generar_plantilla, nombre_archivo_plantilla
from src.servicios.flujo import cargar_archivo

PASOS = [
    ("Estudio", ":material/badge:"),
    ("Método", ":material/menu_book:"),
    ("Magnitudes", ":material/straighten:"),
    ("Puntos", ":material/linear_scale:"),
    ("Equipo a evaluar (IBC)", ":material/device_thermostat:"),
    ("Técnicos", ":material/groups:"),
    ("Patrones", ":material/verified:"),
    ("Condiciones", ":material/tune:"),
    ("Datos a registrar", ":material/edit_note:"),
    ("Resultados de interés", ":material/target:"),
    ("Criterios", ":material/rule:"),
    ("Mediciones", ":material/calendar_month:"),
    ("Generar plantilla", ":material/table_view:"),
    ("Subir DB", ":material/upload_file:"),
]
TOTAL = len(PASOS)
AMBITO_TXT = {"medicion": "Cada medición", "serie": "Una serie (repeticiones de una misma condición)", "punto": "Cada punto de medición",
              "condicion": "Cada grupo comparable", "estudio": "Todo el estudio", "otro": "Otro grupo"}
ORIGEN_TXT = {"calculado": "Se calculará", "directo": "Lo escribo yo"}
SUGERIDOS = ["Error", "Corrección", "Inestabilidad", "Inhomogeneidad"]


# ---------------------------------------------------------------- utilidades
def _txt(v) -> str:
    if v is None:
        return ""
    try:
        if pd.isna(v):
            return ""
    except (TypeError, ValueError):
        pass
    return str(v).strip()


def _num(v):
    t = _txt(v).replace(",", ".")
    try:
        return float(t) if t else None
    except ValueError:
        return None


def _bool(v, defecto=False) -> bool:
    if v is None:
        return defecto
    try:
        if pd.isna(v):
            return defecto
    except (TypeError, ValueError):
        pass
    return bool(v)


def crear_estudio_dialogo() -> None:
    """Contenido del panel «Crear estudio» (solo pide el nombre; el resto lo pregunta el asistente)."""
    st.write("Empieza dándole un nombre. Luego el asistente te preguntará todo lo demás, paso a paso, y guardará tu avance.")
    nombre = st.text_input("¿Cómo vas a identificar este estudio?", placeholder="Ej.: Verificación del método de medios isotermos",
                           help="E01. El código único (EST-0001…) lo asigna el sistema (E02).")
    quien = st.text_input("¿Quién está trabajando?", value=usuario(), help="Se registra en la bitácora.")
    if st.button("Crear y continuar", type="primary", icon=":material/arrow_forward:", width="stretch"):
        if not nombre.strip() or not quien.strip():
            st.error("Escribe el nombre del estudio y tu nombre.")
            return
        st.session_state["usuario"] = quien.strip()
        e = repositorio().crear_estudio(nombre, quien.strip())
        st.session_state["estudio_codigo"] = e.codigo
        st.session_state["asistente_abierto"] = True
        st.session_state.pop("crear_nuevo", None)
        st.rerun()


# ---------------------------------------------------------------- pasos
# Cada paso dibuja sus preguntas y devuelve una función aplicar(e) -> lista de errores.
# Los errores bloquean «Siguiente»; «Anterior» y «Guardar borrador» guardan lo que sea válido.

def paso_estudio(e: Estudio, k: str):
    nombre = st.text_input("¿Cómo vas a identificar este estudio?", e.nombre, key=f"{k}nom", help="E01")
    st.text_input("Código del estudio", e.codigo, disabled=True, help="E02 · Lo asigna el sistema.")
    tipo = st.radio("¿Qué tipo de estudio harás?", ["Verificación", "Validación"], index=0 if e.tipo != "Validación" else 1,
                    key=f"{k}tipo", horizontal=True,
                    captions=["Compruebas que tu laboratorio cumple un método ya establecido.",
                              "Demuestras que un método (propio o modificado) es apto para su uso previsto."],
                    help="E03 · Identifica el propósito; por sí solo no determina la ruta estadística.")

    def aplicar(e):
        e.nombre, e.tipo = nombre.strip(), tipo
        return [] if e.nombre else ["Escribe el nombre del estudio."]
    return aplicar


def paso_metodo(e: Estudio, k: str):
    metodo = st.text_input("¿Qué método vas a evaluar?", e.metodo, key=f"{k}met", placeholder="Nombre o código del método en tu laboratorio", help="E04")
    c1, c2 = st.columns(2)
    version = c1.text_input("Versión del método", e.version_metodo, key=f"{k}ver", placeholder="Ej.: 3", help="E05")
    responsable = c2.text_input("Responsable del estudio", e.responsable, key=f"{k}resp",
                                placeholder="¿Quién revisa y aprueba?", help="E08")
    uso = st.text_area("¿Para qué necesitas comprobarlo?", e.uso_previsto, key=f"{k}uso", height=90,
                       placeholder="Uso previsto y qué buscas demostrar", help="E06")
    ref = st.text_input("Documento de referencia (si existe)", e.documento_referencia, key=f"{k}ref",
                        placeholder="Ej.: DAkkS-DKD-R 5-7 o procedimiento interno", help="E07 · Opcional")

    def aplicar(e):
        e.metodo, e.version_metodo, e.responsable = metodo.strip(), version.strip(), responsable.strip()
        e.uso_previsto, e.documento_referencia = uso.strip(), ref.strip()
        faltan = [n for n, v in (("método", e.metodo), ("versión del método", e.version_metodo),
                                 ("para qué necesitas comprobarlo", e.uso_previsto), ("responsable", e.responsable)) if not v]
        return [f"Completa: {', '.join(faltan)}."] if faltan else []
    return aplicar


MAGNITUDES_COMUNES = {"Temperatura": "°C", "Humedad relativa": "%HR", "Presión": "kPa", "Masa": "g", "Longitud": "mm",
                      "Volumen": "mL", "Tiempo": "s", "Otra": ""}


def _cantidad(etiqueta: str, actual: int, k: str, ayuda: str | None = None, minimo: int = 1) -> int:
    return int(st.number_input(etiqueta, minimo, 30, max(actual, minimo), key=k, help=ayuda))


def paso_magnitudes(e: Estudio, k: str):
    n = _cantidad("¿Cuántas magnitudes intervienen en el estudio?", len(e.magnitudes), f"{k}n", "E09 · Ej.: temperatura y humedad relativa = 2")
    campos = []
    for i in range(n):
        m = e.magnitudes[i] if i < len(e.magnitudes) else None
        with st.container(border=True):
            st.markdown(f"**Magnitud {i + 1}**")
            c1, c2 = st.columns([2, 1])
            opciones = list(MAGNITUDES_COMUNES)
            elegida = m.nombre if m and m.nombre in MAGNITUDES_COMUNES else ("Otra" if m else opciones[i] if i < 2 else "Otra")
            tipo = c1.selectbox("¿Qué magnitud?", opciones, index=opciones.index(elegida), key=f"{k}t{i}")
            nombre = c1.text_input("Nombre de la magnitud", m.nombre if m and tipo == "Otra" else "", key=f"{k}o{i}",
                                   placeholder="Escribe el nombre") if tipo == "Otra" else tipo
            unidad = c2.text_input("Unidad", m.unidad if m else MAGNITUDES_COMUNES[tipo], key=f"{k}u{i}{tipo}", help="Ej.: °C, %HR")
            d1, d2 = st.columns(2)
            desde = d1.number_input("¿Desde qué valor trabajas?", value=m.intervalo_min if m else None, key=f"{k}d{i}",
                                    format="%g", placeholder="Ej.: -20", help="E10 · Intervalo de trabajo")
            hasta = d2.number_input("¿Hasta qué valor?", value=m.intervalo_max if m else None, key=f"{k}h{i}",
                                    format="%g", placeholder="Ej.: 150")
            campos.append((m.id if m else "", nombre, unidad, desde, hasta))

    def aplicar(e):
        nuevas, errores = [], []
        for mid, nombre, unidad, desde, hasta in campos:
            mid = mid or siguiente_id("MAG", [m.id for m in nuevas] + [m.id for m in e.magnitudes])
            mg = Magnitud(mid, (nombre or "").strip(), (unidad or "").strip(), desde, hasta)
            if not mg.nombre or not mg.unidad:
                errores.append("Cada magnitud necesita nombre y unidad.")
            if desde is None or hasta is None:
                errores.append(f"Indica desde y hasta qué valor trabajas en «{mg.nombre or 'la magnitud'}».")
            elif desde > hasta:
                errores.append(f"En «{mg.nombre}», «desde» es mayor que «hasta».")
            nuevas.append(mg)
        usadas = {p.magnitud_id for p in e.puntos} | {x.magnitud_id for x in e.patrones + e.ibcs if x.magnitud_id}
        if usadas - {m.id for m in nuevas}:
            return errores + ["No puedes quitar una magnitud que ya tiene puntos, patrones o equipos asociados."]
        e.magnitudes = nuevas
        for pt in e.puntos:
            mg = e.magnitud(pt.magnitud_id)
            if mg:
                pt.unidad = mg.unidad
        return errores
    return aplicar


def paso_puntos(e: Estudio, k: str):
    st.caption("E11 · Escribe los valores nominales separados por punto y coma. Ej.: 20; 40; 60. "
               "Mediciones en puntos distintos nunca se tratan como repeticiones de una misma condición.")
    entradas = {}
    for m in e.magnitudes:
        actuales = "; ".join(f"{p.valor_nominal:g}" for p in e.puntos if p.magnitud_id == m.id)
        entradas[m.id] = st.text_input(f"¿En qué puntos vas a medir {m.nombre}? [{m.unidad}]", actuales, key=f"{k}pt{m.id}",
                                       placeholder="20; 40; 60",
                                       help=f"Intervalo declarado: {m.intervalo_min:g} a {m.intervalo_max:g} {m.unidad}"
                                       if m.intervalo_min is not None and m.intervalo_max is not None else None)
    if not e.magnitudes:
        st.warning("Primero agrega una magnitud en el paso anterior.")

    def aplicar(e):
        errores, puntos = [], []
        for m in e.magnitudes:
            valores = []
            for parte in entradas[m.id].split(";"):
                if not parte.strip():
                    continue
                v = _num(parte)
                if v is None:
                    errores.append(f"«{parte.strip()}» no es un número ({m.nombre}).")
                elif v not in valores:
                    valores.append(v)
            for v in valores:
                existente = next((p for p in e.puntos if p.magnitud_id == m.id and p.valor_nominal == v), None)
                pid = existente.id if existente else siguiente_id("PT", [p.id for p in puntos] + [p.id for p in e.puntos])
                puntos.append(Punto(pid, m.id, v, m.unidad))
        if not puntos:
            errores.append("Escribe al menos un punto de medición.")
        if errores:
            return errores
        e.puntos = puntos
        quitadas = [x for x in e.plan if not e.punto(x.punto_id)]
        if quitadas:
            e.plan = [x for x in e.plan if e.punto(x.punto_id)]
            st.toast(f"Se quitaron {len(quitadas)} mediciones planificadas de puntos eliminados.")
        return []
    return aplicar


def _opciones_magnitud(e: Estudio) -> dict[str, str]:
    return {f"{m.nombre} [{m.unidad}]": m.id for m in e.magnitudes}


def _selector_magnitud(e: Estudio, col, actual: str, key: str) -> str:
    mags = _opciones_magnitud(e)
    inv = {v: k2 for k2, v in mags.items()}
    if not mags:
        col.caption("Sin magnitudes")
        return ""
    lista = list(mags)
    elegido = col.selectbox("Magnitud", lista, index=lista.index(inv[actual]) if actual in inv else 0, key=key)
    return mags[elegido]


def paso_ibc(e: Estudio, k: str):
    st.caption("Describe el equipo que vas a evaluar (IBC): por ejemplo, la cámara climática, el horno o el baño.")
    n = _cantidad("¿Cuántos equipos vas a evaluar?", len(e.ibcs), f"{k}n")
    campos = []
    for i in range(n):
        x = e.ibcs[i] if i < len(e.ibcs) else None
        with st.container(border=True):
            st.markdown(f"**Equipo {i + 1}**")
            c1, c2 = st.columns([1, 3])
            codigo = c1.text_input("Código", x.codigo if x else f"IBC-{i + 1:02d}", key=f"{k}c{i}")
            desc = c2.text_input("Descripción del equipo", x.descripcion if x else "", key=f"{k}d{i}",
                                 placeholder="Ej.: Cámara climática de temperatura y humedad")
            c3, c4, c5 = st.columns(3)
            marca = c3.text_input("Marca", x.marca if x else "", key=f"{k}ma{i}")
            modelo = c4.text_input("Modelo", x.modelo if x else "", key=f"{k}mo{i}")
            serie = c5.text_input("Número de serie", x.serie if x else "", key=f"{k}s{i}")
            c6, c7, c8, c9 = st.columns(4)
            mag = _selector_magnitud(e, c6, x.magnitud_id if x else "", f"{k}g{i}")
            resol = c7.text_input("Resolución", x.resolucion if x else "", key=f"{k}r{i}", placeholder="Ej.: 0,1 °C")
            desde = c8.number_input("Intervalo desde", value=x.intervalo_min if x else None, key=f"{k}a{i}", format="%g")
            hasta = c9.number_input("Hasta", value=x.intervalo_max if x else None, key=f"{k}b{i}", format="%g")
            campos.append((codigo, desc, marca, modelo, serie, mag, resol, desde, hasta))

    def aplicar(e):
        ibcs = [Recurso(c.strip(), d.strip(), "ibc", g, a, b, descripcion=d.strip(), marca=ma.strip(), modelo=mo.strip(),
                        serie=se.strip(), resolucion=r.strip()) for c, d, ma, mo, se, g, r, a, b in campos]
        e.ibcs = ibcs
        if any(not i.codigo or not i.descripcion for i in ibcs):
            return ["Escribe el código y la descripción de cada equipo a evaluar."]
        return []
    return aplicar


def paso_tecnicos(e: Estudio, k: str):
    n = _cantidad("¿Cuántos técnicos participarán?", len(e.tecnicos), f"{k}n", "R01")
    st.caption("Escribe el código y el nombre de cada técnico. Puedes cambiar el código si en tu laboratorio usan otro.")
    campos = []
    for i in range(n):
        t = e.tecnicos[i] if i < len(e.tecnicos) else None
        c1, c2 = st.columns([1, 3])
        campos.append((c1.text_input(f"Código del técnico {i + 1}", t.codigo if t else f"T-{i + 1:02d}", key=f"{k}c{i}"),
                       c2.text_input(f"Nombre del técnico {i + 1}", t.nombre if t else "", key=f"{k}m{i}")))

    def aplicar(e):
        tecnicos = [Recurso(c.strip(), m.strip(), "tecnico") for c, m in campos if c.strip()]
        codigos = [t.codigo.casefold() for t in tecnicos]
        if len(set(codigos)) != len(codigos):
            return ["Hay códigos de técnico repetidos."]
        e.tecnicos = tecnicos
        return [] if tecnicos else ["Agrega al menos un técnico."]
    return aplicar


def paso_patrones(e: Estudio, k: str):
    n = _cantidad("¿Cuántos patrones utilizarás?", len(e.patrones), f"{k}n", "R02")
    st.caption("R03 · Describe cada patrón: identificación, certificado de calibración y el intervalo en que es útil.")
    campos = []
    for i in range(n):
        x = e.patrones[i] if i < len(e.patrones) else None
        with st.container(border=True):
            st.markdown(f"**Patrón {i + 1}**")
            c1, c2 = st.columns([1, 3])
            codigo = c1.text_input("Código", x.codigo if x else f"P-{i + 1:02d}", key=f"{k}c{i}")
            desc = c2.text_input("Descripción del patrón", (x.descripcion or x.nombre) if x else "", key=f"{k}d{i}",
                                 placeholder="Ej.: Termohigrómetro patrón de 9 sensores")
            c3, c4, c5, c6 = st.columns(4)
            marca = c3.text_input("Marca", x.marca if x else "", key=f"{k}ma{i}")
            modelo = c4.text_input("Modelo", x.modelo if x else "", key=f"{k}mo{i}")
            serie = c5.text_input("Número de serie", x.serie if x else "", key=f"{k}s{i}")
            cert = c6.text_input("Certificado", x.certificado if x else "", key=f"{k}ce{i}", help="Número del certificado de calibración vigente")
            c7, c8, c9 = st.columns(3)
            mag = _selector_magnitud(e, c7, x.magnitud_id if x else "", f"{k}g{i}")
            desde = c8.number_input("Útil desde", value=x.intervalo_min if x else None, key=f"{k}a{i}", format="%g")
            hasta = c9.number_input("Útil hasta", value=x.intervalo_max if x else None, key=f"{k}b{i}", format="%g")
            campos.append((codigo, desc, marca, modelo, serie, cert, mag, desde, hasta))

    def aplicar(e):
        patrones = [Recurso(c.strip(), d.strip(), "patron", g, a, b, descripcion=d.strip(), marca=ma.strip(), modelo=mo.strip(),
                            serie=se.strip(), certificado=ce.strip()) for c, d, ma, mo, se, ce, g, a, b in campos if c.strip()]
        errores = []
        if any(not p.descripcion for p in patrones):
            errores.append("Escribe la descripción de cada patrón.")
        codigos = [p.codigo.casefold() for p in patrones]
        if len(set(codigos)) != len(codigos):
            errores.append("Hay códigos de patrón repetidos.")
        e.patrones = patrones
        return errores or ([] if patrones else ["Agrega al menos un patrón."])
    return aplicar


def _factor(e: Estudio, vinculo: str | None = None, nombre: str | None = None) -> Factor | None:
    for f in e.factores:
        if vinculo and f.vinculo_recurso == vinculo:
            return f
        if nombre and f.vinculo_recurso == "ninguno" and f.nombre.casefold() == nombre.casefold():
            return f
    return None


def paso_condiciones(e: Estudio, k: str):
    st.caption("D03 · D04 · Marca solo lo que cambiarás a propósito para comparar. No es obligatorio comparar nada: "
               "si solo repites mediciones en cada punto, deja todo sin marcar.")
    f_dia = _factor(e, nombre="Día")
    estandar = {id(x) for x in (_factor(e, "tecnico"), _factor(e, "patron"), f_dia) if x}
    otras = [f for f in e.factores if id(f) not in estandar]
    otra = otras[0] if otras and otras[0].vinculo_recurso == "ninguno" else None
    c_tec = st.toggle("¿Compararás los resultados entre técnicos?", _factor(e, "tecnico") is not None, key=f"{k}ct",
                      disabled=len(e.tecnicos) < 2, help="Requiere al menos 2 técnicos.")
    c_pat = st.toggle("¿Compararás los resultados entre patrones?", _factor(e, "patron") is not None, key=f"{k}cp",
                      disabled=len(e.patrones) < 2, help="Requiere al menos 2 patrones.")
    c_dia = st.toggle("¿Compararás días o jornadas?", f_dia is not None, key=f"{k}cd")
    dias = st.multiselect("¿Qué días o jornadas?", f_dia.niveles if f_dia else ["Día 1", "Día 2"],
                          default=f_dia.niveles if f_dia else ["Día 1", "Día 2"], accept_new_options=True,
                          key=f"{k}dias", disabled=not c_dia, placeholder="Escribe una opción y presiona Enter")
    c_otra = st.toggle("¿Otra condición?", otra is not None, key=f"{k}co", help="Ej.: posición del sensor, carga del medio")
    c1, c2 = st.columns([1, 2])
    otra_nombre = c1.text_input("Nombre de la condición", otra.nombre if otra else "", key=f"{k}on", disabled=not c_otra)
    otra_niveles = c2.multiselect("Opciones", otra.niveles if otra else [], default=otra.niveles if otra else [],
                                  accept_new_options=True, key=f"{k}ol", disabled=not c_otra,
                                  placeholder="Escribe una opción y presiona Enter")
    st.divider()
    controladas = st.text_area("¿Qué debe mantenerse igual durante las mediciones?", e.condiciones_controladas, key=f"{k}ctl",
                               height=70, help="D05 · Condiciones controladas")
    unidad = st.text_area("¿Qué cuenta como una repetición independiente?", e.unidad_experimental, key=f"{k}ue", height=70,
                          help="D08 · Pendiente técnico. Ej.: una lectura tomada tras la estabilización y un nuevo ciclo de carga.")

    def aplicar(e):
        errores = []
        nuevos = []
        if c_tec and len(e.tecnicos) >= 2:
            nuevos.append(_factor(e, "tecnico") or Factor("", "Técnico", "Persona que realiza la medición", vinculo_recurso="tecnico"))
        if c_pat and len(e.patrones) >= 2:
            nuevos.append(_factor(e, "patron") or Factor("", "Patrón", "Patrón utilizado", vinculo_recurso="patron"))
        if c_dia:
            if len(dias) < 2:
                errores.append("Para comparar días necesitas al menos dos opciones.")
            f = f_dia or Factor("", "Día", "Día o jornada de medición")
            f.niveles = [str(x).strip() for x in dias if str(x).strip()]
            nuevos.append(f)
        if c_otra:
            if not otra_nombre.strip() or len(otra_niveles) < 2:
                errores.append("La otra condición necesita nombre y al menos dos opciones.")
            f = otra or Factor("", "")
            f.nombre, f.niveles = otra_nombre.strip(), [str(x).strip() for x in otra_niveles if str(x).strip()]
            nuevos.append(f)
        conservadas = [f for f in otras if f is not otra]  # condiciones creadas en la edición avanzada
        for f in nuevos:
            if not f.id:
                f.id = siguiente_id("F", [x.id for x in e.factores + nuevos if x.id])
        e.factores = nuevos + conservadas
        e.agrupacion = [a for a in e.agrupacion if a in {"punto", "tecnico", "patron", "equipo"} | {f.id for f in e.factores}] or ["punto"]
        e.condiciones_controladas, e.unidad_experimental = controladas.strip(), unidad.strip()
        return errores
    return aplicar


def paso_variables(e: Estudio, k: str):
    st.caption("D12 · D13 · D14 · Son los valores que anotarás durante cada medición (lecturas originales). "
               "**No** son el error ni la corrección: esos se definen en el paso siguiente.")
    unidad = e.magnitudes[0].unidad if e.magnitudes else ""
    filas = [{"id": v.id, "nombre": v.nombre, "tipo_dato": v.tipo_dato, "unidad": v.unidad, "obligatoria": v.obligatoria,
              "categoria": v.categoria, "descripcion": v.descripcion} for v in e.variables]
    if not filas:
        st.info("Te proponemos dos datos habituales. Cámbialos, bórralos o agrega los que exija tu método.", icon=":material/lightbulb:")
        filas = [{"id": "", "nombre": "Indicación del IBC", "tipo_dato": "decimal", "unidad": unidad, "obligatoria": True,
                  "categoria": "lectura", "descripcion": "Lectura del equipo a evaluar"},
                 {"id": "", "nombre": "Valor del patrón", "tipo_dato": "decimal", "unidad": unidad, "obligatoria": True,
                  "categoria": "lectura", "descripcion": "Lectura del patrón"}]
    ed = st.data_editor(pd.DataFrame(filas), num_rows="dynamic", hide_index=True, width="stretch", key=f"{k}var", column_config={
        "id": None,
        "nombre": st.column_config.TextColumn("Dato que anotarás", width="medium", required=True),
        "tipo_dato": st.column_config.SelectboxColumn("Tipo", options=TIPOS_DATO, default="decimal", required=True),
        "unidad": st.column_config.TextColumn("Unidad", width="small"),
        "obligatoria": st.column_config.CheckboxColumn("¿Obligatorio?", default=True),
        "categoria": st.column_config.SelectboxColumn("Clase", options=CATEGORIAS_VARIABLE, default="lectura"),
        "descripcion": st.column_config.TextColumn("Descripción", width="medium")})

    def aplicar(e):
        nuevas = []
        for r in ed.itertuples():
            if not _txt(r.nombre):
                continue
            existente = next((v for v in e.variables if v.id == _txt(r.id) or v.nombre.casefold() == _txt(r.nombre).casefold()), None)
            vid = existente.id if existente else siguiente_id("V", [v.id for v in nuevas] + [v.id for v in e.variables])
            nuevas.append(Variable(vid, _txt(r.nombre), _txt(r.tipo_dato) or "decimal", _txt(r.unidad), _bool(r.obligatoria, True),
                                   _txt(r.descripcion), _txt(r.categoria) or "lectura"))
        nombres = [v.nombre.casefold() for v in nuevas]
        if len(set(nombres)) != len(nombres):
            return ["Hay datos con el mismo nombre."]
        e.variables = nuevas
        validos = {v.id for v in nuevas} | {r.id for r in e.resultados}
        for r in e.resultados:
            r.dependencias = [d for d in r.dependencias if d in validos]
        return [] if nuevas else ["Agrega al menos un dato a registrar."]
    return aplicar


def paso_resultados(e: Estudio, k: str):
    st.caption("V01–V09 · Activa los valores que necesitas obtener o analizar. Pueden ser varios. "
               "Aquí no se escriben fórmulas: solo de qué datos dependen.")
    unidad = e.magnitudes[0].unidad if e.magnitudes else ""
    nombres_var = {v.nombre: v.id for v in e.variables}
    ids_var = {v: n for n, v in nombres_var.items()}
    candidatos = list(e.resultados)
    existentes = {r.nombre.casefold() for r in e.resultados}
    candidatos += [ResultadoInteres("", s_, unidad=unidad) for s_ in SUGERIDOS if s_.casefold() not in existentes]
    otro = st.text_input("¿Necesitas otro resultado? Escribe su nombre y pulsa «Guardar»", key=f"{k}otro",
                         placeholder="Ej.: Uniformidad")
    campos = []
    for i, r in enumerate(candidatos):
        with st.container(border=True):
            incluir = st.toggle(f"**{r.nombre}**", bool(r.id), key=f"{k}i{i}")
            if incluir:
                c1, c2, c3 = st.columns([1, 2, 2])
                un = c1.text_input("Unidad", r.unidad, key=f"{k}u{i}", help="V03 · Vacía si no aplica")
                origen = c2.segmented_control("¿Cómo se obtiene?", list(ORIGEN_TXT), default=r.origen,
                                              format_func=ORIGEN_TXT.get, key=f"{k}o{i}", help="V04")
                ambito = c3.selectbox("¿A qué mediciones corresponde?", AMBITOS_RESULTADO, index=AMBITOS_RESULTADO.index(r.ambito),
                                      format_func=AMBITO_TXT.get, key=f"{k}a{i}", help="V07")
                deps = st.multiselect("¿De qué datos depende?", list(nombres_var),
                                      default=[ids_var[d] for d in r.dependencias if d in ids_var], key=f"{k}d{i}",
                                      disabled=(origen or r.origen) != "calculado", placeholder="Solo si se calcula",
                                      help="V05")
                c4, c5 = st.columns(2)
                analizar = c4.checkbox("Analizarlo estadísticamente", r.analizar, key=f"{k}x{i}", help="V08 · No elige una prueba")
                criterio = c5.checkbox("Tiene un requisito que cumplir", r.tiene_criterio, key=f"{k}c{i}", help="V09")
                campos.append((r, un, origen or r.origen, ambito, deps, analizar, criterio))

    def aplicar(e):
        nuevos = []
        for r, un, origen, ambito, deps, analizar, criterio in campos:
            res = r if r.id else ResultadoInteres(siguiente_id("R", [x.id for x in nuevos] + [x.id for x in e.resultados]), r.nombre)
            res.unidad, res.origen, res.ambito = un.strip(), origen, ambito
            res.dependencias = [nombres_var[d] for d in deps if d in nombres_var] if origen == "calculado" else []
            res.analizar, res.tiene_criterio = analizar, criterio
            nuevos.append(res)
        if otro.strip() and otro.strip().casefold() not in {x.nombre.casefold() for x in nuevos}:
            nuevos.append(ResultadoInteres(siguiente_id("R", [x.id for x in nuevos] + [x.id for x in e.resultados]), otro.strip(), unidad=unidad))
        if any(x.nombre.casefold() in {v.nombre.casefold() for v in e.variables} for x in nuevos):
            return ["Un resultado no puede llamarse igual que un dato a registrar."]
        e.resultados = nuevos
        e.criterios = [c for c in e.criterios if any(x.id == c.resultado_id for x in nuevos)]
        return [] if nuevos else ["Activa al menos un resultado de interés."]
    return aplicar


def paso_criterios(e: Estudio, k: str):
    st.caption("C01–C03 · Opcional. Registra los requisitos con su fuente. La aplicación no propone límites ni decide conformidad. "
               "Si aún no los tienes, continúa: podrás agregarlos antes de analizar.")
    nombres = {r.nombre: r.id for r in e.resultados}
    inv = {v: n for n, v in nombres.items()}
    filas = [{"id": c.id, "resultado": inv.get(c.resultado_id, ""), "descripcion": c.descripcion, "fuente": c.fuente,
              "version": c.version_fuente, "valor": c.valor, "unidad": c.unidad, "aprobado": c.aprobado} for c in e.criterios]
    ed = st.data_editor(pd.DataFrame(filas, columns=["id", "resultado", "descripcion", "fuente", "version", "valor", "unidad", "aprobado"]),
                        num_rows="dynamic", hide_index=True, width="stretch", key=f"{k}crit", column_config={
                            "id": None,
                            "resultado": st.column_config.SelectboxColumn("Resultado", options=list(nombres), required=True),
                            "descripcion": st.column_config.TextColumn("Requisito", width="medium"),
                            "fuente": st.column_config.TextColumn("¿De dónde sale?", help="C02"),
                            "version": st.column_config.TextColumn("Versión", width="small"),
                            "valor": st.column_config.TextColumn("Valor o condición", help="C03 · Texto; no se interpreta en esta fase"),
                            "unidad": st.column_config.TextColumn("Unidad", width="small"),
                            "aprobado": st.column_config.CheckboxColumn("¿Aprobado?", default=False)})

    def aplicar(e):
        nuevos = []
        for r in ed.itertuples():
            if not _txt(r.resultado):
                continue
            cid = _txt(r.id) or siguiente_id("C", [c.id for c in nuevos] + [c.id for c in e.criterios])
            nuevos.append(Criterio(cid, nombres[_txt(r.resultado)], _txt(r.descripcion), _txt(r.fuente), _txt(r.version),
                                   valor=_txt(r.valor), unidad=_txt(r.unidad), aprobado=_bool(r.aprobado)))
        e.criterios = nuevos
        return []
    return aplicar


def paso_mediciones(e: Estudio, k: str):
    st.caption("D07 · D09 · Elige cómo se combinan los puntos, los recursos y las condiciones. "
               "Nada se crea hasta que revises la vista previa y confirmes.")
    etiquetas = {etiqueta_punto(e, p.id): p.id for p in e.puntos}
    conservar = False
    if e.plan:
        conservar = st.radio("Ya tienes mediciones planificadas", [f"Conservar las {len(e.plan)} mediciones actuales", "Volver a generarlas"],
                             key=f"{k}keep") .startswith("Conservar")
    if conservar:
        st.dataframe(plan_a_dataframe(e), hide_index=True, width="stretch", height=260)
        st.caption("Puedes editarlas fila por fila en Edición avanzada → Diseño experimental → Mediciones planificadas.")
        return lambda e: [] if e.plan else ["No hay mediciones planificadas."]

    puntos = st.multiselect("Puntos", list(etiquetas), default=list(etiquetas), key=f"{k}pts", placeholder="Elige los puntos")
    cruzar, fijos = {}, {}
    f_tec, f_pat = _factor(e, "tecnico"), _factor(e, "patron")
    c1, c2 = st.columns(2)
    if f_tec:
        cruzar["tecnico"] = c1.multiselect("Técnicos que se comparan", [t.codigo for t in e.tecnicos],
                                           default=[t.codigo for t in e.tecnicos], key=f"{k}tec")
    elif e.tecnicos:
        fijos["tecnico"] = c1.selectbox("¿Quién realizará las mediciones?", [t.codigo for t in e.tecnicos], key=f"{k}tecf",
                                        format_func=lambda c: next(f"{t.codigo} · {t.nombre}" if t.nombre else t.codigo for t in e.tecnicos if t.codigo == c))
    if f_pat:
        cruzar["patron"] = c2.multiselect("Patrones que se comparan", [p.codigo for p in e.patrones],
                                          default=[p.codigo for p in e.patrones], key=f"{k}pat")
    elif e.patrones:
        fijos["patron"] = c2.selectbox("¿Con qué patrón?", [p.codigo for p in e.patrones], key=f"{k}patf",
                                       format_func=lambda c: next(f"{p.codigo} · {p.descripcion}" if p.descripcion else p.codigo for p in e.patrones if p.codigo == c))
    for f in e.factores_libres():
        if f.rol == "se_compara" and f.niveles:
            cruzar[f.id] = st.multiselect(f"Opciones de «{f.nombre}»", f.niveles, default=f.niveles, key=f"{k}f{f.id}")
    reps = st.number_input("¿Cuántas mediciones repetirás en cada condición?", 1, 100, e.repeticiones_por_condicion, key=f"{k}reps", help="D07")
    cruzar = {c: v for c, v in cruzar.items() if v}
    base = Estudio.from_dict({**e.to_dict(), "plan": []})
    propuesta = generar_combinaciones(base, [etiquetas[p] for p in puntos], cruzar, int(reps), fijos)
    nombre_campo = {"tecnico": "técnicos", "patron": "patrones"} | {f.id: f"opciones de «{f.nombre}»" for f in e.factores}
    partes = [f"{len(puntos)} puntos"] + [f"{len(v)} {nombre_campo.get(c, c)}" for c, v in cruzar.items()] + [f"{int(reps)} repeticiones"]
    st.markdown(f"**{' × '.join(partes)} = {len(propuesta)} mediciones**")
    if propuesta:
        vista = Estudio.from_dict({**e.to_dict(), "plan": [vars(m) for m in propuesta]})
        st.dataframe(plan_a_dataframe(vista), hide_index=True, width="stretch", height=240)
    if len(propuesta) > 600:
        st.warning("Son más de 600 mediciones. Revisa si todas esas combinaciones son necesarias.")
    confirmar = st.checkbox("Confirmo que estas son las mediciones que haré", key=f"{k}ok")

    def aplicar(e):
        if not confirmar:
            return ["Revisa la vista previa y confirma las mediciones."]
        if not propuesta:
            return ["No hay mediciones: elige al menos un punto."]
        e.plan = propuesta
        e.repeticiones_por_condicion = int(reps)
        return []
    return aplicar


def paso_plantilla(e: Estudio, k: str):
    repo = repositorio()
    st.markdown(f"**{e.codigo} · {e.nombre}** · {e.tipo} del método **{e.metodo or '—'}** (versión {e.version_metodo or '—'})")
    c = st.columns(4)
    c[0].metric("Puntos", len(e.puntos), border=True)
    c[1].metric("Técnicos · patrones", f"{len(e.tecnicos)} · {len(e.patrones)}", border=True)
    c[2].metric("Datos · resultados", f"{len(e.variables)} · {len(e.resultados)}", border=True)
    c[3].metric("Mediciones", len(e.plan), border=True)
    with st.expander("Ver el resumen completo"):
        st.markdown(
            f"- **Magnitudes:** {', '.join(f'{m.nombre} [{m.unidad}] ({m.intervalo_min:g} a {m.intervalo_max:g})' for m in e.magnitudes if m.intervalo_min is not None and m.intervalo_max is not None)}\n"
            f"- **Puntos:** {', '.join(etiqueta_punto(e, p.id) for p in e.puntos)}\n"
            f"- **Equipo a evaluar:** {', '.join(f'{i.codigo} · {i.descripcion}' for i in e.ibcs)}\n"
            f"- **Técnicos:** {', '.join(f'{t.codigo} {t.nombre}'.strip() for t in e.tecnicos)}\n"
            f"- **Patrones:** {', '.join(f'{p.codigo} · {p.descripcion}' for p in e.patrones)}\n"
            f"- **Condiciones que se comparan:** {', '.join(f.nombre for f in e.factores if f.rol == 'se_compara') or 'ninguna (solo repeticiones por punto)'}\n"
            f"- **Datos a registrar:** {', '.join(v.nombre for v in e.variables)}\n"
            f"- **Resultados de interés:** {', '.join(f'{r.nombre} ({ORIGEN_TXT[r.origen].lower()})' for r in e.resultados)}")
    ok, faltantes = listo_para_aprobar(e)
    advertencias = [a for et in revisar_estudio(e) for a in et.advertencias]
    if not ok:
        st.error("Antes de generar la plantilla falta:\n\n" + "\n".join(f"- {f}" for f in faltantes))
    for a in advertencias[:6]:
        st.caption(f":material/info: {a}")
    vigente = e.estado == "aprobado" and e.version_diseno >= 1
    if vigente:
        st.success(f"Diseño aprobado · versión {e.version_diseno}. Tu plantilla está lista.", icon=":material/verified:")
    else:
        revisado = st.checkbox("Revisé la información y apruebo este diseño (P05)", key=f"{k}rev", disabled=not ok)
        if st.button("Generar plantilla de datos", type="primary", icon=":material/table_view:", disabled=not (ok and revisado), width="stretch"):
            repo.guardar_estudio(e, usuario(), "asistente: revisión final")
            repo.aprobar_version(e, usuario())
            st.session_state["ir_paso"] = TOTAL - 1  # se queda en este paso, ya aprobado
            return "recargar"
    if vigente:
        st.download_button("Descargar plantilla de datos (Excel)", generar_plantilla(e), file_name=nombre_archivo_plantilla(e),
                           type="primary", icon=":material/download:", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.caption("Llénala con tus mediciones (columnas moradas) y continúa con «Subir DB».")
    return lambda e: [] if (e.estado == "aprobado" and e.version_diseno >= 1) else ["Primero genera la plantilla."]


def paso_subir(e: Estudio, k: str):
    repo = repositorio()
    if e.version_diseno < 1:
        st.warning("Primero genera la plantilla en el paso anterior.")
        return lambda e: []
    st.caption("X05 · X06 · Sube la plantilla diligenciada. El sistema guarda el original, comprueba que corresponde a este estudio "
               "y a esta versión, y revisa la calidad de los datos.")
    archivo = st.file_uploader("Plantilla diligenciada (.xlsx)", type=["xlsx"], key=f"{k}file")
    if st.button("Subir y verificar", type="primary", icon=":material/upload:", disabled=archivo is None, width="stretch"):
        carga = cargar_archivo(repo, e.codigo, archivo.getvalue(), archivo.name, usuario(), e.version_diseno)
        st.session_state["ultima_carga"] = carga["carga_id"]
    carga_id = st.session_state.get("ultima_carga")
    cargas = {c["carga_id"] for c in repo.listar_cargas(e.codigo)}
    if carga_id in cargas:
        carga = repo.obtener_carga(e.codigo, carga_id)
        ev = carga["evaluacion_inicial"]
        st.markdown(f"**Resultado de la carga** `{carga_id}` · {carga['nombre_archivo']}")
        for nivel, texto in resumen_mensajes(ev):
            getattr(st, nivel)(texto)
        metricas_conteos(ev["conteos"])
        if ev["incidencias"]:
            with st.expander(f"Incidencias ({len(ev['incidencias'])})", expanded=True):
                for i in ev["incidencias"][:60]:
                    st.markdown(f"- **{i['regla']}** · {i['mensaje']}")
        if ev["registros"]:
            estados = pd.Series([ETIQUETA_ESTADO[r["estado"]][0] for r in ev["registros"]]).value_counts()
            st.caption("Estados: " + " · ".join(f"{n}: {v}" for n, v in estados.items()))
        st.info("Hasta aquí llega esta etapa. La revisión de calidad y la preparación del conjunto están en el menú «Datos».",
                icon=":material/flag:")
    return lambda e: []


FUNCIONES = [paso_estudio, paso_metodo, paso_magnitudes, paso_puntos, paso_ibc, paso_tecnicos, paso_patrones, paso_condiciones,
             paso_variables, paso_resultados, paso_criterios, paso_mediciones, paso_plantilla, paso_subir]


def estado_pasos(e: Estudio) -> list[bool]:
    """Qué pasos ya están completos (para la barra de pasos)."""
    m = {et.clave: et for et in revisar_estudio(e)}
    return [
        bool(e.nombre and e.tipo),
        bool(e.metodo and e.version_metodo and e.uso_previsto and e.responsable),
        bool(e.magnitudes) and not any("magnitud" in f.lower() or "Intervalo" in f for f in m["alcance"].faltantes),
        bool(e.puntos),
        bool(e.ibcs) and all(i.descripcion for i in e.ibcs),
        bool(e.tecnicos),
        bool(e.patrones) and all(p.descripcion for p in e.patrones),
        m["condiciones"].completa,
        bool(e.variables) and m["variables"].completa,
        bool(e.resultados) and m["resultados"].completa,
        bool(e.criterios),
        bool(e.plan) and m["plan"].completa,
        e.estado == "aprobado" and e.version_diseno >= 1,
        bool(repositorio().listar_cargas(e.codigo)),
    ]


# ---------------------------------------------------------------- render
def cerrar_panel() -> None:
    st.session_state["asistente_abierto"] = False
    st.session_state.pop("crear_nuevo", None)


@st.dialog("Crear estudio", width="large", position="right", on_dismiss=cerrar_panel, icon=":material/add_task:")
def panel() -> None:
    """Panel lateral flotante del asistente."""
    from interfaz.comun import estudio_actual
    e = estudio_actual()
    if e is None or st.session_state.get("crear_nuevo"):
        crear_estudio_dialogo()
    else:
        render(e, en_panel=True)


def render(e: Estudio, en_panel: bool) -> None:
    repo = repositorio()
    alcance = "fragment" if en_panel else "app"
    paso = min(max(int(st.session_state.pop("ir_paso", e.paso_asistente) or 1), 1), TOTAL)
    completos = estado_pasos(e)
    k = f"a{paso}_{e.codigo}_{e.actualizado_en}_"

    def mover(destino: int, aplicar, exigir: bool):
        errores = aplicar(e) if aplicar else []
        if errores and exigir:
            for x in errores:
                st.error(x, icon=":material/error:")
            return
        e.paso_asistente = destino
        repo.guardar_estudio(e, usuario() or "sin identificar", f"asistente: paso {paso} ({PASOS[paso - 1][0]})")
        st.rerun(scope=alcance)

    if en_panel:
        st.progress(paso / TOTAL, text=f"Paso {paso} de {TOTAL} · {PASOS[paso - 1][0]}")
        destino = st.selectbox("Ir a un paso", range(1, TOTAL + 1), index=paso - 1, key=f"sel_{k}",
                               format_func=lambda i: f"{'✓' if completos[i - 1] else '○'} {i}. {PASOS[i - 1][0]}")
        cuerpo, lateral = st.container(), None
    else:
        lateral, cuerpo = st.columns([1, 3], gap="large")
        destino = paso

    with cuerpo:
        titulo, icono = PASOS[paso - 1]
        st.markdown(f"### {icono} {titulo}")
        aplicar = FUNCIONES[paso - 1](e, k)
        if aplicar == "recargar":
            st.rerun(scope=alcance)
        st.space("small")
        if paso < TOTAL:
            b1, b2, b3 = st.columns([1, 1, 2])
            if paso > 1 and b1.button("Anterior", icon=":material/arrow_back:", key=f"ant_{k}", width="stretch"):
                mover(paso - 1, aplicar, exigir=False)
            if b2.button("Guardar", icon=":material/save:", key=f"gua_{k}", width="stretch"):
                mover(paso, aplicar, exigir=False)
            siguiente = "Siguiente: Subir DB" if paso == TOTAL - 1 else "Guardar y continuar"
            if b3.button(siguiente, type="primary", icon=":material/arrow_forward:", key=f"sig_{k}", width="stretch"):
                mover(paso + 1, aplicar, exigir=True)
        else:
            if st.button("Anterior", icon=":material/arrow_back:", key=f"ant_{k}"):
                mover(paso - 1, None, exigir=False)

    if lateral is not None:
        with lateral:
            st.caption(f"{e.codigo} · paso {paso} de {TOTAL}")
            st.progress(sum(completos) / TOTAL)
            for i, (nombre, ic) in enumerate(PASOS, start=1):
                marca = ":green[:material/check_circle:]" if completos[i - 1] else ":gray[:material/radio_button_unchecked:]"
                if st.button(f"{marca} {i}. {nombre}", key=f"lat_{i}_{k}", type="secondary" if i == paso else "tertiary",
                             width="stretch"):
                    mover(i, aplicar, exigir=False)
    elif destino != paso:
        mover(destino, aplicar, exigir=False)
