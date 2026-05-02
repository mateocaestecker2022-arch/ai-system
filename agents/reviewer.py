from core.llm import call_llm_async


REVIEWER_PROMPT = """You are a senior code reviewer. Review the following code changes.

Check for:
- Bugs or logic errors
- Security vulnerabilities (injection, XSS, auth bypass, etc.)
- Performance issues
- Missing edge case handling

If changes are needed, return the corrected diff.
If the code is correct, return it unchanged.
No explanation — only the final code/diff.

Code to review:
{code}
"""


class ReviewerAgent:
    def __init__(self, config):
        self.config = config

    async def review(self, code: str) -> str:
        return await call_llm_async(
            REVIEWER_PROMPT.format(code=code),
            self.config,
        )
