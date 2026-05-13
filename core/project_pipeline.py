import inspect
import json
import logging
import os
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from core.approval_gate import ApprovalGate
from core.bootstrap_roles import ProjectPlanningDirector, build_bootstrap_agent
from core.documentation_policy import ensure_documentation_files, write_project_todo
from core.dynamic_orchestrator import DynamicOrchestrator
from core.project_task_board import (
    board_todo_items,
    build_project_board,
    enrich_role_plan,
    write_project_board,
    write_task_execution_plan,
)
from core.utils import (
    append_dashboard_run,
    now_iso,
    print_agent_msg,
    read_yaml,
    safe_id,
    to_portable_path,
    write_yaml,
)
from core.work_item_generator import generate_work_items, slug_from_brief
from core.work_item_parser import sync_board_from_work_items
from core.agent_runner import _safe_print

PROJECT_ROLE_BASELINE_SKILLS = ("file_handler", "core_memory")


class ResearchGateBlocked(RuntimeError):
    """P2 C1: coverage_report.block==True 시 work_item 생성을 차단하는 예외."""


@dataclass
class PreparedBrief:
    """prepare_brief() 결과 — Evidence + Brief까지만 담은 중간 객체.

    Clarification 단계에서 project_brief를 enriched_brief로 교체한 뒤
    prepare_documents()에 전달한다.
    """

    run_id: str
    workspace: str
    task_input: str
    project_brief: dict
    research_evidence: dict = field(default_factory=dict)
    research_evidence_path: str = ""
    project_brief_path: str = ""
    memory_context: dict = field(default_factory=dict)


@dataclass
class PreparedProject:
    """
    prepare() 의 결과 객체.

    승인 전까지 execute() 를 호출하면 안 된다.
    approval_gate.is_execution_open() 이 True 일 때만 execute() 진행.
    """

    run_id: str
    workspace: str
    work_item_slug: str
    project_brief: dict
    role_plan: dict
    task_board: dict
    planning_files: list[str] = field(default_factory=list)
    work_item_files: dict[str, str] = field(default_factory=dict)
    # 하위 호환: 개별 경로 필드
    project_brief_path: str = ""
    role_plan_path: str = ""
    task_board_path: str = ""
    task_execution_plan_path: str = ""
    todo_path: str = ""
    research_evidence: dict = field(default_factory=dict)
    research_evidence_path: str = ""
    # target_path가 있으면 문서는 그 경로에, 없으면 workspace에 생성
    doc_root: str = ""

    def _effective_doc_root(self) -> str:
        """work-item 문서가 실제로 저장된 루트 경로."""
        return self.doc_root if self.doc_root else self.workspace

    def work_item_dir(self) -> str:
        return os.path.join(self._effective_doc_root(), "docs", "work-items", self.work_item_slug)

    def gate(self) -> ApprovalGate:
        return ApprovalGate(self._effective_doc_root(), self.work_item_slug,
                            runtime_workspace=self.workspace)

    def summary_lines(self) -> list[str]:
        roles = self.role_plan.get("roles") or []
        tasks = self.task_board.get("tasks") or []
        modules = self.role_plan.get("modules") or []
        lines = [
            f"  목표: {self.project_brief.get('goal', '')}",
            f"  역할 수: {len(roles)}",
            f"  모듈 수: {len(modules)}",
            f"  작업 수: {len(tasks)}",
            f"  work-item: {self.work_item_dir()}",
        ]
        return lines


class ProjectPipeline:
    """
    2-Phase 프로젝트 파이프라인.

    Phase 1 — prepare():  문서 생성 + work-item 자동 채움. 에이전트 실행 없음.
    Phase 2 — execute():  승인 확인 → 편집 반영 → 에이전트 실행.

    하위 호환:
      run() = prepare() + 자동 승인 + execute()
    """

    def __init__(self, mr, agent_mgr, research_agent, procurer,
                 broker=None, reservation_mgr=None, visualizer=None):
        self.mr = mr
        self.agent_mgr = agent_mgr
        self.research = research_agent
        self.procurer = procurer
        self.planner = ProjectPlanningDirector(mr)
        self._broker = broker
        self._reservation_mgr = reservation_mgr
        self._visualizer = visualizer

    def _write_json(self, path: str, data: dict):
        import tempfile
        dir_ = os.path.dirname(path) or "."
        os.makedirs(dir_, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dir_, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _write_skill_manifest(self, workspace: str, role_id: str, run_id: str, entries: list[dict]) -> None:
        """agents/{role_id}/skill_manifest.json — 스킬 조달 경로 기록 (projection)."""
        rid = safe_id(role_id)
        manifest_dir = os.path.join(workspace, "agents", rid)
        os.makedirs(manifest_dir, exist_ok=True)
        now_str = now_iso()
        manifest = {
            "role_id": rid,
            "run_id": f"{run_id}_{rid}",
            "skills": entries,
            "summary": {
                "requested": len(entries),
                "installed": sum(1 for e in entries if e.get("installed")),
                "by_mode": {},
            },
            "generated_at": now_str,
        }
        for e in entries:
            mode = e.get("decision_mode", "unknown")
            manifest["summary"]["by_mode"][mode] = manifest["summary"]["by_mode"].get(mode, 0) + 1
        self._write_json(os.path.join(manifest_dir, "skill_manifest.json"), manifest)

    def _planning_dir(self, workspace: str) -> str:
        planning_dir = os.path.join(workspace, "planning")
        os.makedirs(planning_dir, exist_ok=True)
        return planning_dir

    # ── Checkpoint helpers ──────────────────────────────────────────────

    def _checkpoint_dir(self, workspace: str) -> str:
        d = os.path.join(workspace, ".checkpoint")
        os.makedirs(d, exist_ok=True)
        return d

    def _save_checkpoint(self, workspace: str, stage: str, data: dict) -> None:
        """단계 완료 시 결과를 .checkpoint/{stage}.json에 저장 (atomic write)."""
        import hashlib as _hl
        path = os.path.join(self._checkpoint_dir(workspace), f"{stage}.json")
        payload = {
            "stage": stage,
            "saved_at": now_iso(),
            "data_hash": _hl.md5(
                json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
            ).hexdigest(),
            "data": data,
        }
        try:
            self._write_json(path, payload)
        except Exception as exc:
            print(f"[Checkpoint] save failed for stage={stage}: {exc}")

    def _load_checkpoint(self, workspace: str, stage: str) -> dict | None:
        """체크포인트가 존재하면 data를 반환, 없으면 None."""
        path = os.path.join(self._checkpoint_dir(workspace), f"{stage}.json")
        if not os.path.exists(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                payload = json.load(f)
            return payload.get("data")
        except Exception:
            return None

    # ── P2 C1 helpers ──────────────────────────────────────────────────

    def _verify_domain_spec(self, workspace: str, slug: str) -> bool:
        """도메인 스펙 파일이 이미 생성되어 있으면 True."""
        from pathlib import Path
        return any((Path(workspace) / "docs" / "specs").glob(f"{slug}-*.md"))

    def _save_specs(self, specs: dict, workspace: str, slug: str) -> list:
        """SpecGenerator 출력을 docs/specs/<slug>-<filename> 에 저장. 저장된 Path 리스트 반환."""
        from pathlib import Path
        from core.spec_generator import SPEC_FILENAMES
        specs_dir = Path(workspace) / "docs" / "specs"
        specs_dir.mkdir(parents=True, exist_ok=True)
        saved = []
        for key, content in specs.items():
            filename = SPEC_FILENAMES.get(key, f"{key}.md")
            p = specs_dir / f"{slug}-{filename}"
            p.write_text(content, encoding="utf-8")
            saved.append(p)
        return saved

    def _load_evidence(self, workspace: str, task_input: str) -> tuple[list[dict], list[dict]]:
        """docs/research/<safe_id(task_input)[:40]>-evidence.json에서 claims/sources를 읽어 반환.

        researcher.py:1069 와 동일한 slug 파생 (`safe_id(task_input)[:40]`) 사용.
        """
        import json
        import logging
        from pathlib import Path
        evidence_slug = safe_id(task_input)[:40]
        path = Path(workspace) / "docs" / "research" / f"{evidence_slug}-evidence.json"
        if not path.exists():
            return [], []
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("claims") or [], data.get("sources") or []
        except json.JSONDecodeError as exc:
            logging.warning("[Pipeline] evidence JSON parse error (%s): %s", path, exc)
            return [], []

    def _save_adr(self, workspace: str, slug: str, adr_md: str) -> "Path":
        """ADR을 docs/decisions/<slug>-rule-baseline.md 에 원자적으로 저장."""
        import tempfile, os
        from pathlib import Path
        out_dir = Path(workspace) / "docs" / "decisions"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{slug}-rule-baseline.md"
        with tempfile.NamedTemporaryFile("w", dir=out_dir, delete=False, suffix=".tmp", encoding="utf-8") as fh:
            fh.write(adr_md)
            tmp = fh.name
        os.replace(tmp, dest)
        return dest

    def _save_traceability(self, workspace: str, slug: str, trace_md: str) -> "Path":
        """traceability를 docs/research/<slug>-traceability.md 에 원자적으로 저장."""
        import tempfile, os
        from pathlib import Path
        out_dir = Path(workspace) / "docs" / "research"
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / f"{slug}-traceability.md"
        with tempfile.NamedTemporaryFile("w", dir=out_dir, delete=False, suffix=".tmp", encoding="utf-8") as fh:
            fh.write(trace_md)
            tmp = fh.name
        os.replace(tmp, dest)
        return dest

    def _coverage_blocked(self, research_evidence: dict) -> bool:
        return bool((research_evidence.get("coverage_report") or {}).get("block"))

    # ── Structural Gate (Rubric-based) ─────────────────────────────────

    def _load_doc_contents(self, work_item_files: dict[str, str]) -> dict[str, str]:
        """{name: path} → {name: content} 변환. 읽기 실패 시 빈 문자열."""
        out: dict[str, str] = {}
        for name, path in work_item_files.items():
            try:
                with open(path, encoding="utf-8") as f:
                    out[name] = f.read()
            except OSError:
                out[name] = ""
        return out

    def run_structural_gate(self, artifact: dict, artifact_type: str = "architecture_plan") -> dict:
        """Rubric Compiler를 사용해 artifact를 평가하고 gate 결과를 반환.

        Returns:
            {"pass": bool, "status": str, "rubric_score": float,
             "errors": [...], "warnings": [...], "weakest_dimensions": [...]}
        """
        try:
            from core.rubric_compiler import RubricCompiler
            result = RubricCompiler().evaluate(artifact, artifact_type)
            return {
                "pass": result.status in ("pass", "pass_with_warnings"),
                "status": result.status,
                "rubric_score": result.total_score,
                "errors": result.errors,
                "warnings": result.warnings,
                "weakest_dimensions": result.weakest_dimensions(2),
                "dimension_scores": {
                    d.name: {"score": d.score, "raw": d.raw_score}
                    for d in result.dimension_scores
                },
            }
        except Exception as exc:
            print(f"[ProjectPipeline] rubric gate failed, falling back: {exc}")
            return self._basic_structural_check(artifact)

    def _basic_structural_check(self, artifact: dict) -> dict:
        errors, warnings = [], []
        if not artifact.get("goal"):
            errors.append("goal is missing")
        if not artifact.get("deliverables"):
            warnings.append("deliverables is empty")
        if not artifact.get("acceptance_criteria"):
            warnings.append("acceptance_criteria is empty")
        return {
            "pass": not errors,
            "status": "pass" if not errors else "fail",
            "rubric_score": 0.5,
            "errors": errors,
            "warnings": warnings,
            "weakest_dimensions": [],
        }

    # ── Gate B: iMAD Debate Necessity Classifier ────────────────────────

    def needs_agent_qa(
        self,
        critique_result: dict,
        structural_gate_result: dict,
        task_profile: dict | None = None,
    ) -> bool:
        """Agent QA가 필요한지 iMAD 패턴으로 판단한다."""
        tp = task_profile or {}
        if tp.get("complexity_tier") == "critical":
            return True
        if tp.get("execution_check_required"):
            return True
        if tp.get("risk_level") == "high":
            return True

        critique_score = float(critique_result.get("score") or 0.0)
        gate_pass = bool(structural_gate_result.get("pass"))
        confirmed_gaps = list(critique_result.get("confirmed_gaps") or [])
        gate_warnings = len(structural_gate_result.get("warnings") or [])

        if gate_pass and critique_score >= 0.85 and not confirmed_gaps:
            return False

        return (
            critique_score < 0.75
            or len(confirmed_gaps) > 0
            or gate_warnings > 2
        )

    # ── Gate A: Confidence Gate (Fast Path) ─────────────────────────────

    def should_fast_path(self, task_profile: dict, evidence_result: dict) -> bool:
        """Gate A: simple 요청을 Draft→Gate→Accept로 단축할지 판단한다."""
        tp = task_profile or {}
        ev = evidence_result or {}
        return (
            tp.get("complexity_tier") == "simple"
            and float(ev.get("score") or 0.0) >= 0.7
            and not tp.get("comparison_mode", False)
            and tp.get("risk_level", "normal") == "low"
        )

    # ── Convergence Detection ────────────────────────────────────────────

    def revision_loop_with_convergence(
        self,
        draft: dict,
        critique_feedback: dict,
        evidence: dict,
        rewrite_fn,
        score_fn,
        max_iterations: int = 5,
        convergence_threshold: float = 0.02,
        min_iterations: int = 2,
        critique_fn=None,
    ) -> tuple[dict, float, int]:
        """자가진화 revision loop: 비평 → 수정 → 재비평 → 수정.

        ISE StrategyLedger와 동일한 원리:
        - 매 iteration마다 새로운 비평 (critique_fn)
        - 이전 실패/무개선 시도 이력을 rewrite_fn에 주입
        - 같은 수정을 반복하지 않도록 학습

        critique_fn(artifact, evidence) → dict: 새 비평 결과
        없으면 초기 critique_feedback 재사용 (하위호환).

        Returns: (최종 artifact, 최종 score, 실제 반복 횟수)
        """
        current = dict(draft)
        previous_score = score_fn(current)
        live_feedback = dict(critique_feedback)

        if max_iterations <= 0:
            return current, previous_score, 0

        actual_iterations = 0
        consecutive_no_gain = 0
        best_artifact, best_score = dict(current), previous_score

        # ── 자가진화 이력: ISE StrategyLedger와 동일 패턴 ──
        revision_history: list[dict] = []

        for i in range(max_iterations):
            actual_iterations = i + 1

            # ── Step 1: 비평(critique) — 매 iteration마다 재평가
            if critique_fn is not None and actual_iterations > 1:
                try:
                    live_feedback = critique_fn(current, evidence)
                    print(f"[RevisionLoop] iter={actual_iterations} re-critique score={live_feedback.get('score', '?')}")
                except Exception as exc:
                    print(f"[RevisionLoop] critique_fn failed at iter {actual_iterations}: {exc}")

            # ── Step 2: 이전 시도 이력을 피드백에 주입
            if revision_history:
                live_feedback = dict(live_feedback)
                history_lines = []
                for h in revision_history[-3:]:
                    history_lines.append(
                        f"- iter {h['iter']}: score {h['score']:.3f} "
                        f"(delta {h['delta']:+.3f}) — {h['summary']}"
                    )
                live_feedback["_revision_history"] = (
                    "[이전 수정 시도 — 같은 접근을 반복하지 마세요]\n"
                    + "\n".join(history_lines)
                )

            # ── Step 3: 수정(rewrite) — 최신 비평 + 이력 기반
            try:
                revised = rewrite_fn(current, live_feedback, evidence)
            except Exception as exc:
                print(f"[RevisionLoop] rewrite_fn failed at iteration {actual_iterations}: {exc}")
                break

            new_score = score_fn(revised)
            delta = new_score - previous_score
            print(f"[RevisionLoop] iter={actual_iterations} score={new_score:.3f} delta={delta:+.3f}")

            # ── Step 4: 이력 기록 (자가진화 학습 데이터)
            revision_history.append({
                "iter": actual_iterations,
                "score": new_score,
                "delta": delta,
                "summary": "improved" if delta > 0 else "no gain" if delta == 0 else "regressed",
                "feedback_keys": list(live_feedback.get("confirmed_gaps", []))[:3],
            })

            if new_score > best_score:
                best_artifact, best_score = dict(revised), new_score
                consecutive_no_gain = 0
            else:
                consecutive_no_gain += 1

            # ── 수렴 판단: min_iterations 충족 후
            if actual_iterations >= min_iterations and consecutive_no_gain >= 2:
                print(f"[RevisionLoop] 수렴 — 연속 {consecutive_no_gain}회 무개선 (iter={actual_iterations})")
                break

            if actual_iterations >= min_iterations and delta < convergence_threshold:
                print(f"[RevisionLoop] 수렴 감지 (delta={delta:.3f} < {convergence_threshold})")
                break

            current, previous_score = revised, new_score

        return best_artifact, best_score, actual_iterations

    # ── Targeted Final Rewrite ───────────────────────────────────────────

    def targeted_rewrite(
        self,
        artifact: dict,
        qa_findings: list[str],
        critique_gaps: list[str],
        gate_warnings: list[str],
        rewrite_section_fn,
    ) -> dict:
        """영향받는 섹션만 재작성한다 (전체 재작성 대신)."""
        all_feedback = qa_findings + critique_gaps + gate_warnings
        if not all_feedback:
            return artifact

        _field_keywords = {
            "goal":                 ["goal", "목표", "요청", "정합성"],
            "deliverables":         ["deliverable", "산출물", "owner"],
            "risks":                ["risk", "위험", "mitigation", "대응"],
            "acceptance_criteria":  ["acceptance", "criteria", "검증", "테스트"],
            "roles":                ["role", "역할", "담당자"],
            "implementation_notes": ["implementation", "구현", "기술", "tech"],
            "evidence_summary":     ["evidence", "근거", "grounding", "출처"],
        }

        field_feedback_map: dict[str, list[str]] = {}
        for fb in all_feedback:
            fb_lower = fb.lower()
            for field_key, keywords in _field_keywords.items():
                if any(kw in fb_lower for kw in keywords):
                    field_feedback_map.setdefault(field_key, []).append(fb)

        if not field_feedback_map:
            return artifact

        revised = dict(artifact)
        for field_key, feedbacks in field_feedback_map.items():
            if field_key not in revised:
                continue
            try:
                revised[field_key] = rewrite_section_fn(field_key, revised[field_key], feedbacks)
            except Exception as exc:
                print(f"[TargetedRewrite] {field_key} failed: {exc}")

        revised["_rewrite_log"] = {
            "type": "targeted",
            "sections_modified": list(field_feedback_map.keys()),
            "feedback_count": len(all_feedback),
        }
        return revised

    def _role_agent_path(self, role_id: str, workspace: str) -> str:
        return os.path.join(workspace, "agents", f"{safe_id(role_id)}.yaml")

    def _merge_role_baseline(self, agent_data: dict) -> dict:
        merged = dict(agent_data or {})
        existing_skills = [safe_id(str(s)) for s in (merged.get("skills") or []) if str(s).strip()]
        merged["skills"] = list(dict.fromkeys(existing_skills + list(PROJECT_ROLE_BASELINE_SKILLS)))

        runtime_rules = merged.get("runtime_rules", {})
        if not isinstance(runtime_rules, dict):
            runtime_rules = {}
        allowed_skills = [
            safe_id(str(s))
            for s in (runtime_rules.get("allowed_skills") or [])
            if str(s).strip()
        ]
        runtime_rules["allowed_skills"] = list(
            dict.fromkeys(allowed_skills + list(PROJECT_ROLE_BASELINE_SKILLS))
        )
        merged["runtime_rules"] = runtime_rules
        return merged

    def _write_todo(self, workspace: str, role_plan: dict, task_board: dict | None = None) -> str:
        todo_items = board_todo_items(task_board or {})
        if not todo_items:
            todo_items = [str(x).strip() for x in (role_plan.get("todo_items") or []) if str(x).strip()]
        if not todo_items:
            todo_items = [f"{item.get('name')}: {item.get('objective')}" for item in (role_plan.get("roles") or [])]
        return write_project_todo(workspace, todo_items, board=task_board or None)

    def _materialize_roles(
        self,
        role_plan: dict,
        project_brief: dict,
        workspace: str,
        execution_mode: str,
        enable_build: bool,
        run_id: str,
    ) -> tuple[list[str], dict[str, list[str]]]:
        roles: list[str] = []
        installed_map: dict[str, list[str]] = {}
        os.makedirs(os.path.join(workspace, "agents"), exist_ok=True)

        for item in (role_plan.get("roles") or []):
            if not isinstance(item, dict):
                continue
            role_id = safe_id(str(item.get("id") or item.get("name") or "role"))
            if not role_id:
                continue
            role_name = str(item.get("name") or role_id)
            objective = str(item.get("objective") or project_brief.get("goal") or "").strip()
            required_skills = [safe_id(str(s)) for s in (item.get("required_skills") or []) if str(s).strip()]
            role_modules = [
                module
                for module in (role_plan.get("modules") or [])
                if isinstance(module, dict) and safe_id(str(module.get("owner_role") or "")) == role_id
            ]
            feature_slices: list[str] = []
            for module in role_modules:
                for slice_name in (module.get("feature_slices") or []):
                    text = str(slice_name).strip()
                    if text and text not in feature_slices:
                        feature_slices.append(text)

            agent = self.agent_mgr.get_or_create(role_id, workspace=workspace)
            agent_path = self._role_agent_path(role_id, workspace)
            agent_data = read_yaml(agent_path) if os.path.exists(agent_path) else dict(agent)
            agent_data = self._merge_role_baseline(agent_data)
            agent_data["name"] = str(agent_data.get("name") or role_name)
            agent_data["role"] = role_name
            agent_data["project_role"] = {
                "objective": objective,
                "required_skills": required_skills,
                "owned_modules": [module.get("id") for module in role_modules if str(module.get("id") or "").strip()],
                "feature_slices": feature_slices,
                "planning_steps": [
                    str(step.get("id") or "").strip()
                    for step in (role_plan.get("planning_steps") or [])
                    if isinstance(step, dict) and str(step.get("id") or "").strip()
                ],
                "updated_at": now_iso(),
            }
            write_yaml(agent_path, agent_data)

            # role_spec.json — 역할 계약만 분리한 파생 뷰 (projection)
            role_spec = {
                "role_id": role_id,
                "name": role_name,
                "objective": objective,
                "required_skills": required_skills,
                "owned_modules": agent_data["project_role"]["owned_modules"],
                "feature_slices": feature_slices,
                "planning_steps": agent_data["project_role"]["planning_steps"],
                "source": "planning/role_plan.json",
                "generated_at": now_iso(),
            }
            spec_dir = os.path.join(workspace, "agents", role_id)
            os.makedirs(spec_dir, exist_ok=True)
            self._write_json(os.path.join(spec_dir, "role_spec.json"), role_spec)

            manifest_entries: list[dict] = []
            if required_skills and enable_build:
                reqs = {
                    "goal": objective or project_brief.get("goal") or role_name,
                    "constraints": list(project_brief.get("constraints") or []),
                    "missing_skills": required_skills,
                }
                installed, manifest_entries = self.procurer.procure_multiple(
                    agent=agent_data,
                    skill_names=required_skills,
                    reqs=reqs,
                    run_id=f"{run_id}_{role_id}",
                    execution_mode=execution_mode,
                    approval_gate=None,
                    workspace=workspace,
                )
                installed_map[role_id] = installed
            elif required_skills:
                self.agent_mgr.install_skills(role_id, required_skills, workspace=workspace)
                installed_map[role_id] = list(required_skills)
                manifest_entries = [
                    {"skill_id": s, "requested": True, "installed": True, "decision_mode": "direct_install", "reused_from": None, "forge_run_id": None, "fallback_chain": []}
                    for s in required_skills
                ]
            else:
                installed_map[role_id] = []

            # skill_manifest.json 저장 (projection)
            if manifest_entries:
                self._write_skill_manifest(workspace, role_id, run_id, manifest_entries)

            roles.append(role_id)

        return list(dict.fromkeys(roles)), installed_map

    # ------------------------------------------------------------------
    # Phase 1a: prepare_brief
    # ------------------------------------------------------------------

    def prepare_brief(
        self,
        task_input: str,
        workspace: str,
        execution_mode: str = "approval",
        enable_build: bool = False,
        requested_role: str = "",
        route: dict | None = None,
    ) -> PreparedBrief:
        """Phase 1a: Evidence 수집 + Brief 생성.

        Clarification 삽입 포인트를 위해 prepare()에서 분리.
        반환된 PreparedBrief.project_brief를 enriched_brief로 교체한 뒤
        prepare_documents()에 전달하면 된다.
        """
        target_workspace = os.path.abspath(workspace)
        os.makedirs(target_workspace, exist_ok=True)
        ensure_documentation_files(target_workspace)
        planning_dir = self._planning_dir(target_workspace)
        run_id = f"project_run_{int(time.time())}"

        # -- Memory Plane 조기 초기화 + 메모리 회상 (Planning 전에 필요) --
        memory_context: dict = {}
        try:
            from core.memory_system.facade import UnifiedMemoryFacade
            _facade = UnifiedMemoryFacade.get_instance()
            if not _facade._initialised:
                from core.agent_runner import _run_async_safe
                from core.memory_system.adapters.core_memory import CoreMemoryAdapter
                from core.memory_system.adapters.knowledge_graph import KnowledgeGraphAdapter
                _facade.register_adapter(CoreMemoryAdapter())
                _facade.register_adapter(KnowledgeGraphAdapter(workspace=target_workspace))
                _run_async_safe(_facade.initialise())
            from core.control.intake import ControlPlaneIntake
            memory_context = ControlPlaneIntake()._recall_from_memory(task_input)
            if memory_context.get("recall_count", 0) > 0:
                print(
                    f"[Pipeline] memory recalled: {memory_context['recall_count']} records "
                    f"({memory_context.get('recall_time_ms', 0):.0f}ms)"
                )
        except Exception:
            pass

        # -- Research --
        research_agent = build_bootstrap_agent("research_director")
        risk_level = str((route or {}).get("risk_level") or "normal").strip()
        comparison_mode = bool((route or {}).get("comparison_mode", False))
        research_evidence: dict = {}
        collect_evidence = getattr(self.research, "collect_project_evidence", None)
        if callable(collect_evidence):
            from core.research_verifier import ResearchVerifier
            verifier = ResearchVerifier()
            try:
                _collect_kwargs = dict(
                    workspace=target_workspace,
                    risk_level=risk_level,
                    comparison_mode=comparison_mode,
                )
                import inspect as _inspect
                _ce_params = _inspect.signature(collect_evidence).parameters
                _supports_risk = "risk_level" in _ce_params

                def _evidence_fn(**kwargs):
                    kw = dict(_collect_kwargs) | kwargs
                    if not _supports_risk:
                        kw.pop("risk_level", None)
                        kw.pop("comparison_mode", None)
                    try:
                        return collect_evidence(task_input, **kw) or {}
                    except TypeError:
                        # old-style collector (e.g. test mock) doesn't accept hint_gaps
                        kw.pop("hint_gaps", None)
                        try:
                            return collect_evidence(task_input, **kw) or {}
                        except Exception as exc2:
                            print(f"[ProjectPipeline] collect_project_evidence failed: {exc2}")
                            return {}
                    except Exception as exc:
                        print(f"[ProjectPipeline] collect_project_evidence failed: {exc}")
                        return {}

                research_evidence, _vr = verifier.verify_with_retry(
                    evidence_fn=_evidence_fn,
                    task_input=task_input,
                )
                if _vr.status != "pass":
                    print(
                        f"[ProjectPipeline] evidence quality={_vr.status} "
                        f"score={_vr.score} gaps={_vr.gaps}"
                    )
                    try:
                        from core.warning_registry import WarningRegistry as _WR
                        _ev_slug = safe_id(task_input)[:40]
                        _WR(workspace=target_workspace).record(
                            project_slug=_ev_slug,
                            rule_id="evidence_quality_warn",
                            affected_phase="scope",
                            count=len(_vr.gaps),
                            severity="warn",
                            extra={"score": _vr.score, "gaps": _vr.gaps},
                            source_path="core/project_pipeline.py:757",
                        )
                    except Exception as _eqw_exc:
                        print(f"[ProjectPipeline] warning_registry record skip (evidence_quality_warn): {_eqw_exc}")
            except Exception as exc:
                print(f"[ProjectPipeline] research verification failed: {exc}")
                try:
                    research_evidence = collect_evidence(task_input, workspace=target_workspace) or {}
                    research_evidence.setdefault("_warnings", []).append(f"evidence_degraded: {exc}")
                except Exception:
                    research_evidence = {"_stage_degraded": "evidence_acquisition", "_warnings": [str(exc)]}
        research_evidence_path = os.path.join(planning_dir, "research_evidence.json")
        self._write_json(research_evidence_path, research_evidence)
        self._save_checkpoint(target_workspace, "evidence_acquisition", research_evidence)

        # -- Brief --
        from core.pipeline_quality import PipelineStageGuard
        _guard = PipelineStageGuard()

        def _gen_brief():
            brief_params = inspect.signature(self.research.research_project_brief).parameters
            if "evidence_bundle" in brief_params:
                return self.research.research_project_brief(
                    research_agent, task_input,
                    workspace=target_workspace,
                    evidence_bundle=research_evidence,
                )
            return self.research.research_project_brief(
                research_agent, task_input, workspace=target_workspace,
            )

        project_brief = _guard.run(
            stage="draft_brief",
            fn=_gen_brief,
            fallback=lambda exc: {
                "goal": task_input[:200],
                "_stage_degraded": "draft_brief",
                "_warnings": [str(exc)],
            },
        )
        if not isinstance(project_brief, dict):
            project_brief = {"goal": task_input[:200]}
        project_brief["requested_role"] = requested_role
        project_brief["route"] = route or {}
        project_brief["generated_at"] = now_iso()
        project_brief_path = os.path.join(planning_dir, "project_brief.json")
        self._write_json(project_brief_path, project_brief)
        self._save_checkpoint(target_workspace, "draft_brief", project_brief)

        # P0 A6: brief를 docs/research/<slug>-project-brief.json 에 저장 (Quality Gate 추적용)
        try:
            _slug = slug_from_brief(project_brief)
            _research_dir = os.path.join(target_workspace, "docs", "research")
            os.makedirs(_research_dir, exist_ok=True)
            self._write_json(os.path.join(_research_dir, f"{_slug}-project-brief.json"), project_brief)
        except Exception:
            pass

        return PreparedBrief(
            run_id=run_id,
            workspace=target_workspace,
            task_input=task_input,
            project_brief=project_brief,
            research_evidence=research_evidence,
            research_evidence_path=to_portable_path(research_evidence_path),
            project_brief_path=to_portable_path(project_brief_path),
            memory_context=memory_context,
        )

    # ------------------------------------------------------------------
    # Phase 1b: prepare_documents
    # ------------------------------------------------------------------

    def prepare_documents(
        self,
        prepared_brief: PreparedBrief,
        execution_mode: str = "approval",
        enable_build: bool = False,
    ) -> PreparedProject:
        """Phase 1b: PreparedBrief → RolePlan → TaskBoard → Documents.

        prepare_brief() 이후, Clarification 적용 완료 상태에서 호출.
        """
        target_workspace = prepared_brief.workspace
        task_input = prepared_brief.task_input
        project_brief = prepared_brief.project_brief
        memory_context = prepared_brief.memory_context
        research_evidence = prepared_brief.research_evidence
        run_id = prepared_brief.run_id
        planning_dir = self._planning_dir(target_workspace)
        research_evidence_path = prepared_brief.research_evidence_path or os.path.join(
            planning_dir, "research_evidence.json"
        )
        project_brief_path = prepared_brief.project_brief_path or os.path.join(
            planning_dir, "project_brief.json"
        )

        # -- Planning --
        from core.pipeline_quality import PipelineStageGuard
        _guard = PipelineStageGuard()
        pd_agent = build_bootstrap_agent("pd_director")

        def _gen_role_plan():
            try:
                raw = self.planner.plan(task_input, project_brief, memory_context=memory_context)
            except TypeError:
                raw = self.planner.plan(task_input, project_brief)
            return enrich_role_plan(task_input, project_brief, raw, workspace=target_workspace)

        role_plan = _guard.run(
            stage="role_planning",
            fn=_gen_role_plan,
            fallback=lambda exc: {
                "roles": [],
                "modules": [],
                "_stage_degraded": "role_planning",
                "_warnings": [str(exc)],
            },
        )
        if not isinstance(role_plan, dict):
            role_plan = {"roles": [], "modules": []}
        role_plan["generated_at"] = now_iso()
        role_plan["pd_agent"] = {
            "id": pd_agent["id"],
            "name": pd_agent["name"],
        }
        role_plan_path = os.path.join(planning_dir, "role_plan.json")
        self._write_json(role_plan_path, role_plan)
        self._save_checkpoint(target_workspace, "role_plan", role_plan)

        # -- Task Board --
        task_board = build_project_board(project_brief, role_plan)
        task_board_path = write_project_board(target_workspace, task_board)
        task_execution_plan_path = write_task_execution_plan(
            target_workspace, project_brief, role_plan, task_board
        )
        todo_path = self._write_todo(target_workspace, role_plan, task_board)

        # -- Work Items --
        slug = slug_from_brief(project_brief)
        _adr_path, _trace_path = None, None  # P2 C3+C4: domain 분기 내에서 설정
        _spec_paths: list = []  # D1: planning_files 주입용

        # D3: research_evidence.research_plan → project_brief 주입 (domain 감지용)
        if not project_brief.get("research_plan") and research_evidence:
            _rp_from_ev = research_evidence.get("research_plan") or {}
            if _rp_from_ev:
                project_brief["research_plan"] = _rp_from_ev

        # P2 C1: Domain Spec Gate — coverage BLOCK 시 work_item 생성 차단
        _domain = (project_brief.get("research_plan") or {}).get("domain", "")
        if _domain:
            _specs_dict: dict = {}
            if not self._verify_domain_spec(target_workspace, slug):
                from core.spec_generator import SpecGenerator
                _specs_dict = SpecGenerator().generate(project_brief)
                _spec_paths = self._save_specs(_specs_dict, target_workspace, slug)
            else:
                from pathlib import Path as _Path
                from core.spec_generator import SPEC_FILENAMES as _SFN
                _key_by_fn = {v: k for k, v in _SFN.items()}
                for _p in (_Path(target_workspace) / "docs" / "specs").glob(f"{slug}-*.md"):
                    _spec_paths.append(_p)
                    try:
                        _fn = _p.name[len(slug) + 1:]
                        _specs_dict[_key_by_fn.get(_fn, _fn)] = _p.read_text(encoding="utf-8")
                    except Exception:
                        pass
            # D1: work_item_generator 프롬프트에 spec 내용이 보이도록 project_brief에 주입
            if _specs_dict:
                project_brief["domain_specs_summary"] = _specs_dict
            # P2 C3+C4: ADR + traceability 자동 생성 (경로는 planning_files에 나중에 추가)
            _claims, _sources = self._load_evidence(target_workspace, task_input)
            from core.spec_generator import AdrGenerator, TraceabilityGenerator
            _adr_md = AdrGenerator().generate(project_brief, _claims, _sources)
            _adr_path = self._save_adr(target_workspace, slug, _adr_md) if _adr_md else None
            _trace_md = TraceabilityGenerator().generate(project_brief, _claims, task_board)
            _trace_path = self._save_traceability(target_workspace, slug, _trace_md) if _trace_md else None
            if self._coverage_blocked(research_evidence):
                _cr = research_evidence.get("coverage_report") or {}
                raise ResearchGateBlocked(
                    f"domain={_domain} match_rate={_cr.get('match_rate', 0):.0%} "
                    f"missing={_cr.get('missing', [])}"
                )

        _raw_target = str(project_brief.get("target_path") or "").strip()
        doc_root = os.path.abspath(_raw_target) if (_raw_target and os.path.isabs(_raw_target)) else target_workspace
        work_item_files = generate_work_items(
            workspace=target_workspace,
            slug=slug,
            project_brief=project_brief,
            role_plan=role_plan,
            task_board=task_board,
            run_id=run_id,
            work_kind=str(project_brief.get("work_kind") or ""),
            blast_radius=str(project_brief.get("blast_radius") or ""),
        )

        # -- Plan-Critique-Verify --
        try:
            from core.plan_verifier import PlanVerifier
            _pv = PlanVerifier(workspace=target_workspace)
            _wi_items = []
            for _wi_path in work_item_files.values():
                try:
                    with open(_wi_path, encoding="utf-8") as _wf:
                        _wi_items.append({"path": _wi_path, "content": _wf.read()})
                except Exception:
                    _wi_items.append({"path": _wi_path})
            _plan_result = _pv.verify(task_input, _wi_items, project_brief)
            if not _plan_result.passed and _plan_result.issues:
                print(f"[Pipeline] plan verify issues: {_plan_result.issues[:3]}")
                for _retry in range(2):
                    _refined = _pv.refine(task_input, _wi_items, _plan_result.issues, project_brief)
                    if not _refined or _refined == _wi_items:
                        break
                    _wi_items = _refined
                    _plan_result = _pv.verify(task_input, _wi_items, project_brief)
                    if _plan_result.passed:
                        break
            print(
                f"[Pipeline] plan verify: {'PASS' if _plan_result.passed else 'WARN'} "
                f"score={_plan_result.score:.2f}"
            )
            if not _plan_result.passed:
                try:
                    from core.warning_registry import WarningRegistry as _WR
                    _WR(workspace=target_workspace).record(
                        project_slug=slug,
                        rule_id="plan_verifier_warn",
                        affected_phase="",
                        count=len(_plan_result.issues),
                        severity="warn",
                        extra={"score": _plan_result.score},
                        source_path="core/project_pipeline.py:983",
                    )
                except Exception as _pvw_exc:
                    print(f"[Pipeline] warning_registry record skip (plan_verifier_warn): {_pvw_exc}")
        except Exception as _pv_err:
            print(f"[Pipeline] plan verify skipped: {_pv_err}")

        # -- 구조 검증 --
        try:
            gate_result = self.run_structural_gate(project_brief, "work_item")
            if gate_result and gate_result.get("errors"):
                _safe_print(f"[Pipeline] structural gate warnings: {gate_result.get('errors', [])}")
        except Exception as _gate_err:
            _safe_print(f"[Pipeline] structural gate skipped: {_gate_err}")

        # -- T1 QA: work-item 문서 세트 구조 검사 --
        try:
            _wi_doc_contents = self._load_doc_contents(work_item_files)
            _wi_doc_gate = self.run_structural_gate(
                {"documents": _wi_doc_contents, "project_brief": project_brief},
                "work_item_doc_set",
            )
            if not _wi_doc_gate.get("pass"):
                _safe_print(f"[Pipeline] T1 QA work-item gate failed: {_wi_doc_gate.get('errors')}")
                # T1 retry: 1회, _refine_document로 문서 보완
                try:
                    from core.work_item_generator import _refine_document
                    _t1_feedback = "; ".join(_wi_doc_gate.get("errors") or ["구조적 품질 기준 미달"])
                    for _dname in list(_wi_doc_contents):
                        _wi_doc_contents[_dname] = _refine_document(
                            original=_wi_doc_contents[_dname],
                            feedback=_t1_feedback,
                            project_brief=project_brief,
                        )
                        if _dname in work_item_files:
                            from core.file_io import write_text
                            write_text(work_item_files[_dname], _wi_doc_contents[_dname])
                    _wi_doc_gate = self.run_structural_gate(
                        {"documents": _wi_doc_contents, "project_brief": project_brief},
                        "work_item_doc_set",
                    )
                    _safe_print(f"[Pipeline] T1 QA retry: {_wi_doc_gate.get('status')}")
                except Exception as _t1_retry_err:
                    _safe_print(f"[Pipeline] T1 QA retry skipped: {_t1_retry_err}")
        except Exception as _wi_gate_err:
            _safe_print(f"[Pipeline] T1 QA work-item gate skipped: {_wi_gate_err}")

        # -- 문서 교차검증 QA --
        cross_review_result = None
        try:
            from core.review_report import DocumentReviewSession
            _level = str(project_brief.get("pipeline_level", "dynamic"))
            if _level != "starter":
                _documents = {}
                for _doc_name, _doc_path in work_item_files.items():
                    if _doc_name.endswith(".md") and _doc_name != "approval-gate.md":
                        try:
                            with open(_doc_path, encoding="utf-8") as _df:
                                _documents[_doc_name] = _df.read()
                        except Exception:
                            pass

                if _documents:
                    _session = DocumentReviewSession(
                        workspace=target_workspace,
                        slug=slug,
                        level=_level,
                        max_rounds=2 if _level == "enterprise" else 1,
                    )
                    for _round in range(1, _session.max_rounds + 1):
                        _report = _session.run_review(
                            documents=_documents,
                            round_num=_round,
                            project_brief=project_brief,
                        )
                        _verdict = (_report.judge.verdict if _report.judge else "PASS")

                        if _verdict in ("PASS", "SKIP"):
                            _rpath = _report.save(target_workspace) if _verdict == "PASS" else ""
                            cross_review_result = {
                                "verdict": _verdict,
                                "confidence": 1.0,
                                "report_path": _rpath,
                            }
                            break

                        if _verdict == "WARN" or _round == _session.max_rounds:
                            _rpath = _report.save(target_workspace)
                            cross_review_result = {
                                "verdict": "WARN",
                                "confidence": 0.6,
                                "report_path": "",
                            }
                            break

                        if _report.judge and _report.judge.fix_instructions:
                            from core.work_item_generator import _refine_document
                            for _dtype, _instr in _report.judge.fix_instructions.items():
                                if _dtype in _documents:
                                    _documents[_dtype] = _refine_document(
                                        original=_documents[_dtype],
                                        feedback=_instr,
                                        project_brief=project_brief,
                                    )
                                    if _dtype in work_item_files:
                                        from core.file_io import write_text
                                        write_text(work_item_files[_dtype], _documents[_dtype])

                    _safe_print(f"[Pipeline] doc cross-review: {cross_review_result}")
        except Exception as _cr_err:
            _safe_print(f"[Pipeline] doc cross-review skipped: {_cr_err}")

        planning_files = [
            to_portable_path(research_evidence_path),
            to_portable_path(project_brief_path),
            to_portable_path(role_plan_path),
            to_portable_path(task_board_path),
            to_portable_path(task_execution_plan_path),
            to_portable_path(todo_path),
        ] + [to_portable_path(p) for p in work_item_files.values()]
        # P2 C3+C4: ADR/traceability 경로 추가 (domain 분기에서 생성된 경우만)
        for _extra_path in (_adr_path, _trace_path):
            if _extra_path is not None:
                planning_files.append(to_portable_path(str(_extra_path)))
        # D1: spec 파일 경로 추가
        for _sp in _spec_paths:
            planning_files.append(to_portable_path(str(_sp)))

        prepared = PreparedProject(
            run_id=run_id,
            workspace=target_workspace,
            work_item_slug=slug,
            project_brief=project_brief,
            role_plan=role_plan,
            task_board=task_board,
            planning_files=planning_files,
            work_item_files=work_item_files,
            project_brief_path=to_portable_path(project_brief_path),
            role_plan_path=to_portable_path(role_plan_path),
            task_board_path=to_portable_path(task_board_path),
            task_execution_plan_path=to_portable_path(task_execution_plan_path),
            todo_path=to_portable_path(todo_path),
            research_evidence=research_evidence,
            research_evidence_path=to_portable_path(research_evidence_path),
            doc_root=doc_root,
        )

        # T1-1: canonical checkpoint double-write (이중 쓰기 phase)
        try:
            from core.checkpoint.canonical import Checkpoint
            from core.checkpoint.storage import get_default_storage
            import hashlib as _hl
            _ext_digest = _hl.sha256(
                json.dumps({"task_input": task_input, "workspace": target_workspace}, sort_keys=True).encode()
            ).hexdigest()[:16]
            _cp = Checkpoint(
                run_id=run_id,
                step_id="prepare_documents",
                idempotency_key=Checkpoint.make_idempotency_key(slug, 0, _ext_digest),
                worktree_snapshot=Checkpoint.snapshot_worktree(target_workspace),
                next_step_cursor="orchestrate",
                test_acceptance_results={},
                project_id=project_brief.get("project_id", ""),
                metadata={
                    "prepared_project": {
                        "run_id": run_id,
                        "workspace": target_workspace,
                        "work_item_slug": slug,
                        "project_brief": project_brief,
                        "role_plan": role_plan,
                        "task_board": task_board,
                        "planning_files": planning_files,
                        "work_item_files": work_item_files,
                        "project_brief_path": to_portable_path(project_brief_path),
                        "role_plan_path": to_portable_path(role_plan_path),
                        "task_board_path": to_portable_path(task_board_path),
                        "task_execution_plan_path": to_portable_path(task_execution_plan_path),
                        "todo_path": to_portable_path(todo_path),
                        "research_evidence": research_evidence,
                        "research_evidence_path": to_portable_path(research_evidence_path),
                        "doc_root": doc_root,
                    },
                    "task_input": task_input,
                },
            )
            get_default_storage().save(_cp)
            print(f"[Checkpoint] canonical saved — run_id={run_id} cursor=orchestrate")
        except Exception as _cp_err:
            print(f"[Checkpoint] canonical save failed (non-fatal): {_cp_err}")

        return prepared

    # ------------------------------------------------------------------
    # Phase 1: prepare (하위 호환 래퍼)
    # ------------------------------------------------------------------

    def prepare(
        self,
        task_input: str,
        workspace: str,
        execution_mode: str = "approval",
        enable_build: bool = False,
        requested_role: str = "",
        route: dict | None = None,
    ) -> PreparedProject:
        """하위 호환 래퍼 — prepare_brief() + prepare_documents() 순차 호출.

        Clarification 없이 바로 진행하는 기존 동작을 유지한다.
        """
        brief = self.prepare_brief(
            task_input=task_input,
            workspace=workspace,
            execution_mode=execution_mode,
            enable_build=enable_build,
            requested_role=requested_role,
            route=route,
        )
        return self.prepare_documents(brief, execution_mode=execution_mode, enable_build=enable_build)

    # ------------------------------------------------------------------
    # Phase 2: execute
    # ------------------------------------------------------------------

    def execute(
        self,
        prepared: PreparedProject,
        enable_build: bool = False,
        execution_mode: str = "approval",
    ) -> dict:
        """
        Phase 2: 승인된 프로젝트를 실행한다.

        실행 전 검사:
          1. gate.is_execution_open() — execution_open: true 확인
          2. gate.check_validity()   — 승인 후 문서 변경 없음 확인
        통과 후:
          3. work-item 편집 내용을 task_board 에 반영
          4. 역할 구체화 (YAML 에이전트 파일 생성)
          5. DynamicOrchestrator.run_project() 실행
        """
        workspace = prepared.workspace
        gate = prepared.gate()

        # B2: canonical checkpoint guard — 이미 완료된 run은 재실행하지 않는다
        try:
            from core.checkpoint.storage import get_default_storage as _get_store
            _cp = _get_store().load(prepared.run_id)
            if _cp and _cp.next_step_cursor == "done":
                logger.info("[execute] run_id=%s already done — skipping", prepared.run_id)
                return {
                    "run_id": prepared.run_id,
                    "pipeline": "project",
                    "ok": True,
                    "reason": "already_done",
                    "work_item_slug": prepared.work_item_slug,
                }
        except Exception:
            pass

        # -- 승인 확인 (W3: is_execution_open이 check_validity를 내부 실행, 변경 시 자동 invalidate) --
        if not gate.is_execution_open():
            return {
                "ok": False,
                "reason": "approval_required",
                "message": "approval-gate.md 를 승인한 후 실행하세요.",
                "gate_path": gate.gate_path,
            }

        # P2: escalation block 체크 (승인 체크 직후)
        blocked, block_decision = gate.read_block_decision()
        if blocked:
            _bd = block_decision or {}
            return {
                "ok": False,
                "reason": "escalation_block",
                "blocking_rules": _bd.get("blocking_rules", []),
                "decision_report": os.path.join(
                    prepared.workspace, "runtime", "warnings",
                    prepared.work_item_slug, "_decision.md",
                ),
                "message": "escalation 차단. _decision.md 를 확인하고 e2e_command 보강 또는 warning-override 후 재실행하세요.",
            }

        # -- 편집 내용 반영 --
        # target_path 설정 시 문서는 doc_root에 있으므로 workspace가 아닌 doc_root 사용
        doc_root = prepared._effective_doc_root()
        updated_board = sync_board_from_work_items(
            workspace=doc_root,
            slug=prepared.work_item_slug,
            existing_board=prepared.task_board,
        )
        write_project_board(workspace, updated_board)

        # -- 역할 구체화 --
        roles, installed_map = self._materialize_roles(
            role_plan=prepared.role_plan,
            project_brief=prepared.project_brief,
            workspace=workspace,
            execution_mode=execution_mode,
            enable_build=enable_build,
            run_id=prepared.run_id,
        )

        # -- 에이전트 실행 --
        from core.model_router import print_startup_routing_notice
        print_startup_routing_notice()

        # execution_mode=ise: AF_ISE_ENABLED가 명시적으로 꺼져 있어도 강제 활성화
        # (기본값은 "1"이므로 대부분의 경우 no-op; AF_ISE_ENABLED=0 환경에서만 차이)
        if execution_mode == "ise" and os.environ.get("AF_ISE_ENABLED", "1") == "0":
            os.environ["AF_ISE_ENABLED"] = "1"
            print_agent_msg("Pipeline", "execution_mode=ise → AF_ISE_ENABLED 강제 활성화", "🌀")

        task_input = str(prepared.project_brief.get("goal") or "")
        orchestrator = DynamicOrchestrator(
            self.mr, max_concurrent=5, terminal_per_agent=True,
            broker=self._broker, visualizer=self._visualizer,
            run_id=prepared.run_id,
        )
        run_board = orchestrator.run_project(task_input, roles, workspace)
        status = str(run_board.get("current_status", "unknown"))

        # ── strategy ledger: 모듈별 outcome 기록 (B2-6) ──────────────
        self._record_ledger_outcomes(
            status=status,
            role_plan=prepared.role_plan,
            workspace=workspace,
            project_slug=prepared.work_item_slug,
        )

        append_dashboard_run(
            {
                "ts": now_iso(),
                "type": "project_run",
                "project_id": os.path.basename(workspace),
                "task": task_input[:300],
                "ok": status == "completed",
                "reason": status,
                "pipeline": "project",
                "roles": roles,
                "planning_files": prepared.planning_files,
                "work_item_slug": prepared.work_item_slug,
            }
        )

        # T1-1: canonical checkpoint → done (run 완료 표시)
        try:
            from core.checkpoint.storage import get_default_storage
            _existing = get_default_storage().load(prepared.run_id)
            if _existing:
                from datetime import datetime, timezone
                _existing.next_step_cursor = "done"
                _existing.saved_at = datetime.now(timezone.utc).isoformat()
                _existing.test_acceptance_results["orchestrator_status"] = status
                get_default_storage().save(_existing)
        except Exception as _done_err:
            logger.warning("[execute] done-checkpoint save failed (run_id=%s): %s", prepared.run_id, _done_err)

        return {
            "run_id": prepared.run_id,
            "pipeline": "project",
            "ok": status == "completed",
            "reason": status,
            "roles": roles,
            "installed_skills": installed_map,
            "work_item_slug": prepared.work_item_slug,
            "work_item_dir": prepared.work_item_dir(),
            "planning_files": prepared.planning_files,
            "board": run_board,
            # 하위 호환 — 기존 코드가 직접 키로 접근하는 경우를 위해
            "project_brief_path": prepared.project_brief_path,
            "role_plan_path": prepared.role_plan_path,
            "task_board_path": prepared.task_board_path,
            "task_execution_plan_path": prepared.task_execution_plan_path,
            "todo_path": prepared.todo_path,
            "research_evidence_path": prepared.research_evidence_path,
        }

    def _record_ledger_outcomes(
        self,
        status: str,
        role_plan: dict,
        workspace: str,
        project_slug: str = "",
    ) -> None:
        """프로젝트 실행 후 strategy ledger에 모듈별 outcome을 기록한다.

        - status in {crashed, unknown} → 전체 skip
        - 그 외: board 로드 → 모듈별 module_outcome_from_board + detect_owner_drift 판정
        """
        _INFRA_STATUSES = {"crashed", "unknown"}
        if status in _INFRA_STATUSES:
            logger.info("strategy ledger 기록 skip — 인프라/불확실 실패 (status=%s)", status)
            return

        try:
            from core.memory_system.strategy_ledger import get_strategy_ledger
            from core.project_task_board import (
                load_project_board,
                module_outcome_from_board,
                detect_owner_drift,
                _build_board_maps,
            )
        except Exception as exc:
            logger.warning("strategy ledger/board import 실패: %s", exc)
            return

        board = load_project_board(workspace)
        if not board:
            logger.info("strategy ledger 기록 skip — board 비어있음")
            return

        task_map, module_map = _build_board_maps(board)

        ledger = get_strategy_ledger(workspace)
        project_id = project_slug or os.path.basename(workspace)

        batch: list[tuple[str, str, str, bool]] = []
        seen: set[tuple[str, str]] = set()

        for mod in (role_plan.get("modules") or []):
            owner = str(mod.get("owner_role") or "")
            if not owner:
                continue
            mid = str(mod.get("id") or "")
            if mid not in module_map:
                continue

            outcome_label = module_outcome_from_board(
                board, mid, task_map=task_map, module_map=module_map,
            )
            if outcome_label == "completed":
                outcome = True
            elif outcome_label == "at_risk":
                outcome = False
            else:
                continue

            board_module = module_map.get(mid)
            mismatches = detect_owner_drift(board_module, board, task_map=task_map) if board_module else []
            if mismatches:
                logger.warning(
                    "strategy ledger skip — owner drift 감지 (module=%s, plan_owner=%s)",
                    mid, owner,
                )
                try:
                    from core.warning_registry import WarningRegistry as _WR
                    _WR(workspace=workspace).record(
                        project_slug=project_id,
                        rule_id="owner_role_mismatch",
                        count=len(mismatches),
                        affected_phase="build",
                        severity="warn",
                        affected_ids=[mid] + [tid for tid, _, _ in mismatches],
                        extra={"mismatches": [
                            {"task_id": tid, "expected": exp, "actual": act}
                            for tid, exp, act in mismatches
                        ]},
                        source_path="core/project_pipeline.py:1455",
                    )
                except Exception as _owr_exc:
                    logger.debug("warning_registry record skip (owner_role_mismatch): %s", _owr_exc)
                continue

            for raw in [str(mod.get("name") or "")] + list(mod.get("deliverables") or []):
                words = str(raw).strip().lower().split()
                dp = " ".join(words[:4]).strip()
                if dp and (dp, owner) not in seen:
                    seen.add((dp, owner))
                    batch.append((dp, owner, project_id, outcome))

        if batch:
            try:
                ledger.record_role_batch(batch)
            except Exception as exc:
                logger.warning("strategy ledger 배치 기록 실패: %s", exc)

    # ------------------------------------------------------------------
    # 하위 호환: run() = prepare + 자동 승인 + execute
    # ------------------------------------------------------------------

    def run(
        self,
        task_input: str,
        workspace: str,
        execution_mode: str = "approval",
        enable_build: bool = False,
        requested_role: str = "",
        route: dict | None = None,
    ) -> dict:
        """
        하위 호환 메서드.

        기존 코드에서 run() 을 직접 호출하면 자동 승인으로 동작한다.
        CLI 에서는 prepare() → 사용자 승인 → execute() 흐름을 사용한다.
        """
        prepared = self.prepare(
            task_input=task_input,
            workspace=workspace,
            execution_mode=execution_mode,
            enable_build=enable_build,
            requested_role=requested_role,
            route=route,
        )
        # 자동 승인 (하위 호환) — gate 파일 없으면 먼저 초기화
        _gate = prepared.gate()
        if not os.path.exists(_gate.gate_path):
            _gate.initialize(prepared.work_item_slug, run_id=prepared.run_id)
        _gate.approve(approver="auto", run_id=prepared.run_id)

        return self.execute(
            prepared=prepared,
            enable_build=enable_build,
            execution_mode=execution_mode,
        )
