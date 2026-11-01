# Cómo incorporar esta entrega a tu repositorio (Windows · PowerShell)

Este ZIP contiene **solo los archivos nuevos o modificados**. Se copia encima de tu carpeta `analitica-verificacion-metodos`, en la rama `prototipo-alejandra`.

## 1. Archivos

| Acción | Archivos |
| --- | --- |
| **Conservar sin cambios** | `.github/workflows/pruebas.yml`, `tests/test_healthcheck.py`, `data/`, `.venv/` |
| **Reemplazar** | `app.py` (ahora es la entrada multipágina), `README.md`, `requirements.txt` (pasa a UTF-8 y se agrega `openpyxl`), `.gitignore` (se agrega `datos_locales/`), `src/healthcheck.py` (quita una función duplicada) |
| **Crear** | `.streamlit/config.toml`, `interfaz/`, `src/` (10 paquetes), `tests/` (7 archivos nuevos), `docs/`, `ejemplos/`, `herramientas/`, `LEEME_PRIMERO.md` |
| **Eliminar (recomendado)** | `app_modulo1.py`: su funcionalidad quedó reemplazada por la nueva aplicación. Nunca se subió a Git, así que basta con borrarlo |

## 2. Copiar e instalar

```powershell
cd C:\ruta\a\analitica-verificacion-metodos
git switch prototipo-alejandra
git status                                   # confirma que no tienes cambios sin guardar que te importen

# Descomprime el ZIP encima de la carpeta del proyecto (reemplaza los archivos cuando lo pregunte):
Expand-Archive -Path "$HOME\Downloads\entrega_v2_asistente.zip" -DestinationPath . -Force
Remove-Item .\app_modulo1.py                 # opcional, recomendado

.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt    # ya tienes casi todo; agrega lo que falte
python -m pytest -q                          # deben pasar 86 pruebas
streamlit run app.py
```

## 3. Probar en 5 minutos

1. Pulsa **Crear estudio** en la barra lateral. Se abre el asistente a la derecha.
2. Responde cada paso y pulsa **Guardar y continuar**: estudio, método, magnitudes, puntos, equipo a evaluar (IBC), técnicos, patrones, condiciones, datos, resultados, criterios y mediciones.
3. En **Generar plantilla**, marca la revisión, genera y descarga el Excel.
4. Llena las columnas moradas y pulsa **Siguiente: Subir DB** para subirlo.
5. Puedes cerrar el panel cuando quieras: al pulsar **Continuar en el asistente** vuelve al último paso guardado.

## 4. Guardar en Git

```powershell
git add .
git status                                   # verifica que NO aparezca datos_locales/
git commit -m "Parametrización, plantilla, ingesta, calidad y exportación de datos"
git push origin prototipo-alejandra
```

GitHub Actions ejecutará las 86 pruebas al hacer push.

## 5. Qué leer después

- `docs/ESTADO.md`: qué funciona, con qué limitaciones y qué queda pendiente.
- `docs/00_interpretacion_matriz.md`: las decisiones provisionales que necesitan tu aprobación.
