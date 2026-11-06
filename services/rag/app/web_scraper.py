"""Procesa páginas HTML públicas y documentos enlazados por URL, como PDF e imágenes."""

import hashlib
import io
import json
import os
import re
import threading
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import parse_qs, unquote, urljoin, urlparse, urlunparse
from zipfile import BadZipFile, ZipFile

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.ingestion import (
    IMAGE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    extract_text_from_bytes,
    process_and_store_pages,
)
from app.models import Doc, DocumentChunk

# Tamaño máximo predeterminado para una descarga web si no se configura otra cifra.
DEFAULT_MAX_SOURCE_MB = 50
# Tipos de página que se pueden interpretar como HTML.
HTML_TYPES = {"text/html", "application/xhtml+xml"}

# Estado en memoria para que Swagger y el frontend puedan mostrar el rastreo actual.
_CRAWL_STATUS_LOCK = threading.Lock()
_CRAWL_HISTORY = []
_CRAWL_STATUS = {
    "run_id": None,
    "state": "idle",
    "crawl_type": None,
    "root_url": None,
    "started_at": None,
    "updated_at": None,
    "finished_at": None,
    "current_program": None,
    "programs_found": 0,
    "programs_processed": 0,
    "programs": [],
    "current_url": None,
    "pages_visited": 0,
    "pages_indexed": 0,
    "pages_failed": 0,
    "indexed_pages": [],
    "pending_pages": 0,
    "limit_reached": False,
    "max_depth_allowed": None,
    "program_path_prefix": None,
    "failures": [],
    "summary": None,
    "scope_note": (
        "El rastreador ve enlaces HTML estáticos del mismo dominio dentro de las rutas y límites "
        "configurados; no ejecuta JavaScript ni puede confirmar enlaces ocultos o restringidos."
    ),
}


def get_crawl_status() -> dict:
    """Devuelve una copia segura del avance del rastreo más reciente."""
    with _CRAWL_STATUS_LOCK:
        snapshot = deepcopy(_CRAWL_STATUS)
        snapshot["recent_runs"] = deepcopy(_CRAWL_HISTORY)
        return snapshot


def _start_crawl(crawl_type: str, root_url: str) -> str:
    """Inicia el registro del rastreo para consultarlo mientras la API trabaja."""
    now = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    with _CRAWL_STATUS_LOCK:
        _CRAWL_STATUS.update({
            "run_id": run_id,
            "state": "running",
            "crawl_type": crawl_type,
            "root_url": root_url,
            "started_at": now,
            "updated_at": now,
            "finished_at": None,
            "current_program": None,
            "programs_found": 0,
            "programs_processed": 0,
            "programs": [],
            "current_url": None,
            "pages_visited": 0,
            "pages_indexed": 0,
            "pages_failed": 0,
            "indexed_pages": [],
            "pending_pages": 0,
            "limit_reached": False,
            "max_depth_allowed": None,
            "program_path_prefix": None,
            "failures": [],
            "summary": None,
        })
    return run_id


def _update_crawl(run_id: str, **values) -> None:
    """Actualiza el avance solo si corresponde al rastreo que sigue activo."""
    with _CRAWL_STATUS_LOCK:
        if _CRAWL_STATUS.get("run_id") != run_id or _CRAWL_STATUS.get("state") != "running":
            return
        _CRAWL_STATUS.update(values)
        _CRAWL_STATUS["updated_at"] = datetime.now(timezone.utc).isoformat()


def _finish_crawl(run_id: str, state: str, summary: str, **values) -> None:
    """Registra el resultado final del rastreo consultable por API."""
    now = datetime.now(timezone.utc).isoformat()
    with _CRAWL_STATUS_LOCK:
        if _CRAWL_STATUS.get("run_id") != run_id:
            return
        _CRAWL_STATUS.update(values)
        _CRAWL_STATUS.update({
            "state": state,
            "summary": summary,
            "current_url": None,
            "current_program": None,
            "finished_at": now,
            "updated_at": now,
        })
        # Conserva los últimos rastreos para comparar por separado los tres catálogos académicos.
        history_entry = {
            key: deepcopy(_CRAWL_STATUS.get(key))
            for key in (
                "run_id", "state", "crawl_type", "root_url", "started_at", "finished_at",
                "programs_found", "programs_processed", "programs", "pages_visited",
                "pages_indexed", "pages_failed", "indexed_pages", "pending_pages",
                "limit_reached", "failures",
                "summary",
            )
        }
        _CRAWL_HISTORY.append(history_entry)
        del _CRAWL_HISTORY[:-10]


def _normalize_source_url(url: str) -> str:
    """Obtiene los archivos originales detrás de las vistas previas de Office y Google Drive."""
    # Algunas vistas previas ocultan la dirección del documento original en sus parámetros.
    parsed = urlparse(url)
    if parsed.netloc.casefold().endswith("officeapps.live.com"):
        # Extrae el archivo que Office Online está mostrando, en vez de descargar su visor.
        source = parse_qs(parsed.query).get("src", [None])[0]
        if source and urlparse(source).scheme in {"http", "https"}:
            return source
    if parsed.netloc.casefold() in {"drive.google.com", "www.drive.google.com"}:
        # Convierte el enlace de vista previa de Drive a su ruta de descarga pública.
        match = re.search(r"/file/d/([^/]+)", parsed.path)
        file_id = match.group(1) if match else parse_qs(parsed.query).get("id", [None])[0]
        if file_id:
            return f"https://drive.google.com/uc?export=download&id={file_id}"
    return url


def _download_source(url: str) -> tuple[bytes, str, str, str | None]:
    """Descarga una URL pública con redirecciones y un límite de tamaño."""
    url = _normalize_source_url(url)
    is_drive_source = "drive.google.com" in urlparse(url).netloc.casefold()
    parsed = urlparse(url)
    # Solo se descargan recursos web; otras formas de URL podrían apuntar a archivos locales.
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("La URL debe comenzar con http:// o https://")

    # Descarga por bloques para poder detener la respuesta si supera el máximo configurado.
    max_bytes = int(os.getenv("MAX_URL_DOWNLOAD_MB", str(DEFAULT_MAX_SOURCE_MB))) * 1024 * 1024
    headers = {"User-Agent": "SIAE-Document-Ingestion/1.0 (+public educational information)"}
    payload = bytearray()
    download_name = None
    try:
        # La respuesta se lee en streaming para aplicar el límite también a archivos grandes.
        with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0), headers=headers) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                final_url = str(response.url)
                disposition = response.headers.get("content-disposition", "")
                # El servidor puede sugerir un nombre distinto al que aparece en la URL.
                filename_match = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", disposition, re.IGNORECASE)
                if filename_match:
                    download_name = unquote(filename_match.group(1).strip().strip('"'))
                for part in response.iter_bytes():
                    payload.extend(part)
                    if len(payload) > max_bytes:
                        raise ValueError(
                            f"La fuente supera el límite MAX_URL_DOWNLOAD_MB ({max_bytes // (1024 * 1024)} MB)."
                        )
    except httpx.HTTPError as exc:
        # Convierte los errores de red a ValueError para que la API los devuelva como error de ingesta.
        raise ValueError(f"No se pudo descargar la fuente: {exc}") from exc

    if not payload:
        raise ValueError("La URL devolvió un archivo vacío.")
    data = bytes(payload)
    # Google Drive puede devolver una página HTML de confirmación para archivos públicos grandes.
    # Sigue una vez el formulario de descarga y conserva el límite de tamaño.
    if is_drive_source and content_type in HTML_TYPES:
        page = BeautifulSoup(data, "html.parser")
        form = page.find("form", action=re.compile(r"/download"))
        if form:
            action = urljoin(final_url, form.get("action", ""))
            fields = {item.get("name"): item.get("value", "") for item in form.select("input[name]")}
            with httpx.Client(follow_redirects=True, timeout=httpx.Timeout(60.0, connect=15.0), headers=headers) as client:
                with client.stream("GET", action, params=fields) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    final_url = str(response.url)
                    payload = bytearray()
                    for part in response.iter_bytes():
                        payload.extend(part)
                        if len(payload) > max_bytes:
                            raise ValueError(f"La fuente supera el límite MAX_URL_DOWNLOAD_MB ({max_bytes // (1024 * 1024)} MB).")
            data = bytes(payload)
    if is_drive_source and content_type in HTML_TYPES:
        raise ValueError("Google Drive devolvió una página de vista previa. Confirma que el archivo tenga acceso 'Cualquier persona con el enlace' o descarga y carga el archivo directamente.")
    return data, content_type, final_url, download_name


def _source_extension(
    url: str,
    content_type: str,
    data: bytes,
    download_name: str | None = None,
) -> str | None:
    # Determina el formato con cabeceras, extensión y firma del contenido descargado.
    path_extension = Path(unquote(urlparse(url).path)).suffix.lower()
    if download_name:
        path_extension = Path(unquote(download_name)).suffix.lower() or path_extension
    # La firma del contenido ayuda cuando el servidor o la URL informan una extensión incorrecta.
    if data.startswith(b"%PDF-") or content_type == "application/pdf" or path_extension == ".pdf":
        return ".pdf"
    if path_extension == ".docx" or content_type in {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-word.document.macroEnabled.12",
    }:
        return ".docx"
    # DOCX también es un ZIP; comprueba que contenga la parte XML propia de Word.
    if data.startswith(b"PK"):
        try:
            with ZipFile(io.BytesIO(data)) as archive:
                if "word/document.xml" in archive.namelist():
                    return ".docx"
        except (BadZipFile, OSError):
            pass
    if content_type.startswith("image/") or path_extension in IMAGE_EXTENSIONS:
        try:
            from PIL import Image

            # Pillow verifica el formato real de la imagen antes de elegir su extensión interna.
            with Image.open(io.BytesIO(data)) as image:
                return {
                    "JPEG": ".jpg",
                    "PNG": ".png",
                    "WEBP": ".webp",
                    "BMP": ".bmp",
                    "GIF": ".gif",
                    "TIFF": ".tiff",
                }.get(image.format or "")
        except Exception:
            return None
    return None


def _html_content(data: bytes, url: str, content_type: str, *, allow_short: bool = False) -> dict:
    """Extrae título, texto organizado, enlaces y fechas de una página HTML pública."""
    # Rechaza otros formatos antes de intentar interpretarlos como una página web.
    if content_type not in HTML_TYPES and not data.lstrip().startswith((b"<!doctype html", b"<html", b"<?xml")):
        raise ValueError(
            f"Tipo de fuente no compatible ({content_type or 'desconocido'}). "
            "Se aceptan páginas HTML públicas, PDF e imágenes PNG/JPG/WEBP."
        )
    soup = BeautifulSoup(data, "html.parser")
    title_tag = soup.find("title") or soup.find("h1")
    title = title_tag.get_text(" ", strip=True) if title_tag else url
    # Conserva fechas publicadas por el sitio para que puedan usarse como metadatos de la fuente.
    dates = {}
    for meta in soup.find_all("meta"):
        key = (meta.get("property") or meta.get("name") or meta.get("itemprop") or "").casefold()
        value = (meta.get("content") or "").strip()
        if not value:
            continue
        if key in {"article:published_time", "datepublished", "dcterms.created", "date"}:
            dates.setdefault("publication_date", value[:40])
        elif key in {"article:modified_time", "datemodified", "dcterms.modified", "last-modified"}:
            dates.setdefault("updated_date", value[:40])

    # Guarda los enlaces antes de limpiar la navegación: en páginas de carreras, los menús
    # desplegables contienen subsecciones y accesos con imágenes que el usuario también necesita.
    link_candidates = []
    for element in soup.select(
        "a[href], button[data-href], button[data-url], button[formaction], "
        "[role='button'][data-href], [role='button'][data-url], img[onclick], [onclick]"
    ):
        destinations = (
            element.get("href"), element.get("data-href"), element.get("data-url"),
            element.get("formaction"),
        )
        destination = next((
            value for value in destinations
            if value and not value.strip().casefold().startswith(
                ("#", "javascript:", "mailto:", "tel:")
            )
        ), None)
        # Algunos botones asignan la URL desde JavaScript en vez de usar href/data-href.
        if not destination:
            onclick = element.get("onclick", "")
            match = re.search(
                r"(?:window\.open\s*\(|(?:window\.)?location(?:\.href)?\s*=?)\s*['\"]([^'\"]+)['\"]",
                onclick,
                re.IGNORECASE,
            )
            destination = match.group(1) if match else None
        if not destination or destination.strip().casefold().startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        label = " ".join(element.stripped_strings) or element.get("aria-label", "") or element.get("title", "")
        if not label:
            label = " ".join(
                (image.get("alt") or image.get("title") or "").strip()
                for image in element.find_all("img")
                if (image.get("alt") or image.get("title") or "").strip()
            )
        if not label and element.name == "img":
            label = (element.get("alt") or element.get("title") or "").strip()
        target = urljoin(url, destination)
        if urlparse(target).scheme in {"http", "https"}:
            link_candidates.append({"title": (label or "Enlace sin texto")[:200], "url": target})

    # Quita código y elementos repetitivos del contenido a indexar. Los enlaces del menú
    # ya quedaron guardados arriba, aunque se descarte su texto como contenido de la página.
    for element in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "iframe", "svg"]):
        element.decompose()
    for element in soup.select(
        ".breadcrumb, .breadcrumbs, .social-share, .share-links, .cookie-banner, "
        ".region-header, .region-footer"
    ):
        element.decompose()

    # Prefiere el contenedor principal para no indexar menús y pie de página como contenido.
    main = soup.find("main") or soup.find(attrs={"role": "main"})
    if main is None:
        main = soup.select_one("#content, #main-content, .region-content, article") or soup.body or soup

    # Conserva los límites entre bloques y encabezados relevantes para que la división posterior
    # mantenga juntos cada tema y sus datos de contacto, en vez de aplanar toda la página.
    blocks = []
    heading_path = []
    seen = set()
    # Etiquetas que suelen contener unidades de texto separables para la división en fragmentos.
    block_tags = [
        "h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "tr", "td", "th",
        "dt", "dd", "address", "div", "section", "article", "button",
        "details", "summary", "dialog", "label",
    ]
    block_tag_set = set(block_tags)
    for element in main.find_all(block_tags):
        # Selecciona los bloques finales para incluir tarjetas hechas con etiquetas div/span
        # genéricas, sin duplicar todo el texto de sus contenedores principales.
        if element.find(block_tag_set):
            continue
        value = " ".join(element.stripped_strings)
        value = re.sub(r"\s+", " ", value).strip()
        # Evita duplicar el texto cuando el mismo bloque aparece en contenedores anidados.
        if value and value not in seen:
            blocks.append(value)
            seen.add(value)
            if element.name in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                # Actualiza la ruta de encabezados para relacionar cada bloque con su sección.
                level = int(element.name[1])
                heading_path = heading_path[: level - 1]
                heading_path.append(value)
                blocks[-1] = {
                    "text": value,
                    "heading_path": list(heading_path),
                    "element_type": "heading",
                }
            else:
                blocks[-1] = {
                    "text": value,
                    "heading_path": list(heading_path),
                    "element_type": element.name,
                }
    structured_text = "\n".join(block["text"] for block in blocks)
    complete_text = "\n".join(
        re.sub(r"\s+", " ", line).strip()
        for line in main.get_text(separator="\n").splitlines()
        if line.strip()
    )
    # Algunos sitios incluyen todos los datos del artículo o contacto en etiquetas span
    # o componentes personalizados. Si faltó una parte importante, usa todo el texto visible.
    # Si la lectura por bloques perdió demasiado texto, usa el texto visible completo como respaldo.
    if len(structured_text) >= len(complete_text) * 0.85:
        text = structured_text
    else:
        text = complete_text
        blocks = [
            {"text": line, "heading_path": [], "element_type": "text"}
            for line in text.splitlines() if line.strip()
        ]
    # Quita duplicados por URL conservando la primera etiqueta disponible.
    unique_links = {}
    for item in link_candidates:
        unique_links.setdefault(item["url"], item)
    links = list(unique_links.values())
    if len(text) < 40 and not allow_short:
        raise ValueError(
            "La página devolvió muy poco texto. Puede depender de JavaScript, requerir inicio de sesión "
            "o bloquear la extracción automática. Descarga el contenido como PDF o imagen y súbelo."
        )
    return {"title": title[:200], "content": text, "blocks": blocks, "links": links, "dates": dates}


def extract_content_from_url(url: str, *, allow_short_html: bool = False) -> dict:
    """Descarga una URL pública y devuelve el tipo detectado junto con el texto extraído."""
    # Guarda la URL solicitada como origen, aunque después haya redirecciones.
    source_url = _normalize_source_url(url)
    data, content_type, final_url, download_name = _download_source(url)
    extension = _source_extension(final_url, content_type, data, download_name)
    # PDF, DOCX e imágenes se entregan al mismo extractor que usan las cargas locales.
    if extension:
        source_name = (
            Path(unquote(download_name)).name if download_name
            else Path(unquote(urlparse(final_url).path)).name
        ) or f"documento{extension}"
        pages = extract_text_from_bytes(data, source_name)
        return {
            "title": Path(unquote(download_name or urlparse(final_url).path)).stem or "Documento web",
            "content": "\n".join(page["text"] for page in pages),
            "pages": pages,
            "source_url": source_url,
            # Conserva tanto el origen solicitado como el nombre y tamaño del recurso descargado.
            "source_name": source_name,
            "source_size": len(data),
            "content_type": content_type,
            "source_type": extension.lstrip("."),
            "links": [],
        }
    # El texto plano no necesita análisis HTML; se conserva como una sola página.
    if content_type == "text/plain":
        text = data.decode("utf-8-sig", errors="replace").strip()
        if len(text) < 40:
            raise ValueError("La URL de texto no contiene suficiente contenido indexable.")
        title = Path(unquote(urlparse(final_url).path)).stem or "Publicación"
        return {
            "title": title[:200],
            "content": text,
            "pages": [{"page": 1, "text": text}],
            "source_url": source_url,
            "source_name": final_url[:200],
            "source_size": len(data),
            "content_type": content_type,
            "source_type": "text",
            "links": [],
        }
    # Si no es un archivo ni texto plano, se procesa como página web.
    # Usa la URL final para resolver enlaces relativos y registrar la ubicación real del HTML.
    page = _html_content(data, final_url, content_type, allow_short=allow_short_html)
    return {
        **page,
        "pages": [{
            "page": 1,
            "text": page["content"],
            "blocks": page["blocks"],
            "metadata": {"source_url": final_url, "source_type": "html", **page.get("dates", {})},
        }],
        "source_url": source_url,
        "source_name": final_url[:200],
        "source_size": len(data),
        "content_type": content_type,
        "source_type": "html",
        "links": page["links"],
    }


def process_url_ingestion(
    url: str,
    custom_title: Optional[str],
    subsection_id: Optional[str],
    uploaded_by: Optional[str],
    db: Session,
    replace_file_name: Optional[str] = None,
    chunk_metadata: dict | None = None,
    extracted_source: dict | None = None,
) -> Doc:
    # Permite reutilizar una extracción ya hecha por el rastreador y evita descargarla otra vez.
    source = extracted_source or extract_content_from_url(url)
    title = (custom_title or source["title"])[:200]
    # Combina URL y contenido para distinguir cambios en una página sin duplicar su misma versión.
    # El hash cambia si cambia el texto extraído, aunque la dirección de la página siga igual.
    digest = hashlib.sha256(
        f"{source['source_url']}\n".encode("utf-8") + source["content"].encode("utf-8")
    ).hexdigest()
    # Guarda páginas y metadatos con el mismo flujo de fragmentación y embeddings del resto del sistema.
    doc = process_and_store_pages(
        pages=source["pages"],
        title=title,
        source=source["source_url"],
        source_name=source["source_name"],
        source_size=source["source_size"],
        doc_hash=digest,
        db=db,
        category="web_scraping" if source["content_type"] in HTML_TYPES else "documento_web",
        subsection_id=subsection_id,
        uploaded_by=uploaded_by,
        chunk_metadata={
            "source_type": source["source_type"],
            "content_type": source["content_type"],
            **(chunk_metadata or {}),
        },
    )
    # Marca como reemplazado un documento local antiguo que fue sustituido por esta fuente web.
    if replace_file_name:
        old_docs = (
            db.query(Doc)
            .filter(
                Doc.file_name.ilike(Path(replace_file_name).name),
                Doc.id != doc.id,
                Doc.rag_status == "vectorizado",
            )
            .all()
        )
        for old_doc in old_docs:
            old_doc.rag_status = "reemplazado"
        if old_docs:
            db.commit()
    return doc


def _canonical_url(url: str) -> str:
    # Quita fragmentos, parámetros y barra final para que una página no se rastree varias veces.
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))


def _site_host(url: str) -> str:
    """Normaliza el alias www para tratarlo como el mismo sitio institucional."""
    host = (urlparse(url).hostname or "").casefold()
    return host[4:] if host.startswith("www.") else host


def _archive_removed_crawl_pages(
    db: Session,
    crawl_root_url: str,
    current_document_ids: set[str],
) -> None:
    """Desactiva las páginas que ya no aparecen en el mapa de enlaces de un rastreo completado."""
    # Busca los documentos que fueron indexados anteriormente bajo esta misma raíz.
    previous_document_ids = set()
    rows = (
        db.query(DocumentChunk.document_id, DocumentChunk.metadata_json)
        .join(Doc, Doc.id == DocumentChunk.document_id)
        .filter(Doc.rag_status == "vectorizado")
        .all()
    )
    for document_id, metadata_json in rows:
        try:
            metadata = json.loads(metadata_json or "{}")
        except (TypeError, ValueError):
            continue
        if metadata.get("crawl_root_url") == crawl_root_url:
            previous_document_ids.add(document_id)

    # Solo se retiran fuentes ausentes del rastreo actual, sin borrar sus registros históricos.
    removed_ids = previous_document_ids - current_document_ids
    if not removed_ids:
        return
    for old_doc in db.query(Doc).filter(
        Doc.id.in_(removed_ids), Doc.rag_status == "vectorizado"
    ).all():
        old_doc.rag_status = "reemplazado"
    db.commit()


def process_url_crawl(
    *,
    root_url: str,
    root_title: str | None,
    allowed_path_prefixes: list[str],
    max_pages: int,
    max_depth: int,
    subsection_id: str | None,
    uploaded_by: str | None,
    db: Session,
    _crawl_run_id: str | None = None,
) -> dict:
    """Indexa una página HTML y una cantidad limitada de páginas enlazadas de su contenido principal."""
    # Valida límites para evitar rastreos accidentales demasiado grandes o profundos.
    if not 1 <= max_pages <= 100:
        raise ValueError("max_pages debe estar entre 1 y 100.")
    if not 0 <= max_depth <= 2:
        raise ValueError("max_depth debe estar entre 0 y 2.")
    # Los prefijos deben ser rutas del sitio, no una forma de escapar a otra ubicación.
    prefixes = [prefix.strip() for prefix in allowed_path_prefixes if prefix.strip()]
    if any(not prefix.startswith("/") or ".." in prefix.split("/") for prefix in prefixes):
        raise ValueError("Los prefijos permitidos deben ser rutas absolutas del sitio.")

    # Normaliza la raíz y limita todos los enlaces al dominio desde el que inicia el rastreo.
    root_url = _canonical_url(_normalize_source_url(root_url))
    root_host = _site_host(root_url)
    run_id = _crawl_run_id or _start_crawl("url", root_url)
    _update_crawl(
        run_id,
        root_url=root_url,
        current_url=root_url,
        max_depth_allowed=max_depth,
    )
    # La cola por niveles limita el rastreo al sitio raíz y evita visitar una URL dos veces.
    queue = [(root_url, 0, root_title, None)]
    seen = set()
    visited_depths = []
    indexed = []
    failures = []

    # Procesa la cola en orden de profundidad hasta agotar enlaces o alcanzar max_pages.
    while queue and len(seen) < max_pages:
        current_url, depth, page_title, parent_url = queue.pop(0)
        canonical = _canonical_url(current_url)
        if canonical in seen:
            continue
        seen.add(canonical)
        visited_depths.append(depth)
        # Hace visible el avance; cada página puede tardar por descarga, extracción y embeddings.
        print(
            f"[rastreo] {len(seen)}/{max_pages} | nivel {depth} | {canonical}",
            flush=True,
        )
        page_status = "error"
        progress = {"current_url": canonical, "pending_pages": len(queue)}
        if _crawl_run_id is None:
            progress.update({
                "pages_visited": len(seen),
                "pages_indexed": len(indexed),
                "pages_failed": len(failures),
                "indexed_pages": [
                    {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                    for item in indexed
                ],
                "failures": failures[-100:],
            })
        _update_crawl(run_id, **progress)
        try:
            source = extract_content_from_url(canonical, allow_short_html=True)
            # Una página breve aún puede servir como índice para encontrar páginas secundarias.
            if len(source["content"].strip()) < 40:
                failures.append({
                    "url": canonical,
                    "error": "La página contiene muy poco texto para indexarse; se rastrearán sus enlaces.",
                })
            else:
                doc = process_url_ingestion(
                    url=canonical,
                    custom_title=page_title or source["title"],
                    subsection_id=subsection_id,
                    uploaded_by=uploaded_by,
                    db=db,
                    chunk_metadata={
                        "parent_url": parent_url,
                        "crawl_root_url": root_url,
                        "crawl_depth": depth,
                    },
                    extracted_source=source,
                )
                indexed.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "url": canonical,
                    "rag_status": doc.rag_status,
                    "depth": depth,
                })
                page_status = (
                    "vectorizado" if doc.rag_status == "vectorizado" else "error"
                )
            # Solo las páginas HTML pueden aportar enlaces; archivos PDF e imágenes son terminales.
            if depth < max_depth and source["source_type"] == "html":
                # Solo se agregan enlaces del mismo dominio que respetan los prefijos permitidos.
                # También se excluyen enlaces ya encolados para que dos páginas no programen la misma URL.
                queued = {item[0] for item in queue}
                for link in source.get("links", []):
                    link_url = _canonical_url(link["url"])
                    parsed = urlparse(link_url)
                    if _site_host(link_url) != root_host or link_url in seen or link_url in queued:
                        continue
                    if prefixes and not any(parsed.path.startswith(prefix) for prefix in prefixes):
                        continue
                    queue.append((link_url, depth + 1, link.get("title"), canonical))
        except Exception as exc:
            # Revierte cambios incompletos de esta página y continúa con las demás.
            db.rollback()
            failures.append({"url": canonical, "error": str(exc)[:500]})
        # Registra el cierre de esta página: hora local, profundidad y resultado final.
        finished_at = datetime.now().astimezone().strftime("%H:%M:%S")
        print(
            f"[rastreo] fin {len(seen)}/{max_pages} | nivel {depth} | "
            f"{finished_at} | {page_status} | {canonical}",
            flush=True,
        )
        progress = {"pending_pages": len(queue)}
        if _crawl_run_id is None:
            progress.update({
                "pages_visited": len(seen),
                "pages_indexed": len(indexed),
                "pages_failed": len(failures),
                "indexed_pages": [
                    {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                    for item in indexed
                ],
                "failures": failures[-100:],
            })
        _update_crawl(run_id, **progress)

    root_was_indexed = any(item["url"] == root_url for item in indexed)
    pending_urls = sorted({
        _canonical_url(item[0]) for item in queue
        if _canonical_url(item[0]) not in seen
    })
    limit_reached = bool(pending_urls) and len(seen) >= max_pages
    # Conserva disponibles las páginas anteriores si falla alguna solicitud. Solo un rastreo
    # completo y sin límites alcanzados permite concluir que una página enlazada fue retirada.
    if root_was_indexed and not failures and not limit_reached:
        # Solo un rastreo completo permite considerar retiradas las páginas que ya no están enlazadas.
        _archive_removed_crawl_pages(
            db,
            root_url,
            {item["document_id"] for item in indexed},
        )

    result = {
        "root_url": root_url,
        "indexed": indexed,
        "failures": failures,
        "pages_indexed": len(indexed),
        "pages_visited": len(seen),
        "pages_failed": len(failures),
        "limit_reached": limit_reached,
        "pending_pages": len(pending_urls),
        "max_depth_reached": max(visited_depths, default=0),
        "max_depth_allowed": max_depth,
        "queue_exhausted": not pending_urls,
        "coverage_note": (
            "Confirma el recorrido de los enlaces estáticos detectados dentro del mismo dominio, "
            "las rutas permitidas y los límites indicados; no incluye enlaces generados por JavaScript."
        ),
    }
    state = "limit_reached" if limit_reached else (
        "completed_with_errors" if failures else "completed"
    )
    if _crawl_run_id is None:
        _finish_crawl(
            run_id,
            state,
            f"{len(indexed)} páginas indexadas; {len(failures)} fallidas; "
            f"{len(pending_urls)} pendientes dentro de la cola descubierta.",
            pages_visited=len(seen),
            pages_indexed=len(indexed),
            pages_failed=len(failures),
            indexed_pages=[
                {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                for item in indexed
            ],
            pending_pages=len(pending_urls),
            limit_reached=limit_reached,
            failures=failures[-100:],
        )
    return result


def process_academic_catalog_crawl(
    *,
    catalog_url: str,
    catalog_title: str | None,
    program_path_prefix: str,
    max_pages_per_program: int,
    max_depth: int,
    subsection_id: str | None,
    uploaded_by: str | None,
    db: Session,
    _crawl_run_id: str | None = None,
) -> dict:
    """Indexa un catálogo y rastrea por separado cada programa y sus secciones enlazadas."""
    # Cada programa tiene una ruta propia; procesarlo por separado evita que el límite de páginas
    # de una carrera impida recorrer las demás del catálogo.
    if not program_path_prefix.startswith("/") or ".." in program_path_prefix.split("/"):
        raise ValueError("program_path_prefix debe ser una ruta absoluta válida del sitio.")
    if not 1 <= max_pages_per_program <= 100:
        raise ValueError("max_pages_per_program debe estar entre 1 y 100.")
    if not 0 <= max_depth <= 2:
        raise ValueError("max_depth debe estar entre 0 y 2.")

    catalog_url = _canonical_url(_normalize_source_url(catalog_url))
    catalog_host = _site_host(catalog_url)
    if catalog_host != "cucei.udg.mx":
        raise ValueError("El catálogo académico debe pertenecer al dominio oficial cucei.udg.mx.")
    expected_prefixes = {
        "/oferta-academica/licenciaturas": "/carreras/",
        "/oferta-academica/maestrias": "/maestrias/",
        "/oferta-academica/doctorados": "/doctorados/",
    }
    expected_prefix = expected_prefixes.get(urlparse(catalog_url).path)
    if expected_prefix and program_path_prefix.rstrip("/") + "/" != expected_prefix:
        raise ValueError("La ruta de programas no corresponde al catálogo indicado.")
    run_id = _crawl_run_id or _start_crawl("academic_catalog", catalog_url)
    _update_crawl(
        run_id,
        root_url=catalog_url,
        current_url=catalog_url,
        max_depth_allowed=max_depth,
        program_path_prefix=program_path_prefix,
    )
    # Indexa la lista general sin seguir el menú institucional compartido del sitio.
    try:
        catalog_source = extract_content_from_url(catalog_url, allow_short_html=True)
        catalog_doc = process_url_ingestion(
            url=catalog_url,
            custom_title=catalog_title or catalog_source["title"],
            subsection_id=subsection_id,
            uploaded_by=uploaded_by,
            db=db,
            chunk_metadata={
                "parent_url": None,
                "crawl_root_url": catalog_url,
                "crawl_depth": 0,
                "academic_catalog": True,
            },
            extracted_source=catalog_source,
        )
    except Exception as exc:
        db.rollback()
        _finish_crawl(
            run_id,
            "failed",
            f"No se pudo descargar o indexar el catálogo: {str(exc)[:300]}",
            pages_failed=1,
            failures=[{"url": catalog_url, "error": str(exc)[:500]}],
        )
        raise
    indexed = [{
        "document_id": catalog_doc.id,
        "title": catalog_doc.title,
        "url": catalog_url,
        "rag_status": catalog_doc.rag_status,
        "depth": 0,
    }]
    failures = []

    # Solo toma enlaces de detalle dentro de la familia del catálogo (carreras, maestrías o doctorados).
    prefix = program_path_prefix.rstrip("/") + "/"
    programs = {}
    for link in catalog_source.get("links", []):
        program_url = _canonical_url(link["url"])
        parsed = urlparse(program_url)
        if _site_host(program_url) != catalog_host or not parsed.path.startswith(prefix):
            continue
        # No trata archivos enlazados desde el catálogo como si fueran fichas de programas.
        if _source_extension(program_url, "", b"", None):
            continue
        programs.setdefault(program_url, link.get("title"))

    # No reportes un catálogo como rastreado correctamente si no se detectó ninguna ficha.
    if not programs:
        failures.append({
            "url": catalog_url,
            "error": (
                f"No se detectaron enlaces de programas bajo la ruta {program_path_prefix}; "
                "el catálogo pudo cambiar o generar sus enlaces con JavaScript."
            ),
        })

    # El total detectado permite compararlo con el catálogo; cada programa informa su propio avance.
    print(
        f"[rastreo académico] {catalog_url}: {len(programs)} fichas de programa detectadas.",
        flush=True,
    )
    _update_crawl(
        run_id,
        programs_found=len(programs),
        programs=[
            {"title": title or url, "url": url, "state": "pending"}
            for url, title in programs.items()
        ],
        pages_visited=1,
        pages_indexed=len(indexed),
        pages_failed=len(failures),
        indexed_pages=[
            {"title": item["title"], "url": item["url"], "depth": item["depth"]}
            for item in indexed
        ],
        failures=failures[-100:],
    )
    program_results = []
    truncated_programs = []
    # La ficha del programa suele exponer menús, submenús y enlaces asociados a imágenes.
    for program_index, (program_url, program_title) in enumerate(programs.items(), start=1):
        try:
            parsed = urlparse(program_url)
            # Restringe los enlaces a la ruta de esta carrera/posgrado para no entrar a otros programas.
            scope = parsed.path.rstrip("/") + "/"
            print(
                f"[rastreo académico] Programa {program_index}/{len(programs)}: "
                f"{program_title or program_url}",
                flush=True,
            )
            _update_crawl(
                run_id,
                current_program=program_title or program_url,
                current_url=program_url,
                programs_processed=program_index - 1,
            )
            result = process_url_crawl(
                root_url=program_url,
                root_title=program_title,
                allowed_path_prefixes=[scope],
                max_pages=max_pages_per_program,
                max_depth=max_depth,
                subsection_id=subsection_id,
                uploaded_by=uploaded_by,
                db=db,
                _crawl_run_id=run_id,
            )
            indexed.extend(result["indexed"])
            failures.extend(result["failures"])
            program_result = {
                "title": program_title or program_url,
                "url": program_url,
                "state": "limit_reached" if result["limit_reached"] else (
                    "completed_with_errors" if result["pages_failed"] else "completed"
                ),
                "pages_indexed": result["pages_indexed"],
                "pages_failed": result["pages_failed"],
                "limit_reached": result["limit_reached"],
                "pending_pages": result["pending_pages"],
                "pages_visited": result["pages_visited"],
                "indexed_pages": [
                    {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                    for item in result["indexed"]
                ],
                "failed_pages": result["failures"],
                "max_depth_reached": result["max_depth_reached"],
                "max_depth_allowed": result["max_depth_allowed"],
                "queue_exhausted": result["queue_exhausted"],
            }
            program_results.append(program_result)
            if result["limit_reached"]:
                truncated_programs.append(program_result)
            print(
                f"[rastreo académico] Fin de programa: {program_result['pages_indexed']} páginas "
                f"indexadas, {program_result['pages_failed']} fallidas, "
                f"límite alcanzado={program_result['limit_reached']}.",
                flush=True,
            )
            _update_crawl(
                run_id,
                current_program=program_title or program_url,
                current_url=None,
                programs_found=len(programs),
                programs_processed=program_index,
                programs=[
                    next(
                        (item for item in program_results if item["url"] == url),
                        {"title": title or url, "url": url, "state": "pending"},
                    )
                    for url, title in programs.items()
                ],
                pages_visited=sum(item["pages_visited"] for item in program_results) + 1,
                pages_indexed=len(indexed),
                pages_failed=len(failures),
                indexed_pages=[
                    {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                    for item in indexed
                ],
                pending_pages=sum(item["pending_pages"] for item in program_results),
                limit_reached=bool(truncated_programs),
                failures=failures[-100:],
            )
        except Exception as exc:
            db.rollback()
            failures.append({"url": program_url, "error": str(exc)[:500]})
            program_results.append({
                "title": program_title or program_url,
                "url": program_url,
                "state": "failed",
                "pages_indexed": 0,
                "pages_failed": 1,
                "limit_reached": False,
                "pending_pages": 0,
                "pages_visited": 0,
                "max_depth_reached": 0,
                "max_depth_allowed": max_depth,
                "queue_exhausted": False,
            })
            _update_crawl(
                run_id,
                programs_found=len(programs),
                programs_processed=program_index,
                programs=[
                    next(
                        (item for item in program_results if item["url"] == url),
                        {"title": title or url, "url": url, "state": "pending"},
                    )
                    for url, title in programs.items()
                ],
                pages_indexed=len(indexed),
                pages_failed=len(failures),
                indexed_pages=[
                    {"title": item["title"], "url": item["url"], "depth": item["depth"]}
                    for item in indexed
                ],
                failures=failures[-100:],
            )

    result = {
        "root_url": catalog_url,
        "programs_found": len(programs),
        "indexed": indexed,
        "failures": failures,
        "pages_indexed": len(indexed),
        "pages_failed": len(failures),
        "program_results": program_results,
        "programs_limit_reached": len(truncated_programs),
        "pages_visited": sum(item["pages_visited"] for item in program_results) + 1,
        "max_depth_allowed": max_depth,
        "queue_exhausted": bool(program_results) and all(
            item["queue_exhausted"] for item in program_results
        ),
        "coverage_note": (
            "El resultado lista las fichas detectadas y sus páginas recorridas. El rastreo sigue "
            "enlaces HTML estáticos del mismo dominio dentro de la carpeta del programa y la profundidad "
            "configurada; no ejecuta JavaScript ni descubre contenido que el sitio no exponga como enlace."
        ),
    }
    state = "limit_reached" if truncated_programs else (
        "completed_with_errors" if failures else "completed"
    )
    _finish_crawl(
        run_id,
        state,
        f"{len(programs)} fichas detectadas; {len(indexed)} páginas indexadas; "
        f"{len(failures)} fallidas; {len(truncated_programs)} programas con límite alcanzado.",
        programs_found=len(programs),
        programs_processed=len(program_results),
        programs=program_results,
        pages_visited=sum(item["pages_visited"] for item in program_results) + 1,
        pages_indexed=len(indexed),
        pages_failed=len(failures),
        indexed_pages=[
            {"title": item["title"], "url": item["url"], "depth": item["depth"]}
            for item in indexed
        ],
        pending_pages=sum(item["pending_pages"] for item in program_results),
        limit_reached=bool(truncated_programs),
        failures=failures[-100:],
    )
    return result
