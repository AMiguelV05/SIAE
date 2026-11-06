# Fuentes públicas y documentos para indexar en SIAE.
import argparse
import hashlib
import os
import re
from pathlib import Path

import requests

# Dirección del backend que recibirá los archivos y las fuentes web.
BASE_URL = os.getenv("SIAE_API_URL", "http://127.0.0.1:8080").rstrip("/")
# Carpeta local y extensiones que la API acepta para la ingesta de archivos.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_DIR = PROJECT_ROOT / "uploads"
SUPPORTED_FILE_EXTENSIONS = (".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff")

# Estas fuentes públicas de CUCEI se cargan cada vez que se ejecuta este script.
# El PDF es la fuente vigente para el organigrama de 2021; se omite la imagen local anterior.
SOURCE_URLS = [
    {
        "url": "https://www.cucei.udg.mx/sites/default/files/adjuntos/organigrama_general-2021.pdf",
        "title": "Organigrama General CUCEI 2021",
        # Al indexar este PDF, pide reemplazar la imagen antigua de prueba con ese nombre.
        "replace_file_name": "organigrama_general-2021.jpeg",
    },
    {
        "url": "https://www.cucei.udg.mx/acerca-de/organizacion",
        "title": "Organización CUCEI",
    },
    {
        "url": "https://www.cucei.udg.mx/acerca-de/ubicacion",
        "title": "Ubicación CUCEI",
    },
    {
        "url": "https://www.cucei.udg.mx/sites/default/files/adjuntos/mapa-cucei-3d-2018.pdf",
        "title": "Mapa CUCEI 3D 2018",
    },
    {
        "url": "https://www.cucei.udg.mx/acerca/directorio",
        "title": "Directorio Oficial CUCEI",
    },
    {
        "url": "https://drive.google.com/file/d/1eNO5y4U0oL6ECFQZjQEYeZvnhUOMF5Zj/view",
    },
    {
        "url": "https://investigacion.cucei.udg.mx/cicual/formatos",
        "title": "CICUAL CUCEI — formatos y registro de protocolos",
    },
    {
        "url": "https://investigacion.cucei.udg.mx/sites/default/files/adjuntos/formato_1_para_registro_de_proyectos_de_investigacion_del_cucei_que_utilizan_animales_de_experimentacion_vf_10052023.docx",
        "title": "CICUAL — Formato 1 para proyectos con animales de experimentación",
    },
    {
        "url": "https://investigacion.cucei.udg.mx/sites/default/files/adjuntos/formato_para_registro_de_proyectos_de_investigacion_del_cucei_que_utilizan_animales_de_experimentacion_vf_10052023.docx",
        "title": "CICUAL — Formato para registro de proyectos con animales de experimentación",
    },
    # Servicios y apoyo a idiomas.
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas", "title": "CUCEI — Apoyo a idiomas"},
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/centro-de-aprendizaje-global", "title": "CUCEI — Centro de Aprendizaje Global"},
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/programa-jobs", "title": "CUCEI — Programa JOBS"},
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/materiales-en-otro-idioma", "title": "CUCEI — Materiales en otro idioma"},
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/becas-y-apoyos-para-idiomas", "title": "CUCEI — Becas y apoyos para idiomas"},
    {"url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas/acreditacion-de-ingles", "title": "CUCEI — Acreditación de inglés"},
    {"url": "https://www.cucei.udg.mx/servicios/becas", "title": "CUCEI — Becas"},
    {"url": "https://www.cucei.udg.mx/servicios/bolsa-de-trabajo", "title": "CUCEI — Bolsa de Trabajo"},
    {"url": "https://www.cucei.udg.mx/servicios/practicas-profesionales", "title": "CUCEI — Prácticas Profesionales"},
    {"url": "https://practicas.cucei.udg.mx/", "title": "CUCEI — Portal de Prácticas Profesionales"},
    {"url": "https://www.cucei.udg.mx/servicios/consultoria-tecnologica", "title": "CUCEI — Consultoría Tecnológica"},
    {"url": "https://www.cucei.udg.mx/servicios/entrenamiento-deportivo", "title": "CUCEI — Entrenamiento Deportivo"},
    {"url": "https://www.cucei.udg.mx/servicios/internet-y-telecomunicaciones", "title": "CUCEI — Internet y Telecomunicaciones"},
    {"url": "https://www.cucei.udg.mx/servicios/medicos-y-clinicos", "title": "CUCEI — Servicios Médicos y Clínicos"},
    {"url": "https://www.cucei.udg.mx/servicios/servicios-bibliotecarios", "title": "CUCEI — Servicios Bibliotecarios"},
    {"url": "https://wdg.biblio.udg.mx/", "title": "UdeG — Biblioteca Digital WDG"},
    {"url": "https://biblioteca.cucei.udg.mx/libros-electronicos-myilibrary", "title": "CUCEI — Libros electrónicos MyiLibrary"},
    {"url": "https://www.riudg.udg.mx/", "title": "UdeG — Repositorio Institucional RIUdeG"},
    {"url": "https://www.cucei.udg.mx/servicios/servicio-social", "title": "CUCEI — Servicio Social"},
    {"url": "https://ss.siiau.udg.mx/", "title": "UdeG — Sistema de Administración de Servicio Social"},
    {"url": "https://www.cucei.udg.mx/servicios/talleres-culturales", "title": "CUCEI — Talleres Culturales"},
    # Extensión, divulgación y comunidad.
    {"url": "https://www.cucei.udg.mx/extension-y-difusion/transferencia-de-tecnologia", "title": "CUCEI — Transferencia de Tecnología"},
    {"url": "https://www.cucei.udg.mx/extension-y-difusion/vinculacion-con-la-empresa", "title": "CUCEI — Vinculación con la Empresa"},
    {"url": "https://www.cucei.udg.mx/extension-y-difusion/difusion-cientifica", "title": "CUCEI — Difusión Científica"},
    {"url": "https://www.cucei.udg.mx/extension-y-difusion/catedras-cucei", "title": "CUCEI — Cátedras CUCEI"},
    {"url": "https://www.cucei.udg.mx/extension-y-difusion/informacion-meteorologica", "title": "CUCEI — Información Meteorológica"},
    {"url": "https://eventos.cucei.udg.mx/", "title": "CUCEI — Sistema de Eventos"},
    {"url": "https://www.cucei.udg.mx/comunidad/academicos", "title": "CUCEI — Directorio de Académicos"},
    # Portales institucionales y oferta educativa.
    {"url": "https://escolar.cucei.udg.mx/cescolar/", "title": "CUCEI — Control Escolar"},
    {"url": "https://escolar.udg.mx/", "title": "UdeG — Control Escolar"},
    {"url": "https://www.cucei.udg.mx/oferta-academica/licenciaturas", "title": "CUCEI — Oferta Académica de Licenciaturas"},
    {"url": "https://www.cucei.udg.mx/oferta-academica/maestrias", "title": "CUCEI — Oferta Académica de Maestrías"},
    {"url": "https://www.cucei.udg.mx/oferta-academica/doctorados", "title": "CUCEI — Oferta Académica de Doctorados"},
    {
        "url": "https://www.cucei.udg.mx/carreras/computacion/es/malla-curricular-icom-2021",
        "title": "Ingeniería en Computación — Malla Curricular ICOM 2021",
    },
    {"url": "https://www.cucei.udg.mx/oferta-academica/educacion-continua", "title": "CUCEI — Educación Continua"},
    {"url": "https://www.cucei.udg.mx/acerca-de/historia", "title": "CUCEI — Historia"},
    {"url": "https://www.cucei.udg.mx/acerca-de/mision-y-vision", "title": "CUCEI — Misión y Visión"},
]

CRAWL_SOURCES = [
    # Los catálogos académicos se recorren por programa para que sus menús no compitan
    # entre sí por un único límite de páginas.
    {
        "strategy": "academic_catalog",
        "url": "https://www.cucei.udg.mx/oferta-academica/licenciaturas",
        "title": "Oferta académica CUCEI — licenciaturas",
        "program_path_prefix": "/carreras/",
        "max_pages_per_program": 60,
        "max_depth": 2,
    },
    {
        "strategy": "academic_catalog",
        "url": "https://www.cucei.udg.mx/oferta-academica/maestrias",
        "title": "Oferta académica CUCEI — maestrías",
        "program_path_prefix": "/maestrias/",
        "max_pages_per_program": 60,
        "max_depth": 2,
    },
    {
        "strategy": "academic_catalog",
        "url": "https://www.cucei.udg.mx/oferta-academica/doctorados",
        "title": "Oferta académica CUCEI — doctorados",
        "program_path_prefix": "/doctorados/",
        "max_pages_per_program": 60,
        "max_depth": 2,
    },
    {
        "url": "https://www.cucei.udg.mx/servicios/apoyo-a-idiomas",
        "title": "CUCEI — apoyo a idiomas y sus programas",
        "allowed_path_prefixes": "/servicios/apoyo-a-idiomas",
        "max_pages": 30,
        "max_depth": 2,
    },
    {
        "url": "https://www.cucei.udg.mx/servicios/bolsa-de-trabajo",
        "title": "CUCEI — bolsa de trabajo y vacantes por carrera",
        "allowed_path_prefixes": "/servicios/bolsa-de-trabajo",
        "max_pages": 60,
        "max_depth": 2,
    },
    {
        "url": "https://practicas.cucei.udg.mx/",
        "title": "CUCEI — portal y guías de prácticas profesionales",
        "allowed_path_prefixes": "/",
        "max_pages": 30,
        "max_depth": 1,
    },
    {
        "url": "https://wdg.biblio.udg.mx/",
        "title": "UdeG — servicios de Biblioteca Digital WDG",
        "allowed_path_prefixes": "/",
        "max_pages": 50,
        "max_depth": 1,
    },
    {
        "url": "https://eventos.cucei.udg.mx/",
        "title": "CUCEI — eventos, actividades y ayuda del sistema",
        "allowed_path_prefixes": "/",
        "max_pages": 40,
        "max_depth": 1,
    },
]


def file_sha256(path):
    """Calcula una huella para reconocer archivos idénticos sin leerlos de una sola vez."""
    # Lee por bloques para calcular el hash sin cargar el archivo completo en memoria.
    digest = hashlib.sha256()
    with open(path, "rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def upload_all_documents():
    """Envía a la API los archivos compatibles que encuentre en uploads/."""
    if not os.path.exists(UPLOADS_DIR):
        print(f"La carpeta '{UPLOADS_DIR}' no existe. Por favor créala y coloca los documentos ahí.")
        return

    # Omite la imagen reemplazada por el PDF y cualquier copia binariamente idéntica.
    replaced_image = os.path.join(UPLOADS_DIR, "organigrama_general-2021.jpeg")
    replaced_hash = file_sha256(replaced_image) if os.path.isfile(replaced_image) else None
    files = [
        f for f in os.listdir(UPLOADS_DIR)
        if f.lower().endswith(SUPPORTED_FILE_EXTENSIONS)
        and f.lower() != "organigrama_general-2021.jpeg"
        and not (
            replaced_hash
            and f.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff"))
            and file_sha256(os.path.join(UPLOADS_DIR, f)) == replaced_hash
        )
    ]
    # Los archivos con nombres legibles quedan primero; al final van los nombres UUID.
    files.sort(
        key=lambda filename: (
            bool(re.fullmatch(r"[0-9a-f]{32}", os.path.splitext(filename)[0].lower())),
            filename.lower(),
        )
    )
    # Conserva el primer nombre por contenido; el orden anterior favorece nombres originales legibles.
    unique_files = {}
    # Si hay duplicados exactos, conserva una sola copia para enviar a la API.
    for filename in files:
        digest = file_sha256(os.path.join(UPLOADS_DIR, filename))
        unique_files.setdefault(digest, filename)
    files = list(unique_files.values())
    print(f"Se encontraron {len(files)} archivos para ingestar.\n")

    # Sube cada archivo de manera independiente para que un fallo no interrumpa los demás.
    for idx, filename in enumerate(files, start=1):
        file_path = os.path.join(UPLOADS_DIR, filename)
        print(f"[{idx}/{len(files)}] Ingestando: {filename}...")

        try:
            with open(file_path, "rb") as f:
                # Envía el documento como multipart/form-data y acompaña un título legible.
                response = requests.post(
                    f"{BASE_URL}/docs/upload",
                    files={"file": (filename, f)},
                    data={"title": filename.replace(".pdf", "").replace("_", " ").title()}
                )
            if response.status_code in [200, 201]:
                res_data = response.json()
                print(f"   Éxito | Status: {res_data.get('rag_status')} | ID: {res_data.get('document_id')}")
            else:
                print(f"   Omitido/Error ({response.status_code}): {response.text}")
        except Exception as err:
            print(f"   Error de conexión con {filename}: {err}")
        print("-" * 50)

    print("\nProceso de ingesta masiva completado.")


def upload_public_sources():
    """Indexa las URL individuales y después rastrea sus subpáginas configuradas."""
    # Las fuentes web y los rastreos se procesan por separado para mostrar sus fallos con claridad.
    print("\nIndexando páginas y documentos oficiales CUCEI...\n")
    # Cada URL individual se envía al endpoint que descarga y procesa un recurso.
    for index, source in enumerate(SOURCE_URLS, start=1):
        label = source.get("title") or source["url"]
        print(f"[{index}/{len(SOURCE_URLS)}] {label} — {source['url']}")
        try:
            response = requests.post(
                f"{BASE_URL}/docs/upload-url",
                data=source,
                # El segundo valor deja esperar la descarga y el OCR de documentos grandes.
                timeout=(15, 600),
            )
            if response.status_code in (200, 201):
                result = response.json()
                print(f"   Éxito | Status: {result.get('rag_status')} | ID: {result.get('document_id')}")
            else:
                print(f"   Error ({response.status_code}): {response.text}")
        except requests.RequestException as err:
            print(f"   Error de conexión: {err}")
        print("-" * 50)

    print("\nRastreando subpáginas oficiales seleccionadas...\n")
    # Los rastreos pueden tardar más porque recorren varias páginas enlazadas.
    for source in CRAWL_SOURCES:
        print(f"{source['title']} — {source['url']}")
        try:
            # Los catálogos académicos tienen un endpoint dedicado que recorre cada programa
            # y limita sus enlaces a la ruta de su propia ficha.
            endpoint = (
                "/docs/crawl-academic-catalog"
                if source.get("strategy") == "academic_catalog"
                else "/docs/crawl-url"
            )
            response = requests.post(
                f"{BASE_URL}{endpoint}",
                data=source,
                # El rastreo puede tardar más porque solicita y procesa varias páginas.
                timeout=(15, 1800),
            )
            if response.ok:
                result = response.json()
                print(f"   Páginas indexadas: {result.get('pages_indexed', 0)}; fallidas: {result.get('pages_failed', 0)}")
                for failure in result.get("failures", []):
                    print(f"   Error {failure['url']}: {failure['error']}")
            else:
                print(f"   Error ({response.status_code}): {response.text}")
        except requests.RequestException as err:
            print(f"   Error de conexión: {err}")
        print("-" * 50)


if __name__ == "__main__":
    # Los modos son excluyentes para permitir ingestar solo fuentes públicas o solo archivos locales.
    parser = argparse.ArgumentParser(description="Indexa documentos y fuentes oficiales de SIAE.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--public-only", action="store_true", help="Solo procesa URLs y subpáginas oficiales.")
    mode.add_argument("--local-only", action="store_true", help="Solo procesa archivos de uploads/.")
    args = parser.parse_args()

    # Sin --public-only, también procesa los documentos de uploads/.
    if not args.public_only:
        upload_all_documents()
    # Sin --local-only, procesa las URL y los rastreos configurados.
    if not args.local_only:
        upload_public_sources()
