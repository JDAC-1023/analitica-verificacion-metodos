"""Estudio sintético de demostración.

ATENCIÓN: es un ejemplo para probar el flujo de datos. No es un método, un
diseño ni un conjunto de criterios aprobados. No contiene datos reales.
"""

from __future__ import annotations

from src.modelos.estudio import Estudio, Factor, Magnitud, Punto, Recurso, ResultadoInteres, Variable
from src.planificacion.plan import generar_combinaciones


def construir_estudio_demo(codigo: str = "EST-DEMO", nombre: str = "Estudio de ejemplo (sintético)") -> Estudio:
    e = Estudio(
        codigo=codigo, nombre=nombre, tipo="Verificación", metodo="MET-EJEMPLO", version_metodo="1",
        uso_previsto="Probar la configuración, la plantilla y la ingesta con datos sintéticos.",
        documento_referencia="", responsable="Responsable técnico (ejemplo)",
        magnitudes=[Magnitud("MAG-01", "Temperatura", "°C", -20.0, 150.0)],
        puntos=[Punto("PT-01", "MAG-01", 20.0, "°C"), Punto("PT-02", "MAG-01", 40.0, "°C")],
        tecnicos=[Recurso("T-01", "Técnico 1", "tecnico"), Recurso("T-02", "Técnico 2", "tecnico")],
        patrones=[Recurso("P-01", "Termómetro patrón", "patron", "MAG-01", -50.0, 200.0, descripcion="Termómetro patrón (ejemplo)")],
        ibcs=[Recurso("IBC-01", "Medio isotermo", "ibc", "MAG-01", 0.0, 100.0, descripcion="Medio isotermo de ejemplo",
                      marca="Marca X", modelo="Modelo Y", serie="0001", resolucion="0,1 °C")],
        factores=[
            Factor("F-01", "Técnico", "Persona que realiza la medición", vinculo_recurso="tecnico"),
            Factor("F-02", "Día", "Día de medición", niveles=["Día 1", "Día 2"]),
        ],
        condiciones_controladas="Mismo equipo bajo prueba y misma ubicación del sensor.",
        agrupacion=["punto"],
        repeticiones_por_condicion=2,
        unidad_experimental="Ejemplo: cada lectura registrada tras la estabilización (por definir).",
        variables=[
            Variable("V-01", "Indicación del equipo", "decimal", "°C", True, "Lectura del equipo bajo prueba", "lectura"),
            Variable("V-02", "Valor del patrón", "decimal", "°C", True, "Lectura del patrón", "lectura"),
            Variable("V-03", "Temperatura ambiente", "decimal", "°C", False, "Condición del laboratorio", "ambiental"),
        ],
        resultados=[
            ResultadoInteres("R-01", "Error", unidad="°C", origen="calculado", dependencias=["V-01", "V-02"],
                             referencia_calculo="Por definir según el método", ambito="medicion", analizar=True),
            ResultadoInteres("R-02", "Inestabilidad", unidad="°C", origen="directo", ambito="punto", analizar=False),
        ],
    )
    e.plan = generar_combinaciones(e, ["PT-01", "PT-02"], {"tecnico": ["T-01", "T-02"], "F-02": ["Día 1", "Día 2"]},
                                   repeticiones=2, fijos={"patron": "P-01"})
    return e
