import argparse
import sys
from core.config import Config
from core.orchestrator import Orchestrator


def print_scan_result(result: dict):
    stats = result.get("stats", {})
    print(f"\n=== Scan — {result.get('files_scanned', 0)} files ===")
    print(f"  High:   {stats.get('high', 0)}")
    print(f"  Medium: {stats.get('medium', 0)}")
    print(f"  Low:    {stats.get('low', 0)}")
    print(f"  Fixes:  {stats.get('auto_fixes', 0)}")

    print("\n=== Issues ===")
    for issue in result.get("issues", []):
        print(f"\n  [{issue['severity'].upper()}] {issue['type']} — {issue['location']}")
        print(f"  {issue['description']}")
        print(f"  Fix: {issue['fix']}")

    if result.get("fixes"):
        print("\n=== Auto-fixes ===")
        for fix in result["fixes"]:
            issue = fix["issue"]
            print(f"\n  --- {issue['location']} ({issue['severity']}) ---")
            print(fix["diff"])


def print_dev_result(result: dict):
    print("\n=== Tasks ===")
    for t in result.get("tasks", []):
        print(f"  [{t['type']}] {t['description']} → {t.get('target', '?')}")

    stats = result.get("stats", {})
    print(f"\n=== Stats ===")
    print(f"  Tasks:            {stats.get('total_tasks', 0)}")
    print(f"  Cached:           {stats.get('cached', 0)}")
    print(f"  Reviewer skipped: {stats.get('reviewer_skipped', 0)}")
    print(f"  ~Tokens out:      {stats.get('estimated_tokens_out', 0)}")

    print("\n=== Results ===")
    for r in result.get("results", []):
        cached_tag = " [CACHED]" if r.get("cached") else ""
        skipped_tag = " [reviewer skipped]" if r.get("reviewer_skipped") else ""
        print(f"\n--- Task {r['task_id']}: {r['task']}{cached_tag}{skipped_tag} ---")
        print(r.get("diff", ""))


def main():
    parser = argparse.ArgumentParser(description="AI System V2")
    parser.add_argument("command", choices=["run", "fix", "optimize", "scan", "index", "serve"])
    parser.add_argument("--project", help="Path to project")
    parser.add_argument("--query", help="What to do")
    parser.add_argument("--autofix", action="store_true", help="Auto-fix issues found during scan")
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

    if args.command == "scan":
        import asyncio
        config = Config()
        orch = Orchestrator(config)
        result = asyncio.run(orch.scan_async(args.project, auto_fix=args.autofix))
        print_scan_result(result)
        return

    if not args.query:
        print("Error: --query is required", file=sys.stderr)
        sys.exit(1)

    config = Config()
    orch = Orchestrator(config)
    result = orch.run(args.query, args.project)
    print_dev_result(result)


if __name__ == "__main__":
    main()
