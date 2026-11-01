"""Informe técnico en PDF (ReportLab).

Se construye solo con la información guardada: resultado del motor,
configuración, versión del diseño, comentarios, historial y bitácora. No
recalcula nada, de modo que el informe corresponde exactamente a la memoria de
cálculo con su huella.
"""

from __future__ import annotations

import io
import re
from pathlib import Path

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer,
                                Table, TableStyle)

from src.modelos.estudio import Estudio
from src.motor import graficos
from src.motor.plantillas import fmt, fmt_p
from src.motor.referencias import CITAS, FUNDAMENTOS, REFERENCIAS
from src.motor.resultado import CONFORME, INDETERMINADO, NO_CONFORME

# ------------------------------------------------------------------ tipografía
_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
for nombre, archivo in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                        ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf")):
    if nombre not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(nombre, str(_FUENTES / archivo)))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

TINTA = colors.HexColor("#1d1d1b")
GRIS = colors.HexColor("#5b5a55")
LINEA = colors.HexColor("#c9c7c0")
FONDO = colors.HexColor("#f2f1ee")
ACENTO = colors.HexColor("#3f3a78")
ESTADO_COLOR = {CONFORME: colors.HexColor("#1f7a3a"), NO_CONFORME: colors.HexColor("#b3261e"),
                INDETERMINADO: colors.HexColor("#9a6700")}

E = {
    "titulo": ParagraphStyle("titulo", fontName="DV-B", fontSize=17, leading=22, textColor=TINTA, spaceAfter=4),
    "subtitulo": ParagraphStyle("subtitulo", fontName="DV", fontSize=10.5, leading=14, textColor=GRIS, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="DV-B", fontSize=12.5, leading=16, textColor=ACENTO, spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="DV-B", fontSize=10.5, leading=14, textColor=TINTA, spaceBefore=10, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="DV-B", fontSize=9, leading=12, textColor=GRIS, spaceBefore=6, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="DV", fontSize=8.8, leading=12.4, textColor=TINTA, alignment=TA_JUSTIFY, spaceAfter=5),
    "nota": ParagraphStyle("nota", fontName="DV-I", fontSize=7.8, leading=10.5, textColor=GRIS, spaceAfter=4),
    "celda": ParagraphStyle("celda", fontName="DV", fontSize=7.4, leading=9.4, textColor=TINTA, alignment=TA_LEFT),
    "celda_b": ParagraphStyle("celda_b", fontName="DV-B", fontSize=7.4, leading=9.4, textColor=TINTA),
    "ref": ParagraphStyle("ref", fontName="DV", fontSize=8, leading=11, textColor=TINTA, leftIndent=14, firstLineIndent=-14,
                          spaceAfter=4),
    "caja": ParagraphStyle("caja", fontName="DV", fontSize=8.6, leading=12, textColor=TINTA, alignment=TA_JUSTIFY),
    "firma": ParagraphStyle("firma", fontName="DV", fontSize=8, leading=10, textColor=TINTA, alignment=TA_CENTER),
}
ANCHO = A4[0] - 4 * cm


def esc(t) -> str:
    t = "" if t is None else str(t)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)


def P(texto, estilo="p"):
    return Paragraph(esc(texto), E[estilo])


def tabla(filas: list[list], anchos=None, cabecera=True, repetir=1) -> Table:
    datos = [[c if not isinstance(c, str) else Paragraph(esc(c), E["celda_b" if cabecera and i == 0 else "celda"])
              for c in fila] for i, fila in enumerate(filas)]
    t = Table(datos, colWidths=anchos, repeatRows=repetir if cabecera else 0, hAlign="LEFT")
    estilo = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINEA),
              ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
              ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3)]
    if cabecera:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), FONDO), ("LINEBELOW", (0, 0), (-1, 0), 0.8, GRIS)]
    t.setStyle(TableStyle(estilo))
    return t


def caja(texto: str, titulo: str = "") -> Table:
    contenido = [Paragraph(f"<b>{esc(titulo)}</b>", E["caja"])] if titulo else []
    contenido.append(Paragraph(esc(texto), E["caja"]))
    t = Table([[contenido]], colWidths=[ANCHO])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FONDO), ("LINEBEFORE", (0, 0), (0, -1), 2.5, ACENTO),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


def imagen(png: bytes, ancho_cm: float) -> Image:
    img = Image(io.BytesIO(png))
    escala = ancho_cm * cm / img.imageWidth
    img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
    return img


# ------------------------------------------------------------------ plantilla de página
class _Doc(SimpleDocTemplate):
    def __init__(self, buf, encabezado: str, pie: str):
        super().__init__(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.3 * cm, bottomMargin=2 * cm,
                         title=encabezado, author="Aplicación de verificación y validación de métodos")
        self.encabezado, self.pie = encabezado, pie


class _Lienzo:
    """Numeración «página x de y» en dos pasadas."""

    @staticmethod
    def fabrica(doc: _Doc):
        from reportlab.pdfgen import canvas

        class Lienzo(canvas.Canvas):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self._paginas = []

            def showPage(self):
                self._paginas.append(dict(self.__dict__))
                self._startPage()

            def save(self):
                total = len(self._paginas)
                for estado in self._paginas:
                    self.__dict__.update(estado)
                    self._marco(total)
                    super().showPage()
                super().save()

            def _marco(self, total):
                w, h = A4
                self.setFont("DV", 7.5)
                self.setFillColor(GRIS)
                self.drawString(2 * cm, h - 1.4 * cm, doc.encabezado)
                self.drawRightString(w - 2 * cm, h - 1.4 * cm, doc.pie)
                self.setStrokeColor(LINEA)
                self.setLineWidth(0.5)
                self.line(2 * cm, h - 1.55 * cm, w - 2 * cm, h - 1.55 * cm)
                self.line(2 * cm, 1.45 * cm, w - 2 * cm, 1.45 * cm)
                self.drawString(2 * cm, 1.05 * cm, "Documento generado por el motor determinista; los datos originales se conservan sin modificación.")
                self.drawRightString(w - 2 * cm, 1.05 * cm, f"Página {self._pageNumber} de {total}")
        return Lienzo


# ------------------------------------------------------------------ secciones
TECNICA_FUNDAMENTO = [("Faltantes", ["faltantes"]), ("Mandel", ["mandel"]), ("Cochran", ["cochran"]), ("Grubbs", ["grubbs"]),
                      ("Shapiro", ["shapiro_wilk"]), ("Anderson", ["anderson_darling"]), ("Lilliefors", ["lilliefors"]),
                      ("Sesgo (t", ["sesgo_t"]), ("Sesgo (solo", ["sesgo_t"]), ("Sesgo (Wilcoxon", ["sesgo_wilcoxon"]),
                      ("Repetibilidad", ["repetibilidad"]), ("Precisión intermedia", ["precision_intermedia", "levene"]),
                      ("Reproducibilidad", ["reproducibilidad"])]
NOMBRE_ETAPA = {"limpieza": "Limpieza de datos y estructura", "atipicos": "Valores atípicos y consistencia",
                "normalidad": "Normalidad", "desempeno": "Desempeño y evaluación frente a criterios"}


def fundamentos_usados(resultado: dict) -> list[str]:
    usados = []
    for r in resultado["resultados"]:
        if r["estado"] != "APLICABLE":
            continue
        for prefijo, claves in TECNICA_FUNDAMENTO:
            if r["tecnica"].startswith(prefijo):
                usados += [c for c in claves if c not in usados]
    if "criterios" not in usados:
        usados.append("criterios")
    return usados


def _control(meta, cfg, control) -> list:
    filas = [["Campo", "Valor"],
             ["Estudio", f"{meta['estudio']} · {meta['nombre_estudio']}"],
             ["Versión del diseño / del análisis", f"v{meta['version_diseno']} / v{meta['version_analisis']}"
              + (f" (deriva de v{cfg.get('padre')}: {cfg.get('motivo_cambio')})" if cfg.get("padre") else "")],
             ["Fecha de emisión", control.get("fecha", "")],
             ["Ejecución del análisis", f"{meta['ejecutado_en']} · motor {meta['motor']} · Python {meta['python']}, SciPy {meta['scipy']}, pandas {meta['pandas']}"],
             ["Edición normativa", f"implementada {meta['edicion_normativa_implementada']}; configurada {meta['edicion_configurada']}"],
             ["Huella del resultado (SHA-256)", meta["huella_resultado"]]]
    t = tabla(filas, [5 * cm, ANCHO - 5 * cm])
    firmas = []
    for rol, nombre in (("Elaboró", control.get("elaborado_por")), ("Revisó", control.get("revisado_por")),
                        ("Autorizó", control.get("autorizado_por"))):
        firmas.append([Spacer(1, 22), Paragraph("_" * 28, E["firma"]),
                       Paragraph(f"<b>{rol}</b><br/>{esc(nombre) or 'pendiente'}", E["firma"])])
    f = Table([firmas], colWidths=[ANCHO / 3] * 3)
    f.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM")]))
    return [t, Spacer(1, 10), f]


def _estudio(e: Estudio) -> list:
    out = [P("2. Información del estudio", "h1")]
    filas = [["Campo", "Valor"], ["Tipo declarado", e.tipo], ["Método", f"{e.metodo} {e.version_metodo}".strip()],
             ["Uso previsto", e.uso_previsto], ["Documento de referencia", e.documento_referencia], ["Responsable", e.responsable],
             ["Magnitudes", "; ".join(f"{m.nombre} ({m.unidad})" for m in e.magnitudes)],
             ["Puntos de evaluación", "; ".join(f"{p.id}: {fmt(p.valor_nominal)} {p.unidad}" for p in e.puntos)],
             ["Equipo evaluado (IBC)", "; ".join(f"{r.codigo} {r.nombre} {r.marca} {r.modelo} {r.serie}".strip() + (f" — {r.descripcion}" if r.descripcion else "") for r in e.ibcs) or "—"],
             ["Patrones", "; ".join(f"{r.codigo} {r.nombre}" + (f" (cert. {r.certificado})" if r.certificado else "") for r in e.patrones) or "—"],
             ["Técnicos", "; ".join(f"{r.codigo} {r.nombre}" for r in e.tecnicos) or "—"],
             ["Factores del diseño", "; ".join(f"{f.nombre}: {', '.join(f.niveles) or 'catálogo'}" for f in e.factores) or "—"],
             ["Mediciones planificadas", str(len(e.plan))]]
    if e.derivado_de:
        filas.append(["Derivado de", e.derivado_de])
    out.append(tabla(filas, [5 * cm, ANCHO - 5 * cm]))
    return out


def _resumen_resultado(r: dict) -> list:
    est = r.get("estadistico") or {}
    crit = {k: v for k, v in (r.get("criticos") or {}).items() if k != "origen"}
    e = r.get("estimacion") or {}
    filas = [["Elemento", "Valor"], ["Estado de aplicabilidad", r["estado"]], ["Origen de la regla", r.get("origen_regla") or "—"]]
    if r.get("referencia"):
        filas.append(["Referencia", r["referencia"]])
    if r.get("formula"):
        filas.append(["Fórmula", r["formula"]])
    if r.get("hipotesis"):
        h = r["hipotesis"]
        filas.append(["Hipótesis", f"H0: {h.get('H0', '—')} · H1: {h.get('H1', '—')}" + (f" · α={fmt(h.get('alfa'))}" if h.get("alfa") else "")])
    if est.get("valor") is not None:
        filas.append(["Estadístico", f"{est.get('simbolo')} = {fmt(est.get('valor'))}" + (f"; gl = {fmt(r['gl'], 4)}" if isinstance(r.get("gl"), (int, float)) else "")])
    if r.get("p_valor") is not None:
        filas.append(["Valor p", fmt_p(r["p_valor"])])
    if crit:
        filas.append(["Valores críticos", "; ".join(f"{k}: {fmt(v)}" for k, v in crit.items()) + f" ({r['criticos'].get('origen', '')})"])
    if e.get("valor") is not None and r["etapa"] == "desempeno":
        filas.append(["Estimación", f"{e['nombre']} = {fmt(e['valor'])} {e.get('unidad') or ''}"
                      + (f"; IC {r['ic'][0] and fmt(r['ic'][0])} a {fmt(r['ic'][1])}" if r.get("ic") and r["ic"][0] is not None else "")])
    if r.get("decision_inferencial"):
        filas.append(["Decisión inferencial", r["decision_inferencial"]])
    if r.get("decision_metrologica"):
        req = r.get("requisito") or {}
        filas.append(["Decisión metrológica", r["decision_metrologica"] + (f" — criterio {req.get('criterio')} ({req.get('fuente')})" if req else "")])
    if r.get("motivos"):
        filas.append(["Motivos", " ".join(r["motivos"])])
    if r.get("limitaciones"):
        filas.append(["Limitaciones", " ".join(r["limitaciones"])])
    return [tabla(filas, [4 * cm, ANCHO - 4 * cm])]


def _tabla_intermedia(r: dict) -> Table | None:
    filas = r.get("tabla") or []
    if not filas or len(filas) > 40 or r["etapa"] == "normalidad":
        return None
    claves = [k for k in filas[0] if k not in ("ids",)]
    datos = [claves] + [[fmt(f.get(k)) if isinstance(f.get(k), float) else ("—" if f.get(k) is None else str(f.get(k)))
                         for k in claves] for f in filas]
    return tabla(datos, [ANCHO / len(claves)] * len(claves))


def _valor_corto(r: dict) -> str:
    e, est = r.get("estimacion") or {}, r.get("estadistico") or {}
    if r["etapa"] == "desempeno" and e.get("valor") is not None:
        return f"{e['nombre']} = {fmt(e['valor'])}"
    if est.get("valor") is not None:
        return f"{est['simbolo']} = {fmt(est['valor'])}" + (f"; p = {fmt_p(r['p_valor'])}" if r.get("p_valor") is not None else "")
    if r["etapa"] == "limpieza" and e.get("valor") is not None:
        return f"{fmt(e['valor'], 3)} {e.get('unidad', '')}"
    return "—"


def _detallar(r: dict) -> bool:
    """Bloque detallado: todo salvo Grubbs por celda (que queda en la tabla resumen)."""
    return not r["tecnica"].startswith("Grubbs (réplicas)")


def generar_informe(resultado: dict, config: dict, estudio: Estudio, comentarios: list[dict], historial: list[dict],
                    bitacora: list[dict], control: dict) -> bytes:
    meta = resultado["meta"]
    final = resultado["conclusion_final"]
    tipo = final.get("tipo") or estudio.tipo
    buf = io.BytesIO()
    doc = _Doc(buf, f"Informe técnico de {tipo.lower()} · {meta['estudio']}", f"Análisis v{meta['version_analisis']}")
    figs = graficos.generar(resultado)
    coment = {}
    for c in comentarios:
        coment.setdefault(c["etapa"], []).append(c)
    h = []

    # Portada y control
    h += [P(f"Informe técnico de {tipo.lower()} del método", "titulo"),
          P(f"{estudio.nombre} — {resultado['objeto']['nombre']} ({resultado['objeto']['unidad']})", "subtitulo")]
    h += _control(meta, config, control)
    h += [Spacer(1, 12), caja(final["texto"] + (" " + " ".join(final["avisos"]) if final["avisos"] else ""),
                              f"Conclusión consolidada: {final['estado']}")]

    # 1. Objeto
    h += [P("1. Objeto y alcance", "h1"),
          P(f"Este informe documenta la {tipo.lower()} de «{estudio.metodo or estudio.nombre}» para el objeto de análisis "
            f"{resultado['objeto']['descripcion']}. Se evalúan las características configuradas por el laboratorio con "
            f"el marco {final['marco']}. Las decisiones metrológicas solo se emiten frente a criterios aprobados con fuente y "
            "regla de decisión; los demás resultados se informan como calculados sin evaluación."),
          P(f"Ruta metodológica: declarada «{resultado['ruta']['declarada']}», sugerida por el estado del método "
            f"«{resultado['ruta']['sugerida'] or 'no determinable'}» (Eurachem, 2016, §4.2). " + " ".join(resultado["ruta"]["avisos"]))]
    h += _estudio(estudio)

    # 3. Datos y trazabilidad
    est = next((r for r in resultado["resultados"] if r["tecnica"] == "Faltantes respecto al plan"), None)
    filas = [["Elemento", "Valor"], ["Conjunto preparado", meta.get("preparacion_id", "—")],
             ["Carga / archivo original", f"{meta.get('carga_id', '—')} · {meta.get('archivo_original', '—')}"],
             ["SHA-256 del archivo original", meta.get("sha256_original", "—")],
             ["Huella del diseño", meta.get("huella_diseno", "—")], ["Conjunto aprobado por", meta.get("conjunto_aprobado_por", "—")]]
    if est:
        filas += [["Resultados esperados / válidos", f"{est['estimacion']['esperadas']} / {est['n']}"],
                  ["Faltantes", f"{est['estimacion']['faltantes']} ({fmt(est['estimacion']['valor'], 3)} %) — sin imputación"]]
    filas.append(["Exclusiones en esta versión", str(len(resultado["excluidas"]))])
    h += [P("3. Datos y trazabilidad", "h1"), tabla(filas, [5 * cm, ANCHO - 5 * cm])]

    # 4. Marco teórico
    h += [CondPageBreak(6 * cm), P("4. Marco teórico y justificación de la ruta metodológica", "h1"),
          P("Las técnicas descritas son exclusivamente las que el motor aplicó en este análisis. Cada una se eligió por una regla "
            "explícita de la matriz de reglas (anexo B) según el tipo de estudio, el tamaño de las celdas y el resultado de la etapa previa.")]
    for clave in fundamentos_usados(resultado):
        f = FUNDAMENTOS[clave]
        citas = "; ".join(CITAS[k] for k in f["refs"])
        h += [KeepTogether([P(f["titulo"], "h2"), P(f["texto"]), P(f"Fuentes: ({citas}).", "nota")])]
    h += [P("Árbol de decisiones del análisis", "h2")]
    arbol = [["#", "Pregunta", "Respuesta", "Evidencia", "Regla"]] + \
        [[str(i + 1), n["pregunta"], n["respuesta"], n["evidencia"], n["regla"]] for i, n in enumerate(resultado["arbol"])]
    h.append(tabla(arbol, [0.7 * cm, 5.3 * cm, 2.2 * cm, 7.2 * cm, 1.6 * cm]))

    # 5. Resultados por etapa
    h += [PageBreak(), P("5. Desarrollo, resultados y trazabilidad por etapa", "h1")]
    for n_etapa, etapa in enumerate(("limpieza", "atipicos", "normalidad", "desempeno"), start=1):
        h += [CondPageBreak(5 * cm), P(f"5.{n_etapa} {NOMBRE_ETAPA[etapa]}", "h2"),
              caja(resultado["conclusiones"].get(etapa, ""), "Conclusión técnica preliminar (automática)")]
        del_etapa = [x for x in resultado["resultados"] if x["etapa"] == etapa]
        h.append(Spacer(1, 4))
        h.append(tabla([["Técnica", "Agrupación", "Estado", "Resultado", "Decisión / motivo"]] +
                       [[x["tecnica"], x["agrupacion"], x["estado"], _valor_corto(x),
                         (x.get("decision_metrologica") or x.get("decision_inferencial") or "") if x["estado"] == "APLICABLE"
                         else " ".join(x.get("motivos") or [])] for x in del_etapa],
                       [3.4 * cm, 3.6 * cm, 2.4 * cm, 3 * cm, ANCHO - 12.4 * cm]))
        for r in del_etapa:
            if r["estado"] != "APLICABLE" or not _detallar(r):
                continue
            bloque = [P(f"{r['tecnica']} — {r['agrupacion']}", "h3")]
            if r.get("texto"):
                bloque.append(P(r["texto"]))
            bloque += _resumen_resultado(r)
            h.append(KeepTogether(bloque[:2]))
            h += bloque[2:]
            ti = _tabla_intermedia(r)
            if ti is not None:
                h += [Spacer(1, 3), ti]
            for clave in r.get("graficos", []):
                if clave in figs:
                    h += [Spacer(1, 4), imagen(figs.pop(clave), 8.5 if clave.startswith("qq") else 16)]
            h.append(Spacer(1, 6))
        h.append(P("Retroalimentación del revisor", "h3"))
        if coment.get(etapa):
            h.append(tabla([["Fecha", "Usuario", "Comentario"]] + [[c["fecha"], c["usuario"], c["texto"]] for c in coment[etapa]],
                           [3.4 * cm, 3 * cm, ANCHO - 6.4 * cm]))
        else:
            h.append(P("Sin comentarios registrados para esta etapa.", "nota"))

    # 6. Evaluación frente a criterios
    h += [CondPageBreak(6 * cm), P("6. Consolidado por característica", "h1")]
    filas = [["Característica", "Configuración", "Ejecución", "Decisión", "Referencia"]]
    for f in resultado["caracteristicas"]:
        if f["estado_configurado"] in ("PENDIENTE", "NO_SOLICITADA") and not f["niveles"]:
            continue
        filas.append([f["caracteristica"], f["estado_configurado"], f["ejecucion"], f["decision"], f["referencia"]])
    h.append(tabla(filas, [4 * cm, 2.6 * cm, 2.8 * cm, 3 * cm, ANCHO - 12.4 * cm]))
    crits = config.get("criterios", [])
    if crits:
        h += [P("Criterios aplicados", "h2"),
              tabla([["Id", "Característica", "Parámetro", "Requisito", "Regla", "Fuente", "Aprobado"]] +
                    [[c["id"], c["caracteristica"], c["parametro"], f"{c['operador']} {fmt(c['limite'])} {c['unidad']}",
                      c["regla_decision"] or "—", c["fuente"] or "—", "sí" if c["aprobado"] else "no"] for c in crits])]
    else:
        h.append(P("No se configuraron criterios: los resultados se informan como CALCULADO_SIN_EVALUACION.", "nota"))

    # 7. Conclusiones finales
    h += [P("7. Conclusiones técnicas finales", "h1"), caja(resultado["conclusiones"]["conclusion_final"], final["estado"])]
    if coment.get("conclusiones"):
        h += [P("Observaciones del revisor sobre las conclusiones", "h3"),
              tabla([["Fecha", "Usuario", "Comentario"]] + [[c["fecha"], c["usuario"], c["texto"]] for c in coment["conclusiones"]],
                    [3.4 * cm, 3 * cm, ANCHO - 6.4 * cm])]
    h.append(P("La significación estadística no se interpreta como conformidad, ni la no significación como equivalencia. "
               "Las características no implementadas o sin criterio aprobado impiden declarar la conformidad global.", "nota"))

    # 8. Limitaciones
    lims = sorted({l for r in resultado["resultados"] for l in r.get("limitaciones", [])})
    h += [P("8. Limitaciones", "h1")] + ([P("• " + l) for l in lims] or [P("Sin limitaciones registradas.")])

    # 9. Historial y bitácora
    h += [CondPageBreak(5 * cm), P("9. Historial de versiones y bitácora de auditoría", "h1")]
    if historial:
        h.append(tabla([["Versión", "Padre", "Motivo", "Cambios", "Estado final"]] +
                       [[f"v{v['version']}", f"v{v['padre']}" if v.get("padre") else "—", v.get("motivo_cambio") or "—",
                         "; ".join(c["campo"] for c in v.get("cambios", [])) or "—", v.get("estado_final") or "sin ejecutar"]
                        for v in historial], [1.6 * cm, 1.4 * cm, 6 * cm, 4.5 * cm, ANCHO - 13.5 * cm]))
    if bitacora:
        h += [Spacer(1, 6), tabla([["Fecha", "Usuario", "Acción", "Detalle"]] +
                                  [[b["fecha"], b["usuario"], b["accion"], str(b.get("detalle") or "")[:160]] for b in bitacora[-60:]],
                                  [3.4 * cm, 2.6 * cm, 3.4 * cm, ANCHO - 9.4 * cm])]

    # Referencias
    usadas = sorted({k for c in fundamentos_usados(resultado) for k in FUNDAMENTOS[c]["refs"]}
                    | {"iso5725_1", "iso5725_2", "eurachem", "vim", "iso17025", "scipy"}, key=lambda k: REFERENCIAS[k])
    if tipo.lower().startswith("verif"):
        usadas += [k for k in ("ema_cenam", "sae") if k not in usadas]
    h += [PageBreak(), P("Referencias", "h1")] + [Paragraph(esc(REFERENCIAS[k]), E["ref"]) for k in sorted(usadas, key=lambda k: REFERENCIAS[k])]

    # Anexos
    h += [PageBreak(), P("Anexo A. Datos analizados", "h1"),
          P("Valores tal como se analizaron (sin redondeo adicional). Las exclusiones se listan aparte.", "nota")]
    datos = resultado["datos"]
    h.append(tabla([["Medición", "Nivel", "Celda", "Valor"]] + [[d["medicion_id"], d["punto"], d["celda"], repr(d["valor"])] for d in datos],
                   [2.5 * cm, 6 * cm, 5 * cm, ANCHO - 13.5 * cm]))
    if resultado["excluidas"]:
        h += [P("Mediciones excluidas", "h2"),
              tabla([["Medición", "Celda", "Valor", "Motivo"]] + [[x["medicion_id"], x["celda"], repr(x["valor"]), x["motivo"]]
                                                                  for x in resultado["excluidas"]])]
    h += [P("Anexo B. Matriz de reglas del motor", "h1"),
          tabla([["Regla", "Descripción", "Origen", "Referencia"]] +
                [[r["codigo"], r["descripcion"], r["origen"], r["referencia"]] for r in resultado["reglas"]],
                [1.5 * cm, 9 * cm, 2.6 * cm, ANCHO - 13.1 * cm])]
    doc.build(h, canvasmaker=_Lienzo.fabrica(doc))
    return buf.getvalue()
