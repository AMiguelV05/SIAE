from datetime import date

import pandas as pd
import pytest

from siae_ml.sintetico import generar
from siae_ml.sintetico import calendario, matricula
from siae_ml.sintetico.catalogos import CUPOS, RETENCION, SEMESTRES, TEMAS


@pytest.fixture(scope="module")
def resultado():
    return generar()


def test_dimensiones(resultado):
    series = resultado.series
    assert series.groupby(["carrera", "tema"]).ngroups == 73
    assert series["semana"].nunique() == 208
    assert (series["semana"].dt.dayofweek == 0).all()
    assert series.groupby("particion")["semana"].nunique().to_dict() == {
        "entrenamiento": 104, "validacion": 52, "prueba": 52}


def test_misma_semilla_mismos_datos():
    primera, segunda = generar(semilla=7), generar(semilla=7)
    pd.testing.assert_frame_equal(primera.series, segunda.series)
    assert not primera.series["conversaciones"].equals(generar(semilla=8).series["conversaciones"])


def test_conteos_validos(resultado):
    series = resultado.series
    assert (series["conversaciones"] >= 0).all()
    assert pd.api.types.is_integer_dtype(series["conversaciones"])


def test_volumen_coincide_con_supuestos(resultado):
    series = resultado.series
    estables = ["ICOM", "INFO", "INRO", "INBI", "FOTONICA"]
    alumnos = sum(CUPOS[carrera] for carrera in estables) * SEMESTRES * RETENCION
    propios = sum(tema.peso for tema in TEMAS if not tema.general) / sum(tema.peso for tema in TEMAS)
    esperado_anual = alumnos * 0.15 * 3 * 2 * propios
    real_anual = series.loc[series["carrera"].isin(estables), "esperado"].sum() / 4
    assert real_anual == pytest.approx(esperado_anual, rel=0.08)


def test_ines_sustituye_a_ince():
    assert matricula.por_semestre("INES", "2024-B").sum() == 0
    assert matricula.por_semestre("INCE", "2025-A")[0] == 0
    assert matricula.por_semestre("INES", "2025-B")[:2].tolist() == [130 * RETENCION] * 2


def test_ines_no_pregunta_por_titulacion(resultado):
    series = resultado.series
    ines = series[(series["carrera"] == "INES") & (series["tema"] == "titulacion")]
    assert ines["esperado"].sum() < 0.1 * ines["esperado"].size


def test_picos_de_agenda_en_registro_o_inicio(resultado):
    # Las dudas de agenda se concentran alrededor del autorregistro y del inicio de clases.
    series = resultado.series
    agenda = series[(series["carrera"] == "ICOM") & (series["tema"] == "agenda")
                    & (series["particion"] == "validacion")]
    fechas = []
    for ciclo in calendario.ciclos():
        fechas += [pd.Timestamp(ciclo.inicio), pd.Timestamp(calendario.registro(ciclo).autorregistro[0])]
    for semana in agenda.nlargest(6, "esperado")["semana"]:
        assert min(abs((semana - fecha).days) for fecha in fechas) <= 14, semana


def test_pascua():
    assert calendario.pascua(2026) == date(2026, 4, 5)
    inicio, fin = calendario.vacaciones(2026)[0]
    assert (inicio, fin) == (date(2026, 3, 30), date(2026, 4, 12))


def test_semana_santa_coincide_con_calendarios_oficiales():
    oficiales = {2022: date(2022, 4, 11), 2023: date(2023, 4, 3), 2024: date(2024, 3, 25),
                 2025: date(2025, 4, 14), 2026: date(2026, 3, 30), 2027: date(2027, 3, 22)}
    for anio, inicio in oficiales.items():
        assert calendario.vacaciones(anio)[0][0] == inicio, anio


def test_regla_de_verano_coincide_con_calendarios_oficiales():
    # La regla de respaldo (primer miércoles desde el 14 de julio, 18 días) simula los años conocidos.
    for anio, periodo in calendario.VERANO.items():
        inicio = calendario._miercoles_desde_14_de_julio(anio)
        assert (inicio, inicio + pd.Timedelta(days=18).to_pytimedelta()) == periodo, anio


def test_registro_conocido_y_por_regla():
    ciclos = {ciclo.clave: ciclo for ciclo in calendario.ciclos()}
    assert calendario.registro(ciclos["2024-B"]).autorregistro[0] == date(2024, 6, 12)
    futuro = calendario.Ciclo("2028-B", date(2028, 8, 14), date(2028, 12, 8))
    regla = calendario.registro(futuro)
    assert regla.autorregistro[0] == date(2028, 6, 12)
    assert regla.modificaciones[1] < futuro.inicio


def test_egel_conocido_y_por_regla():
    ciclos = {ciclo.clave: ciclo for ciclo in calendario.ciclos()}
    assert calendario.egel(ciclos["2026-A"]).aplicacion == (date(2026, 5, 9), date(2026, 5, 9))
    # Las reglas reproducen los ciclos de los que salieron.
    for clave in ["2024-B", "2025-A"]:
        conocido = calendario.EGEL.pop(clave)
        try:
            assert calendario.egel(ciclos[clave]) == conocido, clave
        finally:
            calendario.EGEL[clave] = conocido


def test_semana_ciclo_empieza_en_uno(resultado):
    series = resultado.series
    inicio = series[(series["ciclo"] == "2024-B")]["semana"].min()
    assert inicio == pd.Timestamp("2024-08-12")
    assert series.loc[series["semana"] == inicio, "semana_ciclo"].unique().tolist() == [1]


def test_eventos_formato_academic_events(resultado):
    eventos = resultado.eventos
    assert {"tema", "ciclo", "tipo", "inicio", "fin", "altura"} <= set(eventos.columns)
    assert (eventos["fin"] >= eventos["inicio"]).all()
    assert (eventos["tipo"] == "convocatoria_extra").sum() == len(calendario.ciclos())
