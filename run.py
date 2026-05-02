import argparse
import json
import sys
from core.config import Config
from core.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="AI System V2")
    parser.add_argument("command", choices=["run", "analyze", "fix", "optimize", "index", "serve"])
    parser.add_argument("--project", help="Path to project")
    parser.add_argument("--query", help="What to do")
    parser.add_argument("--port", type=int, default=8000, help="API port (serve mode)")
    args = parser.parse_args()

    if args.command == "serve":
        import uvicorn
        uvicorn.run("api.main:app", host="0.0.0.0", port=args.port, reload=False)
        return

    if not args.project:
        print("Error: --project is required", file=sys.stderr)
        sys.exit(1)

    if args.command == "index":
        from tools.indexer import build_and_save
        print(f"Indexing {args.project}...")
        chunks = build_and_save(args.project)
        print(f"Done — {len(chunks)} chunks in {args.project}/.ai/")
        return

    if not args.query:
        print("Error: --query is required", file=sys.stderr)
        sys.exit(1)

    config = Config()
    orch = Orchestrator(config)
    result = orch.run(args.query, args.project)

    print("\n=== Tasks ===")
    for t in result["tasks"]:
        print(f"  [{t['type']}] {t['description']} → {t.get('target', '?')}")

    print(f"\n=== Stats ===")
    stats = result.get("stats", {})
    print(f"  Tasks: {stats.get('total_tasks', 0)}")
    print(f"  Cached: {stats.get('cached', 0)}")
    print(f"  Reviewer skipped: {stats.get('reviewer_skipped', 0)}")
    print(f"  ~Tokens out: {stats.get('estimated_tokens_out', 0)}")

    print("\n=== Results ===")
    for r in result.get("results", []):
        cached_tag = " [CACHED]" if r.get("cached") else ""
        skipped_tag = " [reviewer skipped]" if r.get("reviewer_skipped") else ""
        print(f"\n--- Task {r['task_id']}: {r['task']}{cached_tag}{skipped_tag} ---")
        print(r.get("diff", ""))


if __name__ == "__main__":
    main()
