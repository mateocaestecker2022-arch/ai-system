import asyncio
import time
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.memory import MemoryAgent
from agents.analyzer import AnalyzerAgent
from core.auto_fix import AutoFixSystem
from core.task_optimizer import TaskGraphOptimizer
from core.tracer import Tracer
from core.logger import Logger
from core import cache, tokens

SCAN_KEYWORDS = {"scan", "audit", "analyze", "check", "security", "review"}


class Orchestrator:
    """
    Leader V2 production-ready — logique Python pure, zéro LLM ici.
    """

    def __init__(self, config):
        self.config = config
        self.planner = PlannerAgent(config)
        self.optimizer = TaskGraphOptimizer()
        self.coder = CoderAgent(config)
        self.reviewer = ReviewerAgent(config)
        self.memory = MemoryAgent(config)
        self.analyzer = AnalyzerAgent(config)
        self.auto_fix = AutoFixSystem(config)
        self.tracer = Tracer(config)
        self.logger = Logger()

    def _is_scan_query(self, query: str) -> bool:
        return any(k in query.lower() for k in SCAN_KEYWORDS)

    def _should_skip_reviewer(self, task: dict) -> bool:
        return task.get("type") in self.config.SIMPLE_TASK_TYPES

    async def _process_task(self, task: dict, project_path: str, trace_id: str) -> dict:
        project_id = project_path.replace("\\", "/").split("/")[-1]

        context = await asyncio.to_thread(
            self.memory.get_context_for_task, project_path, task
        )

        cached = cache.get(task["description"], context)
        if cached:
            self.logger.log({"event": "cache_hit", "trace_id": trace_id, "task_id": task.get("id")})
            return {**cached, "cached": True}

        # Coder
        span = self.tracer.span(trace_id, "Coder", project_id, task.get("id"))
        try:
            diff = await self.coder.generate(task, context)
            span.set_tokens(tokens.estimate("".join(context)), tokens.estimate(diff))
            await span.finish("success")
        except Exception as e:
            await span.finish("error", str(e))
            raise

        # Reviewer (smart skip)
        if self._should_skip_reviewer(task):
            self.logger.log({"event": "reviewer_skip", "trace_id": trace_id, "task_id": task.get("id"), "reason": task.get("type")})
        else:
            span_r = self.tracer.span(trace_id, "Reviewer", project_id, task.get("id"))
            try:
                diff = await self.reviewer.review(diff)
                span_r.set_tokens(tokens.estimate(diff), tokens.estimate(diff))
                await span_r.finish("success")
            except Exception as e:
                await span_r.finish("error", str(e))

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
        if self._is_scan_query(query):
            return await self.scan_async(project_path, auto_fix="fix" in query.lower())

        project_id = project_path.replace("\\", "/").split("/")[-1]
        trace_id = self.tracer.new_trace(project_path)
        start = time.time()

        self.logger.log({"event": "start", "trace_id": trace_id, "query": query})
        await self.tracer.trace_start(trace_id, project_id, query)

        # Planner
        span_p = self.tracer.span(trace_id, "Planner", project_id)
        raw_tasks = await asyncio.to_thread(self.planner.plan, query)
        span_p.set_tokens(tokens.estimate(query), tokens.estimate(str(raw_tasks)))
        await span_p.finish("success")

        # Optimize task graph
        optimized_tasks = self.optimizer.optimize(raw_tasks)
        opt_stats = self.optimizer.stats(len(raw_tasks), len(optimized_tasks))
        self.logger.log({"event": "optimizer", "trace_id": trace_id, **opt_stats})

        # Execute — parallèle pour indépendants, séquentiel pour dépendants
        independent = [t for t in optimized_tasks if not t.get("depends_on")]
        dependent = [t for t in optimized_tasks if t.get("depends_on")]
        self.logger.log({"event": "task_split", "trace_id": trace_id, "parallel": len(independent), "sequential": len(dependent)})
        results = []

        if independent:
            parallel_results = await asyncio.gather(
                *[self._process_task(t, project_path, trace_id) for t in independent]
            )
            results.extend(parallel_results)

        for task in dependent:
            results.append(await self._process_task(task, project_path, trace_id))

        stats = self._compute_stats(results)
        stats["optimizer"] = opt_stats
        duration_ms = int((time.time() - start) * 1000)

        self.logger.log({"event": "end", "trace_id": trace_id, "tasks": len(optimized_tasks), "duration_ms": duration_ms})
        await self.tracer.trace_end(trace_id, project_id, stats["estimated_tokens_out"], duration_ms)

        return {
            "trace_id": trace_id,
            "mode": "dev",
            "tasks": optimized_tasks,
            "results": results,
            "stats": stats,
        }

    async def scan_async(self, project_path: str, auto_fix: bool = False) -> dict:
        from tools.file_selector import select_critical_files

        project_id = project_path.replace("\\", "/").split("/")[-1]
        trace_id = self.tracer.new_trace(project_path)

        self.logger.log({"event": "scan_start", "trace_id": trace_id, "project": project_path})
        await self.tracer.trace_start(trace_id, project_id, "scan")

        files = select_critical_files(project_path, max_files=self.config.MAX_CHUNKS)
        if not files:
            return {"trace_id": trace_id, "mode": "scan", "issues": [], "fixes": [], "files_scanned": 0}

        span_a = self.tracer.span(trace_id, "Analyzer", project_id)
        issues = await self.analyzer.analyze_files(files)
        span_a.set_tokens(
            sum(tokens.estimate(c) for c in files.values()),
            tokens.estimate(str(issues)),
        )
        await span_a.finish("success")

        fixes = []
        if auto_fix and issues:
            context = "\n---\n".join(f"# {p}\n{c[:800]}" for p, c in files.items())
            fixes = await self.auto_fix.fix_issues(issues, context)

        await self.tracer.trace_end(trace_id, project_id, tokens.estimate(str(issues)), 0)
        self.logger.log({"event": "scan_end", "trace_id": trace_id, "issues": len(issues)})

        return {
            "trace_id": trace_id,
            "mode": "scan",
            "files_scanned": len(files),
            "issues": issues,
            "fixes": fixes,
            "stats": {
                "total_issues": len(issues),
                "high": sum(1 for i in issues if i.get("severity") == "high"),
                "medium": sum(1 for i in issues if i.get("severity") == "medium"),
                "low": sum(1 for i in issues if i.get("severity") == "low"),
                "auto_fixes": len(fixes),
            },
        }

    def _compute_stats(self, results: list[dict]) -> dict:
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
