import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, encabezado, repositorio, requerir_estudio, tabla

encabezado("Paso 8", "Informes técnicos",
           "Informes PDF emitidos para el estudio activo. Cada informe corresponde a una versión ejecutada del análisis y guarda su huella SHA-256.")
e = requerir_estudio()
repo = repositorio()
informes = repo.listar_informes(e.codigo)
if not informes:
    with st.container(border=True):
        st.markdown("#### :material/picture_as_pdf: Aún no hay informes emitidos")
        st.write("Ejecuta un análisis y genera el informe en la pestaña **Informe PDF**.")
        st.page_link("interfaz/paginas/analisis.py", label="Ir a Análisis estadístico", icon=":material/arrow_forward:")
    st.stop()

tabla(pd.DataFrame([{"Archivo": i["archivo"], "Versión del análisis": f"v{i['version']}", "Fecha de emisión": i.get("fecha", ""),
                     "Elaboró": i.get("elaborado_por", ""), "Revisó": i.get("revisado_por", ""), "Autorizó": i.get("autorizado_por", ""),
                     "SHA-256": i.get("sha256", "")[:16] + "…"} for i in informes[::-1]]))
for i in informes[::-1]:
    st.download_button(f"Descargar {i['archivo']} (análisis v{i['version']})", repo.obtener_informe(e.codigo, i["version"], i["archivo"]),
                       file_name=f"{e.codigo}_analisis_v{i['version']}_{i['archivo']}", mime="application/pdf",
                       icon=":material/download:", key=f"dl_{i['version']}_{i['archivo']}")
