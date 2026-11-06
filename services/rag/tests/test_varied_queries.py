"""Comprueba distintos estilos de preguntas con documentos locales y fuentes web de CUCEI."""

import argparse

from tests.pipeline_test_support import (
    add_common_arguments,
    ask,
    create_conversation,
    ensure_api,
    indexed_sources,
    matching_citation_titles,
    normalize,
    require_groq_authorization,
    require_indexed_sources,
)


SCENARIOS = (
    {
        "name": "Prácticas por experiencia laboral, con saludo y lenguaje informal",
        "question": (
            "hola, q pex: ya llevo 4 meses trabajando, tengo IMSS de la empresa pero no "
            "tiene convenio con CUCEI. ¿Aún puedo liberar prácticas por experiencia laboral?"
        ),
        "sources": ("liberacion de practicas por experiencia laboral",),
        "answer_contains": ("manual de tramite", "requisitos", "formatos"),
        "expected_url": "https://practicas.cucei.udg.mx/",
    },
    {
        "name": "Prácticas con oficio de asignación, pregunta de varias partes",
        "question": (
            "me aceptaron para practicas, cuantos dias habiles tengo para abrir el expediente "
            "y como genero el oficio de asignacion?"
        ),
        "sources": ("liberacion de practicas por oficio de asignacion",),
        "expected_url": "https://practicas.cucei.udg.mx/",
    },
    {
        "name": "Reportes bimestrales de servicio social, términos administrativos",
        "question": (
            "Para el ciclo 2024B me solicitaron reportes bimestrales del servicio social; "
            "¿qué indica el manual que debo entregar?"
        ),
        "sources": ("servicio social manual reportes bimestrales",),
        "answer_contains": (
            "dos reportes",
            "240 horas",
            "480 horas",
            "6 meses",
            "2 anos",
        ),
        "answer_excludes": ("3 reportes", "tres reportes"),
        "expected_url": "https://www.cucei.udg.mx/servicios/servicio-social",
        "require_citation": False,
    },
    {
        "name": "Programa JOBS, abreviación y pregunta breve",
        "question": "q onda, para q sirve el programa JOBS de idiomas?",
        "sources": ("programa jobs",),
        "expected_url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/programa-jobs",
    },
    {
        "name": "Atención médica, redacción formal",
        "question": "¿Qué atención médica o clínica se ofrece a la comunidad dentro del CUCEI?",
        "sources": ("servicios medicos", "servicios clinicos"),
        "expected_url": "https://www.cucei.udg.mx/servicios/medicos-y-clinicos",
    },
    {
        "name": "Bolsa de trabajo, expresión coloquial",
        "question": "Busco chamba relacionada con mi carrera, ¿en qué página publica CUCEI las vacantes?",
        "sources": ("bolsa de trabajo",),
        "expected_url": "https://www.cucei.udg.mx/servicios/bolsa-de-trabajo",
    },
    {
        "name": "Biblioteca digital, pregunta compuesta",
        "question": (
            "¿Dónde puedo consultar libros electrónicos, revistas o tesis de la UdeG por internet?"
        ),
        "sources": ("biblioteca digital wdg", "repositorio institucional riudeg"),
        "expected_url": "https://wdg.biblio.udg.mx/",
    },
    {
        "name": "Apoyo a idiomas, variante sin acentos",
        "question": "ademas de cursos, que opciones hay en CUCEI para aprender idiomas?",
        "sources": ("apoyo a idiomas", "centro de aprendizaje global"),
        "expected_url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/centro-de-aprendizaje-global",
    },
    {
        "name": "Oferta de licenciaturas, lenguaje de aspirante",
        "question": "Q carreras de licenciatura hay en CUCEI para estudiar algo de computacion?",
        "sources": ("oferta academica cucei licenciaturas", "ingenieria en computacion"),
        "expected_url": "https://www.cucei.udg.mx/carreras/computacion",
    },
    {
        "name": "Ubicación, pregunta directa con restricción de formato",
        "question": "Dime breve y con dirección: ¿dónde queda CUCEI? Indica la ciudad y el estado.",
        "sources": ("ubicacion cucei", "directorio oficial cucei"),
        "expected_url": "https://www.cucei.udg.mx/acerca-de/ubicacion",
        "answer_contains": ("marcelino garcia barragan", "guadalajara", "jalisco"),
        "answer_excludes": ("zapopan",),
    },
    {
        "name": "Becas, saludo informal y falta de puntuación",
        "question": "buenas noches q requisitos hay para pedir una beca en CUCEI",
        "sources": ("cucei becas", "becas y apoyos para idiomas"),
        "expected_url": "https://www.cucei.udg.mx/servicios/becas",
    },
    {
        "name": "Misión institucional, pregunta conceptual",
        "question": (
            "Resume por separado la misión y la visión al 2030 del Centro Universitario de "
            "Ciencias Exactas e Ingenierías. Incluye las ideas principales de ambas."
        ),
        "sources": ("mision y vision",),
        "answer_contains": (
            "mision",
            "vision",
            "colaboracion",
            "calidad academica",
            "desafios globales",
        ),
        "answer_excludes": ("no se incluye el texto de la vision",),
    },
)


def check_control_escolar_route(base_url: str, user_id: str) -> None:
    print("\nESCENARIO: Enlace de trámites de Control Escolar CUCEI")
    conversation_id = create_conversation(base_url, user_id, "Trámites de Control Escolar")
    for question in (
        "¿Cómo puedo dar de baja las materias?",
        "buenas, q pasos tengo q seguir pa sacar el kardex certificado",
        "Necesito saber dónde hago el trámite de alta en el IMSS",
    ):
        result = ask(base_url, user_id, conversation_id, question)
        answer = result.get("answer", "")
        assert "https://escolar.cucei.udg.mx/cescolar/" in answer, (
            "Las consultas de procedimientos de Control Escolar deben dirigir al portal oficial."
        )
        assert result.get("history_used") is False, (
            "El acceso directo al portal no debe depender del historial del chat."
        )
        assert not result.get("citations"), (
            "La respuesta directa con el enlace oficial no debe inventar citas de fragmentos RAG."
        )


def check_service_social_followup(base_url: str, user_id: str) -> None:
    print("\nESCENARIO: Continuidad de la regla de reportes de Servicio Social")
    conversation_id = create_conversation(base_url, user_id, "Seguimiento Servicio Social")
    first = ask(
        base_url,
        user_id,
        conversation_id,
        "¿Cuántos reportes debo entregar en el servicio social?",
    )
    second = ask(
        base_url,
        user_id,
        conversation_id,
        "¿Y cuál es el tiempo mínimo y máximo?",
    )
    for result in (first, second):
        answer = normalize(result.get("answer", ""))
        assert all(term in answer for term in ("dos reportes", "240 horas", "480 horas")), (
            "La respuesta debe conservar la regla actual de los dos reportes y sus horas."
        )
        assert "https://www.cucei.udg.mx/servicios/servicio-social" in result.get("answer", ""), (
            "La regla debe incluir el portal oficial de Servicio Social CUCEI."
        )
    assert first.get("history_used") is False
    assert second.get("history_used") is True, (
        "El seguimiento inmediato del Servicio Social debe reconocer continuidad del tema."
    )
    second_answer = normalize(second.get("answer", ""))
    assert all(term in second_answer for term in ("6 meses", "2 anos")), (
        "El seguimiento debe conservar los límites mínimo y máximo de duración."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser, "test_varied_queries")
    args = parser.parse_args()
    require_groq_authorization(args)
    base_url = args.base_url.rstrip("/")
    ensure_api(base_url)

    documents = indexed_sources(base_url)
    required_sources = (
        "Directorio Oficial CUCEI",
        "Ubicación CUCEI",
        "Mapa CUCEI 3D",
        "CUCEI — Apoyo a idiomas",
        "CUCEI — Programa JOBS",
        "CUCEI — Servicios Médicos",
        "CUCEI — Bolsa de Trabajo",
        "UdeG — Biblioteca Digital WDG",
        "CUCEI oferta academica licenciaturas",
        "CUCEI — Becas",
        "CUCEI — Misión y Visión",
        "servicio-social-manual-reportes-bimestrales-2024b.pdf",
        "liberacion_de_practicas_por_experiencia_laboral.pdf",
        "liberacion_de_practicas_por_oficio_de_asignacion.pdf",
    )
    require_indexed_sources(documents, *required_sources)
    print(f"Fuentes vectorizadas revisadas: {len(documents)} registros en /documents.")

    # Cada escenario crea un chat nuevo para que una prueba no contamine la siguiente.
    for index, scenario in enumerate(SCENARIOS, start=1):
        print(f"\nESCENARIO {index}/{len(SCENARIOS)}: {scenario['name']}")
        conversation_id = create_conversation(
            base_url,
            args.user_id,
            scenario["name"][:50],
        )
        result = ask(base_url, args.user_id, conversation_id, scenario["question"])
        if scenario.get("require_citation", True):
            assert result.get("citations"), f"La consulta no citó fuentes: {scenario['question']}"
        cited_titles = [item.get("title", "") for item in result.get("citations", [])]
        if scenario.get("require_citation", True):
            assert matching_citation_titles(result, *scenario["sources"]), (
                "Las citas no incluyen una fuente esperada para "
                f"{scenario['name']}. Esperadas: {scenario['sources']}; recibidas: {cited_titles}"
            )
        answer = normalize(result.get("answer", ""))
        assert "no encontre informacion oficial suficientemente relacionada" not in answer, (
            f"La API respondió que no encontró información para {scenario['name']}"
        )
        assert result.get("history_used") is False, (
            "Cada escenario informativo inicia una conversación nueva y no debe heredar historial."
        )
        missing_answer_terms = [
            term for term in scenario.get("answer_contains", ())
            if normalize(term) not in answer
        ]
        assert not missing_answer_terms, (
            f"La respuesta de {scenario['name']} omitió información esperada: "
            f"{missing_answer_terms}. Respuesta recibida: {result.get('answer', '')}"
        )
        unexpected_answer_terms = [
            term for term in scenario.get("answer_excludes", ())
            if normalize(term) in answer
        ]
        assert not unexpected_answer_terms, (
            f"La respuesta de {scenario['name']} contiene datos que contradicen la fuente: "
            f"{unexpected_answer_terms}. Respuesta recibida: {result.get('answer', '')}"
        )
        expected_url = scenario.get("expected_url")
        if expected_url:
            assert expected_url in result.get("answer", ""), (
                f"La respuesta de {scenario['name']} debe incluir el enlace oficial "
                f"{expected_url}. Respuesta recibida: {result.get('answer', '')}"
            )

    check_control_escolar_route(base_url, args.user_id)
    check_service_social_followup(base_url, args.user_id)
    print("\n✓ Preguntas formales, coloquiales, abreviadas, con saludo y de varios temas correctas.")


if __name__ == "__main__":
    main()
