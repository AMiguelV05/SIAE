"""Generador de series semanales sintéticas de conversaciones nuevas por tema y carrera.

Volumen esperado de un día para la serie (carrera, tema):

    alumnos que cursan el tema * adopción * tasa diaria * participación del tema * perfil

El conteo diario sigue una binomial negativa (Poisson con media gamma) y se suma por
semana (lunes a domingo).
"""

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import calendario, matricula
from .catalogos import (ADOPCION_FINAL, ADOPCION_INICIAL, CARRERA_GENERAL, CARRERAS,
                        CONVERSACIONES_POR_SEMESTRE, INTERES_PREVIO, SEMESTRES, TEMAS, Tema)

INICIO = date(2022, 8, 15)
SEMANAS = 208                
SEMILLA = 2026
DISPERSION = 8.0             # forma de la gamma diaria
DESVIACION_AFINIDAD = 0.2    # variación del interés por tema entre carreras
DIAS_POR_SEMESTRE = 365.25 / 2
PARTICIONES = [("entrenamiento", 104), ("validacion", 52), ("prueba", 52)]


@dataclass
class Resultado:
    series: pd.DataFrame      
    eventos: pd.DataFrame    
    matricula: pd.DataFrame  


def _perfil(tema: Tema, dias: pd.DatetimeIndex, actividad: np.ndarray, eventos: pd.DataFrame) -> np.ndarray:
    fin_de_semana = np.where(dias.dayofweek >= 5, calendario.FACTOR_FIN_DE_SEMANA, 1.0)
    perfil = tema.base * actividad
    for evento in eventos[eventos["tema"] == tema.clave].itertuples():
        perfil = perfil + evento.altura * calendario.trapecio(dias, evento.inicio, evento.fin) * fin_de_semana
    return perfil / perfil.mean()


def _fraccion_elegible(tema: Tema) -> float:
    """Fracción de una carrera que cursa el tema."""
    elegibles = SEMESTRES - tema.nivel_minimo + 1
    return (elegibles + INTERES_PREVIO * (tema.nivel_minimo - 1)) / SEMESTRES


def _alumnos_del_tema(carreras: list[str], tema: Tema, ciclo: str) -> float:
    total = 0.0
    for carrera in carreras:
        alumnos = matricula.por_semestre(carrera, ciclo)
        semestres_previos = tema.nivel_minimo - 1
        total += alumnos[semestres_previos:].sum() + INTERES_PREVIO * alumnos[:semestres_previos].sum()
    return total


def _particion(n_semanas: int) -> np.ndarray:
    etiquetas = np.concatenate([[nombre] * cantidad for nombre, cantidad in PARTICIONES])
    if n_semanas > len(etiquetas):
        etiquetas = np.concatenate([etiquetas, ["fuera"] * (n_semanas - len(etiquetas))])
    return etiquetas[:n_semanas]


def generar(semilla: int = SEMILLA, inicio: date = INICIO, semanas: int = SEMANAS) -> Resultado:
    if pd.Timestamp(inicio).dayofweek != 0:
        raise ValueError("El inicio debe ser lunes")
    # Un generador por fuente de azar
    rng_eventos, rng_afinidad, rng_ruido = np.random.default_rng(semilla).spawn(3)
    dias = pd.date_range(inicio, periods=semanas * 7, freq="D")
    lista_ciclos = calendario.ciclos()
    ciclo_dia = calendario.ciclo_de(dias, lista_ciclos)
    ciclos_usados = list(dict.fromkeys(ciclo_dia))
    eventos = calendario.eventos_academicos(lista_ciclos, rng_eventos)
    actividad = calendario.actividad(dias, lista_ciclos)
    adopcion = np.linspace(ADOPCION_INICIAL, ADOPCION_FINAL, len(dias))
    tasa_diaria = CONVERSACIONES_POR_SEMESTRE / DIAS_POR_SEMESTRE
    suma_pesos = sum(tema.peso for tema in TEMAS)

    # Calendario por semana
    lunes = dias[::7]
    ciclo_semana = calendario.ciclo_de(lunes + pd.Timedelta(days=6), lista_ciclos)
    inicio_ciclo = {ciclo.clave: pd.Timestamp(ciclo.inicio) for ciclo in lista_ciclos}
    lunes_inicio = pd.DatetimeIndex([inicio_ciclo[clave] - pd.Timedelta(days=inicio_ciclo[clave].dayofweek)
                                     for clave in ciclo_semana])
    semana_ciclo = ((lunes - lunes_inicio).days // 7 + 1).to_numpy()
    particion = _particion(semanas)

    bloques = []
    for tema in TEMAS:
        perfil = _perfil(tema, dias, actividad, eventos)
        participacion = tema.peso / suma_pesos / _fraccion_elegible(tema)
        grupos = [(CARRERA_GENERAL, CARRERAS)] if tema.general else [(carrera, [carrera]) for carrera in CARRERAS]
        for nombre, carreras in grupos:
            alumnos = {clave: _alumnos_del_tema(carreras, tema, clave) for clave in ciclos_usados}
            alumnos_dia = np.array([alumnos[clave] for clave in ciclo_dia])
            afinidad = rng_afinidad.lognormal(0.0, DESVIACION_AFINIDAD)
            media = alumnos_dia * adopcion * tasa_diaria * participacion * perfil * afinidad
            conteo = rng_ruido.poisson(rng_ruido.gamma(DISPERSION, media / DISPERSION))
            bloques.append(pd.DataFrame({
                "semana": lunes,
                "carrera": nombre,
                "tema": tema.clave,
                "conversaciones": conteo.reshape(semanas, 7).sum(axis=1),
                "esperado": media.reshape(semanas, 7).sum(axis=1).round(3),
                "ciclo": ciclo_semana,
                "semana_ciclo": semana_ciclo,
                "particion": particion,
            }))
    series = pd.concat(bloques, ignore_index=True)

    filas = []
    for carrera in CARRERAS:
        for ciclo in ciclos_usados:
            for semestre, alumnos in enumerate(matricula.por_semestre(carrera, ciclo), start=1):
                filas.append(dict(carrera=carrera, ciclo=ciclo, semestre=semestre, alumnos=alumnos))
    return Resultado(series, eventos, pd.DataFrame(filas))
