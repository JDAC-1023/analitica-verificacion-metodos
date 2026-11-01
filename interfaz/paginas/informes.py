import streamlit as st

from interfaz.comun import encabezado

encabezado("Próxima fase", "Informes",
           "Aquí se generará el informe técnico reproducible del estudio. Esta sección no produce documentos todavía.")

with st.container(border=True):
    st.markdown("#### :material/construction: Sección reservada")
    st.write("El contenido automático, las notas del responsable, la revisión y la firma técnica están pendientes de definición (PD19, S02, S03).")
    st.markdown("""
**Disponible hoy para trazabilidad**
- Informe de incidencias y transformaciones de cada preparación (Datos preparados → Informe de incidencias).
- Bitácora de auditoría del estudio (Estudios → Bitácora).
- Versiones aprobadas del diseño con su huella digital.
""")
