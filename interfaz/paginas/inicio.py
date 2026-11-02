"""Inicio: elegir el estudio con tarjetas y ver su panel integrado (configuración, datos, resultados e informes)."""

import html

import pandas as pd
import streamlit as st

from interfaz.comun import PAGINAS, banda_de_pasos, estudio_actual, repositorio, tabla
from src.motor.lenguaje import hallazgos, resumen_global
from src.motor.plantillas import fmt

repo = repositorio()


def _estado_estudio(codigo: str) -> dict:
    preps = repo.listar_preparaciones(codigo)
    analisis = [a for a in repo.listar_analisis(codigo) if a["ejecutado"]]
    return {"datos": any(p.get("aprobada") for p in preps), "preparaciones": len(preps),
            "analisis": analisis[-1] if analisis else None, "informes": len(repo.listar_informes(codigo))}


def _chip(texto: str, tono: str) -> str:
    return f"<span class='avm-chip avm-chip-{tono}'>{html.escape(texto)}</span>"


def _abrir(codigo: str) -> None:
    st.session_state["estudio_codigo"] = codigo
    st.session_state.pop("cambiar_estudio", None)
    st.rerun()


# ------------------------------------------------------------------ selector de estudios
def selector() -> None:
    st.html("""
    <div class='avm-hero'>
      <span class='avm-kicker'>Sistema de analítica de datos</span>
      <h1>¿Qué estudio quieres revisar?</h1>
      <p>Elige un estudio para abrir su panel: configuración, datos, resultados del motor e informes, todo en un solo lugar.</p>
    </div>""")
    estudios = repo.listar_estudios()
    busqueda = st.text_input("Buscar estudio", placeholder="Nombre, código o método", label_visibility="collapsed")
    if busqueda:
        b = busqueda.lower()
        estudios = [x for x in estudios if b in f"{x['codigo']} {x['nombre']} {x['metodo']}".lower()]
    columnas = st.columns(3, gap="medium")
    with columnas[0].container(border=True, height=230):
        st.markdown("#### :material/add_circle: Nuevo estudio")
        st.caption("El asistente te pregunta todo paso a paso, guarda tu avance y genera la plantilla de datos.")
        if st.button("Crear estudio", type="primary", icon=":material/add:", width="stretch", key="crear_inicio"):
            st.session_state["crear_nuevo"] = True
            st.session_state["asistente_abierto"] = True
            st.rerun()
    for i, x in enumerate(estudios, start=1):
        est = _estado_estudio(x["codigo"])
        chips = [_chip(f"Diseño v{x['version_diseno']}", "verde") if x["estado"] == "aprobado" else _chip("Diseño en borrador", "gris"),
                 _chip("Datos aprobados", "verde") if est["datos"] else _chip("Sin datos aprobados", "gris")]
        if est["analisis"]:
            g = resumen_global({"conclusion_final": {"estado": est["analisis"]["estado_final"], "texto": ""}})
            tono = {"green": "verde", "red": "rojo", "orange": "naranja"}.get(g["color"], "gris")
            chips.append(_chip(g["etiqueta"].capitalize(), tono))
        with columnas[i % 3].container(border=True, height=230):
            st.html(f"<div class='avm-tarjeta-codigo'>{html.escape(x['codigo'])} · {html.escape(x['tipo'] or '')}</div>"
                    f"<div class='avm-tarjeta-nombre'>{html.escape(x['nombre'])}</div>"
                    f"<div class='avm-tarjeta-sub'>{html.escape(x['metodo'] or 'Método sin definir')} · {x['mediciones']} mediciones</div>"
                    f"<div class='avm-chips'>{''.join(chips)}</div>")
            if st.button("Abrir", key=f"abrir_{x['codigo']}", icon=":material/arrow_forward:", width="stretch"):
                _abrir(x["codigo"])
    if not estudios:
        st.info("No hay estudios que coincidan con la búsqueda.", icon=":material/search_off:")


# ------------------------------------------------------------------ panel del estudio
def panel(e) -> None:
    est = _estado_estudio(e.codigo)
    c1, c2 = st.columns([5, 1.3], vertical_alignment="bottom")
    c1.html(f"<div class='avm-encabezado'><div class='avm-kicker'>{html.escape(e.codigo)} · {html.escape(e.tipo)}</div>"
            f"<h1>{html.escape(e.nombre)}</h1><p>{html.escape(e.metodo or '')}"
            f"{' · versión ' + html.escape(e.version_metodo) if e.version_metodo else ''} · responsable: {html.escape(e.responsable or '—')}</p></div>")
    if c2.button("Cambiar de estudio", icon=":material/swap_horiz:", width="stretch"):
        st.session_state["cambiar_estudio"] = True
        st.rerun()
    banda_de_pasos(e)
    res = repo.obtener_analisis(e.codigo, est["analisis"]["version"])["resultado"] if est["analisis"] else None
    t_res, t_conf, t_datos, t_resul, t_inf = st.tabs([":material/dashboard: Resumen", ":material/tune: Configuración",
                                                      ":material/dataset: Datos", ":material/query_stats: Resultados",
                                                      ":material/description: Informes"])
    with t_res:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Mediciones planificadas", len(e.plan), border=True)
        k2.metric("Puntos", len(e.puntos), border=True)
        k3.metric("Conjuntos preparados", est["preparaciones"], border=True)
        k4.metric("Informes emitidos", est["informes"], border=True)
        if res:
            from src.motor import flujo
            v = flujo.veredicto(res)
            with st.container(border=True):
                st.markdown(f"#### :{v['color']}[:material/verified:] {v['titulo']}")
                st.write(v["texto"])
                for i in flujo.implicaciones(res):
                    st.markdown(f"- **{i['caracteristica']}:** {i['que_implica']}")
        else:
            st.info("Este estudio aún no tiene un análisis ejecutado.", icon=":material/pending:")
        st.markdown("**Siguiente paso**")
        if not e.version_diseno:
            st.page_link(PAGINAS["asistente"], label="Terminar el diseño en el asistente", icon=":material/add_task:")
        elif not est["datos"]:
            st.page_link(PAGINAS["carga"], label="Subir y aprobar los datos", icon=":material/upload_file:")
        elif not res:
            st.page_link(PAGINAS["analisis"], label="Configurar y ejecutar el análisis", icon=":material/query_stats:")
        else:
            st.page_link(PAGINAS["analisis"], label="Revisar resultados, comentar y emitir el informe", icon=":material/rate_review:")
    with t_conf:
        filas = [("Uso previsto", e.uso_previsto), ("Magnitud", "; ".join(f"{m.nombre} ({m.unidad})" for m in e.magnitudes)),
                 ("Puntos", "; ".join(f"{fmt(p.valor_nominal)} {p.unidad}" for p in e.puntos)),
                 ("Equipo evaluado (IBC)", "; ".join(f"{r.codigo} {r.nombre} {r.marca} {r.modelo}".strip() for r in e.ibcs) or "—"),
                 ("Técnicos", "; ".join(f"{r.codigo} {r.nombre}" for r in e.tecnicos) or "—"),
                 ("Patrones", "; ".join(f"{r.codigo} {r.nombre}" for r in e.patrones) or "—"),
                 ("Condiciones que cambian", "; ".join(f.nombre for f in e.factores) or "—"),
                 ("Lecturas por serie", str(e.repeticiones_por_condicion)),
                 ("Datos que se registran", "; ".join(f"{v.nombre} ({v.unidad})" for v in e.variables)),
                 ("Resultados de interés", "; ".join(r.nombre for r in e.resultados) or "—")]
        tabla(pd.DataFrame(filas, columns=["Campo", "Valor"]))
        b1, b2 = st.columns(2)
        if b1.button("Editar en el asistente", icon=":material/edit:", width="stretch"):
            st.session_state.pop("crear_nuevo", None)
            st.session_state["asistente_abierto"] = True
            st.rerun()
        b2.page_link(PAGINAS["diseno"], label="Diseño experimental (edición avanzada)", icon=":material/science:")
    with t_datos:
        preps = repo.listar_preparaciones(e.codigo)
        if not preps:
            st.info("Aún no hay datos cargados.", icon=":material/upload_file:")
        else:
            p = preps[-1]
            c = p["conteos"]
            d1, d2, d3, d4, d5 = st.columns(5)
            d1.metric("Filas recibidas", c["recibidos"], border=True)
            d2.metric("Pasan al análisis", c["incluidos_en_preparado"], border=True)
            d3.metric("Normalizadas", c["normalizados"], border=True)
            d4.metric("Pendientes", c["pendientes"], border=True)
            d5.metric("Con advertencia", c["con_advertencia"], border=True)
            st.caption(f"Archivo «{p['archivo_original']}» · conjunto {p['preparacion_id']} · "
                       + (f"aprobado por {p['aprobada_por']}" if p.get("aprobada") else "pendiente de aprobación"))
        l1, l2, l3 = st.columns(3)
        l1.page_link(PAGINAS["carga"], label="Subir DB", icon=":material/upload_file:")
        l2.page_link(PAGINAS["calidad"], label="Calidad de datos", icon=":material/fact_check:")
        l3.page_link(PAGINAS["datos"], label="Datos preparados y reporte de limpieza", icon=":material/cleaning_services:")
    with t_resul:
        if res:
            from src.motor import graficos
            from src.motor.multi import partes
            filas = [{"Resultado evaluado": parte["objeto"]["nombre"], "Característica": f["caracteristica"],
                      "Decisión": resumen_global({"conclusion_final": {"estado": f["decision"], "texto": ""}})["etiqueta"].capitalize()
                      if f["decision"] in ("CONFORME", "NO_CONFORME", "INDETERMINADO", "CALCULADO_SIN_EVALUACION") else f["decision"],
                      "Valores": ", ".join(fmt(n["valor"]) for n in f["niveles"] if n["valor"] is not None)[:120]}
                     for parte in partes(res) for f in parte["caracteristicas"] if f["niveles"]]
            tabla(pd.DataFrame(filas))
            primero = partes(res)[0]
            g1, g2 = st.columns(2)
            for col, fig in zip((g1, g2), (graficos.resumen_sesgo(primero), graficos.resumen_precision(primero))):
                if fig:
                    col.image(fig, width="stretch")
            if len(partes(res)) > 1:
                st.caption(f"Gráficos de {primero['objeto']['nombre']}. Los demás resultados están en el análisis completo.")
        else:
            st.info("Sin resultados todavía.", icon=":material/pending:")
        st.page_link(PAGINAS["analisis"], label="Abrir el análisis completo", icon=":material/open_in_new:")
    with t_inf:
        informes = repo.listar_informes(e.codigo)
        for i in informes[::-1]:
            st.download_button(f"{i['archivo']} · análisis v{i['version']} · {i.get('fecha', '')}",
                               repo.obtener_informe(e.codigo, i["version"], i["archivo"]), mime="application/pdf",
                               file_name=f"{e.codigo}_analisis_v{i['version']}_{i['archivo']}", icon=":material/download:",
                               key=f"inf_{i['version']}_{i['archivo']}")
        if not informes:
            st.info("Aún no se ha emitido ningún informe. Se genera en Análisis estadístico → Informe PDF.", icon=":material/description:")


e = estudio_actual()
if e is None or st.session_state.get("cambiar_estudio"):
    selector()
else:
    panel(e)
