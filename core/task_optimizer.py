class TaskGraphOptimizer:
    """
    Optimise le graphe de tâches avant exécution :
    1. Fusionne les tâches similaires (même target + même type)
    2. Sépare parallèles / séquentielles
    """

    def optimize(self, tasks: list[dict]) -> list[dict]:
        tasks = self._merge_similar(tasks)
        parallel, sequential = self._split(tasks)
        return parallel + sequential

    def _merge_similar(self, tasks: list[dict]) -> list[dict]:
        merged: list[dict] = []
        for task in tasks:
            match = next(
                (m for m in merged if self._similar(task, m)),
                None,
            )
            if match:
                match["description"] += " | " + task["description"]
                # Conserve l'id le plus bas
            else:
                merged.append(dict(task))
        return merged

    def _similar(self, a: dict, b: dict) -> bool:
        return (
            a.get("target") == b.get("target")
            and a.get("type") == b.get("type")
            and a.get("target") not in (None, "unknown")
        )

    def _split(self, tasks: list[dict]) -> tuple[list[dict], list[dict]]:
        parallel = [t for t in tasks if not t.get("depends_on")]
        sequential = [t for t in tasks if t.get("depends_on")]
        return parallel, sequential

    def stats(self, before: int, after: int) -> dict:
        saved = before - after
        return {
            "tasks_before": before,
            "tasks_after": after,
            "merged": saved,
            "llm_calls_saved": saved,
        }
