"""Construcción del conjunto de observaciones que analiza el motor.

Parte del conjunto preparado (formato SAL-1.0) y de la versión del diseño. No
modifica valores: solo selecciona el objeto del análisis, aplica la regla de
derivación aprobada (si la hay), asigna cada observación a su nivel (punto) y
celda, y aparta las exclusiones documentadas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from src.modelos.estudio import Estudio
from src.motor.configuracion import ConfiguracionAnalisis
from src.planificacion.plan import etiqueta_punto


class ErrorDatosMotor(Exception):
    pass


@dataclass
class Observaciones:
    df: pd.DataFrame                    # columnas: medicion_id, punto_id, punto, valor, celda, + campos de agrupación
    unidad: str
    nombre_objeto: str
    descripcion_objeto: str
    excluidas: pd.DataFrame
    esperadas: pd.DataFrame             # punto_id, celda, esperadas (según plan)
    trazas: list[str] = field(default_factory=list)


def _campo(mediciones: pd.DataFrame, niveles: pd.DataFrame, e: Estudio, campo: str) -> pd.Series:
    """Valor de un campo de agrupación por medición (técnico, patrón o condición)."""
    f = next((x for x in e.factores if x.id == campo), None)
    if f is not None and f.vinculo_recurso in ("tecnico", "patron", "equipo"):
        campo = f.vinculo_recurso
    if campo in ("tecnico", "patron", "equipo"):
        real = mediciones.get(f"{campo}_real")
        previsto = mediciones.get(f"{campo}_previsto")
        if real is not None:
            return real.where(real.notna() & (real.astype(str) != ""), previsto).fillna("—").astype(object).map(str)
        return previsto.fillna("—").astype(object).map(str)
    sub = niveles[niveles["factor_id"] == campo].set_index("medicion_id")["nivel"]
    return mediciones["medicion_id"].map(sub).fillna("—").astype(object).map(str)


def nombre_campo(e: Estudio, campo: str) -> str:
    if campo in ("tecnico", "patron", "equipo"):
        return {"tecnico": "Técnico", "patron": "Patrón", "equipo": "Equipo"}[campo]
    f = next((x for x in e.factores if x.id == campo), None)
    return f.nombre if f else campo


def campos_celda(cfg: ConfiguracionAnalisis) -> list[str]:
    if cfg.es_interlaboratorio and cfg.factor_laboratorio:
        return [cfg.factor_laboratorio]
    return list(cfg.factores_precision_intermedia)


def construir(tablas: dict, e: Estudio, cfg: ConfiguracionAnalisis) -> Observaciones:
    mediciones = tablas["mediciones"].copy()
    niveles = tablas["niveles_factores"]
    trazas = []
    if cfg.objeto_tipo == "variable":
        var = next((v for v in e.variables if v.id == cfg.objeto_id), None)
        if var is None:
            raise ErrorDatosMotor(f"El dato {cfg.objeto_id} no existe en la versión del diseño.")
        if var.tipo_dato not in ("decimal", "entero"):
            raise ErrorDatosMotor(f"«{var.nombre}» no es numérico; el motor analiza variables cuantitativas continuas.")
        v = tablas["valores"]
        v = v[v["variable_id"] == cfg.objeto_id][["medicion_id", "valor_numerico"]].rename(columns={"valor_numerico": "valor"})
        unidad, nombre, desc = var.unidad, var.nombre, f"dato experimental {var.id} · {var.nombre}"
    elif cfg.objeto_tipo == "resultado_directo":
        res = next((r for r in e.resultados if r.id == cfg.objeto_id), None)
        if res is None:
            raise ErrorDatosMotor(f"El resultado {cfg.objeto_id} no existe.")
        if res.ambito != "medicion":
            raise ErrorDatosMotor(f"«{res.nombre}» tiene ámbito «{res.ambito}»: esta versión del motor analiza resultados por medición.")
        r = tablas["resultados_valores"]
        v = r[r["resultado_id"] == cfg.objeto_id][["registro_id", "valor"]].rename(columns={"registro_id": "medicion_id"})
        unidad, nombre, desc = res.unidad, res.nombre, f"resultado registrado {res.id} · {res.nombre}"
    elif cfg.objeto_tipo == "derivado":
        regla = cfg.regla
        res = next((r for r in e.resultados if r.id == cfg.objeto_id), None)
        if regla is None or not regla.aprobada or not regla.referencia.strip():
            raise ErrorDatosMotor("El resultado calculado no tiene una regla de derivación aprobada con su referencia: "
                                  "el motor no inventa fórmulas.")
        va = next((x for x in e.variables if x.id == regla.a), None)
        vb = next((x for x in e.variables if x.id == regla.b), None)
        if va is None or vb is None:
            raise ErrorDatosMotor("La regla de derivación usa datos que no existen.")
        if va.unidad != vb.unidad:
            raise ErrorDatosMotor(f"«{va.nombre}» y «{vb.nombre}» tienen unidades distintas; no se convierten unidades.")
        val = tablas["valores"]
        a = val[val["variable_id"] == regla.a].set_index("medicion_id")["valor_numerico"]
        b = val[val["variable_id"] == regla.b].set_index("medicion_id")["valor_numerico"]
        dif = (a - b).dropna()
        v = dif.rename("valor").reset_index()
        unidad = va.unidad
        nombre = res.nombre if res else cfg.objeto_id
        desc = f"resultado calculado {cfg.objeto_id} · {nombre} = {va.nombre} − {vb.nombre} (regla aprobada: {regla.referencia})"
        trazas.append(f"Derivación: {nombre} = {va.id} − {vb.id} para {len(v)} mediciones con ambos datos.")
    else:
        raise ErrorDatosMotor(f"Tipo de objeto desconocido: {cfg.objeto_tipo}")

    df = mediciones.merge(v, on="medicion_id", how="left")
    df["punto"] = df["punto_id"].map(lambda p: etiqueta_punto(e, p))
    campos = campos_celda(cfg)
    for c in campos:
        df[f"campo:{c}"] = _campo(df, niveles, e, c).values
    df["celda"] = df[[f"campo:{c}" for c in campos]].agg(" · ".join, axis=1) if campos else "Todas"
    excl_ids = {x.medicion_id for x in cfg.exclusiones}
    excluidas = df[df["medicion_id"].isin(excl_ids)].copy()
    excluidas["motivo"] = excluidas["medicion_id"].map({x.medicion_id: x.motivo for x in cfg.exclusiones})
    df = df[~df["medicion_id"].isin(excl_ids)]
    sin_valor = df["valor"].isna().sum()
    if sin_valor:
        trazas.append(f"{sin_valor} mediciones incluidas no tienen valor del objeto (dato vacío).")
    df = df.dropna(subset=["valor"]).copy()
    df["valor"] = df["valor"].astype(float)

    # Esperadas por celda según el plan aprobado (para porcentajes de faltantes)
    plan = pd.DataFrame([{"medicion_id": m.medicion_id, "punto_id": m.punto_id, "tecnico_previsto": m.tecnico,
                          "patron_previsto": m.patron, "equipo_previsto": m.equipo} for m in e.plan])
    niveles_plan = pd.DataFrame([{"medicion_id": m.medicion_id, "factor_id": k, "nivel": v2}
                                 for m in e.plan for k, v2 in m.niveles.items()], columns=["medicion_id", "factor_id", "nivel"])
    for c in campos:
        plan[f"campo:{c}"] = _campo(plan, niveles_plan, e, c).values
    plan["celda"] = plan[[f"campo:{c}" for c in campos]].agg(" · ".join, axis=1) if campos else "Todas"
    esperadas = plan.groupby(["punto_id", "celda"]).size().rename("esperadas").reset_index()
    return Observaciones(df=df.sort_values(["punto_id", "celda", "medicion_id"]).reset_index(drop=True), unidad=unidad,
                         nombre_objeto=nombre, descripcion_objeto=desc, excluidas=excluidas, esperadas=esperadas, trazas=trazas)


def estructura(obs: Observaciones) -> dict:
    """n_ij, p_j, q, balance y unidades independientes por nivel (no se usa N_total como sustituto)."""
    salida = {"q": int(obs.df["punto_id"].nunique()), "niveles": {}}
    for punto_id, g in obs.df.groupby("punto_id"):
        nij = g.groupby("celda").size()
        salida["niveles"][punto_id] = {
            "punto": g["punto"].iloc[0],
            "n_ij": {k: int(v) for k, v in nij.items()},
            "p_j": int(len(nij)),
            "n_min": int(nij.min()), "n_max": int(nij.max()),
            "balanceado": bool(nij.nunique() == 1),
            "N_j": int(len(g)),
            "celdas_con_replicas": int((nij >= 2).sum()),
            "gl_dentro": int((nij - 1).clip(lower=0).sum()),
        }
    return salida
