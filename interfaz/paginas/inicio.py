import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, banda_de_pasos, estudio_actual, repositorio, usuario
from src.servicios.demo import construir_estudio_demo

st.html("""
<div class='avm-hero'>
  <span class='avm-kicker'>Sistema de analítica de datos</span>
  <h1>Del diseño del estudio a datos listos para analizar</h1>
  <p>Configura el estudio, genera la plantilla de registro, carga los datos y obtén un conjunto
  verificado, trazable y reproducible para el motor estadístico.</p>
</div>
""")

e = estudio_actual()
st.markdown("##### Progreso del estudio activo" + (f" · {e.codigo}" if e else ""))
banda_de_pasos(e)
st.space("small")

repo = repositorio()
estudios = repo.listar_estudios()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Estudios", len(estudios), border=True)
c2.metric("Diseños aprobados", sum(1 for x in estudios if x["version_diseno"] > 0), border=True)
c3.metric("Mediciones planificadas", sum(x["mediciones"] for x in estudios), border=True)
c4.metric("Archivos cargados", sum(x["cargas"] for x in estudios), border=True)

izquierda, derecha = st.columns([2, 1], gap="large")
with izquierda:
    st.markdown("#### Tus estudios")
    if not estudios:
        with st.container(border=True):
            st.markdown(":material/inventory_2: **Todavía no hay estudios.**")
            st.write("Empieza creando uno en **Estudios** o explora la aplicación con un estudio de ejemplo.")
    else:
        df = pd.DataFrame(estudios)
        df["estado"] = df.apply(lambda x: f"Aprobado v{x['version_diseno']}" if x["estado"] == "aprobado"
                                else ("Borrador" if not x["version_diseno"] else f"Borrador (v{x['version_diseno']} aprobada)"), axis=1)
        st.dataframe(df[["codigo", "nombre", "tipo", "metodo", "estado", "mediciones", "cargas"]].rename(columns={
            "codigo": "Código", "nombre": "Nombre", "tipo": "Tipo", "metodo": "Método", "estado": "Estado",
            "mediciones": "Mediciones", "cargas": "Cargas"}), hide_index=True, width="stretch",
            column_config={"Nombre": st.column_config.TextColumn(width="medium"), "Método": st.column_config.TextColumn(width="small")})

with derecha:
    st.markdown("#### Empieza aquí")
    with st.container(border=True):
        st.caption("El asistente te pregunta todo paso a paso, guarda tu avance y termina generando la plantilla y subiendo los datos.")
        if st.button("Crear estudio", type="primary", icon=":material/add:", width="stretch", key="crear_inicio"):
            st.session_state["crear_nuevo"] = True
            st.session_state["asistente_abierto"] = True
            st.rerun()
        if e is not None and st.button(f"Continuar {e.codigo}", icon=":material/play_arrow:", width="stretch", key="continuar_inicio"):
            st.session_state.pop("crear_nuevo", None)
            st.session_state["asistente_abierto"] = True
            st.rerun()
        st.page_link(PAGINAS["asistente"], label="Abrir el asistente en pantalla completa", icon=":material/open_in_full:")
    with st.container(border=True):
        st.markdown(":material/school: **Estudio de ejemplo**")
        st.caption("Crea un estudio sintético para recorrer el flujo. No es un método ni un diseño aprobado.")
        if st.button("Crear estudio de ejemplo", icon=":material/auto_awesome:", width="stretch"):
            base = repo.crear_estudio("Estudio de ejemplo (sintético)", usuario())
            demo = construir_estudio_demo(base.codigo, base.nombre)
            demo.creado_en = base.creado_en
            repo.guardar_estudio(demo, usuario(), "estudio de ejemplo")
            st.session_state["estudio_codigo"] = base.codigo
            st.toast(f"Estudio {base.codigo} creado", icon=":material/check_circle:")
            st.rerun()

st.caption("Dato experimental ≠ resultado de interés ≠ análisis estadístico ≠ criterio de evaluación. "
           "Esta fase prepara los datos; no ejecuta pruebas estadísticas ni decide conformidad.")
