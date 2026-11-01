"""Contexto compartido por las etapas del motor."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.modelos.estudio import Estudio
from src.motor.configuracion import ConfiguracionAnalisis
from src.motor.datos import Observaciones
from src.motor.resultado import NodoDecision, ResultadoAnalisis
from src.motor.reglas import regla


@dataclass
class Contexto:
    e: Estudio
    cfg: ConfiguracionAnalisis
    obs: Observaciones
    est: dict
    resultados: list[ResultadoAnalisis] = field(default_factory=list)
    arbol: list[NodoDecision] = field(default_factory=list)
    normalidad: dict = field(default_factory=dict)   # (objeto, punto_id) -> "rechaza" | "no_rechaza" | None
    homocedasticidad: dict = field(default_factory=dict)   # punto_id -> "rechaza" | "no_rechaza" | None
    _n: int = 0

    def nuevo(self, etapa: str, tecnica: str, agrupacion: str, estado: str, **kw) -> ResultadoAnalisis:
        self._n += 1
        r = ResultadoAnalisis(analysis_id=f"A{self.cfg.version:02d}-{self._n:03d}", etapa=etapa, tecnica=tecnica,
                              study_id=self.e.codigo, version=self.cfg.version, variable_id=self.cfg.objeto_id,
                              unidad=self.obs.unidad, agrupacion=agrupacion, estado=estado, **kw)
        self.resultados.append(r)
        return r

    def decidir(self, pregunta: str, respuesta: str, evidencia: str = "", codigo: str = "") -> NodoDecision:
        nodo = NodoDecision(pregunta, respuesta, evidencia, codigo)
        self.arbol.append(nodo)
        return nodo

    def origen(self, codigo: str) -> str:
        return regla(codigo)["origen"]

    # ----------------------------------------------------------- datos por nivel
    def niveles(self):
        for punto_id, g in self.obs.df.groupby("punto_id", sort=True):
            yield punto_id, g

    @staticmethod
    def celdas(g: pd.DataFrame) -> pd.DataFrame:
        """Resumen por celda: n, media, s (ddof=1; NaN si n=1), ids."""
        filas = []
        for celda, c in g.groupby("celda", sort=True):
            v = c["valor"].to_numpy(float)
            filas.append({"celda": celda, "n": len(v), "media": float(v.mean()),
                          "s": float(v.std(ddof=1)) if len(v) > 1 else np.nan,
                          "ids": list(c["medicion_id"])})
        return pd.DataFrame(filas)
