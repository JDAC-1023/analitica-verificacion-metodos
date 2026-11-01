"""Punto de entrada de la aplicación web.

Ejecutar:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Analítica · Verificación de métodos", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="expanded")

from interfaz.asistente import panel  # noqa: E402
from interfaz.comun import badge_estado_diseno, cargar_estilos, repositorio  # noqa: E402

cargar_estilos()

PAGINA_ASISTENTE = "Crear / continuar estudio"
paginas = {
    "": [
        st.Page("interfaz/paginas/inicio.py", title="Inicio", icon=":material/space_dashboard:", default=True),
        st.Page("interfaz/paginas/asistente.py", title=PAGINA_ASISTENTE, icon=":material/add_task:"),
    ],
    "Datos": [
        st.Page("interfaz/paginas/carga.py", title="Subir DB", icon=":material/upload_file:"),
        st.Page("interfaz/paginas/calidad.py", title="Calidad de datos", icon=":material/fact_check:"),
        st.Page("interfaz/paginas/datos.py", title="Datos preparados", icon=":material/dataset:"),
    ],
    "Edición avanzada": [
        st.Page("interfaz/paginas/estudios.py", title="Estudios", icon=":material/folder_open:"),
        st.Page("interfaz/paginas/diseno.py", title="Diseño experimental", icon=":material/science:"),
        st.Page("interfaz/paginas/plantillas.py", title="Plantillas", icon=":material/table_view:"),
    ],
    "Próximas fases": [
        st.Page("interfaz/paginas/analisis.py", title="Análisis estadístico", icon=":material/query_stats:"),
        st.Page("interfaz/paginas/informes.py", title="Informes", icon=":material/description:"),
    ],
}
navegacion = st.navigation(paginas)

with st.sidebar:
    st.markdown("### :violet[:material/insights:] Analítica de métodos")
    st.caption("Verificación y validación de métodos de calibración")
    if st.button("Crear estudio", type="primary", icon=":material/add:", width="stretch",
                 help="Abre el asistente: te pregunta todo paso a paso y guarda tu avance."):
        st.session_state["crear_nuevo"] = True
        st.session_state["asistente_abierto"] = True
        st.rerun()
    st.text_input("¿Quién está trabajando?", key="usuario", placeholder="Tu nombre",
                  help="Se registra en la bitácora de auditoría de cada acción.")
    estudios = repositorio().listar_estudios()
    if estudios:
        codigos = [x["codigo"] for x in estudios]
        nombres = {x["codigo"]: f"{x['codigo']} · {x['nombre']}" for x in estudios}
        actual = st.session_state.get("estudio_codigo")
        indice = codigos.index(actual) if actual in codigos else None
        elegido = st.selectbox("Estudio activo", codigos, index=indice, format_func=nombres.get,
                               placeholder="Selecciona un estudio")
        if elegido != actual:
            st.session_state["estudio_codigo"] = elegido
            st.rerun()
        if elegido:
            badge_estado_diseno(repositorio().obtener_estudio(elegido))
            if st.button("Continuar en el asistente", icon=":material/play_arrow:", width="stretch"):
                st.session_state.pop("crear_nuevo", None)
                st.session_state["asistente_abierto"] = True
                st.rerun()
    st.divider()
    st.caption(":material/lock: Datos guardados en tu equipo (carpeta `datos_locales/`, excluida de Git).")

# El asistente se muestra como panel lateral flotante, salvo en su propia página.
if st.session_state.get("asistente_abierto") and navegacion.title != PAGINA_ASISTENTE:
    panel()

navegacion.run()
