"""Funciones auxiliares compartidas por las pruebas independientes del flujo de SIAE."""

import argparse
import os
import re
import sys
import time
import unicodedata

import requests


DEFAULT_BASE_URL = "http://127.0.0.1:8080"
REQUEST_TIMEOUT = 180

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def add_common_arguments(parser: argparse.ArgumentParser, default_user_id: str) -> None:
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="URL de la API en ejecución.")
    parser.add_argument("--user-id", default=default_user_id, help="ID local usado para esta prueba.")
    parser.add_argument(
        "--allow-groq-document-context",
        action="store_true",
        help="autoriza enviar a Groq los fragmentos locales recuperados por las preguntas RAG",
    )


def require_groq_authorization(args: argparse.Namespace) -> None:
    # Evita enviar fragmentos locales al proveedor si quien ejecuta no lo autorizó.
    if not args.allow_groq_document_context:
        print(
            "Esta prueba enviará a Groq fragmentos recuperados de documentos locales. "
            "Si autorizas ese envío, vuelve a ejecutarla con --allow-groq-document-context.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in folded if not unicodedata.combining(char))
    plain = re.sub(r"[^\w\s]", " ", plain.replace("_", " "))
    return " ".join(plain.split())


def ensure_api(base_url: str) -> None:
    response = requests.get(f"{base_url.rstrip('/')}/health", timeout=10)
    assert response.ok, f"API no disponible ({response.status_code}): {response.text}"
    print("Backend en línea:", response.json())
    openapi_response = requests.get(f"{base_url.rstrip('/')}/openapi.json", timeout=10)
    assert openapi_response.ok, f"No se pudo consultar OpenAPI: {openapi_response.text}"
    openapi = openapi_response.json()
    # También detecta si Swagger está mostrando una versión vieja de la API.
    operation = openapi.get("paths", {}).get("/messages/ask", {}).get("post", {})
    body_content = operation.get("requestBody", {}).get("content", {})
    body_schema = next(
        (entry.get("schema", {}) for entry in body_content.values()),
        {},
    )
    schema_ref = body_schema.get("$ref", "").rsplit("/", 1)[-1]
    properties = openapi.get("components", {}).get("schemas", {}).get(schema_ref, {}).get("properties", {})
    assert "top_k" not in properties, (
        "La API todavía expone top_k en Swagger; reinicia el backend actualizado."
    )


def create_conversation(base_url: str, user_id: str, title: str) -> str:
    response = requests.post(
        f"{base_url.rstrip('/')}/conversations/new",
        data={"user_id": user_id, "title": title},
        timeout=20,
    )
    assert response.status_code == 201, f"No se pudo crear conversación: {response.text}"
    conversation_id = response.json()["conversation_id"]
    print("Conversación:", conversation_id)
    return conversation_id


def ask(base_url: str, user_id: str, conversation_id: str, question: str) -> dict:
    delay = max(0.0, float(os.getenv("SIAE_TEST_REQUEST_DELAY_SECONDS", "0")))
    if delay:
        print(f"Pausa de {delay:g}s para respetar el límite del proveedor de IA.")
        time.sleep(delay)
    response = requests.post(
        f"{base_url.rstrip('/')}/messages/ask",
        data={
            "conversation_id": conversation_id,
            "user_id": user_id,
            "question": question,
        },
        timeout=REQUEST_TIMEOUT,
    )
    assert response.status_code == 200, (
        f"La pregunta {question!r} falló ({response.status_code}): {response.text}"
    )
    result = response.json()
    citations = result.get("citations", [])
    print(f"\nPregunta: {question}\nRespuesta: {result.get('answer', '')}")
    print("Fuentes:", ", ".join(item.get("title", "") for item in citations) or "ninguna")
    print("Historial aplicado:", result.get("history_used"))
    return result


def matching_citation_titles(result: dict, *needles: str) -> bool:
    titles = normalize(" ".join(item.get("title", "") for item in result.get("citations", [])))
    return any(normalize(needle) in titles for needle in needles)


def require_answer_url(result: dict, url: str, context: str = "respuesta") -> None:
    answer = result.get("answer", "")
    assert url in answer, (
        f"La {context} debería incluir el enlace oficial {url}. Respuesta recibida: {answer}"
    )


def indexed_sources(base_url: str) -> list[dict]:
    response = requests.get(f"{base_url.rstrip('/')}/documents", timeout=30)
    assert response.ok, f"No se pudieron consultar documentos: {response.text}"
    return response.json()


def require_indexed_sources(documents: list[dict], *needles: str) -> None:
    """Falla con un mensaje útil si no está indexado ninguno de los nombres alternativos de fuentes."""
    available = [
        set(normalize(doc.get("title", "") + " " + doc.get("file_name", "")).split())
        for doc in documents
        if doc.get("rag_status") == "vectorizado" and doc.get("chunks", 0) > 0
    ]
    # Los títulos pueden incluir las mismas palabras descriptivas en distinto orden. Por ejemplo:
    # «Oferta académica CUCEI — licenciaturas» y «CUCEI — Oferta académica de licenciaturas».
    # Busca todas las palabras importantes dentro de un mismo registro indexado.
    missing = [
        needle for needle in needles
        if not any(set(normalize(needle).split()).issubset(record) for record in available)
    ]
    assert not missing, (
        "Faltan fuentes vectorizadas necesarias para este escenario: "
        + ", ".join(missing)
        + ". Revisa /documents y ejecuta la ingesta correspondiente."
    )

