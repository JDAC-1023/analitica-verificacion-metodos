"""Flujo completo sin abrir Streamlit: configurar → aprobar → plantilla → diligenciar → cargar → preparar → leer.

Ejecutar desde la raíz del proyecto:
    python -m ejemplos.flujo_completo

Usa una carpeta temporal: no toca los datos de la aplicación. Sirve como
plantilla para construir por código los cuatro conjuntos de prueba controlados
(reemplaza `valores` por los datos de cada escenario).
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd

from src.exportacion.lector_salida import cargar_conjunto
from src.persistencia.repositorio import RepositorioLocal
from src.plantillas.diligenciar import diligenciar_plantilla
from src.plantillas.generador import generar_plantilla
from src.servicios.demo import construir_estudio_demo
from src.servicios.flujo import aprobar_conjunto, cargar_archivo, preparar_conjunto


def main() -> None:
    carpeta = Path(tempfile.mkdtemp(prefix="avm_"))
    repo = RepositorioLocal(carpeta)

    # 1. Configurar y aprobar (aquí con el estudio sintético de ejemplo)
    base = repo.crear_estudio("Estudio de ejemplo", "script")
    estudio = construir_estudio_demo(base.codigo, base.nombre)
    repo.guardar_estudio(estudio, "script")
    repo.aprobar_version(estudio, "script")

    # 2. Plantilla
    plantilla = generar_plantilla(estudio)
    (carpeta / "plantilla.xlsx").write_bytes(plantilla)

    # 3. Diligenciar por código (escenario sintético). Columnas: medicion_id + códigos de los datos.
    valores = pd.DataFrame({
        "medicion_id": [m.medicion_id for m in estudio.plan],
        "V-01": [20.0 + 0.01 * i for i in range(len(estudio.plan))],
        "V-02": [20.0 if m.punto_id == "PT-01" else 40.0 for m in estudio.plan],
    })
    resultados = pd.DataFrame({"registro_id": ["RD0001", "RD0002"], "valor": [0.02, 0.03]})
    diligenciada = diligenciar_plantilla(plantilla, valores, resultados)
    (carpeta / "escenario.xlsx").write_bytes(diligenciada)

    # 4. Cargar, preparar y aprobar
    carga = cargar_archivo(repo, estudio.codigo, diligenciada, "escenario.xlsx", "script")
    print("Carga:", carga["estado_archivo"], carga["conteos"])
    prep = preparar_conjunto(repo, estudio.codigo, carga["carga_id"], ["TR01", "TR03"], [], "script")
    aprobar_conjunto(repo, estudio.codigo, prep["preparacion_id"], "script")

    # 5. Leer la salida como lo hará el motor estadístico
    zip_bytes = repo.obtener_archivo_preparacion(estudio.codigo, prep["preparacion_id"], "conjunto_preparado.zip")
    (carpeta / "conjunto_preparado.zip").write_bytes(zip_bytes)
    datos = cargar_conjunto(zip_bytes)
    obs = datos["observaciones_analisis"]
    print(obs[["medicion_id", "variable_id", "valor_numerico", "punto_id", "factor:Técnico", "factor:Día"]].head())
    print("Archivos en:", carpeta)


if __name__ == "__main__":
    main()
