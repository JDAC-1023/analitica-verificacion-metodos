# Cómo incorporar esta entrega (Windows · PowerShell)

> **Actualización 5.1:** árbol de decisión corregido: sin normalidad no se aplica ningún ANOVA (ni Welch, ni prueba F, ni intervalos χ²); Bartlett solo con normalidad. Documentación y capturas actualizadas (`docs/`, `docs/capturas/`, `docs/diagramas/arbol_decision.png`).
>
> **Actualización 5.0:** flujo de decisión paso a paso (atípicos → normalidad → homocedasticidad → prueba correspondiente), dónde están las diferencias y por qué, reproducibilidad intralaboratorio, veredicto «tu método sirve / no sirve» con qué implica y qué hacer.
>
> **Actualización 4.0:** Inicio con tarjetas para abrir cada estudio y su panel (sin selector lateral) · Testeo 1–4 rehechos: 5 lecturas por serie, errores sembrados y criterio de prueba (cumple / no cumple / con observaciones) · ANOVA de fuentes de variación (técnico × patrón) con tablas de medias · α, confianza y Shapiro-Wilk fijos; solo se configuran los límites · informe con significado metrológico y tablas de contexto.
>
> Si ya tenías Testeo 1–4 de la versión anterior, la app los conserva renombrados como «Testeo N (bases anteriores)» y crea los nuevos.

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

Expand-Archive -Path "$HOME\Downloads\entrega_v5_1_arbol_corregido.zip" -DestinationPath . -Force

.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt           # instala las 5 librerías nuevas
python -m pytest -q                                 # deben pasar 126 pruebas
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
