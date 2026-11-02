"""Varios resultados evaluados en un mismo análisis.

Cuando el laboratorio elige más de un resultado (por ejemplo corrección, inestabilidad e inhomogeneidad), el motor
corre la secuencia COMPLETA (limpieza → atípicos → normalidad → homocedasticidad → prueba correspondiente →
desempeño → criterios) por separado para cada uno. Ningún resultado comparte decisiones con otro: cada uno tiene
sus propias pruebas, sus propios límites y su propio veredicto. El veredicto del análisis es el del peor resultado.
"""

from __future__ import annotations

from src.auditoria.huella import ahora_iso, json_canonico, sha256_bytes
from src.modelos.estudio import Estudio
from src.motor.configuracion import ConfiguracionAnalisis
from src.motor.reglas import matriz

# del peor al mejor: el estado global es el primero que aparezca en algún resultado
ORDEN = ["NO_CONFORME", "INDETERMINADO", "INCOMPLETO", "CALCULADO_SIN_EVALUACION", "SIN_ALCANCE",
         "CONFORME_CON_OBSERVACIONES", "CONFORME"]


def partes(resultado: dict | None) -> list[dict]:
    """Resultados por objeto. Un análisis de un solo resultado (o de versiones anteriores) devuelve [resultado]."""
    if not resultado:
        return []
    return list(resultado["objetos"]) if resultado.get("multi") else [resultado]


def es_multiple(resultado: dict | None) -> bool:
    return bool(resultado and resultado.get("multi"))


def estado_combinado(estados: list[str]) -> str:
    for e in ORDEN:
        if e in estados:
            return e
    return estados[0] if estados else "INCOMPLETO"


def resumen_por_objeto(resultado: dict) -> list[dict]:
    """Una fila por resultado evaluado: nombre, estado y qué no cumple."""
    from src.motor import flujo
    filas = []
    for r in partes(resultado):
        v = flujo.veredicto(r)
        malos = [i["caracteristica"] for i in flujo.implicaciones(r)]
        filas.append({"id": r["objeto"]["id"], "nombre": r["objeto"]["nombre"], "unidad": r["objeto"]["unidad"],
                      "estado": r["conclusion_final"]["estado"], "titulo": v["titulo"], "color": v["color"],
                      "no_cumple": malos})
    return filas


def ejecutar_todos(tablas: dict, e: Estudio, cfg: ConfiguracionAnalisis, meta: dict | None = None) -> dict:
    from src.motor.motor import VERSION_MOTOR, ejecutar
    objetos = cfg.lista_objetos()
    if len(objetos) <= 1:
        return ejecutar(tablas, e, cfg.para_objeto(objetos[0]) if objetos else cfg, meta)
    subs = [ejecutar(tablas, e, cfg.para_objeto(o), meta) for o in objetos]
    estados = [s["conclusion_final"]["estado"] for s in subs]
    estado = estado_combinado(estados)
    nombres = [s["objeto"]["nombre"] for s in subs]
    unidades = sorted({s["objeto"]["unidad"] for s in subs if s["objeto"]["unidad"]})
    texto = "Se evaluaron {} resultados, cada uno con todas las pruebas por separado: {}. El veredicto del análisis es el " \
            "del resultado más desfavorable.".format(len(subs), "; ".join(f"{n}: {s['conclusion_final']['estado']}"
                                                                         for n, s in zip(nombres, subs)))
    salida = {
        "multi": True,
        "meta": {**subs[0]["meta"], "ejecutado_en": ahora_iso(), "motor": VERSION_MOTOR,
                 "huellas_por_objeto": {s["objeto"]["id"]: s["meta"]["huella_resultado"] for s in subs}},
        "objeto": {"tipo": "varios", "id": ", ".join(s["objeto"]["id"] for s in subs), "nombre": ", ".join(nombres),
                   "descripcion": f"{len(subs)} resultados evaluados por separado: " + "; ".join(s["objeto"]["descripcion"] for s in subs),
                   "unidad": unidades[0] if len(unidades) == 1 else ", ".join(unidades)},
        "objetos": subs,
        "conclusion_final": {"estado": estado, "texto": texto, "tipo": subs[0]["conclusion_final"].get("tipo"),
                             "por_objeto": {s["objeto"]["id"]: s["conclusion_final"]["estado"] for s in subs}},
        "reglas": matriz(),
    }
    salida["meta"].pop("huella_resultado", None)
    salida["meta"]["huella_resultado"] = sha256_bytes(json_canonico({k: v for k, v in salida.items() if k != "meta"}).encode())
    return salida
