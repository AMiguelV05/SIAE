"""Reintenta únicamente URLs que fallaron por la cuota diaria de Groq en registros guardados."""

import argparse
import json
import os
import re
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

import requests


BASE_URL = os.getenv("SIAE_API_URL", "http://127.0.0.1:8080").rstrip("/")
# El progreso se guarda fuera del proyecto para que una interrupción no provoque reintentos dobles.
STATE_PATH = Path(tempfile.gettempdir()) / "siae_groq_retry_successes.json"
LOG_PREFIX = "[fuentes] Error en "
# URLs incluidas directamente en la petición, donde el registro adjunto confirmó el mismo 429 TPD.
EXTRA_DAILY_QUOTA_URLS = (
    "https://practicas.cucei.udg.mx/dist/documentos_descarga/ficha-de-registro-laboral.docx",
    "https://practicas.cucei.udg.mx/dist/documentos_descarga/carta-de-solicitud.docx",
    "https://practicas.cucei.udg.mx/dist/documentos_descarga/bitacora-de-actividades.docx",
)


def _is_cucei_url(url: str) -> bool:
    """Limita las URLs extraídas a CUCEI y sus subdominios institucionales."""
    host = (urlsplit(url).hostname or "").casefold()
    return urlsplit(url).scheme in {"http", "https"} and (
        host == "cucei.udg.mx" or host.endswith(".cucei.udg.mx")
    )


def extract_daily_quota_urls(log_paths: list[Path]) -> list[str]:
    """Busca bloques de error cuyo detalle confirma TPD de Groq con límite de 200,000."""
    selected = []
    seen = set()

    for log_path in log_paths:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        current_url = None
        current_detail = []

        def save_current() -> None:
            # Solo guarda errores con código 429, referencia a tokens diarios y el límite indicado.
            detail = " ".join(current_detail).casefold()
            is_daily_quota_error = (
                "429" in detail
                and ("tokens per day" in detail or re.search(r"\btpd\b", detail))
                and ("200000" in detail or "200,000" in detail)
            )
            if current_url and is_daily_quota_error and _is_cucei_url(current_url):
                if current_url not in seen:
                    seen.add(current_url)
                    selected.append(current_url)

        for line in lines:
            if line.startswith(LOG_PREFIX):
                save_current()
                entry = line[len(LOG_PREFIX):]
                # El separador es «: » para no confundirlo con los dos puntos de https://.
                separator = entry.find(": ")
                if separator < 0:
                    current_url = None
                    current_detail = []
                    continue
                current_url = entry[:separator].strip()
                current_detail = [entry[separator + 2:]]
            elif current_url:
                # El mensaje de Groq puede ocupar varias líneas en el registro de PowerShell.
                current_detail.append(line)

        save_current()

    for url in EXTRA_DAILY_QUOTA_URLS:
        if url not in seen:
            selected.append(url)
            seen.add(url)
    return selected


def _load_progress() -> tuple[set[str], set[str]]:
    """Recupera URLs indexadas y fallos no relacionados con la cuota para no repetirlos."""
    try:
        stored = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        return (
            set(stored.get("successful_urls", [])),
            set(stored.get("skipped_urls", [])),
        )
    except (OSError, ValueError, TypeError):
        return set(), set()


def _save_progress(successful_urls: set[str], skipped_urls: set[str]) -> None:
    """Guarda el avance para continuar después sin repetir solicitudes ya resueltas."""
    STATE_PATH.write_text(
        json.dumps(
            {
                "successful_urls": sorted(successful_urls),
                "skipped_urls": sorted(skipped_urls),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reintenta URLs CUCEI rechazadas por el límite diario de tokens de Groq."
    )
    parser.add_argument(
        "logs",
        nargs="+",
        type=Path,
        help="Archivos de texto pegados desde los registros de rastreo.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Envía las URLs elegidas al backend. Sin esta opción solo muestra la lista.",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=3.0,
        help="Pausa entre solicitudes para evitar ráfagas (predeterminado: 3 segundos).",
    )
    args = parser.parse_args()

    missing_logs = [str(path) for path in args.logs if not path.is_file()]
    if missing_logs:
        parser.error("No se encontraron estos registros: " + ", ".join(missing_logs))

    urls = extract_daily_quota_urls(args.logs)
    successful_urls, skipped_urls = _load_progress()
    handled_urls = successful_urls | skipped_urls
    pending_urls = [url for url in urls if url not in handled_urls]

    print(f"URLs CUCEI con rechazo por TPD=200000 encontradas: {len(urls)}")
    print(f"Ya indexadas por este script: {len(set(urls) & successful_urls)}")
    print(f"Omitidas por un error distinto de cuota: {len(set(urls) & skipped_urls)}")
    print(f"Pendientes: {len(pending_urls)}")
    for index, url in enumerate(pending_urls, start=1):
        print(f"{index}. {url}")

    if not args.execute:
        print("\nVista previa: no se envió ninguna solicitud. Añade --execute para iniciar el reintento.")
        return 0
    if not pending_urls:
        print("No hay URLs pendientes para enviar.")
        return 0

    try:
        health = requests.get(f"{BASE_URL}/health", timeout=10)
        health.raise_for_status()
    except requests.RequestException as exc:
        print(f"No se pudo confirmar que la API esté activa en {BASE_URL}: {exc}")
        return 1

    print("\nReintentando una URL a la vez. Si Groq vuelve a rechazar por TPD, el proceso se detendrá.")
    succeeded_this_run = 0
    failed = 0
    for index, url in enumerate(pending_urls, start=1):
        print(f"[{index}/{len(pending_urls)}] {url}", flush=True)
        try:
            response = requests.post(
                f"{BASE_URL}/docs/upload-url",
                data={"url": url},
                timeout=(15, 1800),
            )
        except requests.RequestException as exc:
            # Un timeout no confirma si el servidor terminó el OCR; se detiene para evitar duplicarlo.
            print(f"  Se detuvo por un problema de conexión; no se repetirá esta solicitud automáticamente: {exc}")
            return 1

        if response.ok:
            try:
                result = response.json()
            except ValueError:
                result = {}
            if result.get("rag_status") == "vectorizado":
                successful_urls.add(url)
                _save_progress(successful_urls, skipped_urls)
                succeeded_this_run += 1
                print(f"  Indexada: {result.get('title', 'fuente CUCEI')}")
                time.sleep(max(0.0, args.delay_seconds))
                continue

        detail = response.text
        print(f"  Error HTTP {response.status_code}: {detail[:700]}")
        failed += 1
        lower_detail = detail.casefold()
        if "429" in lower_detail and (
            "tokens per day" in lower_detail or re.search(r"\btpd\b", lower_detail)
        ):
            print("  Se detiene porque la cuota diaria sigue agotada; las URLs restantes quedan pendientes.")
            break
        # Un fallo distinto de TPD necesita otra corrección; no se reintenta al reanudar este lote.
        skipped_urls.add(url)
        _save_progress(successful_urls, skipped_urls)
        time.sleep(max(0.0, args.delay_seconds))

    not_processed = len(pending_urls) - succeeded_this_run - failed
    print(
        f"\nResumen de esta ejecución: {succeeded_this_run} indexadas, {failed} con error, "
        f"{not_processed} pendientes sin enviar."
    )
    print(f"Progreso guardado temporalmente en: {STATE_PATH}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
