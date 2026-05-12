import os
import subprocess

class GitManager:
    """
    (V23) Git Orchestrator — workspace-scoped.

    범위 원칙:
    - commit/rollback은 생성 시 전달된 directory(workspace) 안에서만 동작한다.
    - factory 코드는 에이전트 git 조작 범위에서 제외된다.
    - rollback은 tracked 파일 변경만 되돌린다 (untracked 파일은 보존).
    """
    def __init__(self, directory: str | None = None):
        self.directory = os.path.abspath(directory or os.getcwd())

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_git_repo(self) -> bool:
        """directory 안에 git repo가 존재하는지 확인한다."""
        if not os.path.isdir(self.directory):
            return False
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=self.directory,
            capture_output=True,
        )
        return r.returncode == 0

    def _has_changes(self) -> bool:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.directory,
            capture_output=True,
            text=True,
            check=False,
        )
        return bool(str(r.stdout or "").strip())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commit(self, message: str) -> bool:
        """workspace 내 변경사항을 커밋한다."""
        if not self._is_git_repo():
            return False
        try:
            subprocess.run(["git", "add", "."], check=True, cwd=self.directory)
            if not self._has_changes():
                return True
            subprocess.run(["git", "commit", "-m", message], check=True, cwd=self.directory)
            return True
        except Exception as e:
            print(f"[GitManager] Commit failed: {e}")
            return False

    def rollback(self) -> bool:
        """workspace 내 tracked 파일 변경을 되돌린다.

        전략:
        - tracked 파일: git checkout -- . 으로 HEAD 상태로 복원
        - untracked 파일: 보존 (에이전트가 생성한 결과물 보호)
        - stash를 사용하지 않으므로 stash 축적 문제가 없다
        """
        if not self._is_git_repo():
            return False
        try:
            print(f"[GitManager] Rolling back tracked changes in {self.directory}...")
            if not self._has_changes():
                return True
            subprocess.run(["git", "checkout", "--", "."], check=True, cwd=self.directory)
            return True
        except Exception as e:
            print(f"[GitManager] Rollback failed: {e}")
            return False

    def get_head_sha(self) -> str:
        """현재 HEAD의 SHA를 반환한다. git repo가 아니면 빈 문자열."""
        if not self._is_git_repo():
            return ""
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.directory,
                capture_output=True,
                text=True,
                check=True,
            )
            return str(r.stdout or "").strip()
        except Exception:
            return ""

    def diff_files_since(self, base_sha: str) -> list[str]:
        """base_sha 이후 변경된 파일 목록을 반환한다.

        - base_sha가 비어있거나 유효하지 않으면 working tree의 변경 파일 반환
        - git repo가 아니면 빈 리스트 반환 (graceful fallback)
        """
        if not self._is_git_repo():
            return []
        try:
            if base_sha:
                # committed + staged + unstaged 모두 포함
                r = subprocess.run(
                    ["git", "diff", "--name-only", base_sha, "HEAD"],
                    cwd=self.directory,
                    capture_output=True,
                    text=True,
                    check=True,
                )
                committed = [f.strip() for f in (r.stdout or "").splitlines() if f.strip()]
                # unstaged 변경도 포함
                r2 = subprocess.run(
                    ["git", "diff", "--name-only"],
                    cwd=self.directory,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                unstaged = [f.strip() for f in (r2.stdout or "").splitlines() if f.strip()]
                return list(dict.fromkeys(committed + unstaged))  # 중복 제거, 순서 유지
            else:
                # base_sha 없으면 현재 working tree 변경 파일만
                r = subprocess.run(
                    ["git", "diff", "--name-only"],
                    cwd=self.directory,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                return [f.strip() for f in (r.stdout or "").splitlines() if f.strip()]
        except Exception:
            return []

    def push(self) -> bool:
        """Pushes current branch to origin."""
        try:
            subprocess.run(["git", "push"], check=True, cwd=self.directory)
            return True
        except Exception as e:
            print(f"[GitManager] Push failed: {e}")
            return False

def git_configure_and_push(directory: str, target_dir: str, agent_name: str, model_name: str, logger=print) -> bool:
    """Legacy function for push integration."""
    mgr = GitManager(directory)
    msg = f"feat: Factory generated/updated {agent_name} using {model_name}"
    if mgr.commit(msg):
        return mgr.push()
    return False
