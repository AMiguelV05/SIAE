"""Comprueba las preguntas de seguimiento sobre un tema y el aislamiento al cambiar de tema."""

import argparse

from tests.pipeline_test_support import (
    add_common_arguments,
    ask,
    create_conversation,
    ensure_api,
    matching_citation_titles,
    normalize,
    require_answer_url,
    require_groq_authorization,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser, "test_topic_switching")
    args = parser.parse_args()
    require_groq_authorization(args)
    base_url = args.base_url.rstrip("/")
    ensure_api(base_url)
    conversation_id = create_conversation(base_url, args.user_id, "Cambio y continuidad de temas")

    # La segunda pregunta alude a la primera; la tercera inicia un tema distinto.
    location = ask(
        base_url,
        args.user_id,
        conversation_id,
        "¿Cuál es la ubicación de CUCEI?",
    )
    assert location.get("citations"), "La pregunta inicial debería citar una fuente."
    assert location.get("history_used") is False, "La primera pregunta no tiene historial que usar."
    require_answer_url(
        location,
        "https://www.cucei.udg.mx/acerca-de/ubicacion",
        "respuesta sobre ubicación",
    )

    follow_up = ask(
        base_url,
        args.user_id,
        conversation_id,
        "¿Qué dirección tiene esa ubicación?",
    )
    assert follow_up.get("history_used") is True, (
        "La referencia a 'esa ubicación' debería usar el intercambio inmediatamente anterior."
    )
    assert follow_up.get("citations"), "El seguimiento también necesita fuentes."
    assert matching_citation_titles(follow_up, "ubicacion", "mapa"), (
        "El seguimiento debería conservar fuentes de ubicación/mapa."
    )
    require_answer_url(
        follow_up,
        "https://www.cucei.udg.mx/acerca-de/ubicacion",
        "seguimiento sobre ubicación",
    )

    switched = ask(
        base_url,
        args.user_id,
        conversation_id,
        "¿Qué orientación académica ofrece CUCEI a estudiantes de licenciatura?",
    )
    answer = normalize(switched.get("answer", ""))
    assert switched.get("history_used") is False, "El cambio de tema no debe usar la ubicación anterior."
    assert switched.get("citations"), "La pregunta nueva debería citar fuentes."
    assert "orientacion" in answer or "tutoria" in answer or "asesoria" in answer, (
        "La respuesta no parece tratar orientación académica."
    )
    print("\n✓ Seguimiento inmediato y cambio de tema correctos.")


if __name__ == "__main__":
    main()

