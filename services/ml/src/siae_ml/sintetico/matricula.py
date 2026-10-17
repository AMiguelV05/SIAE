"""Matrícula por carrera, ciclo y semestre a partir de cupos de admisión."""

import numpy as np

from .calendario import indice_ciclo
from .catalogos import CUPOS, INICIO_INES, RETENCION, SEMESTRES


def admitidos(carrera: str, indice: int) -> float:
    """Admitidos de la carrera en el ciclo con ese índice (cupo constante)."""
    ines_vigente = indice >= indice_ciclo(INICIO_INES)
    if carrera == "INCE" and ines_vigente:
        return 0.0
    if carrera == "INES" and not ines_vigente:
        return 0.0
    return float(CUPOS[carrera])


def por_semestre(carrera: str, ciclo: str) -> np.ndarray:
    """Alumnos inscritos en los semestres 1..SEMESTRES durante `ciclo`.

    La generación admitida hace `ciclos_atras` ciclos está en el semestre `ciclos_atras + 1`.
    """
    indice = indice_ciclo(ciclo)
    return np.array([admitidos(carrera, indice - ciclos_atras) * RETENCION
                     for ciclos_atras in range(SEMESTRES)])
