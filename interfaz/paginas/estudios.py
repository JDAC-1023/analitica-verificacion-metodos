import pandas as pd
import streamlit as st

from interfaz.comun import (
    PAGINAS, banda_de_pasos, encabezado, estudio_actual, guardar, repositorio, requerir_usuario, tabla, usuario,
)
from src.configuracion.validacion_estudio import revisar_alcance, revisar_identificacion, revisar_recursos
from src.modelos.estudio import TIPOS_ESTUDIO, Magnitud, Punto, Recurso, siguiente_id


def _num(valor):
    try:
        return None if valor is None or pd.isna(valor) else float(valor)
    except (TypeError, ValueError):
        return None


def _txt(valor) -> str:
    return "" if valor is None or (isinstance(valor, float) and pd.isna(valor)) else str(valor).strip()


def _estado_etapa(etapa) -> None:
    if etapa.completa:
        st.success("Esta sección está completa.", icon=":material/check_circle:")
    else:
        st.warning("Falta: " + " · ".join(etapa.faltantes), icon=":material/pending:")
    for a in etapa.advertencias:
        st.caption(f":material/info: {a}")


encabezado("Paso 1", "Estudios", "Crea el estudio, identifícalo y define en qué magnitudes, puntos y con qué recursos trabajarás.")

repo = repositorio()
e = estudio_actual()
banda_de_pasos(e)

with st.expander("Crear un estudio nuevo", icon=":material/add_circle:", expanded=e is None):
    with st.form("nuevo_estudio", clear_on_submit=True, border=False):
        nombre = st.text_input("Nombre del estudio", placeholder="Ej.: Verificación del método de caracterización de medios isotermos",
                               help="E01 · Identificador descriptivo. El código único lo asigna el sistema (E02).")
        if st.form_submit_button("Crear estudio", type="primary", icon=":material/add:"):
            if not nombre.strip():
                st.error("Escribe un nombre para el estudio.")
            elif requerir_usuario():
                nuevo = repo.crear_estudio(nombre, usuario())
                st.session_state["estudio_codigo"] = nuevo.codigo
                st.rerun()

if e is None:
    st.info("Selecciona un estudio en la barra lateral o crea uno nuevo para continuar.", icon=":material/arrow_back:")
    st.stop()

st.markdown(f"#### {e.codigo} · {e.nombre}")
tab_id, tab_alc, tab_rec, tab_hist = st.tabs([
    ":material/badge: Identificación", ":material/straighten: Magnitudes y puntos",
    ":material/groups: Recursos", ":material/history: Bitácora",
])

# --------------------------------------------------------------------- Identificación
with tab_id:
    _estado_etapa(revisar_identificacion(e))
    with st.form(f"identificacion_{e.actualizado_en}"):
        c1, c2 = st.columns(2)
        nombre = c1.text_input("Nombre del estudio", e.nombre, help="E01")
        c2.text_input("Código del estudio", e.codigo, disabled=True, help="E02 · Lo asigna el sistema para evitar confusiones.")
        tipo = c1.segmented_control("¿Qué tipo de estudio harás?", TIPOS_ESTUDIO, default=e.tipo or TIPOS_ESTUDIO[0],
                                    help="E03 · Identifica el propósito; por sí solo no determina la ruta estadística.")
        responsable = c2.text_input("Responsable del estudio", e.responsable,
                                    help="E08 · ¿Quién revisará y aprobará técnicamente el estudio?")
        metodo = c1.text_input("¿Qué método vas a evaluar?", e.metodo, help="E04 · Nombre o código del método del laboratorio.")
        version_metodo = c2.text_input("Versión del método", e.version_metodo, help="E05 · Edición o versión vigente.")
        uso = st.text_area("¿Para qué necesitas comprobarlo?", e.uso_previsto, height=90,
                           help="E06 · Uso previsto y qué buscas demostrar con el estudio.")
        referencia = st.text_input("Documento de referencia (si existe)", e.documento_referencia,
                                   help="E07 · Norma, guía o procedimiento aplicable. Es sustento documental; no fija reglas.")
        if st.form_submit_button("Guardar identificación", type="primary", icon=":material/save:") and requerir_usuario():
            e.nombre, e.tipo, e.responsable, e.metodo = nombre.strip(), tipo or e.tipo, responsable.strip(), metodo.strip()
            e.version_metodo, e.uso_previsto, e.documento_referencia = version_metodo.strip(), uso.strip(), referencia.strip()
            guardar(e, "identificación del estudio")
            st.rerun()

# --------------------------------------------------------------------- Alcance
with tab_alc:
    _estado_etapa(revisar_alcance(e))
    with st.form(f"alcance_{e.actualizado_en}"):
        st.markdown("**¿Qué magnitudes intervienen y en qué intervalo trabajas?**")
        st.caption("E09 · E10 · Agrega una fila por magnitud con su unidad. El código se asigna al guardar.")
        df_mag = pd.DataFrame([vars(m) for m in e.magnitudes], columns=["id", "nombre", "unidad", "intervalo_min", "intervalo_max"])
        mag = st.data_editor(df_mag, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_mag_{e.actualizado_en}",
                             column_config={
                                 "id": st.column_config.TextColumn("Código", disabled=True, width="small"),
                                 "nombre": st.column_config.TextColumn("Magnitud", required=True),
                                 "unidad": st.column_config.TextColumn("Unidad", required=True, width="small"),
                                 "intervalo_min": st.column_config.NumberColumn("Desde", format="%g"),
                                 "intervalo_max": st.column_config.NumberColumn("Hasta", format="%g"),
                             })
        st.markdown("**¿En qué puntos vas a medir?**")
        st.caption("E11 · Valores nominales por magnitud. Mediciones en puntos distintos nunca se tratan como repeticiones de una misma condición.")
        etiquetas_mag = {f"{m.nombre} [{m.unidad}]": m.id for m in e.magnitudes}
        inv = {v: k for k, v in etiquetas_mag.items()}
        df_pt = pd.DataFrame([{"id": p.id, "magnitud": inv.get(p.magnitud_id, ""), "valor_nominal": p.valor_nominal}
                              for p in e.puntos], columns=["id", "magnitud", "valor_nominal"])
        pts = st.data_editor(df_pt, num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_pt_{e.actualizado_en}",
                             column_config={
                                 "id": st.column_config.TextColumn("Código", disabled=True, width="small"),
                                 "magnitud": st.column_config.SelectboxColumn("Magnitud", options=list(etiquetas_mag), required=True),
                                 "valor_nominal": st.column_config.NumberColumn("Valor nominal", format="%g", required=True),
                             })
        if not e.magnitudes:
            st.caption(":material/info: Guarda primero las magnitudes; luego podrás elegirlas para los puntos.")
        if st.form_submit_button("Guardar magnitudes y puntos", type="primary", icon=":material/save:") and requerir_usuario():
            nuevas = []
            for _, f in mag.iterrows():
                if not _txt(f["nombre"]) and not _txt(f["unidad"]):
                    continue
                mid = _txt(f["id"]) or siguiente_id("MAG", [m.id for m in nuevas] + [m.id for m in e.magnitudes])
                nuevas.append(Magnitud(mid, _txt(f["nombre"]), _txt(f["unidad"]), _num(f["intervalo_min"]), _num(f["intervalo_max"])))
            unidades = {m.id: m.unidad for m in nuevas}
            puntos, errores = [], []
            for _, f in pts.iterrows():
                if not _txt(f["magnitud"]) and _num(f["valor_nominal"]) is None:
                    continue
                magnitud_id = etiquetas_mag.get(_txt(f["magnitud"]))
                if magnitud_id not in unidades or _num(f["valor_nominal"]) is None:
                    errores.append("Cada punto necesita una magnitud existente y un valor nominal.")
                    continue
                pid = _txt(f["id"]) or siguiente_id("PT", [p.id for p in puntos] + [p.id for p in e.puntos])
                puntos.append(Punto(pid, magnitud_id, _num(f["valor_nominal"]), unidades[magnitud_id]))
            usados = {m.punto_id for m in e.plan}
            borrados = usados - {p.id for p in puntos}
            if errores:
                st.error(errores[0])
            elif borrados:
                st.error(f"No puedes eliminar puntos que ya están en el plan ({', '.join(sorted(borrados))}). Quítalos primero del plan.")
            else:
                e.magnitudes, e.puntos = nuevas, puntos
                guardar(e, "magnitudes y puntos")
                st.rerun()

# --------------------------------------------------------------------- Recursos
with tab_rec:
    _estado_etapa(revisar_recursos(e))
    etiquetas_mag = {f"{m.nombre} [{m.unidad}]": m.id for m in e.magnitudes}
    inv = {v: k for k, v in etiquetas_mag.items()}
    with st.form(f"recursos_{e.actualizado_en}"):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("**¿Quiénes pueden medir?**")
            st.caption("R01 · Agrega tantos técnicos como participen.")
            tec = st.data_editor(pd.DataFrame([{"codigo": t.codigo, "nombre": t.nombre} for t in e.tecnicos], columns=["codigo", "nombre"]),
                                 num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_tec_{e.actualizado_en}",
                                 column_config={"codigo": st.column_config.TextColumn("Código", required=True, help="Ej.: T-01"),
                                                "nombre": st.column_config.TextColumn("Nombre")})
        with c2:
            st.markdown("**¿Qué patrones utilizarás?**")
            st.caption("R02 · R03 · Código, magnitud e intervalo útil de cada patrón.")
            pat = st.data_editor(
                pd.DataFrame([{"codigo": p.codigo, "nombre": p.nombre, "magnitud": inv.get(p.magnitud_id, ""),
                               "intervalo_min": p.intervalo_min, "intervalo_max": p.intervalo_max} for p in e.patrones],
                             columns=["codigo", "nombre", "magnitud", "intervalo_min", "intervalo_max"]),
                num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_pat_{e.actualizado_en}",
                column_config={"codigo": st.column_config.TextColumn("Código", required=True, help="Ej.: P-01"),
                               "nombre": st.column_config.TextColumn("Descripción"),
                               "magnitud": st.column_config.SelectboxColumn("Magnitud", options=list(etiquetas_mag)),
                               "intervalo_min": st.column_config.NumberColumn("Útil desde", format="%g"),
                               "intervalo_max": st.column_config.NumberColumn("Útil hasta", format="%g")})
        st.markdown("**Equipo a evaluar (IBC)**")
        st.caption("Descripción e identificación del equipo bajo prueba.")
        ibc = st.data_editor(
            pd.DataFrame([{"codigo": i.codigo, "descripcion": i.descripcion, "marca": i.marca, "modelo": i.modelo, "serie": i.serie,
                           "magnitud": inv.get(i.magnitud_id, ""), "resolucion": i.resolucion, "intervalo_min": i.intervalo_min,
                           "intervalo_max": i.intervalo_max} for i in e.ibcs],
                         columns=["codigo", "descripcion", "marca", "modelo", "serie", "magnitud", "resolucion", "intervalo_min", "intervalo_max"]),
            num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_ibc_{e.actualizado_en}",
            column_config={"codigo": st.column_config.TextColumn("Código", required=True),
                           "descripcion": st.column_config.TextColumn("Descripción", required=True),
                           "marca": st.column_config.TextColumn("Marca"), "modelo": st.column_config.TextColumn("Modelo"),
                           "serie": st.column_config.TextColumn("Serie"),
                           "magnitud": st.column_config.SelectboxColumn("Magnitud", options=list(etiquetas_mag)),
                           "resolucion": st.column_config.TextColumn("Resolución"),
                           "intervalo_min": st.column_config.NumberColumn("Desde", format="%g"),
                           "intervalo_max": st.column_config.NumberColumn("Hasta", format="%g")})
        st.markdown("**Otros equipos necesarios (si aplica)**")
        st.caption("R04 · Equipos o medios adicionales.")
        eq = st.data_editor(pd.DataFrame([{"codigo": x.codigo, "descripcion": x.descripcion} for x in e.equipos], columns=["codigo", "descripcion"]),
                            num_rows="dynamic", hide_index=True, width="stretch", key=f"ed_eq_{e.actualizado_en}",
                            column_config={"codigo": st.column_config.TextColumn("Código", required=True),
                                           "descripcion": st.column_config.TextColumn("Descripción")})
        st.caption(":material/schedule: R05 · Disponibilidad de recursos: **por definir** en la matriz; se registrará cuando se apruebe el cronograma.")
        if st.form_submit_button("Guardar recursos", type="primary", icon=":material/save:") and requerir_usuario():
            tecnicos = [Recurso(_txt(f["codigo"]), _txt(f["nombre"]), "tecnico") for _, f in tec.iterrows() if _txt(f["codigo"])]
            patrones = [Recurso(_txt(f["codigo"]), _txt(f["nombre"]), "patron", etiquetas_mag.get(_txt(f["magnitud"]), ""),
                                _num(f["intervalo_min"]), _num(f["intervalo_max"])) for _, f in pat.iterrows() if _txt(f["codigo"])]
            equipos = [Recurso(_txt(f["codigo"]), "", "equipo", descripcion=_txt(f["descripcion"])) for _, f in eq.iterrows() if _txt(f["codigo"])]
            ibcs = [Recurso(_txt(f["codigo"]), _txt(f["descripcion"]), "ibc", etiquetas_mag.get(_txt(f["magnitud"]), ""),
                            _num(f["intervalo_min"]), _num(f["intervalo_max"]), descripcion=_txt(f["descripcion"]), marca=_txt(f["marca"]),
                            modelo=_txt(f["modelo"]), serie=_txt(f["serie"]), resolucion=_txt(f["resolucion"]))
                    for _, f in ibc.iterrows() if _txt(f["codigo"])]
            en_uso = {(m.tecnico) for m in e.plan} - {""} - {t.codigo for t in tecnicos}
            en_uso |= {(m.patron) for m in e.plan} - {""} - {p.codigo for p in patrones}
            if en_uso:
                st.error(f"Estos recursos están asignados en el plan y no pueden eliminarse: {', '.join(sorted(en_uso))}.")
            else:
                e.tecnicos, e.patrones, e.equipos, e.ibcs = tecnicos, patrones, equipos, ibcs
                guardar(e, "recursos")
                st.rerun()
    st.page_link(PAGINAS["diseno"], label="Continuar con el diseño experimental", icon=":material/arrow_forward:")

# --------------------------------------------------------------------- Bitácora
with tab_hist:
    st.caption("Registro de auditoría del estudio: quién hizo qué y cuándo. Solo se agregan entradas; nunca se borran.")
    eventos = repo.leer_eventos(e.codigo)
    if eventos:
        df = pd.DataFrame(eventos[::-1])
        df["detalle"] = df["detalle"].map(lambda d: "" if d is None else (d if isinstance(d, str) else str(d)))
        tabla(df.rename(columns={"fecha": "Fecha", "usuario": "Usuario", "accion": "Acción", "detalle": "Detalle"}))
    versiones = repo.listar_versiones(e.codigo)
    if versiones:
        st.markdown("**Versiones aprobadas del diseño**")
        tabla(pd.DataFrame(versiones).rename(columns={"version": "Versión", "huella_diseno": "Huella", "aprobado_por": "Aprobó",
                                                      "fecha_aprobacion": "Fecha", "mediciones": "Mediciones"}))
