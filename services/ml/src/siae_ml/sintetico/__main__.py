"""Genera los CSV sintéticos: python -m siae_ml.sintetico [--semilla N] [--salida DIR]"""

import argparse
from pathlib import Path

from .generador import SEMILLA, generar


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semilla", type=int, default=SEMILLA)
    parser.add_argument("--salida", type=Path, default=Path("data/sintetico"))
    opciones = parser.parse_args()

    resultado = generar(opciones.semilla)
    opciones.salida.mkdir(parents=True, exist_ok=True)
    resultado.series.to_csv(opciones.salida / "series_semanales.csv", index=False)
    resultado.eventos.to_csv(opciones.salida / "eventos_academicos.csv", index=False)
    resultado.matricula.to_csv(opciones.salida / "matricula.csv", index=False)

    numero_series = resultado.series.groupby(["carrera", "tema"]).ngroups
    print(f"{numero_series} series, {resultado.series['semana'].nunique()} semanas, "
          f"{resultado.series['conversaciones'].sum():,} conversaciones en {opciones.salida}")


if __name__ == "__main__":
    main()
