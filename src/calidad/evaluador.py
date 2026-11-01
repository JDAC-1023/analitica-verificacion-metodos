"""Evaluación de calidad de los registros leídos (pasos 7 a 11 de la ingesta).

Función pura: con la misma lectura, el mismo diseño, las mismas
transformaciones autorizadas y las mismas exclusiones produce siempre el mismo
resultado. Por eso la preparación es reproducible.

Estados de un registro (precedencia de mayor a menor):
    excluido > pendiente > con_advertencia > normalizado > aceptado
El archivo rechazado se representa en `estado_archivo`.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any

from src.calidad.incidencias import Incidencia, crear
from src.calidad.reglas import ADVERTENCIA, EXCLUYE_REGISTRO, PENDIENTE
from src.ingesta.lector import texto_original
from src.modelos.estudio import Estudio
from src.plantillas.especificacion import (
    HOJA_MEDICIONES, HOJA_RESULTADOS, columnas_mediciones, columnas_resultados, filas_resultados_agrupados,
)

ESTADOS = ["aceptado", "normalizado", "con_advertencia", "pendiente", "excluido"]
INCLUIDOS = {"aceptado", "normalizado", "con_advertencia"}
NOMBRE_TIPO = {"decimal": "número", "entero": "número entero", "fecha": "fecha", "si_no": "Sí/No", "texto": "texto"}

_NUM_PUNTO = re.compile(r"^[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?$")
_NUM_COMA = re.compile(r"^[+-]?\d+,\d+$")
_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HORA = re.compile(r"^([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?$")


def _vacio(raw: Any) -> bool:
    return raw is None or (isinstance(raw, str) and raw.strip() == "")


def interpretar(raw: Any, tipo: str, autorizadas: set[str]) -> tuple[Any, list[str], bool]:
    """Devuelve (valor interpretado, transformaciones aplicadas, es_valido).

    Nunca redondea, nunca cambia el signo, nunca convierte unidades.
    """
    trans: list[str] = []
    if isinstance(raw, dict):  # fechas/horas leídas de Excel
        clave, texto = next(iter(raw.items()))
        if tipo == "fecha":
            return texto[:10], trans, True
        if tipo == "texto":
            return texto, trans, True
        return None, trans, False
    if isinstance(raw, str):
        texto = raw
        if texto != texto.strip():
            if "TR03" in autorizadas or tipo in ("decimal", "entero", "fecha"):
                # Para números y fechas, quitar espacios forma parte de leerlos (TR01).
                texto = texto.strip()
                trans.append("TR03" if "TR03" in autorizadas else "TR01")
            # sin TR03 el texto se conserva exactamente igual
    else:
        texto = None

    if tipo == "texto":
        if isinstance(raw, bool):
            return ("Sí" if raw else "No"), trans, True
        if isinstance(raw, int):
            return str(raw), trans, True
        if isinstance(raw, float):
            return repr(raw), trans, True
        return texto, trans, True

    if tipo == "decimal":
        if isinstance(raw, bool):
            return None, trans, False
        if isinstance(raw, (int, float)):
            return float(raw), trans, True
        if _NUM_PUNTO.match(texto or ""):
            if "TR01" not in autorizadas:
                return None, trans, False
            return float(texto), sorted(set(trans + ["TR01"])), True
        if _NUM_COMA.match(texto or ""):
            if "TR02" not in autorizadas:
                return None, trans, False
            return float(texto.replace(",", ".")), sorted(set(trans + ["TR02"])), True
        return None, trans, False

    if tipo == "entero":
        if isinstance(raw, bool):
            return None, trans, False
        if isinstance(raw, int):
            return raw, trans, True
        if isinstance(raw, float):
            return (int(raw), trans, True) if raw.is_integer() else (None, trans, False)
        if texto and re.fullmatch(r"[+-]?\d+", texto):
            if "TR01" not in autorizadas:
                return None, trans, False
            return int(texto), sorted(set(trans + ["TR01"])), True
        return None, trans, False

    if tipo == "fecha":
        if texto and _FECHA_ISO.match(texto):
            try:
                date.fromisoformat(texto)
            except ValueError:
                return None, trans, False
            if "TR01" not in autorizadas:
                return None, trans, False
            return texto, sorted(set(trans + ["TR01"])), True
        return None, trans, False

    if tipo == "si_no":
        if isinstance(raw, bool):
            return raw, trans, True
        normal = (texto or "").casefold()
        if normal in ("sí", "si"):
            return True, trans, True
        if normal == "no":
            return False, trans, True
        return None, trans, False
    return texto, trans, True


def _comparable(valor: Any) -> str:
    """Normaliza un valor del sistema para compararlo con el plan."""
    if valor is None:
        return ""
    if isinstance(valor, dict):
        return next(iter(valor.values()))[:10]
    if isinstance(valor, bool):
        return str(valor)
    if isinstance(valor, (int, float)):
        return repr(float(valor))
    texto = str(valor).strip()
    try:
        return repr(float(texto))
    except ValueError:
        return texto


def _esperado_sistema(e: Estudio, m, clave: str) -> Any:
    from src.plantillas.generador import _valor_sistema
    return _valor_sistema(e, m, clave)


def _estado(incidencias: list[Incidencia], transformaciones: list[dict]) -> tuple[str, str]:
    severidades = {i.severidad for i in incidencias}
    if EXCLUYE_REGISTRO in severidades:
        motivo = next(i for i in incidencias if i.severidad == EXCLUYE_REGISTRO)
        return "excluido", f"{motivo.regla}: {motivo.mensaje}"
    if PENDIENTE in severidades:
        return "pendiente", "; ".join(sorted({i.regla for i in incidencias if i.severidad == PENDIENTE}))
    if ADVERTENCIA in severidades:
        return "con_advertencia", "; ".join(sorted({i.regla for i in incidencias if i.severidad == ADVERTENCIA}))
    if transformaciones:
        return "normalizado", "; ".join(sorted({t["codigo"] for t in transformaciones}))
    return "aceptado", ""


def evaluar(lectura: dict, e: Estudio, autorizadas: list[str], exclusiones: list[dict] | None = None) -> dict:
    """Evalúa los registros de una carga ya leída (diccionario guardado)."""
    autorizadas_set = set(autorizadas)
    exclusiones = exclusiones or []
    excluir_manual = {x["registro_id"]: x for x in exclusiones}
    incidencias_archivo = [Incidencia(**i) for i in lectura.get("incidencias", [])]
    salida = {
        "estado_archivo": lectura.get("estado_archivo", "rechazado"),
        "registros": [], "registros_resultados": [], "incidencias": [i.to_dict() for i in incidencias_archivo],
        "transformaciones": [], "autorizadas": sorted(autorizadas_set), "exclusiones": exclusiones,
    }
    if salida["estado_archivo"] == "rechazado":
        n = len(lectura.get("filas_mediciones", []))
        salida["conteos"] = _conteos([], n, len(e.plan) if e else 0, 0, rechazado=True)
        return salida

    cols = {c.clave: c for c in columnas_mediciones(e)}
    pos = lectura.get("posiciones_mediciones", {})
    plan = {m.medicion_id: m for m in e.plan}
    tecnicos = {t.codigo: t.codigo for t in e.tecnicos}
    patrones = {p.codigo: p.codigo for p in e.patrones}
    filas = lectura.get("filas_mediciones", [])
    ids = Counter(texto_original(f["valores"].get("medicion_id")).strip() for f in filas)
    filas_por_id = defaultdict(list)
    for f in filas:
        filas_por_id[texto_original(f["valores"].get("medicion_id")).strip()].append(f["fila"])

    claves_datos = [c.clave for c in cols.values() if c.entidad in ("variable", "resultado")]

    for f in filas:
        fila, raw = f["fila"], f["valores"]
        rid = texto_original(raw.get("medicion_id")).strip()
        inc: list[Incidencia] = []
        trans: list[dict] = []
        valores: dict[str, Any] = {}
        base = dict(hoja=HOJA_MEDICIONES, fila=fila, registro_id=rid)

        def celda(clave):
            return f"{pos.get(clave, '?')}{fila}"

        if not rid:
            inc.append(crear("RC09", **base, celda=celda("medicion_id")))
        elif rid not in plan:
            inc.append(crear("RC08", **base, valor=rid, celda=celda("medicion_id")))
        else:
            m = plan[rid]
            if ids[rid] > 1:
                inc.append(crear("RC10", **base, valor=ids[rid], esperado=", ".join(map(str, filas_por_id[rid]))))
            # RC13: celdas del sistema modificadas
            for clave, col in cols.items():
                if col.origen != "sistema" or clave == "medicion_id":
                    continue
                esperado = _esperado_sistema(e, m, clave)
                if _comparable(raw.get(clave)) != _comparable(esperado):
                    inc.append(crear("RC13", **base, columna=col.etiqueta, celda=celda(clave),
                                     valor=texto_original(raw.get(clave)), esperado=texto_original(esperado)))
            # RC14: medición sin ningún dato
            if claves_datos and all(_vacio(raw.get(k)) for k in claves_datos):
                inc.append(crear("RC14", **base))
            else:
                for clave, col in cols.items():
                    if col.origen != "usuario":
                        continue
                    valor_raw = raw.get(clave)
                    if _vacio(valor_raw):
                        valores[clave] = None
                        if col.obligatoria:
                            inc.append(crear("RC15", **base, columna=col.etiqueta, celda=celda(clave)))
                        continue
                    valor, aplicadas, ok = interpretar(valor_raw, col.tipo, autorizadas_set)
                    if not ok:
                        pista = " Si usaste coma decimal, autoriza la transformación TR02 o corrige el archivo." \
                            if isinstance(valor_raw, str) and _NUM_COMA.match(valor_raw.strip()) else ""
                        i = crear("RC16", **base, columna=col.etiqueta, celda=celda(clave),
                                  valor=texto_original(valor_raw), esperado=NOMBRE_TIPO.get(col.tipo, col.tipo))
                        i.mensaje += pista
                        inc.append(i)
                        valores[clave] = None
                        continue
                    # Recursos reales (RC17) y TR04
                    if clave in ("tecnico_real", "patron_real"):
                        catalogo = tecnicos if clave == "tecnico_real" else patrones
                        if valor not in catalogo:
                            coincidencia = next((c for c in catalogo if c.casefold() == str(valor).casefold()), None)
                            if coincidencia and "TR04" in autorizadas_set:
                                valor = coincidencia
                                aplicadas = sorted(set(aplicadas + ["TR04"]))
                            else:
                                inc.append(crear("RC17", **base, columna=col.etiqueta, celda=celda(clave), valor=valor))
                    if clave == "hora_real" and valor and not _HORA.match(str(valor)):
                        inc.append(crear("RC19", **base, celda=celda(clave), valor=valor))
                    if col.entidad == "factor" and valor:
                        factor = next((x for x in e.factores if x.id == col.ref_id), None)
                        if factor and factor.niveles and valor not in factor.niveles:
                            inc.append(crear("RC16", **base, columna=col.etiqueta, celda=celda(clave),
                                             valor=valor, esperado=f"opción de «{factor.nombre}»"))
                    valores[clave] = valor
                    for codigo in aplicadas:
                        trans.append({"registro_id": rid, "hoja": HOJA_MEDICIONES, "fila": fila, "celda": celda(clave),
                                      "columna": col.etiqueta, "codigo": codigo,
                                      "valor_original": texto_original(valor_raw), "valor_resultante": texto_original(valor)})
                # RC18: cambios de recurso sin motivo (X03)
                motivo = valores.get("motivo_cambio")
                for real, previsto, nombre in (("tecnico_real", m.tecnico, "el técnico"), ("patron_real", m.patron, "el patrón")):
                    if valores.get(real) and previsto and valores[real] != previsto and not motivo:
                        inc.append(crear("RC18", **base, columna=nombre, valor=valores[real], esperado=previsto))

        if rid in excluir_manual and not any(i.severidad == EXCLUYE_REGISTRO for i in inc):
            x = excluir_manual[rid]
            estado, motivo_estado = "excluido", f"Exclusión manual por {x.get('usuario', '')}: {x['motivo']}"
        else:
            estado, motivo_estado = _estado(inc, trans)
        salida["registros"].append({
            "registro_id": rid, "hoja": HOJA_MEDICIONES, "fila": fila, "estado": estado, "motivo_estado": motivo_estado,
            "valores": valores, "originales": raw, "extras": f.get("extras", {}),
            "incidencias": [i.regla for i in inc],
        })
        salida["incidencias"].extend(i.to_dict() for i in inc)
        salida["transformaciones"].extend(trans)

    # RC11 / RC12
    recibidos_ids = {r["registro_id"] for r in salida["registros"]}
    ausentes = [mid for mid in plan if mid not in recibidos_ids]
    for mid in ausentes:
        salida["incidencias"].append(crear("RC11", hoja=HOJA_MEDICIONES, registro_id=mid).to_dict())
    con_id = sum(1 for f in filas if texto_original(f["valores"].get("medicion_id")).strip())
    if con_id != len(plan):
        salida["incidencias"].append(crear("RC12", hoja=HOJA_MEDICIONES, valor=con_id, esperado=len(plan)).to_dict())

    _evaluar_resultados(lectura, e, autorizadas_set, excluir_manual, salida)
    salida["conteos"] = _conteos(salida["registros"], len(filas), len(plan), len(ausentes))
    salida["conteos_resultados"] = _conteos(salida["registros_resultados"], len(lectura.get("filas_resultados", [])),
                                            len(filas_resultados_agrupados(e)), 0)
    salida["conteos"]["transformaciones"] = len(salida["transformaciones"])
    return salida


def _evaluar_resultados(lectura: dict, e: Estudio, autorizadas: set[str], excluir_manual: dict, salida: dict) -> None:
    previstos = {f["registro_id"]: f for f in filas_resultados_agrupados(e)}
    if not previstos:
        return
    pos = lectura.get("posiciones_resultados", {})
    cols = {c.clave: c for c in columnas_resultados()}
    filas = lectura.get("filas_resultados", [])
    ids = Counter(texto_original(f["valores"].get("registro_id")).strip() for f in filas)
    for f in filas:
        fila, raw = f["fila"], f["valores"]
        rid = texto_original(raw.get("registro_id")).strip()
        base = dict(hoja=HOJA_RESULTADOS, fila=fila, registro_id=rid)
        inc: list[Incidencia] = []
        trans: list[dict] = []
        valor = None

        def celda(clave):
            return f"{pos.get(clave, '?')}{fila}"

        if not rid:
            inc.append(crear("RC09", **base, celda=celda("registro_id")))
        elif rid not in previstos:
            inc.append(crear("RC08", **base, valor=rid, celda=celda("registro_id")))
        else:
            prev = previstos[rid]
            if ids[rid] > 1:
                inc.append(crear("RC10", **base, valor=ids[rid], esperado=""))
            for clave, col in cols.items():
                if col.origen == "sistema" and clave != "registro_id" and \
                        _comparable(raw.get(clave)) != _comparable(prev.get(clave, "")):
                    inc.append(crear("RC13", **base, columna=col.etiqueta, celda=celda(clave),
                                     valor=texto_original(raw.get(clave)), esperado=prev.get(clave, "")))
            if _vacio(raw.get("valor")):
                inc.append(crear("RC20", **base, columna=prev["resultado"]))
            else:
                valor, aplicadas, ok = interpretar(raw.get("valor"), "decimal", autorizadas)
                if not ok:
                    inc.append(crear("RC16", **base, columna="Valor", celda=celda("valor"),
                                     valor=texto_original(raw.get("valor")), esperado="número"))
                    valor = None
                for codigo in aplicadas:
                    trans.append({"registro_id": rid, "hoja": HOJA_RESULTADOS, "fila": fila, "celda": celda("valor"),
                                  "columna": "Valor", "codigo": codigo, "valor_original": texto_original(raw.get("valor")),
                                  "valor_resultante": texto_original(valor)})
        if rid in excluir_manual and not any(i.severidad == EXCLUYE_REGISTRO for i in inc):
            x = excluir_manual[rid]
            estado, motivo_estado = "excluido", f"Exclusión manual por {x.get('usuario', '')}: {x['motivo']}"
        else:
            estado, motivo_estado = _estado(inc, trans)
        obs = raw.get("observaciones")
        salida["registros_resultados"].append({
            "registro_id": rid, "hoja": HOJA_RESULTADOS, "fila": fila, "estado": estado, "motivo_estado": motivo_estado,
            "valores": {"valor": valor, "observaciones": None if _vacio(obs) else texto_original(obs)},
            "originales": raw, "incidencias": [i.regla for i in inc],
        })
        salida["incidencias"].extend(i.to_dict() for i in inc)
        salida["transformaciones"].extend(trans)


def _conteos(registros: list[dict], recibidos: int, planificados: int, ausentes: int, rechazado: bool = False) -> dict:
    estados = Counter(r["estado"] for r in registros)
    conteo = {
        "planificados": planificados,
        "recibidos": recibidos,
        "aceptados": estados.get("aceptado", 0),
        "normalizados": estados.get("normalizado", 0),
        "con_advertencia": estados.get("con_advertencia", 0),
        "pendientes": estados.get("pendiente", 0),
        "excluidos": estados.get("excluido", 0),
        "rechazados": recibidos if rechazado else 0,
        "planificados_ausentes": ausentes,
    }
    conteo["incluidos_en_preparado"] = conteo["aceptados"] + conteo["normalizados"] + conteo["con_advertencia"]
    suma = sum(conteo[k] for k in ("aceptados", "normalizados", "con_advertencia", "pendientes", "excluidos", "rechazados"))
    conteo["conciliado"] = suma == recibidos
    return conteo


def resumen_mensajes(evaluacion: dict) -> list[tuple[str, str]]:
    """Mensajes agregados para la interfaz: (nivel, texto)."""
    c = evaluacion["conteos"]
    salida: list[tuple[str, str]] = []
    if evaluacion["estado_archivo"] == "rechazado":
        return [("error", "El archivo fue rechazado. Revisa el motivo en la lista de incidencias; el original quedó guardado.")]
    reglas = Counter(i["regla"] for i in evaluacion["incidencias"])
    if reglas.get("RC10"):
        dup = len({i["registro_id"] for i in evaluacion["incidencias"] if i["regla"] == "RC10"})
        salida.append(("warning", f"Se identificaron {dup} mediciones duplicadas. Se conservaron los originales y se requiere revisar su correspondencia con las repeticiones previstas."))
    if c["pendientes"]:
        n = c["pendientes"]
        salida.append(("warning", f"{n} registro quedó pendiente de corrección y no se incorporó al conjunto preparado." if n == 1 else
                       f"{n} registros quedaron pendientes de corrección y no se incorporaron al conjunto preparado."))
    if c["excluidos"]:
        salida.append(("info", f"{c['excluidos']} registros se excluyeron del conjunto preparado con su motivo documentado."))
    if c["planificados_ausentes"]:
        salida.append(("warning", f"{c['planificados_ausentes']} mediciones planificadas no aparecen en el archivo."))
    if c.get("transformaciones"):
        salida.append(("info", f"Se aplicaron {c['transformaciones']} transformaciones autorizadas; cada una conserva su valor original."))
    if not salida:
        salida.append(("success", "Todos los registros recibidos superaron las reglas de calidad."))
    return salida
