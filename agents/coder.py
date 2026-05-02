from core.llm import call_llm_async
from core.tokens import compress

CODER_PROMPT = """You are an expert software engineer.

Rules:
- Return ONLY a diff. Never return a full file.
- Format: lines starting with - are removed, + are added
- Include file path as first comment
- No explanation, no markdown prose

Task: [{type}] {description} → {target}

Context:
{context}
"""


class CoderAgent:
    def __init__(self, config):
        self.config = config

    async def generate(self, task: dict, context: list[str]) -> str:
        context_str = "\n---\n".join(context) if context else "No context."
        # Compression si le contexte dépasse le budget
        context_str = compress(context_str, self.config.MAX_CONTEXT_TOKENS)

        prompt = CODER_PROMPT.format(
            type=task.get("type", "modify"),
            description=task["description"],
            target=task.get("target", "unknown"),
            context=context_str,
        )
        diff = await call_llm_async(prompt, self.config)

        # Tronque le diff si trop long
        return compress(diff, self.config.MAX_DIFF_SIZE)
