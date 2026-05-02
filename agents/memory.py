from tools.search import search_relevant_chunks


class MemoryAgent:
    def __init__(self, config):
        self.config = config

    def get_context(self, project_path: str, tasks: list[dict]) -> list[str]:
        query = " ".join(t["description"] for t in tasks)
        return search_relevant_chunks(
            project_path,
            query,
            max_results=self.config.MAX_CONTEXT_FILES,
        )
