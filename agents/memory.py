from tools.search import search_relevant_chunks
from core.tokens import truncate_to_budget


class MemoryAgent:
    def __init__(self, config):
        self.config = config

    def get_context_for_task(self, project_path: str, task: dict) -> list[str]:
        """Retourne le contexte minimal pour UNE tâche."""
        query = f"{task['description']} {task.get('target', '')}"
        chunks = search_relevant_chunks(
            project_path,
            query,
            max_results=self.config.MAX_CHUNKS,
        )
        # Applique le budget token strict
        return truncate_to_budget(chunks, self.config.MAX_CONTEXT_TOKENS)

    def get_context(self, project_path: str, tasks: list[dict]) -> list[str]:
        """Compatibilité — agrège le contexte pour plusieurs tâches."""
        query = " ".join(
            f"{t.get('description', '')} {t.get('target', '')}" for t in tasks
        )
        chunks = search_relevant_chunks(
            project_path,
            query,
            max_results=self.config.MAX_CHUNKS,
        )
        return truncate_to_budget(chunks, self.config.MAX_CONTEXT_TOKENS)
