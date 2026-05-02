def estimate(text: str) -> int:
    """Estimation rapide : ~4 chars par token (approximation Claude)."""
    return len(text) // 4


def truncate_to_budget(chunks: list[str], max_tokens: int) -> list[str]:
    """Retourne les chunks qui tiennent dans le budget token."""
    result = []
    used = 0
    for chunk in chunks:
        cost = estimate(chunk)
        if used + cost > max_tokens:
            break
        result.append(chunk)
        used += cost
    return result


def compress(text: str, max_tokens: int) -> str:
    """Tronque le texte au budget en coupant proprement aux sauts de ligne."""
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars // 2:
        truncated = truncated[:last_newline]
    return truncated + "\n# [truncated]"
