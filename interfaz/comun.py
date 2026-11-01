"""Utilidades compartidas por las páginas de la interfaz.

La interfaz no contiene lógica de negocio: lee y guarda a través del
repositorio y de los servicios de `src/`.
"""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import streamlit as st

from src.configuracion.validacion_estudio import revisar_estudio
from src.modelos.estudio import Estudio
from src.persistencia.repositorio import ErrorRepositorio, RepositorioLocal

RAIZ = Path(__file__).resolve().parent

PAGINAS = {
    "inicio": "interfaz/paginas/inicio.py",
    "asistente": "interfaz/paginas/asistente.py",
    "estudios": "interfaz/paginas/estudios.py",
    "diseno": "interfaz/paginas/diseno.py",
    "plantillas": "interfaz/paginas/plantillas.py",
    "carga": "interfaz/paginas/carga.py",
    "calidad": "interfaz/paginas/calidad.py",
    "datos": "interfaz/paginas/datos.py",
    "analisis": "interfaz/paginas/analisis.py",
    "informes": "interfaz/paginas/informes.py",
}

ETIQUETA_ESTADO = {
    "aceptado": ("Aceptado", "green"),
    "normalizado": ("Normalizado", "blue"),
    "con_advertencia": ("Con advertencia", "orange"),
    "pendiente": ("Pendiente", "red"),
    "excluido": ("Excluido", "gray"),
    "rechazado": ("Rechazado", "red"),
}

SEVERIDAD = {
    "bloquea_archivo": "Rechaza el archivo",
    "excluye_registro": "Excluye el registro",
    "pendiente": "Deja pendiente",
    "advertencia": "Advertencia",
    "informativa": "Informativa",
}


@st.cache_resource
def repositorio() -> RepositorioLocal:
    return RepositorioLocal()


def cargar_estilos() -> None:
    st.html(f"<style>{(RAIZ / 'estilos.css').read_text(encoding='utf-8')}</style>")


def usuario() -> str:
    return (st.session_state.get("usuario") or "").strip()


def codigo_actual() -> str | None:
    return st.session_state.get("estudio_codigo")


def estudio_actual() -> Estudio | None:
    codigo = codigo_actual()
    if not codigo:
        return None
    try:
        return repositorio().obtener_estudio(codigo)
    except ErrorRepositorio:
        st.session_state.pop("estudio_codigo", None)
        return None


def requerir_estudio() -> Estudio:
    e = estudio_actual()
    if e is None:
        with st.container(border=True):
            st.markdown("#### :material/folder_open: Aún no has abierto un estudio")
            st.write("Ve a **Inicio** y pulsa **Abrir** en el estudio que quieres revisar, o crea uno nuevo.")
            st.page_link(PAGINAS["inicio"], label="Elegir un estudio en Inicio", icon=":material/arrow_forward:")
        st.stop()
    return e


def requerir_dependencias_motor() -> None:
    """Detiene la página con instrucciones claras si faltan las librerías del motor."""
    import importlib.util
    faltan = [m for m in ("scipy", "statsmodels", "matplotlib", "reportlab") if importlib.util.find_spec(m) is None]
    if faltan:
        with st.container(border=True):
            st.error(f"Faltan librerías del motor: {', '.join(faltan)}.", icon=":material/extension_off:")
            st.write("Cierra la aplicación (Ctrl + C en la terminal) y ejecuta, con el entorno activado:")
            st.code(".\\.venv\\Scripts\\Activate.ps1\npython -m pip install -r requirements.txt\nstreamlit run app.py", language="powershell")
        st.stop()


def requerir_usuario() -> bool:
    if not usuario():
        st.warning("Escribe tu nombre en la barra lateral («¿Quién está trabajando?»). Se registra en la bitácora de cada acción.",
                   icon=":material/badge:")
        return False
    return True


def guardar(e: Estudio, detalle: str) -> None:
    repositorio().guardar_estudio(e, usuario(), detalle)
    st.toast(f"Guardado: {detalle}", icon=":material/check_circle:")


def encabezado(kicker: str, titulo: str, descripcion: str = "") -> None:
    st.html(
        f"<div class='avm-encabezado'><div class='avm-kicker'>{html.escape(kicker)}</div>"
        f"<h1>{html.escape(titulo)}</h1>"
        + (f"<p>{html.escape(descripcion)}</p>" if descripcion else "") + "</div>"
    )


def banda_de_pasos(e: Estudio | None) -> None:
    """Indicador de progreso del flujo completo para el estudio activo."""
    pasos = ["Estudio", "Diseño", "Aprobación", "Plantilla", "Carga", "Calidad", "Datos preparados", "Análisis", "Informe"]
    hechos = set()
    if e is not None:
        etapas = {et.clave: et for et in revisar_estudio(e)}
        if etapas["identificacion"].completa and etapas["alcance"].completa and etapas["recursos"].completa:
            hechos.add("Estudio")
        if all(etapas[k].completa for k in ("condiciones", "variables", "resultados", "plan")):
            hechos.add("Diseño")
        if e.version_diseno >= 1:
            hechos |= {"Aprobación", "Plantilla"}
        repo = repositorio()
        cargas = repo.listar_cargas(e.codigo)
        if any(c["estado_archivo"] == "leido" for c in cargas):
            hechos |= {"Carga", "Calidad"}
        if any(p.get("aprobada") for p in repo.listar_preparaciones(e.codigo)):
            hechos.add("Datos preparados")
        if any(v["ejecutado"] for v in repo.listar_analisis(e.codigo)):
            hechos.add("Análisis")
        if repo.listar_informes(e.codigo):
            hechos.add("Informe")
    actual = next((p for p in pasos if p not in hechos), None)
    chips = []
    for p in pasos:
        clase = "hecho" if p in hechos else ("actual" if p == actual else "")
        marca = "✓ " if p in hechos else ""
        chips.append(f"<span class='avm-paso {clase}'>{marca}{html.escape(p)}</span>")
    st.html("<div class='avm-pasos'>" + "".join(chips) + "</div>")


def badge_estado_diseno(e: Estudio) -> None:
    if e.estado == "aprobado":
        st.badge(f"Diseño aprobado · v{e.version_diseno}", icon=":material/verified:", color="green")
    elif e.version_diseno:
        st.badge(f"Borrador con cambios (última aprobada: v{e.version_diseno})", icon=":material/edit_note:", color="orange")
    else:
        st.badge("Borrador sin aprobar", icon=":material/edit_note:", color="gray")


def metricas_conteos(c: dict) -> None:
    columnas = st.columns(6)
    datos = [
        ("Recibidos", c["recibidos"], None), ("Aceptados", c["aceptados"], None),
        ("Normalizados", c["normalizados"], None), ("Con advertencia", c["con_advertencia"], None),
        ("Pendientes", c["pendientes"], None), ("Excluidos", c["excluidos"], None),
    ]
    for col, (titulo, valor, _) in zip(columnas, datos):
        col.metric(titulo, valor, border=True)
    if c.get("rechazados"):
        st.error(f"Archivo rechazado: {c['rechazados']} filas recibidas no se procesaron.", icon=":material/block:")
    if c.get("conciliado"):
        st.caption(f":material/balance: Conteos conciliados: {c['recibidos']} recibidos = aceptados + normalizados + con advertencia "
                   f"+ pendientes + excluidos + rechazados. Planificados: {c['planificados']} · ausentes en el archivo: "
                   f"{c['planificados_ausentes']} · incluidos en el conjunto preparado: {c['incluidos_en_preparado']}.")
    else:
        st.error("Los conteos no concilian. Informa este caso: es un error de la aplicación.", icon=":material/error:")


def tabla(df: pd.DataFrame, **kwargs) -> None:
    st.dataframe(df, hide_index=True, width="stretch", **kwargs)
