import json
import re
from core.llm import call_llm


PLAN_PROMPT = """You are a senior software architect. Analyze the request and decompose it into precise, actionable tasks.

Rules:
- Each task must target a specific file, function, or module
- Tasks must be ordered by dependency (task 2 may depend on task 1)
- Maximum 6 tasks
- Be specific: "add input validation to login() in auth.py" not "fix auth"

Request: {query}

Return ONLY valid JSON. No markdown, no explanation.

{{
  "tasks": [
    {{
      "id": 1,
      "description": "...",
      "target": "file.py or module name",
      "type": "create|modify|delete|refactor",
      "depends_on": []
    }}
  ],
  "summary": "one-line summary of what will be done"
}}"""


class PlannerAgent:
    def __init__(self, config):
        self.config = config

    def plan(self, query: str) -> list[dict]:
        response = call_llm(PLAN_PROMPT.format(query=query), self.config)

        # Strip markdown code blocks if model wraps in ```json
        clean = re.sub(r"```(?:json)?\s*|\s*```", "", response).strip()

        try:
            data = json.loads(clean)
            tasks = data.get("tasks", [])
            if tasks:
                return tasks
        except (json.JSONDecodeError, AttributeError):
            pass

        # Fallback : retourne la query comme tâche unique
        return [{"id": 1, "description": query, "target": "unknown", "type": "modify", "depends_on": []}]

    def tasks_to_strings(self, tasks: list[dict]) -> list[str]:
        return [t["description"] for t in tasks]
