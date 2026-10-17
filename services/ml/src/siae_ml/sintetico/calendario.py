from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd


INICIOS = {
    "2022-B": date(2022, 8, 11),
    "2023-A": date(2023, 1, 16),
    "2023-B": date(2023, 8, 14),
    "2024-A": date(2024, 1, 16),
    "2024-B": date(2024, 8, 12),
    "2025-A": date(2025, 1, 16),
    "2025-B": date(2025, 8, 11),
    "2026-A": date(2026, 1, 19),
    "2026-B": date(2026, 8, 17),
    "2027-A": date(2027, 1, 18),
}
FIN_CLASES = {
    "2022-B": date(2022, 12, 9),
    "2023-A": date(2023, 5, 31),
    "2023-B": date(2023, 12, 15),
    "2024-A": date(2024, 5, 25),
    "2024-B": date(2024, 12, 7),
    "2025-A": date(2025, 5, 23),
    "2025-B": date(2025, 12, 9),
    "2026-A": date(2026, 5, 29),
    "2026-B": date(2026, 12, 11),
    "2027-A": date(2027, 5, 28),
}
DURACION_CLASES = timedelta(days=117)  # aproximado para ciclos sin datos

# Vacaciones de verano e invierno
VERANO = {
    2022: (date(2022, 7, 20), date(2022, 8, 7)),
    2023: (date(2023, 7, 19), date(2023, 8, 6)),
    2024: (date(2024, 7, 17), date(2024, 8, 4)),
    2025: (date(2025, 7, 16), date(2025, 8, 3)),
    2026: (date(2026, 7, 15), date(2026, 8, 2)),
    2027: (date(2027, 7, 14), date(2027, 8, 1)),
}
INVIERNO = {
    2022: (date(2022, 12, 17), date(2023, 1, 4)),
    2023: (date(2023, 12, 16), date(2024, 1, 3)),
    2024: (date(2024, 12, 18), date(2025, 1, 5)),
    2025: (date(2025, 12, 20), date(2026, 1, 7)),
    2026: (date(2026, 12, 19), date(2027, 1, 6)),
    2027: (date(2027, 12, 18), date(2028, 1, 5)),
}

# Examen de ingreso y publicación de resultados
EXAMEN_INGRESO = {
    "2022-B": date(2022, 5, 21),
    "2023-B": date(2023, 5, 20),
    "2026-B": date(2026, 5, 23),
}
RESULTADOS_INGRESO = {
    "2022-B": date(2022, 8, 11),
    "2023-A": date(2023, 1, 9),
    "2023-B": date(2023, 8, 9),
    "2024-A": date(2024, 1, 8),
    "2024-B": date(2024, 8, 7),
    "2025-A": date(2025, 1, 13),
    "2025-B": date(2025, 8, 5),
    "2026-B": date(2026, 8, 10),
}

# Pago de matrícula de reingreso y nuevo ingreso
PAGO_MATRICULA = {
    "2022-B": (date(2022, 8, 11), date(2022, 9, 15)),
    "2023-A": (date(2023, 1, 16), date(2023, 2, 16)),
    "2023-B": (date(2023, 8, 14), date(2023, 9, 17)),
    "2024-A": (date(2024, 1, 16), date(2024, 2, 16)),
    "2024-B": (date(2024, 8, 12), date(2024, 9, 16)),
    "2025-A": (date(2025, 1, 16), date(2025, 2, 17)),
}


@dataclass(frozen=True)
class Egel:
    """Examen General para el Egreso CENEVAL."""
    registro: tuple[date, date]
    aplicacion: tuple[date, date]


EGEL = {
    "2024-B": Egel((date(2025, 1, 10), date(2025, 1, 21)), (date(2025, 3, 28), date(2025, 4, 4))),
    "2025-A": Egel((date(2025, 5, 6), date(2025, 5, 31)), (date(2025, 8, 29), date(2025, 9, 5))),
    "2026-A": Egel((date(2026, 3, 9), date(2026, 3, 25)), (date(2026, 5, 9), date(2026, 5, 9))),
    "2026-B": Egel((date(2026, 8, 24), date(2026, 9, 20)), (date(2026, 10, 24), date(2026, 10, 24))),
}


@dataclass(frozen=True)
class Registro:
    """Registro de materias de DIVTIC."""
    autorregistro: tuple[date, date] 
    ajuste: date                       # ajuste de materias en SIIAU
    modificaciones: tuple[date, date]  # modificaciones por coordinador de carrera
    primer_ingreso: date               # autorregistro de nuevo ingreso


REGISTRO = {
    "2022-B": Registro((date(2022, 6, 9), date(2022, 6, 10)), date(2022, 6, 17),
                       (date(2022, 6, 20), date(2022, 6, 24)), date(2022, 8, 13)),
    "2023-A": Registro((date(2022, 12, 15), date(2022, 12, 16)), date(2023, 1, 7),
                       (date(2023, 1, 9), date(2023, 1, 13)), date(2023, 1, 13)),
    "2023-B": Registro((date(2023, 6, 16), date(2023, 6, 16)), date(2023, 6, 19),
                       (date(2023, 6, 20), date(2023, 6, 23)), date(2023, 8, 11)),
    "2024-A": Registro((date(2024, 1, 11), date(2024, 1, 11)), date(2024, 1, 12),
                       (date(2024, 1, 15), date(2024, 1, 19)), date(2024, 1, 11)),
    "2024-B": Registro((date(2024, 6, 12), date(2024, 6, 12)), date(2024, 6, 14),
                       (date(2024, 6, 17), date(2024, 6, 22)), date(2024, 8, 9)),
    "2025-A": Registro((date(2025, 1, 8), date(2025, 1, 8)), date(2025, 1, 9),
                       (date(2025, 1, 10), date(2025, 1, 11)), date(2025, 1, 15)),
    "2025-B": Registro((date(2025, 6, 17), date(2025, 6, 17)), date(2025, 6, 19),
                       (date(2025, 6, 23), date(2025, 6, 27)), date(2025, 8, 8)),
    "2026-A": Registro((date(2026, 1, 13), date(2026, 1, 13)), date(2026, 1, 14),
                       (date(2026, 1, 14), date(2026, 1, 16)), date(2026, 1, 16)),
    "2026-B": Registro((date(2026, 6, 16), date(2026, 6, 16)), date(2026, 6, 18),
                       (date(2026, 6, 22), date(2026, 6, 26)), date(2026, 8, 12)),
    "2027-A": Registro((date(2027, 1, 11), date(2027, 1, 11)), date(2027, 1, 12),
                       (date(2027, 1, 12), date(2027, 1, 15)), date(2027, 1, 15)),
}

ACTIVIDAD_CLASES = 1.0
ACTIVIDAD_INTERSEMESTRE = 0.4
ACTIVIDAD_VACACIONES = 0.1
FACTOR_FIN_DE_SEMANA = 0.35


@dataclass(frozen=True)
class Ciclo:
    clave: str
    inicio: date
    fin_clases: date

    @property
    def anio(self) -> int:
        return int(self.clave[:4])

    @property
    def letra(self) -> str:
        return self.clave[-1]

    @property
    def indice(self) -> int:
        return indice_ciclo(self.clave)


def indice_ciclo(clave: str) -> int:
    """Número consecutivo del ciclo: 2024-A → 4048, 2024-B → 4049."""
    return int(clave[:4]) * 2 + (clave[-1] == "B")


def ciclos() -> list[Ciclo]:
    lista_ciclos = []
    for clave, inicio in INICIOS.items():
        fin = FIN_CLASES.get(clave)
        if fin is None:
            # Se agrega semana santa a los ciclos A
            semana_santa = timedelta(days=14) if clave.endswith("A") else timedelta(0)
            fin = inicio + DURACION_CLASES + semana_santa
        lista_ciclos.append(Ciclo(clave, inicio, fin))
    return lista_ciclos


def pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo anónimo gregoriano)."""
    ciclo_lunar, siglo, anio_del_siglo = anio % 19, anio // 100, anio % 100
    bisiestos_siglo, resto_siglo = siglo // 4, siglo % 4
    ajuste_lunar = (siglo + 8) // 25
    correccion_lunar = (siglo - ajuste_lunar + 1) // 3
    epacta = (19 * ciclo_lunar + siglo - bisiestos_siglo - correccion_lunar + 15) % 30
    bisiestos_anio, resto_anio = anio_del_siglo // 4, anio_del_siglo % 4
    dias_a_domingo = (32 + 2 * resto_siglo + 2 * bisiestos_anio - epacta - resto_anio) % 7
    correccion_final = (ciclo_lunar + 11 * epacta + 22 * dias_a_domingo) // 451
    mes = (epacta + dias_a_domingo - 7 * correccion_final + 114) // 31
    dia = (epacta + dias_a_domingo - 7 * correccion_final + 114) % 31 + 1
    return date(anio, mes, dia)


def vacaciones(anio: int) -> list[tuple[date, date]]:
    """Periodos vacacionales que empiezan en el año: primavera, verano e invierno."""
    domingo_pascua = pascua(anio)
    inicio_verano = _miercoles_desde_14_de_julio(anio)
    return [
        (domingo_pascua - timedelta(days=6), domingo_pascua + timedelta(days=7)),
        VERANO.get(anio, (inicio_verano, inicio_verano + timedelta(days=18))),
        INVIERNO.get(anio, (date(anio, 12, 18), date(anio + 1, 1, 5))),
    ]


def actividad(dias: pd.DatetimeIndex, lista_ciclos: list[Ciclo]) -> np.ndarray:
    """Nivel de actividad escolar por día (clases, intersemestre o vacaciones)."""
    nivel = np.full(len(dias), ACTIVIDAD_INTERSEMESTRE)
    for ciclo in lista_ciclos:
        nivel[(dias >= pd.Timestamp(ciclo.inicio)) & (dias <= pd.Timestamp(ciclo.fin_clases))] = ACTIVIDAD_CLASES
    for anio in range(dias[0].year - 1, dias[-1].year + 1):
        for inicio, fin in vacaciones(anio):
            nivel[(dias >= pd.Timestamp(inicio)) & (dias <= pd.Timestamp(fin))] = ACTIVIDAD_VACACIONES
    nivel = nivel * np.where(dias.dayofweek >= 5, FACTOR_FIN_DE_SEMANA, 1.0)
    return nivel


def ciclo_de(dias: pd.DatetimeIndex, lista_ciclos: list[Ciclo]) -> np.ndarray:
    """Clave del ciclo vigente por día: el último que ya inició."""
    inicios = pd.DatetimeIndex([pd.Timestamp(ciclo.inicio) for ciclo in lista_ciclos])
    posiciones = inicios.searchsorted(dias, side="right") - 1
    if (posiciones < 0).any():
        raise ValueError("Hay días anteriores al primer ciclo del calendario")
    return np.array([lista_ciclos[posicion].clave for posicion in posiciones])


def _tercer_sabado_de_mayo(anio: int) -> date:
    dia = date(anio, 5, 1)
    dia += timedelta(days=(5 - dia.weekday()) % 7)
    return dia + timedelta(weeks=2)


def _miercoles_desde_14_de_julio(anio: int) -> date:
    dia = date(anio, 7, 14)
    return dia + timedelta(days=(2 - dia.weekday()) % 7)


def _fin_de_febrero(anio: int) -> date:
    return date(anio, 3, 1) - timedelta(days=1)


def _dias(cantidad: int) -> timedelta:
    return timedelta(days=cantidad)


def registro(ciclo: Ciclo) -> Registro:
    """Fechas del registro de materias del ciclo, conocidas o por regla."""
    if ciclo.clave in REGISTRO:
        return REGISTRO[ciclo.clave]
    # Reingreso: 9 semanas antes del inicio en ciclos B y 8 días antes en ciclos A
    autorregistro = ciclo.inicio - (_dias(63) if ciclo.letra == "B" else _dias(8))
    return Registro((autorregistro, autorregistro), autorregistro + _dias(2),
                    (autorregistro + _dias(3), autorregistro + _dias(8)),
                    ciclo.inicio - _dias(3))


def egel(ciclo: Ciclo) -> Egel:
    """Fechas del EGEL del ciclo, conocidas o por regla."""
    if ciclo.clave in EGEL:
        return EGEL[ciclo.clave]
    # Ciclos sin dato 17 y 8 semanas después del fin de clases para registro y aplicación, respectivamente
    fin = ciclo.fin_clases
    if ciclo.letra == "B":
        return Egel((fin + _dias(34), fin + _dias(45)), (fin + _dias(111), fin + _dias(118)))
    return Egel((fin - _dias(17), fin + _dias(8)), (fin + _dias(98), fin + _dias(105)))


def eventos_academicos(lista_ciclos: list[Ciclo], rng: np.random.Generator) -> pd.DataFrame:
    """Eventos por tema y ciclo con su altura relativa sobre la base del tema.
    Un evento sube durante los 7 días antes del inicio del evento, se
    mantiene hasta el fin y baja en 3 días. Las convocatorias extra de becas se
    sortean con `rng`.
    """
    filas = []

    def evento(tema, ciclo, tipo, inicio, fin, altura):
        filas.append(dict(tema=tema, ciclo=ciclo.clave, tipo=tipo,
                          inicio=inicio, fin=fin, altura=altura))

    for ciclo in lista_ciclos:
        inicio, fin, anio = ciclo.inicio, ciclo.fin_clases, ciclo.anio
        es_ciclo_a = ciclo.letra == "A"

        if es_ciclo_a:
            evento("becas", ciclo, "convocatoria", date(anio, 2, 1), date(anio, 3, 15), 1.8)
        else:
            evento("becas", ciclo, "convocatoria", date(anio, 8, 15), date(anio, 9, 30), 1.8)
        # Colocamos una convocatoria extra de becas en ciclos B, entre la primera y la segunda mitad del ciclo.
        inicio_extra = inicio + _dias(int(rng.integers(21, (fin - inicio).days - 42)))
        evento("becas", ciclo, "convocatoria_extra", inicio_extra, inicio_extra + _dias(21), 0.9)

        evento("modular", ciclo, "registro", inicio, inicio + _dias(20), 2.5)
        evento("modular", ciclo, "presentacion", fin - _dias(20), fin, 2.5)

        materias = registro(ciclo)
        evento("agenda", ciclo, "autorregistro",
               materias.autorregistro[0] - _dias(1), materias.autorregistro[1], 4.0)
        evento("agenda", ciclo, "ajuste_y_modificaciones", materias.ajuste, materias.modificaciones[1], 2.5)
        evento("agenda", ciclo, "primer_ingreso", materias.primer_ingreso, materias.primer_ingreso, 2.0)
        evento("agenda", ciclo, "inicio_de_clases", inicio, inicio + _dias(13), 1.5)

        evento("titulacion", ciclo, "tramite_fin_de_ciclo", fin - _dias(28), fin + _dias(14), 1.2)

        evento("justificantes", ciclo, "parciales", inicio + _dias(42), inicio + _dias(49), 0.6)
        evento("justificantes", ciclo, "finales", fin - _dias(10), fin, 0.8)

        # Servicio social
        if es_ciclo_a:
            evento("servicio_social", ciclo, "registro", date(anio - 1, 11, 20), date(anio, 1, 13), 1.0)
            evento("servicio_social", ciclo, "cierre_registro", date(anio, 1, 6), date(anio, 1, 13), 1.5)
            evento("servicio_social", ciclo, "publicacion_agenda", date(anio, 2, 3), date(anio, 2, 3), 3.0)
            evento("servicio_social", ciclo, "seleccion_plazas", date(anio, 3, 1), date(anio, 3, 7), 3.5)
        else:
            evento("servicio_social", ciclo, "registro", date(anio, 5, 20), date(anio, 7, 13), 1.0)
            evento("servicio_social", ciclo, "cierre_registro", date(anio, 7, 6), date(anio, 7, 13), 1.5)
            evento("servicio_social", ciclo, "publicacion_agenda", date(anio, 8, 3), date(anio, 8, 3), 3.0)
            evento("servicio_social", ciclo, "seleccion_plazas", date(anio, 9, 1), date(anio, 9, 7), 3.5)

        evento("practicas", ciclo, "registro", inicio, inicio + _dias(28), 1.0)

        # Acreditación de inglés
        acreditacion = inicio + _dias(49)
        while acreditacion <= fin:
            evento("ingles", ciclo, "acreditacion", acreditacion, acreditacion + _dias(2), 1.5)
            acreditacion += _dias(28)

        examen_egreso = egel(ciclo)
        evento("ceneval", ciclo, "registro_egel", examen_egreso.registro[0], examen_egreso.registro[1], 1.5)
        evento("ceneval", ciclo, "aplicacion_egel",
               examen_egreso.aplicacion[0], examen_egreso.aplicacion[1], 2.0)

        evento("servicios_institucionales", ciclo, "inicio_de_ciclo", inicio - _dias(7), inicio + _dias(14), 0.8)
        fin_pago = PAGO_MATRICULA.get(ciclo.clave, (inicio, inicio + _dias(32)))[1]
        evento("servicios_institucionales", ciclo, "cierre_pago_matricula", fin_pago - _dias(6), fin_pago, 1.2)

        # Ingreso
        if es_ciclo_a:
            evento("ingreso", ciclo, "registro_aspirantes", date(anio - 1, 9, 1), date(anio - 1, 9, 30), 2.0)
            evento("ingreso", ciclo, "examen", date(anio - 1, 11, 15), date(anio - 1, 11, 15), 2.5)
        else:
            evento("ingreso", ciclo, "registro_aspirantes", date(anio, 2, 1), _fin_de_febrero(anio), 2.0)
            examen = EXAMEN_INGRESO.get(ciclo.clave, _tercer_sabado_de_mayo(anio))
            evento("ingreso", ciclo, "examen", examen, examen, 2.5)
        resultados = RESULTADOS_INGRESO.get(ciclo.clave, inicio - _dias(7))
        evento("ingreso", ciclo, "resultados", resultados, resultados, 4.0)

        evento("egreso", ciclo, "fin_de_ciclo", fin - _dias(14), fin + _dias(35), 2.0)

    eventos = pd.DataFrame(filas)
    # Aleatoriedad entre ciclos
    eventos["altura"] = (eventos["altura"] * rng.lognormal(0.0, 0.15, len(eventos))).round(3)
    eventos["inicio"] = pd.to_datetime(eventos["inicio"])
    eventos["fin"] = pd.to_datetime(eventos["fin"])
    return eventos


def trapecio(dias: pd.DatetimeIndex, inicio: pd.Timestamp, fin: pd.Timestamp,
             subida: int = 7, bajada: int = 3) -> np.ndarray:
    """1 entre inicio y fin, con rampas lineales antes y después."""
    desde_inicio = (dias - inicio).days.to_numpy(dtype=float)
    duracion = (fin - inicio).days
    forma = np.zeros(len(dias))
    forma = np.where((desde_inicio >= -subida) & (desde_inicio < 0), 1 + desde_inicio / subida, forma)
    forma = np.where((desde_inicio >= 0) & (desde_inicio <= duracion), 1.0, forma)
    forma = np.where((desde_inicio > duracion) & (desde_inicio <= duracion + bajada),
                     1 - (desde_inicio - duracion) / bajada, forma)
    return forma
