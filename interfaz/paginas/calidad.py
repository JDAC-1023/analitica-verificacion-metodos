import pandas as pd
import streamlit as st

from interfaz.comun import (
    ETIQUETA_ESTADO, PAGINAS, SEVERIDAD, banda_de_pasos, encabezado, metricas_conteos, repositorio, requerir_estudio,
    requerir_usuario, tabla, usuario,
)
from src.calidad.evaluador import resumen_mensajes
from src.calidad.reglas import REGLAS
from src.servicios.flujo import ErrorFlujo, evaluar_carga, preparar_conjunto
from src.transformaciones.catalogo import TRANSFORMACIONES, autorizadas_por_defecto

encabezado("Paso 5", "Calidad de datos",
           "Revisa las incidencias, decide qué transformaciones autorizas y qué registros excluyes, y prepara el conjunto de datos.")
e = requerir_estudio()
repo = repositorio()
banda_de_pasos(e)

cargas = [c for c in repo.listar_cargas(e.codigo) if c["estado_archivo"] == "leido"]
if not cargas:
    with st.container(border=True):
        st.markdown("#### :material/upload_file: Aún no hay archivos leídos")
        st.write("Carga una plantilla diligenciada para revisar su calidad.")
        st.page_link(PAGINAS["carga"], label="Ir a Carga de datos", icon=":material/arrow_forward:")
    st.stop()

ids = [c["carga_id"] for c in cargas][::-1]
preferida = st.session_state.get("ultima_carga")
carga_id = st.selectbox("Carga", ids, index=ids.index(preferida) if preferida in ids else 0,
                        format_func=lambda x: f"{x} · {next(c['nombre_archivo'] for c in cargas if c['carga_id'] == x)}")
carga = repo.obtener_carga(e.codigo, carga_id)

clave_t, clave_x = f"autorizadas_{carga_id}", f"exclusiones_{carga_id}"
st.session_state.setdefault(clave_t, autorizadas_por_defecto())
st.session_state.setdefault(clave_x, [])

izq, der = st.columns([1, 1], gap="large")
with izq:
    with st.container(border=True):
        st.markdown("##### :material/rule_settings: Transformaciones autorizadas")
        st.caption("Ninguna cambia el valor, el signo, las cifras ni la unidad: solo interpretan cómo quedó escrito. Cada aplicación se registra.")
        autorizadas = []
        for t in TRANSFORMACIONES.values():
            if st.toggle(f"{t.codigo} · {t.nombre}", value=t.codigo in st.session_state[clave_t], help=f"{t.descripcion} Ejemplo: {t.ejemplo}",
                         key=f"tg_{carga_id}_{t.codigo}"):
                autorizadas.append(t.codigo)
        st.session_state[clave_t] = autorizadas
        st.caption(":material/do_not_disturb_on: No existen transformaciones para imputar faltantes, redondear, convertir unidades o eliminar atípicos.")
with der:
    with st.container(border=True):
        st.markdown("##### :material/remove_circle: Exclusiones documentadas")
        st.caption("Excluye un registro del conjunto preparado solo con un motivo verificable. El registro original se conserva.")
        registros_ids = sorted({r["registro_id"] for r in carga["evaluacion_inicial"]["registros"] + carga["evaluacion_inicial"].get("registros_resultados", [])
                                if r["registro_id"]})
        ya = {x["registro_id"] for x in st.session_state[clave_x]}
        with st.form(f"excluir_{carga_id}", clear_on_submit=True, border=False):
            c1, c2 = st.columns([1, 2])
            rid = c1.selectbox("Registro", [r for r in registros_ids if r not in ya], index=None, placeholder="Elige")
            motivo = c2.text_input("Motivo verificable", placeholder="Ej.: falla del sensor registrada en la bitácora del equipo")
            if st.form_submit_button("Agregar exclusión", icon=":material/add:"):
                if not rid or not motivo.strip():
                    st.error("Elige el registro y escribe el motivo.")
                elif requerir_usuario():
                    st.session_state[clave_x].append({"registro_id": rid, "motivo": motivo.strip(), "usuario": usuario()})
                    st.rerun()
        for i, x in enumerate(st.session_state[clave_x]):
            a, b = st.columns([5, 1], vertical_alignment="center")
            a.markdown(f"**{x['registro_id']}** · {x['motivo']} · _{x['usuario']}_")
            if b.button("Quitar", key=f"q_{carga_id}_{i}", icon=":material/close:"):
                st.session_state[clave_x].pop(i)
                st.rerun()

evaluacion = evaluar_carga(repo, e.codigo, carga_id, st.session_state[clave_t], st.session_state[clave_x])
st.markdown("#### Resultado con la configuración actual")
for nivel, texto in resumen_mensajes(evaluacion):
    getattr(st, nivel)(texto)
metricas_conteos(evaluacion["conteos"])

t_inc, t_reg, t_tr, t_res = st.tabs([
    f":material/report: Incidencias ({len(evaluacion['incidencias'])})", ":material/list_alt: Registros",
    f":material/autorenew: Transformaciones ({len(evaluacion['transformaciones'])})", ":material/target: Resultados agrupados",
])
with t_inc:
    if not evaluacion["incidencias"]:
        st.success("Sin incidencias.", icon=":material/check_circle:")
    else:
        df = pd.DataFrame(evaluacion["incidencias"])
        df["Tratamiento"] = df["severidad"].map(SEVERIDAD)
        df["Regla"] = df["regla"] + " · " + df["regla"].map(lambda r: REGLAS[r].nombre)
        f1, f2 = st.columns(2)
        sev = f1.multiselect("Filtrar por tratamiento", sorted(df["Tratamiento"].unique()), placeholder="Todos")
        reg = f2.multiselect("Filtrar por regla", sorted(df["Regla"].unique()), placeholder="Todas")
        if sev:
            df = df[df["Tratamiento"].isin(sev)]
        if reg:
            df = df[df["Regla"].isin(reg)]
        df["fila"] = pd.array(df["fila"], dtype="Int64")
        with st.expander("Leer los mensajes completos", icon=":material/notes:"):
            for _, i in df.iterrows():
                st.markdown(f"- **{i['regla']}** · {i['mensaje']}")
        tabla(df[["Regla", "Tratamiento", "mensaje", "hoja", "fila", "celda", "registro_id"]].rename(columns={
            "mensaje": "Mensaje", "hoja": "Hoja", "fila": "Fila", "celda": "Celda", "registro_id": "Registro"}),
            column_config={"Mensaje": st.column_config.TextColumn(width="large")})
with t_reg:
    estados = list(ETIQUETA_ESTADO)[:5]
    filtro = st.segmented_control("Estado", estados, format_func=lambda s: ETIQUETA_ESTADO[s][0], selection_mode="multi", default=estados)
    filas = [{"Fila": r["fila"], "Registro": r["registro_id"], "Estado": ETIQUETA_ESTADO[r["estado"]][0], "Motivo": r["motivo_estado"]}
             for r in evaluacion["registros"] if r["estado"] in (filtro or [])]
    tabla(pd.DataFrame(filas, columns=["Fila", "Registro", "Estado", "Motivo"]), height=360)
with t_tr:
    if evaluacion["transformaciones"]:
        tabla(pd.DataFrame(evaluacion["transformaciones"]).rename(columns={
            "registro_id": "Registro", "hoja": "Hoja", "fila": "Fila", "celda": "Celda", "columna": "Columna", "codigo": "Transformación",
            "valor_original": "Valor original", "valor_resultante": "Valor interpretado"}))
    else:
        st.caption("No se aplicó ninguna transformación.")
with t_res:
    if evaluacion.get("registros_resultados"):
        tabla(pd.DataFrame([{"Registro": r["registro_id"], "Fila": r["fila"], "Valor": r["valores"]["valor"],
                             "Estado": ETIQUETA_ESTADO[r["estado"]][0], "Motivo": r["motivo_estado"]} for r in evaluacion["registros_resultados"]]))
    else:
        st.caption("Este diseño no tiene resultados directos agrupados.")

st.divider()
c1, c2 = st.columns([2, 1], vertical_alignment="center")
c1.markdown(f"**Preparar el conjunto de datos** con {len(st.session_state[clave_t])} transformaciones autorizadas y "
            f"{len(st.session_state[clave_x])} exclusiones. Se incluirán **{evaluacion['conteos']['incluidos_en_preparado']}** mediciones; "
            "los registros pendientes quedan documentados pero fuera del conjunto.")
if c2.button("Preparar conjunto de datos", type="primary", icon=":material/dataset:", width="stretch",
             disabled=evaluacion["conteos"]["incluidos_en_preparado"] == 0) and requerir_usuario():
    try:
        prep = preparar_conjunto(repo, e.codigo, carga_id, st.session_state[clave_t], st.session_state[clave_x], usuario())
        st.session_state["ultima_preparacion"] = prep["preparacion_id"]
        st.switch_page(PAGINAS["datos"])
    except ErrorFlujo as exc:
        st.error(str(exc))
