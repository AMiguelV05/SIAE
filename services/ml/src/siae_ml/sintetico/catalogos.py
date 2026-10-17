"""Catálogos del generador: carreras, cupos de admisión, temas y supuestos de volumen."""

from dataclasses import dataclass

CUPOS = {
    "ICOM": 340,
    "INFO": 275,
    "INRO": 100,
    "INBI": 110,
    "INCE": 130,
    "FOTONICA": 30,
    "INES": 130,
}
CARRERAS = list(CUPOS)
INICIO_INES = "2025-A"

SEMESTRES = 9            
RETENCION = 0.8         
CONVERSACIONES_POR_SEMESTRE = 3
ADOPCION_INICIAL, ADOPCION_FINAL = 0.05, 0.25
INTERES_PREVIO = 0.05  


@dataclass(frozen=True)
class Tema:
    clave: str
    peso: float              
    base: float              
    nivel_minimo: int = 1   # semestre en el que aplica el tema
    general: bool = False   


# Pesos de la encuesta que realizamos en el Sprint II
TEMAS = [
    Tema("becas", 56.7, base=0.5),
    Tema("modular", 53.3, base=1.0, nivel_minimo=6),
    Tema("agenda", 43.3, base=0.3),
    Tema("titulacion", 33.3, base=0.8, nivel_minimo=8),
    Tema("justificantes", 26.7, base=1.0),
    Tema("servicio_social", 20.0, base=0.3, nivel_minimo=6),
    Tema("practicas", 20.0, base=0.8, nivel_minimo=7),
    Tema("ingles", 15.0, base=0.6),
    Tema("ceneval", 10.0, base=0.3, nivel_minimo=8),
    Tema("otros", 10.0, base=1.0),
    Tema("servicios_institucionales", 20.0, base=1.0, general=True),
    Tema("ingreso", 10.0, base=0.3, general=True),
    Tema("egreso", 10.0, base=0.6, nivel_minimo=9, general=True),
]
TEMAS_POR_CLAVE = {tema.clave: tema for tema in TEMAS}
CARRERA_GENERAL = "CUCEI"
