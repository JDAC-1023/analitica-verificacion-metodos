"""Ejemplo mínimo: leer un conjunto preparado descargado desde la aplicación.

Ejecutar desde la raíz del proyecto:
    python -m ejemplos.leer_salida ruta\\al\\conjunto_preparado_EST-0001_PREP-....zip
"""

import sys

from src.exportacion.lector_salida import cargar_conjunto, matriz_por_variable


def main(ruta: str) -> None:
    datos = cargar_conjunto(ruta)  # comprueba las huellas SHA-256 del manifiesto
    m = datos["manifiesto"]
    print(f"Estudio {m['codigo_estudio']} · diseño v{m['version_diseno']} · carga {m['carga_id']}")
    print("Conteos:", m["conteos"])

    obs = datos["observaciones_analisis"]
    print("\nDatos experimentales disponibles:")
    print(datos["definiciones_variables"][["id", "nombre", "unidad"]].to_string(index=False))
    print("\nResultados de interés definidos (los calculados aún no tienen valores):")
    print(datos["definiciones_resultados"][["id", "nombre", "origen", "ambito", "dependencias", "analizar"]].to_string(index=False))

    primera = datos["definiciones_variables"]["id"].iloc[0]
    tabla = matriz_por_variable(datos, primera)
    print(f"\nObservaciones de {primera} por punto y grupo comparable:")
    print(tabla.groupby(["punto_id", "grupo_comparable"])["valor_numerico"].agg(["count"]))
    print(f"\nFilas en la vista de análisis: {len(obs)}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python -m ejemplos.leer_salida <conjunto_preparado.zip>")
    main(sys.argv[1])
