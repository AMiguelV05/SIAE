"""Comprueba que la fuente del mapa de CUCEI esté indexada y se cite en preguntas sobre el mapa."""

import argparse

import requests

from tests.pipeline_test_support import (
    add_common_arguments,
    ask,
    create_conversation,
    ensure_api,
    matching_citation_titles,
    require_groq_authorization,
    require_answer_url,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_common_arguments(parser, "test_cucei_map")
    args = parser.parse_args()
    require_groq_authorization(args)
    base_url = args.base_url.rstrip("/")
    ensure_api(base_url)

    docs_response = requests.get(f"{base_url}/documents", timeout=20)
    assert docs_response.ok, f"No se pudieron consultar documentos: {docs_response.text}"
    maps = [
        doc for doc in docs_response.json()
        if "mapa cucei" in (doc.get("title", "").casefold())
        and doc.get("rag_status") == "vectorizado"
        and doc.get("chunks", 0) > 0
    ]
    assert maps, (
        "No aparece un Mapa CUCEI vectorizado con fragmentos. "
        "Revisa el resultado de python -m scripts.upload_docs --public-only."
    )
    print(f"Mapas CUCEI disponibles: {len(maps)}")

    # La respuesta debe citar el mapa y ofrecer el enlace para consultarlo.
    conversation_id = create_conversation(base_url, args.user_id, "Consulta del mapa CUCEI")
    result = ask(
        base_url,
        args.user_id,
        conversation_id,
        "Según el Mapa CUCEI 3D, ¿qué referencias o edificios aparecen para orientarme dentro del Centro?",
    )
    assert result.get("citations"), "La pregunta del mapa debería devolver citas."
    assert matching_citation_titles(result, "mapa cucei"), (
        "La respuesta debe citar el documento del Mapa CUCEI, no solo una fuente genérica."
    )
    require_answer_url(
        result,
        "https://www.cucei.udg.mx/sites/default/files/adjuntos/mapa-cucei-3d-2018.pdf",
        "orientación basada en el mapa",
    )
    assert result.get("history_used") is False, "La consulta nueva no debería usar historial."
    print("\n✓ El mapa está indexado y fue recuperado para la pregunta de orientación.")


if __name__ == "__main__":
    main()

