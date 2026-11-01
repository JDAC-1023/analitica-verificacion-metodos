"""Construcción del conjunto de datos preparado para el motor estadístico.

Formato de salida SAL-1.0: un archivo ZIP con tablas CSV normalizadas (UTF-8
con BOM para que Excel muestre bien las tildes), un manifiesto JSON y una
copia en Excel de la vista de análisis.

Tablas (ver docs/09_salida_para_el_motor.md):
  observaciones_analisis.csv  vista desnormalizada: 1 fila = 1 dato experimental de una medición incluida
  mediciones.csv              contexto de cada medición incluida
  valores.csv                 datos experimentales (formato largo)
  niveles_factores.csv        condiciones y opciones de cada medición (formato largo)
  resultados_valores.csv      resultados de interés registrados directamente (formato largo)
  definiciones_variables.csv, definiciones_resultados.csv, criterios.csv, factores.csv, puntos.csv, recursos.csv
  registros_estado.csv        TODOS los registros recibidos con su estado (incluye pendientes y excluidos)
  incidencias.csv, transformaciones.csv, exclusiones.csv
  estudio_version.json        diseño aprobado completo
  manifiesto.json             identificación, conteos y huellas de cada archivo

Reproducibilidad: los CSV no contienen marcas de tiempo ni el identificador de
la preparación; con las mismas entradas sus bytes son idénticos.
"""

from __future__ import annotations

import io
import json
import zipfile

import pandas as pd

from src.auditoria.huella import sha256_bytes
from src.calidad.evaluador import INCLUIDOS
from src.ingesta.lector import texto_original
from src.modelos.estudio import Estudio
from src.planificacion.plan import condicion_de, grupo_comparable
from src.plantillas.especificacion import columnas_mediciones, filas_resultados_agrupados

FORMATO_SALIDA = "SAL-1.0"
FECHA_ZIP = (2026, 1, 1, 0, 0, 0)  # fecha fija dentro del ZIP: bytes reproducibles


def _csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, lineterminator="\n").encode("utf-8-sig")


def construir_tablas(evaluacion: dict, e: Estudio, carga: dict) -> dict[str, pd.DataFrame]:
    cols = {c.clave: c for c in columnas_mediciones(e)}
    plan = {m.medicion_id: m for m in e.plan}
    variables = {v.id: v for v in e.variables}
    resultados = {r.id: r for r in e.resultados}
    trans_por_celda: dict[tuple, list[str]] = {}
    for t in evaluacion["transformaciones"]:
        trans_por_celda.setdefault((t["hoja"], t["celda"]), []).append(t["codigo"])
    base = {"codigo_estudio": e.codigo, "version_diseno": e.version_diseno, "carga_id": carga["carga_id"]}

    filas_med, filas_val, filas_niv, filas_res = [], [], [], []
    for r in evaluacion["registros"]:
        if r["estado"] not in INCLUIDOS:
            continue
        m = plan[r["registro_id"]]
        p = e.punto(m.punto_id)
        mag = e.magnitud(p.magnitud_id)
        v = r["valores"]
        condicion = condicion_de(e, m)
        filas_med.append({
            **base, "medicion_id": m.medicion_id, "punto_id": m.punto_id, "magnitud_id": mag.id,
            "magnitud": mag.nombre, "valor_nominal": p.valor_nominal, "unidad_punto": p.unidad,
            "repeticion": m.repeticion, "grupo_comparable": grupo_comparable(e, m),
            "condicion": "|".join([condicion[0], condicion[1], condicion[2], condicion[3]] + [f"{k}={x}" for k, x in condicion[4]]),
            "tecnico_previsto": m.tecnico, "patron_previsto": m.patron, "equipo_previsto": m.equipo,
            "tecnico_real": v.get("tecnico_real"), "patron_real": v.get("patron_real"),
            "fecha_planificada": m.fecha_planificada, "franja_planificada": m.franja_planificada, "orden": m.orden,
            "fecha_real": v.get("fecha_real"), "hora_real": v.get("hora_real"),
            "motivo_cambio": v.get("motivo_cambio"), "observaciones": v.get("observaciones"),
            "estado_calidad": r["estado"], "hoja": r["hoja"], "fila_excel": r["fila"],
        })
        for f in e.factores:
            if f.vinculo_recurso != "ninguno":
                nivel = getattr(m, f.vinculo_recurso)
            elif f.rol == "solo_se_registra":
                nivel = v.get(f"factor:{f.id}")
            else:
                nivel = m.niveles.get(f.id)
            filas_niv.append({**base, "medicion_id": m.medicion_id, "factor_id": f.id, "factor": f.nombre,
                              "nivel": nivel, "unidad": f.unidad, "rol": f.rol, "vinculo_recurso": f.vinculo_recurso})
        for clave, col in cols.items():
            if col.entidad not in ("variable", "resultado"):
                continue
            valor = v.get(clave)
            letra_celda = f"{carga['lectura']['posiciones_mediciones'].get(clave, '?')}{r['fila']}"
            original = texto_original(r["originales"].get(clave))
            comun = {"valor_original": original,
                     "transformaciones": ";".join(sorted(trans_por_celda.get((r["hoja"], letra_celda), []))),
                     "hoja": r["hoja"], "fila_excel": r["fila"], "celda": letra_celda, "estado_calidad": r["estado"]}
            if col.entidad == "variable":
                var = variables[col.ref_id]
                numerico = isinstance(valor, (int, float)) and not isinstance(valor, bool)
                filas_val.append({**base, "medicion_id": m.medicion_id, "variable_id": var.id, "variable": var.nombre,
                                  "categoria": var.categoria, "tipo_dato": var.tipo_dato, "unidad": var.unidad,
                                  "valor_numerico": float(valor) if numerico else None,
                                  "valor_texto": None if numerico or valor is None else str(valor), **comun})
            elif valor is not None:
                res = resultados[col.ref_id]
                filas_res.append({**base, "resultado_id": res.id, "resultado": res.nombre, "ambito": res.ambito,
                                  "origen": res.origen, "registro_id": m.medicion_id, "grupo": m.medicion_id,
                                  "mediciones": m.medicion_id, "valor": float(valor), "unidad": res.unidad, **comun})
    previstos = {f["registro_id"]: f for f in filas_resultados_agrupados(e)}
    for r in evaluacion.get("registros_resultados", []):
        if r["estado"] not in INCLUIDOS or r["valores"].get("valor") is None:
            continue
        prev = previstos[r["registro_id"]]
        res = resultados[prev["resultado_id"]]
        letra_celda = f"{carga['lectura']['posiciones_resultados'].get('valor', '?')}{r['fila']}"
        filas_res.append({**base, "resultado_id": res.id, "resultado": res.nombre, "ambito": res.ambito, "origen": res.origen,
                          "registro_id": r["registro_id"], "grupo": prev["grupo"], "mediciones": prev["mediciones"],
                          "valor": float(r["valores"]["valor"]), "unidad": res.unidad,
                          "valor_original": texto_original(r["originales"].get("valor")),
                          "transformaciones": ";".join(sorted(trans_por_celda.get((r["hoja"], letra_celda), []))),
                          "hoja": r["hoja"], "fila_excel": r["fila"], "celda": letra_celda, "estado_calidad": r["estado"]})

    col_med = list(base) + ["medicion_id", "punto_id", "magnitud_id", "magnitud", "valor_nominal", "unidad_punto", "repeticion",
                            "grupo_comparable", "condicion", "tecnico_previsto", "patron_previsto", "equipo_previsto",
                            "tecnico_real", "patron_real", "fecha_planificada", "franja_planificada", "orden", "fecha_real",
                            "hora_real", "motivo_cambio", "observaciones", "estado_calidad", "hoja", "fila_excel"]
    col_val = list(base) + ["medicion_id", "variable_id", "variable", "categoria", "tipo_dato", "unidad", "valor_numerico",
                            "valor_texto", "valor_original", "transformaciones", "hoja", "fila_excel", "celda", "estado_calidad"]
    col_niv = list(base) + ["medicion_id", "factor_id", "factor", "nivel", "unidad", "rol", "vinculo_recurso"]
    col_res = list(base) + ["resultado_id", "resultado", "ambito", "origen", "registro_id", "grupo", "mediciones", "valor",
                            "unidad", "valor_original", "transformaciones", "hoja", "fila_excel", "celda", "estado_calidad"]
    mediciones = pd.DataFrame(filas_med, columns=col_med).sort_values("medicion_id", kind="stable")
    valores = pd.DataFrame(filas_val, columns=col_val).sort_values(["medicion_id", "variable_id"], kind="stable")
    niveles = pd.DataFrame(filas_niv, columns=col_niv).sort_values(["medicion_id", "factor_id"], kind="stable")
    res_val = pd.DataFrame(filas_res, columns=col_res).sort_values(["resultado_id", "registro_id"], kind="stable")

    # Vista de análisis: datos experimentales + contexto + condiciones en columnas «factor:<nombre>»
    contexto = mediciones.drop(columns=["estado_calidad", "hoja", "fila_excel"] + list(base))
    if len(niveles):
        anchos = niveles.pivot(index="medicion_id", columns="factor", values="nivel")
        anchos.columns = [f"factor:{c}" for c in anchos.columns]
        contexto = contexto.merge(anchos.reset_index(), on="medicion_id", how="left")
    analisis = valores.merge(contexto, on="medicion_id", how="left").sort_values(["medicion_id", "variable_id"], kind="stable")

    tablas = {
        "observaciones_analisis": analisis,
        "mediciones": mediciones,
        "valores": valores,
        "niveles_factores": niveles,
        "resultados_valores": res_val,
        "definiciones_variables": pd.DataFrame([vars(v) for v in e.variables],
                                               columns=["id", "nombre", "tipo_dato", "unidad", "obligatoria", "descripcion", "categoria"]),
        "definiciones_resultados": pd.DataFrame([{**vars(r), "dependencias": ";".join(r.dependencias)} for r in e.resultados],
                                                columns=["id", "nombre", "proposito", "referencia_proposito", "unidad", "origen",
                                                         "dependencias", "referencia_calculo", "ambito", "analizar", "tiene_criterio"]),
        "criterios": pd.DataFrame([vars(c) for c in e.criterios],
                                  columns=["id", "resultado_id", "descripcion", "fuente", "version_fuente", "operador",
                                           "valor", "unidad", "condiciones", "aprobado"]),
        "factores": pd.DataFrame([{**vars(f), "niveles": ";".join(f.niveles)} for f in e.factores],
                                 columns=["id", "nombre", "descripcion", "tipo_valor", "unidad", "niveles", "vinculo_recurso", "rol"]),
        "puntos": pd.DataFrame([{**vars(p), "magnitud": (e.magnitud(p.magnitud_id).nombre if e.magnitud(p.magnitud_id) else "")}
                                for p in e.puntos], columns=["id", "magnitud_id", "magnitud", "valor_nominal", "unidad"]),
        "recursos": pd.DataFrame([vars(r) for r in e.ibcs + e.tecnicos + e.patrones + e.equipos],
                                 columns=["codigo", "nombre", "tipo", "descripcion", "magnitud_id", "intervalo_min", "intervalo_max",
                                          "marca", "modelo", "serie", "resolucion", "certificado"]),
        "registros_estado": pd.DataFrame(
            [{**base, "hoja": r["hoja"], "fila_excel": r["fila"], "registro_id": r["registro_id"], "estado": r["estado"],
              "motivo_estado": r["motivo_estado"], "reglas": ";".join(r["incidencias"])}
             for r in evaluacion["registros"] + evaluacion.get("registros_resultados", [])],
            columns=list(base) + ["hoja", "fila_excel", "registro_id", "estado", "motivo_estado", "reglas"]),
        "incidencias": pd.DataFrame(evaluacion["incidencias"],
                                    columns=["regla", "severidad", "mensaje", "hoja", "fila", "columna", "celda",
                                             "registro_id", "valor", "esperado"]),
        "transformaciones": pd.DataFrame(evaluacion["transformaciones"],
                                         columns=["registro_id", "hoja", "fila", "celda", "columna", "codigo",
                                                  "valor_original", "valor_resultante"]),
        "exclusiones": pd.DataFrame(
            [{"registro_id": r["registro_id"], "hoja": r["hoja"], "fila_excel": r["fila"],
              "origen": "manual" if r["motivo_estado"].startswith("Exclusión manual") else "automático",
              "motivo": r["motivo_estado"]}
             for r in evaluacion["registros"] + evaluacion.get("registros_resultados", []) if r["estado"] == "excluido"],
            columns=["registro_id", "hoja", "fila_excel", "origen", "motivo"]),
    }
    if "fila" in tablas["incidencias"]:
        tablas["incidencias"]["fila"] = pd.array(tablas["incidencias"]["fila"], dtype="Int64")
    return tablas


def empaquetar(tablas: dict[str, pd.DataFrame], e: Estudio, manifiesto_base: dict) -> tuple[bytes, dict]:
    """Crea el ZIP del conjunto preparado. Devuelve (bytes, manifiesto)."""
    archivos: dict[str, bytes] = {f"{nombre}.csv": _csv(df) for nombre, df in tablas.items()}
    archivos["estudio_version.json"] = json.dumps(e.to_dict(), ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
    manifiesto = {
        **manifiesto_base,
        "formato_salida": FORMATO_SALIDA,
        "huellas_archivos": {nombre: sha256_bytes(contenido) for nombre, contenido in sorted(archivos.items())},
        "filas_por_tabla": {nombre: int(len(df)) for nombre, df in tablas.items()},
    }
    # Copia en Excel (útil para revisión o para Minitab). No forma parte de la huella reproducible.
    xlsx = io.BytesIO()
    with pd.ExcelWriter(xlsx, engine="openpyxl") as escritor:
        tablas["observaciones_analisis"].to_excel(escritor, sheet_name="observaciones_analisis", index=False)
        tablas["resultados_valores"].to_excel(escritor, sheet_name="resultados_valores", index=False)
        tablas["registros_estado"].to_excel(escritor, sheet_name="registros_estado", index=False)
    archivos["observaciones_analisis.xlsx"] = xlsx.getvalue()
    archivos["manifiesto.json"] = json.dumps(manifiesto, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")

    salida = io.BytesIO()
    with zipfile.ZipFile(salida, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for nombre in sorted(archivos):
            info = zipfile.ZipInfo(nombre, date_time=FECHA_ZIP)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, archivos[nombre])
    return salida.getvalue(), manifiesto


def informe_incidencias_xlsx(evaluacion: dict, carga: dict) -> bytes:
    """Informe descargable de incidencias, transformaciones y estados (paso 13)."""
    salida = io.BytesIO()
    resumen = pd.DataFrame([
        {"campo": "Carga", "valor": carga["carga_id"]}, {"campo": "Archivo", "valor": carga["nombre_archivo"]},
        {"campo": "SHA-256 del original", "valor": carga["sha256"]}, {"campo": "Fecha", "valor": carga["fecha"]},
        {"campo": "Usuario", "valor": carga["usuario"]}, {"campo": "Estado del archivo", "valor": evaluacion["estado_archivo"]},
        {"campo": "Transformaciones autorizadas", "valor": ", ".join(evaluacion["autorizadas"]) or "ninguna"},
    ] + [{"campo": f"Registros · {k}", "valor": v} for k, v in evaluacion["conteos"].items()])
    estados = pd.DataFrame([{"hoja": r["hoja"], "fila": r["fila"], "registro_id": r["registro_id"], "estado": r["estado"],
                             "motivo": r["motivo_estado"]} for r in evaluacion["registros"] + evaluacion.get("registros_resultados", [])],
                           columns=["hoja", "fila", "registro_id", "estado", "motivo"])
    with pd.ExcelWriter(salida, engine="openpyxl") as escritor:
        resumen.to_excel(escritor, sheet_name="Resumen", index=False)
        pd.DataFrame(evaluacion["incidencias"]).to_excel(escritor, sheet_name="Incidencias", index=False)
        pd.DataFrame(evaluacion["transformaciones"], columns=["registro_id", "hoja", "fila", "celda", "columna", "codigo",
                                                              "valor_original", "valor_resultante"]).to_excel(
            escritor, sheet_name="Transformaciones", index=False)
        estados.to_excel(escritor, sheet_name="Estados", index=False)
    return salida.getvalue()
