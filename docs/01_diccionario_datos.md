# Diccionario de datos · configuración del estudio
> Generado automáticamente desde `src/modelos/estudio.py` por `herramientas/generar_documentacion.py`. No editar a mano: editar el modelo y volver a generar.
La columna «Campo(s) de la matriz» vincula cada atributo con el campo de la *Matriz de parametrización v0.2*. El diccionario de la **salida para el motor** está en `09_salida_para_el_motor.md`.

## Estudio

Configuración y versión del estudio.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| codigo | str | obligatorio al crear | E02 | E02 (automático) |
| nombre | str | obligatorio al crear | E01 | E01 |
| tipo | str | "Verificación" | E03 | E03 |
| metodo | str | "" | E04 | E04 |
| version_metodo | str | "" | E05 | E05 |
| uso_previsto | str | "" | E06 | E06 |
| documento_referencia | str | "" | E07 | E07 |
| responsable | str | "" | E08 | E08 |
| magnitudes | list[Magnitud] | field(default_factory=list) | E09, E10 | E09, E10 |
| puntos | list[Punto] | field(default_factory=list) | E11 | E11 |
| tecnicos | list[Recurso] | field(default_factory=list) | R01 | R01 |
| patrones | list[Recurso] | field(default_factory=list) | R02, R03 | R02, R03 |
| equipos | list[Recurso] | field(default_factory=list) | R04 | R04 |
| ibcs | list[Recurso] | field(default_factory=list) |  | Equipo a evaluar (IBC); agregado a solicitud del equipo |
| factores | list[Factor] | field(default_factory=list) | D03, D04, D15 | D03, D04, D15 |
| condiciones_controladas | str | "" | D05 | D05 |
| agrupacion | list[str] | field(default_factory=lambda: ["punto"]) | D06 | D06: claves que forman grupos comparables |
| repeticiones_por_condicion | int | 2 | D07 | D07 (valor por defecto del planificador, editable por fila) |
| unidad_experimental | str | "" | D08 | D08 (pendiente técnico) |
| restricciones | list[Restriccion] | field(default_factory=list) | D11 | D11 |
| variables | list[Variable] | field(default_factory=list) | D12-D14 | D12-D14 |
| resultados | list[ResultadoInteres] | field(default_factory=list) | V01-V10 | V01-V10 |
| criterios | list[Criterio] | field(default_factory=list) | C01-C03 | C01-C03 |
| periodo_inicio | str | "" | P01 | P01 |
| periodo_fin | str | "" | P01 | P01 |
| plan | list[MedicionPlanificada] | field(default_factory=list) | D09, D10, P02-P04 | D09, D10, P02-P04 |
| version_diseno | int | 0 | P05 | P05 · 0 = nunca aprobado |
| estado | str | "borrador" | P05 | P05 · borrador \| aprobado |
| aprobado_por | str | "" | P05 | P05 |
| fecha_aprobacion | str | "" | P05 | P05 |
| creado_en | str | "" |  |  |
| actualizado_en | str | "" |  |  |
| paso_asistente | int | 1 |  | último paso abierto del asistente de creación (no forma parte del diseño) |
| derivado_de | str | "" |  | «EST-0001 v2» si se creó con «Clonar estudio» (rediseño) |

## Magnitud

Magnitud e intervalo de trabajo.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear |  | MAG-01, generado |
| nombre | str | obligatorio al crear | E09 | E09 |
| unidad | str | obligatorio al crear | E09 | E09 |
| intervalo_min | float \| None | None | E10 | E10 |
| intervalo_max | float \| None | None | E10 | E10 |

## Punto

Punto nominal de medición.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear |  | PT-01, generado |
| magnitud_id | str | obligatorio al crear |  |  |
| valor_nominal | float | obligatorio al crear |  |  |
| unidad | str | obligatorio al crear |  |  |

## Recurso

Técnico, patrón o equipo.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| codigo | str | obligatorio al crear |  | T-01, P-01, EQ-01, IBC-01 (lo escribe el usuario) |
| nombre | str | "" |  |  |
| tipo | str | "tecnico" |  | tecnico \| patron \| equipo \| ibc |
| magnitud_id | str | "" | R03 | R03 (patrones e IBC) |
| intervalo_min | float \| None | None | R03 | R03 intervalo útil del patrón / intervalo del IBC |
| intervalo_max | float \| None | None |  |  |
| descripcion | str | "" |  |  |
| marca | str | "" |  | patrón / IBC |
| modelo | str | "" |  | patrón / IBC |
| serie | str | "" |  | patrón / IBC |
| resolucion | str | "" |  | IBC (texto: se registra tal como figura en el equipo) |
| certificado | str | "" |  | patrón: certificado de calibración vigente |

## Factor

Condición que se compara o se registra (factor experimental).

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear |  | F-01, generado |
| nombre | str | obligatorio al crear | D03 | D03 |
| descripcion | str | "" |  |  |
| tipo_valor | str | "categorico" | D04 | D04 |
| unidad | str | "" |  |  |
| niveles | list[str] | field(default_factory=list) | D04 | D04 |
| vinculo_recurso | str | "ninguno" |  | si el factor es técnico/patrón/equipo, sus niveles vienen del catálogo |
| rol | str | "se_compara" | D15 | D15: se cambia para comparar o solo se registra |

## Restriccion

Combinación no permitida.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| campo_a | str | obligatorio al crear |  | p. ej. "patron" o "F-02" |
| valor_a | str | obligatorio al crear |  |  |
| campo_b | str | obligatorio al crear |  |  |
| valor_b | str | obligatorio al crear |  |  |
| motivo | str | "" |  |  |

## Variable

Dato experimental que se registra.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear |  | V-01, generado (clave técnica estable) |
| nombre | str | obligatorio al crear |  |  |
| tipo_dato | str | "decimal" |  |  |
| unidad | str | "" |  |  |
| obligatoria | bool | True |  |  |
| descripcion | str | "" |  |  |
| categoria | str | "lectura" |  |  |

## ResultadoInteres

Definición de un resultado de interés (no su valor).

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear | V10 | V10: R-01, generado |
| nombre | str | obligatorio al crear | V01 | V01 |
| proposito | str | "exigido_por_el_metodo" | V02 | V02 |
| referencia_proposito | str | "" | V02 | V02 |
| unidad | str | "" | V03 | V03 ("" = no aplica) |
| origen | str | "calculado" | V04 | V04 |
| dependencias | list[str] | field(default_factory=list) | V05 | V05: ids de variables u otros resultados |
| referencia_calculo | str | "" | V06 | V06: referencia/versión del procedimiento (no fórmula) |
| ambito | str | "medicion" | V07 | V07 |
| analizar | bool | False | V08 | V08 |
| tiene_criterio | bool | False | V09 | V09 |

## Criterio

Criterio de evaluación vinculado a un resultado.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| id | str | obligatorio al crear |  | C-01, generado |
| resultado_id | str | obligatorio al crear | C01 | C01 |
| descripcion | str | "" | C01 | C01 |
| fuente | str | "" | C02 | C02 |
| version_fuente | str | "" | C02 | C02 |
| operador | str | "" | C03 | C03 (libre; no se impone) |
| valor | str | "" | C03 | C03 (texto: no se interpreta en esta fase) |
| unidad | str | "" | C03 | C03 |
| condiciones | str | "" | C03 | C03 |
| aprobado | bool | False |  | se aprueba antes de analizar |

## MedicionPlanificada

Medición prevista en el plan aprobado.

| Campo | Tipo | Valor por defecto | Campo(s) de la matriz | Nota |
| --- | --- | --- | --- | --- |
| medicion_id | str | obligatorio al crear |  | M0001, generado |
| punto_id | str | obligatorio al crear |  |  |
| repeticion | int | obligatorio al crear |  |  |
| niveles | dict[str, str] | field(default_factory=dict) |  | factor_id -> nivel (solo factores sin vínculo a recurso) |
| tecnico | str | "" | P02 | P02 |
| patron | str | "" | P03 | P03 |
| equipo | str | "" | R04 | R04 |
| fecha_planificada | str | "" | P04, D16 | P04 / D16 (ISO yyyy-mm-dd) |
| franja_planificada | str | "" | P04 | P04 |
| orden | int \| None | None | D10 | D10 |

## Dominios (listas cerradas)

| Campo | Valores permitidos |
| --- | --- |
| Estudio.tipo | Verificación, Validación |
| Variable.tipo_dato | decimal, entero, texto, fecha, si_no |
| Variable.categoria | lectura, dato_del_metodo, ambiental |
| Factor.tipo_valor | categorico, numerico |
| Factor.vinculo_recurso | ninguno, tecnico, patron, equipo |
| Factor.rol | se_compara, solo_se_registra |
| ResultadoInteres.origen | directo, calculado |
| ResultadoInteres.ambito | medicion, serie, punto, condicion, estudio, otro |
| ResultadoInteres.proposito | exigido_por_el_metodo, objetivo_del_estudio |
| Estudio.estado | borrador, aprobado |
