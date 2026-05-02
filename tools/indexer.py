import os
import json
import numpy as np
import faiss
from pathlib import Path
from tools.embedder import embed_texts


SUPPORTED = (".py", ".js", ".ts", ".go", ".java", ".rs", ".tsx", ".jsx")
SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".ai"}


def index_project(project_path: str, chunk_size: int = 1000) -> list[dict]:
    chunks = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if not file.endswith(SUPPORTED):
                continue
            path = Path(root) / file
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for i in range(0, len(content), chunk_size):
                    chunks.append({
                        "path": str(path),
                        "chunk_index": i // chunk_size,
                        "content": content[i:i + chunk_size],
                    })
            except Exception:
                continue
    return chunks


def build_and_save(project_path: str, chunk_size: int = 1000):
    """Indexe le projet, génère les embeddings, sauvegarde tout dans .ai/"""
    ai_dir = Path(project_path) / ".ai"
    ai_dir.mkdir(exist_ok=True)

    chunks = index_project(project_path, chunk_size)
    if not chunks:
        return chunks

    texts = [c["content"] for c in chunks]
    vectors = embed_texts(texts).astype("float32")

    # Normalisation L2 pour cosine similarity via IndexFlatIP
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    # serialize_index évite les problèmes de chemins avec accents/espaces sur Windows
    (ai_dir / "embeddings.faiss").write_bytes(faiss.serialize_index(index))
    (ai_dir / "chunks.json").write_text(json.dumps(chunks, indent=2), encoding="utf-8")

    return chunks


def load_index(project_path: str):
    ai_dir = Path(project_path) / ".ai"
    chunks_file = ai_dir / "chunks.json"
    faiss_file = ai_dir / "embeddings.faiss"

    if not chunks_file.exists() or not faiss_file.exists():
        return None, None

    chunks = json.loads(chunks_file.read_text(encoding="utf-8"))
    index = faiss.deserialize_index(np.frombuffer(faiss_file.read_bytes(), dtype=np.uint8))
    return chunks, index


def is_index_stale(project_path: str) -> bool:
    """Vérifie si des fichiers ont été modifiés depuis le dernier index."""
    faiss_file = Path(project_path) / ".ai" / "embeddings.faiss"
    if not faiss_file.exists():
        return True

    index_mtime = faiss_file.stat().st_mtime
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if file.endswith(SUPPORTED):
                if (Path(root) / file).stat().st_mtime > index_mtime:
                    return True
    return False
