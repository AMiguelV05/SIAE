"""Modelo de vectores de oraciones, cargado bajo demanda para la ingesta y la búsqueda."""

import os
from functools import lru_cache

from sentence_transformers import SentenceTransformer


# Modelo multilingüe que convierte textos en vectores para compararlos por significado.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    # Reutiliza una sola instancia para evitar volver a cargar el modelo en cada consulta.
    model_name = os.getenv("EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    device = os.getenv("EMBEDDING_DEVICE")
    return SentenceTransformer(model_name, device=device or None)


def embed_documents(texts: list[str]) -> list[list[float]]:
    # Vectoriza los fragmentos de documentos que se guardarán para la búsqueda.
    if not texts:
        return []
    # La normalización permite comparar vectores con el producto punto como similitud coseno.
    vectors = get_embedding_model().encode_document(
        texts,
        batch_size=int(os.getenv("EMBEDDING_BATCH_SIZE", "32")),
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    # Usa el mismo modelo para que la pregunta pueda compararse con los documentos.
    vector = get_embedding_model().encode_query(
        text,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    return vector.tolist()
