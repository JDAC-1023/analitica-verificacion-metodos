import streamlit as st

from interfaz.comun import PAGINAS, encabezado

encabezado("Próxima fase", "Análisis estadístico",
           "Aquí se conectará el motor estadístico basado en reglas de decisión. Esta sección no simula cálculos.")

with st.container(border=True):
    st.markdown("#### :material/construction: Sección reservada")
    st.write("El motor estadístico se diseñará en la siguiente fase (pendiente PD14). Recibirá un conjunto de datos aprobado "
             "(formato SAL-1.0) con sus mediciones, datos experimentales, condiciones, resultados de interés y criterios.")
    st.markdown("""
**Lo que ya está listo para el motor**
- Conjunto preparado y aprobado, con huellas SHA-256 verificables.
- Definiciones de resultados (directos y calculados), con sus dependencias y su ámbito.
- Grupos comparables definidos en el diseño (D06) y condición completa de cada medición.
- Estados de calidad y motivos de exclusión de cada registro.

**Lo que NO hace esta versión**
- No calcula resultados derivados (error, corrección u otros).
- No ejecuta pruebas, diagnósticos ni reglas de decisión.
- No evalúa criterios de aceptación.
""")
    st.page_link(PAGINAS["datos"], label="Ver los datos preparados", icon=":material/dataset:")
