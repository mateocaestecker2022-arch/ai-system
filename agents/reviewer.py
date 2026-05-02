from core.llm import call_llm_async
from core.tokens import compress

REVIEWER_PROMPT = """You are a senior code reviewer.

Rules:
- Input is a diff. Output must also be a diff.
- Never return a full file.
- Check: bugs, security issues, performance, edge cases.
- If the diff is correct, return it unchanged.
- No explanation.

Diff to review:
{diff}
"""


class ReviewerAgent:
    def __init__(self, config):
        self.config = config

    async def review(self, diff: str) -> str:
        # Le Reviewer ne reçoit que le diff — jamais le fichier complet
        diff_compressed = compress(diff, self.config.MAX_DIFF_SIZE)
        return await call_llm_async(
            REVIEWER_PROMPT.format(diff=diff_compressed),
            self.config,
        )
