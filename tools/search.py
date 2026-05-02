import numpy as np
import faiss
from tools.indexer import build_and_save, load_index, is_index_stale
from tools.embedder import embed_query


def search_relevant_chunks(
    project_path: str,
    query: str,
    max_results: int = 5,
) -> list[str]:
    # Rebuild si index absent ou obsolète
    if is_index_stale(project_path):
        print(f"[memory] Indexing {project_path}...")
        build_and_save(project_path)

    chunks, index = load_index(project_path)
    if not chunks or index is None or index.ntotal == 0:
        return []

    vector = embed_query(query).astype("float32").reshape(1, -1)
    faiss.normalize_L2(vector)

    k = min(max_results, index.ntotal)
    scores, indices = index.search(vector, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        chunk = chunks[idx]
        results.append(f"# {chunk['path']} (score: {score:.3f})\n{chunk['content']}")

    return results
