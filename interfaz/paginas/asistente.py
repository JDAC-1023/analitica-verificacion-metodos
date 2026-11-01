import streamlit as st

from interfaz.asistente import crear_estudio_dialogo, render
from interfaz.comun import encabezado, estudio_actual

encabezado("Paso a paso", "Crear o continuar un estudio",
           "Responde las preguntas en orden. Cada vez que avanzas se guarda el borrador; puedes salir y volver cuando quieras.")

e = estudio_actual()
if e is None or st.session_state.get("crear_nuevo"):
    with st.container(border=True):
        st.markdown("#### :material/add_task: Nuevo estudio")
        crear_estudio_dialogo()
    st.stop()

c1, c2 = st.columns([3, 1], vertical_alignment="center")
c1.markdown(f"Estás trabajando en **{e.codigo} · {e.nombre}**")
if c2.button("Crear otro estudio", icon=":material/add:", width="stretch"):
    st.session_state["crear_nuevo"] = True
    st.rerun()
render(e, en_panel=False)
