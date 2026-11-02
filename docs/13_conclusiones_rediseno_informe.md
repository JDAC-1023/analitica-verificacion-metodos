# Conclusiones, retroalimentación, rediseño e informe PDF

## Paso a paso y veredicto (`src/motor/flujo.py`)
- **Paso a paso:** datos → ¿atípicos? (si sí, qué pasa con ellos: sensibilidad) → ¿residuos normales? → (solo si sí) ¿varianzas iguales? → prueba elegida y dónde están las diferencias → sesgo → repetibilidad → reproducibilidad intralaboratorio → veredicto. Cada paso dice qué se encontró y «por lo tanto» qué sigue.
- **Veredicto:** «TU MÉTODO SIRVE», «SIRVE, CON OBSERVACIONES» (cumple pero hubo datos no normales u otras observaciones), «NO SIRVE (TODAVÍA)», «NO SE PUEDE DECIDIR» o «FALTAN LOS LÍMITES».
- **Implicaciones:** para cada parámetro que no cumple, qué significa para el método, qué hacer y si el incumplimiento se debe a un atípico (sensibilidad).
- **Mapa por punto:** ✔/✘ de cada parámetro en cada temperatura y si el resultado depende del técnico o del patrón.
- **Evolución entre versiones:** v1 → v2… con su motivo y veredicto.

## Varios resultados evaluados
Con varios resultados (p. ej. corrección, inestabilidad, inhomogeneidad) la pantalla muestra primero el **veredicto por resultado evaluado** y un selector «Ver resultados y conclusiones de:». El PDF repite el resumen (1.k), los resultados por etapa (4.k) y el consolidado (5.k) para cada resultado, con el título «Resultado evaluado: …», y cierra con la conclusión del análisis completo. Los comentarios se guardan por resultado y etapa.

## Conclusiones preliminares automáticas
`motor.conclusiones_por_etapa` redacta, con reglas fijas, una conclusión para limpieza, atípicos, normalidad, homocedasticidad y desempeño, y la conclusión consolidada. Estados globales: CONFORME, CONFORME_CON_OBSERVACIONES, NO_CONFORME, INDETERMINADO, INCOMPLETO (característica requerida sin resultado evaluable o no implementada), CALCULADO_SIN_EVALUACION, SIN_ALCANCE.

## Comentarios por etapa
Cajas en «Resultados por etapa» (limpieza, atípicos, normalidad, desempeño) y en «Conclusiones». Se guardan en `analisis/vNNN/comentarios.json` (solo se agregan) con usuario y fecha, quedan en la bitácora (`comentario_analisis`) y salen en el PDF bajo cada etapa.

## Rediseño / versión 2
- **Versión derivada del análisis**: copia la configuración de una versión en la N+1 con `padre`, `motivo_cambio` y diferencias (`analisis_version_derivada` en la bitácora). Permite excluir mediciones con motivo técnico y responsable obligatorios. Luego se editan parámetros y criterios en «Configurar» y se ejecuta.
- **Una versión ejecutada es inmutable** (el repositorio rechaza sobrescribirla).
- **Clonar estudio**: crea un estudio nuevo en borrador con el mismo diseño y `derivado_de = «EST-xxxx vN»` (fuera de la huella del diseño), para cambiar puntos, réplicas o condiciones.

## Informe PDF (ReportLab, `src/informes/pdf.py`)
Se construye solo con lo guardado (no recalcula): A4, tipografía DejaVu Sans, encabezado y pie con «Página x de y».

1. Portada y bloque de control: estudio, versiones, fecha de emisión, ejecución, edición normativa, huella SHA-256, firmas de Elaboró / Revisó / Autorizó; conclusión consolidada.
1b. Resumen en lenguaje sencillo: veredicto, paso a paso del motor, desempeño punto por punto, qué implica cada incumplimiento, gráficos de resumen y significado metrológico de cada parámetro.
2. Objeto y alcance; ruta verificación/validación.
3. Información del estudio (método, IBC, patrones, técnicos, puntos, factores).
4. Datos y trazabilidad (preparación, archivo original y SHA-256, faltantes, exclusiones).
5. Marco teórico (solo técnicas aplicadas, con citas APA) y árbol de decisiones.
6. Resultados por etapa (limpieza, atípicos, normalidad, homocedasticidad, desempeño): «qué se compara», conclusión automática, tablas, gráficos, fuentes de variación con la prueba usada en cada punto, dónde están las diferencias (post hoc) y comentarios del revisor.
7. Consolidado por característica y criterios aplicados.
8. Conclusiones técnicas finales.
9. Limitaciones.
10. Historial de versiones y bitácora de auditoría.
11. Referencias (APA 7).
12. Anexo A datos analizados; anexo B matriz de reglas.

Cada informe se guarda como `analisis/vNNN/informe_<fecha>.pdf` con su metadato JSON (SHA-256, firmantes) y se lista en la página «Informes».

## Nota sobre los documentos de referencia
El archivo S2500725S (CEPAL, estimación en áreas pequeñas) no trata de validación de métodos; no se usó.
