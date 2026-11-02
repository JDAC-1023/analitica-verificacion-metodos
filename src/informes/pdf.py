"""Informe técnico en PDF (ReportLab) — diseño 2.

Estructura pensada para dos lectores: un resumen en lenguaje sencillo al
inicio (para cualquier persona) y el detalle técnico completo después (para
el revisor). Se construye solo con lo guardado: resultado del motor,
configuración, diseño aprobado, reporte de limpieza, comentarios, historial y
bitácora; no recalcula nada.
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
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether, NextPageTemplate,
                                PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

from src.modelos.estudio import Estudio
from src.motor import flujo, graficos
from src.motor.multi import partes, resumen_por_objeto
from src.motor.lenguaje import DECISION, GLOBAL, en_palabras, explicar, hallazgos, que_hace
from src.motor.plantillas import fmt, fmt_p
from src.motor.referencias import CITAS, FUNDAMENTOS, REFERENCIAS
from src.motor.tablas_contexto import QUE_SE_COMPARA, SIGNIFICADO, cruce, medias_por_factor, resumen_fuentes


# ------------------------------------------------------------------ tipografía y color
_FUENTES = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
for nombre, archivo in (("DV", "DejaVuSans.ttf"), ("DV-B", "DejaVuSans-Bold.ttf"), ("DV-I", "DejaVuSans-Oblique.ttf"),
                        ("DV-BI", "DejaVuSans-BoldOblique.ttf"), ("DVM", "DejaVuSansMono.ttf")):
    if nombre not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont(nombre, str(_FUENTES / archivo)))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

C = {
    "primario": colors.HexColor("#3f3a78"), "primario_2": colors.HexColor("#6d5bd0"), "suave": colors.HexColor("#efedf9"),
    "tinta": colors.HexColor("#1d1d1b"), "gris": colors.HexColor("#5b5a55"), "linea": colors.HexColor("#d9d7d0"),
    "fondo": colors.HexColor("#f6f5f2"), "blanco": colors.white,
    "verde": colors.HexColor("#1f7a3a"), "verde_f": colors.HexColor("#e6f4ea"),
    "rojo": colors.HexColor("#b3261e"), "rojo_f": colors.HexColor("#fbe9e7"),
    "ambar": colors.HexColor("#9a6700"), "ambar_f": colors.HexColor("#fff4d6"),
    "neutro": colors.HexColor("#5b5a55"), "neutro_f": colors.HexColor("#eeede9"),
}
TONO = {"green": ("verde", "verde_f"), "red": ("rojo", "rojo_f"), "orange": ("ambar", "ambar_f"), "gray": ("neutro", "neutro_f"),
        "blue": ("primario", "suave")}


def _e(nombre, **kw):
    base = dict(fontName="DV", fontSize=8.8, leading=12.6, textColor=C["tinta"])
    base.update(kw)
    return ParagraphStyle(nombre, **base)


E = {
    "p": _e("p", alignment=TA_JUSTIFY, spaceAfter=5),
    "pl": _e("pl", spaceAfter=4),
    "nota": _e("nota", fontName="DV-I", fontSize=7.6, leading=10.4, textColor=C["gris"], spaceAfter=4),
    "h2": _e("h2", fontName="DV-B", fontSize=11, leading=15, textColor=C["primario"], spaceBefore=12, spaceAfter=5),
    "h3": _e("h3", fontName="DV-B", fontSize=9.2, leading=12.5, spaceBefore=8, spaceAfter=3),
    "celda": _e("celda", fontSize=7.4, leading=9.6),
    "celda_b": _e("celda_b", fontName="DV-B", fontSize=7.4, leading=9.6, textColor=C["primario"]),
    "celda_c": _e("celda_c", fontSize=7.4, leading=9.6, alignment=TA_CENTER),
    "ref": _e("ref", fontSize=7.9, leading=11, leftIndent=14, firstLineIndent=-14, spaceAfter=4),
    "caja": _e("caja", fontSize=8.7, leading=12.4, alignment=TA_JUSTIFY),
    "caja_t": _e("caja_t", fontName="DV-B", fontSize=9, leading=12.4, textColor=C["primario"]),
    "firma": _e("firma", fontSize=8, leading=10.5, alignment=TA_CENTER),
    "seccion_n": _e("seccion_n", fontName="DV-B", fontSize=13, leading=16, textColor=C["blanco"], alignment=TA_CENTER),
    "seccion_t": _e("seccion_t", fontName="DV-B", fontSize=13.5, leading=17, textColor=C["primario"]),
    "seccion_s": _e("seccion_s", fontSize=8.2, leading=11, textColor=C["gris"]),
    "kpi_v": _e("kpi_v", fontName="DV-B", fontSize=12.5, leading=15),
    "kpi_t": _e("kpi_t", fontSize=7.4, leading=9.6, textColor=C["gris"]),
    "veredicto": _e("veredicto", fontName="DV-B", fontSize=17, leading=21, alignment=TA_LEFT),
}
ANCHO = A4[0] - 4 * cm


def esc(t) -> str:
    t = "" if t is None else str(t)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)


def P(texto, estilo="p"):
    return Paragraph(esc(texto), E[estilo])


def pastilla(texto: str, tono: str, ancho: float = 2.9 * cm) -> Table:
    fg, bg = TONO.get(tono, TONO["gray"])
    t = Table([[Paragraph(f"<b>{esc(texto)}</b>", _e("pil", fontSize=7.2, leading=9, textColor=C[fg], alignment=TA_CENTER))]],
              colWidths=[ancho])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C[bg]), ("ROUNDEDCORNERS", [6, 6, 6, 6]),
                           ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return t


def tabla(filas: list[list], anchos=None, cabecera=True, cebra=True, estilos_extra=None) -> Table:
    datos = []
    for i, fila in enumerate(filas):
        datos.append([Paragraph(esc(c), E["celda_b" if cabecera and i == 0 else "celda"]) if isinstance(c, (str, int, float)) else c
                      for c in fila])
    t = Table(datos, colWidths=anchos, repeatRows=1 if cabecera else 0, hAlign="LEFT")
    estilo = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2),
              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
              ("LINEBELOW", (0, -1), (-1, -1), 0.6, C["linea"])]
    if cabecera:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), C["suave"]), ("LINEBELOW", (0, 0), (-1, 0), 1, C["primario_2"])]
    if cebra:
        for i in range(1 if cabecera else 0, len(datos)):
            if (i % 2 == 0) == cabecera:
                estilo.append(("BACKGROUND", (0, i), (-1, i), C["fondo"]))
    t.setStyle(TableStyle(estilo + (estilos_extra or [])))
    return t


def caja(texto: str, titulo: str = "", tono: str = "blue") -> Table:
    fg, bg = TONO.get(tono, TONO["blue"])
    contenido = []
    if titulo:
        contenido.append(Paragraph(f"<b>{esc(titulo)}</b>", _e("ct", fontName="DV-B", fontSize=8.8, leading=12, textColor=C[fg])))
    contenido.append(Paragraph(esc(texto), E["caja"]))
    t = Table([[contenido]], colWidths=[ANCHO])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), C[bg]), ("LINEBEFORE", (0, 0), (0, -1), 3, C[fg]),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return t


def seccion(numero: str, titulo: str, subtitulo: str = "") -> list:
    celda_t = [Paragraph(esc(titulo), E["seccion_t"])] + ([Paragraph(esc(subtitulo), E["seccion_s"])] if subtitulo else [])
    t = Table([[Paragraph(numero, E["seccion_n"]), celda_t]], colWidths=[1.1 * cm, ANCHO - 1.1 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), C["primario"]), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("LEFTPADDING", (1, 0), (1, 0), 10), ("TOPPADDING", (0, 0), (-1, -1), 6),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LINEBELOW", (1, 0), (1, 0), 1, C["primario_2"])]))
    return [Spacer(1, 4), t, Spacer(1, 8)]


def imagen(png: bytes, ancho_cm: float) -> Image:
    img = Image(io.BytesIO(png))
    escala = ancho_cm * cm / img.imageWidth
    img.drawWidth, img.drawHeight = img.imageWidth * escala, img.imageHeight * escala
    return img


def kpis(items: list[tuple[str, str, str]]) -> Table:
    """Tarjetas: (valor, etiqueta, tono)."""
    celdas = []
    for valor, etiqueta, tono in items:
        fg, bg = TONO.get(tono, TONO["blue"])
        celdas.append([Paragraph(esc(valor), _e("kv", fontName="DV-B", fontSize=12.5, leading=15, textColor=C[fg])),
                       Paragraph(esc(etiqueta), E["kpi_t"])])
    ancho = ANCHO / len(items)
    t = Table([celdas], colWidths=[ancho] * len(items))
    estilo = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
              ("LEFTPADDING", (0, 0), (-1, -1), 9)]
    for i, (_, _, tono) in enumerate(items):
        estilo += [("BACKGROUND", (i, 0), (i, 0), C[TONO.get(tono, TONO["blue"])[1]]),
                   ("LINEBEFORE", (i, 0), (i, 0), 3, C[TONO.get(tono, TONO["blue"])[0]]),
                   ("LINEAFTER", (i, 0), (i, 0), 3, C["blanco"])]
    t.setStyle(TableStyle(estilo))
    return t


# ------------------------------------------------------------------ páginas
class _Doc(BaseDocTemplate):
    def __init__(self, buf, datos_portada: dict, encabezado: str, pie: str):
        super().__init__(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.2 * cm, bottomMargin=2 * cm,
                         title=encabezado, author=datos_portada.get("elaborado_por") or "")
        self.portada, self.encabezado, self.pie = datos_portada, encabezado, pie
        w, h = A4
        marco_portada = Frame(2 * cm, 2 * cm, w - 4 * cm, h - 12.3 * cm, id="portada")
        marco = Frame(2 * cm, 2 * cm, w - 4 * cm, h - 4.2 * cm, id="normal")
        self.addPageTemplates([PageTemplate("portada", [marco_portada], onPage=self._dibujar_portada),
                               PageTemplate("normal", [marco], onPage=self._dibujar_marco)])

    def _dibujar_portada(self, cv, doc):
        w, h = A4
        d = self.portada
        cv.saveState()
        cv.setFillColor(C["primario"])
        cv.rect(0, h - 9.6 * cm, w, 9.6 * cm, stroke=0, fill=1)
        cv.setFillColor(C["primario_2"])
        cv.rect(0, h - 9.6 * cm, w, 0.25 * cm, stroke=0, fill=1)
        cv.setFillColor(colors.HexColor("#c9c3f2"))
        cv.setFont("DV-B", 8)
        cv.drawString(2 * cm, h - 2.0 * cm, d["kicker"].upper())
        cv.setFillColor(C["blanco"])
        cv.setFont("DV-B", 22)
        y = h - 3.3 * cm
        for linea in _partir(d["titulo"], 38):
            cv.drawString(2 * cm, y, linea)
            y -= 0.95 * cm
        cv.setFont("DV", 11)
        for linea in _partir(d["subtitulo"], 70):
            cv.drawString(2 * cm, y - 0.1 * cm, linea)
            y -= 0.55 * cm
        fg, bg = TONO.get(d["tono"], TONO["gray"])
        cv.setFillColor(C[bg])
        cv.roundRect(2 * cm, h - 8.6 * cm, 9.5 * cm, 1.25 * cm, 8, stroke=0, fill=1)
        cv.setFillColor(C[fg])
        cv.setFont("DV", 7.5)
        cv.drawString(2.5 * cm, h - 7.85 * cm, "CONCLUSIÓN CONSOLIDADA")
        cv.setFont("DV-B", 12.5)
        cv.drawString(2.5 * cm, h - 8.35 * cm, d["veredicto"])
        cv.setFillColor(colors.HexColor("#c9c3f2"))
        cv.setFont("DV", 8)
        cv.drawRightString(w - 2 * cm, h - 7.85 * cm, d["linea_1"])
        cv.drawRightString(w - 2 * cm, h - 8.35 * cm, d["linea_2"])
        cv.restoreState()
        self._pie(cv)

    def _dibujar_marco(self, cv, doc):
        w, h = A4
        cv.saveState()
        cv.setFillColor(C["primario"])
        cv.rect(0, h - 0.35 * cm, w, 0.35 * cm, stroke=0, fill=1)
        cv.setFont("DV", 7.5)
        cv.setFillColor(C["gris"])
        cv.drawString(2 * cm, h - 1.25 * cm, self.encabezado)
        cv.drawRightString(w - 2 * cm, h - 1.25 * cm, self.pie)
        cv.setStrokeColor(C["linea"])
        cv.setLineWidth(0.5)
        cv.line(2 * cm, h - 1.45 * cm, w - 2 * cm, h - 1.45 * cm)
        cv.restoreState()
        self._pie(cv)

    def _pie(self, cv):
        w, _ = A4
        cv.saveState()
        cv.setStrokeColor(C["linea"])
        cv.line(2 * cm, 1.45 * cm, w - 2 * cm, 1.45 * cm)
        cv.setFont("DV", 7)
        cv.setFillColor(C["gris"])
        cv.drawString(2 * cm, 1.05 * cm, "Motor determinista basado en reglas · los datos originales se conservan sin modificación")
        cv.restoreState()


def _partir(texto: str, n: int) -> list[str]:
    palabras, lineas, actual = texto.split(), [], ""
    for p in palabras:
        if len(actual) + len(p) + 1 > n and actual:
            lineas.append(actual)
            actual = p
        else:
            actual = f"{actual} {p}".strip()
    return lineas + ([actual] if actual else [])


def _lienzo_numerado():
    """Lienzo que escribe «Página x de y» al final, cuando ya se conoce el total."""
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
                self.setFont("DV", 7)
                self.setFillColor(C["gris"])
                self.drawRightString(A4[0] - 2 * cm, 1.05 * cm, f"Página {self._pageNumber} de {total}")
                super().showPage()
            super().save()
    return Lienzo


# ------------------------------------------------------------------ bloques de contenido
FUND = [("Faltantes", ["faltantes"]), ("Mandel", ["mandel"]), ("Cochran", ["cochran"]), ("Grubbs", ["grubbs"]),
        ("Shapiro", ["shapiro_wilk"]), ("Anderson", ["anderson_darling"]), ("Lilliefors", ["lilliefors"]),
        ("Sesgo (t", ["sesgo_t"]), ("Sesgo (solo", ["sesgo_t"]), ("Sesgo (Wilcoxon", ["sesgo_wilcoxon"]),
        ("Repetibilidad", ["repetibilidad"]), ("Reproducibilidad intralaboratorio", ["precision_intermedia", "levene"]), ("Fuentes de variación", ["fuentes_variacion", "posthoc"]), ("Homocedasticidad", ["homocedasticidad"]),
        ("Reproducibilidad", ["reproducibilidad"])]
NOMBRE_ETAPA = {"limpieza": "Limpieza y estructura", "atipicos": "Datos raros (atípicos)", "normalidad": "Forma de los datos (normalidad)",
                "homocedasticidad": "Igualdad de varianzas (homocedasticidad)", "desempeno": "Desempeño del método"}


def fundamentos_usados(resultado: dict) -> list[str]:
    usados = []
    for r in resultado["resultados"]:
        if r["estado"] != "APLICABLE":
            continue
        for prefijo, claves in FUND:
            if r["tecnica"].startswith(prefijo):
                usados += [c for c in claves if c not in usados]
    return usados + (["criterios"] if "criterios" not in usados else [])


def _fundamentos_todos(subs: list[dict]) -> list[str]:
    usados = []
    for x in subs:
        usados += [c for c in fundamentos_usados(x) if c not in usados]
    return usados


def _configs(config: dict, subs: list[dict]) -> list[dict]:
    """Configuración propia de cada resultado evaluado (criterios), en el mismo orden que los resultados."""
    objetos = {o["id"]: o for o in config.get("objetos", [])}
    return [objetos.get(x["objeto"]["id"], config) for x in subs]


def _pruebas_en_palabras(resultado: dict) -> Table:
    """Una fila por técnica y estado: ¿se aplicó?, en cuántos grupos y por qué."""
    grupos = {}
    for r in resultado["resultados"]:
        clave = (r["tecnica"].split(" (")[0] if r["tecnica"].startswith(("Sesgo", "Precisión", "Repetibilidad", "Reproducibilidad"))
                 else r["tecnica"], r["estado"])
        grupos.setdefault(clave, []).append(r)
    filas = [["Prueba", "¿Se aplicó?", "Qué hace", "Qué pasó / por qué no"]]
    extra = []
    for i, ((tec, _), rs) in enumerate(grupos.items(), start=1):
        ex = explicar(rs[0])
        texto = ex["explicacion"] if rs[0]["estado"] != "APLICABLE" else f"Se aplicó en {len(rs)} grupo(s). Ver resultados en la sección 4."
        if rs[0]["estado"] != "APLICABLE" and ex["que_hacer"]:
            texto += f" Qué haría falta: {ex['que_hacer']}"
        filas.append([tec, pastilla(ex["estado"], ex["color"], 2.4 * cm), que_hace(rs[0]["tecnica"]), texto])
    return tabla(filas, [3.1 * cm, 2.6 * cm, 4.6 * cm, ANCHO - 10.3 * cm])


def _tabla_desempeno(resultado: dict, caracteristica: str) -> list:
    rs = [r for r in resultado["resultados"] if r["etapa"] == "desempeno" and r["caracteristica"] == caracteristica]
    if not rs:
        return []
    u = resultado["objeto"]["unidad"]
    aplic = [r for r in rs if r["estado"] == "APLICABLE"]
    if not aplic:
        ex = explicar(rs[0])
        return [caja(ex["explicacion"] + (f" {ex['que_hacer']}" if ex["que_hacer"] else ""), f"{rs[0]['tecnica']}: {ex['estado']}", "gray")]
    filas = [["Punto", "Método", "Estimación", "IC 95 %", "gl", "p", "Decisión"]]
    for r in aplic:
        e = r["estimacion"]
        d = DECISION.get(r.get("decision_metrologica") or "", ("—", "", "gray", ""))
        filas.append([r["agrupacion"].replace("nivel ", "").split(" · ")[0], r["tecnica"].split("(")[-1].rstrip(")"),
                      f"{fmt(e['valor'])} {u}",
                      f"{fmt(r['ic'][0])} a {fmt(r['ic'][1])}" if r.get("ic") and r["ic"][0] is not None else "—",
                      fmt(r["gl"], 3) if isinstance(r.get("gl"), (int, float)) else "—",
                      fmt_p(r["p_valor"]) if r.get("p_valor") is not None else "—", pastilla(d[0], d[2], 2.5 * cm)])
    return [tabla(filas, [2.2 * cm, 2.7 * cm, 2.6 * cm, 3 * cm, 1.2 * cm, 1.6 * cm, ANCHO - 13.3 * cm])]


def _limpieza(rep: dict) -> list:
    h = []
    c = rep["conteos"]
    h.append(kpis([(str(c["recibidos"]), "filas recibidas", "blue"), (str(c["incluidos_en_preparado"]), "pasan al análisis", "green"),
                   (str(c["pendientes"]), "pendientes de corregir", "orange" if c["pendientes"] else "gray"),
                   (str(c["excluidos"]), "excluidas con motivo", "red" if c["excluidos"] else "gray")]))
    h += [Spacer(1, 8), P("Paso a paso", "h3"), tabla([["Paso", "Qué se hizo"]] + [[a, b] for a, b in rep["pasos"]], [3.2 * cm, ANCHO - 3.2 * cm])]
    h += [P("Reglas de calidad aplicadas a cada fila", "h3"),
          P("Cada regla revisa algo concreto. «Si falla» indica qué se hace con la fila; ninguna regla cambia valores.", "nota")]
    filas = [["Regla", "Qué revisa", "Si falla", "Resultado"]]
    for r in rep["reglas"]:
        filas.append([f"{r['codigo']} · {r['nombre']}", r["que_revisa"], r["si_falla"],
                      pastilla(r["resultado"], "green" if r["hallazgos"] == 0 else "orange", 2.6 * cm)])
    h.append(tabla(filas, [4.2 * cm, 6.6 * cm, 2.6 * cm, ANCHO - 13.4 * cm]))
    h += [P("Transformaciones (solo cambian la forma de escribir un valor, nunca el valor)", "h3"),
          tabla([["Código", "Qué hace", "Ejemplo", "Autorizada", "Veces"]] +
                [[t["codigo"], t["que_hace"], t["ejemplo"], "Sí" if t["autorizada"] else "No", str(t["veces"])] for t in rep["transformaciones"]],
                [1.4 * cm, 7.4 * cm, 3.6 * cm, 1.9 * cm, ANCHO - 14.3 * cm])]
    if rep["exclusiones"]:
        h += [P("Registros excluidos", "h3"), tabla([["Registro", "Origen", "Motivo"]] +
                                                   [[x["registro_id"], x["origen"], x["motivo"]] for x in rep["exclusiones"]])]
    if rep.get("motor"):
        m = rep["motor"]
        h += [P("En el análisis estadístico", "h3"),
              P(f"Para «{m['objeto']}» se esperaban {m['esperadas']} resultados según el plan y hay {m['validas']} válidos "
                f"({fmt(m['pct'], 3)} % faltantes). Exclusiones adicionales en esta versión del análisis: {len(m['exclusiones_analisis'])}.")]
    h += [P("Lo que la limpieza nunca hace", "h3")] + [P("•  " + x, "pl") for x in rep["nunca"]]
    h += [P("Herramientas usadas", "h3"), tabla([["Herramienta", "Para qué"]] + [list(x) for x in rep["herramientas"]], [6 * cm, ANCHO - 6 * cm])]
    return h


# ------------------------------------------------------------------ informe completo
TONO_PASO = {"ok": ("Bien", "green"), "alerta": ("Atención", "orange"), "falla": ("No cumple", "red"), "info": ("Info", "gray")}


def _paso_a_paso(resultado: dict) -> list:
    filas = [["#", "Paso", "Qué se encontró", "Por lo tanto…"]]
    for i, p in enumerate(flujo.pasos(resultado), start=1):
        etiqueta, tono = TONO_PASO[p["estado"]]
        filas.append([str(i), [Paragraph(f"<b>{esc(p['paso'])}</b>", E["celda"]), Spacer(1, 2), pastilla(etiqueta, tono, 2.2 * cm)],
                      p["texto"], p["siguiente"] or "—"])
    return [P("Paso a paso del motor (flujo de decisión)", "h3"),
            P("Cada paso decide el siguiente: primero los datos atípicos, luego la normalidad, luego la igualdad de varianzas, y con eso "
              "se elige la prueba estadística; al final se compara cada parámetro con su límite.", "nota"),
            tabla(filas, [0.7 * cm, 3.3 * cm, 7.6 * cm, ANCHO - 11.6 * cm])]


def _implicaciones(resultado: dict) -> list:
    imps = flujo.implicaciones(resultado)
    if not imps:
        return []
    return [CondPageBreak(5 * cm), P("Qué implica cada parámetro que no cumple y qué hacer", "h3"),
            tabla([["Parámetro", "Qué implica para el método", "Qué hacer"]] + [[i["caracteristica"], i["que_implica"], i["que_hacer"]] for i in imps],
                  [3.2 * cm, 8.4 * cm, ANCHO - 11.6 * cm])]


def _donde(resultado: dict) -> list:
    filas = [["Punto", "Condición", "Comparación", "Diferencia", "p", "Prueba", "Origen probable"]]
    u = resultado["objeto"]["unidad"]
    for r in resultado["resultados"]:
        if r.get("caracteristica") != "fuentes_variacion" or r["estado"] != "APLICABLE":
            continue
        for x in r["estimacion"].get("donde", []):
            filas.append([r["agrupacion"].replace("nivel ", "").split(" · ")[0], x["factor"], x["comparacion"], f"{fmt(x['diferencia'])} {u}",
                          fmt_p(x["p"]), x["metodo"], r["estimacion"].get("causas", {}).get(x["factor"], "")])
    if len(filas) == 1:
        return []
    return [Spacer(1, 4), P("Dónde están las diferencias y por qué se originan (pruebas post hoc)", "h3"),
            tabla(filas[:41], [1.6 * cm, 1.8 * cm, 2.6 * cm, 2.2 * cm, 1.6 * cm, 2.2 * cm, ANCHO - 12 * cm])]


def generar_informe(resultado: dict, config: dict, estudio: Estudio, comentarios: list[dict], historial: list[dict],
                    bitacora: list[dict], control: dict, limpieza: dict | None = None) -> bytes:
    meta = resultado["meta"]
    final = resultado["conclusion_final"]
    tipo = (final.get("tipo") or estudio.tipo or "estudio").lower()
    veredicto, tono_final = GLOBAL.get(final["estado"], (final["estado"], "gray"))
    obj = resultado["objeto"]
    subs = partes(resultado)
    multi = len(subs) > 1
    total = resultado
    buf = io.BytesIO()
    doc = _Doc(buf, {"kicker": f"Informe técnico de {tipo}", "titulo": estudio.nombre,
                     "subtitulo": f"{estudio.metodo or ''} · {'resultados evaluados' if multi else 'resultado evaluado'}: {obj['nombre']} ({obj['unidad']})".strip(" ·"),
                     "veredicto": veredicto, "tono": tono_final, "elaborado_por": control.get("elaborado_por"),
                     "linea_1": f"{meta['estudio']} · diseño v{meta['version_diseno']} · análisis v{meta['version_analisis']}",
                     "linea_2": f"Emitido {control.get('fecha', '')}"},
               f"{estudio.nombre} · informe técnico de {tipo}", f"{meta['estudio']} · análisis v{meta['version_analisis']}")
    coment = {}
    for c in comentarios:
        coment.setdefault(c["etapa"], []).append(c)
    h = [NextPageTemplate("normal")]

    # ---------- portada: control y firmas
    filas = [["Dato", "Valor"], ["Estudio", f"{meta['estudio']} · {estudio.nombre}"], ["Tipo", estudio.tipo],
             ["Método", f"{estudio.metodo} {('v' + estudio.version_metodo) if estudio.version_metodo else ''}".strip()],
             ["Equipo evaluado", "; ".join(f"{r.codigo} {r.nombre} {r.marca} {r.modelo}".strip() for r in estudio.ibcs) or "—"],
             ["Versión del análisis", f"v{meta['version_analisis']}" + (f" (deriva de v{config.get('padre')}: {config.get('motivo_cambio')})" if config.get("padre") else "")],
             ["Fecha de emisión", control.get("fecha", "")], ["Ejecutado", f"{meta['ejecutado_en'][:16].replace('T', ' ')} por {meta.get('ejecutado_por', '—')}"],
             ["Norma implementada", f"{meta['edicion_normativa_implementada']} · Eurachem (2016)"],
             ["Huella del resultado", meta["huella_resultado"][:32] + "…"]]
    h += [Spacer(1, 2), tabla(filas, [4.4 * cm, ANCHO - 4.4 * cm]), Spacer(1, 26)]
    firmas = []
    for rol, nombre in (("Elaboró", control.get("elaborado_por")), ("Revisó", control.get("revisado_por")),
                        ("Autorizó", control.get("autorizado_por"))):
        firmas.append([Spacer(1, 26), Paragraph("_" * 26, E["firma"]), Paragraph(f"<b>{rol}</b><br/>{esc(nombre) or 'pendiente'}", E["firma"])])
    f = Table([firmas], colWidths=[ANCHO / 3] * 3)
    f.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "BOTTOM"), ("BACKGROUND", (0, 0), (-1, -1), C["fondo"]),
                           ("LINEAFTER", (0, 0), (1, 0), 3, C["blanco"]), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    h += [f, PageBreak()]

    # ---------- 1. resumen para todos
    h += seccion("1", "Resumen en lenguaje sencillo", "Para cualquier lector: qué se evaluó, qué se encontró y qué significa")
    def _resumen(resultado: dict, cfg_r: dict) -> list:
        h = []
        v = flujo.veredicto(resultado)
        h.append(caja(v["texto"], v["titulo"], {"green": "green", "red": "red", "orange": "orange"}.get(v["color"], "gray")))
        h.append(Spacer(1, 6))
        h += _paso_a_paso(resultado)
        cab_m, filas_m = flujo.mapa(resultado)
        if filas_m:
            h += [CondPageBreak(5 * cm), P("Desempeño punto por punto (✔ cumple · ✘ no cumple · · sin criterio)", "h3"),
                  tabla([cab_m] + filas_m, [2 * cm] + [(ANCHO - 2 * cm) / (len(cab_m) - 1)] * (len(cab_m) - 1))]
        h += _implicaciones(resultado)
        h.append(Spacer(1, 6))
        caracts = [x for x in resultado["caracteristicas"] if x["estado_configurado"] in ("REQUERIDA", "SELECCIONADA")]
        if caracts:
            items = []
            for x in caracts[:4]:
                d = DECISION.get(x["decision"], (x["decision"].replace("_", " ").capitalize(), "", "gray", ""))
                items.append((d[0], x["caracteristica"], d[2]))
            h.append(kpis(items))
            h.append(Spacer(1, 6))
        limite = next((c["limite"] for c in cfg_r.get("criterios", []) if c["caracteristica"] == "sesgo" and c["aprobado"]
                       and c["parametro"] == "abs_sesgo" and c["limite"] is not None), None)
        for fig in (graficos.resumen_sesgo(resultado, limite), graficos.resumen_precision(resultado)):
            if fig:
                h += [imagen(fig, 16.5), Spacer(1, 4)]
        h += [CondPageBreak(7 * cm), P("Qué pruebas se aplicaron y cuáles no (y por qué)", "h3"), _pruebas_en_palabras(resultado)]

        return h

    if multi:
        h.append(P("Veredicto por resultado evaluado", "h3"))
        h.append(P("Cada resultado pasó por la secuencia completa de pruebas por separado (atípicos → normalidad → igualdad de "
                   "varianzas → prueba correspondiente → desempeño). El veredicto del análisis es el del resultado más desfavorable.", "nota"))
        h.append(tabla([["Resultado evaluado", "Veredicto", "No cumple en"]] +
                       [[f"{f['nombre']} ({f['unidad']})", pastilla(f["titulo"].replace("TU MÉTODO ", "").capitalize(),
                                                                       {"green": "green", "red": "red", "orange": "orange"}.get(f["color"], "gray"), 5.2 * cm),
                         ", ".join(f["no_cumple"]) or "—"] for f in resumen_por_objeto(total)],
                       [5 * cm, 5.6 * cm, ANCHO - 10.6 * cm]))
        h.append(Spacer(1, 8))
    for k_obj, (sub, cfg_r) in enumerate(zip(subs, _configs(config, subs)), start=1):
        if multi:
            h += [CondPageBreak(8 * cm), P(f"1.{k_obj}  Resultado evaluado: {sub['objeto']['nombre']} ({sub['objeto']['unidad']})", "h2")]
        h += _resumen(sub, cfg_r)
    h.append(P("Qué significa cada parámetro (significado metrológico)", "h3"))
    h.append(tabla([["Parámetro", "Qué es", "Qué significa para el método", "Referencia"]] + [list(x) for x in SIGNIFICADO],
                   [3.2 * cm, 4.6 * cm, 6.2 * cm, ANCHO - 14 * cm]))
    # ---------- 2. limpieza
    h += [CondPageBreak(10 * cm)] + seccion("2", "Reporte de limpieza de datos", "Qué se revisó, qué se encontró, qué se hizo y con qué herramienta")
    if limpieza:
        h += _limpieza(limpieza)
    else:
        h.append(P("No se adjuntó el reporte de limpieza del conjunto preparado.", "nota"))

    # ---------- 3. estudio y marco
    h += [CondPageBreak(10 * cm)] + seccion("3", "Estudio, ruta metodológica y fundamento", "Por qué se eligió cada prueba")
    filas = [["Campo", "Valor"], ["Uso previsto", estudio.uso_previsto or "—"],
             ["Puntos", "; ".join(f"{fmt(p.valor_nominal)} {p.unidad}" for p in estudio.puntos)],
             ["Técnicos", "; ".join(f"{r.codigo} {r.nombre}" for r in estudio.tecnicos) or "—"],
             ["Patrones", "; ".join(f"{r.codigo} {r.nombre}" for r in estudio.patrones) or "—"],
             ["Condiciones del diseño", "; ".join(f"{x.nombre}" for x in estudio.factores) or "—"],
             ["Mediciones planificadas", str(len(estudio.plan))],
             ["Ruta", f"Declarada: {subs[0]['ruta']['declarada']} · sugerida por el estado del método: {subs[0]['ruta']['sugerida'] or 'no determinable'} (Eurachem, 2016, §4.2)"],
             ["Resultados evaluados", "; ".join(f"{x['objeto']['nombre']} ({x['objeto']['unidad']}) · {x['objeto']['descripcion']}" for x in subs)]]
    h.append(tabla(filas, [4.4 * cm, ANCHO - 4.4 * cm]))
    for aviso in sorted({a for x in subs for a in x["ruta"]["avisos"]}):
        h += [Spacer(1, 4), caja(aviso, "Observación sobre la ruta", "orange")]
    h.append(P("Fundamento de las pruebas aplicadas", "h2"))
    for clave in _fundamentos_todos(subs):
        fu = FUNDAMENTOS[clave]
        h.append(KeepTogether([P(fu["titulo"], "h3"), P(fu["texto"]), P("Fuentes: (" + "; ".join(CITAS[k] for k in fu["refs"]) + ").", "nota")]))

    # ---------- 4. resultados por etapa
    h += [PageBreak()] + seccion("4", "Resultados por etapa", "Conclusión automática, explicación sencilla, detalle técnico y comentarios del revisor")
    def _etapas(resultado: dict, num: str, pref: str) -> list:
        h = []
        for n, etapa in enumerate(("limpieza", "atipicos", "normalidad", "homocedasticidad", "desempeno"), start=1):
            h += [CondPageBreak(6 * cm), P(f"{num}{n}  {NOMBRE_ETAPA[etapa]}" + (f" · {resultado['objeto']['nombre']}" if multi else ""), "h2" if not multi else "h3"),
                  caja(en_palabras(resultado["conclusiones"].get(etapa, "")), "Conclusión preliminar (automática)")]
            rs = [x for x in resultado["resultados"] if x["etapa"] == etapa]
            comp = QUE_SE_COMPARA.get(etapa)
            if comp:
                h += [P("Qué se compara en esta etapa", "h3"), tabla([["Elemento", "Qué se compara", "Con qué"]] + comp,
                                                                      [3.6 * cm, 6.8 * cm, ANCHO - 10.4 * cm]), Spacer(1, 4)]
            if etapa == "desempeno":
                for car, titulo in (("sesgo", "Sesgo"), ("repetibilidad", "Repetibilidad"), ("precision_intermedia", "Reproducibilidad intralaboratorio (precisión intermedia)"),
                                    ("reproducibilidad", "Reproducibilidad interlaboratorio")):
                    bloque = _tabla_desempeno(resultado, car)
                    if bloque:
                        h += [P(titulo, "h3"), P(que_hace(titulo), "nota")] + bloque
                        ej = next((r for r in rs if r["caracteristica"] == car and r["estado"] == "APLICABLE"), None)
                        if ej:
                            h.append(P("Ejemplo en palabras: " + explicar(ej)["explicacion"], "nota"))
                cab, filas_fv = resumen_fuentes(resultado)
                if filas_fv:
                    h += [CondPageBreak(7 * cm), P("Fuentes de variación: ¿depende el resultado del técnico o del patrón?", "h3"),
                          P(que_hace("Fuentes de variación") + " ✱ = influye significativamente (p < 0,05). El porcentaje es la parte de la "
                            "variación total que explica cada fuente; el resto es repetibilidad (residual).", "nota"),
                          tabla([cab] + filas_fv, [1.8 * cm] + [(ANCHO - 1.8 * cm - 3.6 * cm) / (len(cab) - 2)] * (len(cab) - 2) + [3.6 * cm])]
                    for nombre_f, (cab_f, filas_f) in medias_por_factor(resultado).items():
                        h += [Spacer(1, 4), KeepTogether([P(f"{resultado['objeto']['nombre']} media por {nombre_f.lower()} en cada punto ({resultado['objeto']['unidad']})", "h3"),
                              tabla([cab_f] + filas_f, [1.8 * cm] + [(ANCHO - 1.8 * cm) / (len(cab_f) - 1)] * (len(cab_f) - 1))])]
                    fig = graficos.interaccion_grid(resultado)
                    if fig:
                        h += [Spacer(1, 4), P("Medias por combinación en cada punto (líneas paralelas = sin interacción)", "h3"), imagen(fig, 16.5)]
                    h += _donde(resultado)
                    ej = cruce(resultado)
                    if ej:
                        h += [Spacer(1, 4), P(f"Ejemplo de tabla cruzada en {ej[0]} (media por combinación)", "h3"),
                              tabla([ej[1]] + ej[2], [4 * cm] + [(ANCHO - 4 * cm) / (len(ej[1]) - 1)] * (len(ej[1]) - 1))]
                lims = sorted({l for r in rs for l in r.get("limitaciones", [])})
                if lims:
                    h += [P("Advertencias técnicas", "h3")] + [P("•  " + l, "pl") for l in lims[:12]]
            elif etapa == "normalidad":
                aplic = [r for r in rs if r["estado"] == "APLICABLE"]
                if aplic:
                    h.append(tabla([["Punto", "Qué se revisó", "Estadístico", "p", "En palabras"]] +
                                   [[r["agrupacion"].replace("nivel ", "").split(" · ")[0],
                                     "unidades del sesgo" if "sesgo" in r["agrupacion"] else "residuos (precisión)",
                                     f"{r['estadistico']['simbolo']} = {fmt(r['estadistico']['valor'])}", fmt_p(r["p_valor"]),
                                     pastilla("No normal" if r["decision_inferencial"] == "Se rechaza H0" else "Compatible con normal",
                                              "orange" if r["decision_inferencial"] == "Se rechaza H0" else "green", 3.2 * cm)] for r in aplic],
                                   [2.2 * cm, 3.6 * cm, 3 * cm, 1.8 * cm, ANCHO - 10.6 * cm]))
                    for obj_n in ("sesgo", "precision"):
                        fig = graficos.qq_grid(resultado, obj_n)
                        if fig:
                            h += [Spacer(1, 6), imagen(fig, 16.5)]
                for r in [r for r in rs if r["estado"] != "APLICABLE"][:3]:
                    ex = explicar(r)
                    h.append(caja(ex["explicacion"], f"{r['tecnica']}: {ex['estado']}", "gray"))
            else:
                filas = [["Prueba", "Grupo", "Estado", "En palabras sencillas"]]
                for r in rs:
                    ex = explicar(r)
                    filas.append([r["tecnica"], r["agrupacion"], pastilla(ex["estado"], ex["color"], 2.4 * cm),
                                  ex["explicacion"] + (f" Qué haría falta: {ex['que_hacer']}" if ex["que_hacer"] else "")])
                h.append(tabla(filas, [3.2 * cm, 3.4 * cm, 2.6 * cm, ANCHO - 9.2 * cm]))
                if etapa == "limpieza":
                    fig = graficos.puntos_grid(resultado)
                    if fig:
                        h += [Spacer(1, 6), imagen(fig, 16.5)]
                for r in rs:
                    if r["estado"] == "APLICABLE" and r["tecnica"].startswith(("Cochran", "Grubbs (medias", "Mandel")):
                        h += [P(f"{r['tecnica']} — {r['agrupacion']}", "h3"), P(r.get("texto") or "")]
                        for g in r.get("graficos", []):
                            png = graficos.mandel(resultado, g.split(":")[1], g[7]) if g.startswith("mandel") else None
                            if png:
                                h.append(imagen(png, 15))
            h.append(P("Comentarios del revisor", "h3"))
            if coment.get(pref + etapa):
                h.append(tabla([["Fecha", "Usuario", "Comentario"]] + [[c["fecha"][:16].replace("T", " "), c["usuario"], c["texto"]] for c in coment[pref + etapa]],
                               [3 * cm, 3 * cm, ANCHO - 6 * cm]))
            else:
                h.append(P("Sin comentarios registrados en esta etapa.", "nota"))

        return h

    for k_obj, sub in enumerate(subs, start=1):
        if multi:
            h += [CondPageBreak(8 * cm), P(f"4.{k_obj}  Resultado evaluado: {sub['objeto']['nombre']} ({sub['objeto']['unidad']})", "h2")]
            h += _etapas(sub, f"4.{k_obj}.", f"{sub['objeto']['id']}:")
        else:
            h += _etapas(sub, "4.", "")

    # ---------- 5. consolidado y conclusiones
    h += [PageBreak()] + seccion("5", "Evaluación frente a criterios y conclusiones finales", "Cumplimiento consolidado según ISO 5725 y Eurachem")
    def _consolidado(resultado: dict, cfg_r: dict) -> list:
        h = []
        filas = [["Característica", "¿Se pidió?", "¿Se calculó?", "Decisión", "Referencia"]]
        for x in resultado["caracteristicas"]:
            if x["estado_configurado"] in ("PENDIENTE", "NO_SOLICITADA") and not x["niveles"]:
                continue
            d = DECISION.get(x["decision"], (x["decision"].replace("_", " ").capitalize(), "", "gray", ""))
            filas.append([x["caracteristica"], x["estado_configurado"].capitalize(), "Sí" if x["ejecucion"] == "APLICABLE" else x["ejecucion"].replace("_", " ").capitalize(),
                          pastilla(d[0], d[2], 2.7 * cm), x["referencia"]])
        h.append(tabla(filas, [4.2 * cm, 2.3 * cm, 2.6 * cm, 3.1 * cm, ANCHO - 12.2 * cm]))
        crits = cfg_r.get("criterios", [])
        h.append(P("Criterios de aceptación aplicados", "h3"))
        if crits:
            h.append(tabla([["Id", "Característica", "Requisito", "Regla", "Fuente", "Aprobado"]] +
                           [[c["id"], c["caracteristica"], f"{c['parametro']} {c['operador']} {fmt(c['limite'])} {c['unidad']}",
                             c["regla_decision"] or "—", c["fuente"] or "—", "Sí" if c["aprobado"] else "No"] for c in crits]))
        else:
            h.append(caja("El laboratorio no ha definido criterios de aceptación para este análisis. Por eso los resultados se presentan "
                          "como «calculados sin criterio»: no se declara cumplimiento ni incumplimiento.", "Sin criterios", "orange"))
        vf = flujo.veredicto(resultado)
        h += [Spacer(1, 8), caja(vf["texto"] + " " + resultado["conclusiones"]["conclusion_final"], (f"Conclusión técnica final · {resultado['objeto']['nombre']}: " if multi else "Conclusión técnica final: ") + vf["titulo"],
                                 {"green": "green", "red": "red", "orange": "orange"}.get(vf["color"], "gray"))]
        h += _implicaciones(resultado)
        return h

    for k_obj, (sub, cfg_r) in enumerate(zip(subs, _configs(config, subs)), start=1):
        if multi:
            h += [CondPageBreak(8 * cm), P(f"5.{k_obj}  Resultado evaluado: {sub['objeto']['nombre']} ({sub['objeto']['unidad']})", "h2")]
        h += _consolidado(sub, cfg_r)
    if multi:
        g_txt, g_tono = GLOBAL.get(total["conclusion_final"]["estado"], (total["conclusion_final"]["estado"], "gray"))
        h += [Spacer(1, 8), caja(total["conclusion_final"]["texto"], f"Conclusión del análisis completo: {g_txt}",
                                 {"green": "green", "red": "red", "orange": "orange"}.get(g_tono, "gray"))]
    obs_concl = [c for k_c, cs in coment.items() if k_c.split(":")[-1] == "conclusiones" for c in cs]
    if obs_concl:
        h += [P("Observaciones del revisor", "h3"), tabla([["Fecha", "Usuario", "Comentario"]] +
                                                          [[c["fecha"][:16].replace("T", " "), c["usuario"], (f"[{c['etapa'].split(':')[0]}] " if ":" in c["etapa"] else "") + c["texto"]] for c in obs_concl],
                                                          [3 * cm, 3 * cm, ANCHO - 6 * cm])]
    h.append(P("Una diferencia estadísticamente significativa no equivale a incumplir, ni una no significativa a cumplir: "
               "la decisión se toma solo frente al criterio aprobado.", "nota"))
    lims = sorted({(f"{x['objeto']['nombre']}: " if multi else "") + l for x in subs for r in x["resultados"] for l in r.get("limitaciones", [])})
    h.append(P("Limitaciones", "h2"))
    h += [P("•  " + l, "pl") for l in lims] or [P("Sin limitaciones registradas.")]

    # ---------- 6. trazabilidad
    h += [PageBreak()] + seccion("6", "Trazabilidad", "Versiones del análisis, bitácora de auditoría y árbol de decisiones")
    if historial:
        h.append(tabla([["Versión", "Padre", "Motivo", "Cambios", "Estado"]] +
                       [[f"v{v['version']}", f"v{v['padre']}" if v.get("padre") else "—", v.get("motivo_cambio") or "—",
                         "; ".join(c["campo"] for c in v.get("cambios", [])) or "—", GLOBAL.get(v.get("estado_final"), (v.get("estado_final") or "sin ejecutar",))[0]]
                        for v in historial], [1.6 * cm, 1.4 * cm, 6.2 * cm, 4 * cm, ANCHO - 13.2 * cm]))
    if bitacora:
        h += [P("Bitácora de auditoría", "h3"), tabla([["Fecha", "Usuario", "Acción", "Detalle"]] +
                                                     [[b["fecha"][:16].replace("T", " "), b["usuario"], b["accion"].replace("_", " "),
                                                       str(b.get("detalle") or "")[:140]] for b in bitacora[-50:]],
                                                     [2.8 * cm, 3 * cm, 3.4 * cm, ANCHO - 9.2 * cm])]
    for sub in subs:
        h += [P("Árbol de decisiones del motor" + (f" · {sub['objeto']['nombre']}" if multi else ""), "h3"),
              tabla([["#", "Pregunta", "Respuesta", "Evidencia", "Regla"]] +
                    [[str(i + 1), n["pregunta"], n["respuesta"], n["evidencia"], n["regla"]] for i, n in enumerate(sub["arbol"])],
                    [0.8 * cm, 5.4 * cm, 2.2 * cm, 7 * cm, ANCHO - 15.4 * cm])]

    # ---------- referencias y anexos
    usadas = sorted({k for c in _fundamentos_todos(subs) for k in FUNDAMENTOS[c]["refs"]}
                    | {"iso5725_1", "iso5725_2", "eurachem", "vim", "iso17025", "scipy"}
                    | ({"ema_cenam", "sae"} if tipo.startswith("verif") else set()), key=lambda k: REFERENCIAS[k])
    h += [PageBreak()] + seccion("R", "Referencias", "Formato APA 7")
    h += [Paragraph(esc(REFERENCIAS[k]), E["ref"]) for k in usadas]
    h += [PageBreak()] + seccion("A", "Anexo A · Datos analizados", "Valores tal como se analizaron, sin redondeo adicional")
    for sub in subs:
        if multi:
            h.append(P(f"Resultado evaluado: {sub['objeto']['nombre']} ({sub['objeto']['unidad']})", "h3"))
        h.append(tabla([["Medición", "Punto", "Grupo de condiciones", "Valor"]] +
                       [[d["medicion_id"], d["punto"], d["celda"], repr(d["valor"])] for d in sub["datos"]],
                       [2.4 * cm, 5.6 * cm, 5.6 * cm, ANCHO - 13.6 * cm]))
        if sub["excluidas"]:
            h += [P("Mediciones excluidas", "h3"), tabla([["Medición", "Grupo", "Valor", "Motivo"]] +
                                                        [[x["medicion_id"], x["celda"], repr(x["valor"]), x["motivo"]] for x in sub["excluidas"]])]
    h += [PageBreak()] + seccion("B", "Anexo B · Matriz de reglas del motor", "NORMA = exigido por la norma · COMPLEMENTARIA = buena práctica · CRITERIO_LAB = decisión del laboratorio")
    h.append(tabla([["Regla", "Descripción", "Origen", "Referencia"]] +
                   [[r["codigo"], r["descripcion"], r["origen"], r["referencia"]] for r in resultado["reglas"]],
                   [1.5 * cm, 9 * cm, 2.6 * cm, ANCHO - 13.1 * cm]))
    doc.build(h, canvasmaker=_lienzo_numerado())
    return buf.getvalue()


def generar_reporte_limpieza(rep: dict, estudio: Estudio, fecha: str, usuario: str) -> bytes:
    """PDF independiente con el reporte de limpieza de un conjunto preparado."""
    buf = io.BytesIO()
    doc = _Doc(buf, {"kicker": "Reporte de limpieza de datos", "titulo": estudio.nombre,
                     "subtitulo": f"Archivo: {rep['archivo']}", "veredicto": f"{rep['conteos']['incluidos_en_preparado']} de {rep['conteos']['recibidos']} filas pasan al análisis",
                     "tono": "green" if rep["conteos"]["pendientes"] == 0 else "orange", "elaborado_por": usuario,
                     "linea_1": f"{estudio.codigo} · {rep['preparacion_id']}", "linea_2": f"Emitido {fecha}"},
               f"{estudio.nombre} · reporte de limpieza", estudio.codigo)
    h = [NextPageTemplate("normal"), tabla([["Dato", "Valor"], ["Archivo original", rep["archivo"]], ["SHA-256", rep["sha256"]],
                                            ["Cargado", f"{rep['fecha_carga'][:16].replace('T', ' ')} por {rep['usuario_carga']}"],
                                            ["Conjunto preparado", rep["preparacion_id"]], ["Emitido por", usuario or "—"]],
                                           [4.4 * cm, ANCHO - 4.4 * cm]), PageBreak()]
    h += seccion("1", "Reporte de limpieza de datos", "Qué se revisó, qué se encontró, qué se hizo y con qué herramienta")
    h += _limpieza(rep)
    doc.build(h, canvasmaker=_lienzo_numerado())
    return buf.getvalue()
