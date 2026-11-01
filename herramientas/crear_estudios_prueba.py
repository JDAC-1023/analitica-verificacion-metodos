"""Crea los estudios de prueba desde data/estudios_prueba/*.xlsx en datos_locales/.

Uso (PowerShell, con el entorno activado):
    python -m herramientas.crear_estudios_prueba "Tu nombre"
"""

import sys

from src.persistencia.repositorio import RepositorioLocal
from src.servicios.estudios_prueba import crear_estudios_prueba

if __name__ == "__main__":
    usuario = sys.argv[1] if len(sys.argv) > 1 else "pruebas"
    for x in crear_estudios_prueba(RepositorioLocal(), usuario):
        if "codigo" in x:
            print(f"{x['codigo']} · {x['nombre']} · {x['mediciones']} mediciones · análisis v1: {x['analisis']}")
        else:
            print(f"{x['nombre']}: {x['omitido']}")
