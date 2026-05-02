import asyncio
import time
from agents.planner import PlannerAgent
from agents.coder import CoderAgent
from agents.reviewer import ReviewerAgent
from agents.memory import MemoryAgent
from agents.analyzer import AnalyzerAgent
from core.auto_fix import AutoFixSystem
from core.tracer import Tracer
from core import cache, tokens

SCAN_KEYWORDS = {"scan", "audit", "analyze", "check", "security", "review"}


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
        self.analyzer = AnalyzerAgent(config)
        self.auto_fix = AutoFixSystem(config)
        self.tracer = Tracer(config)

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
            return {**cached, "cached": True}

        # Span Coder
        span = self.tracer.span(trace_id, "Coder", project_id, task.get("id"))
        try:
            diff = await self.coder.generate(task, context)
            span.set_tokens(
                tokens.estimate("".join(context)),
                tokens.estimate(diff),
            )
            await span.finish("success")
        except Exception as e:
            await span.finish("error", str(e))
            raise

        # Span Reviewer (optionnel)
        if not self._should_skip_reviewer(task):
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

        await self.tracer.trace_start(trace_id, project_id, query)

        # Span Planner
        span_p = self.tracer.span(trace_id, "Planner", project_id)
        tasks = await asyncio.to_thread(self.planner.plan, query)
        span_p.set_tokens(tokens.estimate(query), tokens.estimate(str(tasks)))
        await span_p.finish("success")

        independent, dependent = self._split_by_deps(tasks)
        results = []

        if independent:
            parallel_results = await asyncio.gather(
                *[self._process_task(t, project_path, trace_id) for t in independent]
            )
            results.extend(parallel_results)

        for task in dependent:
            results.append(await self._process_task(task, project_path, trace_id))

        stats = self._compute_stats(results)
        duration_ms = int((time.time() - start) * 1000)
        await self.tracer.trace_end(trace_id, project_id, stats["estimated_tokens_out"], duration_ms)

        return {
            "trace_id": trace_id,
            "mode": "dev",
            "tasks": tasks,
            "results": results,
            "stats": stats,
        }

    async def scan_async(self, project_path: str, auto_fix: bool = False) -> dict:
        from tools.file_selector import select_critical_files

        project_id = project_path.replace("\\", "/").split("/")[-1]
        trace_id = self.tracer.new_trace(project_path)
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

    def _split_by_deps(self, tasks):
        return (
            [t for t in tasks if not t.get("depends_on")],
            [t for t in tasks if t.get("depends_on")],
        )

    def _compute_stats(self, results):
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
