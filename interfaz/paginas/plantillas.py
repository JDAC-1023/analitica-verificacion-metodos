import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, banda_de_pasos, encabezado, repositorio, requerir_estudio, tabla
from src.plantillas.especificacion import columnas_mediciones, filas_resultados_agrupados
from src.plantillas.generador import generar_plantilla, nombre_archivo_plantilla
from src.planificacion.plan import plan_a_dataframe

encabezado("Paso 3", "Plantillas", "Descarga el Excel de registro generado desde una versión aprobada del diseño.")
e = requerir_estudio()
repo = repositorio()
banda_de_pasos(e)

versiones = repo.listar_versiones(e.codigo)
if not versiones:
    with st.container(border=True):
        st.markdown("#### :material/lock: La plantilla se genera desde un diseño aprobado")
        st.write("Completa el diseño experimental y apruébalo en **Revisión y aprobación**. Así la plantilla queda vinculada a una versión inmutable.")
        st.page_link(PAGINAS["diseno"], label="Ir al diseño experimental", icon=":material/arrow_forward:")
    st.stop()

if e.estado != "aprobado":
    st.warning(f"El diseño tiene cambios sin aprobar. Puedes descargar la plantilla de una versión aprobada (la última es v{versiones[-1]['version']}).",
               icon=":material/edit_note:")

numeros = [v["version"] for v in versiones]
version = st.selectbox("Versión del diseño", numeros[::-1], format_func=lambda n: f"Versión {n}", help="Cada versión aprobada conserva su propia plantilla.")
ev, huella = repo.obtener_version(e.codigo, version)
cols = columnas_mediciones(ev)
grupos = filas_resultados_agrupados(ev)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Mediciones planificadas", len(ev.plan), border=True)
c2.metric("Columnas que completas", sum(1 for c in cols if c.origen == "usuario"), border=True)
c3.metric("Datos obligatorios", sum(1 for c in cols if c.origen == "usuario" and c.obligatoria), border=True)
c4.metric("Resultados por grupo", len(grupos), border=True)

izq, der = st.columns([2, 1], gap="large")
with izq:
    st.markdown("##### Hoja «Mediciones»")
    st.html("""<div class='avm-leyenda'>
      <span><span class='avm-muestra' style='background:#EEF1F6;border:1px solid #CBD2DF'></span>Gris: la completa el sistema (bloqueada)</span>
      <span><span class='avm-muestra' style='background:#FFFFFF;border:1px solid #6D5BD0'></span>Blanca con encabezado morado: la completas tú</span>
      <span><span class='avm-muestra' style='background:#4C3BB0'></span>Encabezado con *: obligatoria</span></div>""")
    columnas = pd.DataFrame([{"Encabezado en Excel": c.etiqueta, "Quién la completa": "Sistema" if c.origen == "sistema" else "Tú",
                              "Tipo": c.tipo, "Obligatoria": "Sí" if c.obligatoria and c.origen == "usuario" else ""} for c in cols])
    tabla(columnas, height=360)
    if grupos:
        st.markdown("##### Hoja «Resultados_directos»")
        st.caption("Resultados de interés que registras directamente y que corresponden a un grupo de mediciones (no a cada fila).")
        tabla(pd.DataFrame(grupos)[["registro_id", "resultado", "ambito", "grupo", "unidad"]].rename(columns={
            "registro_id": "ID registro", "resultado": "Resultado", "ambito": "Ámbito", "grupo": "Grupo", "unidad": "Unidad"}))
with der:
    with st.container(border=True):
        st.markdown("#### :material/download: Descargar")
        st.caption(f"Versión {version} · huella `{huella[:12]}…`")
        st.download_button("Descargar plantilla Excel", generar_plantilla(ev) if ev.estado == "aprobado" else b"",
                           file_name=nombre_archivo_plantilla(ev), type="primary", icon=":material/table_view:", width="stretch",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.markdown("""
**Cómo diligenciarla**
1. Registra los valores tal como los obtuviste: sin redondear ni cambiar unidades o signos.
2. Si un dato no se tomó, deja la celda vacía: nunca escribas cero.
3. Si cambió el técnico o el patrón, regístralo y escribe el motivo.
4. No cambies encabezados, hojas ni columnas grises.
""")
        st.page_link(PAGINAS["carga"], label="Cuando la tengas lista, cárgala aquí", icon=":material/upload_file:")
    with st.expander("Ver mediciones de esta versión"):
        tabla(plan_a_dataframe(ev), height=300)
    with st.expander("¿Y los resultados calculados?"):
        calculados = [r for r in ev.resultados if r.origen == "calculado"]
        if calculados:
            st.write("No tienen columna en la plantilla: se obtendrán en una fase posterior con un procedimiento aprobado.")
            for r in calculados:
                st.markdown(f"- **{r.nombre}** · depende de: {', '.join(r.dependencias) or 'por definir'}")
        else:
            st.write("Este diseño no tiene resultados calculados.")
