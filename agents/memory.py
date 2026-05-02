import numpy as np
from tools.indexer import build_and_save, load_index, is_index_stale
from tools.embedder import embed_query
from core.tokens import truncate_to_budget
import faiss


class MemoryAgent:
    def __init__(self, config):
        self.config = config

    def get_context_for_task(self, project_path: str, task: dict) -> list[str]:
        query = f"{task['description']} {task.get('target', '')}"
        chunks = self._search_and_rerank(project_path, query)
        return truncate_to_budget(chunks, self.config.MAX_CONTEXT_TOKENS)

    def get_context(self, project_path: str, tasks: list[dict]) -> list[str]:
        query = " ".join(
            f"{t.get('description', '')} {t.get('target', '')}" for t in tasks
        )
        chunks = self._search_and_rerank(project_path, query)
        return truncate_to_budget(chunks, self.config.MAX_CONTEXT_TOKENS)

    def _search_and_rerank(self, project_path: str, query: str) -> list[str]:
        if is_index_stale(project_path):
            build_and_save(project_path)

        chunks, index = load_index(project_path)
        if not chunks or index is None or index.ntotal == 0:
            return []

        # 1. FAISS top-30 candidates
        vector = embed_query(query).astype("float32").reshape(1, -1)
        faiss.normalize_L2(vector)
        k = min(30, index.ntotal)
        _, indices = index.search(vector, k)
        candidates = [chunks[i] for i in indices[0] if i != -1]

        # 2. Rerank par keyword overlap (léger, 0 token)
        query_terms = set(query.lower().split())
        ranked = sorted(
            candidates,
            key=lambda c: len(query_terms & set(c["content"].lower().split())),
            reverse=True,
        )

        # 3. Top 5 max, compressé à 800 chars chacun
        top = ranked[: self.config.MAX_CHUNKS]
        return [
            f"# {c['path']}\n{c['content'][:800]}"
            for c in top
        ]
