"""Prueba integral del ciclo de vida de un ticket con una base de datos aislada en memoria.

Ejecución: python -m tests.test_tickets
No se necesita un proceso Uvicorn activo, una clave de Groq ni documentos indexados.
"""

from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import GENERIC_CONVERSATION_TITLE, _conversation_topic_title, app
from app.models import Admin, Conversation, Message, User


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    user_id = "ticket-demo-student"
    admin_id = "ticket-demo-admin"
    original_conversation_id = "ticket-demo-original-chat"
    original_message_id = "ticket-demo-original-question"
    base_time = datetime.now(timezone.utc)

    with TestSession() as db:
        db.add_all([
            User(id=user_id, name="Estudiante", lastname="Demo"),
            Admin(
                id=admin_id,
                name="Administradora",
                lastname="Demo",
                email="ticket-demo-admin@example.invalid",
            ),
            Conversation(
                id=original_conversation_id,
                user_id=user_id,
                title="Consulta de ejemplo",
                status="active",
            ),
            Message(
                id="ticket-demo-earlier-disclosure",
                conversation_id=original_conversation_id,
                sender="system",
                content="El usuario escribió: Te paso mi contraseña: Secreta123",
                sent_at=base_time,
            ),
            Message(
                id="ticket-demo-earlier-answer",
                conversation_id=original_conversation_id,
                sender="system",
                content="SIAE indicó que no compartas claves y revises el portal oficial.",
                sent_at=base_time + timedelta(seconds=1),
            ),
            Message(
                id=original_message_id,
                conversation_id=original_conversation_id,
                sender="user",
                content="No pude completar mi registro de servicio social.",
                sent_at=base_time + timedelta(seconds=2),
            ),
            Message(
                id="ticket-demo-initial-answer",
                conversation_id=original_conversation_id,
                sender="system",
                content="SIAE indicó que revisara los requisitos y el portal de servicio social.",
                sent_at=base_time + timedelta(seconds=3),
            ),
        ])
        db.commit()

    def override_get_db():
        with TestSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    # El ciclo normal inicializa la base local y puede lanzar el rastreo automático.
    # La prueba ya prepara una SQLite en memoria, así que reemplaza el ciclo de vida.
    @asynccontextmanager
    async def isolated_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = isolated_lifespan
    client = TestClient(app)
    try:
        # Primero se comprueba que el título se derive del tema y no del saludo.
        print("0. Los títulos distinguen saludos de consultas y tickets.")
        assert _conversation_topic_title(
            ["hola, q tal"], fallback=GENERIC_CONVERSATION_TITLE
        ) == GENERIC_CONVERSATION_TITLE
        chat_title = _conversation_topic_title([
            "hola q pex",
            "¿dónde puedo hacer el registro de servicio social?",
        ])
        assert "servicio social" in chat_title.casefold()
        ticket_title = _conversation_topic_title(
            ["No pude completar mi registro de servicio social."], prefix="Ayuda: "
        )
        assert ticket_title.startswith("Ayuda: ")
        assert "servicio social" in ticket_title.casefold()
        print("   Saludo solo: título genérico; consulta: tema detectado; ticket:", ticket_title)

        print("1. El usuario abre un ticket desde su mensaje original.")
        response = client.post(
            "/tickets/create",
            data={"user_id": user_id, "message_id": original_message_id},
        )
        assert response.status_code == 201, response.text
        ticket = response.json()
        ticket_id = ticket["ticket_id"]
        support_conversation_id = ticket["conversation_id"]
        assert ticket["status"] == "pendiente"
        assert support_conversation_id != original_conversation_id
        assert ticket["title"].startswith("Ayuda: ")
        assert "servicio social" in ticket["title"].casefold()
        print("   Estado:", ticket["status"])
        print("   Chat de soporte:", support_conversation_id)

        print("2. El administrador ve el ticket pendiente en su bandeja.")
        response = client.get(f"/tickets/admin/{admin_id}")
        assert response.status_code == 200, response.text
        assert any(item["ticket_id"] == ticket_id for item in response.json())
        admin_ticket = next(item for item in response.json() if item["ticket_id"] == ticket_id)
        assert admin_ticket["title"] == ticket["title"]
        print("   Tickets activos:", len(response.json()))

        print("3. El administrador toma el ticket.")
        response = client.post(
            f"/tickets/{ticket_id}/claim", data={"admin_id": admin_id}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "en_proceso"
        print("   Estado:", response.json()["status"])

        print("4. Administrador y usuario conversan en el chat separado.")
        # El historial inicial debe acompañar al ticket antes de los mensajes nuevos.
        response = client.post(
            f"/tickets/{ticket_id}/messages",
            data={"admin_id": admin_id, "content": "¿Qué error te aparece al registrarte?"},
        )
        assert response.status_code == 201, response.text
        response = client.post(
            f"/tickets/{ticket_id}/messages",
            data={"user_id": user_id, "content": "El sistema dice que no encuentra mi unidad receptora."},
        )
        assert response.status_code == 201, response.text
        response = client.get(
            f"/tickets/{ticket_id}/messages", params={"user_id": user_id}
        )
        assert response.status_code == 200, response.text
        messages = response.json()["messages"]
        assert [item["sender"] for item in messages] == ["assistant", "admin", "user"]
        assert "Resumen del chat inicial" in messages[0]["content"]
        assert "[Mensaje omitido por seguridad" in messages[0]["content"]
        assert "Secreta123" not in messages[0]["content"], "El resumen no debe copiar credenciales."
        assert "revisara los requisitos" in messages[0]["content"], (
            "El administrador debe ver qué orientación inicial dio SIAE."
        )
        assert "No pude completar mi registro" in messages[0]["content"]
        assert "SIAE indicó" in messages[0]["content"]
        assert response.json()["conversation_id"] == support_conversation_id
        print("   Mensajes del chat:", len(messages), "(contexto inicial → admin → usuario)")

        print("5. El administrador finaliza el caso; el ticket desaparece de su bandeja.")
        response = client.post(
            f"/tickets/{ticket_id}/resolve", data={"admin_id": admin_id}
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "finalizado"
        response = client.get(f"/tickets/admin/{admin_id}")
        assert response.status_code == 200 and not response.json(), response.text
        print("   Estado:", "finalizado")
        print("   Tickets activos para el administrador:", len(response.json()))

        print("6. El usuario conserva el ticket finalizado y su historial de soporte.")
        response = client.get(f"/tickets/user/{user_id}")
        assert response.status_code == 200, response.text
        user_ticket = next(item for item in response.json() if item["ticket_id"] == ticket_id)
        assert user_ticket["status"] == "finalizado"
        assert user_ticket["conversation_id"] == support_conversation_id
        response = client.get(f"/conversations/user/{user_id}")
        assert response.status_code == 200, response.text
        assert any(
            item["conversation_id"] == support_conversation_id
            for item in response.json()
        )
        response = client.get(
            f"/tickets/{ticket_id}/messages", params={"user_id": user_id}
        )
        assert response.status_code == 200 and len(response.json()["messages"]) == 3
        print("   Visible en el historial del usuario:", user_ticket["status"])

        print("7. Un ticket cerrado ya no acepta nuevos mensajes.")
        response = client.post(
            f"/tickets/{ticket_id}/messages",
            data={"user_id": user_id, "content": "Un mensaje después del cierre."},
        )
        assert response.status_code == 409, response.text
        print("   Mensaje rechazado con:", response.status_code)
        print("\n✓ Ciclo completo del ticket correcto.")
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.router.lifespan_context = original_lifespan
        engine.dispose()


if __name__ == "__main__":
    main()
