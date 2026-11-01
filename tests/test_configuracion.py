"""Configuración, planificación, versiones y persistencia del estudio."""

import pytest

from src.configuracion.validacion_estudio import listo_para_aprobar, revisar_estudio
from src.modelos.estudio import Factor, Magnitud, Punto, Recurso, Restriccion, ResultadoInteres, Variable
from src.persistencia.repositorio import RepositorioLocal
from src.planificacion.plan import generar_combinaciones, importar_plan, plan_a_dataframe, plan_desde_dataframe, validar_plan
from src.plantillas.generador import ErrorPlantilla, generar_plantilla
from src.servicios.demo import construir_estudio_demo


def test_guardar_y_recuperar_estudio(repo):
    """Entrada: estudio creado, configurado con el ejemplo y guardado.
    Esperado: al leerlo de nuevo conserva identificación, recursos, factores, variables, resultados y plan; el código es automático (EST-0001)."""
    base = repo.crear_estudio("Mi estudio", "ana")
    assert base.codigo == "EST-0001"
    e = construir_estudio_demo(base.codigo, base.nombre)
    repo.guardar_estudio(e, "ana")
    leido = repo.obtener_estudio("EST-0001")
    assert leido.to_dict() == {**e.to_dict(), "actualizado_en": leido.actualizado_en}
    assert [ev["accion"] for ev in repo.leer_eventos("EST-0001")] == ["estudio_creado", "estudio_guardado"]


def test_persistencia_entre_sesiones(tmp_path):
    """Entrada: un estudio guardado con una instancia del repositorio; se crea otra instancia sobre la misma carpeta.
    Esperado: la segunda instancia (otra sesión) lista y lee el estudio y su versión aprobada."""
    r1 = RepositorioLocal(tmp_path)
    e = construir_estudio_demo(r1.crear_estudio("Persistente", "ana").codigo, "Persistente")
    r1.guardar_estudio(e, "ana")
    r1.aprobar_version(e, "ana")
    r2 = RepositorioLocal(tmp_path)
    assert [x["codigo"] for x in r2.listar_estudios()] == [e.codigo]
    version, huella = r2.obtener_version(e.codigo, 1)
    assert version.plan == e.plan and len(huella) == 64


def test_cantidades_variables_de_recursos_puntos_y_condiciones():
    """Entrada: 3 técnicos, 1 patrón, 2 equipos, 5 puntos y 3 condiciones (una numérica).
    Esperado: la configuración es válida sin asumir dos técnicos ni dos patrones."""
    e = construir_estudio_demo()
    e.tecnicos = [Recurso(f"T-0{i}", tipo="tecnico") for i in range(1, 4)]
    e.patrones = [Recurso("P-01", tipo="patron", magnitud_id="MAG-01", intervalo_min=-50, intervalo_max=200)]
    e.equipos = [Recurso("EQ-01", tipo="equipo"), Recurso("EQ-02", tipo="equipo")]
    e.puntos = [Punto(f"PT-0{i}", "MAG-01", v, "°C") for i, v in enumerate([0, 20, 40, 60, 80], start=1)]
    e.factores.append(Factor("F-03", "Carga del medio", tipo_valor="numerico", unidad="kg", niveles=["0", "5"]))
    e.plan = generar_combinaciones(e, [p.id for p in e.puntos],
                                   {"tecnico": ["T-01", "T-02", "T-03"], "F-02": ["Día 1"], "F-03": ["0", "5"]},
                                   repeticiones=3, fijos={"patron": "P-01", "equipo": "EQ-01"})
    assert len(e.plan) == 5 * 3 * 1 * 2 * 3
    ok, faltantes = listo_para_aprobar(e)
    assert ok, faltantes


def test_no_se_genera_factorial_automaticamente():
    """Entrada: estudio con factores y niveles configurados pero sin filas de plan.
    Esperado: el plan sigue vacío y la revisión exige planificar explícitamente las mediciones."""
    e = construir_estudio_demo()
    e.plan = []
    plan = next(x for x in revisar_estudio(e) if x.clave == "plan")
    assert e.plan == [] and plan.faltantes == ["Al menos una medición planificada (D09)"]


def test_generador_explicito_solo_cruza_lo_elegido():
    """Entrada: generador con 2 puntos, cruzando solo «Día» y con técnico fijo T-01.
    Esperado: 2 × 2 × 2 = 8 mediciones; el técnico no se cruza."""
    e = construir_estudio_demo()
    e.plan = []
    nuevas = generar_combinaciones(e, ["PT-01", "PT-02"], {"F-02": ["Día 1", "Día 2"]}, 2, fijos={"tecnico": "T-01", "patron": "P-01"})
    assert len(nuevas) == 8 and {m.tecnico for m in nuevas} == {"T-01"}


def test_puntos_distintos_no_son_repeticiones_y_duplicados_se_detectan():
    """Entrada: plan con la repetición 1 en dos puntos distintos (válido) y luego una repetición 1 duplicada en la misma condición.
    Esperado: el primer caso no genera error; el segundo informa la repetición duplicada."""
    e = construir_estudio_demo()
    errores, _ = validar_plan(e)
    assert errores == []
    duplicada = e.plan[1]
    duplicada.repeticion = 1  # M0002 pasa a ser repetición 1 igual que M0001
    errores, _ = validar_plan(e)
    assert any("La repetición 1 aparece 2 veces" in x for x in errores)


def test_restriccion_de_combinacion_bloquea():
    """Entrada: restricción «T-02 no puede usar P-01» (D11).
    Esperado: las filas que la violan aparecen como error."""
    e = construir_estudio_demo()
    e.restricciones = [Restriccion("tecnico", "T-02", "patron", "P-01", "Sin autorización")]
    errores, _ = validar_plan(e)
    assert sum("combinación no permitida" in x for x in errores) == 8


def test_patron_fuera_de_intervalo_advierte():
    """Entrada: patrón con intervalo útil 0–30 °C y un punto de 40 °C.
    Esperado: advertencia de compatibilidad (PD06 pendiente: no bloquea)."""
    e = construir_estudio_demo()
    e.patrones[0].intervalo_max = 30
    errores, advertencias = validar_plan(e)
    assert errores == [] and any("fuera del intervalo útil" in a for a in advertencias)


def test_tabla_editable_ida_y_vuelta():
    """Entrada: plan convertido a la tabla del editor y de vuelta.
    Esperado: se obtiene exactamente el mismo plan."""
    e = construir_estudio_demo()
    plan, errores = plan_desde_dataframe(e, plan_a_dataframe(e))
    assert errores == [] and plan == e.plan


def test_importar_plan_csv():
    """Entrada: CSV con columnas Punto, Repetición, Técnico, Patrón, Día (sin IDs).
    Esperado: se crean mediciones con IDs nuevos y sin errores de lectura."""
    e = construir_estudio_demo()
    e.plan = []
    csv = "Punto;Repetición;Técnico;Patrón;Día\n20;1;T-01;P-01;Día 1\n20;2;T-01;P-01;Día 1\n40;1;T-02;P-01;Día 2\n"
    plan, errores = importar_plan(e, csv.encode("utf-8"), "plan.csv")
    assert errores == [] and [m.medicion_id for m in plan] == ["M0001", "M0002", "M0003"]
    assert plan[2].punto_id == "PT-02" and plan[2].niveles == {"F-02": "Día 2"}


def test_validaciones_de_configuracion_incompleta():
    """Entrada: estudio vacío y un resultado con el mismo nombre que un dato registrado.
    Esperado: la revisión lista lo que falta por etapa y no permite aprobar."""
    from src.modelos.estudio import Estudio
    e = Estudio(codigo="EST-X", nombre="")
    ok, faltantes = listo_para_aprobar(e)
    assert not ok and any("Nombre del estudio" in f for f in faltantes)
    d = construir_estudio_demo()
    d.resultados.append(ResultadoInteres("R-03", "Valor del patrón"))
    assert any("mismo nombre que un dato" in f for f in listo_para_aprobar(d)[1])


def test_versiones_del_diseno(repo):
    """Entrada: diseño aprobado (v1), luego modificado (otro punto) y aprobado de nuevo.
    Esperado: al modificar vuelve a borrador; la nueva aprobación crea v2 y v1 se conserva intacta."""
    e = construir_estudio_demo(repo.crear_estudio("V", "ana").codigo)
    repo.guardar_estudio(e, "ana")
    assert repo.aprobar_version(e, "ana") == 1
    e.puntos.append(Punto("PT-03", "MAG-01", 60.0, "°C"))
    repo.guardar_estudio(e, "ana")
    assert repo.obtener_estudio(e.codigo).estado == "borrador"
    with pytest.raises(ErrorPlantilla):
        generar_plantilla(repo.obtener_estudio(e.codigo))
    assert repo.aprobar_version(e, "ana") == 2
    v1, _ = repo.obtener_version(e.codigo, 1)
    assert len(v1.puntos) == 2 and [v["version"] for v in repo.listar_versiones(e.codigo)] == [1, 2]
