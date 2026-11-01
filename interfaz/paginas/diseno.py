import pandas as pd
import streamlit as st

from interfaz.comun import (
    PAGINAS, badge_estado_diseno, banda_de_pasos, encabezado, guardar, repositorio, requerir_estudio,
    requerir_usuario, tabla, usuario,
)
from src.configuracion.validacion_estudio import (
    listo_para_aprobar, revisar_condiciones, revisar_criterios, revisar_estudio, revisar_plan, revisar_resultados,
    revisar_variables,
)
from src.modelos.estudio import (
    AMBITOS_RESULTADO, CATEGORIAS_VARIABLE, TIPOS_DATO, Criterio, Factor, Restriccion, ResultadoInteres, Variable,
    siguiente_id,
)
from src.planificacion import plan as pl

AMBITO_TXT = {"medicion": "Cada medición", "serie": "Una serie (repeticiones de una misma condición)", "punto": "Un punto de medición",
              "condicion": "Un grupo comparable (según cómo agrupas)", "estudio": "Todo el estudio", "otro": "Otro grupo (lo describes)"}
ROL_TXT = {"se_compara": "La cambiaré para comparar", "solo_se_registra": "Solo la registraré"}
VINCULO_TXT = {"ninguno": "Opciones propias", "tecnico": "Catálogo de técnicos", "patron": "Catálogo de patrones", "equipo": "Catálogo de equipos"}
SUGERENCIAS = {"Técnico": "tecnico", "Patrón": "patron", "Equipo": "equipo", "Día": "ninguno", "Franja horaria": "ninguno",
               "Condición ambiental": "ninguno", "Otra condición": "ninguno"}


def _txt(v) -> str:
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def _estado(etapa) -> None:
    if etapa.completa:
        st.success("Sección completa.", icon=":material/check_circle:")
    else:
        st.warning("Falta: " + " · ".join(etapa.faltantes[:6]) + (" …" if len(etapa.faltantes) > 6 else ""), icon=":material/pending:")
    for a in etapa.advertencias[:8]:
        st.caption(f":material/info: {a}")


encabezado("Paso 2", "Diseño experimental",
           "Define qué condiciones compararás, qué datos registrarás, qué resultados necesitas y cuáles mediciones harás.")
e = requerir_estudio()
repo = repositorio()
banda_de_pasos(e)
badge_estado_diseno(e)
if e.estado == "aprobado":
    st.info("El diseño está aprobado. Si lo modificas, volverá a borrador y deberás aprobar una nueva versión; "
            "las versiones anteriores y sus plantillas se conservan.", icon=":material/lock_open:")

t_cond, t_datos, t_res, t_crit, t_plan, t_apr = st.tabs([
    ":material/tune: Condiciones", ":material/edit_note: Datos a registrar", ":material/target: Resultados de interés",
    ":material/rule: Criterios", ":material/calendar_month: Mediciones planificadas", ":material/verified: Revisión y aprobación",
])
clave = e.actualizado_en

# ===================================================================== Condiciones
with t_cond:
    _estado(revisar_condiciones(e))
    st.markdown("##### ¿Qué condiciones quieres comparar?")
    st.caption("D03 · Técnicamente son los *factores experimentales*. Agrega solo las que cambiarás intencionalmente o que quieras registrar. "
               "No es obligatorio que todas varíen a la vez, y el sistema no creará combinaciones automáticamente.")
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    sugerida = c1.pills("Sugerencias", list(SUGERENCIAS), key=f"pill_{clave}")
    if c2.button("Agregar condición", icon=":material/add:", disabled=not sugerida, width="stretch") and requerir_usuario():
        vinculo = SUGERENCIAS[sugerida]
        if vinculo != "ninguno" and any(f.vinculo_recurso == vinculo for f in e.factores):
            st.error(f"Ya existe una condición vinculada al catálogo de {sugerida.lower()}s.")
        else:
            nombre = "Nueva condición" if sugerida == "Otra condición" else sugerida
            e.factores.append(Factor(siguiente_id("F", [f.id for f in e.factores]), nombre, vinculo_recurso=vinculo,
                                     rol="solo_se_registra" if sugerida == "Condición ambiental" else "se_compara"))
            guardar(e, f"condición agregada: {nombre}")
            st.rerun()

    if not e.factores:
        with st.container(border=True):
            st.markdown(":material/tune: **Aún no hay condiciones.** Si tu estudio solo repite mediciones en cada punto, puedes continuar sin ellas.")

    for f in list(e.factores):
        with st.container(border=True):
            with st.form(f"factor_{f.id}_{clave}", border=False):
                cab1, cab2 = st.columns([3, 2])
                nombre = cab1.text_input("Nombre de la condición", f.nombre, key=f"fn_{f.id}_{clave}")
                rol = cab2.segmented_control("¿Qué harás con ella?", list(ROL_TXT), format_func=ROL_TXT.get, default=f.rol,
                                             key=f"fr_{f.id}_{clave}", help="D15 · Separar un factor que se compara de un dato que solo se registra.")
                descripcion = st.text_input("Descripción (opcional)", f.descripcion, key=f"fd_{f.id}_{clave}")
                if f.vinculo_recurso != "ninguno":
                    catalogo = {"tecnico": e.tecnicos, "patron": e.patrones, "equipo": e.equipos}[f.vinculo_recurso]
                    st.caption(f":material/link: Sus opciones vienen del {VINCULO_TXT[f.vinculo_recurso].lower()}: "
                               + (", ".join(r.codigo for r in catalogo) or "aún vacío (complétalo en Estudios → Recursos)"))
                    niveles, tipo_valor, unidad = [], "categorico", ""
                else:
                    d1, d2 = st.columns([1, 1])
                    tipo_valor = d1.segmented_control("Tipo de valor", ["categorico", "numerico"], default=f.tipo_valor,
                                                      format_func={"categorico": "Categorías", "numerico": "Números"}.get, key=f"ft_{f.id}_{clave}")
                    unidad = d2.text_input("Unidad (si aplica)", f.unidad, key=f"fu_{f.id}_{clave}")
                    niveles = st.multiselect("¿Qué opciones o valores tendrá?", options=f.niveles, default=f.niveles,
                                             accept_new_options=True, key=f"fo_{f.id}_{clave}", placeholder="Escribe una opción y presiona Enter",
                                             help="D04 · Escribe una opción y presiona Enter. Ej.: Día 1, Día 2.")
                b1, b2, _ = st.columns([1, 1, 3])
                if b1.form_submit_button("Guardar", type="primary", icon=":material/save:") and requerir_usuario():
                    f.nombre, f.descripcion, f.rol = nombre.strip(), descripcion.strip(), rol or f.rol
                    if f.vinculo_recurso == "ninguno":
                        quitadas = set(f.niveles) - set(niveles)
                        if any(m.niveles.get(f.id) in quitadas for m in e.plan):
                            st.error("Algunas opciones que quitaste se usan en el plan. Cámbialas primero en las mediciones planificadas.")
                        else:
                            f.niveles, f.tipo_valor, f.unidad = [str(n).strip() for n in niveles if str(n).strip()], tipo_valor or "categorico", unidad.strip()
                            guardar(e, f"condición {f.id}")
                            st.rerun()
                    else:
                        guardar(e, f"condición {f.id}")
                        st.rerun()
                if b2.form_submit_button("Eliminar", icon=":material/delete:") and requerir_usuario():
                    if any(f.id in m.niveles for m in e.plan) or f.id in e.agrupacion:
                        st.error("Esta condición se usa en el plan o en la agrupación. Quítala de allí primero.")
                    else:
                        e.factores = [x for x in e.factores if x.id != f.id]
                        guardar(e, f"condición eliminada {f.id}")
                        st.rerun()

    st.markdown("##### Estructura de las comparaciones")
    with st.form(f"estructura_{clave}"):
        opciones = {"punto": "Punto de medición", "tecnico": "Técnico", "patron": "Patrón", "equipo": "Equipo"}
        opciones.update({f.id: f.nombre for f in e.factores_libres()})
        agrupacion = st.multiselect("¿Qué mediciones deben compararse entre sí?", list(opciones), default=[a for a in e.agrupacion if a in opciones],
                                    format_func=opciones.get, placeholder="Elige uno o varios campos", help="D06 · Los grupos comparables se forman con estos campos. Incluir el punto evita mezclar puntos nominales distintos.")
        c1, c2 = st.columns([1, 2])
        reps = c1.number_input("¿Cuántas mediciones repetirás por condición?", min_value=1, max_value=100, value=e.repeticiones_por_condicion,
                               help="D07 · Valor sugerido para el planificador. Puede variar fila por fila si el diseño lo requiere.")
        controladas = c2.text_area("¿Qué debe mantenerse igual?", e.condiciones_controladas, height=80, help="D05 · Condiciones controladas.")
        unidad_exp = st.text_area("¿Qué cuenta como una repetición independiente?", e.unidad_experimental, height=80,
                                  help="D08 · Unidad experimental e independencia. Pendiente técnico: descríbelo antes de aprobar.")
        if st.form_submit_button("Guardar estructura", type="primary", icon=":material/save:") and requerir_usuario():
            e.agrupacion, e.repeticiones_por_condicion = agrupacion, int(reps)
            e.condiciones_controladas, e.unidad_experimental = controladas.strip(), unidad_exp.strip()
            guardar(e, "estructura de comparaciones")
            st.rerun()

    with st.expander("¿Hay combinaciones que no se pueden hacer? (opcional)", icon=":material/block:"):
        st.caption("D11 · Ej.: un técnico que no está autorizado para un patrón. Las filas del plan que las incumplan se marcarán como error.")
        campos = {"tecnico": "Técnico", "patron": "Patrón", "equipo": "Equipo", "punto": "Punto (código)"}
        campos.update({f.id: f.nombre for f in e.factores_libres()})
        with st.form(f"restricciones_{clave}", border=False):
            df_r = pd.DataFrame([vars(r) for r in e.restricciones], columns=["campo_a", "valor_a", "campo_b", "valor_b", "motivo"])
            ed = st.data_editor(df_r, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_res_{clave}", column_config={
                "campo_a": st.column_config.SelectboxColumn("Campo A", options=list(campos), required=True),
                "valor_a": st.column_config.TextColumn("Valor A", required=True),
                "campo_b": st.column_config.SelectboxColumn("Campo B", options=list(campos), required=True),
                "valor_b": st.column_config.TextColumn("Valor B", required=True),
                "motivo": st.column_config.TextColumn("Motivo")})
            st.caption("Campos: " + " · ".join(f"`{k}` = {v}" for k, v in campos.items()))
            if st.form_submit_button("Guardar restricciones", icon=":material/save:") and requerir_usuario():
                e.restricciones = [Restriccion(_txt(r.campo_a), _txt(r.valor_a), _txt(r.campo_b), _txt(r.valor_b), _txt(r.motivo))
                                   for r in ed.itertuples() if _txt(r.campo_a) and _txt(r.campo_b)]
                guardar(e, "restricciones del diseño")
                st.rerun()

# ===================================================================== Datos a registrar
with t_datos:
    _estado(revisar_variables(e))
    st.markdown("##### ¿Qué datos registrarás realmente en cada medición?")
    st.caption("D12 · D13 · D14 · Son los valores originales (lecturas, datos propios del método, condiciones ambientales). "
               "**No** son resultados de interés: el error o la corrección se definen en la pestaña siguiente.")
    with st.form(f"variables_{clave}"):
        df_v = pd.DataFrame([vars(v) for v in e.variables], columns=["id", "nombre", "tipo_dato", "unidad", "obligatoria", "categoria", "descripcion"])
        ed = st.data_editor(df_v, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_var_{clave}", column_config={
            "id": st.column_config.TextColumn("Código", disabled=True, width="small"),
            "nombre": st.column_config.TextColumn("Dato", required=True, help="Ej.: Indicación del equipo"),
            "tipo_dato": st.column_config.SelectboxColumn("Tipo", options=TIPOS_DATO, required=True, default="decimal"),
            "unidad": st.column_config.TextColumn("Unidad", width="small"),
            "obligatoria": st.column_config.CheckboxColumn("¿Obligatorio?", default=True),
            "categoria": st.column_config.SelectboxColumn("Clase", options=CATEGORIAS_VARIABLE, default="lectura",
                                                          help="lectura · dato_del_metodo · ambiental"),
            "descripcion": st.column_config.TextColumn("Descripción", width="large")})
        if st.form_submit_button("Guardar datos a registrar", type="primary", icon=":material/save:") and requerir_usuario():
            nuevas = []
            for r in ed.itertuples():
                if not _txt(r.nombre):
                    continue
                vid = _txt(r.id) or siguiente_id("V", [v.id for v in nuevas] + [v.id for v in e.variables])
                nuevas.append(Variable(vid, _txt(r.nombre), _txt(r.tipo_dato) or "decimal", _txt(r.unidad),
                                       bool(r.obligatoria) if r.obligatoria is not None and not pd.isna(r.obligatoria) else True,
                                       _txt(r.descripcion), _txt(r.categoria) or "lectura"))
            usadas = {d for res in e.resultados for d in res.dependencias if d.startswith("V-")}
            faltan = usadas - {v.id for v in nuevas}
            if faltan:
                st.error(f"Estos datos son origen de un resultado de interés y no pueden eliminarse: {', '.join(sorted(faltan))}.")
            else:
                e.variables = nuevas
                guardar(e, "datos a registrar")
                st.rerun()

# ===================================================================== Resultados de interés
with t_res:
    _estado(revisar_resultados(e))
    st.markdown("##### ¿Qué valores necesitas obtener o analizar?")
    st.caption("V01 · Un estudio puede tener varios resultados (error, corrección, inestabilidad, inhomogeneidad u otros). "
               "Los nombres sugeridos son ejemplos, no campos obligatorios. Aquí **no** se definen fórmulas.")
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    sug = c1.pills("Sugerencias", ["Error", "Corrección", "Inestabilidad", "Inhomogeneidad", "Personalizado"], key=f"pres_{clave}")
    if c2.button("Agregar resultado", icon=":material/add:", disabled=not sug, width="stretch", key="add_res") and requerir_usuario():
        nombre = "Nuevo resultado" if sug == "Personalizado" else sug
        if any(r.nombre.casefold() == nombre.casefold() for r in e.resultados):
            st.error(f"Ya existe un resultado llamado «{nombre}».")
        else:
            e.resultados.append(ResultadoInteres(siguiente_id("R", [r.id for r in e.resultados]), nombre))
            guardar(e, f"resultado agregado: {nombre}")
            st.rerun()
    opciones_dep = {v.id: f"{v.nombre} (dato)" for v in e.variables} | {r.id: f"{r.nombre} (resultado)" for r in e.resultados}
    for r in list(e.resultados):
        with st.container(border=True):
            with st.form(f"res_{r.id}_{clave}", border=False):
                st.markdown(f"**{r.id}**")
                a1, a2, a3 = st.columns([2, 1, 2])
                nombre = a1.text_input("Nombre que verá el usuario", r.nombre, key=f"rn_{r.id}_{clave}")
                unidad = a2.text_input("¿En qué unidad?", r.unidad, key=f"ru_{r.id}_{clave}", help="V03 · Déjala vacía si no aplica.")
                origen = a3.segmented_control("¿Cómo obtendrás este valor?", ["directo", "calculado"], default=r.origen, key=f"ro_{r.id}_{clave}",
                                              format_func={"directo": "Lo escribo yo", "calculado": "Se calculará"}.get, help="V04")
                b1, b2 = st.columns(2)
                ambito = b1.selectbox("¿A qué mediciones corresponde?", AMBITOS_RESULTADO, index=AMBITOS_RESULTADO.index(r.ambito),
                                      format_func=AMBITO_TXT.get, key=f"ra_{r.id}_{clave}", help="V07 · Evita forzar valores de grupo en cada fila.")
                proposito = b2.selectbox("¿Por qué lo necesitas?", ["exigido_por_el_metodo", "objetivo_del_estudio"],
                                         index=["exigido_por_el_metodo", "objetivo_del_estudio"].index(r.proposito),
                                         format_func={"exigido_por_el_metodo": "Lo exige el método", "objetivo_del_estudio": "Por el objetivo del estudio"}.get,
                                         key=f"rp_{r.id}_{clave}", help="V02")
                ref_prop = st.text_input("Referencia documental (opcional)", r.referencia_proposito, key=f"rrp_{r.id}_{clave}")
                deps = st.multiselect("¿Qué información necesita para obtenerse?", [k for k in opciones_dep if k != r.id],
                                      default=[d for d in r.dependencias if d in opciones_dep], format_func=opciones_dep.get,
                                      key=f"rd_{r.id}_{clave}", placeholder="Elige datos o resultados", help="V05 · Solo si se calcula. No hace falta definir la fórmula ahora.")
                ref_calc = st.text_input("Referencia del procedimiento de cálculo", r.referencia_calculo, key=f"rc_{r.id}_{clave}",
                                         help="V06 · Pendiente técnico. Referencia o versión del procedimiento aprobado; no una fórmula.")
                c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
                analizar = c1.toggle("Analizar estadísticamente", r.analizar, key=f"rx_{r.id}_{clave}", help="V08 · No elige una prueba.")
                criterio = c2.toggle("Tiene criterio de evaluación", r.tiene_criterio, key=f"rk_{r.id}_{clave}", help="V09")
                if c3.form_submit_button("Guardar", type="primary", icon=":material/save:") and requerir_usuario():
                    r.nombre, r.unidad, r.origen, r.ambito, r.proposito = nombre.strip(), unidad.strip(), origen or r.origen, ambito, proposito
                    r.referencia_proposito, r.dependencias, r.referencia_calculo = ref_prop.strip(), deps, ref_calc.strip()
                    r.analizar, r.tiene_criterio = analizar, criterio
                    guardar(e, f"resultado {r.id}")
                    st.rerun()
                if c4.form_submit_button("Eliminar", icon=":material/delete:") and requerir_usuario():
                    if any(r.id in x.dependencias for x in e.resultados) or any(c.resultado_id == r.id for c in e.criterios):
                        st.error("Otro resultado o un criterio depende de este resultado.")
                    else:
                        e.resultados = [x for x in e.resultados if x.id != r.id]
                        guardar(e, f"resultado eliminado {r.id}")
                        st.rerun()

# ===================================================================== Criterios
with t_crit:
    _estado(revisar_criterios(e))
    st.markdown("##### ¿Hay requisitos que deban comprobarse?")
    st.caption("C01 · C02 · C03 · Relaciona cada criterio con su resultado y su fuente. La aplicación no propone límites ni tolerancias, "
               "no los interpreta y no decide conformidad: solo los registra para la fase de evaluación.")
    nombres_res = {r.id: f"{r.id} · {r.nombre}" for r in e.resultados}
    if not e.resultados:
        st.info("Define primero los resultados de interés.", icon=":material/arrow_back:")
    else:
        with st.form(f"criterios_{clave}"):
            df_c = pd.DataFrame([vars(c) for c in e.criterios],
                                columns=["id", "resultado_id", "descripcion", "fuente", "version_fuente", "operador", "valor", "unidad", "condiciones", "aprobado"])
            ed = st.data_editor(df_c, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_crit_{clave}", column_config={
                "id": st.column_config.TextColumn("Código", disabled=True, width="small"),
                "resultado_id": st.column_config.SelectboxColumn("Resultado", options=list(nombres_res), required=True),
                "descripcion": st.column_config.TextColumn("Requisito"),
                "fuente": st.column_config.TextColumn("Fuente", help="C02 · Documento o requisito técnicamente aprobado"),
                "version_fuente": st.column_config.TextColumn("Versión", width="small"),
                "operador": st.column_config.TextColumn("Comparación", width="small", help="C03 · Por definir; texto libre"),
                "valor": st.column_config.TextColumn("Valor", width="small"),
                "unidad": st.column_config.TextColumn("Unidad", width="small"),
                "condiciones": st.column_config.TextColumn("Condiciones"),
                "aprobado": st.column_config.CheckboxColumn("¿Aprobado?", default=False)})
            if st.form_submit_button("Guardar criterios", type="primary", icon=":material/save:") and requerir_usuario():
                nuevos = []
                for c in ed.itertuples():
                    if not _txt(c.resultado_id):
                        continue
                    cid = _txt(c.id) or siguiente_id("C", [x.id for x in nuevos] + [x.id for x in e.criterios])
                    nuevos.append(Criterio(cid, _txt(c.resultado_id), _txt(c.descripcion), _txt(c.fuente), _txt(c.version_fuente),
                                           _txt(c.operador), _txt(c.valor), _txt(c.unidad), _txt(c.condiciones),
                                           bool(c.aprobado) if c.aprobado is not None and not pd.isna(c.aprobado) else False))
                e.criterios = nuevos
                guardar(e, "criterios de evaluación")
                st.rerun()

# ===================================================================== Plan
with t_plan:
    _estado(revisar_plan(e))
    resumen = pl.resumen_plan(e)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mediciones", resumen["mediciones"], border=True)
    m2.metric("Puntos", resumen["puntos"], border=True)
    m3.metric("Condiciones distintas", resumen["condiciones"], border=True)
    m4.metric("Grupos comparables", resumen["grupos_comparables"], border=True)
    if not e.puntos:
        st.info("Primero define los puntos de medición en Estudios → Magnitudes y puntos.", icon=":material/arrow_back:")

    with st.expander("Generar combinaciones (opcional y explícito)", icon=":material/auto_awesome:"):
        st.caption("D09 · Elige qué cruzar. Nada se agrega al plan hasta que revises la vista previa y lo confirmes.")
        etiquetas = pl.mapa_etiquetas_punto(e)
        puntos_sel = st.multiselect("Puntos", list(etiquetas), default=list(etiquetas), key=f"g_pt_{clave}", placeholder="Elige los puntos")
        campos = []
        if e.tecnicos:
            campos.append(("tecnico", "Técnico", [t.codigo for t in e.tecnicos]))
        if e.patrones:
            campos.append(("patron", "Patrón", [p.codigo for p in e.patrones]))
        if e.equipos:
            campos.append(("equipo", "Equipo", [x.codigo for x in e.equipos]))
        campos += [(f.id, f.nombre, f.niveles) for f in e.factores_libres() if f.rol == "se_compara" and f.niveles]
        cruzar, fijos = {}, {}
        for cid, nombre, opciones in campos:
            g1, g2 = st.columns([1, 2])
            modo = g1.segmented_control(nombre, ["No incluir", "Valor fijo", "Cruzar"], default="No incluir", key=f"g_m_{cid}_{clave}")
            if modo == "Valor fijo":
                fijos[cid] = g2.selectbox(f"Valor de {nombre}", opciones, key=f"g_f_{cid}_{clave}")
            elif modo == "Cruzar":
                elegidas = g2.multiselect(f"Opciones de {nombre} a cruzar", opciones, default=opciones, key=f"g_c_{cid}_{clave}", placeholder="Elige opciones")
                if elegidas:
                    cruzar[cid] = elegidas
        reps = st.number_input("Repeticiones por condición", 1, 100, e.repeticiones_por_condicion, key=f"g_r_{clave}")
        propuesta = pl.generar_combinaciones(e, [etiquetas[p] for p in puntos_sel], cruzar, int(reps), fijos)
        st.markdown(f"**Vista previa:** {len(propuesta)} mediciones")
        if propuesta:
            vista = type(e).from_dict({**e.to_dict(), "plan": [vars(m) for m in propuesta]})
            tabla(pl.plan_a_dataframe(vista).head(40))
        confirmar = st.checkbox("Confirmo que estas combinaciones corresponden al diseño que voy a aprobar", key=f"g_ok_{clave}")
        b1, b2 = st.columns(2)
        if b1.button("Agregar al plan", icon=":material/playlist_add:", disabled=not (confirmar and propuesta), width="stretch") and requerir_usuario():
            e.plan = e.plan + propuesta
            guardar(e, f"{len(propuesta)} mediciones generadas y agregadas")
            st.rerun()
        if b2.button("Reemplazar el plan actual", icon=":material/swap_horiz:", disabled=not (confirmar and propuesta), width="stretch") and requerir_usuario():
            e.plan = []
            e.plan = pl.generar_combinaciones(e, [etiquetas[p] for p in puntos_sel], cruzar, int(reps), fijos)
            guardar(e, f"plan reemplazado por {len(e.plan)} mediciones generadas")
            st.rerun()

    with st.expander("Importar una planificación (CSV o Excel)", icon=":material/upload:"):
        st.caption("Columnas: Punto, Repetición y, si aplica, Técnico, Patrón, Equipo, una por condición, Fecha prevista (AAAA-MM-DD), Franja prevista, Orden. "
                   "Puedes descargar el plan actual, editarlo y volverlo a importar.")
        st.download_button("Descargar plan actual (CSV)", pl.plan_a_dataframe(e).to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"plan_{e.codigo}.csv", icon=":material/download:")
        archivo = st.file_uploader("Archivo de planificación", type=["csv", "xlsx"], key=f"imp_{clave}")
        if archivo and st.button("Importar y reemplazar el plan", icon=":material/upload:") and requerir_usuario():
            nuevo, errores = pl.importar_plan(e, archivo.getvalue(), archivo.name)
            if errores:
                for x in errores[:10]:
                    st.error(x)
            else:
                e.plan = nuevo
                guardar(e, f"plan importado ({len(nuevo)} mediciones)")
                st.rerun()

    st.markdown("##### Mediciones planificadas")
    st.caption("D09 · D10 · P02 · P03 · P04 · Una fila por medición. Agrega filas con «+». El identificador se asigna al guardar. "
               "La repetición se numera dentro de cada condición; mediciones en puntos distintos no son repeticiones entre sí.")
    with st.form(f"plan_{clave}"):
        p1, p2 = st.columns(2)
        inicio = p1.text_input("¿Cuándo empieza el estudio? (AAAA-MM-DD)", e.periodo_inicio, help="P01")
        fin = p2.text_input("¿Cuándo termina? (AAAA-MM-DD)", e.periodo_fin, help="P01")
        df = pl.plan_a_dataframe(e)
        df[pl.COL_FECHA] = pd.to_datetime(df[pl.COL_FECHA], errors="coerce").dt.date
        config = {
            pl.COL_ID: st.column_config.TextColumn("Medición", disabled=True, width="small"),
            pl.COL_PUNTO: st.column_config.SelectboxColumn("Punto", options=list(pl.mapa_etiquetas_punto(e)), required=True),
            pl.COL_REP: st.column_config.NumberColumn("Repetición", min_value=1, step=1, required=True, width="small"),
            pl.COL_TEC: st.column_config.SelectboxColumn("Técnico", options=[t.codigo for t in e.tecnicos]),
            pl.COL_PAT: st.column_config.SelectboxColumn("Patrón", options=[p.codigo for p in e.patrones]),
            pl.COL_FECHA: st.column_config.DateColumn("Fecha prevista", format="YYYY-MM-DD"),
            pl.COL_FRANJA: st.column_config.TextColumn("Franja prevista"),
            pl.COL_ORDEN: st.column_config.NumberColumn("Orden", min_value=1, step=1, width="small"),
        }
        if e.equipos:
            config[pl.COL_EQ] = st.column_config.SelectboxColumn("Equipo", options=[x.codigo for x in e.equipos])
        for f in e.factores_libres():
            config[f.nombre] = st.column_config.SelectboxColumn(f.nombre, options=f.niveles)
        editado = st.data_editor(df, num_rows="dynamic", hide_index=True, width="stretch", height=420,
                                 column_config=config, key=f"ed_plan_{clave}")
        if st.form_submit_button("Guardar mediciones planificadas", type="primary", icon=":material/save:") and requerir_usuario():
            nuevo, errores = pl.plan_desde_dataframe(e, editado)
            if errores:
                for x in errores[:10]:
                    st.error(x)
            else:
                e.plan, e.periodo_inicio, e.periodo_fin = nuevo, inicio.strip(), fin.strip()
                guardar(e, f"plan ({len(nuevo)} mediciones)")
                st.rerun()

# ===================================================================== Revisión y aprobación
with t_apr:
    etapas = revisar_estudio(e)
    obligatorias = [x for x in etapas if x.obligatoria]
    completas = sum(1 for x in obligatorias if x.completa)
    st.markdown("##### ¿Quieres revisar el plan antes de descargarlo?")
    st.caption("P05 · Al aprobar, el diseño se congela como una versión inmutable con su huella digital. La plantilla se genera desde esa versión.")
    st.progress(completas / len(obligatorias), text=f"{completas} de {len(obligatorias)} secciones obligatorias completas")
    for x in etapas:
        icono = ":material/check_circle:" if x.completa else ":material/radio_button_unchecked:"
        color = "green" if x.completa else "orange"
        with st.container(border=True):
            st.markdown(f":{color}[{icono}] **{x.titulo}**" + ("" if x.obligatoria else " · opcional"))
            for f in x.faltantes:
                st.markdown(f"- :orange[{f}]")
            for a in x.advertencias:
                st.caption(f":material/info: {a}")
    ok, faltantes = listo_para_aprobar(e)
    if e.estado == "aprobado":
        st.success(f"Versión {e.version_diseno} aprobada por {e.aprobado_por} el {e.fecha_aprobacion[:16].replace('T', ' ')}.",
                   icon=":material/verified:")
        st.page_link(PAGINAS["plantillas"], label="Ir a descargar la plantilla", icon=":material/arrow_forward:")
    else:
        confirmar = st.checkbox("Revisé las mediciones planificadas y confirmo que corresponden al diseño que se ejecutará.", disabled=not ok)
        if st.button("Aprobar diseño y congelar versión", type="primary", icon=":material/verified:", disabled=not (ok and confirmar)) \
                and requerir_usuario():
            version = repo.aprobar_version(e, usuario())
            st.toast(f"Diseño aprobado · versión {version}", icon=":material/verified:")
            st.rerun()
        if not ok:
            st.caption("Completa lo marcado en naranja para poder aprobar.")
