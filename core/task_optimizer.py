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
        if a.get("target") in (None, "unknown") or b.get("target") in (None, "unknown"):
            return False
        if a.get("type") != b.get("type"):
            return False
        score = self._jaccard(a["description"], b["description"])
        return score >= 0.85 or a["target"] == b["target"]

    @staticmethod
    def _jaccard(text_a: str, text_b: str) -> float:
        a = set(text_a.lower().split())
        b = set(text_b.lower().split())
        if not a or not b:
            return 0.0
        return len(a & b) / len(a | b)

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
