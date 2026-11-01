"""Catálogo de reglas de calidad de datos (matriz de reglas).

Estas reglas comprueban la calidad ESTRUCTURAL de los datos: formato,
correspondencia con el diseño, completitud, tipos e identificadores.
No evalúan estadísticamente los resultados: ningún valor se marca como
incorrecto por ser extremo y ninguna observación se elimina por su
comportamiento estadístico.

El documento docs/04_matriz_reglas_calidad.md se genera desde este catálogo
(herramientas/generar_documentacion.py), de modo que código y documentación
no pueden divergir.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

# Severidades
BLOQUEA_ARCHIVO = "bloquea_archivo"      # el archivo completo se rechaza
EXCLUYE_REGISTRO = "excluye_registro"    # el registro sale del conjunto preparado (motivo automático)
PENDIENTE = "pendiente"                  # el registro queda pendiente de corrección
ADVERTENCIA = "advertencia"              # el registro se conserva y se informa
INFORMATIVA = "informativa"              # solo informa (archivo)


@dataclass(frozen=True)
class ReglaCalidad:
    codigo: str
    nombre: str
    descripcion: str
    aplica_a: str
    condicion: str
    tipo_incidencia: str
    severidad: str
    tratamiento: str
    mensaje: str            # plantilla del mensaje para el usuario
    conserva: str
    prueba: str             # prueba automatizada que demuestra la regla

    def to_dict(self) -> dict:
        return asdict(self)


REGLAS: dict[str, ReglaCalidad] = {r.codigo: r for r in [
    ReglaCalidad("RC01", "Archivo incompatible",
                 "El archivo no se puede abrir como libro de Excel (.xlsx).",
                 "Archivo", "openpyxl no logra abrir el contenido recibido", "Formato", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo; no se lee ningún registro.",
                 "El archivo «{archivo}» no es un Excel válido (.xlsx) y fue rechazado. Descarga de nuevo la plantilla y guárdala como .xlsx.",
                 "Archivo original, huella SHA-256, fecha y usuario de la carga.",
                 "tests/test_ingesta.py::test_archivo_no_excel_se_rechaza"),
    ReglaCalidad("RC02", "Hoja requerida ausente",
                 "Falta una hoja que la plantilla debe contener.",
                 "Archivo / hoja", "Hoja «Mediciones», «_control» o «Resultados_directos» (si el diseño la exige) no existe", "Estructura", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo.",
                 "Falta la hoja «{hoja}». El archivo fue rechazado porque no conserva la estructura de la plantilla.",
                 "Archivo original y lista de hojas encontradas.",
                 "tests/test_ingesta.py::test_hoja_mediciones_ausente_rechaza"),
    ReglaCalidad("RC03", "Plantilla no reconocida",
                 "El archivo no tiene los metadatos de control o el formato de plantilla no es compatible.",
                 "Archivo / _control", "formato_plantilla ≠ PLT-1.0 o metadatos ilegibles", "Versión de formato", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo.",
                 "El archivo no corresponde a una plantilla generada por esta aplicación (formato {valor}).",
                 "Archivo original y metadatos leídos.",
                 "tests/test_ingesta.py::test_formato_de_plantilla_incompatible"),
    ReglaCalidad("RC04", "Archivo de otro estudio",
                 "El código de estudio del archivo no coincide con el estudio seleccionado.",
                 "Archivo / _control", "codigo_estudio del archivo ≠ estudio seleccionado", "Identificación", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo.",
                 "Este archivo pertenece al estudio {valor}, no al estudio {esperado}. Fue rechazado.",
                 "Archivo original y código encontrado.",
                 "tests/test_ingesta.py::test_archivo_de_otro_estudio"),
    ReglaCalidad("RC05", "Versión del diseño incompatible",
                 "La versión del diseño del archivo no existe, no es la seleccionada o su huella no coincide con la versión aprobada.",
                 "Archivo / _control", "version_diseno inexistente o distinta, o huella_diseno ≠ huella aprobada", "Versión", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo.",
                 "El archivo corresponde a la versión {valor} del diseño, pero se esperaba la versión {esperado}. Fue rechazado para no mezclar diseños.",
                 "Archivo original, versión y huella encontradas.",
                 "tests/test_ingesta.py::test_version_incompatible"),
    ReglaCalidad("RC06", "Columnas o unidades inconsistentes",
                 "Falta una columna de la plantilla o su encabezado (incluida la unidad entre corchetes) fue modificado.",
                 "Hoja / encabezados", "Encabezado esperado no encontrado en la fila 1", "Estructura / unidades", BLOQUEA_ARCHIVO,
                 "Rechazar el archivo.",
                 "No se encontró la columna «{esperado}» en la hoja {hoja}. Si cambiaste un encabezado o una unidad, usa la plantilla original.",
                 "Archivo original y encabezados encontrados.",
                 "tests/test_ingesta.py::test_unidad_modificada_en_encabezado"),
    ReglaCalidad("RC07", "Columna no prevista",
                 "El archivo tiene una columna adicional que no forma parte de la plantilla.",
                 "Hoja / encabezados", "Encabezado no previsto en la fila 1", "Estructura", ADVERTENCIA,
                 "Ignorar la columna en la preparación; se conserva en el archivo original.",
                 "La columna «{valor}» de la hoja {hoja} no es parte de la plantilla y no se usará. Se conserva en el archivo original.",
                 "Nombre y posición de la columna.",
                 "tests/test_ingesta.py::test_columna_adicional_advierte"),
    ReglaCalidad("RC08", "Identificador desconocido",
                 "La fila tiene un identificador que no corresponde a ninguna medición o registro planificado.",
                 "Registro", "ID no existe en el plan aprobado", "Correspondencia", EXCLUYE_REGISTRO,
                 "Excluir del conjunto preparado con motivo automático.",
                 "La fila {fila} de la hoja {hoja} tiene el identificador «{valor}», que no está planificado. Se excluyó del conjunto preparado.",
                 "Fila completa original, ubicación y motivo.",
                 "tests/test_calidad.py::test_identificador_desconocido_se_excluye"),
    ReglaCalidad("RC09", "Fila sin identificador",
                 "La fila tiene datos pero no tiene identificador de medición.",
                 "Registro", "ID vacío y al menos una celda con contenido", "Correspondencia", EXCLUYE_REGISTRO,
                 "Excluir del conjunto preparado con motivo automático.",
                 "La fila {fila} de la hoja {hoja} tiene datos pero no tiene identificador. Se excluyó del conjunto preparado.",
                 "Fila completa original y ubicación.",
                 "tests/test_calidad.py::test_fila_sin_identificador_se_excluye"),
    ReglaCalidad("RC10", "Registro duplicado",
                 "El mismo identificador aparece en más de una fila.",
                 "Registro", "ID repetido en la hoja", "Duplicidad", PENDIENTE,
                 "Dejar pendientes todas las filas con ese ID; no se elige ninguna automáticamente.",
                 "La medición {medicion} aparece {valor} veces (filas {esperado}). Se conservaron los originales y quedó pendiente de revisar.",
                 "Todas las filas originales duplicadas.",
                 "tests/test_calidad.py::test_registros_duplicados_quedan_pendientes"),
    ReglaCalidad("RC11", "Medición planificada ausente",
                 "Una medición del plan no aparece en el archivo.",
                 "Archivo / plan", "ID planificado no encontrado", "Completitud", ADVERTENCIA,
                 "Informar; la medición no forma parte del conjunto preparado.",
                 "La medición planificada {medicion} no está en el archivo.",
                 "Lista de mediciones ausentes.",
                 "tests/test_calidad.py::test_medicion_planificada_ausente"),
    ReglaCalidad("RC12", "Cantidad de registros distinta de la planificada",
                 "El número de filas recibidas no coincide con el número de mediciones planificadas.",
                 "Archivo / plan", "filas con ID ≠ mediciones planificadas", "Completitud", ADVERTENCIA,
                 "Informar.",
                 "Se recibieron {valor} filas y se planificaron {esperado} mediciones.",
                 "Conteos.",
                 "tests/test_calidad.py::test_medicion_planificada_ausente"),
    ReglaCalidad("RC13", "Planificación modificada",
                 "Una celda gris (completada por el sistema) no coincide con el plan aprobado.",
                 "Registro / celda", "Valor de columna del sistema ≠ valor planificado", "Cambio no autorizado", PENDIENTE,
                 "Dejar pendiente; los cambios de ejecución se registran en las columnas «real» con su motivo.",
                 "La medición {medicion} tiene «{valor}» en {columna} ({celda}), pero el plan aprobado indica «{esperado}». El registro quedó pendiente.",
                 "Valor encontrado, valor planificado y ubicación.",
                 "tests/test_calidad.py::test_planificacion_modificada"),
    ReglaCalidad("RC14", "Medición sin datos",
                 "La medición no tiene ningún dato experimental registrado.",
                 "Registro", "Todas las columnas de datos y resultados directos vacías", "Completitud", PENDIENTE,
                 "Dejar pendiente; no se imputa ni se reemplaza por cero.",
                 "La medición {medicion} (hoja {hoja}, fila {fila}) no tiene datos registrados. Quedó pendiente y no se incorporó al conjunto preparado.",
                 "Fila original.",
                 "tests/test_calidad.py::test_valores_faltantes_obligatorios"),
    ReglaCalidad("RC15", "Dato obligatorio faltante",
                 "Un dato marcado como obligatorio está vacío.",
                 "Registro / celda", "Celda vacía en columna obligatoria", "Completitud", PENDIENTE,
                 "Dejar pendiente; no se imputa ni se reemplaza por cero.",
                 "La medición {medicion} tiene un valor obligatorio sin diligenciar («{columna}») en la hoja {hoja}, fila {fila} ({celda}). Este registro quedó pendiente y no se incorporó al conjunto preparado.",
                 "Ubicación de la celda vacía.",
                 "tests/test_calidad.py::test_valores_faltantes_obligatorios"),
    ReglaCalidad("RC16", "Valor no interpretable",
                 "El valor no corresponde al tipo de dato configurado y ninguna transformación autorizada permite interpretarlo.",
                 "Registro / celda", "Tipo incompatible (texto en campo numérico, decimal en entero, fecha inválida…)", "Tipo de dato", PENDIENTE,
                 "Dejar pendiente; el valor original se conserva sin cambios.",
                 "La medición {medicion} tiene «{valor}» en «{columna}» ({celda}), que no es un {esperado} válido. El registro quedó pendiente.",
                 "Valor original y ubicación.",
                 "tests/test_calidad.py::test_tipo_de_dato_incompatible"),
    ReglaCalidad("RC17", "Recurso no registrado",
                 "El técnico o el patrón real no existe en el catálogo del estudio.",
                 "Registro / celda", "Código no encontrado en el catálogo", "Identificación", PENDIENTE,
                 "Dejar pendiente.",
                 "La medición {medicion} indica «{valor}» en «{columna}» ({celda}), que no está en el catálogo del estudio. El registro quedó pendiente.",
                 "Valor original y ubicación.",
                 "tests/test_calidad.py::test_recurso_no_registrado"),
    ReglaCalidad("RC18", "Cambio sin motivo",
                 "El técnico o el patrón real es distinto del previsto y no se escribió el motivo del cambio (X03).",
                 "Registro", "real ≠ previsto y motivo vacío", "Desviación del plan", ADVERTENCIA,
                 "Conservar el registro e informar.",
                 "En la medición {medicion} cambió {columna} (previsto «{esperado}», real «{valor}») sin motivo registrado.",
                 "Valores previsto y real.",
                 "tests/test_calidad.py::test_cambio_sin_motivo_advierte"),
    ReglaCalidad("RC19", "Hora no interpretable",
                 "La hora real no tiene el formato HH:MM.",
                 "Registro / celda", "No coincide con HH:MM o HH:MM:SS", "Formato", ADVERTENCIA,
                 "Conservar el registro e informar.",
                 "La hora «{valor}» de la medición {medicion} ({celda}) no tiene el formato HH:MM.",
                 "Valor original.",
                 "tests/test_calidad.py::test_hora_invalida_advierte"),
    ReglaCalidad("RC20", "Resultado directo sin valor",
                 "Un registro de resultado agrupado no tiene valor.",
                 "Registro de resultado", "Celda «Valor» vacía", "Completitud", PENDIENTE,
                 "Dejar pendiente; no se imputa.",
                 "El registro {medicion} («{columna}») de la hoja {hoja}, fila {fila}, no tiene valor. Quedó pendiente.",
                 "Ubicación.",
                 "tests/test_calidad.py::test_resultados_agrupados"),
]}

# Reglas que se decidió NO implementar, para que quede explícito.
REGLAS_EXCLUIDAS = [
    ("Valores extremos o atípicos", "La identificación de atípicos es una decisión estadística del motor; aquí no se marca ni elimina ningún valor por ser extremo."),
    ("Coherencia entre unidades de variables", "Las unidades se fijan en la configuración y viajan en el encabezado; no se convierten unidades sin una regla explícita."),
    ("Fecha real fuera del periodo planificado", "No hay un criterio aprobado; se registra la fecha real sin evaluarla."),
]
