import asyncio
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.memory import MemoryAgent
from core import cache, tokens


class Orchestrator:
    """
    Leader V2 — logique Python pure, jamais de LLM ici.
    Pilote les agents avec un contexte minimal et contrôlé.
    """

    def __init__(self, config):
        self.config = config
        self.planner = PlannerAgent(config)
        self.coder = CoderAgent(config)
        self.reviewer = ReviewerAgent(config)
        self.memory = MemoryAgent(config)

    def _should_skip_reviewer(self, task: dict) -> bool:
        return task.get("type") in self.config.SIMPLE_TASK_TYPES

    async def _process_task(self, task: dict, project_path: str) -> dict:
        # Memory : contexte minimal pour cette tâche uniquement
        context = await asyncio.to_thread(
            self.memory.get_context_for_task, project_path, task
        )

        # Cache hit ?
        cached = cache.get(task["description"], context)
        if cached:
            return {**cached, "cached": True}

        # Coder
        diff = await self.coder.generate(task, context)

        # Reviewer : optionnel selon la complexité
        if not self._should_skip_reviewer(task):
            diff = await self.reviewer.review(diff)

        result = {
            "task_id": task["id"],
            "task": task["description"],
            "target": task.get("target"),
            "diff": diff,
            "cached": False,
            "reviewer_skipped": self._should_skip_reviewer(task),
        }

        cache.set(task["description"], context, result)
        return result

    async def run_async(self, query: str, project_path: str) -> dict:
        # Planner reçoit UNIQUEMENT la query — aucun code, aucun contexte
        tasks = await asyncio.to_thread(self.planner.plan, query)

        # Traitement des tâches : parallèle si pas de dépendances
        independent, dependent = self._split_by_deps(tasks)

        results = []

        # Tâches indépendantes en parallèle
        if independent:
            parallel_results = await asyncio.gather(
                *[self._process_task(t, project_path) for t in independent]
            )
            results.extend(parallel_results)

        # Tâches dépendantes en séquence
        for task in dependent:
            results.append(await self._process_task(task, project_path))

        token_stats = self._compute_stats(results)

        return {
            "tasks": tasks,
            "results": results,
            "stats": token_stats,
        }

    def _split_by_deps(self, tasks: list[dict]) -> tuple[list, list]:
        independent = [t for t in tasks if not t.get("depends_on")]
        dependent = [t for t in tasks if t.get("depends_on")]
        return independent, dependent

    def _compute_stats(self, results: list[dict]) -> dict:
        total_diff_chars = sum(len(r.get("diff", "")) for r in results)
        cached = sum(1 for r in results if r.get("cached"))
        skipped = sum(1 for r in results if r.get("reviewer_skipped"))
        return {
            "total_tasks": len(results),
            "cached": cached,
            "reviewer_skipped": skipped,
            "estimated_tokens_out": tokens.estimate(
                "".join(r.get("diff", "") for r in results)
            ),
        }

    def run(self, query: str, project_path: str) -> dict:
        return asyncio.run(self.run_async(query, project_path))
