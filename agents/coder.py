from core.llm import call_llm_async


CODER_PROMPT = """You are an expert software engineer. Generate ONLY the necessary code changes.

Rules:
- Use diff format for modifications (- removed, + added)
- Never rewrite a whole file if only one function needs changing
- No explanation, no markdown prose — code only
- Include the file path as a comment at the top

Tasks:
{tasks}

Relevant context:
{context}
"""


class CoderAgent:
    def __init__(self, config):
        self.config = config

    async def generate(self, tasks: list[dict], context: list[str]) -> str:
        tasks_str = "\n".join(
            f"[{t['type'].upper()}] {t['description']} → {t['target']}"
            for t in tasks
        )
        context_str = "\n---\n".join(context) if context else "No context available."

        return await call_llm_async(
            CODER_PROMPT.format(tasks=tasks_str, context=context_str),
            self.config,
        )
