import os


class Config:
    MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-6")
    API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    MAX_CONTEXT_FILES = int(os.getenv("MAX_CONTEXT_FILES", "5"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
    SUPPORTED_EXTENSIONS = (".py", ".js", ".ts", ".go", ".java", ".rs")
