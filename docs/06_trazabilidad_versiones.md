# Trazabilidad y control de versiones

## Qué se conserva

| Elemento | Dónde | Inmutable |
| --- | --- | --- |
| Diseño aprobado (vN) + huella SHA-256 | `versiones/v00N.json` | Sí |
| Borrador actual | `borrador.json` | No (editable) |
| Archivo original de cada carga | `cargas/<id>/original.xlsx` | Sí: nunca se sobrescribe |
| SHA-256 del original, fecha, usuario y nombre del archivo | `carga.json` | Sí |
| Lectura cruda (valor de cada celda tal como vino y su fila de Excel) | `carga.json` → `lectura` | Sí |
| Incidencias con hoja, fila, celda, valor y esperado | `carga.json`, `incidencias.csv` | Sí |
| Transformaciones (celda, valor original, valor interpretado, código) | `transformaciones.csv` | Sí |
| Exclusiones con motivo y origen (automático o manual, con usuario) | `exclusiones.csv`, manifiesto | Sí |
| Estado de **todos** los registros, incluidos pendientes y excluidos | `registros_estado.csv` | Sí |
| Diferencias con la carga anterior de la misma versión | `carga.json` → `cambios_vs_anterior` | Sí |
| Bitácora de acciones (crear, guardar, aprobar, cargar, preparar, aprobar conjunto) | `eventos.jsonl` | Solo se agrega |
| Huella de cada CSV de la salida | `manifiesto.json` | Sí |

## Cadena de trazabilidad

Del dato preparado al original:

```text
valores.csv (fila) ──carga_id + hoja + fila_excel + celda──▶ original.xlsx (celda exacta)
       │                                                            │
       └─version_diseno + huella_diseno──▶ versiones/v00N.json ◀─_control (huella impresa)
```

## Política de versiones (PD13, provisional)

1. **Borrador → aprobado:** «Aprobar diseño» congela la configuración como vN. Si no hubo cambios desde la última versión, se reutiliza.
2. **Cambio después de aprobar:** al guardar un cambio que altera la huella, el estudio vuelve a *borrador*. Las versiones anteriores y sus plantillas siguen disponibles.
3. **Plantilla:** siempre se genera desde una versión aprobada. Lleva el estudio, la versión y la huella en la hoja oculta `_control`.
4. **Carga:** el archivo debe coincidir en estudio, versión y huella; si no, se rechaza (RC04, RC05). Así nunca se mezclan datos de diseños distintos.
5. **Segunda carga (corrección):** es una carga nueva. La anterior se conserva y se registran las celdas que cambiaron.
6. **Preparación:** cada preparación tiene su ID y queda guardada. Una misma carga puede prepararse varias veces (por ejemplo, con otras exclusiones). Los CSV son idénticos si los parámetros lo son.
7. **Aprobación del conjunto (X07):** marca qué preparación es la entrada del motor.

## Control de versiones del código

- Rama de trabajo: `prototipo-alejandra`.
- `datos_locales/` está en `.gitignore`: los datos de estudios y los archivos cargados no se suben a GitHub.
- No hay credenciales en el repositorio. Cuando se conecte Supabase, las claves irán en `.streamlit/secrets.toml`, que ya está excluido.
- GitHub Actions (`.github/workflows/pruebas.yml`) ejecuta las 86 pruebas en cada push.
