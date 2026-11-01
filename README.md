# Sistema de analítica de datos · Verificación y validación de métodos de calibración

Trabajo de grado de la Especialización en Analítica de Datos.
Participantes: Jessica Alejandra González Segura y Juan David Ahumada Caro.

## Estado

**Fase de parametrización, ingeniería de datos e ingesta: funcional y probada (86 pruebas automatizadas).**
El flujo completo funciona: crear estudio → configurar el método → condiciones → mediciones → resultados de interés → revisar y aprobar → plantilla Excel → registrar datos → cargar → verificar calidad → gestionar incidencias → preparar → descargar el conjunto normalizado.
El motor estadístico y los informes son fases posteriores (secciones reservadas en la aplicación). El detalle está en [`docs/ESTADO.md`](docs/ESTADO.md).

## Tecnologías

Python 3.13 · Streamlit 1.66 · pandas · openpyxl · pytest · Git/GitHub · GitHub Actions. Persistencia: local en archivos JSON, con un contrato listo para Supabase.

## Instalación en Windows (PowerShell, desde la carpeta del proyecto)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloquea la activación: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` (una sola vez).

## Ejecutar la aplicación

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```

Se abre en <http://localhost:8501>. Los estudios, las cargas y las preparaciones se guardan en `datos_locales/` (excluida de Git). Para usar otra carpeta: `$env:AVM_DATOS_DIR = "C:\ruta\a\mis_datos"`.

## Pruebas

```powershell
python -m pytest -q
python -m herramientas.generar_documentacion   # regenera diccionario, reglas, librerías y el informe de pruebas en docs/
```

## Usar el núcleo desde Python (sin Streamlit)

```powershell
python -m ejemplos.flujo_completo                    # recorre todo el flujo con datos sintéticos
python -m ejemplos.leer_salida ruta\al\conjunto.zip  # lee un conjunto preparado descargado
```

## Estructura

```text
app.py                     entrada de Streamlit (navegación y barra lateral)
interfaz/                  páginas, estilos y utilidades de presentación (sin lógica de negocio)
src/modelos/               modelo del estudio (campos de la matriz)
src/configuracion/         completitud y coherencia por etapa
src/planificacion/         plan explícito, generador opcional, importación, validación
src/plantillas/            especificación de columnas, generador Excel, diligenciamiento por código
src/ingesta/               lectura e identificación del archivo
src/calidad/               reglas RC01–RC20, evaluador, incidencias
src/transformaciones/      transformaciones autorizables TR01–TR04
src/servicios/             flujo: cargar, preparar, aprobar; estudio de ejemplo
src/exportacion/           conjunto preparado (SAL-1.0) y lector para el motor
src/persistencia/          repositorio local (contrato listo para Supabase)
src/auditoria/             huellas SHA-256
tests/                     pruebas automatizadas (datos sintéticos)
docs/                      insumos técnicos editables para el documento académico
ejemplos/, herramientas/   scripts de ejemplo y generación de documentación
```

## Documentación técnica (`docs/`)

| Archivo | Contenido |
| --- | --- |
| 00_interpretacion_matriz.md | Lectura de la matriz, decisiones provisionales e incompatibilidades |
| 01_diccionario_datos.md / .csv | Diccionario de datos (generado desde el código) |
| 02_modelo_datos.md | Modelo conceptual, lógico, físico local y propuesta para Supabase |
| 03_arquitectura.md | Diagrama de arquitectura y componentes |
| 04_matriz_reglas_calidad.md / .csv | Matriz de reglas de calidad y transformaciones (generada) |
| 05_procedimientos.md | Generación de plantillas, ingesta, limpieza y transformación |
| 06_trazabilidad_versiones.md | Trazabilidad y control de versiones |
| 07_pruebas.md | Pruebas: entrada, resultado esperado y resultado obtenido (generado al ejecutar pytest) |
| 08_librerias.md | Librerías con su versión real (generado) |
| 09_salida_para_el_motor.md | Salida que recibirá el motor estadístico |
| 10_capturas.md | Capturas reales de la aplicación |
| diagramas/ | Diagramas en Mermaid (editables) y PNG |
| ESTADO.md | Qué está terminado, qué funciona y qué está pendiente |
