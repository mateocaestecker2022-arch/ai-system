import os
from pathlib import Path

# Fichiers critiques prioritaires (sécurité / data)
CRITICAL_KEYWORDS = [
    "auth", "login", "logout", "session", "token", "jwt",
    "password", "passwd", "secret", "key", "credential",
    "payment", "billing", "stripe", "invoice",
    "db", "database", "query", "sql", "model",
    "api", "route", "endpoint", "middleware",
    "admin", "permission", "role", "acl",
    "upload", "file", "storage",
]

SKIP_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "dist", "build", ".ai"}
SUPPORTED = (".py", ".js", ".ts", ".go", ".java", ".rs", ".tsx", ".jsx")


def select_critical_files(project_path: str, max_files: int = 5) -> dict[str, str]:
    """
    Sélectionne les fichiers les plus critiques d'un projet.
    Retourne {path: content}.
    """
    scored = []

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if not file.endswith(SUPPORTED):
                continue
            path = Path(root) / file
            name_lower = file.lower()
            path_lower = str(path).lower()

            score = sum(
                2 if k in name_lower else (1 if k in path_lower else 0)
                for k in CRITICAL_KEYWORDS
            )
            if score > 0:
                scored.append((score, path))

    scored.sort(key=lambda x: x[0], reverse=True)

    result = {}
    for _, path in scored[:max_files]:
        try:
            result[str(path)] = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

    return result


def select_files_by_paths(paths: list[str]) -> dict[str, str]:
    result = {}
    for p in paths:
        path = Path(p)
        if path.exists() and path.is_file():
            try:
                result[str(path)] = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
    return result
