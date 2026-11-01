import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, banda_de_pasos, encabezado, metricas_conteos, repositorio, requerir_estudio, requerir_usuario, tabla, usuario
from src.calidad.evaluador import resumen_mensajes
from src.servicios.flujo import cargar_archivo

encabezado("Datos", "Subir DB",
           "Sube la plantilla diligenciada. El sistema guarda el original, comprueba que corresponde al estudio y verifica su calidad.")
e = requerir_estudio()
repo = repositorio()
banda_de_pasos(e)

versiones = [v["version"] for v in repo.listar_versiones(e.codigo)]
if not versiones:
    st.info("Este estudio aún no tiene un diseño aprobado ni plantilla.", icon=":material/lock:")
    st.page_link(PAGINAS["diseno"], label="Ir al diseño experimental", icon=":material/arrow_forward:")
    st.stop()

with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    version = c1.selectbox("¿Qué versión del diseño originó la plantilla?", versiones[::-1], format_func=lambda n: f"Versión {n}",
                           help="X05 · El archivo debe corresponder a esta versión; si no, se rechaza para no mezclar diseños.")
    archivo = c2.file_uploader("Plantilla diligenciada (.xlsx)", type=["xlsx"], help="El archivo original se conserva sin cambios.")
    if st.button("Cargar y verificar", type="primary", icon=":material/fact_check:", disabled=archivo is None) and requerir_usuario():
        with st.status("Procesando el archivo…", expanded=True) as estado:
            st.write("Guardando el original y calculando su huella SHA-256…")
            carga = cargar_archivo(repo, e.codigo, archivo.getvalue(), archivo.name, usuario(), version)
            st.write("Identificando estudio, versión y columnas…")
            st.write("Aplicando las reglas de calidad…")
            estado.update(label="Archivo procesado" if carga["estado_archivo"] == "leido" else "Archivo rechazado",
                          state="complete" if carga["estado_archivo"] == "leido" else "error")
        st.session_state["ultima_carga"] = carga["carga_id"]

cargas = repo.listar_cargas(e.codigo)
ultima = st.session_state.get("ultima_carga")
if ultima and any(c["carga_id"] == ultima for c in cargas):
    carga = repo.obtener_carga(e.codigo, ultima)
    ev = carga["evaluacion_inicial"]
    st.markdown(f"#### Resultado de la carga `{carga['carga_id']}`")
    for nivel, texto in resumen_mensajes(ev):
        getattr(st, nivel)(texto)
    metricas_conteos(ev["conteos"])
    if carga["estado_archivo"] == "rechazado":
        for i in ev["incidencias"]:
            st.error(i["mensaje"], icon=":material/block:")
    else:
        if carga.get("cambios_vs_anterior"):
            with st.expander(f"Cambios frente a la carga anterior ({len(carga['cambios_vs_anterior'])} celdas)", icon=":material/difference:"):
                st.caption("X08 · La carga anterior se conserva completa; aquí solo se listan las diferencias.")
                tabla(pd.DataFrame(carga["cambios_vs_anterior"]))
        st.page_link(PAGINAS["calidad"], label="Revisar incidencias, autorizar transformaciones y preparar los datos",
                     icon=":material/arrow_forward:")

st.markdown("#### Historial de cargas")
if not cargas:
    st.caption("Aún no se han cargado archivos en este estudio.")
else:
    filas = []
    for c in cargas[::-1]:
        k = c.get("conteos") or {}
        filas.append({"Carga": c["carga_id"], "Fecha": (c["fecha"] or "")[:19].replace("T", " "), "Usuario": c["usuario"],
                      "Archivo": c["nombre_archivo"], "Versión": c["version_diseno"],
                      "Estado": "Leído" if c["estado_archivo"] == "leido" else "Rechazado",
                      "Recibidos": k.get("recibidos"), "Incluibles": k.get("incluidos_en_preparado"), "Pendientes": k.get("pendientes"),
                      "SHA-256": (c["sha256"] or "")[:16] + "…"})
    tabla(pd.DataFrame(filas))
    elegida = st.selectbox("Descargar el archivo original de una carga", [c["carga_id"] for c in cargas[::-1]])
    original = repo.obtener_original(e.codigo, elegida)
    nombre = next(c["nombre_archivo"] for c in cargas if c["carga_id"] == elegida)
    st.download_button("Descargar original", original, file_name=f"{elegida}_{nombre}", icon=":material/download:")
