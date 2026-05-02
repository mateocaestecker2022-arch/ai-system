import json
import re
import hashlib
from core.llm import call_llm_async
from core.tokens import compress

ANALYZER_PROMPT = """You are a senior security auditor and software engineer.

Analyze this code for:
- Bugs (logic errors, null refs, race conditions)
- Security issues — focus on:
  - Injection (SQL, command, LDAP)
  - Authentication & session flaws
  - Sensitive data exposure
  - Broken access control
  - Security misconfiguration
  - XSS / CSRF
- Performance issues (N+1, blocking calls, memory leaks)

Return ONLY valid JSON array. No markdown, no explanation.

[
  {{
    "type": "bug | security | perf",
    "severity": "low | medium | high",
    "description": "...",
    "location": "{file_path}",
    "line_hint": "function or line reference",
    "fix": "short fix suggestion (1-2 lines max)"
  }}
]

If no issues found, return: []

Code ({file_path}):
{content}
"""


class AnalyzerAgent:
    def __init__(self, config):
        self.config = config
        self._cache: dict[str, list[dict]] = {}

    def _hash(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    async def analyze_file(self, file_path: str, content: str) -> list[dict]:
        file_hash = self._hash(content)

        if file_hash in self._cache:
            return self._cache[file_hash]

        # Chunk limité pour ne pas exploser les tokens
        truncated = compress(content, 1500)

        prompt = ANALYZER_PROMPT.format(file_path=file_path, content=truncated)
        response = await call_llm_async(prompt, self.config)

        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()
        try:
            issues = json.loads(clean)
        except json.JSONDecodeError:
            issues = []

        self._cache[file_hash] = issues
        return issues

    async def analyze_files(self, files: dict[str, str]) -> list[dict]:
        """Analyse plusieurs fichiers en parallèle."""
        import asyncio
        results = await asyncio.gather(
            *[self.analyze_file(path, content) for path, content in files.items()]
        )
        all_issues = []
        for issues in results:
            all_issues.extend(issues)

        # Tri par sévérité
        severity_order = {"high": 0, "medium": 1, "low": 2}
        all_issues.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 2))
        return all_issues
