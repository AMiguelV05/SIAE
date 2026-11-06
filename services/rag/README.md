# SIAE Backend: ingesta documental y asistente RAG

Esto se trata de un backend con base de datos provisional para probar el módulo RAG de asistencia estudiantil del SIAE e integrarlo gradualmente con el resto del sistema. Permite indexar PDFs, imágenes y páginas web públicas; responder preguntas con información recuperada de esas fuentes; y guardar conversaciones, mensajes y citas.

Se puede ejecutar de forma independiente durante el desarrollo. Usa SQLite por defecto y crea las tablas que necesita; más adelante puede conectarse a la base de datos compartida del sistema. La autenticación todavía no está integrada, así que en desarrollo se crean usuarios locales de prueba a partir del `user_id` recibido.

Para generar respuestas, el backend envía a Groq la pregunta y los fragmentos recuperados. Cuando una fuente requiere OCR, también envía las imágenes de sus páginas o las imágenes incrustadas en un DOCX. Por eso, evita usar información personal o sensible mientras trabajas con esta configuración de desarrollo.

## Qué incluye

- Extracción página por página de PDF con texto seleccionable y OCR de páginas escaneadas o con una capa de texto insuficiente mediante Groq Vision.
- OCR/lectura de imágenes PNG, JPG, WEBP, BMP, GIF y TIFF mediante Groq Vision.
- Extracción ampliada de DOCX: párrafos, tablas, encabezados y pies, notas, comentarios, hipervínculos, cuadros de texto, gráficos y diagramas; también aplica OCR a imágenes rasterizadas incrustadas.
- Ingesta desde URL de páginas HTML públicas, PDF, DOCX e imágenes; conserva títulos, encabezados y bloques de contenido. También desenvuelve enlaces de Office Viewer y Google Drive.
- Metadatos por fragmento (título, URL, formato, encabezado, ubicación, índice y relación con página padre) que enriquecen la recuperación híbrida.
- Rastreo opcional y acotado de enlaces internos, con límites explícitos de páginas, profundidad y prefijos de ruta permitidos.
- Fragmentos más pequeños, embeddings locales multilingües y búsqueda semántica con coincidencia de palabras.
- Respuestas en español con citas a documento, página, fragmento y puntaje de similitud.
- Ingesta de páginas institucionales públicas.
- Registro local de conversaciones, mensajes, fuentes y tickets.
- Documentación interactiva de la API en `/docs`.

La base local incluye las tablas de documentos, fragmentos, conversaciones, mensajes, fuentes y tickets, además de tablas mínimas de usuario, administrador y subsección para conservar las relaciones principales del diagrama. El CRUD de usuarios y administradores, publicaciones, notificaciones y pronósticos queda fuera de este módulo. Los vectores se guardan como JSON en SQLite y se comparan en memoria, adecuado para desarrollo y corpus pequeños. Al integrar PostgreSQL puede cambiarse `DATABASE_URL` y luego migrar la búsqueda a `pgvector`.

## Requisitos

- Windows 10/11, macOS o Linux.
- Python 3.11 recomendado (3.10 como mínimo).
- Conexión a internet la primera vez para instalar paquetes y descargar el modelo de embeddings.
- Una API key de Groq para generar respuestas y procesar imágenes o PDFs escaneados. La extracción de PDFs con texto seleccionable y la creación de embeddings no requieren una API key.
- El renderizado de PDF usa `pypdfium2`, incluido en las dependencias de Python; no requiere instalar Poppler por separado.

## Instalación en Windows PowerShell

Desde la carpeta del repositorio:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Abre `.env` y pega tu clave en `GROQ_API_KEY`. Nunca la subas al repositorio. Para usar el entorno en una sesión nueva, activa `.venv` antes de ejecutar comandos.

Si PowerShell bloquea la activación del entorno virtual, ejecuta en esa sesión:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## Instalación en macOS/Linux

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y configura `GROQ_API_KEY`.

## OCR de PDFs escaneados

Para leer un PDF escaneado, el backend primero convierte sus páginas en imágenes con `pypdfium2`, una dependencia de Python; por eso no necesitas instalar Poppler ni modificar el `PATH`. Después, Groq Vision reconoce el texto de las páginas que requieren lectura visual, por lo que debes configurar `GROQ_API_KEY` para usar OCR. El mismo proceso se aplica a páginas con imágenes grandes —como capturas de pantalla— aunque también tengan texto seleccionable: se combinan el texto extraído localmente y el texto reconocido en la imagen. El tamaño mínimo de imagen que activa esta lectura se configura con `PDF_OCR_MIN_IMAGE_PIXELS` (por defecto, `250000` píxeles). Si una página solo contiene texto seleccionable y no necesita OCR, se procesa localmente sin enviarla a Groq.

## Ejecutar

Ejecuta los comandos desde la carpeta raíz del repositorio (`siae-backend`).

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8080
```

La primera carga de `SentenceTransformer` descarga el modelo indicado por `EMBEDDING_MODEL` y puede tardar. Después, la API queda disponible en:

- Estado: <http://127.0.0.1:8080/health>
- Swagger: <http://127.0.0.1:8080/docs>
- Redoc: <http://127.0.0.1:8080/redoc>

Mantén `--host 127.0.0.1` mientras no tengas autenticación. No expongas esta API en una red pública.

## Configuración

Copia `.env.example` a `.env`. Las variables opcionales tienen valores de desarrollo razonables.

| Variable | Uso | Valor local predeterminado |
| --- | --- | --- |
| `GROQ_API_KEY` | Respuestas del LLM y visión/OCR | vacío |
| `DATABASE_URL` | Conexión SQLAlchemy | `sqlite:///./siae_local.db` |
| `UPLOAD_DIR` | Archivos originales cargados; se conserva un archivo con nombre legible por contenido | `uploads` |
| `MAX_UPLOAD_MB` | Tamaño máximo de archivo | `25` |
| `MAX_URL_DOWNLOAD_MB` | Tamaño máximo de cualquier recurso descargado desde una URL | `50` |
| `EMBEDDING_MODEL` | Modelo de embeddings local | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `EMBEDDING_DEVICE` | `cpu`, `cuda` u otro dispositivo compatible | automático |
| `EMBEDDING_BATCH_SIZE` | Fragmentos por lote al generar vectores | `32` |
| `CHUNK_SIZE_WORDS` | Tamaño máximo aproximado del fragmento en palabras | `100` |
| `CHUNK_OVERLAP_WORDS` | Palabras compartidas entre fragmentos consecutivos | `20` |
| `RAG_TOP_K` | Valor predeterminado para llamadas internas sin `top_k`; `/messages/ask` fija 6 | `6` |
| `RAG_MIN_SCORE` | Umbral semántico mínimo; también se conservan coincidencias léxicas fuertes | `0.25` |
| `LLM_MODEL` | Modelo de chat en Groq | `openai/gpt-oss-120b` |
| `VISION_MODEL` | Modelo multimodal en Groq | `qwen/qwen3.8-27b` |
| `VISION_MAX_TOKENS` | Máximo de salida por lectura OCR de imagen | `850` (máximo admitido por el backend: `900`) |
| `LLM_MAX_TOKENS` | Límite de salida del modelo | `900` |
| `CORS_ORIGINS` | Orígenes web permitidos, separados por coma | localhost en puertos 3000 y 5173 |
| `SIAE_AUTO_REFRESH_SOURCES` | Activa la actualización automática de fuentes públicas | `true` |
| `SIAE_SOURCE_REFRESH_HOURS` | Intervalo entre revisiones automáticas | `96` (4 días) |
| `SIAE_SOURCE_REFRESH_START_DELAY_SECONDS` | Espera tras iniciar la API antes de la primera revisión | `30` |

Para PostgreSQL instala también `psycopg[binary]` (ya está incluido en `requirements.txt`) y asigna, por ejemplo, `DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/siae`. Las tablas se crean al iniciar. La aplicación agrega de forma compatible la columna `metadata_json` a una tabla `document_chunks` existente y rellena metadatos básicos de los registros antiguos sin recalcular embeddings.

## API principal

Las operaciones que reciben campos usan `multipart/form-data`, incluidos los endpoints de chat.

| Método y ruta | Uso |
| --- | --- |
| `GET /health` | Comprueba que la API responde. |
| `POST /conversations/new` | Crea una conversación titulada inicialmente `Nueva consulta SIAE`. `user_id` es opcional y por defecto usa `local-demo-user`. |
| `POST /messages/ask` | Pregunta al RAG. Campos: `question`, opcionales `user_id` y `conversation_id`. Al responder, intenta asignar un título usando las primeras preguntas informativas disponibles (hasta tres); si solo hay saludos, conserva el título genérico y lo asigna cuando aparezca un tema. Una vez asignado, lo mantiene. Devuelve `conversation_title`, `user_message_id` (para crear un ticket desde esa pregunta) y `message_id` (para la respuesta del asistente). La búsqueda usa 6 fragmentos por defecto. |
| `GET /conversations/user/{user_id}` | Lista conversaciones activas. |
| `GET /conversations/{conversation_id}/messages` | Obtiene mensajes y citas guardadas. |
| `POST /docs/upload` | Indexa PDF, DOCX o imagen PNG, JPG, JPEG, WEBP, BMP, GIF o TIFF. Reutiliza archivos con el mismo contenido y guarda nuevas fuentes con su nombre original, sin crear copias UUID. Acepta `file` y opcionalmente `title`, `category`, `subsections_id`, `uploaded_by`. |
| `POST /docs/upload-url` | Descarga e indexa HTML público, PDF, DOCX o imagen. Acepta `url` y opcionalmente `title`, `subsections_id`, `uploaded_by`, `replace_file_name`. |
| `POST /docs/crawl-url` | Indexa una página HTML y sus enlaces internos permitidos. Campos: `url`, opcional `title`, `allowed_path_prefixes` (separados por coma), `max_pages` (1–100), `max_depth` (0–2). El valor predeterminado solo sigue rutas `/carreras/`. |
| `POST /docs/crawl-academic-catalog` | Indexa un catálogo de licenciaturas, maestrías o doctorados y después recorre cada ficha de programa por separado. Campos: `url`, `program_path_prefix`, `max_pages_per_program` (1–100) y `max_depth` (0–2). |
| `GET /docs/crawl-status` | Muestra el rastreo más reciente en curso o finalizado, las fichas encontradas y procesadas, páginas visitadas/indexadas/fallidas, límites, enlaces pendientes y los últimos 10 resultados. `completed` significa que terminó la cola de enlaces HTML detectados dentro del alcance; no demuestra que el sitio no tenga secciones ocultas o contenido generado con JavaScript. |
| `GET /documents` | Lista documentos indexados y la URL original cuando la fuente es web. |
| `POST /tickets/create` | Abre un ticket desde `message_id` (ID de una pregunta del usuario) y crea un chat de soporte separado, con título `Ayuda: ...` basado en las preguntas recientes del chat inicial. Copia ahí un extracto cronológico del chat (preguntas y respuestas de SIAE) para que el administrador conozca los intentos previos. Devuelve `ticket_id`, `conversation_id` y `title`. |
| `GET /tickets/user/{user_id}` | Lista tickets del usuario, incluido su estado y el chat asociado. Los finalizados quedan en el historial del usuario. |
| `GET /tickets/admin/{admin_id}` | Bandeja del administrador con tickets pendientes o en proceso asignados a él o sin asignar. No muestra finalizados. |
| `POST /tickets/{ticket_id}/claim` | El administrador toma un ticket; cambia a `en_proceso`. Campo: `admin_id`. |
| `GET /tickets/{ticket_id}/messages` | Lee el chat del ticket. Envía `user_id` o `admin_id` como query parameter. |
| `POST /tickets/{ticket_id}/messages` | Usuario o administrador escribe en el chat. Campos: `content` y uno de `user_id`/`admin_id`. |
| `POST /tickets/{ticket_id}/resolve` | El administrador cierra el ticket; cambia a `finalizado` y sale de su bandeja activa. Campo: `admin_id`. El chat queda en la lista del usuario y puede leerse, pero ya no acepta mensajes. |

Para recorrer el ciclo de tickets de principio a fin sin Groq, documentos ni un servidor activo, ejecuta `python -m tests.test_tickets`. Usa una base SQLite en memoria aislada. Los identificadores de usuario y administrador son provisionales en este prototipo: al integrar autenticación, deben obtenerse de la sesión/token, no de campos que el cliente pueda falsificar. La migración de inicio agrega `tickets.conversation_id` a bases locales existentes para vincular el chat separado.

En modo independiente deja `subsections_id` vacío. Si lo envías, esa subsección debe existir en la tabla `subsections`. Los usuarios de desarrollo se crean automáticamente; esto no sustituye el login ni debe usarse como autenticación real.

### Ejemplo rápido desde PowerShell

Para indexar los documentos de `uploads/` y las fuentes públicas de CUCEI incluidas en el proyecto, inicia la API y ejecuta:

```powershell
python -m scripts.upload_docs
```

Si solo quieres reintentar páginas y subpáginas oficiales sin volver a recorrer `uploads/`, ejecuta `python -m scripts.upload_docs --public-only`. Para procesar únicamente los archivos locales, usa `python -m scripts.upload_docs --local-only`.

El script indexa el organigrama desde el PDF oficial y omite `uploads/organigrama_general-2021.jpeg`. Al procesar el PDF, `replace_file_name` marca el registro de la imagen anterior como `reemplazado`, así deja de participar en búsquedas. Ejecutarlo de nuevo no duplica las mismas fuentes ni genera copias UUID en `uploads/`.

La ingesta por URL admite páginas HTML públicas estáticas, PDF, DOCX e imágenes. Sin embargo, algunas páginas requieren iniciar sesión, bloquean las descargas o generan su contenido únicamente con JavaScript. Si la API no puede acceder al contenido o extraer texto, devuelve un error; en ese caso, puedes exportar la información a un archivo compatible y cargarlo mediante `/docs/upload`. Para descargar archivos de Google Drive automáticamente, habilita el acceso “Cualquier persona con el enlace”. En todos los casos, una fuente vacía o cuyo contenido no se pudo extraer queda registrada como error y no se marca como `vectorizado`.

La extracción HTML conserva el texto de botones, pestañas, diálogos y paneles plegables que ya está presente en el HTML, aunque aparezca oculto hasta una interacción. Sigue sus enlaces internos del mismo dominio según los prefijos y límites configurados. El rastreador no inicia sesión ni ejecuta JavaScript: la información que una aplicación descarga solo después de pulsar un botón requiere un endpoint público exportable o una fuente documental alternativa.

La base añade `metadata_json` a `document_chunks` al iniciar y rellena metadatos básicos para fragmentos existentes sin volver a calcular embeddings. Cada bloque nuevo guarda título y URL de origen, tipo de fuente, categoría, página e índice; HTML y DOCX también guardan la ruta de encabezados y el tipo de bloque. En DOCX se intenta extraer el texto de párrafos, tablas, encabezados, pies, notas, comentarios, hipervínculos, cuadros de texto, gráficos y diagramas; las imágenes rasterizadas incrustadas pasan por OCR de Groq Vision. El formato antiguo `.doc`, los archivos protegidos y el contenido opaco de objetos OLE incrustados no se pueden interpretar de forma general. Las páginas rastreadas guardan además URL padre, raíz y profundidad. Si el contenido declara una fecha de publicación, actualización o vigencia, se conserva y las fuentes con fecha más reciente suben en el ranking cuando coinciden con la pregunta. Los documentos de CUCEI reciben preferencia en este asistente para consultas de alcance ambiguo; si se pide explícitamente una norma general de UdeG, se favorecen las fuentes generales. Si una fuente no declara fechas, no se supone que sea reciente por haber sido cargada hoy. Estos datos enriquecen la coincidencia léxica junto con el texto y el título, y las citas incluyen URL, encabezados, alcance y fechas para localizar el pasaje. Para la oferta académica, `/docs/crawl-academic-catalog` detecta las fichas enlazadas desde cada catálogo y recorre cada programa por separado, con un máximo de 60 páginas y dos niveles de enlaces por ficha. El registro visible en `/docs/crawl-status` muestra cuántos programas se detectaron y procesaron, el detalle por programa, las páginas visitadas, indexadas, fallidas, los límites alcanzados y los rastreos recientes; la terminal también muestra cada URL. `completed` confirma que terminó la cola de enlaces HTML que el extractor logró detectar dentro de esas rutas y límites, pero no que el sitio carezca de páginas ocultas, contenido tras iniciar sesión o enlaces creados por JavaScript. El rastreador no simula clics en imágenes: solo puede seguirlas si son enlaces HTML detectables. La malla ICOM 2021 de Ingeniería en Computación también está configurada como fuente directa; agregar esa URL permite indexarla explícitamente, pero no demuestra por sí sola que se haya recorrido el resto del programa. `upload_docs.py --public-only` y la actualización automática diaria ejecutan esos rastreos. Los contenidos que solo aparecen tras autenticarse o interactuar con una página y no se exponen como enlaces deben revisarse y exportarse manualmente.

Sube un reglamento:

```powershell
curl.exe -X POST "http://127.0.0.1:8080/docs/upload" `
  -F "file=@C:\ruta\reglamento.pdf" `
  -F "title=Reglamento de becas" `
  -F "category=becas"
```

Pregunta al asistente:

```powershell
curl.exe -X POST "http://127.0.0.1:8080/messages/ask" `
  -F "user_id=local-demo-user" `
  -F "question=¿Qué requisitos menciona el reglamento para conservar una beca?"
```

La respuesta incluye `conversation_id`, `answer`, `citations` y `history_used`. El historial solo se aplica cuando la pregunta continúa el tema de la pregunta inmediatamente anterior; sirve para resolver referencias, pero las respuestas factuales siguen necesitando citas de las fuentes indexadas. Guarda el `conversation_id` para continuar el mismo chat. Los saludos solos, preguntas personales breves como «¿quién eres?» o «¿eres feliz?» y la charla casual reciben una respuesta directa sin buscar documentos ni llamar a Groq; también se reconoce `qn` como abreviación de «quién». Si el mismo mensaje contiene una consulta («qué onda wey dónde está CUCEI»), se responde el saludo y se busca la pregunta.

Las expresiones afectuosas frecuentes, como «tqm», «tkm» o «te quiero mucho», reciben un agradecimiento breve que aclara que el asistente no tiene sentimientos. Si vienen junto con una pregunta, se reconoce el gesto y se procesa la consulta por separado. Las solicitudes para generar contenido sexual explícito se rechazan antes de consultar Groq; las dudas educativas o de apoyo sobre salud sexual, consentimiento, anticoncepción, ITS, acoso o violencia pueden pasar a la búsqueda de fuentes oficiales. Si no se encuentra información institucional suficiente, se orienta a los servicios médicos de CUCEI o a solicitar ayuda humana. Estas reglas son filtros por expresiones e intención, no una clasificación infalible; las respuestas sensibles deben revisarse con fuentes oficiales.

El reconocedor cubre expresiones frecuentes de distintas regiones: «pura vida», «mae» y «diay» (Costa Rica); «quiubo», «parce» y «¿qué más?» (Colombia); «epa», «épale», «pana» y «todo fino» (Venezuela); «habla, causa» y «¿qué fue?» (Perú); «qué fue, ñaño» (Ecuador); «qué onda», «qué ondas», «maje» y «chero» (Centroamérica); «qué bolá» y «asere» (Cuba); «klk», «qué lo qué» y «manín» (Caribe); «qué xopa» (Panamá); «wena po», «weón» y «cómo estai» (Chile); «che», «¿qué hacés?», «¿cómo andás?» y «todo piola» (Argentina/Uruguay); «mba'eichapa» y «jallalla» (Paraguay y región andina); «qué onda», «qué rollo», «qué tranza», «qué show», «qué pex» y «quiubo» (México); además de saludos comunes de España. También reconoce algunas aperturas en portugués de Brasil (`oi`, `e aí`, `tudo bem`, `beleza`), inglés y francés/creole caribeño. Normaliza abreviaciones como `q`/`k`/`ke`, `qmas`, `qonda`, `qrollo`, `qshow`, `qtranza`, `qase`/`kase`, `qvuelta`, `qtal`, `klk`, `qpd`, `xq`/`pq`, `tmb`/`tb`, `xfa`/`xfi`, `pls`/`plis`, `ntp`, `dnd`, `toy`, `salu2`, y atajos de chat como `idk`, `tbh`, `btw`, `rn`, `omg`, `fyi`, `imo`, `imho`, `asap`, `lmk`, `brb`, `wsp`, `wyd`, `hbu`, `wbu`, `ntc`, `vdd`, `gpi`, `npi` y `x2`. Tolera letras repetidas y algunos errores tipográficos en saludos; las risas y expresiones afectuosas se quitan solo de los extremos, para conservar la pregunta central. Estas son variantes conocidas, no una lista exhaustiva: los usos cambian según país, edad y contexto. Si un saludo precede una consulta, la consulta debe conservarse para la búsqueda RAG.

### Prueba integral de calidad

Con el entorno virtual activado, la API corriendo en el puerto `8080` y `python -m scripts.upload_docs` ejecutado al menos una vez:

```powershell
python -m tests.test_pipeline --allow-groq-document-context
```

El argumento `--allow-groq-document-context` confirma que las consultas pueden enviar a Groq fragmentos recuperados de la base local. El script verifica además que Swagger no exponga `top_k` porque la API usa seis fragmentos de forma fija. Comprueba el saludo, orientación académica, contacto y enlace del directorio, los cuatro departamentos y el enlace de Organización/Organigrama, el seguimiento de tema, el cambio de tema, las fuentes de becas, la creación de un ticket y el historial persistido. Si cualquiera de esas condiciones falla, termina con código distinto de cero y muestra la comprobación que falló; un HTTP 200 por sí solo no cuenta como prueba exitosa.

La prueba crea una conversación y un ticket de demostración en la base local. Se puede volver a ejecutar; usa el usuario `test_student_eval_002`.

### Variantes de pruebas por escenario

Con Uvicorn activo y las fuentes cargadas, puedes ejecutar escenarios independientes. Cada consulta RAG exige la opción de autorización para enviar fragmentos locales a Groq:

```powershell
python -m tests.test_greeting_and_question --allow-groq-document-context
python -m tests.test_topic_switching --allow-groq-document-context
python -m tests.test_cucei_map --allow-groq-document-context
python -m tests.test_varied_queries --allow-groq-document-context
python -m tests.test_vision "C:\ruta\a\una-imagen.png" --allow-groq-image-content
```

`test_greeting_and_question.py` prueba un saludo simple, charla breve, una pregunta de ubicación tras el saludo y el ciclo básico de tickets; también verifica el enlace de Ubicación CUCEI. `test_topic_switching.py` verifica que el enlace de ubicación sobreviva a una pregunta de seguimiento y que no se arrastre al cambiar a orientación académica. `test_cucei_map.py` comprueba la indexación, cita y enlace directo del mapa. `test_varied_queries.py` valida preguntas formales, coloquiales, abreviadas, sin acentos, con saludo y de varias partes; cubre idiomas, becas, bolsa de trabajo, prácticas, servicio social, atención médica, bibliotecas, licenciaturas, ubicación y misión. También comprueba enlaces de fuentes, la regla operativa de dos reportes de Servicio Social en una pregunta inicial y su seguimiento («¿y cuál es el tiempo mínimo y máximo?»), además de la ruta del portal de Control Escolar. Antes de consultar la API, los scripts compartidos confirman que Swagger ya no exponga el parámetro `top_k` y señalan fuentes que falten o no estén vectorizadas.

`test_vision.py` comprueba OCR de una imagen local seleccionada por quien ejecuta el script. Como envía el contenido de esa imagen a Groq Vision, requiere `--allow-groq-image-content`.

Si Groq responde con un límite de solicitudes o tokens por minuto durante `test_varied_queries.py`, puedes espaciar sus consultas desde PowerShell: `$env:SIAE_TEST_REQUEST_DELAY_SECONDS='22'`. El valor indica los segundos de espera antes de cada pregunta.

Las pruebas crean conversaciones de demostración; la primera también crea un ticket pendiente. Puedes indicar otra API o un usuario de prueba con `--base-url` y `--user-id`.

## Estructura de archivos

### Aplicación (`app/`)

- `main.py`: crea la API FastAPI y define sus rutas para preguntas, conversaciones, documentos y tickets.
- `database.py`: configura la conexión a SQLite o PostgreSQL y las sesiones de base de datos.
- `models.py`: define los modelos de datos usados por el backend RAG.
- `embeddings.py`: carga el modelo que convierte texto en vectores para la búsqueda semántica.
- `ingestion.py`: extrae texto de documentos, procesa OCR, divide el contenido en fragmentos y guarda sus vectores.
- `rag_engine.py`: recupera fragmentos relevantes y genera respuestas con citas.
- `web_scraper.py`: rastrea páginas públicas y procesa el contenido que puede extraer.
- `__init__.py`: marca `app` como paquete importable de Python.

### Pruebas (`tests/`)

- `test_pipeline.py`: prueba el recorrido general de preguntas, respuestas y citas.
- `test_tickets.py`: comprueba el ciclo del ticket, desde su creación hasta su cierre.
- `test_conversation_handling.py`: prueba saludos, charla casual, ambigüedad, seguridad y otros casos conversacionales.
- `test_greeting_and_question.py`: verifica saludos combinados con consultas.
- `test_topic_switching.py`: comprueba preguntas de seguimiento y cambios de tema.
- `test_cucei_map.py`: comprueba la fuente y el enlace del mapa de CUCEI.
- `test_varied_queries.py`: prueba temas y preguntas con distintos estilos de lenguaje.
- `test_vision.py`: prueba la lectura visual de una imagen.
- `pipeline_test_support.py`: contiene utilidades compartidas por las pruebas.
- `__init__.py`: permite ejecutar las pruebas con `python -m tests...`.

### Herramientas (`scripts/`)

- `upload_docs.py`: envía documentos locales y fuentes web a la API para indexarlos.
- `retry_groq_failures.py`: vuelve a intentar fuentes que fallaron por límites de Groq.
- `__init__.py`: permite ejecutar estas herramientas con `python -m scripts...`.

### Configuración y documentos

- `requirements.txt`: lista las dependencias de Python.
- `.env.example`: plantilla de variables de configuración. Crea un `.env` local a partir de ella y agrega ahí tus claves; el `.env` privado no se incluye en el repositorio.
- `.gitignore`: evita que Git agregue secretos, bases de datos locales, cachés y archivos de `uploads/`.
- `README.md`: contiene instrucciones de instalación, ejecución, ingesta y pruebas.
- `.gitkeep`: marcador vacío que ya estaba en la carpeta destino para que Git conserve esa carpeta.
- `uploads/`: contiene los documentos originales que se pueden indexar; tenerlos aquí no significa que ya estén indexados. Incluye reglamentos de conducta, ética, organización, evaluación, faltas, planes de estudio, posgrado, ingreso, modalidad virtual, reconocimientos, validez de estudios, titulación, protección contra el tabaco, becas, defensoría y servicio social; materiales de liberación de prácticas; dos versiones del protocolo de violencia de género; el organigrama en imagen; y tutoriales de oferta de verano, prerregistro de materias y registro del servicio social.
- `siae_local.db`: SQLite local que la aplicación puede crear al iniciarse; se ignora en Git y no se copió desde el backend de origen.

## Limitaciones actuales

- El asistente solo responde sobre documentos y páginas que hayas indexado.
- La búsqueda carga vectores a memoria y está pensada para un corpus local pequeño, no para millones de fragmentos.
- Mientras la API esté ejecutándose, las fuentes públicas configuradas se revisan al iniciar y cada 24 horas. Si cambia el contenido, se crean fragmentos y embeddings nuevos y la versión anterior deja de participar en la búsqueda. Si la API estuvo apagada, la revisión ocurre al volver a iniciarla. Para actualizar manualmente en ese momento ejecuta `python -m scripts.upload_docs --public-only` con la API activa. Puedes desactivar el ciclo con `SIAE_AUTO_REFRESH_SOURCES=false`.
- No hay login, gestión de permisos, dashboard, notificaciones ni integración con Control Escolar.
- No hay todavía modelo entrenado para clasificar tickets ni historial suficiente para predicción de demanda.
- El OCR de imágenes y PDFs escaneados depende de Groq; los PDFs digitales se extraen localmente.
- Cambiar el modelo de embeddings requiere volver a indexar los documentos para que todos los vectores tengan el mismo espacio.

## Solución de problemas

- **`Form data requires "python-multipart"`:** activa el entorno virtual e instala `pip install -r requirements.txt`.
- **Falla al descargar el modelo de embeddings:** revisa la conexión a internet y vuelve a iniciar. El primer inicio necesita descargar el modelo.
- **`Falta GROQ_API_KEY`:** agrega una key válida al `.env` para preguntas que necesiten LLM o para OCR.
- **Error al leer un PDF escaneado:** confirma que instalaste `requirements.txt` en el entorno virtual activo y que `GROQ_API_KEY` está configurada.
- **La API reutiliza un esquema viejo:** reiníciala para que agregue `metadata_json`; crea una copia de seguridad antes de usar una base de desarrollo existente.
- **La respuesta no encuentra información:** confirma que `/documents` muestre el documento como `vectorizado`, usa una pregunta sobre su contenido y revisa `RAG_MIN_SCORE`.
- **`No such table` o fallo de clave foránea:** confirma que `DATABASE_URL` apunta a una base nueva para este esquema; inicia de nuevo para que se creen las tablas locales.

## Manejo de conversaciones atípicas

El asistente limita las respuestas a temas de CUCEI, mantiene un tono respetuoso ante insultos o frustración, ignora peticiones de inventar datos o revelar instrucciones internas y comprueba las premisas contra las fuentes. Si una referencia como «eso» no se entiende con el turno inmediatamente anterior, pide aclaración. Las preguntas coordinadas se separan para buscar evidencia para cada parte, hasta cuatro por mensaje. Los cambios de tema no arrastran contexto antiguo. Las preguntas repetidas reciben una explicación reformulada.

Si el mensaje parece incluir una contraseña, NIP, token o código de acceso, el backend evita enviarlo a Groq y guarda una nota segura en el historial en lugar del texto original. Evita compartir también otros datos personales en el chat.

Para consultas sobre violencia de género, se priorizan los fragmentos del Protocolo de la UdeG y se orienta a la persona Primer Contacto de su Centro; si no hay uno disponible, el protocolo indica escribir a `igualdad@udg.mx`. Ante señales de peligro inmediato, el asistente recomienda buscar un lugar seguro y contactar los servicios de emergencia locales. Los tickets no se crean automáticamente al detectar frustración: la persona debe usar la función de soporte de la aplicación para abrir uno.

Para que el nuevo archivo `uploads/Protocolo violencia de genero.pdf` participe con sus fragmentos y citas, debe estar vectorizado en la base local. Después de agregarlo, ejecuta `python -m scripts.upload_docs --local-only` con la API activa.
