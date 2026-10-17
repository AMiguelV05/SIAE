# services/ml

Pronóstico de demanda de SIAE: conversaciones nuevas por semana, tema y carrera.

## Generador sintético

Simula 4 años (2022-B a 2026-A, 208 semanas) de 73 series: 10 temas * 7 carreras + 3 temas generales de CUCEI.

```bash
cd services/ml
PYTHONPATH=src python -m siae_ml.sintetico          
python -m pytest
```

Salida (no se versiona; se regenera con la misma semilla):

| Archivo | Contenido |
|---|---|
| `series_semanales.csv` | semana, carrera, tema, conversaciones, esperado, ciclo, semana_ciclo, particion |
| `eventos_academicos.csv` | eventos por tema y ciclo |
| `matricula.csv` | alumnos por carrera, ciclo y semestre |

Particiones: años 1 y 2 entrenamiento, año 3 validación, año 4 prueba.

Fuentes y supuestos: `src/siae_ml/sintetico/catalogos.py` (cupos DIVTIC, pesos de la encuesta) y
`src/siae_ml/sintetico/calendario.py`. Las fechas de 2022-B a 2025-A (inicio y fin de clases, vacaciones,
registro de materias de DIVTIC, dictamen y pago de matrícula) vienen de los calendarios de actividades
de Control Escolar de CUCEI. De 2025-B a 2027-A vienen de los
calendarios escolares en general de la UdeG para centros universitarios; ahí el día de
autorregistro de DIVTIC es estimado. Los ciclos siguientes usan reglas para ser simulados y verificados.
