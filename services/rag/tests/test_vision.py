"""Comprueba la extracción OCR de una imagen elegida por el usuario mediante Groq Vision."""

import argparse
from pathlib import Path
import sys

from PIL import Image

from app.ingestion import extract_text_from_image


# Permite mostrar en la consola de Windows el texto OCR con acentos y otros caracteres.
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "image",
        type=Path,
        help="Ruta a una imagen local PNG, JPG, WEBP, BMP, GIF o TIFF.",
    )
    parser.add_argument(
        "--allow-groq-image-content",
        action="store_true",
        help="confirma que se enviará la imagen a Groq Vision para extraer su texto",
    )
    args = parser.parse_args()
    if not args.allow_groq_image_content:
        parser.error(
            "esta prueba envía el contenido de la imagen a Groq; autorízalo con "
            "--allow-groq-image-content"
        )
    if not args.image.is_file():
        parser.error(f"no existe el archivo de imagen: {args.image}")

    # El OCR requiere confirmación porque el contenido se envía al servicio de Groq.
    with Image.open(args.image) as image:
        text = extract_text_from_image(image)
    if not text or not text.strip():
        raise AssertionError("Groq Vision no extrajo texto de la imagen.")
    print("=== TEXTO EXTRAÍDO POR GROQ VISION ===")
    print(text)
    print("\n✓ La imagen produjo texto extraído.")


if __name__ == "__main__":
    main()
