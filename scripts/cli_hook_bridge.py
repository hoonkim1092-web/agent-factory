import argparse
import json
import os
import sys

# core/ 모듈 import를 위해 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# __init__.py의 heavy import 체인(cli.py → implementation_language_policy 등)을
# 완전히 우회하기 위해 spec_from_file_location으로 session_adapter만 직접 로드
import importlib.util as _ilu
_sa_path = os.path.join(_PROJECT_ROOT, "core", "providers", "session_adapter.py")
_spec = _ilu.spec_from_file_location("core.providers.session_adapter", _sa_path,
                                      submodule_search_locations=[])
_mod = _ilu.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
handle_hook_event = _mod.handle_hook_event


def _configure_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(description="Bridge CLI hook events into agent-factory continuity.")
    parser.add_argument("--provider", required=True, choices=("claude", "gemini"))
    parser.add_argument("--workspace", default="")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", default="")
    args = parser.parse_args(argv)
    if not args.workspace:
        args.workspace = _PROJECT_ROOT

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
        print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
