import argparse
import json
import sys
from core.config import Config
from core.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(description="AI system for code optimization")
    parser.add_argument("command", choices=["analyze", "fix", "optimize", "index", "serve"])
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
        print(f"  [{t['type']}] {t['description']}")
    print(f"\n=== Context files used: {result['context_files']} ===\n")
    print(result["result"])


if __name__ == "__main__":
    main()
