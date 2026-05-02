import os


class Config:
    MODEL = os.getenv("AI_MODEL", "claude-sonnet-4-6")
    API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

    # Limites strictes V2
    MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "5"))
    MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "3000"))
    MAX_DIFF_SIZE = int(os.getenv("MAX_DIFF_SIZE", "1500"))
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))

    # Compatibilité ancien nom
    MAX_CONTEXT_FILES = MAX_CHUNKS

    SUPPORTED_EXTENSIONS = (".py", ".js", ".ts", ".go", ".java", ".rs", ".tsx", ".jsx")

    # Types de tâches qui skip le Reviewer
    SIMPLE_TASK_TYPES = {"simple_fix", "rename", "comment", "formatting"}
