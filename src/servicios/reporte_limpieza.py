"""Reporte de limpieza: qué se revisó, qué se encontró, qué se hizo y con qué herramienta.

Se arma con la información guardada de la carga y del conjunto preparado; no
vuelve a evaluar nada.
"""

from __future__ import annotations

from src.calidad.reglas import REGLAS
from src.exportacion.lector_salida import cargar_conjunto
from src.persistencia.repositorio import Repositorio
from src.transformaciones.catalogo import TRANSFORMACIONES

SEVERIDAD_TXT = {"bloquea_archivo": "Rechaza el archivo", "excluye_registro": "Saca el registro",
                 "pendiente": "Deja pendiente", "advertencia": "Solo avisa", "informativa": "Informa"}

NUNCA = [
    "Rellenar datos faltantes (con cero, promedios u otros valores).",
    "Redondear valores o cambiar sus cifras.",
    "Convertir unidades o cambiar signos de errores y correcciones.",
    "Borrar datos por ser extremos o «raros»: eso solo lo decide una persona, con motivo y en una versión nueva.",
    "Modificar el archivo original: se conserva tal como llegó, con su huella SHA-256.",
]

HERRAMIENTAS = [
    ("openpyxl", "Leer el Excel celda por celda, sin abrirlo en Excel."),
    ("Reglas RC01–RC20 (src/calidad/reglas.py)", "Revisar estructura, identificadores, completitud y tipos de dato."),
    ("Transformaciones TR01–TR04 (src/transformaciones)", "Interpretar la forma en que quedó escrito un valor, sin cambiarlo."),
    ("SHA-256 (hashlib)", "Huella digital del archivo y del conjunto preparado para demostrar que no se alteraron."),
    ("pandas", "Ordenar los datos en tablas normalizadas para el motor."),
]


def construir(repo: Repositorio, codigo: str, prep_id: str, resultado: dict | None = None) -> dict:
    prep = repo.obtener_preparacion(codigo, prep_id)
    carga = repo.obtener_carga(codigo, prep["carga_id"])
    tablas = cargar_conjunto(repo.obtener_archivo_preparacion(codigo, prep_id, "conjunto_preparado.zip"))
    inc = tablas["incidencias"]
    conteo = inc["regla"].value_counts().to_dict() if len(inc) else {}
    reglas = []
    for r in REGLAS.values():
        n = int(conteo.get(r.codigo, 0))
        reglas.append({"codigo": r.codigo, "nombre": r.nombre, "que_revisa": r.descripcion,
                       "si_falla": SEVERIDAD_TXT.get(r.severidad, r.severidad), "hallazgos": n,
                       "resultado": "Sin hallazgos" if n == 0 else f"{n} hallazgo(s)"})
    tr = tablas["transformaciones"]
    usos = tr["codigo"].value_counts().to_dict() if len(tr) else {}
    transformaciones = [{"codigo": t.codigo, "nombre": t.nombre, "que_hace": t.descripcion, "ejemplo": t.ejemplo,
                         "autorizada": t.codigo in prep["transformaciones_autorizadas"], "veces": int(usos.get(t.codigo, 0))}
                        for t in TRANSFORMACIONES.values()]
    ejemplos = tr.head(15).to_dict("records") if len(tr) else []
    exclusiones = tablas["exclusiones"].to_dict("records") if len(tablas["exclusiones"]) else []
    c = prep["conteos"]
    pasos = [
        ("1. Recepción", f"Se recibió «{carga['nombre_archivo']}» el {carga['fecha'][:16].replace('T', ' ')} por {carga['usuario']}. "
                         f"Se guardó intacto con su huella SHA-256."),
        ("2. Identificación", "Se comprobó que el archivo es la plantilla de este estudio y de la versión aprobada del diseño."),
        ("3. Revisión de calidad", f"Se aplicaron las {len(REGLAS)} reglas de calidad a cada fila: "
                                   f"{sum(1 for r in reglas if r['hallazgos'])} regla(s) con hallazgos, "
                                   f"{sum(r['hallazgos'] for r in reglas)} hallazgo(s) en total."),
        ("4. Transformaciones", f"Autorizadas: {', '.join(prep['transformaciones_autorizadas']) or 'ninguna'}. "
                                f"Aplicadas {len(tr)} vez/veces (solo cambian la forma de escribir, no el valor)."),
        ("5. Exclusiones", f"{len(exclusiones)} registro(s) excluido(s), cada uno con su motivo."),
        ("6. Resultado", f"De {c['recibidos']} filas recibidas pasan al análisis {c['incluidos_en_preparado']} "
                         f"(aceptadas {c['aceptados']}, normalizadas {c['normalizados']}, con advertencia {c['con_advertencia']}; "
                         f"pendientes {c['pendientes']}, excluidas {c['excluidos']})."),
        ("7. Aprobación", f"Conjunto aprobado por {prep.get('aprobada_por') or '—'} el {(prep.get('fecha_aprobacion') or '—')[:16].replace('T', ' ')}."
         if prep.get("aprobada") else "Conjunto aún no aprobado para el análisis."),
    ]
    motor = None
    if resultado:
        f = next((x for x in resultado["resultados"] if x["tecnica"] == "Faltantes respecto al plan"), None)
        motor = {"esperadas": f["estimacion"]["esperadas"] if f else None, "validas": f["n"] if f else None,
                 "faltantes": f["estimacion"]["faltantes"] if f else None,
                 "pct": f["estimacion"]["valor"] if f else None,
                 "exclusiones_analisis": resultado.get("excluidas", []), "objeto": resultado["objeto"]["nombre"]}
    return {"archivo": carga["nombre_archivo"], "sha256": carga["sha256"], "fecha_carga": carga["fecha"],
            "usuario_carga": carga["usuario"], "preparacion_id": prep_id, "conteos": c, "pasos": pasos,
            "reglas": reglas, "transformaciones": transformaciones, "ejemplos_transformacion": ejemplos,
            "exclusiones": exclusiones, "nunca": NUNCA, "herramientas": HERRAMIENTAS, "motor": motor,
            "incidencias": inc.head(50).to_dict("records") if len(inc) else []}
