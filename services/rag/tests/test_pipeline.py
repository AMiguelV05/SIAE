"""Pruebas integrales de calidad para una API local de SIAE en ejecución.

Requisito: inicia el backend y ejecuta ``python -m scripts.upload_docs`` al menos una vez.
A diferencia de una prueba básica de HTTP, este script comprueba el contenido de
las respuestas, sus citas y que el historial solo se use para dar continuidad
inmediata a una pregunta sobre el mismo tema.
"""

import argparse
import sys
import time
import unicodedata

import requests


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


BASE_URL = "http://127.0.0.1:8080"
TEST_USER_ID = "test_student_eval_002"
REQUEST_TIMEOUT = 180


def print_header(title: str) -> None:
    print("\n" + "=" * 64)
    print(f" {title}")
    print("=" * 64)


def plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))


def ask(conversation_id: str, question: str) -> dict:
    response = requests.post(
        f"{BASE_URL}/messages/ask",
        data={
            "conversation_id": conversation_id,
            "user_id": TEST_USER_ID,
            "question": question,
        },
        timeout=REQUEST_TIMEOUT,
    )
    assert response.status_code == 200, (
        f"La consulta {question!r} falló ({response.status_code}): {response.text}"
    )
    result = response.json()
    print(f"Pregunta: {question}")
    print(f"Respuesta: {result['answer']}")
    print("Fuentes:", ", ".join(s.get("title", "") for s in result.get("citations", [])))
    print(
        "Historial aplicado:",
        repr(result.get("history_used")),
        f"(tipo={type(result.get('history_used')).__name__})",
    )
    return result


def assert_any_source_url(result: dict, *urls: str) -> None:
    answer = result.get("answer", "")
    assert any(url in answer for url in urls), (
        f"La respuesta debe incluir uno de los enlaces específicos: {urls}. "
        f"Respuesta: {answer}"
    )


def run_pipeline_tests(base_url: str = BASE_URL) -> None:
    global BASE_URL
    BASE_URL = base_url.rstrip("/")
    # Esta prueba usa una API activa para revisar respuestas, citas e historial en conjunto.
    started = time.time()
    print_header("1. API Y FUENTES PREPARADAS")
    health = requests.get(f"{BASE_URL}/health", timeout=10)
    assert health.status_code == 200, f"Backend no disponible: {health.status_code}"
    print("Backend en línea:", health.json())

    openapi_response = requests.get(f"{BASE_URL}/openapi.json", timeout=10)
    assert openapi_response.ok, f"No se pudo consultar OpenAPI: {openapi_response.text}"
    openapi = openapi_response.json()
    operation = openapi.get("paths", {}).get("/messages/ask", {}).get("post", {})
    request_body = operation.get("requestBody", {}).get("content", {})
    body_schema = next((item.get("schema", {}) for item in request_body.values()), {})
    body_schema_name = body_schema.get("$ref", "").rsplit("/", 1)[-1]
    body_properties = openapi.get("components", {}).get("schemas", {}).get(
        body_schema_name, {}
    ).get("properties", {})
    assert "top_k" not in body_properties, (
        "Swagger debe usar el top_k fijo del backend y no exponerlo como parámetro."
    )
    print("top_k: fijo en 6 (no editable en Swagger).")

    # El rastreo académico debe estar publicado en OpenAPI con controles por programa y profundidad.
    academic_operation = openapi.get("paths", {}).get("/docs/crawl-academic-catalog", {}).get("post")
    assert academic_operation, "Falta el endpoint para recorrer catálogos académicos completos."
    academic_schema_ref = next(
        iter(academic_operation.get("requestBody", {}).get("content", {}).values())
    )["schema"].get("$ref", "").rsplit("/", 1)[-1]
    academic_properties = openapi.get("components", {}).get("schemas", {}).get(
        academic_schema_ref, {}
    ).get("properties", {})
    assert {"url", "program_path_prefix", "max_pages_per_program", "max_depth"}.issubset(
        academic_properties
    ), "El endpoint debe exponer catálogo, ruta de programas y límites por ficha."

    crawl_status = requests.get(f"{BASE_URL}/docs/crawl-status", timeout=10)
    assert crawl_status.ok, f"No se pudo consultar el avance de rastreo: {crawl_status.text}"
    status_fields = {
        "state", "crawl_type", "root_url", "started_at", "finished_at",
        "pages_visited", "pages_indexed", "pages_failed", "programs_found",
        "programs_processed", "programs", "pending_pages", "failures",
    }
    assert status_fields.issubset(crawl_status.json()), (
        "El estado de rastreo debe mostrar progreso, resultados y errores de páginas/programas."
    )
    print("Rastreo académico y endpoint de estado publicados correctamente.")

    docs_response = requests.get(f"{BASE_URL}/documents", timeout=20)
    assert docs_response.status_code == 200, f"No se pudieron consultar documentos: {docs_response.text}"
    documents = docs_response.json()
    directory_docs = [
        doc for doc in documents
        if "directorio" in plain(doc.get("title", "") + " " + doc.get("file_name", ""))
        and doc.get("rag_status") == "vectorizado"
    ]
    assert directory_docs, (
        "Falta el Directorio Oficial CUCEI indexado. Ejecuta primero python -m scripts.upload_docs."
    )
    assert any(doc.get("chunks", 0) > 0 for doc in directory_docs), (
        "El directorio aparece indexado pero no tiene fragmentos para recuperar."
    )
    print(f"Fuentes disponibles: {len(documents)}; directorio indexado correctamente.")

    print_header("2. CREACIÓN DE CONVERSACIÓN")
    response = requests.post(
        f"{BASE_URL}/conversations/new",
        data={"user_id": TEST_USER_ID, "title": "Prueba de calidad RAG"},
        timeout=20,
    )
    assert response.status_code == 201, f"No se pudo crear conversación: {response.text}"
    created_conversation = response.json()
    conversation_id = created_conversation["conversation_id"]
    assert created_conversation.get("title") == "Nueva consulta SIAE", (
        "Una conversación nueva debe iniciar con el título genérico."
    )
    print("Conversación:", conversation_id)

    print_header("3. SALUDO SIMPLE; NO DEBE CONSULTAR EL RAG")
    greeting = ask(conversation_id, "Buenas tardes")
    assert "hola" in plain(greeting["answer"]), "El saludo no recibió una bienvenida."
    assert not greeting.get("citations"), "Un saludo simple no debería citar documentos."
    assert greeting.get("history_used") is False, "Un saludo nuevo no debe recuperar historial."

    print_header("4. PREGUNTA INFORMATIVA; NO ES UN SALUDO")
    services = ask(
        conversation_id,
        "Como estudiante de licenciatura, ¿qué apoyo de orientación académica ofrece CUCEI?",
    )
    services_answer = plain(services["answer"])
    services_sources = plain(" ".join(s.get("title", "") for s in services.get("citations", [])))
    assert "orientacion" in services_answer, "La respuesta debe tratar la orientación académica preguntada."
    assert "no contiene informacion" not in services_answer, (
        "La respuesta negó información que sí existe en el Estatuto Orgánico."
    )
    assert any(term in services_answer for term in ("tutoria", "asesoria", "planes de estudio")), (
        "La respuesta debe mencionar el tipo de orientación descrito en la fuente."
    )
    assert "posgrado" not in services_answer, (
        "La respuesta a una pregunta de licenciatura se desvió a normas de posgrado."
    )
    assert "licenciatura" in plain(services.get("conversation_title", "")), (
        "El título debe cambiar del genérico al tema de los primeros mensajes útiles."
    )
    assert "estatuto" in services_sources, "La orientación debe citar el Estatuto Orgánico CUCEI."
    assert services.get("history_used") is False, "La consulta de servicios no debe heredar el saludo."

    print_header("5. BÚSQUEDA DE CONTACTO Y CITA DEL DIRECTORIO")
    contact = ask(
        conversation_id,
        "¿Quién es el encargado o coordinador de la Secretaría Académica y a qué correo puedo escribirle?",
    )
    contact_answer = plain(contact["answer"])
    contact_sources = plain(" ".join(s.get("title", "") for s in contact.get("citations", [])))
    assert "sac@cucei.udg.mx" in contact_answer, "No se recuperó el correo de Secretaría Académica."
    assert "eduardo" in contact_answer, "No se recuperó el nombre que aparece en el directorio."
    assert "directorio" in contact_sources, "La respuesta de contacto debe citar el directorio."
    assert_any_source_url(
        contact,
        "https://www.cucei.udg.mx/acerca/directorio",
    )
    assert contact.get("history_used") is False, "El tema de servicios no debe mezclarse con el contacto."

    print_header("6. ESTRUCTURA DE DIVISIÓN")
    departments = ask(
        conversation_id,
        "¿Cuáles departamentos integran la División de Ciencias Básicas?",
    )
    department_answer = plain(departments["answer"])
    department_sources = plain(" ".join(s.get("title", "") for s in departments.get("citations", [])))
    expected_departments = ("matematicas", "fisica", "quimica", "farmacobiologia")
    missing_departments = [name for name in expected_departments if name not in department_answer]
    assert not missing_departments, f"Faltaron departamentos en la respuesta: {missing_departments}"
    assert "organizacion" in department_sources or "organigrama" in department_sources, (
        "La estructura debe citar la página de Organización o el organigrama."
    )
    assert_any_source_url(
        departments,
        "https://www.cucei.udg.mx/acerca-de/organizacion",
        "https://www.cucei.udg.mx/sites/default/files/adjuntos/organigrama_general-2021.pdf",
    )
    assert departments.get("history_used") is False, "La consulta de división debe empezar sin historial."

    print_header("7. SEGUIMIENTO DEL MISMO TEMA")
    follow_up = ask(conversation_id, "¿Cuántos son esos departamentos?")
    follow_up_answer = plain(follow_up["answer"])
    assert follow_up.get("history_used") is True, (
        "La pregunta consecutiva debe usar el intercambio inmediato para resolver 'esos departamentos'."
    )
    assert "4" in follow_up_answer or "cuatro" in follow_up_answer, (
        "El seguimiento debía responder que son cuatro departamentos."
    )
    assert follow_up.get("citations"), "La respuesta de seguimiento también requiere fuentes oficiales."

    print_header("8. CAMBIO DE TEMA; NO DEBE USAR EL CHAT ANTERIOR")
    regulation = ask(
        conversation_id,
        "Según el Reglamento de Becas, ¿qué requisitos se deben cumplir para conservar una beca?",
    )
    regulation_sources = plain(" ".join(s.get("title", "") for s in regulation.get("citations", [])))
    assert regulation.get("history_used") is False, (
        "Una pregunta nueva sobre becas no debe analizar el tema anterior de departamentos."
    )
    assert "beca" in regulation_sources, "La respuesta normativa debe recuperar el documento de becas."
    assert "beca" in plain(regulation["answer"]), "La respuesta no parece contestar la consulta sobre becas."

    print_header("9. TICKET E HISTORIAL")
    ticket_response = requests.post(
        f"{BASE_URL}/tickets/create",
        data={
            "user_id": TEST_USER_ID,
            "message_id": regulation["user_message_id"],
            "file": "prueba_pipeline.pdf",
        },
        timeout=20,
    )
    assert ticket_response.status_code == 201, f"No se pudo crear ticket: {ticket_response.text}"
    print("Ticket creado:", ticket_response.json().get("ticket_id"))

    history_response = requests.get(
        f"{BASE_URL}/conversations/{conversation_id}/messages", timeout=20
    )
    assert history_response.status_code == 200, f"No se pudo leer el historial: {history_response.text}"
    history = history_response.json()
    assert history.get("total_messages", 0) >= 12, "El historial no contiene todos los turnos de prueba."
    print("Mensajes persistidos:", history["total_messages"])

    print_header("RESULTADO")
    print(f"✓ Todas las comprobaciones de contenido, fuentes e historial pasaron ({time.time() - started:.1f}s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pruebas integrales de calidad del RAG SIAE")
    parser.add_argument(
        "--allow-groq-document-context",
        action="store_true",
        help=(
            "confirma que las consultas de prueba pueden enviar a Groq los fragmentos "
            "recuperados de la base local para generar respuestas"
        ),
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="URL base de la API en ejecución (predeterminado: %(default)s)",
    )
    arguments = parser.parse_args()
    if not arguments.allow_groq_document_context:
        print(
            "Esta prueba usa Groq y enviará fragmentos recuperados de documentos locales. "
            "Si autorizas ese envío, vuelve a ejecutarla con "
            "--allow-groq-document-context.",
            file=sys.stderr,
        )
        sys.exit(2)
    try:
        run_pipeline_tests(arguments.base_url)
    except (AssertionError, requests.RequestException) as exc:
        print(f"\n✗ PRUEBA FALLIDA: {exc}", file=sys.stderr)
        sys.exit(1)
