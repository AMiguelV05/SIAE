"""Puntos de acceso FastAPI para documentos SIAE y el módulo RAG independiente."""

import asyncio
import hashlib
import os
import re
import unicodedata
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session, selectinload

from app.database import SessionLocal, get_db, init_db
from app.ingestion import SUPPORTED_EXTENSIONS, process_and_store_document, sha256_file
from app.models import Admin, Conversation, Doc, Message, MessageSource, Subsection, Ticket, User
from app.rag_engine import query_rag_pipeline, redact_sensitive_disclosure
from app.web_scraper import (
    get_crawl_status,
    process_academic_catalog_crawl,
    process_url_crawl,
    process_url_ingestion,
)

load_dotenv()

# Título provisional que se reemplaza cuando el chat ya tiene un tema identificable.
GENERIC_CONVERSATION_TITLE = "Nueva consulta SIAE"

# Sintaxis de los patrones: ^ exige el inicio; | separa opciones; \s+ acepta espacios;
# ? marca partes opcionales. Las cadenas r"..." consecutivas se unen y se ignoran mayúsculas.
# Los grupos opcionales (?) y las clases como [ií] permiten aceptar variantes de escritura.

# Reconoce saludos en español y variantes regionales de Latinoamérica, además de algunas formas
# comunes en inglés, portugués y otros idiomas cercanos. Solo se aplica al inicio del mensaje:
# limpia el título del chat sin borrar palabras del tema que viene después.
GREETING_PREFIX = re.compile(
    r"^(?:(?:hola+|holi+|hey|hi|ey|oi|buenos?\s+d[ií]as|buenas?(?:\s+(?:tardes|noches))?|"
    r"good\s+(?:morning|afternoon|evening)|bom\s+dia|boa\s+(?:tarde|noite)|"
    r"qu[eé]\s+(?:tal|onda|ondas|pex|pedo|pedos|rollo|show|tranza|transa|"
    r"hubo|hongo|bola|vuelta|fue|hay|xopa|lo\s+que|m[aá]s(?:\s+pues)?|"
    r"me\s+cuentas|pasa|novedades)|q\s+(?:onda|pex|pedo|rollo|show|tranza|"
    r"hubo|bola|vuelta|tal|ondas|hay|fue|cuentas|m[aá]s)|quiubo|klk|pura\s+vida|todo\s+(?:piola|fino|tuanis)|"
    r"c[oó]mo\s+(?:and[aá]s|est[aá]s|va|vas|amaneciste|es)|"
    r"wena(?:\s+po)?|che|diay|ideay|epa(?:le)?|habla(?:\s+causa)?|dime\s+bich[aá]n|"
    r"mbaeichapa|jallalla|wepa|acho|bo|mae|asere|parce|pana|causa|chamo|man[ií]n|"
    r"tudo\s+bem|beleza|e\s+a[ií]|sak\s+pase|nap\s+boule|fa\s+waka|salut|"
    r"qu[eé]\s+es\s+la\s+que\s+hay|saludos)"
    r"[\s,!.?¡¿:;-]*(?:(?:bro|broder|wey|guey|mae|parce|pana|causa|chamo|"
    r"man[ií]n|asere|che|t[ií]o|t[ií]a|bolud[oa]|we[oó]n)[\s,!.?¡¿:;-]*)*)+",
    re.IGNORECASE,
)
# Quita introducciones y frases de cortesía o de problema antes del tema de la consulta.
TITLE_FILLER_PREFIX = re.compile(
    r"^(?:(?:oye|disculpa|una\s+pregunta|una\s+duda|me\s+puedes\s+decir|"
    r"me\s+podr[ií]as\s+decir|podr[ií]as\s+decirme|quisiera\s+saber|"
    r"quiero\s+saber|necesito\s+saber|por\s+favor|me\s+ayudas\s+a|"
    r"ay[uú]dame\s+a|no\s+pude\s+completar|no\s+puedo\s+completar|"
    r"tengo\s+problemas?\s+con|problema\s+con|me\s+falla)[\s,!.?¡¿:;-]*)+",
    re.IGNORECASE,
)
# Quita la forma interrogativa y verbos de intención para dejar el asunto de la pregunta.
TITLE_QUESTION_PREFIX = re.compile(
    r"^(?:(?:como|donde|cuando|cuanto|cual|que|q|k|dime|sabes)\s+)?"
    r"(?:(?:puedo|podria|podrias|debo|deberia|tengo que|necesito|ocupo|hago|"
    r"hacer|realizo|realizar|tramito|tramitar|solicito|solicitar|consulto|"
    r"consultar|encuentro|obtener|averiguar)\s+)*"
    r"(?:(?:el|la|los|las|un|una)\s+)?"
    r"(?:(?:tramite|proceso|procedimiento|requisito|requisitos|paso|pasos|"
    r"forma|manera|informacion)\s+(?:de|para)\s+)?",
    re.IGNORECASE,
)
# Mensajes completos que, tras limpiar prefijos, siguen sin aportar un tema útil para el título.
# Se repiten algunas variantes regionales porque un saludo puede no coincidir con GREETING_PREFIX
# (por ejemplo, por puntuación o escritura informal); así el título permanece como el genérico.
GENERIC_TITLE_TEXTS = {
    "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    "que tal", "q tal", "que onda", "q onda", "q pex", "que pex", "quiubo",
    "necesito ayuda", "me ayudas", "me puedes ayudar", "tengo una duda",
    "tengo una pregunta", "no entiendo", "ayuda",
    "diay", "ideay", "epa", "epale", "mae", "asere", "parce", "pana",
    "causa", "chamo", "manin", "weon", "weona", "boludo", "boluda",
    "jallalla", "mbaeichapa", "klk", "que bola", "que lo que", "que xopa",
    "pura vida", "todo fino", "todo tuanis", "todo piola", "tudo bem", "beleza",
    "e ai", "sak pase", "nap boule", "fa waka", "oi", "salut",
}
# Palabras comunes que no cuentan como tema al evaluar un título; no se borran del texto mostrado.
TITLE_STOPWORDS = {
    "a", "al", "algo", "de", "del", "el", "en", "es", "esta", "este",
    "la", "las", "lo", "los", "me", "mi", "para", "por", "que", "se",
    "sobre", "un", "una", "y", "como", "cuando", "donde", "puedo", "puede",
    "hacer", "hago", "quiero", "necesito", "saber", "decir", "ayuda",
    "necesito", "ayudas", "ayudar", "tengo", "duda", "pregunta", "pude",
}

# Convierte consultas frecuentes a nombres cortos y consistentes en la lista de chats.
# Las expresiones más específicas van primero para no perder el motivo particular del trámite.
TITLE_TOPIC_LABELS = (
    (re.compile(r"\b(practicas?|liberacion)\b.*\b(experiencia laboral|trabajo)\b|"
                r"\b(experiencia laboral|trabajo)\b.*\b(practicas?|liberacion)\b"),
     "Prácticas por experiencia laboral"),
    (re.compile(r"\b(baja voluntaria|darme de baja)\b"), "Baja voluntaria"),
    (re.compile(r"\b(baja de materias|dar de baja materias|bajar materias)\b"),
     "Baja de materias"),
    (re.compile(r"\b(malla curricular|plan de estudios)\b"), "Malla curricular"),
    (re.compile(r"\b(servicio social)\b"), "Servicio social"),
    (re.compile(r"\b(practicas? profesionales?)\b"), "Prácticas profesionales"),
    (re.compile(r"\b(becas?|apoyos economicos?)\b"), "Becas y apoyos"),
    (re.compile(r"\b(bolsa de trabajo|vacantes|ofertas? de trabajo)\b"), "Bolsa de trabajo"),
    (re.compile(r"\b(nuevo ingreso|soy nuevo|soy nueva|primer semestre)\b"), "Nuevo ingreso"),
    (re.compile(r"\b(licenciaturas?|ingenierias?)\b"), "Oferta de licenciaturas"),
    (re.compile(r"\b(maestrias?)\b"), "Oferta de maestrías"),
    (re.compile(r"\b(doctorados?)\b"), "Oferta de doctorados"),
    (re.compile(r"\b(kardex)\b"), "Kardex"),
    (re.compile(r"\b(constancias?|certificados? de estudios)\b"), "Constancias y certificados"),
    (re.compile(r"\b(ubicacion|direccion|mapa|como llegar)\b"), "Ubicación de CUCEI"),
    (re.compile(r"\b(biblioteca|libros electronicos)\b"), "Biblioteca"),
    (re.compile(r"\b(ingles|idiomas?|acreditacion del ingles)\b"), "Idiomas e inglés"),
    (re.compile(r"\b(que dia es|dia es|fecha actual|fecha de hoy|dia de hoy)\b"), "Fecha actual"),
    (re.compile(r"\b(que hora es|hora actual)\b"), "Hora actual"),
)


def _fold_title_text(value: str) -> str:
    # Normaliza acentos para comparar palabras sin depender de cómo se escribieron.
    folded = unicodedata.normalize("NFKD", value.casefold())
    return "".join(char for char in folded if not unicodedata.combining(char))


def _clean_title_candidate(value: str) -> str | None:
    # Quita saludos y frases de cortesía para que el título describa el tema consultado.
    text = " ".join(value.split()).strip()
    text = GREETING_PREFIX.sub("", text)
    text = TITLE_FILLER_PREFIX.sub("", text)
    # Reduce preguntas largas como «¿cómo puedo hacer el trámite de beca?» a su tema.
    text = TITLE_QUESTION_PREFIX.sub("", text)
    text = text.strip(" \t\r\n¿?¡!.,;:-\"'()[]{}")
    if not text:
        return None
    folded = _fold_title_text(text)
    folded_words = re.findall(r"[a-z0-9]+", folded)
    if folded in GENERIC_TITLE_TEXTS:
        return None
    informative_words = [word for word in folded_words if word not in TITLE_STOPWORDS]
    if not informative_words:
        return None
    return text


def _conversation_topic_title(
    user_messages: list[str], *, prefix: str = "", fallback: str | None = None
) -> str:
    """Crea un título breve a partir de los mensajes más informativos del usuario."""
    candidates = [cleaned for item in user_messages if (cleaned := _clean_title_candidate(item))]
    if candidates:
        # Prioriza el tema inicial más claro; usa mensajes posteriores para precisar
        # una apertura ambigua, como un saludo o una pregunta de seguimiento breve.
        topic = max(
            candidates,
            key=lambda item: (
                sum(word not in TITLE_STOPWORDS for word in re.findall(r"[a-z0-9]+", _fold_title_text(item))),
                len(item),
            ),
        )
        # Usa un rótulo legible cuando la pregunta coincide con un trámite o tema conocido.
        folded_topic = _fold_title_text(topic)
        topic = next(
            (label for pattern, label in TITLE_TOPIC_LABELS if pattern.search(folded_topic)),
            topic,
        )
    else:
        topic = fallback or "Consulta"

    max_topic_length = max(1, 50 - len(prefix))
    topic = topic.rstrip(" .?!")
    if len(topic) > max_topic_length:
        truncated = topic[:max_topic_length].rsplit(" ", 1)[0]
        topic = truncated or topic[:max_topic_length]
    topic = topic[:1].upper() + topic[1:]
    return f"{prefix}{topic}"[:50]


def _stored_upload_path(upload_dir: Path, original_name: str, contents: bytes) -> tuple[Path, bool]:
    """Reutiliza una fuente con nombre existente o la guarda una sola vez con su nombre original."""
    # La huella del contenido permite detectar duplicados aunque el nombre sea distinto.
    digest = hashlib.sha256(contents).hexdigest()
    upload_dir.mkdir(parents=True, exist_ok=True)

    matching_named_files = []
    for candidate in upload_dir.iterdir():
        if not candidate.is_file() or candidate.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        try:
            if candidate.stat().st_size != len(contents):
                continue
            if sha256_file(candidate) == digest and not re.fullmatch(r"[0-9a-f]{32}", candidate.stem, re.I):
                matching_named_files.append(candidate)
        except OSError:
            continue
    if matching_named_files:
        return sorted(matching_named_files, key=lambda path: path.name.casefold())[0], False

    # Si ya hay una copia con nombre reconocible, se reutiliza aunque el nombre recibido sea distinto.
    # Quita las rutas de Windows o POSIX que el cliente pudo incluir en el nombre.
    safe_name = original_name.replace("\\", "/").rsplit("/", 1)[-1].strip().rstrip(".")
    # Separa la extensión y limpia el nombre base con las reglas de archivos de Windows.
    suffix = Path(safe_name).suffix.lower()
    stem = Path(safe_name).stem
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", stem).strip(" .")[:160]
    # Un nombre vacío o un UUID no ayuda a identificar el archivo; usa parte de su huella.
    if not stem or re.fullmatch(r"[0-9a-f]{32}", stem, re.I):
        stem = f"documento_{digest[:10]}"
    safe_name = f"{stem}{suffix}"

    candidate = upload_dir / safe_name
    if candidate.exists():
        try:
            # Mismo nombre y mismo contenido: no hace falta guardar otra copia.
            if sha256_file(candidate) == digest:
                return candidate, False
        except OSError:
            pass
        # El nombre ya pertenece a otro contenido; agrega la huella para distinguirlos.
        candidate = upload_dir / f"{stem}_{digest[:10]}{suffix}"
        collision = 2
        while candidate.exists():
            try:
                # También comprueba colisiones con sufijo antes de probar otro nombre.
                if sha256_file(candidate) == digest:
                    return candidate, False
            except OSError:
                pass
            candidate = upload_dir / f"{stem}_{digest[:10]}_{collision}{suffix}"
            collision += 1

    # Escribe el archivo solo cuando no encontró una copia idéntica.
    candidate.write_bytes(contents)
    return candidate, True

@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    # La actualización de fuentes corre en segundo plano mientras la API atiende solicitudes.
    refresh_task = asyncio.create_task(_automatic_public_source_refresh())
    try:
        # FastAPI permanece activa hasta que comienza el apagado.
        yield
    finally:
        # Cancela y espera la tarea periódica para que no quede activa al cerrar la API.
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass


def _refresh_public_sources_once() -> None:
    """Obtiene las fuentes configuradas y vuelve a indexar el contenido que cambió en esta base de datos."""
    from upload_docs import CRAWL_SOURCES, SOURCE_URLS

    db = SessionLocal()
    try:
        print("[fuentes] Iniciando actualización de fuentes públicas...")
        # Las URL individuales se actualizan una por una para que un fallo no detenga las demás.
        for source in SOURCE_URLS:
            try:
                doc = process_url_ingestion(
                    url=source["url"],
                    custom_title=source.get("title"),
                    subsection_id=None,
                    uploaded_by=None,
                    replace_file_name=source.get("replace_file_name"),
                    db=db,
                )
                print(f"[fuentes] {doc.rag_status}: {doc.title}")
            except Exception as exc:
                db.rollback()
                print(f"[fuentes] Error en {source['url']}: {str(exc)[:400]}")

        # Los rastreos recorren enlaces permitidos bajo cada página raíz.
        for source in CRAWL_SOURCES:
            try:
                print(
                    f"[fuentes] Iniciando rastreo: {source.get('title') or source['url']}",
                    flush=True,
                )
                if source.get("strategy") == "academic_catalog":
                    result = process_academic_catalog_crawl(
                        catalog_url=source["url"],
                        catalog_title=source.get("title"),
                        program_path_prefix=source["program_path_prefix"],
                        max_pages_per_program=source.get("max_pages_per_program", 60),
                        max_depth=source.get("max_depth", 2),
                        subsection_id=None,
                        uploaded_by=None,
                        db=db,
                    )
                    print(
                        f"[fuentes] Catálogo académico {source['url']}: "
                        f"{result['programs_found']} programas detectados, "
                        f"{result['pages_indexed']} páginas indexadas, "
                        f"{result['pages_failed']} fallidas, "
                        f"{result.get('programs_limit_reached', 0)} programas alcanzaron el límite."
                    )
                    for failure in result.get("failures", []):
                        print(f"[fuentes] Error en {failure['url']}: {failure['error'][:300]}")
                    continue
                prefixes = source.get("allowed_path_prefixes", [])
                if isinstance(prefixes, str):
                    prefixes = [item.strip() for item in prefixes.split(",") if item.strip()]
                result = process_url_crawl(
                    root_url=source["url"],
                    root_title=source.get("title"),
                    allowed_path_prefixes=prefixes,
                    max_pages=source.get("max_pages", 50),
                    max_depth=source.get("max_depth", 1),
                    subsection_id=None,
                    uploaded_by=None,
                    db=db,
                )
                print(
                    f"[fuentes] Rastreo {source['url']}: "
                    f"{result['pages_indexed']} páginas indexadas, "
                    f"{result['pages_failed']} fallidas, "
                    f"límite alcanzado={result.get('limit_reached', False)}, "
                    f"pendientes={result.get('pending_pages', 0)}."
                )
                for failure in result.get("failures", []):
                    print(f"[fuentes] Error en {failure['url']}: {failure['error'][:300]}")
            except Exception as exc:
                db.rollback()
                print(f"[fuentes] Error rastreando {source['url']}: {str(exc)[:400]}")
    finally:
        db.close()


async def _automatic_public_source_refresh() -> None:
    """Actualiza en segundo plano las fuentes públicas según el intervalo configurado."""
    enabled = os.getenv("SIAE_AUTO_REFRESH_SOURCES", "true").casefold() not in {
        "0", "false", "no", "off"
    }
    if not enabled:
        return
    # El retraso deja que la API termine de iniciar antes de consultar sitios externos.
    initial_delay = max(0, int(os.getenv("SIAE_SOURCE_REFRESH_START_DELAY_SECONDS", "30")))
    interval_hours = max(1, int(os.getenv("SIAE_SOURCE_REFRESH_HOURS", "96")))
    await asyncio.sleep(initial_delay)
    while True:
        try:
            await asyncio.to_thread(_refresh_public_sources_once)
        except Exception as exc:
            print(f"[fuentes] La actualización automática falló: {str(exc)[:500]}")
        await asyncio.sleep(interval_hours * 60 * 60)


# Metadatos visibles en la documentación automática de la API; lifespan gestiona inicio y apagado.
app = FastAPI(
    title="SIAE - Backend de documentos y asistente RAG",
    description="API local para indexar fuentes de CUCEI, responder con citas y registrar consultas.",
    version="1.1.0",
    lifespan=lifespan,
)

# Lee desde qué direcciones web se permiten llamadas del navegador; usa estos valores por defecto.
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://localhost:5173"
    ).split(",")
    if origin.strip()
]
# CORS habilita solicitudes del frontend y restringe métodos, encabezados y orígenes permitidos.
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,  # Permite que el navegador incluya credenciales en la solicitud.
    allow_methods=["GET", "POST"],  # Métodos HTTP que puede usar el frontend.
    allow_headers=["*"],  # Acepta los encabezados que envíe el frontend.
)


def _ensure_local_user(db: Session, user_id: str) -> User:
    if not user_id.strip():
        raise HTTPException(status_code=422, detail="user_id no puede estar vacío.")
    user = db.get(User, user_id)
    if user is None:
        # Un usuario local provisional permite usar la API RAG antes de implementar la autenticación.
        user = User(id=user_id, name="Usuario local", lastname="")
        db.add(user)
        db.flush()
    return user


def _ensure_local_admin(db: Session, admin_id: str) -> Admin:
    if not admin_id.strip():
        raise HTTPException(status_code=422, detail="admin_id no puede estar vacío.")
    admin = db.get(Admin, admin_id)
    if admin is None:
        # Identidad solo para desarrollo, acorde con el flujo del usuario local provisional.
        admin = Admin(
            id=admin_id,
            name="Administrador",
            lastname="local",
            email=f"{admin_id}@local.invalid",
            role="admin",
        )
        db.add(admin)
        db.flush()
    if not admin.is_active:
        raise HTTPException(status_code=403, detail="La cuenta administrativa está inactiva.")
    return admin


def _validate_subsection(db: Session, subsection_id: str | None) -> None:
    if subsection_id and db.get(Subsection, subsection_id) is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "subsections_id no existe todavía. Omítelo en modo independiente o crea "
                "la subsección desde SQL cuando esté disponible el catálogo institucional."
            ),
        )


@app.get("/")
def read_root():
    # Endpoint informativo con el estado general y enlaces básicos de la API.
    return {
        "status": "online",
        "system": "Sistema Integral de Asistencia Estudiantil (SIAE) - CUCEI",
        "docs_url": "/docs",
        "module": "RAG y gestión de documentos",
    }


@app.get("/health")
def health_check():
    # Comprobación simple para confirmar que el servidor responde.
    return {"status": "ok"}


@app.get("/docs/crawl-status")
def crawl_status():
    # Permite ver en Swagger qué parte del sitio se está procesando y qué falló.
    return get_crawl_status()


@app.post("/conversations/new", status_code=status.HTTP_201_CREATED)
def create_conversation(
    user_id: str = Form("local-demo-user"),
    db: Session = Depends(get_db),
):
    # Crea el usuario provisional si aún no existe y asocia el chat con él.
    _ensure_local_user(db, user_id)
    conversation = Conversation(
        # Cada conversación recibe un identificador único y comienza activa.
        id=str(uuid.uuid4()),
        user_id=user_id,
        # Los chats comienzan con el título genérico; /messages/ask lo actualiza
        # cuando identifica un tema en los primeros mensajes del usuario.
        title=GENERIC_CONVERSATION_TITLE,
        status="active",
    )
    # Guarda el registro y vuelve a cargarlo para obtener valores generados por la base.
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return {
        "conversation_id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "created_at": conversation.created_at,
    }


@app.get("/conversations/user/{user_id}")
def get_user_conversations(user_id: str, db: Session = Depends(get_db)):
    # Solo se muestran chats activos; los más recientes aparecen primero.
    conversations = (
        db.query(Conversation)
        .filter(
            Conversation.user_id == user_id,
            Conversation.status == "active",
        )
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "conversation_id": item.id,
            "title": item.title,
            "created_at": item.created_at,
        }
        for item in conversations
    ]


@app.get("/conversations/{conversation_id}/messages")
def get_conversation_messages(conversation_id: str, db: Session = Depends(get_db)):
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="No existe esa conversación.")
    # Carga las citas junto con cada mensaje para evitar consultas repetidas a la base.
    messages = (
        db.query(Message)
        .options(selectinload(Message.sources))
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    return {
        "conversation_id": conversation_id,
        "total_messages": len(messages),
        "messages": [
            {
                "message_id": message.id,
                "sender": "assistant" if message.sender == "system" else message.sender,
                # Oculta credenciales que pudieran existir en conversaciones guardadas antes de esta protección.
                "content": redact_sensitive_disclosure(message.content),
                "sent_at": message.sent_at,
                "citations": [
                    {
                        "document_id": source.document_id,
                        "chunk_id": source.document_chunk_id,
                        "rank": source.rank,
                        "similarity_score": source.similarity_score,
                    }
                    for source in message.sources
                ],
            }
            for message in messages
        ],
    }


@app.post("/messages/ask")
def ask_question(
    question: str = Form(...),
    user_id: str = Form("local-demo-user"),
    conversation_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    question = question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="question no puede estar vacía.")
    _ensure_local_user(db, user_id)

    conversation = db.get(Conversation, conversation_id) if conversation_id else None
    if conversation_id and conversation is None:
        raise HTTPException(status_code=404, detail="No existe esa conversación.")
    if conversation and conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="La conversación pertenece a otro usuario.")
    if conversation is None:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            title=GENERIC_CONVERSATION_TITLE,
            status="active",
        )
        db.add(conversation)
        db.flush()

    previous_messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation.id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    # El RAG recibe un historial corto; la búsqueda decide si el último turno continúa el tema.
    history = [
        {
            "role": "user" if message.sender == "user" else "assistant",
            # No reutiliza credenciales que pudieran haberse guardado en mensajes antiguos.
            "content": redact_sensitive_disclosure(message.content),
        }
        for message in previous_messages[-6:]
        if message.sender in {"user", "system"}
    ]

    # top_k fijo mantiene una cantidad estable de fragmentos para las consultas de la API.
    try:
        result = query_rag_pipeline(
            question=question,
            history=history,
            top_k=6,
            db=db,
        )
    except (RuntimeError, ValueError) as exc:
        db.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail=f"No se pudo completar la consulta al servicio de IA: {exc}",
        ) from exc

    # Asigna identificadores distintos para vincular la pregunta, la respuesta y sus citas.
    user_message_id = str(uuid.uuid4())
    assistant_message_id = str(uuid.uuid4())
    # Si el mensaje incluía una credencial, solo conserva una nota segura en el historial.
    stored_question = redact_sensitive_disclosure(question)
    # Guarda la pregunta y la respuesta como mensajes separados de la misma conversación.
    db.add_all(
        [
            Message(
                id=user_message_id,
                conversation_id=conversation.id,
                sender="user",
                content=stored_question,
            ),
            Message(
                id=assistant_message_id,
                conversation_id=conversation.id,
                sender="system",
                content=result["answer"],
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
                total_tokens=result.get("total_tokens", 0),
                response_time_seconds=result.get("response_time_seconds", 0),
            ),
        ]
    )
    # Hace visibles los mensajes pendientes para consultar el tema antes del commit final.
    db.flush()
    if conversation.title == GENERIC_CONVERSATION_TITLE:
        # Usa hasta los primeros tres mensajes del usuario para obtener un título informativo.
        first_user_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation.id,
                Message.sender == "user",
            )
            .order_by(Message.sent_at.asc(), Message.id.asc())
            .limit(3)
            .all()
        )
        conversation.title = _conversation_topic_title(
            [redact_sensitive_disclosure(message.content) for message in first_user_messages],
            fallback=GENERIC_CONVERSATION_TITLE,
        )
    # Registra qué fragmentos respaldaron la respuesta, conservando su orden y relevancia.
    for citation in result.get("citations", []):
        db.add(
            MessageSource(
                id=str(uuid.uuid4()),
                message_id=assistant_message_id,
                document_id=citation["document_id"],
                document_chunk_id=citation["chunk_id"],
                similarity_score=citation["relevance_score"],
                rank=citation["rank"],
            )
        )
    # Actualiza la actividad del chat y guarda juntos los mensajes, las citas y el título.
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()

    # Devuelve al cliente los datos necesarios para mostrar la respuesta y sus fuentes.
    return {
        "conversation_id": conversation.id,
        "conversation_title": conversation.title,
        "user_message_id": user_message_id,
        "message_id": assistant_message_id,
        "answer": result["answer"],
        "citations": result["citations"],
        "response_time_seconds": result["response_time_seconds"],
        "history_used": result.get("history_used", False),
    }


@app.post("/docs/upload", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    category: str = Form("reglamento"),
    subsections_id: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Recibe un archivo y metadatos opcionales como formulario para indexarlo en el RAG."""
    # Reduce el nombre a su archivo base antes de comprobar la extensión permitida.
    original_name = (file.filename or "documento").replace("\\", "/").rsplit("/", 1)[-1]
    extension = Path(original_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Formato no soportado. Usa: {', '.join(sorted(SUPPORTED_EXTENSIONS))}.",
        )

    # Lee como máximo el límite más un byte para detectar archivos demasiado grandes.
    max_bytes = int(os.getenv("MAX_UPLOAD_MB", "25")) * 1024 * 1024
    contents = file.file.read(max_bytes + 1)
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail="El archivo supera el límite configurado.")
    if not contents:
        raise HTTPException(status_code=422, detail="El archivo está vacío.")
    # Comprueba que las relaciones opcionales existan antes de iniciar la ingesta.
    _validate_subsection(db, subsections_id)
    if uploaded_by:
        _ensure_local_user(db, uploaded_by)

    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    stored_path, created_file = _stored_upload_path(upload_dir, original_name, contents)
    try:
        # Extrae el contenido, lo divide en fragmentos y guarda sus vectores en la base.
        doc = process_and_store_document(
            file_path=stored_path,
            title=title or Path(original_name).stem,
            category=category,
            subsection_id=subsections_id,
            original_filename=original_name,
            uploaded_by=uploaded_by,
            db=db,
        )
        # Guarda la ruta absoluta para que el registro apunte al archivo real en disco.
        canonical_path = str(stored_path.resolve())
        if doc.storage_in != canonical_path:
            doc.storage_in = canonical_path
            db.commit()
            db.refresh(doc)
    except Exception as exc:
        db.rollback()
        # Si esta solicitud creó el archivo y falló la ingesta, elimina el archivo que quedó sin indexar.
        if created_file:
            stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"No se pudo indexar el documento: {exc}") from exc
    return {
        "document_id": doc.id,
        "title": doc.title,
        "rag_status": doc.rag_status,
        "message": "Documento indexado.",
    }


@app.post("/docs/upload-url", status_code=status.HTTP_201_CREATED)
def upload_document_url(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    subsections_id: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    replace_file_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Descarga e indexa una fuente pública indicada por URL."""
    # Valida los datos locales opcionales antes de descargar la fuente externa.
    _validate_subsection(db, subsections_id)
    if uploaded_by:
        _ensure_local_user(db, uploaded_by)
    try:
        # El ingestor determina el formato de la respuesta y aplica el lector correspondiente.
        doc = process_url_ingestion(
            url=url,
            custom_title=title,
            subsection_id=subsections_id,
            uploaded_by=uploaded_by,
            db=db,
            replace_file_name=replace_file_name,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"No se pudo indexar la URL: {exc}") from exc
    return {
        "document_id": doc.id,
        "title": doc.title,
        "rag_status": doc.rag_status,
        "message": "Fuente indexada.",
    }


@app.post("/docs/crawl-url")
def crawl_document_urls(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    allowed_path_prefixes: str = Form("/carreras/"),
    max_pages: int = Form(50, ge=1, le=100),
    max_depth: int = Form(1, ge=0, le=2),
    subsections_id: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Rastrea e indexa páginas enlazadas desde una URL dentro de límites definidos.
    url es la página de inicio; title permite asignarle un título personalizado.
    allowed_path_prefixes restringe qué rutas enlazadas se visitan. max_pages y
    max_depth limitan la cantidad de páginas y niveles recorridos. subsections_id
    y uploaded_by son metadatos opcionales; db es la sesión de base de datos.
    """
    _validate_subsection(db, subsections_id)
    if uploaded_by:
        _ensure_local_user(db, uploaded_by)
    # Convierte la lista separada por comas a prefijos individuales para el rastreador.
    prefixes = [prefix.strip() for prefix in allowed_path_prefixes.split(",") if prefix.strip()]
    try:
        return process_url_crawl(
            root_url=url,
            root_title=title,
            allowed_path_prefixes=prefixes,
            max_pages=max_pages,
            max_depth=max_depth,
            subsection_id=subsections_id,
            uploaded_by=uploaded_by,
            db=db,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"No se pudo rastrear la URL: {exc}") from exc


@app.post("/docs/crawl-academic-catalog")
def crawl_academic_catalog(
    url: str = Form(...),
    title: Optional[str] = Form(None),
    program_path_prefix: str = Form(...),
    max_pages_per_program: int = Form(60, ge=1, le=100),
    max_depth: int = Form(2, ge=0, le=2),
    subsections_id: Optional[str] = Form(None),
    uploaded_by: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Indexa un catálogo y recorre por separado las páginas de cada programa y sus subsecciones."""
    _validate_subsection(db, subsections_id)
    if uploaded_by:
        _ensure_local_user(db, uploaded_by)
    try:
        return process_academic_catalog_crawl(
            catalog_url=url,
            catalog_title=title,
            program_path_prefix=program_path_prefix,
            max_pages_per_program=max_pages_per_program,
            max_depth=max_depth,
            subsection_id=subsections_id,
            uploaded_by=uploaded_by,
            db=db,
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=f"No se pudo rastrear el catálogo académico: {exc}") from exc


@app.get("/documents")
def list_documents(db: Session = Depends(get_db)):
    # Incluye los fragmentos para informar cuántos bloques se pueden recuperar en el RAG.
    documents = (
        db.query(Doc)
        .options(selectinload(Doc.chunks))
        .order_by(Doc.uploaded_at.desc())
        .all()
    )
    return [
        {
            "document_id": doc.id,
            "title": doc.title,
            "file_name": doc.file_name,
            "source_url": doc.storage_in if doc.storage_in.startswith(("http://", "https://")) else None,
            "rag_status": doc.rag_status,
            "uploaded_at": doc.uploaded_at,
            "chunks": len(doc.chunks),
        }
        for doc in documents
    ]


def _build_ticket_chat_context(
    db: Session,
    original_conversation_id: str,
    opening_message_id: str,
) -> str:
    """Crea un resumen breve y fiel de la conversación sin llamar a un LLM."""
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == original_conversation_id)
        .order_by(Message.sent_at.asc(), Message.id.asc())
        .all()
    )
    opening_index = next(
        (index for index, message in enumerate(messages) if message.id == opening_message_id),
        None,
    )
    if opening_index is None:
        return "Resumen del chat inicial: no se encontró el mensaje de origen."

    context = messages[: opening_index + 1]
    # Incluye la respuesta del asistente a la pregunta elegida, pero se detiene antes
    # de un mensaje posterior del usuario para excluir del ticket temas no relacionados.
    for message in messages[opening_index + 1 :]:
        if message.sender == "user":
            break
        context.append(message)
        if message.sender == "system":
            break

    omitted_count = max(0, len(context) - 20)
    # Conserva como máximo veinte mensajes recientes antes de aplicar el límite de caracteres.
    context = context[-20:]
    lines = []
    # Etiqueta cada intervención para que el administrador distinga al usuario de SIAE.
    for message in context:
        speaker = "Usuario" if message.sender == "user" else (
            "SIAE" if message.sender == "system" else "Administrador"
        )
        # El resumen del ticket tampoco debe copiar una credencial de mensajes antiguos.
        content = " ".join(redact_sensitive_disclosure(message.content or "").split())
        lines.append(f"{speaker}: {content}")

    header = "Resumen del chat inicial (extracto cronológico; texto original, sin generar hechos nuevos):"
    if omitted_count:
        lines.insert(0, f"[{omitted_count} mensajes anteriores omitidos por longitud]")
    max_chars = 9000
    history_trimmed = False
    # Reduce el contexto desde el comienzo para priorizar los mensajes cercanos al problema.
    max_body_chars = max_chars - len(header) - 80
    while len(lines) > 1 and sum(map(len, lines)) + len(lines) > max_body_chars:
        lines.pop(0)
        history_trimmed = True
    if history_trimmed:
        lines.insert(0, "[Se omitió parte del historial anterior por longitud]")
    if lines and len(lines[-1]) > max_body_chars:
        lines[-1] = lines[-1][: max_body_chars - 3].rstrip() + "..."
    return header + "\n" + "\n".join(lines)


def _ticket_title(db: Session, ticket: Ticket) -> str:
    # El título vive en la conversación de soporte vinculada al ticket.
    support_chat = db.get(Conversation, ticket.conversation_id) if ticket.conversation_id else None
    return support_chat.title if support_chat and support_chat.title else "Ayuda: Seguimiento de consulta"


@app.post("/tickets/create", status_code=status.HTTP_201_CREATED)
def create_ticket(
    user_id: str = Form("local-demo-user"),
    message_id: str = Form(...),
    subsection_id: Optional[str] = Form(None),
    file: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Abre un ticket y un chat de soporte a partir de un mensaje del usuario."""
    _ensure_local_user(db, user_id)
    _validate_subsection(db, subsection_id)
    original_message = db.get(Message, message_id)
    if original_message is None or original_message.sender != "user":
        raise HTTPException(status_code=404, detail="No existe el mensaje asociado al ticket.")
    original_conversation = db.get(Conversation, original_message.conversation_id)
    # Impide abrir tickets desde mensajes que pertenecen a la conversación de otra persona.
    if original_conversation is None or original_conversation.user_id != user_id:
        raise HTTPException(status_code=403, detail="El mensaje no pertenece a este usuario.")

    # Crea un chat de soporte independiente para que el administrador atienda el caso
    # sin mezclar los mensajes de soporte humano con la conversación RAG del estudiante.
    support_conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title="Nueva consulta SIAE",
        status="active",
    )
    # El título se basa en hasta tres preguntas recientes para reflejar mejor el motivo de ayuda.
    recent_user_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == original_conversation.id,
            Message.sender == "user",
        )
        .order_by(Message.sent_at.desc(), Message.id.desc())
        .limit(3)
        .all()
    )
    support_conversation.title = _conversation_topic_title(
        [message.content for message in recent_user_messages],
        prefix="Ayuda: ",
        fallback="Seguimiento de consulta",
    )
    db.add(support_conversation)
    # Guarda primero el chat de soporte para poder asociarle sus mensajes y el ticket.
    db.flush()
    # El primer mensaje conserva contexto del chat original dentro del hilo de soporte.
    db.add(Message(
        id=str(uuid.uuid4()),
        conversation_id=support_conversation.id,
        sender="system",
        content=_build_ticket_chat_context(
            db,
            original_conversation.id,
            original_message.id,
        ),
    ))
    ticket = Ticket(
        id=str(uuid.uuid4()),
        user_id=user_id,
        message_id=message_id,
        conversation_id=support_conversation.id,
        subsection_id=subsection_id,
        file=file,
        status="pendiente",
    )
    # El ticket queda pendiente hasta que un administrador lo tome.
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return {
        "ticket_id": ticket.id,
        "conversation_id": ticket.conversation_id,
        "title": support_conversation.title,
        "status": ticket.status,
        "created_at": ticket.created_at,
        "message": "Ticket creado. Se abrió un chat de atención separado.",
    }


@app.get("/tickets/user/{user_id}")
def get_user_tickets(user_id: str, db: Session = Depends(get_db)):
    # A diferencia de la bandeja del administrador, el usuario conserva también los finalizados.
    tickets = db.query(Ticket).filter(Ticket.user_id == user_id).order_by(Ticket.created_at.desc()).all()
    return [
        {
            "ticket_id": ticket.id,
            "message_id": ticket.message_id,
            "conversation_id": ticket.conversation_id,
            "title": _ticket_title(db, ticket),
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
            "resolved_at": ticket.resolved_at,
        }
        for ticket in tickets
    ]


@app.get("/tickets/admin/{admin_id}")
def get_admin_tickets(admin_id: str, db: Session = Depends(get_db)):
    """Lista los tickets que debe atender el administrador; los finalizados salen de esta bandeja."""
    _ensure_local_admin(db, admin_id)
    # Muestra tickets abiertos sin asignar o asignados a este administrador.
    tickets = (
        db.query(Ticket)
        .filter(
            Ticket.status != "finalizado",
            (Ticket.admin_id.is_(None)) | (Ticket.admin_id == admin_id),
        )
        .order_by(Ticket.created_at.asc())
        .all()
    )
    return [
        {
            "ticket_id": ticket.id,
            "user_id": ticket.user_id,
            "message_id": ticket.message_id,
            "conversation_id": ticket.conversation_id,
            "title": _ticket_title(db, ticket),
            "status": ticket.status,
            "created_at": ticket.created_at,
            "updated_at": ticket.updated_at,
        }
        for ticket in tickets
    ]


@app.post("/tickets/{ticket_id}/claim")
def claim_ticket(
    ticket_id: str,
    admin_id: str = Form(...),
    db: Session = Depends(get_db),
):
    """Asigna al administrador el ticket indicado y lo cambia a estado en_proceso."""
    _ensure_local_admin(db, admin_id)
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="No existe ese ticket.")
    if ticket.status == "finalizado":
        raise HTTPException(status_code=409, detail="El ticket ya está finalizado.")
    if ticket.admin_id not in (None, admin_id):
        raise HTTPException(status_code=409, detail="Otro administrador ya tomó este ticket.")
    # La asignación evita que dos administradores atiendan el mismo caso a la vez.
    ticket.admin_id = admin_id
    # La toma cambia el estado para distinguirlo de los casos aún pendientes.
    ticket.status = "en_proceso"
    ticket.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ticket_id": ticket.id, "status": ticket.status, "admin_id": ticket.admin_id}


def _ticket_for_participant(
    ticket_id: str,
    db: Session,
    *,
    user_id: str | None = None,
    admin_id: str | None = None,
) -> Ticket:
    # Centraliza la validación para que usuario y administrador accedan solo a sus tickets.
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="No existe ese ticket.")
    if user_id:
        if ticket.user_id != user_id:
            raise HTTPException(status_code=403, detail="El ticket pertenece a otro usuario.")
    elif admin_id:
        if ticket.admin_id != admin_id:
            raise HTTPException(status_code=403, detail="El ticket no está asignado a este administrador.")
    else:
        raise HTTPException(status_code=422, detail="Indica user_id o admin_id.")
    if not ticket.conversation_id:
        raise HTTPException(status_code=409, detail="El ticket antiguo no tiene chat de atención asociado.")
    return ticket


@app.get("/tickets/{ticket_id}/messages")
def get_ticket_messages(
    ticket_id: str,
    user_id: Optional[str] = None,
    admin_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Devuelve el historial del chat de soporte al usuario dueño o al administrador asignado."""
    # La validación confirma que quien consulta sea el usuario dueño o el administrador asignado.
    ticket = _ticket_for_participant(
        ticket_id, db, user_id=user_id, admin_id=admin_id
    )
    # Ordena el hilo desde el mensaje de contexto inicial hasta el intercambio más reciente.
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == ticket.conversation_id)
        .order_by(Message.sent_at.asc())
        .all()
    )
    return {
        "ticket_id": ticket.id,
        "conversation_id": ticket.conversation_id,
        "status": ticket.status,
        "messages": [
            {
                "message_id": message.id,
                # La API presenta los mensajes del sistema como respuestas del asistente.
                "sender": "assistant" if message.sender == "system" else message.sender,
                "admin_id": message.admin_id,
                # También protege el historial del ticket si un mensaje antiguo contenía datos de acceso.
                "content": redact_sensitive_disclosure(message.content),
                "sent_at": message.sent_at,
            }
            for message in messages
        ],
    }


@app.post("/tickets/{ticket_id}/messages", status_code=status.HTTP_201_CREATED)
def send_ticket_message(
    ticket_id: str,
    content: str = Form(...),
    user_id: Optional[str] = Form(None),
    admin_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    """Agrega un mensaje al chat de soporte si el ticket sigue abierto."""
    # Quita espacios sobrantes y rechaza mensajes vacíos antes de consultar la base.
    content = content.strip()
    if not content:
        raise HTTPException(status_code=422, detail="content no puede estar vacío.")
    ticket = _ticket_for_participant(
        ticket_id, db, user_id=user_id, admin_id=admin_id
    )
    # Un ticket finalizado conserva su historial, pero ya no acepta nuevos mensajes.
    if ticket.status == "finalizado":
        raise HTTPException(status_code=409, detail="El ticket ya está finalizado.")

    # El rol del remitente se determina por el identificador que acompañó la solicitud.
    if admin_id:
        _ensure_local_admin(db, admin_id)
        sender = "admin"
    else:
        _ensure_local_user(db, user_id or "")
        sender = "user"
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=ticket.conversation_id,
        admin_id=admin_id if sender == "admin" else None,
        sender=sender,
        content=content,
    )
    ticket.updated_at = datetime.now(timezone.utc)
    db.add(message)
    db.commit()
    db.refresh(message)
    return {
        "ticket_id": ticket.id,
        "message_id": message.id,
        "conversation_id": ticket.conversation_id,
        "sender": sender,
        "status": ticket.status,
        "sent_at": message.sent_at,
    }


@app.post("/tickets/{ticket_id}/resolve")
def resolve_ticket(
    ticket_id: str,
    admin_id: str = Form(...),
    db: Session = Depends(get_db),
):
    _ensure_local_admin(db, admin_id)
    ticket = _ticket_for_participant(ticket_id, db, admin_id=admin_id)
    if ticket.status == "finalizado":
        return {"ticket_id": ticket.id, "status": ticket.status, "resolved_at": ticket.resolved_at}
    # El cambio de estado lo retira de la bandeja activa del administrador.
    # Usa el mismo instante para actualizar la última actividad y registrar el cierre.
    now = datetime.now(timezone.utc)
    ticket.status = "finalizado"
    ticket.resolved_at = now
    ticket.updated_at = now
    db.commit()
    return {"ticket_id": ticket.id, "status": ticket.status, "resolved_at": ticket.resolved_at}
