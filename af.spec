# -*- mode: python ; coding: utf-8 -*-

import os
import sys

from PyInstaller.utils.hooks import collect_submodules  # noqa: E402

ROOT = os.path.dirname(os.path.abspath(SPEC))  # noqa: F821 – PyInstaller provides SPEC

block_cipher = None

# 설계문서 §4.6.2: typer/rich/nlm은 lazy import가 많아 상단 hiddenimports만으로는
# sub-module 누락 가능. PyInstaller 6.x는 .spec과 CLI `--collect-submodules`를
# 함께 쓸 수 없으므로 spec 안에서 직접 collect_submodules()로 안전망을 건다.
_auto_hiddenimports = []
for pkg in ("typer", "rich", "nlm"):
    try:
        _auto_hiddenimports.extend(collect_submodules(pkg))
    except Exception:
        # 빌드 환경에 해당 패키지가 없으면 명시 hiddenimports만으로 진행
        pass

a = Analysis(
    ['run_factory_cli.py'],
    pathex=[ROOT],
    binaries=[],
    datas=[
        ('skills', 'skills'),
        ('config', 'config'),
        ('policy.yaml', '.'),
    ],
    hiddenimports=[
        # ── core ──
        'core.agent_runner',
        'core.agent_worker',
        'core.agent_specializer',
        'core.approval_gate',
        'core.ast_engine',
        'core.ast_memory_hub',
        'core.bootstrap_roles',
        'core.builder',
        'core.capability_intent',
        'core.concurrency',
        'core.config_paths',
        'core.control_plane_llm',
        'core.context_window_manager',
        'core.dashboard',
        'core.destructive_guard',
        'core.document_chunker',
        'core.document_index',
        'core.documentation_policy',
        'core.dynamic_orchestrator',
        'core.engine_auth',
        'core.evaluator',
        'core.executor',
        'core.failure_classifier',
        'core.external_skill_candidate_importer',
        'core.external_skill_source_ids',
        'core.external_skill_sources',
        'core.file_io',
        'core.file_lock',
        'core.fsa_loop',
        'core.lineage_ledger',
        'core.git_manager',
        'core.hashline_editor',
        'core.ingestion_pipeline',
        'core.install_candidate_utils',
        'core.intent',
        'core.interactive_chat',
        # ── ISE (Phase A Step 1b: --mode ise 배선을 위해 PyInstaller hidden import 명시) ──
        'core.ise_analyzer',
        'core.ise_loop',
        'core.ise_redesigner',
        'core.ise_stall_detector',
        'core.ise_strategy_ledger',
        'core.knowledge_skill',
        'core.langchain_adapter',
        'core.llm_engine',
        'core.lsp_bridge',
        'core.manager',
        'core.mcp_adapter',
        'core.memory',
        'core.message_broker',
        'core.model_router',
        'core.policy',
        'core.policy_runtime',
        'core.project_init',
        'core.project_mailbox',
        'core.project_pipeline',
        'core.project_task_board',
        'core.registry',
        'core.registry_manager',
        'core.role_decomposer',
        'core.run_budget',
        'core.runner',
        'core.security_guard',
        'core.security_scanner',
        'core.semantic_embedder',
        'core.skill_autodiscover',
        'core.skill_cache',
        'core.skill_context_config',
        'core.skill_creator',
        'core.skill_enricher',
        'core.skill_eval_harness',
        'core.skill_quality_gate',
        'core.skill_evolution_bus',
        'core.skill_feedback',
        'core.skill_forge',
        'core.skill_loader',
        'core.skill_metadata',
        'core.skill_metadata_adapter',
        'core.skill_preflight',
        'core.skill_procurer',
        'core.skill_promotion',
        'core.skill_registry',
        'core.skill_retrieval_engine',
        'core.skill_spec_synthesizer',
        'core.swarm_council',
        'core.synergy_runner',
        'core.setup_wizard',
        'core.template_input',
        'core.terminal_bridge',
        'core.tool_runtime',
        'core.utils',
        'core.web_search',
        'core.work_item_generator',
        'core.work_item_parser',
        'core.plan_verifier',
        # ── core.continuity ──
        'core.continuity',
        'core.continuity.manifest_store',
        'core.continuity.resume_brief',
        'core.continuity.runtime_paths',
        # ── core.hooks ──
        'core.hooks.base',
        'core.hooks.checkpoint',
        'core.hooks.context_fork',
        'core.hooks.event_bus',
        'core.hooks.guardrails',
        'core.hooks.human_interrupt',
        'core.hooks.langsmith_tracing',
        'core.hooks.lsp_check',
        'core.hooks.memory_consolidation',
        'core.hooks.skill_self_evolution',
        'core.hooks.code_review_doc',
        'core.hooks.design_review_hook',
        'core.design_review_utils',
        'core.review_report',
        'core.review_runner',
        'core.pipeline_quality',
        # ── core.memory_system ──
        'core.memory_system',
        'core.memory_system.models',
        'core.memory_system.facade',
        'core.memory_system.config',
        'core.memory_system.cross_project',
        'core.memory_system.decay',
        'core.memory_system.episode_extractor',
        'core.memory_system.episode_matcher',
        'core.memory_system.strategy_ledger',
        'core.memory_system.graph_builder',
        'core.memory_system.graph_query',
        'core.memory_system.issue_tracker',
        'core.memory_system.knowledge_forger',
        'core.memory_system.knowledge_injection',
        'core.memory_system.project_lifecycle',
        'core.memory_system.router',
        'core.memory_system.adapters',
        'core.memory_system.adapters.base',
        'core.memory_system.adapters.ast_hub',
        'core.memory_system.adapters.continuity',
        'core.memory_system.adapters.core_memory',
        'core.memory_system.adapters.cortex_vector',
        'core.memory_system.adapters.knowledge_graph',
        'core.memory_system.adapters.sync_compyne',
        'core.memory_system.adapters.trace_log',
        # ── core.providers ──
        'core.providers',
        # ── NotebookLM CLI (import name: nlm) — 설계문서 §4.6.2 ──
        'nlm',
        'nlm.__main__',
        'nlm.ai_docs',
        'nlm.cli',
        'nlm.cli.alias',
        'nlm.cli.auth',
        'nlm.cli.chat',
        'nlm.cli.config',
        'nlm.cli.main',
        'nlm.cli.notebook',
        'nlm.cli.repl',
        'nlm.cli.research',
        'nlm.cli.source',
        'nlm.cli.studio',
        'nlm.core',
        'nlm.core.alias',
        'nlm.core.auth',
        'nlm.core.auth_refresh',
        'nlm.core.client',
        'nlm.core.constants',
        'nlm.core.exceptions',
        'nlm.core.models',
        'nlm.output',
        'nlm.output.formatters',
        'nlm.utils',
        'nlm.utils.browser',
        'nlm.utils.cdp',
        'nlm.utils.config',
        # ── Typer/Rich 체인 (top-level; build_exe.py가 --collect-submodules로 보강) ──
        'typer',
        'rich',
        'shellingham',
        'websocket',          # websocket-client
        'annotated_doc',
        # ── 파일락 (BLOCK-A: .af_setup_state.json 동시 실행 경쟁 방지) ──
        'filelock',
        # ── Tavily (외부 검색) ──
        'tavily',
        # ── third-party ──
        'yaml',
        'anthropic',
        # 'google.generativeai',  # Phase B3 (2026-04-14) 제거:
        #   - skills/core/cortex.py를 신 SDK(google.genai)로 마이그레이션 완료
        #   - 바이너리에서 구 SDK 제거 → googleapiclient 전체(94MB) 이미 B1에서
        #     filter됐으나 hiddenimport 제거로 구 SDK 부속 모듈도 bundle에서 배제
        #   - venv uninstall은 의도적으로 보류 (agents/*/tools/cortex.py 런타임 호환)
        'google.genai',
        'openai',
        'langsmith',
        'langchain',
        'langchain_core',
        # 'langchain_community',  # Phase B2 (2026-04-14) 제거:
        #   - langchain 1.0 업그레이드 후 Required-by 없음 (orphan)
        #   - 우리 코드에서 import 0건 (grep 검증)
        #   - numpy/langchain-classic/SQLAlchemy 등 약 40MB 간접 의존 제거 목적
        'tiktoken',
        'tiktoken_ext',
        'tiktoken_ext.openai_public',
        'chromadb',
        'sentence_transformers',
        'pydantic',
        'pydantic.v1',
        'httpx',
        'httpcore',
        'charset_normalizer',
        'certifi',
        'idna',
        'anyio',
        'sniffio',
    ] + _auto_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ── Phase B1 (2026-04-14): googleapiclient/discovery_cache/documents 전량 제거 ──
# 근거: 우리 주 경로는 신 SDK(google.genai, REST/gapic 직접). 구 SDK는
# skills/core/cortex.py의 embed_content() 하나뿐이며 discovery_cache를 쓰지 않음.
# cross-review 확인: 580개 JSON 중 generativelanguage.*.json 자체가 없음 → 전량 제거
# 동치. 방어적으로 drive/customsearch/gmail만은 남겨둬서 LangChain Google 툴
# 실수 호출 시 ImportError가 나도록 하지 않고 UnknownApiNameOrVersion 으로 낮춤.
_DISCOVERY_PATTERNS = (
    "googleapiclient/discovery_cache/documents",
    "googleapiclient\\discovery_cache\\documents",  # Windows 경로
)
_DEFENSIVE_KEEP = (
    "drive.v3.json",
    "customsearch.v1.json",
    "gmail.v1.json",
)


def _is_discovery_doc(dest: str) -> bool:
    return any(p in dest for p in _DISCOVERY_PATTERNS)


def _should_keep(dest: str) -> bool:
    return any(dest.endswith(k) for k in _DEFENSIVE_KEEP)


_before = len(a.datas)
a.datas = [d for d in a.datas if not _is_discovery_doc(d[0]) or _should_keep(d[0])]
_removed = _before - len(a.datas)
print(f"[af.spec B1] discovery_cache 필터: -{_removed}개 파일 제거 (방어 whitelist: {list(_DEFENSIVE_KEEP)})")

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='af',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='af',
)
