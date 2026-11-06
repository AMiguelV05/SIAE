"""Comprueba un saludo seguido de una pregunta informativa en una misma conversación."""

import argparse
import requests

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
    add_common_arguments(parser, "test_greeting_question")
    args = parser.parse_args()
    require_groq_authorization(args)
    base_url = args.base_url.rstrip("/")
    ensure_api(base_url)
    conversation_id = create_conversation(base_url, args.user_id, "Saludo y ubicación")

    # Primero se validan varios saludos; después, uno que incluye una pregunta real.
    greeting = ask(base_url, args.user_id, conversation_id, "Buenas tardes")
    assert "hola" in normalize(greeting.get("answer", "")), "El saludo no recibió bienvenida."
    assert greeting.get("conversation_title") == "Nueva consulta SIAE", (
        "El chat debe conservar el título genérico mientras solo reciba saludos."
    )
    assert not greeting.get("citations"), "El saludo simple no debe consultar ni citar el RAG."
    assert greeting.get("history_used") is False, "El saludo no debe recuperar historial."

    question = ask(
        base_url,
        args.user_id,
        conversation_id,
        "qué onda wey donde sta ubicado CUCEI",
    )
    answer = normalize(question.get("answer", ""))
    assert "no encontre informacion" not in answer, "La pregunta informativa se trató como saludo."
    assert question.get("citations"), "La pregunta sobre ubicación debería citar fuentes."
    assert matching_citation_titles(question, "ubicacion", "mapa", "directorio"), (
        "La ubicación debería citar la página de Ubicación CUCEI, un mapa o el directorio oficial."
    )
    require_answer_url(
        question,
        "https://www.cucei.udg.mx/acerca-de/ubicacion",
        "consulta de ubicación",
    )
    assert question.get("history_used") is False, "La pregunta informativa no debe heredar el saludo."
    assert "ubicacion" in normalize(question.get("conversation_title", "")), (
        "El título debe actualizarse cuando aparece el primer tema informativo."
    )

    # Un chat separado comprueba que las frases sociales no dependan de citas ni del historial.
    social_conversation_id = create_conversation(
        base_url, args.user_id, "Variantes sociales regionales"
    )
    for small_talk_question in (
        "hola, q haces?",
        "ola k ase",
        "qué onda wey",
        "qué pex bro",
        "quiúbole mano",
        "buenasss",
        "¿Qué más, pues?",
        "pura vida",
        "¿Cómo estai?",
        "¿Qué tranza?",
        "¿Qué tal, tío?",
        "¿Qué fue, causa?",
        "todo piola",
        "epa mi gente",
        "hello what's up",
    ):
        small_talk = ask(
            base_url, args.user_id, social_conversation_id, small_talk_question
        )
        normalized_social_answer = normalize(small_talk.get("answer", ""))
        assert any(term in normalized_social_answer for term in ("hola", "listo para ayudarte")), (
            "La charla breve después de un saludo debería recibir una respuesta social."
        )
        assert not small_talk.get("citations"), "La charla breve no debe citar fuentes del RAG."
        assert small_talk.get("history_used") is False, "La charla breve no debe usar historial factual."

    # La forma social no debe tragarse el resto cuando el usuario añade una consulta real.
    social_question = ask(
        base_url,
        args.user_id,
        social_conversation_id,
        "q onda, parce, ¿dónde está la biblioteca?",
    )
    assert social_question.get("citations"), "El saludo con consulta debe recuperar fuentes."
    assert "https://www.cucei.udg.mx/servicios/servicios-bibliotecarios" in social_question.get("answer", ""), (
        "La consulta social debe conservar el enlace específico del servicio bibliotecario."
    )
    assert social_question.get("history_used") is False

    # Preguntar qué hace el asistente es charla social y no una pregunta documental.
    social_action = ask(base_url, args.user_id, social_conversation_id, "q haces?")
    assert not social_action.get("citations") and social_action.get("history_used") is False
    assert "listo para ayudarte" in normalize(social_action.get("answer", ""))

    ticket_response = requests.post(
        f"{base_url}/tickets/create",
        data={
            "user_id": args.user_id,
            "message_id": question["user_message_id"],
            "file": "evidencia_prueba.txt",
        },
        timeout=20,
    )
    assert ticket_response.status_code == 201, f"No se pudo crear ticket: {ticket_response.text}"
    ticket = ticket_response.json()
    assert ticket.get("status") == "pendiente", f"Estado inesperado del ticket: {ticket}"
    tickets_response = requests.get(
        f"{base_url}/tickets/user/{args.user_id}", timeout=20
    )
    assert tickets_response.ok, f"No se pudieron consultar tickets: {tickets_response.text}"
    assert any(item.get("ticket_id") == ticket.get("ticket_id") for item in tickets_response.json()), (
        "El ticket recién creado no aparece en la lista del usuario."
    )
    print("\n✓ Saludo, pregunta informativa y ciclo básico de ticket correctos.")


if __name__ == "__main__":
    main()

