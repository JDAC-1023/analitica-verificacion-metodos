"""Punto de entrada de la aplicación web.

Ejecutar:  streamlit run app.py
"""

import streamlit as st

st.set_page_config(page_title="Analítica · Verificación de métodos", page_icon=":material/insights:",
                   layout="wide", initial_sidebar_state="expanded")

from interfaz.asistente import panel  # noqa: E402
from interfaz.comun import badge_estado_diseno, cargar_estilos, repositorio  # noqa: E402

cargar_estilos()


@st.cache_resource(show_spinner="Preparando los estudios de testeo…")
def _testeos_listos() -> bool:
    """Carga una sola vez los 4 estudios de testeo (data/estudios_prueba) en la base de datos local."""
    import os
    if os.environ.get("AVM_SIN_TESTEOS") != "1":
        from src.servicios.estudios_prueba import asegurar_testeos
        asegurar_testeos(repositorio())
    return True


_testeos_listos()

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
    "Análisis e informes": [
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
    codigo_activo = st.session_state.get("estudio_codigo")
    if codigo_activo:
        try:
            activo = repositorio().obtener_estudio(codigo_activo)
        except Exception:  # noqa: BLE001 - estudio borrado
            activo = None
        if activo is not None:
            with st.container(border=True):
                st.caption("Estudio abierto")
                st.markdown(f"**{activo.nombre}**  \n:gray[{activo.codigo} · {activo.tipo}]")
                badge_estado_diseno(activo)
                if st.button("Cambiar de estudio", icon=":material/swap_horiz:", width="stretch", key="cambiar_lateral"):
                    st.session_state["cambiar_estudio"] = True
                    st.switch_page("interfaz/paginas/inicio.py")
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
