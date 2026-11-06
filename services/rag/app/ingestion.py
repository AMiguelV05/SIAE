"""Extrae, divide, vectoriza y guarda documentos locales para el índice RAG."""

import base64
import hashlib
import io
import json
import os
import re
import unicodedata
import uuid
import zipfile
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from PIL import Image
from pypdf import PdfReader
import pypdfium2 as pdfium
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.embeddings import embed_documents
from app.models import Doc, DocumentChunk

load_dotenv()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | {".pdf", ".docx"}
DEFAULT_CHUNK_WORDS = 100
DEFAULT_CHUNK_OVERLAP_WORDS = 20
MIN_NATIVE_PDF_TEXT_CHARS = 60
PDF_OCR_MIN_IMAGE_PIXELS = max(1, int(os.getenv("PDF_OCR_MIN_IMAGE_PIXELS", "250000")))
# Cambiar esta versión fuerza a distinguir los documentos procesados con otra lógica de ingesta.
INGESTION_PIPELINE_VERSION = "structured-v2"

# Relaciona cada nombre de mes en español con su número para interpretar fechas escritas.
_MONTHS_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5,
    "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9,
    "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}
# Formatos de fecha que se aceptan: año-mes-día, día/mes/año o fecha escrita con palabras.
_DATE_VALUE = (
    r"(?P<iso>20\d{2}-\d{1,2}-\d{1,2})|"
    r"(?P<slash>\d{1,2}[/-]\d{1,2}[/-]20\d{2})|"
    r"(?P<text>\d{1,2}\s+de\s+[a-záéíóú]+\s+de\s+20\d{2})"
)


def _parse_date_value(value: str) -> str | None:
    # Convierte las fechas reconocidas al formato estándar AAAA-MM-DD.
    value = " ".join(value.casefold().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").split())
    try:
        if re.fullmatch(r"20\d{2}-\d{1,2}-\d{1,2}", value):
            return date.fromisoformat(value).isoformat()
        if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]20\d{2}", value):
            day, month, year = map(int, re.split(r"[/-]", value))
            return date(year, month, day).isoformat()
        match = re.fullmatch(r"(\d{1,2}) de ([a-z]+) de (20\d{2})", value)
        if match and match.group(2) in _MONTHS_ES:
            return date(int(match.group(3)), _MONTHS_ES[match.group(2)], int(match.group(1))).isoformat()
    except ValueError:
        try:
            return date.fromisoformat(value[:10]).isoformat()
        except ValueError:
            return None
    return None


def derive_source_metadata(title: str, source: str, content: str) -> dict:
    """Deduce el alcance de la fuente y sus fechas explícitas sin asumir que la ingesta indica actualidad."""
    # El alcance y las fechas se infieren del contenido; no se usa la fecha de carga como fecha oficial.
    host = re.sub(r"^https?://", "", source.casefold()).split("/", 1)[0].split(":", 1)[0]
    identity = f"{title} {source} {content[:100_000]}".casefold()
    normalized_identity = "".join(
        char for char in unicodedata.normalize("NFKD", identity)
        if not unicodedata.combining(char)
    )
    if (
        re.search(r"(^|\.)cucei\.udg\.mx$", host)
        or "cucei" in f"{title} {source}".casefold()
        or "centro universitario de ciencias exactas e ingenierias" in normalized_identity
        or normalized_identity.count("cucei") >= 3
    ):
        scope = "cucei"
    elif "udg.mx" in host or re.search(r"\b(universidad de guadalajara|udeg)\b", normalized_identity):
        scope = "udeg_general"
    else:
        scope = "unknown"

    text = normalized_identity[:250_000]
    date_patterns = {
        "updated_date": re.compile(r"(?:ultima\s+actualizacion|actualizado(?:\s+el)?|actualizada(?:\s+el)?|modificado(?:\s+el)?|modificada(?:\s+el)?)[^\n\r]{0,80}?" + _DATE_VALUE, re.I),
        "effective_date": re.compile(r"(?:vigencia|vigente\s+a\s+partir\s+de|entra\s+en\s+vigor\s+el)[^\n\r]{0,80}?" + _DATE_VALUE, re.I),
        "publication_date": re.compile(r"(?:fecha\s+de\s+publicacion|publicado(?:\s+el)?|publicada(?:\s+el)?|fecha)[^\n\r]{0,80}?" + _DATE_VALUE, re.I),
    }
    result = {"source_scope": scope}
    for key, pattern in date_patterns.items():
        for match in pattern.finditer(text):
            raw_date = next((match.group(name) for name in ("iso", "slash", "text") if match.group(name)), None)
            parsed = _parse_date_value(raw_date) if raw_date else None
            if parsed:
                result[key] = parsed
                break

    # También reconoce periodos académicos o ediciones con año, aunque no indiquen día y mes.
    # «2025B» se representa como agosto de 2025 para poder ordenarlo frente a «2025A».
    period_pattern = re.compile(
        r"\b(?:ciclo|periodo|calendario|semestre|convocatoria|edicion|curso)"
        r"[^\n\r]{0,40}?(20\d{2})\s*([ab])?\b",
        re.I,
    )
    period_dates = []
    for match in period_pattern.finditer(text):
        year = int(match.group(1))
        term = (match.group(2) or "").casefold()
        month = 8 if term == "b" else 1
        period_dates.append(date(year, month, 1).isoformat())

    # Si el contenido no nombra un periodo, un año en el título puede identificar su edición.
    normalized_title = "".join(
        char for char in unicodedata.normalize("NFKD", title.casefold())
        if not unicodedata.combining(char)
    )
    title_period = re.search(r"\b(20\d{2})\s*([ab])?\b", normalized_title)
    if title_period:
        year = int(title_period.group(1))
        month = 8 if (title_period.group(2) or "").casefold() == "b" else 1
        period_dates.append(date(year, month, 1).isoformat())
    if period_dates:
        result["content_period_date"] = max(period_dates)

    # Conserva como referencia comparativa la fecha explícita más reciente de la fuente.
    declared_dates = [
        result[key]
        for key in (
            "updated_date",
            "publication_date",
            "effective_date",
            "content_period_date",
        )
        if result.get(key)
    ]
    if declared_dates:
        result["recency_date"] = max(declared_dates)
    return result


def _versioned_hash(source_hash: str) -> str:
    # Incluye la versión del proceso para poder reindexar si cambia la forma de extraer o dividir.
    return hashlib.sha256(
        f"{INGESTION_PIPELINE_VERSION}:{source_hash}".encode("utf-8")
    ).hexdigest()


def _is_generated_filename(filename: str) -> bool:
    # Reconoce nombres UUID que suelen asignarse a archivos sin nombre original.
    return bool(re.fullmatch(r"[0-9a-f]{32}", Path(filename).stem.casefold()))


def _archive_previous_versions(
    db: Session,
    doc: Doc,
    *,
    source: str | None = None,
    previous_hash: str | None = None,
) -> None:
    # Las versiones anteriores se conservan en la base, pero dejan de participar en las búsquedas.
    query = db.query(Doc).filter(Doc.id != doc.id, Doc.rag_status == "vectorizado")
    previous_versions = [Doc.file_name == doc.file_name]
    if source:
        previous_versions.append(Doc.storage_in == source)
    if previous_hash:
        previous_versions.append(Doc.doc_hashed == previous_hash)
    query = query.filter(or_(*previous_versions))
    for old_doc in query.all():
        old_doc.rag_status = "reemplazado"


def sha256_file(file_path: str | Path) -> str:
    # Calcula una huella del archivo para detectar contenido idéntico con nombres distintos.
    digest = hashlib.sha256()
    with open(file_path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _groq_client() -> Groq:
    # La clave solo es necesaria para OCR de imágenes o páginas que requieran lectura visual.
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta GROQ_API_KEY. Configúrala en .env para procesar imágenes o PDFs escaneados."
        )
    return Groq(api_key=api_key)


def _image_as_data_url(image: Image.Image) -> str:
    # Reduce el tamaño y codifica la imagen para enviarla en la solicitud de visión.
    image = image.convert("RGB")
    image.thumbnail((2200, 2200))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=85, optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return f"data:image/jpeg;base64,{encoded}"


def extract_text_from_image(image: Image.Image) -> str:
    configured_limit = int(os.getenv("VISION_MAX_TOKENS", "850"))
    max_tokens = max(256, min(configured_limit, 900))
    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "Transcribe todo el texto visible que aporte información, en orden de lectura. "
                        "Incluye pasos e instrucciones, notas, nombres, fechas, horarios, correos, "
                        "teléfonos, enlaces, etiquetas de campos, opciones de menú y texto de botones. "
                        "Conserva el orden de los pasos y las relaciones señaladas por flechas. "
                        "Mantén tablas en filas y organigramas como relaciones 'padre > hijo'. "
                        "No infieras contenido fuera de la imagen ni inventes texto: marca como "
                        "[ilegible] lo que no puedas leer. Devuelve solo la transcripción estructurada."
                    ),
                },
                {"type": "image_url", "image_url": {"url": _image_as_data_url(image)}},
            ],
        }
    ]
    try:
        response = _groq_client().chat.completions.create(
            model=os.getenv("VISION_MODEL", "qwen/qwen3.8-27b"),
            messages=messages,
            temperature=0,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        detail = str(exc)
        if "expected output tokens exceed" in detail.casefold() and max_tokens > 700:
            try:
                response = _groq_client().chat.completions.create(
                    model=os.getenv("VISION_MODEL", "qwen/qwen3.8-27b"),
                    messages=messages,
                    temperature=0,
                    max_tokens=700,
                )
            except Exception as retry_exc:
                raise RuntimeError(
                    "Groq rechazó el OCR por el límite de tokens. Reduce VISION_MAX_TOKENS "
                    "o vuelve a intentarlo cuando se restablezca la cuota."
                ) from retry_exc
        else:
            raise
    choice = response.choices[0]
    if getattr(choice, "finish_reason", None) == "length":
        raise RuntimeError(
            "Groq paró la lectura visual por el límite de tokens. Aumenta VISION_MAX_TOKENS "
            "hasta 900 o divide la página en recortes antes de indexarla."
        )
    return (choice.message.content or "").strip()


def _page_has_substantial_embedded_image(page) -> bool:
    """Detecta páginas PDF con muchas capturas aunque también contengan texto seleccionable."""
    try:
        for embedded in page.images:
            try:
                width, height = embedded.image.size
            except Exception:
                continue
            if width * height >= PDF_OCR_MIN_IMAGE_PIXELS:
                return True
    except Exception:
        return False
    return False


def _xml_text(element) -> str:
    """Combina el texto visible contenido en un elemento XML de Word."""
    return "".join(
        node.text or ""
        for node in element.iter()
        if node.tag.rsplit("}", 1)[-1] == "t"
    ).strip()


def _docx_additional_blocks(data: bytes, existing_blocks: list[dict]) -> list[dict]:
    """Extrae texto de partes DOCX que no aparecen en los párrafos y tablas principales."""
    # Word repite contenido entre partes; normalizarlo evita indexar el mismo texto dos veces.
    known_text = {
        " ".join(str(block.get("text", "")).split()).casefold()
        for block in existing_blocks
    }
    extra_blocks = []

    def add_text(text: str, label: str, element_type: str) -> None:
        text = " ".join(text.split())
        key = text.casefold()
        if len(text) < 2 or key in known_text:
            return
        known_text.add(key)
        extra_blocks.append({
            "text": f"{label}: {text}" if label else text,
            "heading_path": [],
            "element_type": element_type,
        })

    def add_element(element, label: str, element_type: str) -> None:
        # Mantener separados los párrafos ayuda a conservar los límites del contenido original.
        paragraphs = [
            child for child in element.iter()
            if child.tag.rsplit("}", 1)[-1] == "p"
        ]
        if paragraphs:
            for paragraph in paragraphs:
                add_text(_xml_text(paragraph), label, element_type)
        else:
            add_text(_xml_text(element), label, element_type)

    # DOCX es un ZIP; se leen las partes que pueden contener texto adicional al cuerpo principal.
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        names = set(package.namelist())
        story_prefixes = (
            "word/header", "word/footer", "word/footnotes.xml", "word/endnotes.xml",
            "word/comments", "word/charts/", "word/diagrams/", "word/glossary/",
        )
        xml_parts = sorted(
            name for name in names
            if name.startswith("word/") and name.endswith(".xml")
            and (name == "word/document.xml" or name.startswith(story_prefixes))
        )

        for part_name in xml_parts:
            try:
                root = ET.fromstring(package.read(part_name))
            except ET.ParseError:
                # Un componente mal formado no debe impedir extraer el resto del documento.
                continue

            # Las relaciones contienen destinos de enlaces que no siempre aparecen como texto.
            part_directory, part_filename = part_name.rsplit("/", 1)
            rels_name = f"{part_directory}/_rels/{part_filename}.rels"
            relationships = {}
            if rels_name in names:
                try:
                    rels_root = ET.fromstring(package.read(rels_name))
                    relationships = {
                        rel.attrib.get("Id"): rel.attrib.get("Target")
                        for rel in rels_root.iter()
                        if rel.attrib.get("TargetMode") == "External"
                    }
                except ET.ParseError:
                    pass
            for link in root.iter():
                if link.tag.rsplit("}", 1)[-1] != "hyperlink":
                    continue
                label = _xml_text(link)
                relation_id = next(
                    (value for key, value in link.attrib.items() if key.endswith("}id")),
                    None,
                )
                target = relationships.get(relation_id)
                if label or target:
                    add_text(
                        f"{label} ({target})" if target else label,
                        "Hipervínculo",
                        "hyperlink",
                    )

            if part_name == "word/document.xml":
                # El cuerpo normal ya se leyó con python-docx; aquí se rescatan elementos especiales.
                special_elements = []
                special_elements.extend(
                    (element, "Cuadro de texto", "textbox")
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "txbxContent"
                )
                special_elements.extend(
                    (element, "Texto insertado", "tracked_text")
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "ins"
                )
                special_elements.extend(
                    (element, "Control de contenido", "content_control")
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "sdt"
                )
                for element, label, element_type in special_elements:
                    add_element(element, label, element_type)

                for element in root.iter():
                    if element.tag.rsplit("}", 1)[-1] in {"docPr", "cNvPr"}:
                        description = element.attrib.get("descr") or element.attrib.get("title")
                        if description:
                            add_text(description, "Descripción de imagen u objeto", "object_description")

                continue

            part_lower = part_name.casefold()
            if "/header" in part_lower:
                label, element_type = "Encabezado", "header"
            elif "/footer" in part_lower:
                label, element_type = "Pie de página", "footer"
            elif "footnotes" in part_lower:
                label, element_type = "Nota al pie", "footnote"
            elif "endnotes" in part_lower:
                label, element_type = "Nota final", "endnote"
            elif "comments" in part_lower:
                label, element_type = "Comentario", "comment"
            elif "/charts/" in part_lower:
                label, element_type = "Gráfico", "chart"
            elif "/diagrams/" in part_lower:
                label, element_type = "Diagrama", "diagram"
            else:
                label, element_type = "Contenido adicional", "supplemental"

            paragraphs = [
                _xml_text(element)
                for element in root.iter()
                if element.tag.rsplit("}", 1)[-1] in {"p", "si"}
            ]
            if "/charts/" in part_lower:
                # Algunos gráficos guardan etiquetas y categorías como valores en caché.
                paragraphs.extend(
                    element.text or ""
                    for element in root.iter()
                    if element.tag.rsplit("}", 1)[-1] == "v" and element.text
                )
            if not any(text.strip() for text in paragraphs):
                paragraphs = [_xml_text(root)]
            for paragraph in paragraphs:
                add_text(paragraph, label, element_type)

    return extra_blocks


def _extract_docx_images(data: bytes) -> list[dict]:
    """Lee con OCR las imágenes rasterizadas incluidas en el paquete DOCX."""
    image_blocks = []
    seen_hashes = set()
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        for name in sorted(package.namelist()):
            if not name.startswith("word/media/") or name.endswith("/"):
                continue
            image_data = package.read(name)
            image_hash = hashlib.sha256(image_data).hexdigest()
            # Word puede guardar varias copias idénticas de una imagen dentro del paquete.
            if image_hash in seen_hashes:
                continue
            seen_hashes.add(image_hash)
            try:
                with Image.open(io.BytesIO(image_data)) as image:
                    extracted = extract_text_from_image(image)
            except Exception as exc:
                if name.casefold().endswith(".svg"):
                    try:
                        # Los SVG suelen incluir texto como elementos XML y no requieren OCR visual.
                        svg_root = ET.fromstring(image_data)
                        extracted = " ".join(
                            node.text.strip()
                            for node in svg_root.iter()
                            if node.tag.rsplit("}", 1)[-1] in {"text", "tspan", "title", "desc"}
                            and node.text and node.text.strip()
                        )
                    except ET.ParseError:
                        continue
                else:
                    raise RuntimeError(
                        f"No se pudo leer la imagen incrustada {Path(name).name}: {exc}"
                    ) from exc
            if extracted and extracted.strip():
                image_blocks.append({
                    "text": f"Texto de imagen incrustada ({Path(name).name}):\n{extracted.strip()}",
                    "heading_path": [],
                    "element_type": "embedded_image",
                })
    return image_blocks


def extract_text_from_bytes(data: bytes, filename: str) -> list[dict]:
    """Extrae texto de un documento compatible sin necesitar una ruta local."""
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Formato no soportado: {extension or '(sin extensión)'}")

    if extension in IMAGE_EXTENSIONS:
        # Las imágenes no tienen texto seleccionable, así que se leen mediante visión.
        with Image.open(io.BytesIO(data)) as image:
            extracted = extract_text_from_image(image)
        if not extracted:
            raise ValueError("No se pudo extraer texto de la imagen.")
        return [{"page": 1, "text": extracted}]

    if extension == ".docx":
        try:
            from docx import Document

            document = Document(io.BytesIO(data))
            blocks = []
            heading_stack: list[tuple[int, str]] = []
            # Conserva la jerarquía de encabezados para asociar cada párrafo con su sección.
            for element in document.iter_inner_content():
                if hasattr(element, "style") and hasattr(element, "text"):
                    text = " ".join(element.text.split())
                    if not text:
                        continue
                    style_name = getattr(element.style, "name", "") or ""
                    if style_name.casefold().startswith("heading"):
                        match = re.search(r"(\d+)$", style_name)
                        level = int(match.group(1)) if match else 1
                        heading_stack = [item for item in heading_stack if item[0] < level]
                        heading_stack.append((level, text))
                        element_type = "heading"
                    else:
                        element_type = "paragraph"
                    blocks.append({
                        "text": text,
                        "heading_path": [heading for _, heading in heading_stack],
                        "element_type": element_type,
                    })
                else:
                    rows = [
                        [" ".join(cell.text.split()) for cell in row.cells]
                        for row in element.rows
                    ]
                    if not rows:
                        continue
                    headers = rows[0]
                    for row in rows[1:] if len(rows) > 1 else rows:
                        cells = [
                            f"{headers[index] or f'Columna {index + 1}'}: {value}"
                            for index, value in enumerate(row)
                            if value
                        ]
                        if cells:
                            blocks.append({
                                "text": " | ".join(cells),
                                "heading_path": [heading for _, heading in heading_stack],
                                "element_type": "table_row",
                            })
            blocks.extend(_docx_additional_blocks(data, blocks))
            blocks.extend(_extract_docx_images(data))
            text = "\n".join(block["text"] for block in blocks)
            if not text.strip():
                raise ValueError("El DOCX no contiene suficiente texto indexable.")
            return [{"page": None, "text": text, "blocks": blocks}]
        except Exception as exc:
            raise ValueError(f"No se pudo extraer el texto del DOCX: {exc}") from exc

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        pages = []
        ocr_page_numbers = []
        native_text = {}
        force_visual_read = any(
            marker in Path(filename).stem.casefold()
            for marker in ("organigrama", "mapa", "map-")
        )
        # Extrae texto normal primero y reserva el OCR para páginas escaneadas o visuales.
        for number, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                native_text[number] = text
            has_substantial_image = _page_has_substantial_embedded_image(page)
            needs_visual_read = force_visual_read or has_substantial_image
            if len(text) >= MIN_NATIVE_PDF_TEXT_CHARS and not needs_visual_read:
                pages.append({"page": number, "text": text})
            else:
                ocr_page_numbers.append(number)
    except Exception as exc:
        raise ValueError(f"No se pudo leer el PDF: {exc}") from exc

    # Aplica OCR a páginas con poco texto original, capturas grandes incrustadas
    # o fuentes principalmente visuales, como mapas. Combina el OCR con el texto
    # seleccionable para que se puedan buscar tanto las explicaciones como los pasos visuales.
    if ocr_page_numbers:
        pdf_document = None
        try:
            # PDFium se instala como paquete de Python junto con las dependencias,
            # por lo que no hace falta instalar Poppler ni configurar PATH.
            pdf_document = pdfium.PdfDocument(data)
            for page_number in ocr_page_numbers:
                pdf_page = pdf_document[page_number - 1]
                bitmap = None
                image = None
                try:
                    bitmap = pdf_page.render(scale=240 / 72)
                    # Copia los píxeles del búfer de PDFium antes de liberarlo.
                    image = bitmap.to_pil().copy()
                    extracted = extract_text_from_image(image)
                finally:
                    if image is not None:
                        image.close()
                    if bitmap is not None:
                        bitmap.close()
                    pdf_page.close()

                if extracted:
                    native = native_text.get(page_number, "")
                    combined = (
                        f"Texto extraído del PDF:\n{native}\n\n"
                        f"Lectura visual y jerarquía:\n{extracted}"
                        if native
                        else extracted
                    )
                    pages.append({"page": page_number, "text": combined})
                elif page_number not in [p["page"] for p in pages]:
                    raise RuntimeError(f"OCR sin resultado en página {page_number}.")
        except Exception as exc:
            raise RuntimeError(
                "No se pudo extraer el texto de todas las páginas del PDF. "
                "Verifica la dependencia pypdfium2 y GROQ_API_KEY para OCR, "
                "o usa un PDF con texto seleccionable. "
                f"Detalle: {exc}"
            ) from exc
        finally:
            if pdf_document is not None:
                pdf_document.close()

    pages.sort(key=lambda page: page["page"])
    if not pages:
        raise ValueError("El PDF no contiene texto extraíble.")
    return pages


def extract_text_from_file(file_path: str | Path) -> list[dict]:
    path = Path(file_path)
    return extract_text_from_bytes(path.read_bytes(), path.name)


def chunk_text(
    pages_text: list[dict],
    chunk_size: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_WORDS,
) -> list[dict]:
    """Divide el texto de las páginas en fragmentos para indexarlos y buscarlos."""
    # El tamaño debe ser positivo y el solapamiento menor que el fragmento para avanzar.
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size debe ser positivo y overlap debe ser menor que chunk_size.")

    chunks = []
    # El solapamiento conserva contexto cuando una respuesta queda partida entre fragmentos.
    step = chunk_size - overlap
    for page_info in pages_text:
        blocks = page_info.get("blocks") or [
            {"text": part, "heading_path": [], "element_type": "paragraph"}
            for part in page_info["text"].splitlines()
            if part.strip()
        ]
        current: list[str] = []
        current_words = 0
        current_heading: list[str] = []
        element_types: set[str] = set()

        def flush_group() -> None:
            nonlocal current, current_words, element_types
            if current:
                chunks.append({
                    "page": page_info.get("page"),
                    "content": "\n".join(current),
                    "metadata": {
                        **page_info.get("metadata", {}),
                        "heading_path": current_heading,
                        "element_types": sorted(element_types),
                    },
                })
                current = []
                current_words = 0
                element_types = set()

        for block in blocks:
            paragraph = " ".join(str(block.get("text", "")).split())
            if not paragraph:
                continue
            heading_path = list(block.get("heading_path", []))
            if heading_path and current and heading_path != current_heading:
                # No mezcla fragmentos que pertenecen a encabezados distintos.
                flush_group()
            if heading_path:
                current_heading = heading_path

            words = paragraph.split()
            if len(words) > chunk_size:
                flush_group()
                # Los bloques largos se dividen en ventanas con solapamiento.
                for start in range(0, len(words), step):
                    content = " ".join(words[start : start + chunk_size]).strip()
                    if content:
                        chunks.append({
                            "page": page_info.get("page"),
                            "content": content,
                            "metadata": {
                                **page_info.get("metadata", {}),
                                "heading_path": current_heading,
                                "element_types": [block.get("element_type", "paragraph")],
                            },
                        })
                continue
            if current and current_words + len(words) > chunk_size:
                flush_group()
            current.append(paragraph)
            current_words += len(words)
            element_types.add(block.get("element_type", "paragraph"))
        flush_group()
    return chunks


def process_and_store_pages(
    *,
    pages: list[dict],
    title: str,
    source: str,
    source_name: str,
    source_size: int,
    doc_hash: str,
    db: Session,
    category: str = "web_scraping",
    subsection_id: str | None = None,
    uploaded_by: str | None = None,
    chunk_metadata: dict | None = None,
) -> Doc:
    """Guarda las páginas extraídas de una URL u otra fuente no local."""
    previous_hash = doc_hash
    doc_hash = _versioned_hash(previous_hash)
    # El hash hace idempotente la ingesta: el mismo contenido no genera otra copia.
    existing = db.query(Doc).filter(Doc.doc_hashed == doc_hash).first()
    if existing and existing.rag_status in {"vectorizado", "reemplazado"}:
        # Si este contenido ya estaba registrado como reemplazado, lo reactiva sin volver a vectorizarlo.
        existing.rag_status = "vectorizado"
        _archive_previous_versions(
            db, existing, source=source, previous_hash=previous_hash
        )
        db.commit()
        return existing
    if existing:
        db.delete(existing)
        db.flush()

    chunks = chunk_text(
        pages,
        chunk_size=int(os.getenv("CHUNK_SIZE_WORDS", str(DEFAULT_CHUNK_WORDS))),
        overlap=int(os.getenv("CHUNK_OVERLAP_WORDS", str(DEFAULT_CHUNK_OVERLAP_WORDS))),
    )
    if not chunks:
        raise ValueError("La fuente no produjo texto indexable.")

    all_text = "\n".join(page.get("text", "") for page in pages)
    derived_metadata = derive_source_metadata(title, source, all_text)
    page_metadata = {
        key: value
        for page in pages
        for key, value in (page.get("metadata") or {}).items()
        if key in {"publication_date", "updated_date", "effective_date"} and value
    }
    for key, value in page_metadata.items():
        parsed = _parse_date_value(str(value))
        if parsed:
            derived_metadata[key] = parsed
    # Incluye las fechas de metadatos de página y periodos académicos al comparar actualidad.
    declared_dates = [
        derived_metadata[key]
        for key in (
            "updated_date",
            "publication_date",
            "effective_date",
            "content_period_date",
        )
        if derived_metadata.get(key)
    ]
    if declared_dates:
        derived_metadata["recency_date"] = max(declared_dates)

    doc = Doc(
        id=str(uuid.uuid4()),
        title=title[:200],
        subsections_id=subsection_id,
        uploaded_by=uploaded_by,
        file_name=source_name[:200],
        storage_in=source[:500],
        file_size=source_size,
        doc_hashed=doc_hash,
        rag_status="procesando",
    )
    db.add(doc)
    db.flush()
    _persist_chunks(
        db=db,
        doc=doc,
        chunks=chunks,
        category=category,
        subsection_id=subsection_id,
        source_metadata={
            **derived_metadata,
            "source_title": title,
            "source_url": source if source.startswith(("http://", "https://")) else None,
            "source_type": (chunk_metadata or {}).get("source_type", category),
            **(chunk_metadata or {}),
        },
    )
    # Solo se marca como vectorizado después de guardar sus fragmentos y vectores.
    doc.rag_status = "vectorizado"
    _archive_previous_versions(db, doc, source=source, previous_hash=previous_hash)
    db.commit()
    db.refresh(doc)
    return doc


def _persist_chunks(
    *,
    db: Session,
    doc: Doc,
    chunks: list[dict],
    category: str,
    subsection_id: str | None,
    source_metadata: dict | None = None,
) -> None:
    # Calcula los vectores en lote para reducir el costo de procesar cada fragmento por separado.
    vectors = embed_documents([chunk["content"] for chunk in chunks])
    for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True)):
        db.add(
            DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=doc.id,
                subsection_id=subsection_id,
                content=chunk["content"],
                metadata_json=json.dumps(
                    {
                        **(source_metadata or {}),
                        **chunk.get("metadata", {}),
                        "page_number": chunk.get("page"),
                        "chunk_index": index,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                category=category,
                chunk_index=index,
                page_number=chunk.get("page"),
                embedding_json=json.dumps(vector, separators=(",", ":")),
            )
        )


def process_and_store_document(
    *,
    file_path: str | Path,
    title: str,
    db: Session,
    category: str = "reglamento",
    subsection_id: str | None = None,
    original_filename: str | None = None,
    uploaded_by: str | None = None,
) -> Doc:
    path = Path(file_path)
    previous_hash = sha256_file(path)
    digest = _versioned_hash(previous_hash)
    # Comprueba duplicados antes de extraer texto y calcular vectores, que son pasos costosos.
    existing = db.query(Doc).filter(Doc.doc_hashed == digest).first()
    if existing and existing.rag_status in {"vectorizado", "reemplazado"}:
        existing.rag_status = "vectorizado"
        _archive_previous_versions(db, existing, previous_hash=previous_hash)
        incoming_name = original_filename or path.name
        if (
            existing.rag_status == "vectorizado"
            and _is_generated_filename(existing.file_name)
            and not _is_generated_filename(incoming_name)
        ):
            existing.title = title[:200]
            existing.file_name = incoming_name[:200]
            existing.storage_in = str(path.resolve())
            existing.file_size = path.stat().st_size
        db.commit()
        return existing
    if existing:
        db.delete(existing)
        db.flush()

    pages = extract_text_from_file(path)
    chunks = chunk_text(
        pages,
        chunk_size=int(os.getenv("CHUNK_SIZE_WORDS", str(DEFAULT_CHUNK_WORDS))),
        overlap=int(os.getenv("CHUNK_OVERLAP_WORDS", str(DEFAULT_CHUNK_OVERLAP_WORDS))),
    )
    if not chunks:
        raise ValueError("El documento no produjo fragmentos indexables.")

    extension = path.suffix.lower()
    doc = Doc(
        id=str(uuid.uuid4()),
        title=title[:200],
        subsections_id=subsection_id,
        uploaded_by=uploaded_by,
        file_name=(original_filename or path.name)[:200],
        storage_in=str(path.resolve()),
        file_size=path.stat().st_size,
        doc_hashed=digest,
        rag_status="procesando",
    )
    db.add(doc)
    db.flush()

    # Marca las fuentes visuales para poder distinguirlas de PDF y documentos de texto.
    if extension in IMAGE_EXTENSIONS:
        category = "vision"
    _persist_chunks(
        db=db,
        doc=doc,
        chunks=chunks,
        category=category,
        subsection_id=subsection_id,
        source_metadata={
            "source_title": title,
            "source_name": original_filename or path.name,
            "source_type": "local_file",
            "file_extension": extension,
        },
    )
    doc.rag_status = "vectorizado"
    _archive_previous_versions(db, doc, previous_hash=previous_hash)
    db.commit()
    db.refresh(doc)
    return doc


def process_and_store_text(
    *,
    text: str,
    title: str,
    source: str,
    doc_hash: str,
    db: Session,
    category: str = "web_scraping",
    subsection_id: str | None = None,
    uploaded_by: str | None = None,
) -> Doc:
    """Guarda el texto web extraído mediante el mismo flujo de división y vectorización."""
    return process_and_store_pages(
        pages=[{"page": 1, "text": text}],
        title=title,
        source=source,
        source_name=source,
        source_size=len(text.encode("utf-8")),
        doc_hash=doc_hash,
        db=db,
        category=category,
        subsection_id=subsection_id,
        uploaded_by=uploaded_by,
    )
