"""Análisis estadístico: configurar, ver la ruta en tiempo real, ejecutar, revisar, comentar, rediseñar e informar."""

from __future__ import annotations

import json
from datetime import date

import pandas as pd
import streamlit as st

from interfaz.comun import (PAGINAS, encabezado, repositorio, requerir_dependencias_motor, requerir_estudio,
                            requerir_usuario, tabla, usuario)

requerir_dependencias_motor()
from src.auditoria.huella import sha256_bytes
from src.motor import graficos
from src.motor.configuracion import (CARACTERISTICAS, ESTADOS_CARACTERISTICA, OPERADORES, PARAMETROS, PRUEBAS_NORMALIDAD,
                                     REGLAS_DECISION, CaracteristicaConfig, ConfiguracionAnalisis, CriterioMotor, Exclusion,
                                     ReferenciaNivel, ReglaDerivacion)
from src.motor.datos import ErrorDatosMotor
from src.motor.motor import ESTADOS_COLOR, ETAPAS, ejecutar
from src.motor.plantillas import fmt, fmt_p
from src.persistencia.repositorio import ErrorRepositorio
from src.servicios.analisis import (ErrorAnalisis, bitacora_analisis, datos_de_preparacion, derivar_version,
                                    ejecutar_analisis, guardar_configuracion, historial, nueva_configuracion)

encabezado("Paso 7", "Análisis estadístico",
           "Motor determinista basado en reglas: cada decisión muestra la pregunta, la evidencia y la regla que la justifica.")
e_activo = requerir_estudio()
repo = repositorio()
codigo = e_activo.codigo

preps = [p for p in repo.listar_preparaciones(codigo) if p.get("aprobada")]
versiones = repo.listar_analisis(codigo)
if not preps and not versiones:
    with st.container(border=True):
        st.markdown("#### :material/dataset: Primero aprueba un conjunto de datos")
        st.write("El motor solo analiza conjuntos preparados y **aprobados** («Confirmar datos listos para analizar»).")
        st.page_link(PAGINAS["datos"], label="Ir a Datos preparados", icon=":material/arrow_forward:")
    st.stop()

# ------------------------------------------------------------------ selección de versión
NUEVA = "nueva"
opciones = [v["version"] for v in versiones][::-1]
if not opciones or st.session_state.get("analisis_nuevo"):
    opciones = [NUEVA] + opciones
preferida = st.session_state.get("analisis_version")
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
version_sel = c1.selectbox(
    "Versión del análisis", opciones, index=opciones.index(preferida) if preferida in opciones else 0,
    format_func=lambda v: "Nueva configuración (sin guardar)" if v == NUEVA else
    next(f"v{x['version']}" + (f" · deriva de v{x['padre']}" if x["padre"] else "") + (" · ejecutada · " + (x["estado_final"] or "")
                                                                                         if x["ejecutado"] else " · sin ejecutar")
         for x in versiones if x["version"] == v))
if c2.button("Nueva configuración", icon=":material/add:", width="stretch", disabled=not preps):
    st.session_state["analisis_nuevo"] = True
    st.session_state["analisis_version"] = NUEVA
    st.rerun()

if version_sel == NUEVA:
    base = nueva_configuracion(repo, codigo, preps[-1]["preparacion_id"], usuario())
    guardado = {"config": base.to_dict(), "resultado": None, "comentarios": []}
else:
    guardado = repo.obtener_analisis(codigo, version_sel)
cfg_guardada = ConfiguracionAnalisis.from_dict(guardado["config"])
resultado = guardado["resultado"]
ejecutada = resultado is not None
clave = f"{codigo}_{cfg_guardada.version}_{'n' if version_sel == NUEVA else 'g'}"

if ejecutada:
    final = resultado["conclusion_final"]
    st.badge(f"Conclusión consolidada: {final['estado']}", color=ESTADOS_COLOR.get(final["estado"], "violet"),
             icon=":material/fact_check:")

t_conf, t_res, t_concl, t_red, t_inf, t_hist = st.tabs(
    [":material/tune: Configurar", ":material/query_stats: Resultados por etapa", ":material/rate_review: Conclusiones",
     ":material/fork_right: Rediseño / versión 2", ":material/picture_as_pdf: Informe PDF", ":material/history: Historial y bitácora"])


# ------------------------------------------------------------------ 1 · configurar
def _formulario(cfg0: ConfiguracionAnalisis, bloqueado: bool) -> ConfiguracionAnalisis | None:
    k = lambda n: f"{n}_{clave}"  # noqa: E731
    ids_prep = [p["preparacion_id"] for p in preps] or [cfg0.preparacion_id]
    if cfg0.preparacion_id and cfg0.preparacion_id not in ids_prep:
        ids_prep = [cfg0.preparacion_id] + ids_prep
    prep_id = st.selectbox("Conjunto preparado (aprobado)", ids_prep[::-1], key=k("prep"), disabled=bloqueado,
                           index=ids_prep[::-1].index(cfg0.preparacion_id) if cfg0.preparacion_id in ids_prep else 0)
    try:
        tablas, e, prep = datos_de_preparacion(repo, codigo, prep_id)
    except ErrorRepositorio as exc:
        st.error(str(exc))
        return None
    st.caption(f"Diseño v{prep['version_diseno']} · {prep['conteos']['incluidos_en_preparado']} mediciones incluidas · "
               f"archivo {prep['archivo_original']}")

    with st.container(border=True):
        st.markdown("##### :material/target: Qué se analiza")
        tipos = {"variable": "Dato registrado", "resultado_directo": "Resultado registrado", "derivado": "Resultado calculado (regla aprobada)"}
        tipo = st.segmented_control("Tipo de objeto", list(tipos), format_func=tipos.get, default=cfg0.objeto_tipo, key=k("tipo"),
                                    disabled=bloqueado) or "variable"
        regla = None
        if tipo == "variable":
            ops = {v.id: f"{v.id} · {v.nombre} ({v.unidad})" for v in e.variables if v.tipo_dato in ("decimal", "entero")}
        elif tipo == "resultado_directo":
            ops = {r.id: f"{r.id} · {r.nombre}" for r in e.resultados if r.origen == "directo" and r.ambito == "medicion"}
        else:
            ops = {r.id: f"{r.id} · {r.nombre}" for r in e.resultados if r.origen == "calculado" and r.ambito == "medicion"}
        if not ops:
            st.warning("El diseño no tiene objetos de este tipo.")
            return None
        lista = list(ops)
        objeto = st.selectbox("Objeto del análisis", lista, format_func=ops.get, key=k("obj"), disabled=bloqueado,
                              index=lista.index(cfg0.objeto_id) if cfg0.objeto_id in lista else 0)
        if tipo == "derivado":
            res = next(r for r in e.resultados if r.id == objeto)
            vars_num = {v.id: f"{v.id} · {v.nombre} ({v.unidad})" for v in e.variables if v.tipo_dato in ("decimal", "entero")}
            r0 = cfg0.regla or ReglaDerivacion(a=(res.dependencias + [""])[0], b=(res.dependencias + ["", ""])[1],
                                               referencia=res.referencia_calculo)
            lv = list(vars_num)
            a1, a2 = st.columns(2)
            a = a1.selectbox("Minuendo (a)", lv, format_func=vars_num.get, index=lv.index(r0.a) if r0.a in lv else 0, key=k("ra"), disabled=bloqueado)
            b = a2.selectbox("Sustraendo (b)", lv, format_func=vars_num.get, index=lv.index(r0.b) if r0.b in lv else min(1, len(lv) - 1),
                             key=k("rb"), disabled=bloqueado)
            ref = st.text_input("Documento que aprueba la regla «a − b»", r0.referencia, key=k("rref"), disabled=bloqueado,
                                help="El motor solo implementa la diferencia a − b. No inventa fórmulas.")
            apr = st.checkbox("Regla aprobada", r0.aprobada, key=k("rapr"), disabled=bloqueado)
            regla = ReglaDerivacion("diferencia", a, b, ref, apr)

    with st.container(border=True):
        st.markdown("##### :material/alt_route: Verificación o validación")
        m1, m2 = st.columns(2)
        mv = m1.segmented_control("¿El método está validado?", ["si", "no"], default=cfg0.metodo_validado or None, key=k("mv"),
                                  format_func={"si": "Sí, validado", "no": "No"}.get, disabled=bloqueado) or ""
        modif = m2.text_input("Modificaciones al método (vacío = ninguna)", cfg0.modificaciones, key=k("mod"), disabled=bloqueado)
        docp = st.text_input("Documentación de validación previa (si existe)", cfg0.documentacion_previa, key=k("doc"), disabled=bloqueado)
        st.caption("Características: el laboratorio decide cuáles son requeridas. El motor no las impone.")
        filas = []
        for cod, (nombre, impl, ref) in CARACTERISTICAS.items():
            c = cfg0.caracteristica(cod) or CaracteristicaConfig(cod)
            filas.append({"codigo": cod, "Característica": nombre, "Implementada": impl, "Estado": c.estado,
                          "Justificación": c.justificacion, "Fuente": c.fuente, "Referencia": ref})
        car = st.data_editor(pd.DataFrame(filas), key=k("car"), hide_index=True, width="stretch", disabled=bloqueado or ["codigo", "Característica", "Implementada", "Referencia"],
                             column_config={"codigo": None, "Estado": st.column_config.SelectboxColumn(options=ESTADOS_CARACTERISTICA, required=True)})

    with st.container(border=True):
        st.markdown("##### :material/account_tree: Estructura del diseño")
        inter = st.toggle("Estudio interlaboratorio (ISO 5725-2: participan laboratorios distintos)", cfg0.es_interlaboratorio,
                          key=k("inter"), disabled=bloqueado)
        campos = {"tecnico": "Técnico", "patron": "Patrón"} | {f.id: f"{f.id} · {f.nombre}" for f in e.factores}
        lab, pi = "", []
        if inter:
            lc = list(campos)
            lab = st.selectbox("¿Qué campo identifica al laboratorio?", lc, format_func=campos.get, key=k("lab"), disabled=bloqueado,
                               index=lc.index(cfg0.factor_laboratorio) if cfg0.factor_laboratorio in lc else 0)
            st.warning("Los técnicos de un mismo laboratorio **no** son laboratorios. Marca esta opción solo si cada nivel del campo "
                       "es un laboratorio distinto.", icon=":material/warning:")
        else:
            pi = st.multiselect("Condiciones que cambian dentro del laboratorio (precisión intermedia)", list(campos),
                                default=[x for x in cfg0.factores_precision_intermedia if x in campos], format_func=campos.get,
                                key=k("pi"), disabled=bloqueado,
                                help="Forman las celdas: dentro de cada celda las réplicas se consideran en condiciones de repetibilidad.")
    with st.container(border=True):
        st.markdown("##### :material/straighten: Referencia para el sesgo")
        tr = {"ninguna": "Sin referencia", "valor_por_nivel": "Valor de referencia por punto",
              "objeto_es_diferencia": "El objeto ya es una diferencia (error/corrección): referencia 0"}
        rtipo = st.radio("Referencia", list(tr), format_func=tr.get, index=list(tr).index(cfg0.referencia_tipo), key=k("rt"),
                         horizontal=True, disabled=bloqueado, label_visibility="collapsed")
        refs = []
        if rtipo == "valor_por_nivel":
            df = pd.DataFrame([{"punto_id": p.id, "Punto": f"{fmt(p.valor_nominal)} {p.unidad}",
                                "Valor": next((r.valor for r in cfg0.referencias if r.punto_id == p.id), None),
                                "u estándar": next((r.incertidumbre for r in cfg0.referencias if r.punto_id == p.id), None),
                                "Fuente": next((r.fuente for r in cfg0.referencias if r.punto_id == p.id), "")} for p in e.puntos])
            ed = st.data_editor(df, key=k("refs"), hide_index=True, width="stretch", disabled=bloqueado or ["punto_id", "Punto"],
                                column_config={"punto_id": None, "Valor": st.column_config.NumberColumn(format="%.6g"),
                                               "u estándar": st.column_config.NumberColumn(format="%.6g")})
            refs = [ReferenciaNivel(r["punto_id"], None if pd.isna(r["Valor"]) else float(r["Valor"]),
                                    None if pd.isna(r["u estándar"]) else float(r["u estándar"]), r["Fuente"] or "") for _, r in ed.iterrows()]

    with st.container(border=True):
        st.markdown("##### :material/rule: Criterios de aceptación (sin valores por defecto)")
        st.caption("Sin criterio aprobado, con límite, regla de decisión y fuente, el resultado queda «CALCULADO_SIN_EVALUACION».")
        params = sorted({p for v in PARAMETROS.values() for p in v})
        dfc = pd.DataFrame([{"Id": c.id, "Característica": c.caracteristica, "Parámetro": c.parametro, "Operador": c.operador,
                             "Límite": c.limite, "Unidad": c.unidad, "Regla de decisión": c.regla_decision, "Fuente": c.fuente,
                             "Aprobado": c.aprobado, "Puntos (vacío = todos)": ", ".join(c.puntos)} for c in cfg0.criterios],
                           columns=["Id", "Característica", "Parámetro", "Operador", "Límite", "Unidad", "Regla de decisión",
                                    "Fuente", "Aprobado", "Puntos (vacío = todos)"])
        edc = st.data_editor(dfc, key=k("crit"), hide_index=True, width="stretch", num_rows="dynamic", disabled=bloqueado,
                             column_config={"Característica": st.column_config.SelectboxColumn(options=list(PARAMETROS)),
                                            "Parámetro": st.column_config.SelectboxColumn(options=params),
                                            "Operador": st.column_config.SelectboxColumn(options=OPERADORES),
                                            "Límite": st.column_config.NumberColumn(format="%.6g"),
                                            "Regla de decisión": st.column_config.SelectboxColumn(options=list(REGLAS_DECISION), help=" · ".join(f"{a}: {b}" for a, b in REGLAS_DECISION.items())),
                                            "Aprobado": st.column_config.CheckboxColumn(default=False)})
        criterios = []
        for i, r in edc.reset_index(drop=True).iterrows():
            if not r["Característica"]:
                continue
            criterios.append(CriterioMotor(r["Id"] or f"CM-{i + 1:02d}", r["Característica"], r["Parámetro"] or PARAMETROS[r["Característica"]][0],
                                           r["Operador"] or "<=", None if pd.isna(r["Límite"]) else float(r["Límite"]),
                                           r["Unidad"] or "", r["Regla de decisión"] or "", r["Fuente"] or "", bool(r["Aprobado"]),
                                           [x.strip() for x in str(r["Puntos (vacío = todos)"] or "").split(",") if x.strip()]))

    with st.container(border=True):
        st.markdown("##### :material/calculate: Parámetros estadísticos y responsables")
        s1, s2, s3, s4 = st.columns(4)
        alfa = s1.number_input("α", 0.001, 0.2, float(cfg0.alfa), 0.01, format="%.3f", key=k("alfa"), disabled=bloqueado)
        conf = s2.number_input("Nivel de confianza (IC)", 0.80, 0.999, float(cfg0.nivel_confianza), 0.01, format="%.3f", key=k("conf"), disabled=bloqueado)
        pn = s3.selectbox("Prueba de normalidad", PRUEBAS_NORMALIDAD, index=PRUEBAS_NORMALIDAD.index(cfg0.prueba_normalidad), key=k("pn"), disabled=bloqueado)
        alerta = s4.number_input("Alerta de faltantes % (opcional)", 0.0, 100.0, cfg0.alerta_faltantes_pct, key=k("al"), disabled=bloqueado,
                                 help="No es un criterio de aplicabilidad; solo genera un aviso. Vacío = sin alerta.")
        r1, r2, r3 = st.columns(3)
        edicion = r1.text_input("Edición normativa aplicada", cfg0.version_normativa, key=k("ed"), disabled=bloqueado)
        rev = r2.text_input("Revisor", cfg0.revisado_por, key=k("rev"), disabled=bloqueado)
        aut = r3.text_input("Autorizador", cfg0.autorizado_por, key=k("aut"), disabled=bloqueado)

    caracteristicas = [CaracteristicaConfig(r["codigo"], r["Estado"], r["Justificación"] or "", r["Fuente"] or "") for _, r in car.iterrows()]
    datos = cfg0.to_dict()
    datos.update(preparacion_id=prep_id, objeto_tipo=tipo, objeto_id=objeto, metodo_validado=mv, modificaciones=modif,
                 documentacion_previa=docp, es_interlaboratorio=inter, factor_laboratorio=lab, factores_precision_intermedia=pi,
                 referencia_tipo=rtipo, alfa=alfa, nivel_confianza=conf, prueba_normalidad=pn, alerta_faltantes_pct=alerta,
                 version_normativa=edicion.strip(), revisado_por=rev, autorizado_por=aut)
    cfg = ConfiguracionAnalisis.from_dict(datos)
    cfg.regla, cfg.caracteristicas, cfg.criterios, cfg.referencias = regla, caracteristicas, criterios, refs
    cfg.exclusiones = cfg0.exclusiones
    st.session_state[f"tablas_{clave}"] = (tablas, e, prep)
    return cfg


def _vista_previa(cfg: ConfiguracionAnalisis) -> None:
    tablas, e, prep = st.session_state[f"tablas_{clave}"]
    try:
        r = ejecutar(tablas, e, cfg, {"vista_previa": True})
    except ErrorDatosMotor as exc:
        st.error(str(exc), icon=":material/error:")
        return
    st.markdown("##### :material/bolt: Ruta de decisión en tiempo real")
    st.caption("Se recalcula con cada cambio, sin guardar. Muestra qué técnicas aplican y por qué.")
    ap = pd.DataFrame([{"Etapa": x["etapa"], "Técnica": x["tecnica"], "Agrupación": x["agrupacion"], "Estado": x["estado"],
                        "Motivo": " ".join(x["motivos"][:1])} for x in r["resultados"]])
    orden = {k: i for i, (k, _) in enumerate(ETAPAS)}
    resumen = ap.groupby(["Etapa", "Técnica", "Estado"], sort=False).size().rename("Grupos").reset_index()
    resumen = resumen.sort_values("Etapa", key=lambda s: s.map(orden), kind="stable")
    if not any(cfg.activa(c) for c in CARACTERISTICAS):
        st.warning("Ninguna característica está marcada como REQUERIDA o SELECCIONADA: no se calculará desempeño.",
                   icon=":material/checklist:")
    tabla(resumen)
    with st.expander("Árbol de decisiones (pregunta → respuesta → evidencia → regla)"):
        tabla(pd.DataFrame(r["arbol"]).rename(columns={"pregunta": "Pregunta", "respuesta": "Respuesta", "evidencia": "Evidencia", "regla": "Regla"}))
    for aviso in r["ruta"]["avisos"]:
        st.warning(aviso, icon=":material/alt_route:")
    st.info(f"Conclusión prevista: **{r['conclusion_final']['estado']}** — {r['conclusion_final']['texto']}", icon=":material/visibility:")


with t_conf:
    if ejecutada:
        st.info("Esta versión ya se ejecutó y es inmutable. Para cambiar parámetros, criterios o excluir datos usa "
                "**Rediseño / versión 2**.", icon=":material/lock:")
    cfg_actual = _formulario(cfg_guardada, ejecutada)
    if cfg_actual is not None:
        if not ejecutada:
            b1, b2 = st.columns(2)
            if b1.button("Guardar configuración", icon=":material/save:", width="stretch") and requerir_usuario():
                try:
                    guardar_configuracion(repo, cfg_actual, usuario())
                    st.session_state["analisis_version"] = cfg_actual.version
                    st.session_state.pop("analisis_nuevo", None)
                    st.rerun()
                except ErrorRepositorio as exc:
                    st.error(str(exc))
            if b2.button("Ejecutar análisis", type="primary", icon=":material/play_arrow:", width="stretch") and requerir_usuario():
                try:
                    ejecutar_analisis(repo, cfg_actual, usuario())
                    st.session_state["analisis_version"] = cfg_actual.version
                    st.session_state.pop("analisis_nuevo", None)
                    st.toast("Análisis ejecutado y guardado.", icon=":material/check_circle:")
                    st.rerun()
                except (ErrorAnalisis, ErrorDatosMotor, ErrorRepositorio) as exc:
                    st.error(str(exc))
        with st.container(border=True):
            _vista_previa(cfg_actual)


# ------------------------------------------------------------------ 2 · resultados por etapa
def _comentarios(etapa: str) -> None:
    propios = [c for c in guardado["comentarios"] if c["etapa"] == etapa]
    with st.container(border=True):
        st.markdown(f"**:material/comment: Retroalimentación humana — {etapa}**")
        for c in propios:
            st.markdown(f"<small>{c['fecha'][:16].replace('T', ' ')} · **{c['usuario']}**</small><br>{c['texto']}", unsafe_allow_html=True)
        if version_sel == NUEVA:
            return
        with st.form(f"com_{etapa}_{clave}", clear_on_submit=True, border=False):
            txt = st.text_area("Nuevo comentario", key=f"txt_{etapa}_{clave}", height=80, placeholder="Observación técnica de esta etapa…")
            if st.form_submit_button("Guardar comentario", icon=":material/send:") and requerir_usuario():
                try:
                    repo.agregar_comentario(codigo, version_sel, etapa, txt, usuario())
                    st.rerun()
                except ErrorRepositorio as exc:
                    st.error(str(exc))


def _detalle(r: dict, figs: dict) -> None:
    color = ESTADOS_COLOR.get(r.get("decision_metrologica") or r["estado"], "gray")
    titulo = f"{r['tecnica']} · {r['agrupacion']}"
    with st.expander(f":{color}[●] {titulo}"):
        if r["texto"]:
            st.write(r["texto"])
        filas = [("Estado", r["estado"]), ("Origen de la regla", r["origen_regla"]), ("Referencia", r["referencia"]),
                 ("Fórmula", r["formula"]), ("Estadístico", f"{r['estadistico'].get('simbolo', '')} = {fmt(r['estadistico'].get('valor'))}" if r["estadistico"] else ""),
                 ("gl", fmt(r["gl"], 4) if isinstance(r["gl"], (int, float)) else (json.dumps(r["gl"]) if r["gl"] else "")),
                 ("Valor p", fmt_p(r["p_valor"]) if r["p_valor"] is not None else ""),
                 ("Críticos", "; ".join(f"{a}: {fmt(b)}" for a, b in r["criticos"].items() if a != "origen") + (f" ({r['criticos'].get('origen')})" if r["criticos"] else "")),
                 ("IC", f"[{fmt(r['ic'][0])}; {fmt(r['ic'][1])}]" if r["ic"] and r["ic"][0] is not None else ""),
                 ("Estimación", f"{r['estimacion'].get('nombre')} = {fmt(r['estimacion'].get('valor'))} {r['estimacion'].get('unidad') or ''}" if r["estimacion"] and r["etapa"] == "desempeno" else ""),
                 ("Decisión inferencial", r["decision_inferencial"]), ("Decisión metrológica", r["decision_metrologica"]),
                 ("Motivos", " ".join(r["motivos"])), ("Limitaciones", " ".join(r["limitaciones"]))]
        tabla(pd.DataFrame([f for f in filas if f[1]], columns=["Campo", "Valor"]))
        if r["tabla"] and r["etapa"] != "normalidad":
            st.caption("Cálculos intermedios")
            tabla(pd.DataFrame(r["tabla"]).drop(columns=["ids"], errors="ignore"))
        for g in r["graficos"]:
            if g in figs:
                st.image(figs[g], width=420 if g.startswith("qq") else "stretch")


with t_res:
    if not ejecutada:
        st.info("Ejecuta el análisis para ver los resultados por etapa.", icon=":material/play_arrow:")
    else:
        figs = graficos.generar(resultado)
        st.caption(f"Ejecutado {resultado['meta']['ejecutado_en'][:16].replace('T', ' ')} por {resultado['meta'].get('ejecutado_por', '—')} · "
                   f"huella `{resultado['meta']['huella_resultado'][:16]}…` · {resultado['objeto']['descripcion']}")
        for etapa, nombre in ETAPAS:
            st.markdown(f"#### {nombre}")
            st.info(resultado["conclusiones"].get(etapa, ""), icon=":material/smart_toy:")
            for r in [x for x in resultado["resultados"] if x["etapa"] == etapa]:
                _detalle(r, figs)
            _comentarios(etapa)
        with st.expander(":material/account_tree: Árbol completo de decisiones"):
            tabla(pd.DataFrame(resultado["arbol"]))

# ------------------------------------------------------------------ 3 · conclusiones
with t_concl:
    if not ejecutada:
        st.info("Ejecuta el análisis para ver las conclusiones.", icon=":material/play_arrow:")
    else:
        st.markdown("#### Conclusiones técnicas preliminares (automáticas)")
        for etapa, nombre in ETAPAS:
            st.markdown(f"**{nombre}.** {resultado['conclusiones'].get(etapa, '')}")
        final = resultado["conclusion_final"]
        with st.container(border=True):
            st.markdown(f"##### :{ESTADOS_COLOR.get(final['estado'], 'violet')}[:material/verified:] {final['estado']}")
            st.write(resultado["conclusiones"]["conclusion_final"])
        tabla(pd.DataFrame([{"Característica": f["caracteristica"], "Configuración": f["estado_configurado"], "Ejecución": f["ejecucion"],
                             "Decisión": f["decision"], "Referencia": f["referencia"]} for f in resultado["caracteristicas"]]))
        _comentarios("conclusiones")

# ------------------------------------------------------------------ 4 · rediseño
with t_red:
    if version_sel == NUEVA:
        st.info("Guarda o ejecuta primero esta configuración.", icon=":material/save:")
    else:
        st.markdown("#### Crear una versión derivada del análisis")
        st.write("Clona esta configuración en una versión nueva (con versión padre, motivo y diferencias en el historial). "
                 "Después podrás modificar parámetros y criterios en **Configurar** y volver a ejecutar.")
        sugeridos = []
        if ejecutada:
            for r in resultado["resultados"]:
                for f in r.get("tabla", []):
                    if f.get("clasificacion") in ("rezagado (*)", "atípico (**)") and f.get("medicion_id"):
                        sugeridos.append(f["medicion_id"])
            ids = [d["medicion_id"] for d in resultado["datos"]]
        else:
            ids = []
        with st.form(f"red_{clave}"):
            motivo = st.text_area("Motivo del cambio (obligatorio)", placeholder="p. ej. Ajuste del criterio según observación del revisor")
            excl = st.multiselect("Excluir mediciones (opcional)", ids, help="Señaladas por las pruebas: " + (", ".join(sugeridos) or "ninguna"))
            m_ex = st.text_input("Motivo técnico de la exclusión", placeholder="Causa verificable (bitácora, falla del equipo…)")
            resp = st.text_input("Responsable que autoriza la exclusión", value=usuario())
            if st.form_submit_button("Crear versión derivada", type="primary", icon=":material/fork_right:") and requerir_usuario():
                try:
                    nueva = derivar_version(repo, codigo, version_sel, motivo, usuario(),
                                            exclusiones=[Exclusion(m, m_ex, resp) for m in excl])
                    st.session_state["analisis_version"] = nueva.version
                    st.rerun()
                except (ErrorAnalisis, ErrorRepositorio) as exc:
                    st.error(str(exc))
        st.divider()
        st.markdown("#### Clonar el estudio completo (rediseño del experimento)")
        st.write("Crea un estudio nuevo en borrador con el mismo diseño, para cambiar puntos, réplicas o condiciones. "
                 "Queda vinculado al estudio original (campo «derivado de»).")
        with st.form(f"clon_{clave}"):
            nombre = st.text_input("Nombre del nuevo estudio", value=f"{e_activo.nombre} (versión 2)")
            if st.form_submit_button("Clonar estudio", icon=":material/content_copy:") and requerir_usuario():
                clon = repo.clonar_estudio(codigo, nombre, usuario())
                st.session_state["estudio_codigo"] = clon.codigo
                st.success(f"Estudio {clon.codigo} creado. Edítalo en el asistente o en Edición avanzada.")

# ------------------------------------------------------------------ 5 · informe
with t_inf:
    if not ejecutada:
        st.info("Ejecuta el análisis para emitir el informe.", icon=":material/play_arrow:")
    else:
        with st.form(f"inf_{clave}"):
            i1, i2 = st.columns(2)
            fecha = i1.date_input("Fecha de emisión", date.today())
            elab = i2.text_input("Elaboró", usuario() or cfg_guardada.elaborado_por)
            i3, i4 = st.columns(2)
            rev = i3.text_input("Revisó", cfg_guardada.revisado_por)
            aut = i4.text_input("Autorizó", cfg_guardada.autorizado_por)
            generar = st.form_submit_button("Generar informe PDF", type="primary", icon=":material/picture_as_pdf:")
        if generar and requerir_usuario():
            from src.informes.pdf import generar_informe
            estudio_v, _ = repo.obtener_version(codigo, resultado["meta"]["version_diseno"])
            control = {"fecha": fecha.isoformat(), "elaborado_por": elab, "revisado_por": rev, "autorizado_por": aut}
            with st.spinner("Generando informe…"):
                pdf = generar_informe(resultado, guardado["config"], estudio_v, guardado["comentarios"], historial(repo, codigo),
                                      bitacora_analisis(repo, codigo), control)
            nombre = repo.guardar_informe(codigo, version_sel, pdf, {**control, "emitido_por": usuario(), "sha256": sha256_bytes(pdf),
                                                                     "fecha": fecha.isoformat()})
            st.session_state[f"pdf_{clave}"] = (nombre, pdf)
        if st.session_state.get(f"pdf_{clave}"):
            nombre, pdf = st.session_state[f"pdf_{clave}"]
            st.success(f"Informe emitido: {nombre} (SHA-256 `{sha256_bytes(pdf)[:16]}…`).", icon=":material/task:")
            st.download_button("Descargar informe PDF", pdf, file_name=f"{codigo}_analisis_v{version_sel}_{nombre}", mime="application/pdf",
                               icon=":material/download:", type="primary")

# ------------------------------------------------------------------ 6 · historial
with t_hist:
    h = historial(repo, codigo)
    if h:
        tabla(pd.DataFrame([{"Versión": f"v{v['version']}", "Padre": f"v{v['padre']}" if v["padre"] else "—", "Motivo": v["motivo_cambio"],
                             "Cambios": "; ".join(c["campo"] for c in v["cambios"]), "Ejecutada": "sí" if v["ejecutado"] else "no",
                             "Estado final": v["estado_final"], "Creada": v["creado_en"][:16].replace("T", " ")} for v in h]))
        for v in h:
            if v["cambios"]:
                with st.expander(f"Diferencias de v{v['version']} respecto a v{v['padre']}"):
                    tabla(pd.DataFrame([{"Campo": c["campo"], "Antes": json.dumps(c["antes"], ensure_ascii=False)[:300],
                                         "Después": json.dumps(c["despues"], ensure_ascii=False)[:300]} for c in v["cambios"]]))
    st.markdown("##### Bitácora de auditoría")
    tabla(pd.DataFrame(bitacora_analisis(repo, codigo)[::-1]).assign(detalle=lambda d: d["detalle"].astype(str)) if bitacora_analisis(repo, codigo) else pd.DataFrame())
