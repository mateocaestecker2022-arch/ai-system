from sentence_transformers import SentenceTransformer
import numpy as np

_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        # Léger (80MB), rapide, bon pour le code
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_texts(texts: list[str]) -> np.ndarray:
    model = get_model()
    return model.encode(texts, convert_to_numpy=True, show_progress_bar=False)


def embed_query(query: str) -> np.ndarray:
    return embed_texts([query])[0]
