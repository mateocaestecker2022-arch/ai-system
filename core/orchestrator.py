import asyncio
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.memory import MemoryAgent


class Orchestrator:
    def __init__(self, config):
        self.config = config
        self.planner = PlannerAgent(config)
        self.coder = CoderAgent(config)
        self.reviewer = ReviewerAgent(config)
        self.memory = MemoryAgent(config)

    async def run_async(self, query: str, project_path: str) -> dict:
        # Étape 1 : Planner + Memory en parallèle
        # Memory utilise la query brute pendant que Planner travaille
        tasks_future = asyncio.create_task(
            asyncio.to_thread(self.planner.plan, query)
        )
        context_raw_future = asyncio.create_task(
            asyncio.to_thread(self.memory.get_context, project_path, [
                {"description": query, "target": "unknown", "type": "modify", "depends_on": []}
            ])
        )

        tasks, context_raw = await asyncio.gather(tasks_future, context_raw_future)

        # Étape 2 : Affiner le contexte avec les vraies tâches du Planner
        context = await asyncio.to_thread(self.memory.get_context, project_path, tasks)

        # Étape 3 : Coder (dépend des 2 précédents)
        code = await self.coder.generate(tasks, context)

        # Étape 4 : Reviewer
        reviewed = await self.reviewer.review(code)

        return {
            "tasks": tasks,
            "context_files": len(context),
            "result": reviewed,
        }

    def run(self, query: str, project_path: str) -> dict:
        return asyncio.run(self.run_async(query, project_path))
