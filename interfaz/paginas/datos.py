import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, banda_de_pasos, encabezado, metricas_conteos, repositorio, requerir_estudio, requerir_usuario, tabla, usuario
from src.exportacion.lector_salida import cargar_conjunto
from src.servicios.flujo import ErrorFlujo, aprobar_conjunto

encabezado("Paso 6", "Datos preparados",
           "Consulta y descarga el conjunto normalizado que recibirá el motor estadístico, con su trazabilidad completa.")
e = requerir_estudio()
repo = repositorio()
banda_de_pasos(e)

preps = repo.listar_preparaciones(e.codigo)
if not preps:
    with st.container(border=True):
        st.markdown("#### :material/dataset: Aún no hay conjuntos preparados")
        st.write("Revisa la calidad de una carga y pulsa **Preparar conjunto de datos**.")
        st.page_link(PAGINAS["calidad"], label="Ir a Calidad de datos", icon=":material/arrow_forward:")
    st.stop()

ids = [p["preparacion_id"] for p in preps][::-1]
preferida = st.session_state.get("ultima_preparacion")
prep_id = st.selectbox("Conjunto preparado", ids, index=ids.index(preferida) if preferida in ids else 0,
                       format_func=lambda x: f"{x}" + (" · aprobado" if next(p for p in preps if p["preparacion_id"] == x)["aprobada"] else ""))
prep = repo.obtener_preparacion(e.codigo, prep_id)
paquete = repo.obtener_archivo_preparacion(e.codigo, prep_id, "conjunto_preparado.zip")
datos = cargar_conjunto(paquete)

if prep["aprobada"]:
    st.success(f"Conjunto aprobado para el motor por {prep['aprobada_por']} el {prep['fecha_aprobacion'][:16].replace('T', ' ')}.", icon=":material/verified:")
else:
    st.info("Conjunto preparado, pendiente de confirmar como listo para analizar (X07).", icon=":material/pending:")

metricas_conteos(prep["conteos"])
with st.container(border=True):
    st.markdown("##### :material/fingerprint: Trazabilidad")
    t1, t2, t3 = st.columns(3)
    t1.markdown(f"**Carga**  \n`{prep['carga_id']}`  \n**Archivo**  \n{prep['archivo_original']}")
    t2.markdown(f"**SHA-256 del original**  \n`{prep['sha256_original'][:24]}…`  \n**Diseño**  \nversión {prep['version_diseno']} · `{prep['huella_diseno'][:16]}…`")
    t3.markdown(f"**Transformaciones autorizadas**  \n{', '.join(prep['transformaciones_autorizadas']) or 'ninguna'} · exclusiones manuales: "
                f"{len(prep['exclusiones_manuales'])}  \n**Preparó**  \n{prep['usuario']} · {prep['fecha'][:16].replace('T', ' ')}")

b1, b2, b3 = st.columns(3)
b1.download_button("Descargar conjunto (ZIP)", paquete, file_name=f"conjunto_preparado_{e.codigo}_{prep_id}.zip", type="primary",
                   icon=":material/folder_zip:", width="stretch")
b2.download_button("Informe de incidencias (Excel)", repo.obtener_archivo_preparacion(e.codigo, prep_id, "informe_incidencias.xlsx"),
                   file_name=f"informe_incidencias_{prep_id}.xlsx", icon=":material/summarize:", width="stretch")
if not prep["aprobada"]:
    if b3.button("Confirmar datos listos para analizar", icon=":material/verified:", width="stretch") and requerir_usuario():
        try:
            aprobar_conjunto(repo, e.codigo, prep_id, usuario())
            st.rerun()
        except ErrorFlujo as exc:
            st.error(str(exc))

tablas = [("observaciones_analisis", "Vista de análisis"), ("mediciones", "Mediciones"), ("valores", "Datos experimentales"),
          ("resultados_valores", "Resultados registrados"), ("niveles_factores", "Condiciones"), ("registros_estado", "Estado de registros"),
          ("incidencias", "Incidencias"), ("transformaciones", "Transformaciones"), ("exclusiones", "Exclusiones")]
pestanas = st.tabs([f"{titulo} ({len(datos[nombre])})" for nombre, titulo in tablas])
constantes = ["codigo_estudio", "version_diseno", "carga_id"]
for (nombre, _), pestana in zip(tablas, pestanas):
    with pestana:
        df = datos[nombre]
        tabla(df.drop(columns=[c for c in constantes if c in df.columns]), height=380)
st.caption("Vista previa sin las columnas constantes (código del estudio, versión y carga). La pantalla abrevia los decimales al mostrarlos; el archivo descargado conserva el valor completo, igual que «valor_original».")

with st.expander("Cómo leer este conjunto desde Python (para el motor estadístico)", icon=":material/code:"):
    st.code(f'''from src.exportacion.lector_salida import cargar_conjunto, matriz_por_variable

datos = cargar_conjunto("conjunto_preparado_{e.codigo}_{prep_id}.zip")   # verifica huellas SHA-256
obs = datos["observaciones_analisis"]          # 1 fila = 1 dato experimental de una medición incluida
print(datos["manifiesto"]["conteos"])          # recibidos, incluidos, pendientes, excluidos...

# Ejemplo: una variable, agrupada por punto y condición
indicacion = matriz_por_variable(datos, "{e.variables[0].id if e.variables else 'V-01'}")
print(indicacion.groupby(["punto_id", "grupo_comparable"])["valor_numerico"].count())
''', language="python")
    st.caption("Las definiciones de resultados de interés, criterios y condiciones viajan en el mismo ZIP (definiciones_resultados.csv, criterios.csv, factores.csv).")
