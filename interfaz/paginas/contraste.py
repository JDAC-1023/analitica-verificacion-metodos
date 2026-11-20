"""Contraste del motor con los informes técnicos del laboratorio (datos reales de temperatura y humedad relativa)."""

import io
import zipfile

import pandas as pd
import streamlit as st

from interfaz.comun import encabezado, repositorio, requerir_dependencias_motor, tabla
from src.motor.multi import partes

requerir_dependencias_motor()

from src.contraste.laboratorio import contrastar, grafico_operadores, grafico_p, valores_informe  # noqa: E402
from src.servicios.estudios_reales import CARPETA_REALES, ETIQUETA_REAL, leer_libro  # noqa: E402

encabezado("Paso 9", "Contraste con datos reales del laboratorio",
           "Los datos reales se leen de la base de datos de la aplicación (estudios cargados y aprobados por el flujo normal), "
           "se procesan con el mismo motor y se comparan con lo que imprimen los informes técnicos del laboratorio.")

repo = repositorio()
ARCHIVOS = {"temperatura": "data_temperatura.xlsx", "humedad": "DATA_HUMEDAD.xlsx"}
estudios = [x for x in repo.listar_estudios() if x["nombre"].startswith("Datos reales")]
if not estudios:
    st.warning("Todavía no hay estudios con datos reales en la base de datos. Se crean solos al iniciar la aplicación si "
               "los libros del laboratorio están en data/datos_reales/.", icon=":material/database:")
    st.stop()

nombres = {x["codigo"]: x["nombre"] for x in estudios}
codigo = st.segmented_control("Magnitud", list(nombres), format_func=nombres.get, default=list(nombres)[0], key="contraste_est") \
    or list(nombres)[0]
magnitud = "temperatura" if "Temperatura" in nombres[codigo] else "humedad"


@st.cache_data(show_spinner="Comparando el motor con el informe…", max_entries=4)
def _contraste(codigo_: str, magnitud_: str, huella: str):
    g = repo.obtener_analisis(codigo_, 1)
    lib = leer_libro((CARPETA_REALES / ARCHIVOS[magnitud_]).read_bytes())
    t = contrastar(magnitud_, lib.datos, g["resultado"], lib.componentes_lab)
    return lib, t, g


try:
    e = repo.obtener_estudio(codigo)
    guardado = repo.obtener_analisis(codigo, 1)
except Exception as exc:  # noqa: BLE001
    st.error(f"No se pudo leer el estudio o su análisis desde la base de datos: {exc}")
    st.stop()
lib, t, guardado = _contraste(codigo, magnitud, guardado["resultado"]["meta"].get("huella_resultado", ""))
inf = valores_informe(magnitud)

# 1. identificación
with st.container(border=True):
    st.markdown("#### :material/badge: Conjunto de datos")
    c = st.columns(4)
    c[0].metric("Estudio en la base de datos", codigo)
    c[1].metric("Magnitud", lib.nombre_magnitud)
    c[2].metric("Mediciones", len(lib.datos))
    c[3].metric("Puntos", len(lib.datos["nominal"].unique()))
    st.caption(f"Informe del laboratorio: {inf['informe']}. Archivo de datos: {inf['archivo_datos']}. "
               f"Diseño: 3 operadores × 5 tiempos × 1 observación por combinación, en cada punto. {ETIQUETA_REAL}")
    for a in lib.advertencias:
        st.warning(f"Calidad de datos (no se corrige): {a}", icon=":material/content_copy:")

t_ent, t_proc, t_comp, t_pi, t_desc = st.tabs(["Datos de entrada", "Procesamiento del motor", "Laboratorio vs motor",
                                                "Precisión intermedia", "Exportar"])
with t_ent:
    st.caption("Datos ORIGINALES del laboratorio, tal como están en el libro (sin redondear).")
    vista = lib.datos[["nominal", "unidad", "operador", "tiempo", "fecha", "Corrección", "Inestabilidad", "Inhomogeneidad"]]
    tabla(vista.rename(columns={"nominal": "Punto", "unidad": "Unidad", "operador": "Operador", "tiempo": "Tiempo", "fecha": "Fecha"}))
    var = st.selectbox("Ver por operador", ["Corrección", "Inestabilidad", "Inhomogeneidad"], key="contraste_var")
    st.image(grafico_operadores(lib.datos, var, f"{var} por operador (línea roja: promedio)"), width="stretch")

with t_proc:
    st.caption("RESULTADOS GENERADOS POR EL SISTEMA. Motor determinista con celdas por operador (los 5 tiempos son las "
               "réplicas de cada operador) y el Tiempo como factor de bloque aditivo en las fuentes de variación.")
    st.info(f"Conclusión del motor: **{guardado['resultado']['conclusion_final']['estado']}**. No hay límites de aceptación "
            "declarados en el informe para s_r o s_I, así que el motor calcula y no decide conformidad (RM-17).", icon=":material/info:")
    tabla(t["motor"].rename(columns={"punto": "Punto", "variable": "Resultado evaluado", "atipicos_grubbs": "Lecturas señaladas (Grubbs)",
                                     "grubbs_series": "Series revisadas", "motor_ruta": "Ruta", "motor_influyen": "Factores que influyen",
                                     "motor_posthoc": "Comparaciones post hoc", "motor_s_r": "s_r", "motor_s_I": "s_I"}).drop(columns=["magnitud"]))

with t_comp:
    st.caption("Laboratorio = valor impreso en el informe · Reproducción = mismo procedimiento recalculado aquí · "
               "Motor = valor del motor. La decisión es «rechaza / no rechaza H0» con α = 0,05.")
    r = t["resumen"].copy()
    total, ok = int(r["comparaciones"].sum()), int(r["coincidencias"].sum())
    c = st.columns(3)
    c[0].metric("Decisiones comparadas", total)
    c[1].metric("Decisiones coincidentes", ok)
    c[2].metric("Diferencia máx. ANOVA (p)", f"{r[r['prueba'].str.startswith('ANOVA')]['dif_max_motor'].max():.1e}")
    tabla(r.rename(columns={"prueba": "Prueba", "comparaciones": "Comparaciones", "coincidencias": "Coinciden",
                            "dif_max_motor": "Dif. máx. motor", "dif_max_reproduccion": "Dif. máx. reproducción"}).drop(columns=["magnitud"]))
    st.image(grafico_p(t["comparacion"], "Valores p: informe del laboratorio vs motor"), width=520)
    st.caption("Shapiro-Wilk difiere en valor p porque el laboratorio prueba las 15 lecturas del punto y el motor prueba los "
               "residuos dentro de cada operador (el supuesto que exige el ANOVA). La decisión coincide en todos los casos.")
    filtro = st.multiselect("Pruebas", sorted(t["comparacion"]["prueba"].unique()), key="contraste_pruebas")
    d = t["comparacion"] if not filtro else t["comparacion"][t["comparacion"]["prueba"].isin(filtro)]
    tabla(d.drop(columns=["magnitud"]))

with t_pi:
    st.caption("Precisión intermedia de la corrección con las fórmulas del informe: s²_O = (MC_O − MC_r)/b, s²_T = (MC_T − MC_r)/a, "
               "s²_r = MC_r; u_lab = √(s²_O + s²_T) (componentes negativas → 0).")
    tabla(t["componentes"].drop(columns=["magnitud"]))

with t_desc:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, df in t.items():
            z.writestr(f"{magnitud}_{nombre}.csv", df.to_csv(index=False))
        z.writestr(f"{magnitud}_datos_originales.csv", lib.datos.to_csv(index=False))
        z.writestr(f"{magnitud}_contraste_p.png", grafico_p(t["comparacion"], f"Valores p · {magnitud}"))
    st.download_button("Descargar contraste (CSV + gráfico)", buf.getvalue(), f"contraste_{magnitud}.zip", "application/zip",
                       icon=":material/download:")
    st.page_link("interfaz/paginas/analisis.py", label="Ver el análisis completo y generar el informe PDF del motor",
                 icon=":material/description:")
