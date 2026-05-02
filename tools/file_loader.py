from pathlib import Path


def load_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def load_files(paths: list[str]) -> dict[str, str]:
    return {p: load_file(p) for p in paths if Path(p).exists()}
