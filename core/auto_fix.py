import asyncio
from agents.coder import CoderAgent
from core.tokens import compress

AUTOFIX_PROMPT = """Fix this issue with a minimal code change.

Type: {type}
Severity: {severity}
Location: {location} ({line_hint})
Description: {description}
Suggested fix: {fix}

Context:
{context}

Return ONLY a diff. No explanation.
- removed line
+ added line
"""


class AutoFixSystem:
    def __init__(self, config):
        self.coder = CoderAgent(config)
        self.config = config

    async def _fix_issue(self, issue: dict, context: str) -> dict:
        context_compressed = compress(context, self.config.MAX_CONTEXT_TOKENS)

        prompt = AUTOFIX_PROMPT.format(
            type=issue.get("type", "bug"),
            severity=issue.get("severity", "medium"),
            location=issue.get("location", "unknown"),
            line_hint=issue.get("line_hint", ""),
            description=issue.get("description", ""),
            fix=issue.get("fix", ""),
            context=context_compressed,
        )

        # On passe par call_llm_async directement — le prompt est déjà construit
        from core.llm import call_llm_async
        diff = await call_llm_async(prompt, self.config)

        return {
            "issue": issue,
            "diff": compress(diff, self.config.MAX_DIFF_SIZE),
        }

    async def fix_issues(
        self,
        issues: list[dict],
        context: str,
        max_fixes: int = 5,
    ) -> list[dict]:
        # Priorité aux high severity, limite stricte
        prioritized = sorted(
            issues,
            key=lambda x: {"high": 0, "medium": 1, "low": 2}.get(x.get("severity", "low"), 2),
        )[:max_fixes]

        return await asyncio.gather(
            *[self._fix_issue(issue, context) for issue in prioritized]
        )
