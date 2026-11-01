# Conclusiones, retroalimentación, rediseño e informe PDF

## Conclusiones preliminares automáticas
`motor.conclusiones_por_etapa` redacta, con reglas fijas, una conclusión para limpieza, atípicos, normalidad y desempeño, y la conclusión consolidada. Estados globales: CONFORME, CONFORME_CON_OBSERVACIONES, NO_CONFORME, INDETERMINADO, INCOMPLETO (característica requerida sin resultado evaluable o no implementada), CALCULADO_SIN_EVALUACION, SIN_ALCANCE.

## Comentarios por etapa
Cajas en «Resultados por etapa» (limpieza, atípicos, normalidad, desempeño) y en «Conclusiones». Se guardan en `analisis/vNNN/comentarios.json` (solo se agregan) con usuario y fecha, quedan en la bitácora (`comentario_analisis`) y salen en el PDF bajo cada etapa.

## Rediseño / versión 2
- **Versión derivada del análisis**: copia la configuración de una versión en la N+1 con `padre`, `motivo_cambio` y diferencias (`analisis_version_derivada` en la bitácora). Permite excluir mediciones con motivo técnico y responsable obligatorios. Luego se editan parámetros y criterios en «Configurar» y se ejecuta.
- **Una versión ejecutada es inmutable** (el repositorio rechaza sobrescribirla).
- **Clonar estudio**: crea un estudio nuevo en borrador con el mismo diseño y `derivado_de = «EST-xxxx vN»` (fuera de la huella del diseño), para cambiar puntos, réplicas o condiciones.

## Informe PDF (ReportLab, `src/informes/pdf.py`)
Se construye solo con lo guardado (no recalcula): A4, tipografía DejaVu Sans, encabezado y pie con «Página x de y».

1. Portada y bloque de control: estudio, versiones, fecha de emisión, ejecución, edición normativa, huella SHA-256, firmas de Elaboró / Revisó / Autorizó; conclusión consolidada.
2. Objeto y alcance; ruta verificación/validación.
3. Información del estudio (método, IBC, patrones, técnicos, puntos, factores).
4. Datos y trazabilidad (preparación, archivo original y SHA-256, faltantes, exclusiones).
5. Marco teórico (solo técnicas aplicadas, con citas APA) y árbol de decisiones.
6. Resultados por etapa: conclusión automática, tabla resumen, detalle con hipótesis, estadístico, críticos, IC, decisiones, cálculos intermedios, gráficos y comentarios del revisor.
7. Consolidado por característica y criterios aplicados.
8. Conclusiones técnicas finales.
9. Limitaciones.
10. Historial de versiones y bitácora de auditoría.
11. Referencias (APA 7).
12. Anexo A datos analizados; anexo B matriz de reglas.

Cada informe se guarda como `analisis/vNNN/informe_<fecha>.pdf` con su metadato JSON (SHA-256, firmantes) y se lista en la página «Informes».

## Nota sobre los documentos de referencia
El archivo S2500725S (CEPAL, estimación en áreas pequeñas) no trata de validación de métodos; no se usó.
