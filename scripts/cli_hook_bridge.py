import argparse
import json
import os
import sys

# core/ 모듈 import를 위해 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# __init__.py의 heavy import 체인(cli.py → implementation_language_policy 등)을
# 우회하기 위해 session_adapter를 직접 import
import importlib
_mod = importlib.import_module("core.providers.session_adapter")
handle_hook_event = _mod.handle_hook_event


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bridge CLI hook events into agent-factory continuity.")
    parser.add_argument("--provider", required=True, choices=("claude", "gemini"))
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)

    raw = sys.stdin.read().strip()
    payload = json.loads(raw) if raw else {}
    result = handle_hook_event(
        args.provider,
        payload,
        workspace=args.workspace,
        run_id=args.run_id,
        repo_root=args.repo_root,
    )
    if result:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
