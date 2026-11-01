# Cómo incorporar esta entrega (Windows · PowerShell)

> **Actualización 3.1:** botón «Siguiente: Análisis estadístico» en Datos preparados, aviso claro si faltan librerías y los 4 estudios de prueba (`data/estudios_prueba/`) que se crean con un clic en **Inicio → Crear los estudios de prueba**.

Entrega 3: **motor estadístico, conclusiones, comentarios, versión 2 e informe PDF.** El ZIP trae el proyecto completo (sin `datos_locales/` ni `.venv/`). Se descomprime encima de tu carpeta en la rama `prototipo-alejandra`.

## 1. Qué cambia

| Acción | Archivos |
| --- | --- |
| **Nuevos** | `src/motor/` (motor), `src/informes/` (PDF), `src/servicios/analisis.py`, `tests/test_motor.py`, `tests/test_analisis_servicio.py`, `tests/motor_casos.py`, `docs/11_…`, `docs/12_…`, `docs/13_…` |
| **Reemplazados** | `app.py`, `requirements.txt` (agrega scipy, statsmodels, matplotlib, reportlab, pypdf), `interfaz/paginas/analisis.py` e `informes.py`, `interfaz/comun.py`, `src/persistencia/repositorio.py`, `src/modelos/estudio.py`, `src/auditoria/huella.py`, `tests/test_interfaz.py`, `README.md`, `docs/` |
| **No se toca** | `datos_locales/` (tus estudios siguen ahí), `.venv/`, `.github/` |

## 2. Copiar, instalar y probar

```powershell
cd C:\ruta\a\analitica-verificacion-metodos
git switch prototipo-alejandra
git status                                          # que no haya cambios pendientes que te importen

Expand-Archive -Path "$HOME\Downloads\entrega_v3_1_motor_pruebas.zip" -DestinationPath . -Force

.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt           # instala las 5 librerías nuevas
python -m pytest -q                                 # deben pasar 120 pruebas
streamlit run app.py
```

## 3. Probar el motor en 5 minutos

1. Elige un estudio que tenga un conjunto **aprobado** (Datos preparados → «Confirmar datos listos para analizar»).
2. Ve a **Análisis e informes → Análisis estadístico**.
3. En **Configurar**: elige qué se analiza (por ejemplo «Resultado calculado» = Indicación − Patrón, marca «Regla aprobada»), marca las características como REQUERIDA, indica qué condiciones cambian (Técnico, Día), la referencia y, si los tienes, los criterios.
4. Mira abajo la **Ruta de decisión en tiempo real**: cambia con cada ajuste.
5. Pulsa **Ejecutar análisis** → revisa **Resultados por etapa**, escribe comentarios, mira **Conclusiones**.
6. **Informe PDF**: escribe quién revisó y autorizó y genera el PDF.
7. **Rediseño / versión 2**: crea la versión 2 (con exclusiones motivadas si aplica) o clona el estudio.

## 4. Guardar en Git

```powershell
git add .
git status                                          # verifica que NO aparezca datos_locales/
git commit -m "Motor estadístico, conclusiones, versión 2 e informe PDF"
git push origin prototipo-alejandra
```

## 5. Qué leer

- `docs/11_motor_contrato.md`: los campos que la matriz no tenía y que ahora pide el motor (hay que aprobarlos).
- `docs/12_motor_reglas_y_arbol.md`: árbol de decisión y reglas.
- `docs/ESTADO.md`: qué funciona y qué falta.
