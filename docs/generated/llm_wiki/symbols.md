---
generated_at: 2026-06-19T20:52:50+09:00
source_commit: 47e7c16a
sources:
  - "Master_Blueprint.md"
  - "docs/code_review/code-review.md"
  - "NEXT_STEPS.md"
  - "scripts/codebase_symbols.py"
  - "**/*.py"
  - "**/*.cs"
---

> Source: scripts/codebase_symbols.py (AST 추출, read-only)
> 관련: [[index]] | [[architecture]] | [[source_refs]]

# Codebase Symbols

## `af.py`

**Functions:**
- `_forward_args`
- `main`

## `agent_launcher.py`

**Classes:**
- `AgentFactory`

**Functions:**
- `_configure_cli_text_streams`
- `_utf8_subprocess_env`
- `_git_modified_files`
- `_scope_guard_report`
- `_maybe_isolate_project_root_for_self_run`
- `_safe_write_json`
- `_detect_mode`
- `_build_arg_parser`

## `agents/backend-architect-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/backend-dev-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/backend-dev-agent/tools/database_performance_tuning.py`

_(no top-level symbols)_

## `agents/backend-dev-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/backend-dev-agent/tools/scalable_api_architecture.py`

_(no top-level symbols)_

## `agents/backend-dev-agent/tools/zero_downtime_deployment_playbook.py`

_(no top-level symbols)_

## `agents/calculus-tutor-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/chef-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/chef-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/chef-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/general-assistant-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/general-assistant-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/himari-test-agent-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/iguro_obanai/tools/api_security_vetting.py`

**Functions:**
- `vet_api`
- `main`

## `agents/iguro_obanai/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/iguro_obanai/tools/db_optimizer.py`

**Functions:**
- `optimize_db`
- `main`

## `agents/iguro_obanai/tools/infrastructure_scaler.py`

**Functions:**
- `scale_report`
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/japanese-restaurant-master-chef-agent/tools/edomae_sushi_shikomi_playbook.py`

**Functions:**
- `get_available_ingredients`
- `find_recipe_steps`
- `handle_prepare`
- `handle_status`
- `handle_recipe`
- `handle_report`
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/omakase_service_pacing_control.py`

_(no top-level symbols)_

## `agents/japanese-restaurant-master-chef-agent/tools/perishable_inventory_control.py`

**Functions:**
- `load_inventory`
- `save_inventory`
- `add_item`
- `update_item`
- `remove_item`
- `list_items`
- `alert_items`
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/precision_knife_techniques.py`

**Classes:**
- `MasterChef`

**Functions:**
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/japanese-restaurant-master-chef-agent/tools/seasonal_ingredient_procurement.py`

**Functions:**
- `load_history`
- `save_history`
- `handle_recommend`
- `handle_order`
- `handle_history`
- `main`

## `agents/japanese-restaurant-master-chef-agent/tools/seasonal_omakase_inventory_optimization.py`

_(no top-level symbols)_

## `agents/lilith-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/lilith-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/lilith-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/marketer-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/marketer-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/marketer-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/stock-analyst-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/system-admin-(uses-run_command-tool)-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/system-admin-(uses-run_command-tool)-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/system-admin-(uses-run_command-tool)-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/system-admin-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `agents/system-admin-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/system-admin-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `agents/test-agent-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/test-assistant-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agents/web-app-specialist-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `agt.py`

**Functions:**
- `main`

## `antigravity_link.py`

**Classes:**
- `SmartLinker`

**Functions:**
- `resolve_python_exec`
- `safe_id`
- `safe_key`
- `_truncate`
- `resolve_global_memory_dir`
- `mirror_global_memory`
- `handle_command`
- `main`

## `artifacts/db_customization_loader.py`

**Functions:**
- `load_db`
- `to_dict_rows`
- `q_all`
- `q_one`
- `fmt_to_strptime`
- `transform_value`
- `validate_row`
- `extract_records`
- `compute_business_key`
- `main`

## `build_exe.py`

**Functions:**
- `_get_version`
- `main`

## `cdx.py`

**Functions:**
- `_log`
- `main`

## `check_rel.py`

**Functions:**
- `check_releases`

## `config/schema.py`

**Classes:**
- `EngineConfig`
- `SkillConfig`
- `ExperimentalConfig`
- `BackgroundTasksConfig`
- `HooksConfig`
- `LanguagePolicyConfig`
- `PolicyConfig`
- `AgentFactoryConfig`

**Functions:**
- `load_factory_config`

## `core/agent_reservation.py`

**Classes:**
- `AgentLease`
- `AgentReservationManager`

## `core/agent_runner.py`

**Classes:**
- `FallbackRejectedError`
- `AgentRunner`

**Functions:**
- `_safe_print`
- `_run_async_safe`

## `core/agent_specializer.py`

**Classes:**
- `AgentSpecializer`

## `core/agent_worker.py`

**Functions:**
- `_configure_text_streams`
- `main`

## `core/approval_gate.py`

**Classes:**
- `ApprovalGate`

**Functions:**
- `_sanitize_reason`
- `_auto_approve_env_active`
- `_emit_approval_event`
- `_read_domain_review_verdict`
- `_parse_domain_review`
- `_sha256_file`
- `_clean`

## `core/architect_agent.py`

**Functions:**
- `_load_blueprint_text`
- `_extract_section`
- `_section_for_step`
- `_load_accepted_adrs`
- `_adr_matches`
- `_resolve_finding`
- `_patch_final_plan`
- `architect_fn`

## `core/ast_engine.py`

**Functions:**
- `detect_lang`
- `_ensure_available`
- `search`
- `replace`
- `search_file`
- `replace_file`
- `search_dir`
- `replace_dir`

## `core/ast_memory_hub.py`

**Classes:**
- `AstMemoryHub`

## `core/bootstrap_roles.py`

**Classes:**
- `ProjectPlanningDirector`

**Functions:**
- `_load_task_decomposition_policy`
- `_build_policy_rules`
- `build_bootstrap_agent`

## `core/builder.py`

**Classes:**
- `SandboxedBuilder`

## `core/capability_intent.py`

**Classes:**
- `CapabilityNeed`
- `CapabilityIntentAnalyzer`

**Functions:**
- `dedupe_strings`
- `dedupe_capabilities`
- `normalize_risk`
- `tokenize`
- `token_overlap`

## `core/checkpoint/__init__.py`

_(no top-level symbols)_

## `core/checkpoint/canonical.py`

**Classes:**
- `Checkpoint`

**Functions:**
- `_utcnow`

## `core/checkpoint/storage.py`

**Classes:**
- `CheckpointStorage`
- `FileCheckpointStorage`

**Functions:**
- `get_default_storage`
- `get_storage_for`

## `core/clarification.py`

**Functions:**
- `_safe_json_load`
- `generate_clarification_questions`
- `should_skip_clarification`
- `merge_clarification`
- `auto_apply_defaults`
- `synthesize_research_answers`
- `synthesize_via_research`

## `core/cli_session_cleanup.py`

**Functions:**
- `cleanup_stale_sessions`

## `core/completion_contract.py`

**Classes:**
- `GoalEvidence`
- `GoalEntry`
- `TestManifest`
- `GoalContract`
- `HarnessResult`
- `ExecutionHarness`
- `AcceptanceGate`

**Functions:**
- `_infer_harness_type`
- `_extract_command`
- `parse_acceptance_criteria`
- `build_evidence_ledger`

## `core/concurrency.py`

**Classes:**
- `TaskCircuitBreaker`
- `BackgroundTask`
- `BackgroundTaskManager`

## `core/config_paths.py`

**Functions:**
- `_boot_safe_id`
- `_config_value`

## `core/consensus_engine.py`

**Classes:**
- `ConsensusEngine`

## `core/context_window_manager.py`

**Classes:**
- `ContextBudget`
- `ToolTracker`
- `HistoryEntry`
- `HistoryManager`
- `KnowledgeInjector`
- `ContextWindowManager`

**Functions:**
- `estimate_tokens`

## `core/continuity/__init__.py`

_(no top-level symbols)_

## `core/continuity/manifest_store.py`

**Classes:**
- `OrchestratorManifestStore`

**Functions:**
- `_now_iso`

## `core/continuity/resume_brief.py`

**Functions:**
- `_now_iso`
- `_load_json`
- `_load_manifest`
- `_open_todos`
- `_sort_session_state`
- `_latest_session_state`
- `_format_task`
- `build_resume_brief`
- `write_resume_brief`
- `read_resume_brief_excerpt`

## `core/continuity/runtime_paths.py`

**Functions:**
- `workspace_runtime_dir`
- `workspace_runtime_file`

## `core/control/__init__.py`

_(no top-level symbols)_

## `core/control/change_impact.py`

**Classes:**
- `ImpactProfile`
- `ChangeImpactProfiler`

## `core/control/context_scanner.py`

**Classes:**
- `LightContextScanner`

**Functions:**
- `_dir_hash`

## `core/control/continuity_snapshot.py`

**Classes:**
- `ContinuitySnapshot`
- `ContinuitySnapshotBuilder`

## `core/control/execution_policy.py`

**Classes:**
- `ExecutionPolicy`
- `ExecutionPolicyResolver`

## `core/control/intake.py`

**Classes:**
- `NormalizedRequest`
- `ControlPlaneIntake`

## `core/control/issue_context.py`

**Classes:**
- `IssueContext`
- `IssueContextManager`

## `core/control/lifecycle_bridge.py`

**Classes:**
- `CanonicalEvent`
- `CanonicalLifecycleBridge`

## `core/control/maintenance_pipeline.py`

**Classes:**
- `MaintenancePipeline`

## `core/control/maintenance_state.py`

**Classes:**
- `StateRecord`
- `MaintenanceStateMachine`

## `core/control/question_router.py`

**Classes:**
- `Question`
- `QuestionResult`
- `QuestionBatchResult`
- `QuestionRouterLLMCaller`
- `BriefBackedQuestionCaller`
- `QuestionRouter`

**Functions:**
- `load_question_schema`
- `_validate_schema`
- `parse_questions`

## `core/control/regression_gate.py`

**Classes:**
- `RegressionSafetyGate`

## `core/control/rollback.py`

**Classes:**
- `RollbackPlan`
- `RollbackManager`

## `core/control/run_ledger.py`

**Classes:**
- `LedgerEntry`
- `RunLedger`

## `core/control/stage_artifacts.py`

**Classes:**
- `ContextScanArtifact`
- `ProjectGoalArtifact`
- `PausedHitlQuestion`
- `DomainReviewArtifact`
- `AssumptionLedgerEntry`
- `PausedHitlArtifact`

## `core/control/stage_router.py`

**Classes:**
- `StageRouter`

**Functions:**
- `_atomic_write_text`
- `_render_project_goal`
- `_render_domain_review`
- `_render_context_scan`
- `_render_paused_hitl`
- `_to_list`

## `core/control/supervisor.py`

**Classes:**
- `RuntimeSupervisor`

## `core/control/verdicts.py`

**Classes:**
- `QuestionRoute`
- `DomainVerdict`
- `BlockCause`

## `core/control/work_kind.py`

**Classes:**
- `WorkKindClassifier`

## `core/control_plane_llm.py`

**Classes:**
- `ControlPlaneLLM`

**Functions:**
- `_parse_json_from_text`

## `core/conversation_manager.py`

**Classes:**
- `ConversationResult`
- `TranscriptStore`
- `ConversationManager`

**Functions:**
- `infer_turn_type_from_text`

## `core/conversation_prompts.py`

**Functions:**
- `build_conversation_prompt`
- `build_moderator_decision_prompt`
- `build_consensus_check_prompt`
- `_format_initial_context`

## `core/conversation_room.py`

**Classes:**
- `ConversationBudget`
- `ConversationTurn`
- `ConsensusResult`
- `ConversationRoom`

## `core/conversation_task_adapter.py`

**Classes:**
- `ConversationToTaskAdapter`

**Functions:**
- `_normalize`
- `_to_snake`

## `core/critic_skill_router.py`

**Functions:**
- `map_paths_to_skills`
- `resolve_skill_paths`
- `main`

## `core/cross_verification.py`

**Classes:**
- `VerificationResult`
- `JudgmentResult`
- `CrossVerificationLoop`

**Functions:**
- `run_cross_verification`

## `core/dashboard.py`

**Functions:**
- `_current_dashboard_config`
- `_normalize_dashboard_path`
- `_normalize_dashboard_entry`
- `append_dashboard_run`
- `_append_dashboard_run_locked`
- `_safe_write_json`
- `validate_context_with_schema`

## `core/design_review_utils.py`

**Functions:**
- `normalize_path`
- `_matches_glob`
- `is_design_doc`
- `is_code_file`
- `check_code_review_budget`
- `increment_code_review_count`
- `pathhash`
- `_get_pending_dir`
- `enqueue`
- `_process_alive`
- `_is_watcher_alive`
- `_update_heartbeat`
- `_start_watcher`
- `_try_acquire_spawn_lock`
- `_release_spawn_lock`
- `ensure_watcher`
- `_count_pending`
- `show_status`
- `run_sync`

## `core/destructive_guard.py`

**Functions:**
- `inject_destructive_guard_contract`
- `merge_claude_destructive_guard`
- `write_gemini_destructive_policy`
- `attach_gemini_policy_path`
- `blocked_command_message`
- `detect_destructive_shell_text`
- `detect_destructive_process`

## `core/document_chunker.py`

**Classes:**
- `DocumentChunk`
- `DocumentChunker`

**Functions:**
- `make_virtual_chunk`

## `core/document_index.py`

**Classes:**
- `SearchResult`
- `_SparseIndex`
- `_DenseIndex`
- `DocumentIndex`

**Functions:**
- `_tokenize`
- `_cosine_similarity`

## `core/document_policy.py`

**Functions:**
- `scan_forbidden_tokens`
- `parse_frontmatter_exempt`
- `jaccard_similarity`

## `core/documentation_policy.py`

**Functions:**
- `_now_iso`
- `_normalize_language_code`
- `get_document_language_code`
- `documentation_language_profile`
- `project_todo_title`
- `resume_brief_strings`
- `_architecture_doc_template`
- `_change_history_template`
- `ensure_documentation_files`
- `documentation_todo_items`
- `normalize_project_todo_items`
- `_normalize_instruction`
- `_mark_for_status`
- `_instruction_status_map`
- `write_project_todo`
- `single_task_todo_items`
- `inject_thinking_contract`
- `inject_documentation_contract`
- `inject_code_review_contract`
- `inject_cross_validation_contract`

## `core/dogfood.py`

**Classes:**
- `DogfoodPhase`
- `GitWorktreeError`
- `TriadContractError`
- `DogfoodState`
- `MergePolicy`
- `VerifyResult`
- `ReviewDecision`

**Functions:**
- `_validate_run_id`
- `_default_command_runner`
- `_build_ai_task`
- `_record_run_budget`
- `_run_budget_exhausted`
- `_default_ai_executor`
- `_utf8_subprocess_env`
- `_dogfood_root`
- `_default_runtime_workspace`
- `_default_worktree_workspace`
- `_state_path`
- `_snapshot_run_budget`
- `_restore_run_budget`
- `save_state`
- `load_state`
- `create_run`
- `advance_phase`
- `block_run`
- `retry_run`
- `_git`
- `_git_bytes`
- `_is_crlf_only_diff`
- `_dirty_files`
- `_safe_to_cleanup_partial_isolation`
- `_cleanup_partial_isolation`
- `_branch_exists`
- `_remove_worktree_only`
- `_handle_blocked_worktree`
- `prepare_isolated_worktree`
- `_run_final_docs_sync`
- `finalize_dogfood_result`
- `_check_merge_policy`
- `build_merge_policy`
- `merge_dogfood_branch`
- `_build_interview_fn`
- `_run_interview_phase`
- `_run_research_brief_phase`
- `_research_load_interview`
- `_research_scope_files`
- `_research_collect_refs`
- `_run_research_phase`
- `_run_spec_phase`
- `_run_premortem_phase`
- `_run_plan_phase`
- `_run_isolate_phase`
- `_fingerprint_untracked`
- `_run_implement_phase`
- `_develop_isolation_env`
- `_changed_files_fallback`
- `_derive_verify_cmds`
- `_normalize_develop_result`
- `_intended_scope`
- `_record_route_decision`
- `_light_allowed`
- `_run_develop_full`
- `_run_develop_light`
- `_run_develop_phase`
- `_run_verify_phase`
- `_run_review_phase`
- `_run_finalize_phase`
- `_run_merge_phase`
- `run_all`
- `run_phase`
- `_artifact_path`
- `atomic_write_json`
- `load_policy_json`
- `_estimate_tokens`
- `_keys`
- `_critical_counts`
- `_append_phase_trace`
- `read_phase_trace`
- `_strict_contract_failure`
- `_plan_python_paths`
- `_pre_implement_static_smoke`
- `_spec_from_dict`
- `_premortem_from_dict`

## `core/dynamic_orchestrator.py`

**Classes:**
- `DynamicOrchestrator`

## `core/engine_auth.py`

**Functions:**
- `_truthy_env`
- `_has_required_credentials`
- `_config_value`
- `_configured_cli_providers`
- `engine_api_keys_disabled`
- `supports_cli_bootstrap`
- `auto_configure_cli_provider`
- `check_llm_available`
- `get_engine_api_key`

## `core/escalation_decision_report.py`

**Functions:**
- `write_decision_report`
- `write_error_decision`
- `_write_decision_json`
- `_write_decision_md`
- `_extract_phase_from_decision_reason`
- `_atomic_write_json`
- `_atomic_write_text`

## `core/escalation_evaluator.py`

**Classes:**
- `EscalationDecision`
- `RunDecision`
- `_PolicyRule`

**Functions:**
- `load_policy`
- `read_current_phase`
- `_find_rule`
- `_is_phase_active`
- `evaluate`
- `compute_run_decision`

## `core/evaluator.py`

**Classes:**
- `StrategyEvaluator`

## `core/events/__init__.py`

_(no top-level symbols)_

## `core/events/run_event.py`

**Classes:**
- `RunEventType`
- `RunEvent`
- `RunEventStore`
- `FileRunEventStore`

**Functions:**
- `_utcnow`
- `get_default_store`
- `get_store_for`

## `core/evolution_ledger.py`

**Classes:**
- `LedgerEntry`
- `EvolutionLedger`

## `core/evolution_types.py`

**Classes:**
- `EvolutionDecision`
- `EvolutionResult`

## `core/executor.py`

**Functions:**
- `run_skill_safely`

## `core/express_router.py`

**Classes:**
- `RouteDecision`

**Functions:**
- `_tokens_found`
- `_trivial_found`
- `_classify`
- `route_task`

## `core/external_skill_candidate_importer.py`

**Functions:**
- `_default_root_dir`
- `cache_root_for_source`
- `_candidate_key`
- `_portable_candidate_path`
- `_read_yaml_file`
- `_cache_roots_for_source`
- `_discover_source_ids`
- `_iter_repo_dirs`
- `_candidate_from_manifest`
- `_manifest_candidate_mapping`
- `_scan_repo_manifest_candidates`
- `_python_candidate`
- `_markdown_candidate`
- `_scan_repo_fallback_candidates`
- `discover_external_candidates`
- `merge_install_candidates`
- `import_external_candidates`
- `_build_arg_parser`
- `main`

## `core/external_skill_source_ids.py`

**Functions:**
- `safe_id`
- `safe_optional_id`
- `normalize_external_source_id`
- `legacy_external_source_ids`

## `core/external_skill_sources.py`

**Classes:**
- `ExternalSkillCandidate`
- `ExternalSkillSource`
- `ManifestSkillSource`
- `RepoCacheSkillSource`
- `CodexOfficialSkillSource`
- `ClaudeOfficialSkillSource`
- `CacheSweepSkillSource`
- `ExternalSkillResolver`

**Functions:**
- `_split_csv`
- `_split_raw_csv`
- `_normalize_urls`
- `_normalize_paths`
- `_source_priority`
- `_repo_source_configs`
- `_parse_frontmatter_name`
- `_extract_skill_id`
- `_official_codex_skill_roots`
- `_official_claude_skill_roots`

## `core/failure_classifier.py`

**Classes:**
- `FailureCategory`

**Functions:**
- `classify_failure`

## `core/file_io.py`

**Functions:**
- `_env_flag`
- `_yaml_cache_max_entries`
- `_sha256_file`
- `_yaml_cache_put`
- `read_yaml`
- `write_yaml`
- `write_text`
- `sha256_text`

## `core/file_lock.py`

**Functions:**
- `_get_thread_lock`
- `locked_file`

## `core/fsa_loop.py`

**Classes:**
- `FSALoop`

**Functions:**
- `parse_evaluator_response`

## `core/git_manager.py`

**Classes:**
- `GitManager`

**Functions:**
- `git_configure_and_push`

## `core/hashline_editor.py`

**Classes:**
- `HashlineEditor`

## `core/hooks/base.py`

**Classes:**
- `ToolCallDecision`
- `ContinuationHook`

## `core/hooks/checkpoint.py`

**Classes:**
- `CheckpointHook`

## `core/hooks/code_review_doc.py`

**Classes:**
- `CodeReviewDocHook`

## `core/hooks/context_fork.py`

**Classes:**
- `ContextForkHook`

**Functions:**
- `_invoke_with_timeout`
- `_to_text`
- `_fallback_summarize`
- `_extract_dict_status`

## `core/hooks/design_review_hook.py`

**Classes:**
- `DesignReviewHook`

**Functions:**
- `_extract_file_path`
- `_git_changed_files`

## `core/hooks/event_bus.py`

**Classes:**
- `HookEventBus`

## `core/hooks/guardrails.py`

**Classes:**
- `IntentGateHook`
- `TodoContinuationEnforcer`
- `ToolOutputTruncator`

## `core/hooks/human_interrupt.py`

**Classes:**
- `HumanInterruptHook`

## `core/hooks/langsmith_tracing.py`

**Classes:**
- `_StdoutCapturer`
- `LangSmithTracingHook`

**Functions:**
- `_is_enabled`

## `core/hooks/lsp_check.py`

**Classes:**
- `LSPCheckHook`

**Functions:**
- `_is_enabled`
- `_find_pyright`
- `_validate_file_path`
- `_run_pyright`
- `_extract_file_path`
- `_is_python_file`

## `core/hooks/memory_consolidation.py`

**Classes:**
- `MemoryConsolidationHook`

**Functions:**
- `register_active_hook`
- `request_consolidation_hint`

## `core/hooks/skill_self_evolution.py`

**Classes:**
- `SkillSelfEvolutionHook`

## `core/implementation_language_policy.py`

**Functions:**
- `_env_flag`
- `enforce_os_language_for_human_text`
- `implementation_language_profile`
- `implementation_language_contract_text`
- `inject_implementation_language_contract`

## `core/ingestion_pipeline.py`

**Classes:**
- `IngestionPipeline`

## `core/install_candidate_utils.py`

**Functions:**
- `safe_id`
- `infer_source_id_from_candidate_key`
- `canonical_install_candidate_key`
- `legacy_install_candidate_keys`
- `normalize_install_candidate_item`
- `normalize_install_candidate_collection`

## `core/intent.py`

**Classes:**
- `IntentGate`

## `core/interactive_chat.py`

**Classes:**
- `InteractiveChat`
- `PDCAInteractiveChat`

**Functions:**
- `_c`
- `_print_banner`
- `_make_pdca_commands`
- `run_pdca_interactive`
- `_run_pdca_repl`
- `_print_pdca_help`
- `_load_or_build_agent`
- `run_interactive`

## `core/interview.py`

**Functions:**
- `_default_output_path`
- `_write_json`
- `collect_answers`
- `_build_assumptions`
- `_ensure_artifact_shape`
- `run_interview`
- `cli_main`

## `core/ise_analyzer.py`

**Classes:**
- `ISEAnalysis`
- `ISEAnalyzer`

## `core/ise_loop.py`

**Classes:**
- `ISELoop`

## `core/ise_redesigner.py`

**Classes:**
- `ISERedesigner`

## `core/ise_stall_detector.py`

**Classes:**
- `StallDetector`

## `core/ise_strategy_ledger.py`

**Classes:**
- `StrategyEntry`
- `StrategyLedger`

## `core/knowledge_skill.py`

**Classes:**
- `KnowledgeSkill`

**Functions:**
- `parse_skill_md`
- `scan_knowledge_skills`
- `filter_relevant_knowledge`
- `build_knowledge_prompt`

## `core/langchain_adapter.py`

**Classes:**
- `LangChainToolAdapter`
- `LangChainChatModelFactory`
- `PydanticOutputAdapter`

## `core/lineage_ledger.py`

**Classes:**
- `LineageEntry`
- `LineageLedger`

**Functions:**
- `get_lineage_ledger`
- `reset_lineage_ledger`

## `core/llm_engine.py`

**Classes:**
- `LLMEngine`

**Functions:**
- `_load_gemini_keys`
- `get_next_gemini_key`
- `get_current_gemini_key`
- `get_latest_flash_model`
- `get_best_model`
- `_flash_auto_upgrade_enabled`

## `core/lsp_bridge.py`

**Classes:**
- `LSPBridge`

## `core/manager.py`

**Classes:**
- `AgentManager`
- `RequirementAnalyzer`

## `core/mcp_adapter.py`

**Classes:**
- `MCPServerConnection`
- `MCPAdapter`

**Functions:**
- `_log`
- `_make_request`
- `_make_notification`
- `load_mcp_tools_sync`

## `core/memory.py`

**Functions:**
- `_to_epoch`
- `_iter_recent_json_files`
- `_scan_dir_recursive`
- `_memory_value_to_text`
- `_load_core_json`
- `read_core_memory`

## `core/memory_system/__init__.py`

_(no top-level symbols)_

## `core/memory_system/adapters/__init__.py`

_(no top-level symbols)_

## `core/memory_system/adapters/ast_hub.py`

**Classes:**
- `AstHubAdapter`

## `core/memory_system/adapters/base.py`

**Classes:**
- `MemoryBackendAdapter`

## `core/memory_system/adapters/continuity.py`

**Classes:**
- `ContinuityAdapter`

## `core/memory_system/adapters/core_memory.py`

**Classes:**
- `CoreMemoryAdapter`

**Functions:**
- `_memory_root`

## `core/memory_system/adapters/cortex_vector.py`

**Classes:**
- `CortexVectorAdapter`

**Functions:**
- `_try_import_cortex`

## `core/memory_system/adapters/knowledge_graph.py`

**Classes:**
- `KnowledgeGraphAdapter`

## `core/memory_system/adapters/sync_compyne.py`

**Classes:**
- `SyncCompyneAdapter`

## `core/memory_system/adapters/trace_log.py`

**Classes:**
- `TraceLogAdapter`

## `core/memory_system/config.py`

**Classes:**
- `MemoryPaths`
- `RelevanceWeights`
- `TTLDefaults`
- `AdapterTimeouts`
- `MemorySystemConfig`

**Functions:**
- `_env`
- `_env_float`
- `get_config`
- `set_config`

## `core/memory_system/cross_project.py`

**Classes:**
- `CrossProjectRecall`

## `core/memory_system/decay.py`

**Classes:**
- `MemoryDecayManager`

**Functions:**
- `_build_ttl_map`

## `core/memory_system/episode_extractor.py`

**Functions:**
- `extract_episode_from_jsonl`
- `extract_episode_from_events`
- `_parse_jsonl`
- `_events_to_episode`

## `core/memory_system/episode_matcher.py`

**Classes:**
- `EpisodeMatcher`

**Functions:**
- `keyword_similarity`
- `_search_seed_episodes`
- `_extract_hints_from_md`
- `_find_repo_root`

## `core/memory_system/facade.py`

**Classes:**
- `UnifiedMemoryFacade`

**Functions:**
- `_deduplicate`
- `_episode_to_content`

## `core/memory_system/graph_builder.py`

**Functions:**
- `extract_triple`
- `promote_to_global`
- `_truncate`
- `_diff_actions`

## `core/memory_system/graph_query.py`

**Classes:**
- `GraphQuery`

## `core/memory_system/issue_tracker.py`

**Classes:**
- `Issue`
- `IssueTrackerAdapter`
- `GitHubIssuesAdapter`
- `JiraAdapter`

## `core/memory_system/knowledge_forger.py`

**Classes:**
- `KnowledgeForger`

**Functions:**
- `_extract_tags`

## `core/memory_system/knowledge_injection.py`

**Classes:**
- `KnowledgeInjectionHook`

## `core/memory_system/models.py`

**Classes:**
- `MemoryType`
- `MemoryScope`
- `NodeType`
- `EdgeType`
- `MemoryRecord`
- `EpisodeRecord`
- `KnowledgeNode`
- `KnowledgeEdge`

**Functions:**
- `_utcnow`
- `_new_id`
- `content_hash`

## `core/memory_system/project_lifecycle.py`

**Classes:**
- `ProjectState`
- `ProjectLifecycleManager`

## `core/memory_system/router.py`

**Classes:**
- `MemoryQueryType`
- `MemoryQueryPlan`
- `MemoryRouter`

**Functions:**
- `_match_score`

## `core/memory_system/strategy_ledger.py`

**Classes:**
- `RoleAssignmentRecord`
- `FailurePatternRecord`
- `StrategyLedger`

**Functions:**
- `get_strategy_ledger`
- `reset_strategy_ledger`

## `core/message_broker.py`

**Classes:**
- `MessageBroker`

**Functions:**
- `_log`
- `make_message`

## `core/model_router.py`

**Classes:**
- `ModelRouter`

**Functions:**
- `_print_no_subscription_guide`
- `_print_single_provider_notice`
- `_print_multi_provider_notice`
- `print_startup_routing_notice`

## `core/nightly_state.py`

**Classes:**
- `BudgetState`
- `NightlyState`

**Functions:**
- `af_dir`
- `snapshot_path`
- `lock_path`
- `alert_flag_path`
- `summary_path`
- `load_state`
- `save_state`
- `_render_derived_files`
- `_write_json_file`
- `mark_alert`
- `clear_alert`
- `make_tick_id`

## `core/onboarding_wizard.py`

**Classes:**
- `OnboardingWizard`

**Functions:**
- `_c`
- `_hr`
- `_print_welcome`
- `_safe_project_id`
- `print_resume_banner`

## `core/parallel_critique.py`

**Classes:**
- `CritiqueResult`
- `MergedCritique`
- `ParallelCritiqueEngine`

## `core/pdca_commands.py`

**Classes:**
- `PDCACommandRegistry`

**Functions:**
- `_c`
- `_hr`
- `_box_header`
- `_checkpoint_prompt`

## `core/pdca_state.py`

**Classes:**
- `PDCAPhase`
- `ProjectLevel`
- `PDCAState`
- `PDCAStateMachine`

## `core/pipeline_quality.py`

**Classes:**
- `VerdictResult`
- `AggregatedVerdict`
- `PipelineStageGuard`

## `core/plan_verifier.py`

**Classes:**
- `PlanVerifyResult`
- `PlanVerifier`

## `core/planner.py`

**Classes:**
- `PlanStep`
- `ExecutablePlan`

**Functions:**
- `_test_file_for`
- `_collect_verification_commands`
- `_collect_approval_points`
- `_unresolved_risks`
- `_is_assumption_risk`
- `_extract_duplicate_function_paths`
- `_extract_conflicting_import_pairs`
- `_extract_long_function_pairs`
- `_extract_complexity_pairs`
- `_extract_nesting_depth_pairs`
- `_extract_scope_file_paths`
- `_extract_stale_test_paths`
- `_build_investigation_steps`
- `_references_for_scope_item`
- `_build_implementation_steps`
- `_build_verification_step`
- `build_plan`
- `implementation_steps`

## `core/policy.py`

**Functions:**
- `_coerce_int`
- `_coerce_float`
- `resolve_runtime_mode`
- `resolve_quality_gate_policy`

## `core/policy_runtime.py`

**Classes:**
- `PolicyRuntime`

**Functions:**
- `_config_to_dict`
- `resolve_quality_gate_policy`

## `core/premortem.py`

**Classes:**
- `VerificationStep`
- `PremortomRisk`
- `PremortomResult`

**Functions:**
- `_any_match`
- `_detect_blueprint_sync_risk`
- `_detect_packaging_risk`
- `_detect_workspace_risk`
- `_detect_destructive_risk`
- `_detect_existing_pattern_risk`
- `_detect_scope_file_risk`
- `_detect_duplicate_function_risk`
- `_detect_stale_test_risk`
- `_detect_conflicting_import_risk`
- `_detect_long_function_risk`
- `_detect_complexity_risk`
- `_max_block_depth`
- `_detect_nesting_depth_risk`
- `_detect_assumption_risks`
- `_detect_gap_risks`
- `run_premortem`

## `core/project_init.py`

**Functions:**
- `_current_paths`
- `ensure_project_files`

## `core/project_mailbox.py`

**Functions:**
- `_clean_text`
- `_clean_list`
- `_messages_path`
- `_normalize_related_files`
- `_is_expired`
- `load_mailbox_messages`
- `_write_messages`
- `send_agent_message`
- `read_inbox`
- `ack_mailbox_message`
- `mailbox_prompt_digest`

## `core/project_pipeline.py`

**Classes:**
- `ResearchGateBlocked`
- `PreparedBrief`
- `PreparedProject`
- `ProjectPipeline`

**Functions:**
- `_stage_enabled`

## `core/project_task_board.py`

**Functions:**
- `_module_sort_key`
- `compute_max_cycles`
- `default_planning_steps`
- `_clean_text`
- `_clean_list`
- `_role_name`
- `_role_objective`
- `_module_status`
- `_task_is_infra_failure`
- `_build_board_maps`
- `module_outcome_from_board`
- `detect_owner_drift`
- `_pick_owner_role`
- `_normalize_roles`
- `_normalize_planning_steps`
- `_task_template`
- `_deliverable_to_module_name`
- `_auto_modules`
- `_normalize_tasks`
- `enrich_role_plan`
- `build_project_board`
- `_recalculate_board`
- `board_todo_items`
- `write_project_board`
- `load_project_board`
- `board_is_complete`
- `_dependency_satisfied`
- `next_board_tasks`
- `update_project_board_task`
- `sync_todo_from_board`
- `append_project_board_note`
- `reset_in_progress_tasks`
- `board_prompt_digest`
- `write_task_execution_plan`
- `inject_review_tasks`

## `core/provider_detect.py`

**Classes:**
- `ProviderState`
- `ProviderProbeResult`

**Functions:**
- `_resolve_ping_cmd`
- `_cache_path`
- `_ttl_sec`
- `_now_iso`
- `_read_cache_raw`
- `_write_cache_raw`
- `_cache_fresh`
- `_result_from_dict`
- `_apply_rate_limit_override`
- `_parse_skip_providers`
- `_ping_one`
- `_probe_one`
- `detect_provider_states`
- `mark_rate_limited`
- `detect_rate_limit_signal`
- `invalidate_cache`
- `_main`

## `core/providers/__init__.py`

_(no top-level symbols)_

## `core/providers/cli.py`

**Classes:**
- `CliChatRequest`
- `CliProviderSpec`

**Functions:**
- `_default_cli_timeout_sec`
- `get_cli_provider_spec`
- `_split_command_template`
- `_resolve_base_command`
- `_windows_roaming_npm_dir`
- `_resolve_installed_command`
- `_env_truthy`
- `_default_install_command`
- `_resolve_install_command`
- `_should_auto_install`
- `_progress_printer`
- `_run_command`
- `_attempt_cli_auto_install`
- `_build_cli_env`
- `_command_exists`
- `_excerpt`
- `_classify_cli_issue`
- `_should_auto_login`
- `_auth_timeout_sec`
- `_auth_status_timeout_sec`
- `_build_auth_command`
- `_run_cli_auth_preflight`
- `_build_preflight_failure_result`
- `_compose_prompt`
- `_detect_repo_root`
- `_collect_git_context`
- `_should_include_model`
- `_build_workspace_access_flags`
- `compose_cli_prompt`
- `_swap_flag_value`
- `_apply_sandbox_mode`
- `build_cli_command`
- `_extract_text`
- `_extract_codex_agent_message`
- `execute_cli_chat`

## `core/providers/registry.py`

**Functions:**
- `_env_truthy`
- `configure_providers`
- `get_active_provider_setting`
- `parse_provider_list`
- `get_requested_cli_providers`
- `supports_cli_bootstrap`
- `engine_api_keys_disabled`
- `get_engine_api_key`
- `get_configured_engine_api_key`
- `is_engine_api_key_env`
- `strip_engine_api_keys`
- `default_chat_model_for_provider`
- `_windows_roaming_npm_dir`
- `_unix_npm_global_dirs`
- `detect_installed_cli_providers`
- `invalidate_installed_cli_cache`
- `detect_available_cli_providers`
- `get_cli_display_name`
- `get_cli_install_command`
- `get_cli_auth_command`
- `pick_review_provider`

## `core/providers/session_adapter.py`

**Classes:**
- `CliSessionSpec`

**Functions:**
- `_safe_slug`
- `_quote_command`
- `_hook_path_arg`
- `_hook_runner_python`
- `_merge_pythonpath`
- `_load_json`
- `_save_json`
- `_hook_json_dumps`
- `_sanitize_hook_value`
- `_append_jsonl`
- `_now_iso`
- `_prepend_path`
- `_prepend_pathext`
- `get_cli_session_spec`
- `_repo_root`
- `_is_frozen`
- `_runtime_paths`
- `_extract_open_todos`
- `_build_continuity_context`
- `_hook_command`
- `_is_managed_bridge_hook`
- `_merge_named_hook_group`
- `_write_claude_settings`
- `_write_gemini_defaults`
- `_resolve_delegate_path`
- `_write_codex_shell_guard`
- `_prepare_codex_runtime_env`
- `_seed_codex_runtime_home`
- `prepare_cli_session`
- `finalize_cli_session`
- `_event_name`
- `_assistant_excerpt`
- `_is_headless_session`
- `_hook_output`
- `handle_hook_event`

## `core/qa_report.py`

**Functions:**
- `render_html`
- `_goal_header`
- `_field`
- `_pre`
- `_section_verified`
- `_section_failed`
- `_section_cannot_verify`
- `_section_unverified`
- `_section_confirm`

## `core/registry.py`

**Classes:**
- `ToolRegistry`

## `core/registry_manager.py`

**Classes:**
- `RegistryManager`

**Functions:**
- `read_project_policies`
- `ensure_registry_files`

## `core/request_router.py`

**Classes:**
- `RequestRouter`

## `core/requirement_llm.py`

**Classes:**
- `RequirementCandidate`

**Functions:**
- `_workspace_path`
- `_effective_requirement_prompt`
- `_extract_openai_text`
- `_make_usage`
- `_call_google_api`
- `_call_openai_api`
- `_call_anthropic_api`
- `_cli_model_for_provider`
- `list_requirement_candidates`
- `pick_requirement_candidate`
- `execute_document_prompt`
- `execute_requirement_prompt`

## `core/research/__init__.py`

_(no top-level symbols)_

## `core/research/checklist_merger.py`

**Classes:**
- `ChecklistMerger`

## `core/research/quality_contract.py`

**Classes:**
- `QualityContractBuildError`
- `QualityContractItem`
- `QualityContract`
- `QualityContractBuilder`

## `core/research/work_spec.py`

**Classes:**
- `WorkSpec`
- `WorkSpecExtractor`

**Functions:**
- `_extract_json`

## `core/research_brief.py`

**Classes:**
- `ResearchBrief`

**Functions:**
- `build_from_interview`
- `_tokenize`
- `_is_on_brief`
- `_evidence_text`
- `tag_evidence`
- `split_evidence`

## `core/research_engine.py`

**Classes:**
- `ResearchMode`

**Functions:**
- `_get_archive_notebook_id`
- `_nlm_cmd_base`
- `_nlm_env`
- `_is_auth_error`
- `_reauth_notebooklm`
- `_nlm_cli`
- `classify_research_depth`
- `query_notebooklm`
- `create_notebook`
- `inject_source_url`
- `inject_source_text`
- `inject_sources`
- `generate_deep_research_prompt`

## `core/research_router.py`

**Classes:**
- `ResearchGap`
- `ResearchPlan`
- `ResearchRouter`

**Functions:**
- `gap_to_mode`
- `_count_matches`

## `core/research_verifier.py`

**Classes:**
- `VerificationResult`
- `ResearchVerifier`

## `core/researcher.py`

**Classes:**
- `HimariResearchAgent`

## `core/retrieval_router.py`

**Classes:**
- `RetrievalStrategy`
- `RetrievalPlan`
- `RetrievalRouter`

## `core/review_bundle.py`

**Functions:**
- `_ast_available`
- `_grep_risks`
- `_ast_risks`
- `build`
- `save`
- `load`
- `_git_diff`
- `_extract_changed_symbols`
- `_find_related_tests`
- `_caller_context`
- `_find_direct_callers`
- `_read_test_gap`
- `_read_prior_findings`
- `_compute_source_hash`
- `_assemble`
- `build_full`
- `save_full`

## `core/review_report.py`

**Classes:**
- `ReviewerResult`
- `JudgeResult`
- `ReviewReport`
- `DocumentReviewSession`

## `core/review_runner.py`

**Functions:**
- `detect_providers`
- `detect_blocked_providers`
- `select_review_pair`
- `select_judge`
- `_load_prompt`
- `_run_provider`
- `_build_review_prompt`
- `run_critic`
- `run_cross`
- `run_aggregation`
- `_parse_verdict`
- `_extract_vendor_label`
- `run_critic_review`
- `run_cross_review`

## `core/review_skill_router.py`

**Classes:**
- `ReviewContext`
- `TierSkillProfile`
- `ReviewSkillPlan`

**Functions:**
- `_has_blueprint_impact`
- `_is_worktree_work`
- `_dedup`
- `route_review_skills`

## `core/right_sized_router.py`

**Classes:**
- `RouteDecision`

**Functions:**
- `_get_router_llm`
- `_fallback_decision`
- `_validate_raw`
- `_isolation_rank`
- `_stage_ordered_union`
- `_is_self_modification`
- `_max_tier`
- `_apply_safety_floors`
- `_build_empty_scope_prompt`
- `_classify_empty_scope`
- `_build_prompt`
- `classify`

## `core/role_decomposer.py`

**Functions:**
- `log`
- `get_random_signature`
- `load_policy`
- `resolve_agent_engine`
- `get_engine_model`
- `research_required_skills`

## `core/rubric_compiler.py`

**Classes:**
- `DimensionScore`
- `RubricResult`
- `RubricCompiler`

## `core/run_budget.py`

**Classes:**
- `RunBudget`

**Functions:**
- `set_run_budget`
- `get_run_budget`

## `core/runner.py`

**Classes:**
- `RunPipeline`

## `core/sandbox_config.py`

**Functions:**
- `sandbox_enabled`
- `set_sandbox_enabled`

## `core/security_guard.py`

**Functions:**
- `safe_generate`
- `quick_guard`
- `run_isolated`
- `build_child_env`

## `core/security_scanner.py`

**Functions:**
- `security_scan`

## `core/semantic_embedder.py`

**Classes:**
- `SemanticEmbedder`

## `core/setup_wizard.py`

**Functions:**
- `_get_env_path`
- `_load_existing`
- `_save_env`
- `run_setup`
- `check_and_hint`
- `_default_state`
- `_get_setup_state_path`
- `_now_utc_iso`
- `_load_setup_state`
- `_save_setup_state`
- `_resolve_mode`
- `_is_interactive_mode`
- `_check_chrome_installed`
- `_nlm_cmd_base`
- `_check_notebooklm_auth`
- `_run_notebooklm_login`
- `_parse_notebook_create_output`
- `_parse_notebook_list_for_title`
- `_looks_like_valid_json_array`
- `_validate_notebook_uuid`
- `_find_or_create_archive_notebook`
- `_prompt_manual_notebook_uuid`
- `_box`
- `_ensure_tavily`
- `_ensure_notebooklm`
- `_handle_chrome_missing`
- `_handle_notebooklm_login`
- `_confirm_skip_notebooklm`
- `_ensure_archive_notebook`
- `_handle_archive_fallback`
- `ensure_external_research_capabilities`

## `core/skill_autodiscover.py`

**Classes:**
- `SkillAutoDiscovery`

**Functions:**
- `get_discoverer`
- `auto_discover_skills`

## `core/skill_cache.py`

**Classes:**
- `SkillRelevanceCache`
- `OptimizedSkillRelevance`

## `core/skill_context_config.py`

**Classes:**
- `SkillLoaderConfig`

**Functions:**
- `get_context_tokens`
- `get_max_skills_for_model`

## `core/skill_creator.py`

**Functions:**
- `normalize_skill_name`
- `_title_case`
- `_safe_id`
- `validate_skill`
- `_validate_skill_md`
- `_validate_skill_py`
- `init_skill_dir`
- `_knowledge_body_template`
- `_create_example_file`
- `generate_skill_content`
- `create_skill`
- `_bump_minor_version`
- `_detect_skill_type`
- `_read_skill_file`
- `_read_meta`
- `_write_meta`
- `_skill_name_from_dir`
- `update_skill`
- `evolve_skill`
- `retire_skill`
- `benchmark_skill`
- `cli_main`

## `core/skill_enricher.py`

**Functions:**
- `meta_quality_score`
- `_read_skill_content`
- `_read_meta`
- `_write_meta`
- `_extract_enrichment_via_llm`
- `enrich_skill_metadata`
- `bulk_enrich_all_skills`

## `core/skill_eval_harness.py`

**Classes:**
- `EvalCaseResult`
- `EvalPhaseSummary`
- `ShadowEvalSummary`
- `SkillEvalReport`
- `SkillEvalHarness`

**Functions:**
- `load_eval_report`
- `_phase_from_payload`
- `_shadow_from_payload`
- `_coerce_cases`
- `_load_shadow_replay_cases`
- `_resolve_shadow_feedback_path`
- `_resolve_shadow_runs_dir`
- `_build_shadow_replay_case`
- `_resolve_optional_path`
- `_discover_evals_path`
- `_infer_workspace_root`
- `_is_truthy`
- `_coerce_int`
- `_load_skill_callable`
- `_run_eval_case`
- `_excerpt`
- `_extract_skill_id`
- `_read_json`
- `_write_json`
- `cli_main`

## `core/skill_evolution_bus.py`

**Classes:**
- `SkillEvolutionBus`

## `core/skill_evolution_controller.py`

**Classes:**
- `SelfEvolutionController`

## `core/skill_evolution_safety.py`

**Functions:**
- `verify_evolved_skill_sandbox`
- `rollback_evolved_skill`

## `core/skill_feedback.py`

**Classes:**
- `SkillFeedbackEvent`
- `SkillFeedbackSummary`
- `SkillFeedbackLoop`

## `core/skill_forge.py`

**Classes:**
- `ForgeCritique`
- `ForgeRunResult`
- `SkillForge`

## `core/skill_loader.py`

**Classes:**
- `SkillDependencyGraph`
- `SkillRelevance`
- `DynamicSkillLoader`
- `AdaptiveSkillLoader`

## `core/skill_metadata.py`

**Classes:**
- `SkillCategory`
- `SkillType`
- `SkillMetadata`

**Functions:**
- `skill_metadata`
- `get_skill_metadata`
- `has_skill_metadata`
- `require_skill_metadata`

## `core/skill_metadata_adapter.py`

**Functions:**
- `_first_non_empty`
- `_coerce_bool`
- `_coerce_int`
- `_coerce_str`
- `_coerce_list`
- `_coerce_argument_hint`
- `_merge_lists`
- `_normalize_skill_id`
- `_default_display_name`
- `_parse_category`
- `_parse_skill_type`
- `_default_category_for_type`
- `_detect_eval_manifest`
- `_detect_generated_spec`
- `_split_frontmatter`
- `_extract_markdown_description`
- `_resolve_context_mode`
- `_eval_manifest_from_fields`
- `_generated_spec_from_fields`
- `_mapping_to_metadata`
- `convert_skill_yaml_to_metadata`
- `convert_meta_yaml_to_metadata`
- `convert_skill_md_to_metadata`
- `convert_yaml_config_to_metadata`
- `_fill_missing_description`
- `auto_detect_and_convert`

## `core/skill_pack_bootstrapper.py`

**Classes:**
- `SkillPackBootstrapper`

## `core/skill_preflight.py`

**Classes:**
- `PreflightResult`
- `PreflightEvaluator`

**Functions:**
- `cli_main`
- `_print_report`
- `_load_skill_module`
- `_extract_skill_id`
- `_calc_consistency`
- `_calc_stddev`

## `core/skill_procurer.py`

**Classes:**
- `SkillOrchestrator`

**Functions:**
- `log`
- `sync_warehouse`
- `snapshot_registry`
- `normalize_skill_id`
- `_resolve_available_skill_path`
- `get_installed_skill_ids`
- `get_missing_skills`
- `procure_skill`
- `evaluate_and_promote`
- `_prepare_forge_context`
- `_generate_and_validate_evals`
- `_evaluate_promote_and_register`
- `forge_new_skill`
- `_forge_knowledge_skill`

## `core/skill_promotion.py`

**Classes:**
- `PromotionDecision`
- `SkillPromotionManager`

**Functions:**
- `_ensure_report`
- `_normalize_stage`
- `_write_json`
- `cli_main`

## `core/skill_quality_gate.py`

**Classes:**
- `GateResult`
- `SkillQualityGate`

## `core/skill_registry.py`

**Classes:**
- `SkillRegistry`

**Functions:**
- `get_global_registry`
- `register_skill_metadata`
- `get_skill_metadata_global`
- `list_all_skills`
- `ensure_skills_loaded`
- `_load_registry`
- `_source_to_id`
- `_save_registry`
- `check_skill_exists`
- `rebuild_registry_from_disk`
- `_normalize_skill_entry`
- `register_skill`

## `core/skill_retrieval_engine.py`

**Classes:**
- `CapabilityGap`
- `ReuseDecision`
- `SkillRetrievalEngine`

## `core/skill_spec_synthesizer.py`

**Classes:**
- `SynthesizedSkillArtifacts`
- `SkillSpecSynthesizer`

**Functions:**
- `_resolve_baseline_skill_path`
- `_looks_destructive`
- `_infer_allowed_tools`
- `cli_main`

## `core/spec_compiler.py`

**Classes:**
- `CompiledSpec`

**Functions:**
- `_str_list`
- `_flatten_evidence`
- `_detect_gaps`
- `_scope_from_intent`
- `_scope_from_clarification_log`
- `compile_spec`

## `core/spec_generator.py`

**Classes:**
- `SpecGenerator`
- `AdrGenerator`
- `TraceabilityGenerator`

**Functions:**
- `_call_llm_raw`

## `core/swarm_council.py`

**Classes:**
- `SwarmCouncil`

**Functions:**
- `now_iso`

## `core/synergy/__init__.py`

_(no top-level symbols)_

## `core/synergy/bridge.py`

**Classes:**
- `JobRegistry`
- `SynergyBridge`

## `core/synergy/job.py`

**Classes:**
- `JobStatus`
- `OmoJob`

## `core/synergy/process.py`

**Classes:**
- `OmoDetector`

**Functions:**
- `_truncate`
- `_kill_tree`

## `core/synergy/tools.py`

**Functions:**
- `get_synergy_context`
- `build_synergy_tools`

## `core/synergy_runner.py`

_(no top-level symbols)_

## `core/template_input.py`

**Functions:**
- `prompt_mission_template`

## `core/terminal_bridge.py`

**Classes:**
- `TerminalBridge`

**Functions:**
- `_truncate`
- `_is_command_safe`

## `core/terminal_visualizer.py`

**Classes:**
- `AgentPhase`
- `VisualMode`
- `AgentVisualState`
- `TerminalVisualizer`

**Functions:**
- `get_visualizer`
- `set_visualizer`
- `_progress_bar`

## `core/text_integrity.py`

**Classes:**
- `TextFileFormat`
- `TextFileSnapshot`

**Functions:**
- `is_supported_text_path`
- `detect_newline_style`
- `decode_utf8_bytes`
- `inspect_text_bytes`
- `inspect_text_file`
- `normalize_newlines`
- `encode_text`
- `write_text_preserving_format`
- `find_suspicious_markers`

## `core/tool_runtime.py`

**Classes:**
- `ToolRuntimeWrapper`

## `core/triad.py`

**Classes:**
- `TriadCriticFinding`
- `TriadCriticReport`
- `TriadDecision`
- `TriadResult`
- `TriadBlockedError`

**Functions:**
- `_validate_findings`
- `_coerce_verdict`
- `_default_critic_fn`
- `_default_architect_fn`
- `run_triad`

## `core/utils.py`

**Functions:**
- `now_iso`
- `safe_id`
- `safe_optional_id`
- `truncate_text`
- `clamp`
- `clamp_ratio`
- `median`
- `mode`
- `variance`
- `std_dev`
- `mean_absolute_deviation`
- `zscore`
- `percentile`
- `range_span`
- `normalize`
- `cumsum`
- `running_max`
- `running_min`
- `exponential_moving_average`
- `moving_average`
- `geometric_mean`
- `harmonic_mean`
- `weighted_mean`
- `interquartile_range`
- `covariance`
- `pearson_correlation`
- `spearman_correlation`
- `kurtosis`
- `skewness`
- `root_mean_square`
- `chunks`
- `flatten`
- `_split_env_paths`
- `test_file_for`
- `strip_code_fences`
- `safe_json_load`
- `get_random_signature`
- `safe_print`
- `print_agent_msg`
- `is_codex_model`
- `is_claude_model`
- `read_project_policies`
- `read_skill_lock`
- `lock_skill_state`
- `read_project_settings`
- `resolve_existing_path`
- `to_portable_path`
- `is_portable_rel_path`
- `resolve_skill_paths`
- `skill_markdown_filenames`
- `get_external_skill_roots`
- `resolve_knowledge_skill_path`
- `resolve_any_skill_path`
- `has_local_skill`
- `_merge_dict`
- `apply_agent_overrides`

## `core/warning_overrides.py`

**Functions:**
- `overrides_path`
- `load_overrides`
- `upsert_override`
- `remove_override`
- `is_overridden`
- `_atomic_write`

## `core/warning_registry.py`

**Classes:**
- `WarningRecord`
- `WarningRegistry`

**Functions:**
- `_normalize_phase`
- `_hash8`
- `_count_rule_records`
- `_write_minimal_block_decision`
- `_build_summary`

## `core/warning_stats.py`

**Classes:**
- `ProjectStats`
- `Distribution`

**Functions:**
- `_load_index`
- `_validate_slug`
- `_compute_distribution`
- `iter_warning_records`
- `collect_workspace_stats`

## `core/watchdog.py`

**Classes:**
- `LineageCounter`
- `WatchdogState`

## `core/web_search.py`

**Functions:**
- `_get_tavily_key`
- `tavily_search`
- `tavily_extract`
- `extract_urls`

## `core/work_item_generator.py`

**Classes:**
- `DocGenerationResult`

**Functions:**
- `_build_full_run_id`
- `_clean`
- `_clean_list`
- `_trim_text`
- `_research_bullets`
- `_reference_bullets`
- `_inline`
- `_skill_gap_bullets`
- `_structured_evidence_block`
- `_slug_from_goal`
- `_make_checklist`
- `_fallback_feature_plan`
- `_fallback_feature_spec`
- `_fallback_impl_design`
- `_fallback_impl_tasks`
- `_generate_doc_with_llm`
- `_generate_feature_plan`
- `_generate_feature_spec`
- `_generate_implementation_design`
- `_generate_implementation_tasks`
- `_extract_section_outline`
- `_resolve_future_or_fallback`
- `_exec_stage2`
- `_exec_stage1`
- `_exec_stage3`
- `_build_episode_hints_section`
- `_is_e2e_missing`
- `_backfill_e2e_from_tasks_md`
- `generate_work_items`
- `_generate_and_refine`
- `_refine_document`
- `_copy_extra_templates`
- `slug_from_brief`

## `core/work_item_parser.py`

**Functions:**
- `_clean`
- `_extract_section`
- `_bullet_list`
- `parse_feature_plan`
- `parse_feature_spec`
- `parse_implementation_tasks`
- `sync_board_from_work_items`

## `core/work_item_telemetry.py`

**Functions:**
- `update_t1_refine_attempts`
- `write_initial_record`

## `demo_runner.py`

**Functions:**
- `run_demo`

## `drive_meeting_stt.py`

_(no top-level symbols)_

## `end_db.py`

**Functions:**
- `_resolve_target`
- `_global_user_key`
- `_run`
- `main`

## `end_git.py`

**Functions:**
- `_resolve_target`
- `main`

## `end_sync.py`

**Functions:**
- `_run`
- `main`

## `extract_phase3.py`

**Functions:**
- `main`

## `factory_manager.py`

**Functions:**
- `find_existing_agent`
- `load_agent_config`
- `assemble_and_push`

## `lm.py`

**Functions:**
- `main`

## `model_utils.py`

**Classes:**
- `ModelSelection`

**Functions:**
- `log`
- `_get_genai_client`
- `load_cache`
- `save_cache`
- `normalize_model_name`
- `get_forced_model_override`
- `_is_not_found_error`
- `_build_gemini_retry_candidates`
- `generate_content_with_self_heal`
- `create_chat_with_self_heal`
- `get_available_models`
- `fetch_openai_models`
- `fetch_anthropic_models`
- `_pick_anthropic_model`
- `_pick_openai_model`
- `find_latest_model`
- `get_dynamic_default_model`
- `get_best_model`
- `resolve_dynamic_model`
- `_load_role_provider_cache`
- `_save_role_provider_cache`
- `pick_cli_provider_for_role`
- `resolve_engine_for_available`
- `_llm_decide_provider`
- `_infer_engine_id`
- `resolve_preferred_model`
- `print_agent_model_summary`

## `probe_openai.py`

_(no top-level symbols)_

## `project_orchestrator.py`

**Functions:**
- `print_message`
- `parse_mentions`
- `decompose_roles`
- `forge_roles`
- `parse_roles`
- `main`

## `projects/agent_factory/runs/r2/dp_skill.py`

**Functions:**
- `_validate`
- `_norm`
- `propose`
- `apply`
- `test`

## `projects/agent_factory/runs/r3/dp_skill.py`

**Functions:**
- `_validate`
- `_norm`
- `propose`
- `apply`
- `test`

## `projects/gemini_live_edit/artifacts/live_edit_check.py`

**Functions:**
- `status`

## `projects/lotto_mobile_web/conftest.py`

_(no top-level symbols)_

## `projects/lotto_mobile_web/server/__init__.py`

_(no top-level symbols)_

## `projects/lotto_mobile_web/server/app.py`

**Classes:**
- `RequestIdMiddleware`

**Functions:**
- `_parse_cors_origins`
- `_resolve_static_dir`
- `create_app`
- `_jsonify`

## `projects/lotto_mobile_web/server/bootstrap.py`

**Functions:**
- `_resolve_predictor_src`
- `ensure_predictor_importable`
- `smoke_import`

## `projects/lotto_mobile_web/server/dependencies.py`

**Functions:**
- `get_recommendation_service`
- `get_draw_cache_service`

## `projects/lotto_mobile_web/server/errors.py`

**Classes:**
- `ApiError`
- `DataUnavailableError`

**Functions:**
- `_envelope`
- `_validation_exception_handler`
- `_api_error_handler`
- `_http_exception_handler`
- `_unexpected_exception_handler`
- `install_error_handlers`

## `projects/lotto_mobile_web/server/schemas.py`

**Classes:**
- `RecommendationQuery`
- `RecommendationCombo`
- `RecommendationResponse`
- `DrawCacheEntry`
- `HealthResponse`
- `ErrorBody`
- `ErrorEnvelope`

## `projects/lotto_mobile_web/server/services/__init__.py`

_(no top-level symbols)_

## `projects/lotto_mobile_web/server/services/draw_cache.py`

**Classes:**
- `CacheLoadResult`
- `DrawCacheService`

## `projects/lotto_mobile_web/server/services/recommendation.py`

**Classes:**
- `RecommendationService`

**Functions:**
- `_combo_to_dict`

## `projects/lotto_mobile_web/tests/api/conftest.py`

**Classes:**
- `PredictorStub`
- `ApiTestClient`

**Functions:**
- `_load_dotted_path`
- `_resolve_app_target`
- `_install_predictor_override`
- `predictor_stub`
- `valid_query`
- `app_client`

## `projects/lotto_mobile_web/tests/api/test_recommend_endpoint.py`

**Functions:**
- `_assert_combo_shape`
- `test_recommend_returns_contract_shape`
- `test_recommend_rejects_invalid_query`
- `test_recommend_matches_requested_combo_count`
- `test_recommend_uses_offline_source_when_requested`

## `projects/lotto_mobile_web/tests/frontend/conftest.py`

**Classes:**
- `IndexHtmlParser`

**Functions:**
- `frontend_root`
- `render_contract`
- `index_html`
- `parsed_index`
- `recommendation_stub`
- `module_exports`

## `projects/lotto_mobile_web/tests/frontend/test_offline_cache_contract.py`

**Functions:**
- `run_node`
- `test_offline_cache_persists_and_restores_last_success`
- `test_offline_banner_contract_accepts_cache_and_offline_sources`

## `projects/lotto_mobile_web/tests/frontend/test_param_panel_contract.py`

**Functions:**
- `test_param_panel_slider_contract`

## `projects/lotto_mobile_web/tests/frontend/test_smoke_render.py`

**Functions:**
- `test_frontend_smoke_assets_exist`
- `test_index_html_declares_mobile_shell_contract`
- `test_javascript_modules_export_required_symbols`
- `test_representative_render_state_contract`

## `projects/lotto_pattern_predictor/scripts/run_qa_checks.py`

**Classes:**
- `CheckResult`

**Functions:**
- `now_iso`
- `run_shell_command`
- `append_result`
- `validate_path_target`
- `contains_any`
- `preflight_checks`
- `module_contract_checks`
- `extract_number_sets`
- `end_to_end_check`
- `write_json_report`
- `write_markdown_report`
- `summarize`
- `parse_args`
- `main`

## `projects/lotto_pattern_predictor/src/__init__.py`

_(no top-level symbols)_

## `projects/lotto_pattern_predictor/src/lotto/__init__.py`

_(no top-level symbols)_

## `projects/lotto_pattern_predictor/src/lotto/analysis.py`

**Classes:**
- `NumberFrequency`
- `PairCooccurrence`
- `AnalysisResult`
- `AnalysisEngine`

## `projects/lotto_pattern_predictor/src/lotto/cache_store.py`

**Classes:**
- `CacheStore`

**Functions:**
- `_result_to_row`
- `_row_to_result`

## `projects/lotto_pattern_predictor/src/lotto/exceptions.py`

**Classes:**
- `LottoError`
- `FetchError`
- `DrawNotFoundError`
- `CacheError`
- `AnalysisError`

## `projects/lotto_pattern_predictor/src/lotto/fetcher.py`

**Classes:**
- `LottoFetcher`

**Functions:**
- `_parse_draw_response`

## `projects/lotto_pattern_predictor/src/lotto/models.py`

**Classes:**
- `DrawResult`

## `projects/lotto_pattern_predictor/tests/__init__.py`

_(no top-level symbols)_

## `projects/lotto_pattern_predictor/tests/test_analysis.py`

**Classes:**
- `TestInit`
- `TestComputeFrequencies`
- `TestComputeBonusFrequencies`
- `TestComputePairCooccurrences`
- `TestComputeWindowFrequencies`
- `TestComputeWeights`
- `TestAnalyze`
- `TestSingleDraw`

**Functions:**
- `_draw`
- `sample_draws`
- `engine`

## `projects/lotto_pattern_predictor/tests/test_analyzer.py`

**Classes:**
- `TestComputeFrequencies`
- `TestComputePairCooccurrences`
- `TestComputeWindowFrequencies`
- `TestComputeWeights`
- `TestAnalysisResult`

**Functions:**
- `_load_analysis_module`
- `_추첨결과`
- `_회전_번호`
- `분석용_추첨목록`
- `단일_추첨`
- `육십회_윈도우_추첨목록`
- `전체번호_포함_추첨목록`

## `projects/lotto_pattern_predictor/tests/test_cache_store.py`

**Classes:**
- `TestInit`
- `TestSave`
- `TestQuery`
- `TestRoundTrip`
- `_FakeResponse`
- `_FakeSession`
- `TestFetcherIntegration`
- `TestContextManager`

**Functions:**
- `_make_draw`

## `projects/lotto_pattern_predictor/tests/test_fetcher.py`

**Classes:**
- `TestParseDrawResponse`
- `TestLottoFetcher`

**Functions:**
- `sample_response`
- `not_found_response`
- `response_factory`
- `session_mock`
- `fetcher`
- `_make_draw_result`

## `projects/lotto_pattern_predictor/tests/test_fetcher_integration.py`

**Classes:**
- `TestFetcherIntegration`

**Functions:**
- `fetcher`

## `projects/lotto_pattern_predictor/tests/test_models.py`

**Classes:**
- `TestDrawResult`

## `projects/lotto_pattern_predictor/tests/test_recommender.py`

**Classes:**
- `Test추천조합_기본검증`
- `Test가중치_반영`
- `Test엣지케이스`

**Functions:**
- `_추천_함수`
- `_추천_생성`
- `_번호_빈도_집계`
- `기본_가중치`
- `고가중치_가중치`
- `영가중치_포함_가중치`
- `균등_가중치`

## `projects/lotto_predictor_v2/src/lotto/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto/__main__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto/analytics/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto/analytics/patterns.py`

**Classes:**
- `PatternStats`

**Functions:**
- `calculate_number_frequency`
- `calculate_consecutive_gaps`
- `calculate_odd_even_ratio`
- `calculate_section_distribution`
- `calculate_trend_weights`
- `analyze_patterns`
- `_normalize_draws`
- `_extract_numbers`
- `_section_label`

## `projects/lotto_predictor_v2/src/lotto/cache/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto/cache/store.py`

**Classes:**
- `CacheLockTimeoutError`
- `LottoCacheStore`

## `projects/lotto_predictor_v2/src/lotto/cli.py`

**Functions:**
- `run`
- `_load_draws`
- `_build_online_store`
- `_load_offline`
- `_pause`
- `_build_parser`
- `main`
- `_is_frozen_double_click`

## `projects/lotto_predictor_v2/src/lotto/collector.py`

**Classes:**
- `DrawResult`
- `DrawRangeCollector`
- `CollectorAdapter`

**Functions:**
- `_date_to_iso`

## `projects/lotto_predictor_v2/src/lotto/recommender.py`

**Classes:**
- `Combination`

**Functions:**
- `recommend_combinations`
- `_build_candidate_pool`
- `_satisfies_constraints`
- `_build_section_pool`
- `_generate_section_balanced_candidates`
- `_score_candidate`
- `_gap_priority`
- `_count_sections`
- `_section_label`
- `_format_odd_even_ratio`

## `projects/lotto_predictor_v2/src/lotto/report.py`

**Functions:**
- `format_report`
- `_write_contract_source`
- `_write_contract_status`
- `_write_header`
- `_write_combinations`
- `_write_pattern_summary`
- `_write_footer`
- `_format_section_distribution`
- `write_report`

## `projects/lotto_predictor_v2/src/lotto_predictor/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/__main__.py`

**Functions:**
- `_ensure_src_on_path`

## `projects/lotto_predictor_v2/src/lotto_predictor/analytics/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/analytics/patterns.py`

**Classes:**
- `AnalysisRunSummary`
- `DrawCacheLike`

**Functions:**
- `analyze_patterns`
- `build_pattern_stats_from_cache`
- `build_statistics_summary`
- `summarize_analysis_run`
- `_calculate_number_last_seen`
- `_calculate_sum_range`
- `_normalize_numbers`

## `projects/lotto_predictor_v2/src/lotto_predictor/backend/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/backend/http_client.py`

**Classes:**
- `DhLotteryClient`
- `ThreeTierLotteryClient`

**Functions:**
- `_is_retryable_status`

## `projects/lotto_predictor_v2/src/lotto_predictor/backend/models.py`

**Classes:**
- `BackendError`
- `DrawNotFoundError`
- `TransientFetchError`
- `LottoDraw`
- `FetchCheckpoint`
- `NumberFrequencyRow`
- `FetchResult`

## `projects/lotto_predictor_v2/src/lotto_predictor/backend/serialization.py`

**Functions:**
- `parse_draw`
- `_optional_int`

## `projects/lotto_predictor_v2/src/lotto_predictor/backend/storage.py`

**Classes:**
- `LottoStorage`
- `_transaction`

**Functions:**
- `_draw_to_row`
- `_row_to_draw`
- `_optional_int`

## `projects/lotto_predictor_v2/src/lotto_predictor/cache/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/cache/core.py`

**Classes:**
- `_CollectorLike`
- `LottoDrawCache`

## `projects/lotto_predictor_v2/src/lotto_predictor/cache/json_store.py`

**Classes:**
- `CacheLockTimeoutError`
- `DrawLookupResult`
- `JsonCacheStatus`
- `JsonDrawCacheStore`

**Functions:**
- `_parse_iso`
- `_coerce_draw_no`
- `_coerce_freshness_hours`
- `_now_in_tz`

## `projects/lotto_predictor_v2/src/lotto_predictor/cache/models.py`

**Classes:**
- `CacheConfig`
- `CacheStatus`
- `CacheReadyResult`
- `CacheGapReport`

## `projects/lotto_predictor_v2/src/lotto_predictor/collector/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/collector/core.py`

**Classes:**
- `DrawFetcher`
- `LottoCollector`
- `_FetchOutcome`

## `projects/lotto_predictor_v2/src/lotto_predictor/collector/models.py`

**Classes:**
- `CollectorConfig`
- `FetchFailure`
- `SyncResult`

## `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/engine.py`

**Classes:**
- `RecommendationEngine`
- `_ScoredCandidate`

## `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/errors.py`

**Classes:**
- `InvalidRequestError`
- `RuleConflictError`
- `InsufficientCandidateError`

## `projects/lotto_predictor_v2/src/lotto_predictor/game_logic/models.py`

**Classes:**
- `CandidateStage`
- `LottoDraw`
- `StatisticsSummary`
- `RecommendationConfig`
- `RecommendationRequest`
- `RejectedCandidate`
- `RejectionReasonSummary`
- `EvaluationSummary`
- `RecommendationResult`
- `RecommendationBatch`

## `projects/lotto_predictor_v2/tests/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/cache/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/cache/_fakes.py`

**Classes:**
- `FakeStorage`
- `FakeCollector`

**Functions:**
- `make_draw`
- `fixed_clock`

## `projects/lotto_predictor_v2/tests/cache/test_cache_continuity.py`

**Functions:**
- `_cache_with`
- `test_validate_continuity_empty_storage_returns_no_range`
- `test_validate_continuity_continuous_range_has_no_gaps`
- `test_validate_continuity_reports_missing_in_middle`
- `test_validate_continuity_single_draw_is_continuous`
- `test_validate_continuity_ignores_starting_offset`

## `projects/lotto_predictor_v2/tests/cache/test_cache_ensure_ready.py`

**Functions:**
- `_fresh_storage`
- `test_ensure_ready_skipped_when_fresh`
- `test_ensure_ready_offline_mode_skips_collector`
- `test_ensure_ready_no_collector_yields_offline_action`
- `test_ensure_ready_refresh_policy_never_skips_even_when_stale`
- `test_ensure_ready_synced_refreshes_status_after_collection`
- `test_ensure_ready_preserves_sync_result_even_on_aborted`

## `projects/lotto_predictor_v2/tests/cache/test_cache_reads.py`

**Functions:**
- `_cache_with`
- `test_get_recent_draws_returns_descending_with_limit`
- `test_get_recent_draws_zero_or_negative_raises_value_error`
- `test_get_recent_draws_more_than_available_returns_all`
- `test_get_all_draws_returns_ascending`
- `test_get_all_draws_empty_storage_returns_empty_list`
- `test_get_draw_returns_matching_row_or_none`
- `test_get_draw_rejects_non_positive_input`

## `projects/lotto_predictor_v2/tests/cache/test_cache_status.py`

**Functions:**
- `test_status_beoinn_empty_storage_reports_missing_checkpoint_and_insufficient`
- `test_status_insufficient_draws_flag_when_below_required`
- `test_status_expired_checkpoint_flag_when_older_than_freshness`
- `test_status_fresh_and_sufficient_returns_not_stale`
- `test_status_freshness_zero_disables_expiration_check`
- `test_status_parametrized_combinations`

## `projects/lotto_predictor_v2/tests/collector/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/collector/_fakes.py`

**Classes:**
- `FakeClient`
- `FakeStorage`

**Functions:**
- `make_payload`
- `make_draw`

## `projects/lotto_predictor_v2/tests/collector/test_collector_detect.py`

**Classes:**
- `DetectLatestDrawNoTest`

## `projects/lotto_predictor_v2/tests/collector/test_collector_failures.py`

**Classes:**
- `ConsecutiveFailureAbortTest`
- `UnknownFailureTest`

## `projects/lotto_predictor_v2/tests/collector/test_collector_sync.py`

**Classes:**
- `SyncIncrementalTest`
- `SyncRangeTest`

## `projects/lotto_predictor_v2/tests/conftest.py`

**Functions:**
- `_ensure_src_on_path`

## `projects/lotto_predictor_v2/tests/fixtures/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/fixtures/e2e/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/fixtures/e2e/pyinstaller_samples.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/fixtures/mock_responses.py`

**Functions:**
- `clone_payload`

## `projects/lotto_predictor_v2/tests/fixtures/recommender/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/fixtures/recommender/mock_stats.py`

**Functions:**
- `_base_number_frequency`
- `_base_trend_weights`
- `_base_consecutive_gaps`
- `build_pattern_stats`
- `recommender_stats`
- `trend_shifted_stats`
- `invalid_missing_frequency_stats`
- `invalid_section_distribution_stats`

## `projects/lotto_predictor_v2/tests/game_logic/__init__.py`

_(no top-level symbols)_

## `projects/lotto_predictor_v2/tests/game_logic/test_engine.py`

**Classes:**
- `RecommendationEngineTest`

## `projects/lotto_predictor_v2/tests/test_analytics_integration.py`

**Functions:**
- `_load_fixture`
- `_build_500_draws`
- `_import_cache_contract`
- `_import_patterns_contract`
- `test_500회차_데이터를_로드해_통계_엔진과_추천기까지_연결하는_골격`

## `projects/lotto_predictor_v2/tests/test_cache_store.py`

**Functions:**
- `_load_fixture`
- `_import_cache_contract`
- `cache_hit_fixture`
- `cache_expired_fixture`
- `test_json_파일_기반_저장소의_cache_hit_miss_동작_골격`
- `test_cache_만료와_무효화_처리_골격`
- `test_동시성_파일_락_시나리오_골격`

## `projects/lotto_predictor_v2/tests/test_lotto_collector.py`

**Classes:**
- `FakeResponse`
- `SequencedSession`
- `FakeFetcher`

**Functions:**
- `temp_storage`
- `test_정상_회차_응답을_파싱해_저장한다`
- `test_네트워크_오류와_타임아웃은_재시도_후_성공한다`
- `test_비정상_응답은_명시적으로_실패한다`
- `test_500회차_일괄_수집시_rate_limit_대응_골격`

## `projects/lotto_predictor_v2/tests/test_patterns.py`

**Classes:**
- `PatternAnalyticsTest`

## `projects/lotto_predictor_v2/tests/test_pyinstaller_e2e.py`

**Functions:**
- `_completed_process`
- `_parse_recommendations`
- `fake_subprocess_run`
- `test_pyinstaller_onefile_빌드_dry_run_성공_검증`
- `test_단일_실행_파일이_전체_파이프라인을_완료한다`
- `test_네트워크_차단_환경에서_캐시_fallback_동작을_검증한다`
- `test_windows_macos_hiddenimports_누락을_체크한다`

## `projects/lotto_predictor_v2/tests/test_recommender.py`

**Functions:**
- `test_5조합_추천결과는_형식과_범위_중복_계약을_만족한다`
- `test_빈도_구간_홀짝_패턴_가중치가_추천점수와_조합에_반영된다`
- `test_통계입력_누락과_비정상값은_명시적_예외로_차단되어야한다`
- `test_최근_트렌드_가중치가_바뀌면_추천결과도_함께_변한다`
- `_top_pool`

## `projects/lotto_predictor_v2/tests/test_report.py`

**Functions:**
- `_make_stats`
- `_make_combinations`
- `test_report_contains_contract_lines_for_api_source`
- `test_report_contains_cache_fallback_lines_for_cache_source`
- `test_report_combination_lines_match_contract_regex`
- `test_report_header_includes_generation_time`
- `test_report_validates_inputs`
- `test_write_report_appends_newline_if_missing`

## `projects/meeting_stt_app/app/__init__.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/audio/__init__.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/audio/capture.py`

**Classes:**
- `CaptureThread`

## `projects/meeting_stt_app/app/audio/devices.py`

**Classes:**
- `Device`

**Functions:**
- `detect_compute_device`
- `enumerate_devices`

## `projects/meeting_stt_app/app/audio/mixer.py`

**Classes:**
- `AudioMixer`

**Functions:**
- `to_mono_float32`
- `resample_to_16k`
- `rms`

## `projects/meeting_stt_app/app/config.py`

**Classes:**
- `AppSettings`

**Functions:**
- `_config_path`
- `resolve_save_root`

## `projects/meeting_stt_app/app/io/__init__.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/io/recorder.py`

**Classes:**
- `WavRecorder`

## `projects/meeting_stt_app/app/io/session.py`

**Classes:**
- `RecordingSession`

## `projects/meeting_stt_app/app/io/transcript_writer.py`

**Classes:**
- `TranscriptWriter`

**Functions:**
- `_fmt_ts`

## `projects/meeting_stt_app/app/main.py`

**Classes:**
- `PipelineController`

**Functions:**
- `_now_iso`
- `_new_session_id`
- `main`

## `projects/meeting_stt_app/app/qt_compat.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/stt/__init__.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/stt/transcriber.py`

**Classes:**
- `Transcriber`

## `projects/meeting_stt_app/app/stt/types.py`

**Classes:**
- `TranscriptChunk`

## `projects/meeting_stt_app/app/stt/worker.py`

**Classes:**
- `TranscribeWorker`

## `projects/meeting_stt_app/app/ui/__init__.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/ui/main_window.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/app/ui/widgets.py`

_(no top-level symbols)_

## `projects/meeting_stt_app/build.py`

**Functions:**
- `run_selftest`
- `run_pyinstaller`
- `main`

## `projects/meeting_stt_app/build_onedir.py`

**Functions:**
- `_parse_args`
- `_ensure_pyinstaller_available`
- `_build_command`
- `main`

## `projects/meeting_stt_app/meeting_stt.py`

**Functions:**
- `_check_devices`
- `main`

## `projects/meeting_stt_app/scripts/synthetic_audio_headless_selftest.py`

**Classes:**
- `AudioSpec`
- `ValidationResult`

**Functions:**
- `parse_args`
- `validate_spec`
- `synthesize_samples`
- `write_wav`
- `read_wav_samples`
- `rms`
- `estimate_frequency`
- `validate_wav`
- `write_report`
- `main`

## `projects/meeting_stt_app/tests/selftest_pipeline.py`

**Classes:**
- `FakeTranscriber`

**Functions:**
- `_sine`
- `_check`
- `test_imports`
- `test_resolve_save_root`
- `test_mixer_chunk`
- `test_pipeline_e2e`
- `test_real_whisper_optional`
- `main`

## `projects/meeting_stt_app/tests/test_audio_mixer.py`

**Functions:**
- `_block`
- `_sine`
- `test_to_mono_float32_int16_정규화`
- `test_to_mono_float32_다채널_평균`
- `test_resample_to_16k_shape_rate`
- `test_rms_값`
- `test_믹싱_번갈아_push_정렬`
- `test_믹싱_bulk_push_정렬`
- `test_믹싱_부분_겹침`
- `test_합성_사인파_이중스트림_헤드리스`
- `test_max_chunk_sec_컷`
- `test_vad_무음_tail_컷`
- `test_flush_잔여_반환`
- `test_단일_소스_마이크_단독`
- `test_단일_소스_loopback_단독`
- `test_2소스_파트너_영구부재_holdoff_통과`
- `test_capture_device_none_무동작`
- `test_level_changed_시그널`
- `_run_all`

## `projects/minesweeper-baseline/minesweeper.py`

**Classes:**
- `GameState`
- `Cell`
- `Board`

**Functions:**
- `create_board`
- `place_mines`
- `reveal_cell`
- `toggle_flag`
- `check_game_state`
- `check_win`
- `check_lose`
- `_make_header`
- `render_board`
- `print_game_over`
- `parse_command`
- `_parse_args`
- `_handle_command`
- `main`

## `projects/minesweeper-baseline/src/__init__.py`

_(no top-level symbols)_

## `projects/minesweeper-baseline/src/game_logic.py`

**Classes:**
- `Cell`
- `Coord`
- `GameState`

**Functions:**
- `_in_bounds`
- `_clone_board`
- `getNeighborCoords`
- `_with_adjacent_counts`
- `createGame`
- `getGameStatus`
- `_cascade_open`
- `openCell`
- `toggleFlag`

## `projects/minesweeper-baseline/tests/conftest.py`

_(no top-level symbols)_

## `projects/minesweeper-baseline/tests/test_game_logic.py`

**Functions:**
- `test_create_game_keeps_first_click_safe`
- `test_open_mine_transitions_to_lost`
- `test_toggle_flag_works_only_for_closed_cells`
- `test_cascade_open_opens_neighbors_for_zero_adjacent`
- `test_win_transition_when_all_safe_opened`

## `projects/minesweeper-baseline/tests/test_minesweeper_unit.py`

**Functions:**
- `ms`
- `_get`
- `_cells_iter`
- `_cell`
- `_cell_get`
- `_count_mines`
- `_count_revealed_safe_cells`
- `test_create_board_defaults`
- `test_create_board_rejects_invalid_mine_count`
- `test_parse_command_reveal`
- `test_parse_command_flag`
- `test_parse_command_rejects_invalid`
- `test_place_mines_keeps_first_click_safe`
- `test_reveal_cell_skips_flagged_cell`
- `test_reveal_cell_cascade_on_zero_adjacent`
- `test_toggle_flag_toggles_state`
- `test_check_game_state_lose_after_revealing_mine`
- `test_check_game_state_win_when_all_safe_revealed`
- `test_render_board_returns_ascii_grid`
- `test_render_board_reveal_all_shows_mine_symbol`

## `projects/minesweeper/agents/architect-agent/tools/ast_grep.py`

**Functions:**
- `run_ast_grep`

## `projects/minesweeper/agents/architect-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `projects/minesweeper/agents/architect-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `propose`
- `apply`
- `test`

## `projects/minesweeper/agents/architect-agent/tools/file_handler.py`

**Functions:**
- `read_file`
- `write_file`
- `list_files`

## `projects/minesweeper/agents/architect-agent/tools/lsp_hover.py`

**Functions:**
- `lsp_goto_definition`

## `projects/minesweeper/agents/architect-agent/tools/mcp_client.py`

**Functions:**
- `call_mcp_tool`

## `projects/minesweeper/agents/architect-agent/tools/mcp_exa_search.py`

**Functions:**
- `exa_search`

## `projects/minesweeper/agents/architect-agent/tools/memory_pruner.py`

**Functions:**
- `prune_text`

## `projects/minesweeper/agents/architect-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/ast_grep.py`

**Functions:**
- `run_ast_grep`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `propose`
- `apply`
- `test`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/file_handler.py`

**Functions:**
- `read_file`
- `write_file`
- `list_files`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/lsp_hover.py`

**Functions:**
- `lsp_goto_definition`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/mcp_client.py`

**Functions:**
- `call_mcp_tool`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/mcp_exa_search.py`

**Functions:**
- `exa_search`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/memory_pruner.py`

**Functions:**
- `prune_text`

## `projects/minesweeper/agents/logicdeveloper-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `projects/minesweeper/agents/uideveloper-agent/tools/ast_grep.py`

**Functions:**
- `run_ast_grep`

## `projects/minesweeper/agents/uideveloper-agent/tools/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `projects/minesweeper/agents/uideveloper-agent/tools/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `propose`
- `apply`
- `test`

## `projects/minesweeper/agents/uideveloper-agent/tools/file_handler.py`

**Functions:**
- `read_file`
- `write_file`
- `list_files`

## `projects/minesweeper/agents/uideveloper-agent/tools/lsp_hover.py`

**Functions:**
- `lsp_goto_definition`

## `projects/minesweeper/agents/uideveloper-agent/tools/mcp_client.py`

**Functions:**
- `call_mcp_tool`

## `projects/minesweeper/agents/uideveloper-agent/tools/mcp_exa_search.py`

**Functions:**
- `exa_search`

## `projects/minesweeper/agents/uideveloper-agent/tools/memory_pruner.py`

**Functions:**
- `prune_text`

## `projects/minesweeper/agents/uideveloper-agent/tools/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `pyinstaller_hooks/hook-ast_grep_py.py`

_(no top-level symbols)_

## `repo_shortcuts.py`

**Functions:**
- `_nearest_git_root`
- `resolve_repo_path`
- `handle_repo_shortcut`

## `run_eval_loop.py`

**Functions:**
- `main`
- `extract_reasoning`

## `run_factory_cli.py`

**Functions:**
- `_load_dotenv`
- `_safe_project_id`
- `_resolve_projects_root`
- `_run_skill_creator`
- `_run_skill_spec`
- `_run_preflight`
- `_run_skill_eval`
- `_run_skill_promote`
- `_run_interview_subcommand`
- `_run_setup_subcommand`
- `_run_worker_subcommand`
- `_run_nlm_subcommand`
- `_run_check_nlm_subcommand`
- `_run_nightly_start`
- `_run_nightly_stop`
- `_run_nightly_status`
- `_run_nightly_tick`
- `_run_warning_summary_subcommand`
- `_run_warning_repair_subcommand`
- `_run_warning_override_subcommand`
- `_run_warning_stats_subcommand`
- `_run_warning_export_subcommand`
- `_run_resume_subcommand`
- `_is_help_arg`
- `_is_meta_arg`
- `_run_setup_gate`
- `_invoke_nlm_app`
- `_launch_interactive_mode`
- `main`

## `scripts/af_doctor.py`

**Classes:**
- `DoctorResult`

**Functions:**
- `check_python`
- `check_git`
- `check_git_dirty`
- `check_providers`
- `check_hooks`
- `check_pytest`
- `check_dogfood_root`
- `run_checks`
- `format_text`
- `format_json`
- `_exit_code`
- `main`

## `scripts/af_project_inspect.py`

**Functions:**
- `_git_info`
- `_detect_manifests`
- `_pyproject_has_pytest`
- `_detect_test_indicators`
- `_detect_entrypoint_candidates`
- `_detect_docs`
- `_build_risks`
- `_recommend_next_steps`
- `_find_nested_test_file`
- `_count_py_files`
- `inspect_project`
- `format_markdown`
- `main`

## `scripts/af_sandbox.py`

**Functions:**
- `_load_json`
- `_save_json`
- `_merge_claude_settings`
- `_cmd_off`
- `_cmd_on`
- `_cmd_status`
- `main`

## `scripts/af_symbols.py`

**Functions:**
- `build_symbols_index`
- `main`

## `scripts/agent_model_selector.py`

**Functions:**
- `resolve_model_id`
- `select_model`
- `log_routing`
- `store_pending_escalation`
- `get_pending_escalation`
- `clear_pending_escalation`

## `scripts/blast_radius.py`

**Functions:**
- `_normalize`
- `_validate_tier`
- `classify_path`
- `_has_tier3_content`
- `classify_with_content`
- `required_agents`
- `_cli`

## `scripts/blueprint_updater.py`

**Functions:**
- `_git`
- `_detect_workspace`
- `_changed_files`
- `_new_files`
- `_deleted_files`
- `_all_core_maxdepth1`
- `_registered_core_files`
- `_remove_section_0_rows`
- `_diff_content`
- `_short_commit`
- `_read_version`
- `_should_run_debounce`
- `_has_trigger_files`
- `_llm_changelog`
- `_fallback_changelog`
- `_extract_ast_symbols`
- `_changed_public_symbols`
- `_module_doc_summary`
- `_changed_core_files`
- `_update_section_3_auto_summary`
- `_update_section_0`
- `full_sync`
- `_already_logged`
- `_prepend_to_section_12`
- `_update_header_metadata`
- `_atomic_write`
- `update_blueprint`
- `main`

## `scripts/build_llm_wiki.py`

**Functions:**
- `_git`
- `_short_commit`
- `_make_frontmatter`
- `_parse_blueprint`
- `_slug_text`
- `_slugify_blueprint_heading`
- `_split_blueprint_sections`
- `_parse_code_review`
- `_slugify_code_review_section`
- `_split_code_review_sections`
- `_parse_open_items`
- `_build_index`
- `_build_codebase_tree`
- `_build_architecture`
- `_build_review_patterns`
- `_build_open_items`
- `_build_symbols`
- `_build_blueprint_index`
- `_build_blueprint_section`
- `_build_code_review_index`
- `_build_code_review_section`
- `_build_source_refs`
- `build`
- `main`

## `scripts/build_resume_docx.py`

**Functions:**
- `_make_rpr`
- `_make_run`
- `make_p`
- `make_empty_p`
- `insert_after`
- `insert_sequence`
- `make_image_p`
- `build_stock_analyzer_content`
- `replace_stock_analyzer`
- `build_af_content`
- `main`

## `scripts/build_review_bundle.py`

**Functions:**
- `_detect_workspace`
- `_load_pending`
- `_resolve_paths`
- `run`
- `main`

## `scripts/check_changed_text_integrity.py`

**Classes:**
- `IntegrityIssue`

**Functions:**
- `_run_git`
- `resolve_repo_root`
- `list_changed_paths`
- `load_revision_bytes`
- `check_paths_against_revision`
- `main`

## `scripts/check_design_pending.py`

**Functions:**
- `_detect_workspace`
- `_load_fired`
- `_coerce_float`
- `_normalize_entry`
- `_save_fired`
- `main`

## `scripts/check_model_escalation.py`

**Functions:**
- `_detect_workspace`
- `main`

## `scripts/check_pending_review.py`

**Functions:**
- `_detect_workspace`
- `_inject_model_override`
- `_agents_for_tier`
- `_all_external_providers_unavailable`
- `_atomic_write`
- `main`

## `scripts/check_staged_design_review.py`

**Functions:**
- `_extract_block_sections`
- `_map_doc_to_queue_fname`
- `_record_verdicts_to_fired_marker`
- `_reset_verdict_in_fired_marker`
- `_repo_root`
- `_staged_files`
- `load_latest_design_verdicts`
- `find_blocked`
- `find_unreviewed`
- `_external_provider_status`
- `main`

## `scripts/claude_session_bridge.py`

_(no top-level symbols)_

## `scripts/clean_agents_yaml.py`

**Functions:**
- `clean_yaml`

## `scripts/cli_hook_bridge.py`

**Functions:**
- `_configure_stdout`
- `main`

## `scripts/code_review_updater.py`

**Functions:**
- `_git`
- `_detect_workspace`
- `_changed_files`
- `_diff_content`
- `_branch`
- `_short_commit`
- `_llm_review`
- `_atomic_write`
- `_atomic_append`
- `_update_last_modified`
- `_should_run_debounce`
- `_last_logged_commit`
- `update_code_review_doc`
- `main`

## `scripts/codebase_symbols.py`

**Functions:**
- `_is_excluded`
- `extract_symbols`
- `extract_csharp_symbols`
- `_extract_path_symbols`
- `collect_symbols`
- `render`
- `build`
- `main`

## `scripts/codex_session_bridge.py`

_(no top-level symbols)_

## `scripts/design_review_trigger.py`

**Functions:**
- `_detect_workspace`
- `main`

## `scripts/design_review_watcher.py`

**Functions:**
- `_read_document`
- `_read_project_context`
- `_write_result`
- `_write_notification`
- `_prompt_prefix_for_type`
- `process_review`
- `_write_notification_skip`
- `_move_to_failed`
- `_scan_pending_dir`
- `process_queue`
- `_write_pid`
- `_remove_pid`
- `_has_actionable_pending`
- `run_daemon`
- `run_sync_single`
- `main`

## `scripts/destructive_guard_proxy.py`

**Functions:**
- `_parse_args`
- `main`

## `scripts/enqueue_agent_review.py`

**Functions:**
- `_is_review_target`
- `_detect_workspace`
- `main_for_path`
- `main`

## `scripts/enqueue_staged_review.py`

**Functions:**
- `_detect_workspace`
- `_staged_files`
- `_staged_blob_hash`
- `_script_dir`
- `_pending_path`
- `_load_pending`
- `_save_pending`
- `_mark_seen_staged_hash`
- `_already_enqueued_for_staged_hash`
- `enqueue_staged`
- `main`

## `scripts/fix_runner_cwm.py`

_(no top-level symbols)_

## `scripts/gemini_session_bridge.py`

_(no top-level symbols)_

## `scripts/gen_resume_diagrams.py`

**Functions:**
- `rbox`
- `arrow`
- `make_architecture`
- `make_workflow`
- `make_pipeline`

## `scripts/generate_agents_md.py`

**Classes:**
- `AgentRecord`

**Functions:**
- `_resolve_path`
- `_read_text_with_fallback`
- `_load_yaml`
- `_first_non_empty_str`
- `_coerce_type_role`
- `_extract_role`
- `_extract_name`
- `_extract_dashboard_overrides`
- `_detect_role_type`
- `_resolve_core_agent_emoji`
- `_collect_yaml_files`
- `_relative_posix`
- `collect_records`
- `_md_escape`
- `render_roster`
- `render_markdown`
- `parse_args`
- `main`

## `scripts/hook_runner.py`

**Functions:**
- `_project_root`
- `_detect_workspace`
- `_find_venv_python`
- `_resolve_script`
- `_read_hook_stdin_once`
- `_extract_file_path`
- `_portable_fp`
- `_log_hook_event`
- `_post_edit_py_compile`
- `_post_edit_enqueue`
- `_post_edit_code_review`
- `_post_edit_blueprint`
- `_post_edit_design_review`
- `_post_edit_test`
- `_pre_bash_review_gate`
- `_detect_escalation_triggers`
- `_post_agent_record`
- `_apply_test_gap_verdict`
- `_test_gap_report_path`
- `_write_test_gap_report`
- `_clear_test_gap_report`
- `_post_commit_clear`
- `main`

## `scripts/import_external_skill_candidates.py`

_(no top-level symbols)_

## `scripts/install_scheduler.py`

**Functions:**
- `install`
- `uninstall`
- `_install_macos`
- `_uninstall_macos`
- `_install_linux`
- `_uninstall_linux`
- `_install_windows`
- `_uninstall_windows`
- `_find_python`
- `_find_python_windows`
- `_ensure_log_dir`

## `scripts/measure_goal_overlap.py`

**Functions:**
- `_extract_goals_section`
- `_tokenize`
- `_jaccard`
- `main`

## `scripts/migrate_registry.py`

**Functions:**
- `_read_yaml`
- `main`

## `scripts/migrate_workitem_e2e.py`

**Functions:**
- `_migrate_tasks_file`
- `_migrate_verification_file`
- `main`

## `scripts/nightly_summary.py`

**Functions:**
- `_render_modules_section`
- `render_summary`
- `write_summary`

## `scripts/nightly_tick.py`

**Functions:**
- `_sigterm_handler`
- `deadline_exceeded`
- `_acquire_flock`
- `_release_flock`
- `_dispatch_actions`
- `_run_task`
- `_sweep_verify_handoffs`
- `tick_once`
- `main`

## `scripts/project_context_git_sync.py`

**Functions:**
- `_safe_id`
- `_is_git_repo`
- `_git_pull`
- `_git_push`
- `main`

## `scripts/project_context_sync.py`

**Functions:**
- `load_dotenv_simple`
- `load_dotenv_override`
- `now_iso`
- `safe_id`
- `normalize_match_key`
- `sync_project_id`
- `_same_path`
- `_project_sync_id_for_path`
- `_is_repo_root_alias`
- `resolve_project_root`
- `resolve_global_root`
- `_normalize_newlines`
- `read_text`
- `write_text`
- `b64e`
- `b64d`
- `http_json`
- `try_read_json`
- `_include_text_file`
- `_is_excluded`
- `_include_tree`
- `_include_root_files`
- `_parse_exclude_globs`
- `_apply_exclude_globs`
- `_collect_run_files`
- `collect_snapshot`
- `collect_global_snapshot`
- `write_snapshot`
- `make_scope_key`
- `parse_project_inputs`
- `main`

## `scripts/refresh_lotto_seed.py`

**Functions:**
- `_fetch_draw`
- `_detect_latest`
- `main`

## `scripts/replace_react_loop.py`

_(no top-level symbols)_

## `scripts/review_consensus.py`

**Functions:**
- `_surrounding_code`
- `_enclosing_function`
- `_find_callees`
- `_find_callers`
- `_find_tests`
- `collect_evidence`
- `main`

## `scripts/review_gate.py`

**Functions:**
- `_extract_verdict_from_content`
- `_extract_t3_required_from_content`
- `_deterministic_t3_skip_candidate`
- `_critic_t3_advisory`
- `_allows_t3_skip`
- `_is_always_tier3`
- `_telemetry_skip_enacted`
- `_queue_path`
- `_lock_path`
- `_state_lock`
- `_log_path`
- `_load_state`
- `_save_state`
- `_log_event`
- `_required_tiers_for`
- `_is_staged_review_target`
- `_staged_review_py_files`
- `is_gate_blocked`
- `record_review_done`
- `_make_claim_id`
- `downgrade_blast_tier`
- `clear_committed_files`
- `_detect_workspace`
- `_cli`

## `scripts/review_metrics_logger.py`

**Functions:**
- `_queue_dir`
- `_metrics_path`
- `_skip_audit_path`
- `_git_sha`
- `_append_jsonl`
- `parse_findings_count`
- `parse_extension_log_count`
- `append_metric`
- `append_skip_audit`
- `_load_records`
- `_load_skip_audit_records`
- `compute_report`
- `compute_t3_telemetry_skip`

## `scripts/review_metrics_report.py`

**Functions:**
- `_detect_workspace`
- `main`

## `scripts/run.py`

**Functions:**
- `_safe_script`
- `main`

## `scripts/session_bridge.py`

**Classes:**
- `SessionBridgeProvider`

**Functions:**
- `safe_id`
- `safe_key`
- `now_iso`
- `truncate`
- `resolve_global_root`
- `load_json`
- `save_json`
- `read_env_value`
- `read_windows_user_env`
- `is_noise`
- `_extract_text_chunks`
- `_join_chunks`
- `_extract_codex_chat_text`
- `_extract_generic_role_content_text`
- `get_provider`
- `resolve_sessions_root`
- `iter_session_files`
- `collect_new_events`
- `write_memory_entries`
- `_resolve_user_key`
- `run_bridge`
- `main`
- `main_for_provider`

## `scripts/sync_claude_memory.py`

**Functions:**
- `_load_dotenv`
- `_now_iso`
- `_mtime_iso`
- `_path_to_claude_key`
- `_find_memory_dir`
- `_http_json`
- `_supabase_env`
- `_fetch_remote_row`
- `_normalize_newlines`
- `_write_atomic`
- `_print_json`
- `_push`
- `_pull`
- `main`

## `scripts/sync_provider_instructions.py`

**Functions:**
- `_repo_root`
- `_read_instructions`
- `_inject_common_block`
- `_generate_agents_md`
- `sync`
- `main`

## `scripts/sync_skill_registry.py`

**Functions:**
- `now_iso`
- `safe_id`
- `read_yaml`
- `write_yaml`
- `to_portable`
- `load_meta`
- `discover_dir_skills`
- `discover_forge_skills`
- `normalize_install_candidates`
- `sync_registry`
- `main`

## `scripts/t3_classifier.py`

**Classes:**
- `T3Decision`
- `_CosmeticAstNormalizer`

**Functions:**
- `_normalize_path`
- `_git`
- `_read_head_file`
- `_read_worktree_file`
- `_git_diff`
- `_changed_diff_lines`
- `_summarize_diff`
- `_risk_tokens_present`
- `_normalized_ast_dump`
- `_is_python_cosmetic_only`
- `classify_t3_requirement`
- `record_skip_telemetry`
- `_cli`

## `scripts/t3_skip_report.py`

**Functions:**
- `_detect_workspace`
- `_telemetry_path`
- `load_records`
- `build_report`
- `main`

## `scripts/test_gap_analyzer.py`

**Classes:**
- `TestGap`
- `TestGapReport`

**Functions:**
- `_norm`
- `_is_test_file`
- `_is_candidate_python_file`
- `_read_text`
- `_git`
- `_is_git_tracked`
- `_is_git_ignored`
- `_untracked_python_files_from_fs`
- `changed_files_from_pending`
- `changed_files_from_git`
- `_synthetic_added_diff`
- `git_diff`
- `find_related_tests`
- `_combined_related_test_text`
- `_file_diff_excerpt`
- `_extract_params`
- `_extract_wiring_candidates`
- `_find_production_callers`
- `_any_caller_passes_param`
- `_has_deferred_marker`
- `_is_subprocess_quoting_risk`
- `_has_cross_platform_quoted_path_tests`
- `_has_frozen_build_evidence`
- `_is_packaging_runtime_path_risk`
- `analyze_diff`
- `_format_text`
- `main`

## `scripts/verify_handoff_checker.py`

**Functions:**
- `_check_report`
- `_propagate_block_to_gate`
- `_staged_reports`
- `main`

## `scripts/write_resume_brief.py`

**Functions:**
- `refresh_resume_briefs`
- `main`

## `set_utf8.py`

**Functions:**
- `main`

## `setup-dev.py`

_(no top-level symbols)_

## `setup_dev.py`

**Functions:**
- `_add_scripts_to_path_windows`
- `main`

## `skills/ai_funnel_routing/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/core/ast_grep.py`

**Functions:**
- `run_ast_grep`

## `skills/core/cortex.py`

**Classes:**
- `CortexClient`

**Functions:**
- `_embed`
- `propose`
- `apply`
- `test`

## `skills/core/file_handler.py`

**Functions:**
- `read_file`
- `write_file`
- `list_files`

## `skills/core/lsp_hover.py`

**Functions:**
- `lsp_goto_definition`

## `skills/core/mcp_client.py`

**Functions:**
- `call_mcp_tool`

## `skills/core/mcp_exa_search.py`

**Functions:**
- `exa_search`

## `skills/core/memory_pruner.py`

**Functions:**
- `prune_text`

## `skills/core/retrofit_cortex.py`

**Functions:**
- `retrofit_agents`

## `skills/core_memory/skill.py`

**Functions:**
- `_safe_id`
- `_agent_id_from_ctx`
- `_resolve_scope`
- `_default_store_scope`
- `_get_local_data_dir`
- `_get_global_data_dir`
- `_memory_roots`
- `_category_dirs`
- `_legacy_memory_path`
- `_store_root`
- `store`
- `retrieve`
- `search`
- `propose`
- `apply`
- `test`

## `skills/create_design_system/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/css_styling/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/data_visualize/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/domain/langchain/langchain_guidelines.py`

**Functions:**
- `_read_skill_md`
- `get_framework_selection_guideline`
- `get_langchain_dependencies_guideline`
- `get_langchain_fundamentals_guideline`
- `get_langchain_middleware_guideline`
- `get_langchain_rag_guideline`
- `get_langgraph_fundamentals_guideline`
- `get_langgraph_human_in_the_loop_guideline`
- `get_langgraph_persistence_guideline`
- `get_deep_agents_core_guideline`
- `get_deep_agents_memory_guideline`
- `get_deep_agents_orchestration_guideline`

## `skills/dp/skill.py`

**Functions:**
- `_validate`
- `_norm`
- `propose`
- `apply`
- `test`

## `skills/eval/langsmith_eval.py`

**Functions:**
- `trace_execution`
- `summarize_failure`
- `generate_eval_dataset`
- `_extract_error_line`

## `skills/evaluator/__init__.py`

_(no top-level symbols)_

## `skills/evaluator/doc_qa/skill.py`

**Classes:**
- `DocQASkill`

## `skills/evaluator/generate_eval_dataset/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`
- `_parse_jsonl`
- `_extract_run_info`
- `_calc_duration_ms`
- `_parse_ts`
- `_balance_dataset`
- `_deduplicate_cases`
- `_filter_duration_outliers`
- `_percentile`
- `_calc_dataset_quality`

## `skills/evaluator/summarize_failure/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`
- `_parse_jsonl`
- `_collect_error_texts`
- `_classify_failure`
- `_extract_root_cause`
- `_generate_suggestions`
- `_find_similar_failures`
- `_trace_error_chain`
- `_detect_duration_anomaly`
- `_calc_duration_between`
- `_calc_refined_severity`

## `skills/evaluator/trace_execution/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`
- `_parse_jsonl`
- `_build_skill_call`
- `_calc_duration_ms`
- `_parse_ts`
- `_summarize_dict`
- `_detect_timeline_anomalies`
- `_detect_skill_errors`

## `skills/forge/api_security_vetting.py`

**Functions:**
- `_security_checks`
- `vet_api`
- `propose`
- `apply`
- `test`
- `main`

## `skills/forge/core_module.py`

**Functions:**
- `setup_logging`
- `cmd_initialize`
- `cmd_analyze`
- `cmd_terminate`
- `main`

## `skills/forge/database_performance_tuning.py`

_(no top-level symbols)_

## `skills/forge/db_optimizer.py`

**Functions:**
- `_analyze_query`
- `optimize_db`
- `propose`
- `apply`
- `test`
- `main`

## `skills/forge/edomae_sushi_shikomi_playbook.py`

**Functions:**
- `get_available_ingredients`
- `find_recipe_steps`
- `handle_prepare`
- `handle_status`
- `handle_recipe`
- `handle_report`
- `main`

## `skills/forge/file_handler.py`

**Functions:**
- `read_file`
- `write_file`
- `list_files`

## `skills/forge/infrastructure_scaler.py`

**Functions:**
- `_build_scale_plan`
- `scale_report`
- `propose`
- `apply`
- `test`
- `main`

## `skills/forge/needs_issue.py`

_(no top-level symbols)_

## `skills/forge/new_skill.py`

_(no top-level symbols)_

## `skills/forge/omakase_service_pacing_control.py`

_(no top-level symbols)_

## `skills/forge/perishable_inventory_control.py`

**Functions:**
- `load_inventory`
- `save_inventory`
- `add_item`
- `update_item`
- `remove_item`
- `list_items`
- `alert_items`
- `main`

## `skills/forge/precision_knife_techniques.py`

**Classes:**
- `MasterChef`

**Functions:**
- `main`

## `skills/forge/scalable_api_architecture.py`

_(no top-level symbols)_

## `skills/forge/seasonal_ingredient_procurement.py`

**Functions:**
- `load_history`
- `save_history`
- `handle_recommend`
- `handle_order`
- `handle_history`
- `main`

## `skills/forge/seasonal_omakase_inventory_optimization.py`

_(no top-level symbols)_

## `skills/forge/zero_downtime_deployment_playbook.py`

_(no top-level symbols)_

## `skills/frontend_ui_ux/skill.py`

**Classes:**
- `FrontendUIUXSkill`

## `skills/generate_image/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/gherkin_sdd_authoring/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/git_master/skill.py`

**Classes:**
- `GitMasterSkill`

## `skills/graphify/skill.py`

**Classes:**
- `GraphifySkill`

**Functions:**
- `_exists`

## `skills/hash_edit/skill.py`

**Functions:**
- `get_file_with_hashes`
- `find_hash`
- `apply_edit`
- `apply_block_edit`
- `get_edit_history`

## `skills/hashline_edit/skill.py`

**Classes:**
- `HashlineEditSkill`

## `skills/hound_librarian/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/issue_tracker/skill.py`

**Functions:**
- `_load_issues`
- `_save_issues`
- `propose`
- `apply`
- `test`

## `skills/liability_traceability_design/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/new_skill/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/perform_web_design_review/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/react_coding/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/research_assistant/skill.py`

**Functions:**
- `_extract_answer`
- `_query_notebooklm`
- `propose`
- `apply`
- `test`

## `skills/roi_defense_modeling/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/state_machine_exception_planning/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/stitch_design/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/trigger_rule_design/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/user_flow_optimization/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `skills/zero_integration_parsing_spec/skill.py`

**Functions:**
- `propose`
- `apply`
- `test`

## `start_db.py`

**Functions:**
- `_resolve_target`
- `_global_user_key`
- `_run`
- `main`

## `start_git.py`

**Functions:**
- `_resolve_target`
- `main`

## `start_sync.py`

**Functions:**
- `_run`
- `main`

## `test_fallback.py`

**Functions:**
- `divide_numbers`

## `tests/check_models.py`

_(no top-level symbols)_

## `tests/conftest.py`

**Functions:**
- `_cleanup_test_runtime_root`
- `_reset_run_event_store_singleton`
- `_af_isolate_skill_registry_writes`
- `tmp_path`

## `tests/e2e/__init__.py`

_(no top-level symbols)_

## `tests/e2e/conftest.py`

**Functions:**
- `sim_workspace`
- `no_dispatch`
- `fail_dispatch`

## `tests/e2e/tick_simulator.py`

**Functions:**
- `test_48_ticks_no_crash`
- `test_watchdog_escalation_after_no_progress`
- `test_alert_flag_after_consecutive_failures`

## `tests/run_verify_agent.py`

**Functions:**
- `run_verification`

## `tests/test_acceptance_gate.py`

**Classes:**
- `TestExecutionHarnessCliMocked`
- `TestExecutionHarnessLibraryReal`
- `TestExecutionHarnessOther`
- `TestExecutionHarnessServerMocked`
- `TestAcceptanceGate`

**Functions:**
- `_cli_goal`
- `_lib_goal`
- `_server_goal`
- `_gui_goal`
- `_none_goal`
- `_fake_proc`

## `tests/test_acceptance_gate_integration.py`

**Classes:**
- `TestVerifiedGoalOkTrue`
- `TestFailedGoalBlocks`
- `TestExecuteDirectPathGated`
- `TestNullContractEmptyVerifyBlocks`
- `TestCannotVerifyNotBlocked`
- `TestDashboardAndReturnOkMatch`
- `TestAlreadyDoneReaggregates`
- `TestParseAcceptanceCriteria`
- `TestBuildEvidenceLedger`

**Functions:**
- `_verified_contract`
- `_cannot_verify_contract`
- `_failed_contract`
- `_unverified_contract`

## `tests/test_af_doctor.py`

**Functions:**
- `test_check_python_always_ok`
- `test_check_git_ok`
- `test_check_git_fail_not_repo`
- `test_check_git_fail_no_git`
- `test_check_git_dirty_clean`
- `test_check_git_dirty_has_changes`
- `test_check_git_dirty_subprocess_fail`
- `test_check_providers_fast_installed`
- `test_check_providers_fast_none_installed`
- `test_check_providers_normal_available`
- `test_check_hooks_git_config`
- `test_check_hooks_missing`
- `test_check_pytest_installed`
- `test_check_pytest_missing`
- `test_check_dogfood_root_exists`
- `test_check_dogfood_root_missing`
- `test_check_dogfood_root_env_override`
- `_sample_checks`
- `test_format_text_contains_icons`
- `test_format_text_shows_fix_hint`
- `test_format_json_structure`
- `test_exit_code_all_ok`
- `test_exit_code_fail`
- `test_exit_code_warn_no_strict`
- `test_exit_code_warn_strict`
- `test_exit_code_fail_takes_priority_over_warn`
- `test_run_checks_fast_returns_list`

## `tests/test_af_project_inspect.py`

**Classes:**
- `TestDetectManifests`
- `TestDetectTestIndicators`
- `TestPyprojectHasPytest`
- `TestFindNestedTestFile`
- `TestDetectEntrypointCandidates`
- `TestDetectDocs`
- `TestBuildRisks`
- `TestRecommendNextSteps`
- `TestFormatMarkdown`
- `TestInspectProject`
- `TestMain`

**Functions:**
- `_doctor_check`
- `_clean_git`
- `_base_docs`
- `_ctx_for_steps`

## `tests/test_af_project_symbols.py`

**Classes:**
- `TestSymbolsStdout`
- `TestSymbolsOutDir`
- `TestSymbolsErrorHandling`
- `TestSymbolsEmptyDir`

**Functions:**
- `_run`

## `tests/test_af_symbols.py`

**Classes:**
- `TestBuildSymbolsIndex`
- `TestMain`
- `TestForwardArgs`
- `TestFrozenBuildParity`

**Functions:**
- `_write_sample_module`

## `tests/test_agent_launcher_cli_dispatch.py`

**Classes:**
- `TestDetectMode`
- `TestBuildArgParserAdHoc`
- `TestBuildArgParserSubcommand`
- `TestIsolateProjectRootForSelfRun`
- `TestEnvFlagConvention`
- `TestPromptMissionTemplateImport`
- `TestSelfRunWorkspaceSplit`

## `tests/test_agent_model_selector.py`

**Classes:**
- `TestSelectModel`
- `TestPendingEscalation`
- `TestResolveModelId`
- `TestLogRouting`

## `tests/test_agent_runner_force_provider.py`

**Classes:**
- `TestForceProviderLogic`

**Functions:**
- `_pick_cli_providers`

## `tests/test_agent_specializer.py`

**Classes:**
- `TestSpecializeForceProvider`

**Functions:**
- `_base_agent`
- `_task`

## `tests/test_agent_worker.py`

**Functions:**
- `_write_task`
- `_run_worker`
- `test_worker_writes_result_atomically`
- `test_worker_bad_task_json`
- `test_worker_missing_tmp_files_cleanup`

## `tests/test_approval_gate_auto_approve.py`

**Functions:**
- `gate`
- `_clear_auto_env`
- `test_default_approve_user_label`
- `test_default_no_auto_marker_in_review_notes`
- `test_explicit_auto_true_marks_approver_auto`
- `test_explicit_auto_with_reason`
- `test_explicit_auto_writes_audit_line`
- `test_explicit_auto_opens_execution`
- `test_env_auto_activates_with_slug_whitelist`
- `test_env_auto_writes_env_marker_in_audit`
- `test_env_auto_no_whitelist_does_not_activate`
- `test_env_auto_slug_not_in_whitelist_does_not_activate`
- `test_env_auto_wildcard_activates_all_slugs`
- `test_env_flag_true_activates`
- `test_env_value_other_than_truthy_does_not_activate`
- `test_env_unset_default_inactive`
- `test_explicit_auto_overrides_when_env_off`
- `test_no_gate_path_returns_false`
- `test_auto_rejected_when_verification_blocked`
- `test_user_approve_can_override_verification_blocked`
- `test_auto_rejected_when_block_decision_blocked`
- `test_user_approve_not_affected_by_block_decision`
- `test_auto_reason_sanitizes_newlines`
- `test_auto_reason_sanitizes_markdown_headers`
- `test_auto_reason_truncates_to_120_chars`
- `test_auto_approve_idempotent_no_audit_accumulation`

## `tests/test_approval_gate_block_decision.py`

**Functions:**
- `_make_gate`
- `_write_json`
- `test_read_block_decision_no_summary`
- `test_read_block_decision_no_phase_marker`
- `test_read_block_decision_missing_decision_file`
- `test_read_block_decision_phase_mismatch`
- `test_read_block_decision_stale`
- `test_read_block_decision_phase_forward_compat`

## `tests/test_approval_gate_domain_gate.py`

**Classes:**
- `TestDomainGateSystemWide`
- `TestDomainGateNonSystemWide`
- `TestDomainGateCheckValidity`
- `TestDomainGateSkipEnv`
- `TestDomainGateNeedsAdr`
- `TestDomainGateBlockCause`

**Functions:**
- `_write`
- `test_verdict_explicit_pass`
- `test_verdict_explicit_block`
- `test_verdict_explicit_needs_adr`
- `test_verdict_checkbox_fallback`
- `test_verdict_multiple_explicit`
- `test_verdict_multiple_checkbox`
- `test_verdict_missing`
- `test_verdict_file_not_found`
- `gate_system_wide`
- `gate_module`
- `gate_isolated`
- `gate_cross_module`
- `_write_domain_review`

## `tests/test_approval_gate_domain_review.py`

**Functions:**
- `_read_source`
- `test_no_invalid_blast_radius_local_token`
- `test_no_invalid_blast_radius_system_token`

## `tests/test_approval_gate_metadata_persistence.py`

**Functions:**
- `_seed_gate`
- `gate`
- `test_approve_preserves_metadata`
- `test_invalidate_preserves_metadata`
- `test_apply_verification_verdict_preserves_metadata`
- `test_no_metadata_fields_backward_compat`

## `tests/test_approval_gate_runtime_workspace.py`

**Functions:**
- `test_single_mode_runtime_workspace_defaults_to_workspace`
- `test_split_mode_runtime_workspace`
- `test_render_injects_gate_decision_report`
- `test_keyword_arg_backward_compat`

## `tests/test_architect_agent.py`

**Classes:**
- `TestLoadBlueprintText`
- `TestExtractSection`
- `TestSectionForStep`
- `TestLoadAcceptedAdrs`
- `TestAdrMatches`
- `TestResolveFinding`
- `TestPatchFinalPlan`
- `TestArchitectFn`

**Functions:**
- `_finding`
- `_plan`

## `tests/test_ast_engine_smoke.py`

**Functions:**
- `test_search_finds_print`
- `test_search_returns_empty_on_no_match`
- `test_replace_substitutes_pattern`
- `test_search_file`
- `test_search_file_nonexistent`
- `test_search_dir`
- `test_detect_lang_python`
- `test_detect_lang_unknown_falls_back`

## `tests/test_blueprint_updater.py`

**Functions:**
- `_minimal_blueprint`
- `test_update_blueprint_writes_section3_auto_summary`
- `test_changed_public_symbols_extracts_toplevel_added`
- `test_changed_public_symbols_attributes_body_only_via_hunk_context`
- `test_changed_public_symbols_empty_when_no_toplevel`
- `test_section3_reflects_changed_symbol_regardless_of_position`

## `tests/test_bootstrap_policy_rules.py`

**Functions:**
- `_get_rules`
- `test_granularity_injected`
- `test_module_task_count_injected`
- `test_only_max_tasks`
- `test_no_granularity_no_injection`
- `test_no_modules_policy_no_injection`
- `test_constraints_still_injected`
- `test_fallback_when_no_policy`

## `tests/test_build_llm_wiki.py`

**Classes:**
- `TestParsers`
- `TestBuild`
- `TestExternalProject`

## `tests/test_build_review_bundle.py`

**Functions:**
- `_script`
- `test_load_pending_empty_when_no_queue`
- `test_load_pending_returns_files`
- `test_load_pending_skips_empty_entries`
- `test_resolve_paths_only_py`
- `test_resolve_paths_skips_missing`
- `test_run_returns_0_when_no_queue`
- `test_run_creates_bundle_file`
- `test_build_full_returns_required_keys`
- `test_build_full_bundle_md_has_all_sections`
- `test_build_full_source_hash_is_hex`
- `test_build_full_detects_risk_flags`
- `test_build_full_respects_100kb_cap`
- `test_save_full_writes_file`
- `test_run_returns_0_on_error`

## `tests/test_builder_cli_fallback.py`

**Functions:**
- `_load_builder`
- `test_builder_uses_cli_provider_when_google_key_missing`
- `test_builder_without_cli_or_google_key_returns_no_api_key`

## `tests/test_builder_multi_pass.py`

**Functions:**
- `_load_builder`
- `test_builder_runs_multi_pass_forge_with_reference_candidate`

## `tests/test_bulk_enrich_trigger_routing.py`

**Classes:**
- `TestBulkEnrichTriggerConsistency`

## `tests/test_capability_intent.py`

**Functions:**
- `test_capability_intent_analyzer_derives_capabilities_and_evidence`

## `tests/test_check_design_pending.py`

**Classes:**
- `TestNormalizeEntry`
- `TestRoundCap`
- `TestRoundCountIncrement`
- `TestLegacyFloatMigration`
- `TestLastVerdictPreserved`
- `TestOscillationDetection`

**Functions:**
- `_make_queue_entry`
- `_write_fired`
- `_read_fired`
- `_run_main`

## `tests/test_check_model_escalation.py`

**Functions:**
- `test_main_returns_early_when_frozen`
- `test_main_runs_without_error_when_no_pending_state`
- `test_main_prints_escalation_when_pending`
- `test_main_clears_pending_after_print`
- `test_main_frozen_build_does_not_clear_pending`

## `tests/test_check_pending_review.py`

**Classes:**
- `TestInjectModelOverride`

## `tests/test_check_staged_design_review.py`

**Classes:**
- `TestLoadLatestVerdicts`
- `TestFindBlocked`
- `TestFindUnreviewed`
- `TestMain`
- `TestMainFailClosed`
- `TestExtractBlockSections`
- `TestMapDocToQueueFname`
- `TestRecordVerdictsToFiredMarker`
- `TestResetVerdictInFiredMarker`

**Functions:**
- `_write_review`

## `tests/test_cli_providers.py`

**Classes:**
- `TestAllowFileEdit`

**Functions:**
- `test_config_paths_allows_cli_only_bootstrap_without_api_keys`
- `test_cli_provider_registry_defaults_and_filtering`
- `test_config_paths_ignores_engine_api_keys_when_disabled`
- `test_build_cli_command_uses_provider_specific_defaults`
- `test_codex_cli_path_override_keeps_exec_subcommand`
- `test_build_cli_command_falls_back_to_windows_roaming_npm_shim`
- `test_gemini_cli_default_alias_omits_model_flag`
- `test_gemini_cli_prompt_prioritizes_task_before_system_context`
- `test_gemini_cli_normalized_default_alias_omits_model_flag`
- `test_codex_cli_combined_prompt_prioritizes_task_and_includes_destructive_guard`
- `test_build_cli_command_uses_stdin_prompt_for_codex_cli`
- `test_claude_cli_append_system_prompt_includes_destructive_guard`
- `test_cli_provider_includes_repo_root_when_workspace_is_nested`
- `test_agent_runner_uses_cli_provider_before_sdk_fallback`
- `test_agent_runner_cli_only_short_task_does_not_require_todo`
- `test_agent_runner_cli_only_still_blocks_complex_task_without_todo`
- `test_execute_cli_chat_persists_failed_launch_state`
- `test_execute_cli_chat_auto_installs_missing_provider_and_retries`
- `test_execute_cli_chat_keeps_not_found_when_auto_install_disabled`
- `test_execute_cli_chat_strips_provider_api_key_env`
- `test_execute_cli_chat_sends_codex_prompt_via_stdin`
- `test_execute_cli_chat_sends_claude_prompt_via_stdin`
- `test_execute_cli_chat_runs_codex_auth_preflight_and_auto_login`
- `test_execute_cli_chat_codex_preflight_stops_on_permission_denied`
- `test_execute_cli_chat_runs_claude_auth_preflight_and_auto_login`
- `test_agent_runner_writes_skill_runtime_feedback`
- `test_compose_prompt_includes_git_state_claude_cli`
- `test_compose_prompt_omits_git_state_when_empty`
- `test_gemini_cli_prompt_git_state_after_workspace`
- `test_codex_cli_prompt_git_state_between_workspace_and_system`
- `test_collect_git_context_returns_empty_for_non_git_dir`

## `tests/test_cli_session_adapter.py`

**Functions:**
- `_read_json`
- `test_prepare_cli_session_writes_claude_hook_settings`
- `test_prepare_cli_session_routes_gemini_hooks_via_generated_defaults_file`
- `test_prepare_cli_session_sets_codex_shell_guard_on_windows`
- `test_prepare_cli_session_seeds_codex_auth_files`
- `test_codex_shell_guard_blocks_destructive_commands_on_windows`
- `test_handle_hook_event_returns_context_and_runs_bridge`
- `test_handle_hook_event_writes_surrogate_payload_safely`
- `test_handle_hook_event_skips_gemini_context_in_headless_mode`
- `test_handle_hook_event_keeps_gemini_context_for_interactive_sessions`

## `tests/test_codebase_symbols.py`

**Functions:**
- `test_extract_symbols_top_level_classes_and_functions`
- `test_extract_symbols_includes_async_functions`
- `test_extract_symbols_excludes_methods_and_nested`
- `test_extract_symbols_empty_source`
- `test_extract_csharp_symbols_types_and_methods`
- `test_extract_csharp_symbols_does_not_treat_primary_constructor_as_method`
- `test_collect_symbols_finds_python_files`
- `test_collect_symbols_recurses_with_posix_keys`
- `test_collect_symbols_ignores_non_python`
- `test_collect_symbols_finds_csharp_files`
- `test_collect_symbols_skips_runtime_and_cache_directories`
- `test_collect_symbols_empty_directory`
- `test_collect_symbols_does_not_modify_source`
- `test_collect_symbols_tolerates_syntax_error`
- `test_collect_symbols_respects_python_encoding_cookie`
- `test_collect_symbols_tolerates_csharp_decode_error`
- `test_collect_symbols_tolerates_decode_error`
- `test_build_returns_markdown_string`
- `test_build_is_deterministic`
- `test_build_empty_directory_returns_string`
- `test_build_accepts_str_path`
- `test_build_renders_csharp_symbols`

## `tests/test_coding_conventions.py`

**Functions:**
- `_iter_py_files`
- `_is_type_def`
- `_collect_type_defs`
- `test_no_duplicate_type_names`
- `_func_name`
- `_collect_abspath_violations`
- `test_no_hardcoded_abspath`

## `tests/test_compact_step2.py`

**Classes:**
- `TestRunBudgetRecord`
- `TestHistoryManagerBudget`
- `TestSkillPackBootstrapper`
- `TestPlanVerifierGate`

**Functions:**
- `reset_run_budget`

## `tests/test_completion_contract.py`

**Functions:**
- `_entry`
- `test_empty_contract_is_not_done`
- `test_all_verified_is_done`
- `test_verified_plus_cannot_verify_is_done`
- `test_unverified_blocks_done`
- `test_failed_blocks_done`
- `test_has_failures_true_only_for_failed`
- `test_has_failures_empty_contract`
- `test_goal_entry_defaults`
- `test_harness_result_is_plain_struct`
- `test_evidence_round_trip`
- `test_entry_round_trip_with_evidence`
- `test_entry_round_trip_without_evidence`
- `test_contract_round_trip_nested`
- `test_empty_contract_round_trip`
- `_mk_state`
- `test_dogfood_state_round_trip_with_contract`
- `test_dogfood_state_round_trip_none_contract`
- `test_dogfood_state_legacy_dict_without_contract_key`
- `test_goal_entry_q_s1_defaults`
- `test_goal_entry_q_s1_round_trip`
- `test_goal_entry_provenance_research`
- `test_goal_entry_legacy_dict_missing_q_s1_fields`
- `test_goal_entry_scenario_preserved_in_contract_round_trip`
- `test_test_manifest_defaults`
- `test_test_manifest_round_trip`
- `test_test_manifest_legacy_dict_missing_fields`
- `test_goal_contract_manifest_none_by_default`
- `test_goal_contract_manifest_round_trip`
- `test_goal_contract_manifest_none_round_trip`
- `test_goal_contract_legacy_dict_missing_manifest`
- `test_goal_contract_full_round_trip_with_manifest_and_q_s1`

## `tests/test_context_window_manager.py`

**Classes:**
- `TestEstimateTokens`
- `TestContextBudget`
- `TestToolTracker`
- `TestHistoryManager`
- `TestKnowledgeInjector`
- `TestContextWindowManager`

## `tests/test_conversation_collaboration.py`

**Classes:**
- `TestAgentReservationManager`
- `TestConversationRoom`
- `TestConversationTurn`
- `TestConversationBudget`
- `TestConsensusEngine`
- `TestConversationToTaskAdapter`
- `TestConversationManagerLeaseConflict`
- `TestInferTurnTypeFromText`
- `TestConsensusEngineHallucinationDefense`
- `TestUnstructuredTurnHandling`

## `tests/test_coverage_gate_hoist.py`

**Classes:**
- `TestCoverageGateHoistStep1`
- `TestCoverageGateHoistStep2`
- `TestCoverageGateHoistStep3`
- `TestCoverageGateHoistStep4`
- `TestCoverageGateHoistStep5`
- `TestCoverageGateHoistStep6`
- `TestCoverageGateHoistStep7`
- `TestCoverageGateHoistStep8`

**Functions:**
- `_make_agent`
- `_plan`

## `tests/test_critic_skill_router.py`

**Functions:**
- `test_empty_paths_returns_default`
- `test_unknown_path_returns_default`
- `test_frontend_tsx_maps_to_react_skills`
- `test_css_file_maps_to_frontend`
- `test_langchain_path_maps_to_domain`
- `test_memory_system_maps_to_core_memory`
- `test_orchestrator_maps_to_state_machine`
- `test_approval_gate_maps_to_state_machine`
- `test_max_skills_caps_result`
- `test_default_max_is_three`
- `test_dedup_across_multiple_paths`
- `test_windows_backslash_normalization`
- `test_first_match_wins_per_path`
- `test_order_preserved`
- `test_resolve_returns_existing_paths`
- `test_resolve_empty_input`
- `test_cli_main_smoke`

## `tests/test_cross_cli_skill_discovery.py`

**Functions:**
- `test_get_external_skill_roots_alias`
- `test_get_external_skill_roots_personal_before_project`
- `test_get_external_skill_roots_includes_claude_paths`
- `test_get_external_skill_roots_env_override`
- `test_get_external_skill_roots_includes_skills_dir`
- `test_get_external_skill_roots_skills_dir_before_project_root_skills`
- `test_get_external_skill_roots_self_run_excludes_skills_dir`
- `test_get_external_skill_roots_includes_project_skills`
- `test_get_external_skill_roots_project_skills_before_dotdirs`
- `test_get_external_skill_roots_no_windows_appdata`
- `test_claude_official_in_priority`
- `test_claude_official_before_repo_sources`
- `test_claude_official_aliases`
- `test_parse_frontmatter_name`
- `test_parse_frontmatter_name_no_frontmatter`
- `test_extract_skill_id_frontmatter_priority`
- `test_extract_skill_id_fallback_to_dirname`
- `_make_skill_dir`
- `test_claude_official_source_finds_skills`
- `test_claude_official_source_id`
- `test_claude_official_dedup`
- `test_should_rescan_external_detects_new_file`
- `test_ensure_skills_loaded_uses_external_scanned`

## `tests/test_cross_schema.py`

**Functions:**
- `test_registry_schema_cross_validation`

## `tests/test_decision_report.py`

**Functions:**
- `_make_run_decision`
- `test_write_decision_report_creates_files`
- `test_write_decision_report_required_keys`
- `test_write_error_decision`

## `tests/test_default_context_schema.py`

**Classes:**
- `TestDefaultSchemaNoSentinel`
- `TestSchemaValidatesCanonicalCtx`

**Functions:**
- `_load`

## `tests/test_destructive_guard.py`

**Functions:**
- `test_inject_destructive_guard_contract_is_idempotent`
- `test_merge_claude_destructive_guard_deduplicates_rules`
- `test_write_gemini_destructive_policy_contains_shell_deny_rules`
- `test_detect_destructive_process_covers_cmd_and_git_paths`

## `tests/test_documentation_policy.py`

**Functions:**
- `test_ensure_documentation_files_creates_korean_skeletons`
- `test_documentation_policy_falls_back_to_english_templates`
- `test_inject_documentation_contract_is_idempotent`
- `_make_board`
- `test_write_project_todo_no_board_all_unchecked`
- `test_write_project_todo_board_completed`
- `test_write_project_todo_board_in_progress`
- `test_write_project_todo_board_blocked_failed`
- `test_write_project_todo_documentation_items_always_unchecked`
- `test_write_project_todo_duplicate_instruction_conservative`
- `test_write_project_todo_long_instruction_no_truncation`
- `test_write_project_todo_whitespace_normalization`
- `test_update_project_board_task_syncs_todo`
- `test_update_project_board_task_todo_sync_disabled`
- `test_project_pipeline_todo_includes_documentation_tasks`

## `tests/test_dogfood.py`

**Classes:**
- `TestAtomicWriteJson`
- `TestLoadPolicyJson`
- `TestArtifactConstants`
- `TestMergeReportCorruptBlocks`
- `TestMergeExceptionCrashLoop`
- `TestMergePolicyAllowPartialImpl`
- `TestRunMergePhaseUsesStateMode`
- `TestFingerprintUntracked`
- `TestCheckMergePolicyDeniedPaths`

**Functions:**
- `_state`
- `_interview_artifact`
- `test_phase_values_are_strings`
- `test_phase_order_starts_at_pending`
- `test_phase_order_ends_at_complete`
- `test_terminal_phases_not_in_order`
- `test_blocked_is_terminal`
- `test_complete_is_terminal`
- `test_pending_is_not_terminal`
- `test_state_to_dict_keys`
- `test_state_phase_serialized_as_string`
- `test_state_from_dict_roundtrip`
- `test_state_from_dict_defaults`
- `test_state_is_terminal_true`
- `test_state_is_terminal_false`
- `test_save_creates_file`
- `test_save_load_roundtrip`
- `test_save_overwrites_on_phase_change`
- `test_state_path_structure`
- `reset_run_budget`
- `test_save_state_snapshots_run_budget`
- `test_load_state_restores_run_budget_singleton`
- `test_build_ai_task_includes_reference_artifacts`
- `test_build_ai_task_omits_reference_section_when_empty`
- `test_build_ai_task_investigation_outputs_in_prompt`
- `test_build_ai_task_no_investigation_outputs_backward_compat`
- `test_build_ai_task_investigation_outputs_none_backward_compat`
- `test_build_ai_task_investigation_truncation`
- `test_build_ai_task_investigation_truncation_boundary`
- `test_build_ai_task_investigation_entry_count_capped`
- `test_build_ai_task_investigation_multiple_steps`
- `test_build_ai_task_investigation_evidence_fence_and_label`
- `test_build_ai_task_investigation_items_cap_11`
- `test_build_ai_task_investigation_items_cap_5_no_omitted`
- `test_run_implement_investigation_output_forwarded_to_ai`
- `test_run_implement_no_commands_step_no_investigation_section`
- `test_run_implement_two_investigation_steps_both_reach_ai`
- `test_save_state_preserves_stopped_flag`
- `test_save_state_preserves_project_id`
- `test_create_run_returns_pending`
- `test_create_run_persists_state`
- `test_create_run_custom_run_id`
- `test_create_run_unique_ids`
- `test_advance_from_pending`
- `test_advance_from_isolate`
- `test_advance_from_review`
- `test_advance_from_complete_raises`
- `test_advance_from_blocked_raises`
- `test_advance_full_sequence`
- `test_block_run_sets_blocked`
- `test_read_phase_trace_missing_file_returns_empty`
- `test_read_phase_trace_parses_valid_records`
- `test_read_phase_trace_skips_corrupt_last_line`
- `test_read_phase_trace_skips_blank_lines`
- `test_read_phase_trace_truncated_multibyte_utf8_does_not_raise`
- `test_read_phase_trace_oserror_returns_empty`
- `test_handle_blocked_worktree_pending_noop`
- `test_handle_blocked_worktree_failed_always_cleans`
- `test_handle_blocked_worktree_failed_cleanup_failure_wt_remains`
- `test_handle_blocked_worktree_failed_cleanup_failure_branch_remains`
- `test_handle_blocked_worktree_ready_preserved_by_default`
- `test_handle_blocked_worktree_ready_cleaned_when_requested`
- `test_handle_blocked_worktree_failed_no_worktree_skips_branch_delete`
- `test_handle_blocked_worktree_failed_branch_exists_unknown_marks_failed`
- `test_run_phase_pending_returns_empty`
- `test_run_phase_terminal_raises`
- `test_run_phase_blocked_raises`
- `test_run_interview_stores_path`
- `test_run_interview_missing_intent_and_goal_raises`
- `test_run_interview_empty_artifact_ok`
- `test_run_interview_returns_artifact`
- `test_run_research_brief_stores_path`
- `test_run_research_brief_returns_dict`
- `test_run_research_returns_evidence_bundle`
- `test_run_research_reads_scope_file`
- `test_run_research_includes_companion_test`
- `test_run_research_ignores_nonexistent_scope`
- `test_research_scope_files_filters_non_py`
- `test_research_scope_files_traversal_rejected`
- `test_research_scope_files_clarification_log_fallback`
- `test_research_scope_files_intent_fallback`
- `test_research_scope_files_string_scope_not_char_iterated`
- `test_run_spec_stores_path`
- `test_run_spec_sets_completion_criteria`
- `test_run_spec_returns_dict_with_intent`
- `_minimal_spec_dict`
- `test_run_premortem_returns_dict_with_risks`
- `_minimal_premortem_dict`
- `test_run_plan_stores_path`
- `test_run_plan_returns_dict_with_intent`
- `_plan_dict`
- `_step`
- `test_run_implement_empty_plan_ok`
- `test_run_implement_steps_without_commands_use_ai_executor`
- `test_run_implement_commands_all_pass`
- `test_run_implement_command_failure`
- `test_run_implement_loads_plan_from_disk`
- `test_run_implement_context_plan_dict_takes_priority`
- `test_run_implement_mixed_steps`
- `test_run_implement_preflight_static_blocks_existing_syntax_error`
- `test_run_implement_ai_output_records_run_budget`
- `test_run_implement_new_untracked_file_included_in_actual_changed`
- `test_strict_contract_blocks_empty_research_brief_and_premortem`
- `test_verify_result_to_dict`
- `test_review_decision_to_dict`
- `_make_runner`
- `test_run_verify_no_commands_passes`
- `test_run_verify_all_commands_pass`
- `test_run_verify_partial_failure`
- `test_run_verify_commands_from_plan_dict`
- `test_run_verify_context_commands_takes_priority`
- `test_run_verify_no_commands_no_steps_passes`
- `test_run_verify_no_commands_with_steps_fails`
- `_verify_passed_ctx`
- `test_run_review_passed_returns_pass`
- `test_run_review_failed_always_blocks`
- `test_run_review_missing_verify_result_assumes_passed`
- `test_spec_from_dict_roundtrip`
- `test_premortem_from_dict_roundtrip`
- `_patch_all_runners`
- `_stub_merge`
- `test_run_all_returns_complete`
- `test_run_all_persists_complete_state`
- `test_run_all_blocked_on_first_verify_fail`
- `test_run_all_blocked_persists_state`
- `test_run_all_returns_dogfood_state`
- `test_run_all_verify_receives_develop_result`
- `test_run_all_traverses_active_phases`
- `test_run_all_develop_blocked_when_pipeline_raises`
- `_dev_state`
- `_light_decision`
- `_full_decision`
- `_stub_light_internals`
- `test_inv_light_route`
- `test_inv_full_route`
- `test_inv_norm_light`
- `test_inv_norm_full`
- `test_inv_record`
- `test_inv_floor_e2e`
- `test_inv_noscope`
- `test_inv_iso_env`
- `test_router_exc_fallback_to_pipeline`

## `tests/test_dogfood_cli.py`

**Functions:**
- `_make_state`
- `_noop_isolate`
- `_noop_implement`
- `_noop_verify`
- `_noop_finalize`
- `_noop_merge`
- `_run_all_side_effect_patches`
- `test_dogfood_subcommand_registered`
- `test_agent_launcher_utf8_env_defaults`
- `test_parser_dogfood_run_parses`
- `test_parser_dogfood_run_with_options`
- `test_parser_dogfood_status_parses`
- `test_cli_dogfood_run_complete`
- `test_cli_dogfood_run_blocked`
- `test_dogfood_command_runner_uses_utf8_subprocess_env`
- `test_cli_dogfood_status_found`
- `test_cli_dogfood_status_not_found`
- `test_run_id_traversal_rejected_create`
- `test_run_id_traversal_rejected_load`
- `test_detect_mode_dogfood`
- `test_detect_mode_ad_hoc_not_dogfood`
- `test_parser_dogfood_interview_basic`
- `test_parser_dogfood_interview_flags`
- `test_parser_dogfood_interview_deep_skip`
- `test_parser_dogfood_run_from_file`
- `test_parser_dogfood_run_no_from_file_default`
- `test_cli_dogfood_interview_dispatch`
- `test_cli_dogfood_interview_failure`
- `test_cli_dogfood_run_from_file_success`
- `test_cli_dogfood_run_from_file_missing`
- `test_cli_dogfood_run_from_file_bad_json`
- `test_run_interview_phase_calls_interview_fn`
- `test_run_interview_phase_raises_on_fn_failure`
- `test_run_interview_phase_no_fn_uses_artifact`
- `test_run_phase_passes_interview_fn`
- `test_run_all_skips_interview_fn_when_artifact_provided`
- `test_parser_dogfood_run_non_interactive`

## `tests/test_dogfood_integration.py`

**Functions:**
- `_minimal_interview`
- `_noop_runner`
- `_failing_runner`
- `_noop_isolate`
- `_noop_finalize`
- `_noop_merge`
- `_noop_ai_executor`
- `_smoke_patches`
- `test_run_all_reaches_complete`
- `test_run_all_persists_state_json`
- `test_run_all_artifacts_written`
- `_minimal_state`
- `_minimal_spec`
- `test_plan_phase_wires_real_architect_fn`
- `test_plan_phase_accept_finding_surfaces_in_plan`
- `test_plan_phase_e2e_runs_complete`

## `tests/test_dogfood_isolation.py`

**Functions:**
- `_make_state`
- `_fake_git_ok`
- `_fake_git_dirty`
- `_make_git_clean`
- `test_prepare_isolated_worktree_records_fields`
- `test_implement_uses_worktree_cwd`
- `test_verify_uses_worktree_cwd`
- `test_implement_falls_back_to_source_when_not_isolated`
- `test_runtime_artifacts_in_runtime_workspace`
- `test_finalize_records_dogfood_commit`
- `test_finalize_selective_staging_uses_plan_allowlist`
- `test_finalize_runs_final_docs_sync_before_staging`
- `test_finalize_stages_review_artifacts_under_docs_reviews`
- `test_build_merge_policy_allows_docs_reviews_dir`
- `test_build_merge_policy_skills_only_plan_allows_docs_reviews`
- `test_finalize_fallback_stages_all_when_no_plan`
- `_make_merge_state`
- `test_check_merge_policy_clean_source_passes`
- `test_check_merge_policy_dirty_source_blocks`
- `test_check_merge_policy_source_advanced_blocks`
- `test_check_merge_policy_denied_path_blocks`
- `test_check_merge_policy_allowed_path_suffix_sibling_blocks`
- `test_check_merge_policy_allowed_path_exact_and_dir_boundary`
- `test_build_merge_policy_empty_mode_raises`
- `test_build_merge_policy_none_mode_uses_state_default`
- `test_check_merge_policy_scope_violations_blocks`
- `test_check_merge_policy_dogfood_commit_equals_base_ref_blocks`
- `test_finalize_crlf_only_files_excluded_from_scope_violations`
- `test_run_merge_phase_manual_sets_ready_and_complete`
- `test_run_merge_phase_never_completes_without_merge`
- `test_safe_to_cleanup_only_when_not_ready`
- `test_safe_to_cleanup_false_when_ready`
- `test_default_runtime_workspace_uses_run_id`
- `test_default_runtime_workspace_cwd_independent`
- `test_merge_crash_recovery_already_ancestor`
- `test_conflict_check_uses_reset_merge_not_abort`
- `test_prepare_isolated_worktree_retries_once`
- `test_merge_policy_triad_pass_not_required`
- `test_merge_policy_defaults`
- `test_prepare_isolated_worktree_crlf_only_passes`
- `test_prepare_isolated_worktree_real_dirty_blocks`
- `test_run_all_merge_never_reaches_complete`
- `_stub_all_phases`
- `test_run_all_merge_manual_terminates`
- `test_workspace_property_returns_source_workspace`
- `test_from_dict_backward_compat_workspace_key`
- `test_dirty_files_returns_tracked_changes`
- `test_dirty_files_crlf_filtered`
- `test_dirty_files_whitespace_not_crlf`
- `test_dirty_files_includes_untracked`
- `test_merge_dirty_check_applies_crlf_filter`
- `test_finalize_untracked_file_not_filtered_as_crlf`
- `test_merge_branch_default_policy_applies_denied_paths`
- `_write_plan`
- `test_build_merge_policy_derives_allowed_paths_from_plan`
- `test_build_merge_policy_no_plan_empty_allowed`
- `test_run_merge_phase_auto_enforces_plan_allowed_paths`
- `test_create_run_rejects_invalid_merge_mode`
- `test_merge_policy_rejects_invalid_mode`
- `test_merge_policy_rejects_whitespace_mode`
- `test_valid_merge_modes_membership`
- `test_dirty_files_untracked_not_crlf_filtered`
- `test_dirty_files_all_crlf_returns_empty`
- `test_dirty_files_git_status_failure_raises`
- `test_remove_worktree_only_dirty_refuses`
- `test_prepare_isolated_worktree_sets_autocrlf_false`
- `test_prepare_isolated_worktree_source_repo_autocrlf_unchanged`
- `test_is_crlf_only_diff_doubled_cr_treated_as_noise`
- `test_is_crlf_only_diff_real_content_change_not_noise`
- `test_is_crlf_only_diff_standard_crlf_still_works`
- `test_is_crlf_only_diff_doubled_cr_raw_bytes_comparison`
- `test_prepare_isolated_worktree_no_permanent_config_change_real_git`

## `tests/test_dogfood_realignment.py`

**Classes:**
- `_FakePipeline`

**Functions:**
- `_mk`
- `test_inv1_empty_allowlist_with_changes_fails_closed`
- `test_inv2_placeholder_verify_commands_fail_closed`
- `test_inv3_failed_verify_blocks_without_retry`
- `test_inv4_develop_runs_pipeline_research_in_worktree`
- `test_inv5_develop_confines_writes_via_reused_guards`

## `tests/test_dynamic_orchestrator_workspace_scope.py`

**Classes:**
- `_DummyMR`
- `_DummyLLM`
- `_RepeatingLLM`
- `_DummyRunner`
- `_FailingRunner`
- `_DummyAgentManager`
- `_DummyMemoryHub`
- `_DummyEvaluator`

**Functions:**
- `test_workspace_is_propagated_without_rebinding`
- `test_runtime_workspace_is_propagated_to_runner`
- `test_lineage_maxed_check_reads_runtime_workspace`
- `test_todo_fallback_assigns_tasks_when_llm_is_unavailable`
- `test_project_board_fallback_respects_dependencies`
- `test_execute_agent_task_marks_project_board_completed`
- `test_retry_failure_reopens_board_task_for_reschedule`
- `test_completed_todo_blocks_repeated_llm_reassignment`
- `test_role_scoped_todo_is_not_cross_assigned`
- `test_needs_llm_intervention_blocks_stall_when_all_recent_failures_are_infra`
- `test_needs_llm_intervention_allows_stall_when_impl_failures_mixed`

## `tests/test_engine_auth_provider_priority.py`

**Functions:**
- `test_claude_cli_always_available`
- `test_gemini_no_keys_not_available`
- `test_gemini_with_google_api_key`
- `test_gemini_with_gemini_api_key`
- `test_codex_no_key_not_available`
- `test_codex_with_openai_key`
- `_setup_auto_configure`
- `test_no_google_key_claude_preferred`
- `test_with_google_key_gemini_preferred`
- `test_only_gemini_no_key_still_returns_gemini`
- `test_all_three_no_keys_claude_first`

## `tests/test_enqueue_staged_review.py`

**Functions:**
- `_git`
- `test_enqueue_staged_review_targets_staged_python_without_provider_hooks`
- `test_precommit_invokes_provider_neutral_staged_enqueue`
- `test_enqueue_staged_review_uses_module_path_under_pyinstaller_frozen_build`
- `test_enqueue_staged_review_does_not_make_completed_reviews_stale`

## `tests/test_escalation_evaluator.py`

**Functions:**
- `_make_record`
- `test_evaluate_rule_not_active_never`
- `test_evaluate_inactive_phase_p4`
- `test_evaluate_exempt_scope`
- `test_evaluate_threshold_met_build`
- `test_evaluate_below_threshold_count_zero`
- `test_evaluate_false_positive_override`
- `test_compute_run_decision_no_active_rules`
- `test_compute_run_decision_blocked`
- `test_compute_run_decision_override`
- `test_is_phase_active`

## `tests/test_escalation_evaluator_p4a.py`

**Functions:**
- `_make_record`
- `test_evaluate_observation_below_threshold_returns_warn`
- `test_evaluate_observation_threshold_met_returns_block_candidate`
- `test_evaluate_off_mode_skips_threshold`
- `test_evaluate_enforce_mode_default_when_field_missing`
- `test_read_current_phase_fallback_p2_when_missing_or_invalid`
- `test_observation_respects_false_positive_override`
- `test_e2e_command_missing_blocks_under_p4_current_phase`

## `tests/test_escalation_policy_yaml_p4a.py`

**Functions:**
- `test_yaml_v1_loads_current_phase_and_modes`
- `test_yaml_invalid_mode_raises`

## `tests/test_evolution_ledger.py`

**Classes:**
- `TestLedgerAppendLoad`
- `TestLedgerFilters`
- `TestLedgerStats`

**Functions:**
- `_entry`

## `tests/test_executor.py`

**Functions:**
- `test_executor_success`
- `test_executor_timeout`
- `test_executor_failure`

## `tests/test_express_router.py`

**Functions:**
- `test_tokens_found_case_insensitive`
- `test_tokens_found_substring_match`
- `test_tokens_found_none_present`
- `test_tokens_found_multiple_matches`
- `test_core_path_triggers_dogfood`
- `test_af_spec_triggers_dogfood`
- `test_master_blueprint_triggers_dogfood`
- `test_dogfood_keyword_triggers_dogfood`
- `test_self_modifying_keyword_triggers_dogfood`
- `test_windows_backslash_path_triggers_dogfood`
- `test_windows_backslash_path_rationale`
- `test_dogfood_rationale_contains_signal`
- `test_risk_token_delete_triggers_full`
- `test_risk_token_security_triggers_full`
- `test_research_token_investigate_triggers_full`
- `test_research_token_architecture_triggers_full`
- `test_complexity_short_stays_light`
- `test_complexity_long_triggers_full`
- `test_full_rationale_contains_signal`
- `test_status_query_triggers_direct`
- `test_version_query_triggers_direct`
- `test_trivial_too_long_stays_light`
- `test_direct_rationale_contains_trivial`
- `test_helper_word_does_not_trigger_trivial`
- `test_blacklist_does_not_trigger_list_token`
- `test_complexity_plus_trivial_short_is_not_direct`
- `test_complexity_trivial_combo_does_not_escalate_to_full_if_short`
- `test_simple_bug_fix_is_light`
- `test_empty_task_is_light`
- `test_plain_feature_is_light`
- `test_force_route_dogfood`
- `test_force_route_direct`
- `test_force_route_rationale`
- `test_force_route_invalid_raises`
- `test_hints_can_trigger_dogfood`
- `test_hints_can_trigger_full`
- `test_direct_flags`
- `test_light_flags`
- `test_full_flags`
- `test_dogfood_flags`
- `test_direct_phases`
- `test_light_phases_contains_interview`
- `test_full_phases_contains_research`
- `test_dogfood_phases_contains_isolate_and_merge`
- `test_phases_returns_copy`
- `test_to_dict_structure`

## `tests/test_external_skill_candidate_importer.py`

**Functions:**
- `test_import_external_candidates_from_manifest`
- `test_import_external_candidates_can_fallback_to_python_scan`
- `test_import_external_candidates_can_fallback_to_codex_markdown_scan`
- `test_import_external_candidates_blocks_duplicate_skill_ids_within_same_source`
- `test_import_external_candidates_replaces_legacy_source_keys`
- `test_merge_install_candidates_preserves_legacy_list_form_entries`
- `test_discover_external_candidates_sweeps_custom_sources_when_unspecified`
- `test_discover_external_candidates_prefers_manifest_before_python_fallback`
- `test_main_uses_default_paths_for_check_only`
- `test_main_accepts_legacy_cli_aliases`

## `tests/test_external_skill_sources.py`

**Functions:**
- `test_external_resolver_prefers_claude_before_codex`
- `test_external_resolver_records_miss_before_falling_through`
- `test_external_resolver_treats_prepare_error_as_source_error_then_falls_through`
- `test_repo_cache_source_reads_imported_candidates`
- `test_repo_cache_source_uses_same_cache_segment_as_importer`
- `test_repo_cache_source_falls_back_to_python_scan_when_manifest_missing`
- `test_external_resolver_surfaces_repo_sync_failure_as_source_error`
- `test_official_codex_source_reads_skill_directories`
- `test_external_resolver_prefers_official_codex_before_repo_cache`

## `tests/test_factory_evolution.py`

**Functions:**
- `_load_launcher`
- `test_factory_reuses_verified_skill`
- `test_factory_builds_unresolved_skill_and_registers`
- `test_factory_run_workflow_sequences_roles`

## `tests/test_failure_classifier.py`

**Functions:**
- `test_infra_patterns_classified_as_infra`
- `test_implementation_patterns`

## `tests/test_fallback_auto_gen.py`

**Functions:**
- `test_regression_fix`

## `tests/test_fsa_runtime_workspace.py`

**Classes:**
- `_DummyRunner`
- `_InfraFailRunner`

**Functions:**
- `test_fsa_saves_ledger_under_runtime_workspace`
- `test_fsa_infra_failure_exits_immediately`
- `test_ise_loop_forwards_runtime_workspace`

## `tests/test_gemini_smoke.py`

**Functions:**
- `test_gemini_new_sdk_list_models`
- `test_gemini_old_sdk_embedding`
- `test_discovery_cache_not_required_by_import`

## `tests/test_hook_event_bus.py`

**Classes:**
- `_NormalizeArgsHook`
- `_ReadonlyWorkspaceHook`
- `_TruncateToolResultHook`

**Functions:**
- `test_pre_tool_call_hooks_can_mutate_and_block`
- `test_post_tool_call_hooks_can_transform_result`

## `tests/test_hook_runner.py`

**Functions:**
- `hook_runner_mod`
- `_read_log_lines`
- `test_log_hook_event_split_invariant`
- `test_log_hook_event_split_invariant_with_payload_pipe_documented`

## `tests/test_hook_runner_builtins.py`

**Functions:**
- `_runner`
- `_payload`
- `test_extract_file_path_normal`
- `test_extract_file_path_missing_tool_input`
- `test_extract_file_path_empty_string`
- `test_extract_file_path_none_value`
- `test_read_hook_stdin_valid_json`
- `test_read_hook_stdin_invalid_json`
- `test_read_hook_stdin_empty`
- `test_py_compile_non_py_file`
- `test_py_compile_empty_path`
- `test_py_compile_valid_file`
- `test_py_compile_syntax_error`
- `test_enqueue_non_py_file`
- `test_enqueue_calls_script_for_py`
- `test_builtins_keys_present`
- `test_main_dispatches_builtin`
- `test_main_falls_through_for_unknown_cmd`
- `test_log_hook_event_creates_log`
- `test_log_hook_event_silently_swallows_errors`
- `test_post_agent_record_forces_fail_when_test_gap_analyzer_fails`
- `test_post_agent_record_keeps_verdict_when_test_gap_analyzer_passes`
- `test_post_agent_record_clears_stale_test_gap_report_when_analyzer_passes`
- `test_post_agent_record_stores_critic_t3_advisory`
- `test_apply_test_gap_verdict_does_not_modify_blast_tier_on_fail`
- `test_detect_triggers_test_failure_on_block_verdict`
- `test_detect_triggers_test_failure_on_fail_verdict`
- `test_detect_triggers_pass_verdict_no_test_failure`
- `test_detect_triggers_flaky_keyword_in_content`
- `test_detect_triggers_timeout_keyword`
- `test_detect_triggers_importerror_keyword`
- `test_detect_triggers_subprocess_keyword`
- `test_detect_triggers_packaging_keyword`
- `test_detect_triggers_security_for_critic`
- `test_detect_triggers_policy_for_critic`
- `test_detect_triggers_cross_platform_for_critic`
- `test_detect_triggers_unknown_agent_returns_empty`
- `test_detect_triggers_multiple_matches`
- `test_detect_triggers_windows_quoted_path_in_content`
- `test_detect_triggers_posix_quoted_path_in_content`

## `tests/test_implementation_language_policy.py`

**Functions:**
- `test_inject_implementation_language_contract_is_idempotent`
- `test_inject_implementation_language_contract_can_be_disabled`
- `test_agent_runner_runtime_prompt_includes_implementation_language_contract`
- `test_codex_cli_prompt_includes_implementation_language_contract`

## `tests/test_inject_review_tasks_e2e_command.py`

**Functions:**
- `_seed_board`
- `test_inject_review_tasks_e2e_command`
- `test_inject_review_tasks_provider_id_routing`
- `test_inject_review_tasks_provider_id_missing_defaults_to_first`

## `tests/test_interview.py`

**Functions:**
- `test_run_interview_collects_answers_and_writes_brief`
- `test_run_interview_non_interactive_applies_defaults`
- `test_run_interview_deep_skip_applies_llm_defaults_without_prompting`
- `test_run_interview_interactive_records_mode`
- `test_cli_main_requires_task`
- `test_artifact_shape_interactive_has_required_fields`
- `test_artifact_shape_deep_skip_derives_assumptions`
- `test_artifact_shape_non_interactive_assumptions_empty`
- `test_artifact_shape_no_questions`
- `test_ensure_artifact_shape_does_not_overwrite_existing`

## `tests/test_ise_integration.py`

**Functions:**
- `test_agent_launcher_routes_ise_mode_to_ise_loop`
- `test_strategy_ledger_hash_returns_32_chars`
- `test_strategy_ledger_hash_distinct_for_different_inputs`
- `test_stall_detector_escalates_on_repeated_same_error`
- `test_should_decompose_triggers_on_three_logic_failures`
- `test_should_decompose_rejects_transient_failures`
- `test_should_decompose_below_retry_threshold`

## `tests/test_ise_provider_awareness.py`

**Functions:**
- `test_inv1_ise_analyzer_uses_cli_when_available`
- `test_inv2_infra_failure_triggers_fallback`
- `test_inv3_graceful_degrade_no_provider`
- `test_inv4_control_plane_llm_has_required_interface`
- `test_inv5_no_llmengine_direct_instantiation_in_targets`
- `test_inv6_strategy_evaluator_llm_is_control_plane`

## `tests/test_key_combos.py`

**Functions:**
- `test_engine_selection_per_key_combination`

## `tests/test_knowledge_skill.py`

**Classes:**
- `TestParseSkillMd`
- `TestScanKnowledgeSkills`
- `TestFilterRelevantKnowledge`
- `TestBuildKnowledgePrompt`
- `TestSkillRegistryKnowledgeType`

**Functions:**
- `temp_skills_dir`
- `sample_skill_md`
- `sample_no_frontmatter`

## `tests/test_korean_encoding.py`

**Functions:**
- `test_korean_text_is_preserved`

## `tests/test_lineage_ledger.py`

**Functions:**
- `tmp_ledger_path`
- `test_is_maxed_returns_false_on_new_lineage`
- `test_is_maxed_triggers_on_max_level`
- `test_is_maxed_false_below_max_level`
- `test_is_maxed_triggers_on_max_attempts`
- `test_entry_persists_across_reload`
- `test_history_persists_after_success_reset`
- `test_on_task_success_resets_maxed_state`
- `test_lifetime_attempts_cap_blocks_oscillation`
- `test_legacy_data_without_lifetime_attempts_loads`
- `test_get_lineage_ledger_caches_per_workspace`

## `tests/test_llm_doc_gen_p3_p6.py`

**Classes:**
- `TestPreparedBrief`
- `TestGenerateClarificationQuestions`
- `TestMergeClarification`
- `TestShouldSkipClarification`
- `TestAutoApplyDefaults`
- `TestMergeClarificationRobustness`
- `TestCollectClarificationAnswers`

## `tests/test_llm_engine_auto_upgrade_scope.py`

**Functions:**
- `test_auto_upgrade_is_enabled_by_env_flag`
- `test_auto_upgrade_is_disabled_without_env_flag`

## `tests/test_llm_wiki_precommit.py`

**Functions:**
- `_hook_text`
- `test_precommit_regenerates_llm_wiki_for_source_docs`
- `test_precommit_regenerates_llm_wiki_for_python_symbol_changes`

## `tests/test_manager.py`

**Functions:**
- `test_agent_manager_cli_bootstrap_creates_fallback_agent`

## `tests/test_midori_skills.py`

**Functions:**
- `load_skill_module`
- `run_tests`

## `tests/test_model_name_normalization.py`

**Classes:**
- `_FakeModels`
- `_FakeClient`

**Functions:**
- `test_normalize_model_name_for_gemini_prefix`
- `test_normalize_model_name_non_gemini_passthrough`
- `test_forced_model_override`
- `test_no_project_level_forced_override`
- `test_generate_content_with_self_heal_retries_on_404`
- `test_resolve_preferred_model_uses_dynamic_routing_when_not_forced`

## `tests/test_nightly_summary.py`

**Functions:**
- `_make_board_fixture`
- `test_render_summary_no_workspace`
- `test_render_summary_no_board`
- `test_render_summary_modules_mix`
- `test_render_summary_workspace_priority`

## `tests/test_nlm_regression.py`

**Functions:**
- `test_nlm_auth_status_output_format`
- `test_nlm_notebook_help_subcommands_exist`

## `tests/test_omo_env_parse.py`

**Functions:**
- `test_build_argv_extracts_leading_env_assignments`
- `test_build_argv_without_env_prefix_is_unchanged`

## `tests/test_optional_id_calib.py`

**Functions:**
- `ws`
- `_send`
- `test_c1a_empty_to_role_raises`
- `test_c1b_empty_from_role_becomes_unknown_sender`
- `test_c1c_empty_task_id_uses_general_thread`
- `test_c1d_empty_task_id_read_returns_all`
- `test_c1e_empty_role_ack_succeeds`
- `test_c2_empty_raw_key_string_path_returns_none`
- `test_c2_empty_id_dict_returns_none`
- `test_c3_empty_dep_is_satisfied`
- `test_c3_whitespace_dep_is_satisfied`
- `test_c4_empty_task_id_not_in_completed_keys`
- `test_c5_whitespace_only_title_task_id_is_empty`

## `tests/test_orchestrator_manifest.py`

**Classes:**
- `_DummyMR`
- `_DummyLLM`
- `_DummyRunner`
- `_DummyAgentManager`
- `_DummyMemoryHub`
- `_DummyEvaluator`

**Functions:**
- `test_manifest_store_converts_active_work_into_interrupted`
- `test_dynamic_orchestrator_writes_manifest_and_restores_interruptions`

## `tests/test_pending_review.py`

**Functions:**
- `_write_marker`
- `_read_marker`
- `_check_main`
- `_enqueue_main`
- `test_no_marker_silent`
- `test_first_fire_suppressed_within_batch_interval`
- `test_first_fire_triggers_after_interval`
- `test_first_fire_t3_skip_prints_two_agents`
- `test_first_fire_t3_skip_ignored_for_blast_tier3_guidance`
- `test_first_fire_writes_fired_at`
- `test_first_fire_debounced_by_recent_reedit`
- `test_first_fire_uses_updated_at_not_created_at`
- `test_refires_when_updated_at_newer_than_fired_at`
- `test_no_refire_when_updated_at_older_than_fired_at`
- `test_empty_files_list_silent`
- `test_marker_kept_after_fire`
- `test_t3_skipped_when_all_external_rate_limited`
- `test_t3_included_when_no_rate_limit`
- `test_enqueue_creates_marker_for_core_py`
- `test_enqueue_skips_non_review_file`
- `test_enqueue_always_refreshes_updated_at_for_existing_file`
- `test_enqueue_deduplicates_file_list`
- `test_enqueue_accumulates_multiple_files`
- `test_enqueue_atomic_write_produces_valid_json`
- `test_enqueue_t3_classifier_stale_file_set_fails_closed`
- `test_enqueue_telemetry_failure_does_not_drop_marker`
- `test_enqueue_classifier_unavailable_fails_closed_over_stale_skip`
- `_seed_clean_metrics`
- `test_enqueue_stores_telemetry_skip_and_logs_once`
- `test_enqueue_risk_file_no_telemetry_skip_log`

## `tests/test_phase10_memory_foundation.py`

**Classes:**
- `InMemoryAdapter`
- `TestMemoryRecord`
- `TestEpisodeRecord`
- `TestKnowledgeGraph`
- `TestAdapterABC`
- `TestFacade`
- `TestCortexVectorAdapter`

**Functions:**
- `run`

## `tests/test_phase11_adapters.py`

**Classes:**
- `TestCoreMemoryAdapter`
- `TestAstHubAdapter`
- `TestContinuityAdapter`
- `TestSyncCompyneAdapter`
- `TestTraceLogAdapter`
- `TestFacadeMultiAdapter`

**Functions:**
- `run`

## `tests/test_phase12_episodic_memory.py`

**Classes:**
- `TestEpisodeExtractor`
- `TestConsolidationHook`

**Functions:**
- `run`

## `tests/test_phase13_knowledge_graph.py`

**Classes:**
- `TestKnowledgeGraphAdapter`
- `TestGraphBuilder`
- `TestGraphQuery`

**Functions:**
- `run`

## `tests/test_phase14_decay_cross_project.py`

**Classes:**
- `TestDecayManager`
- `TestCrossProjectRecall`

**Functions:**
- `run`

## `tests/test_phase15_lifecycle_issues.py`

**Classes:**
- `TestProjectLifecycle`
- `TestGitHubIssuesAdapter`
- `TestJiraAdapter`

**Functions:**
- `run`

## `tests/test_phase16_integration.py`

**Classes:**
- `TestMemoryRouterClassification`
- `TestMemoryRouterRouting`
- `TestE2EScenario`

**Functions:**
- `run`

## `tests/test_phase1_2_integration.py`

**Classes:**
- `TestPhase12Integration`

**Functions:**
- `test_batch_performance`

## `tests/test_phase1_blast_tier_invariant.py`

**Functions:**
- `_runner`
- `_write_queue`
- `_read_queue`
- `test_layer1_blast_tier_unchanged_on_test_gap_fail`
- `test_layer2_gate_blocks_after_test_gap_fail`
- `test_layer3_blast_tier_preserved_through_full_cycle`
- `test_layer5_gate_blocked_fixture_blast_tier3_no_reviews`
- `test_layer5_gate_pass_fixture_blast_tier3_all_reviews`
- `test_layer6_state_matrix`

## `tests/test_phase3_langsmith_tracing.py`

**Classes:**
- `TestStdoutCapturer`
- `TestLangSmithTracingHook`
- `TestPhase3Integration`

## `tests/test_phase4_evaluator_skills.py`

**Classes:**
- `TestTraceExecution`
- `TestSummarizeFailure`
- `TestGenerateEvalDataset`

**Functions:**
- `tmp_dir`
- `_write_jsonl`
- `_make_success_events`
- `_make_failure_events`

## `tests/test_phase5_context_fork_preflight.py`

**Classes:**
- `TestContextForkHook`
- `TestPreflightEvaluator`

## `tests/test_phase6_semantic_matching.py`

**Classes:**
- `TestCosineSimilarity`
- `TestBuildSkillText`
- `TestEmbedderFallback`
- `TestScoreWeights`
- `TestDiskCache`
- `TestQueryCacheLRU`
- `TestAdapterParsing`

**Functions:**
- `_make_skill`

## `tests/test_phase7_dep_graph_evolve.py`

**Classes:**
- `TestSkillDependencyGraph`
- `TestDynamicSkillLoaderDeps`
- `TestFSALoopSkillEvolve`

## `tests/test_phase8_retrieval_router.py`

**Classes:**
- `TestRetrievalRouter`
- `TestEvidencePackExtension`

## `tests/test_phase9_hybrid_retrieval.py`

**Classes:**
- `TestDocumentChunker`
- `TestSparseIndex`
- `TestDocumentIndex`
- `TestIngestionPipeline`
- `TestRouterDocumentIntegration`
- `TestTokenizer`

## `tests/test_phase_a_step3_evolution.py`

**Classes:**
- `TestGateResult`
- `TestSkillEvolutionBus`
- `TestSkillQualityGate`
- `TestSkillSelfEvolutionHook`
- `TestDefectSkillE2E`
- `TestFetchEpisodeContext`

## `tests/test_pipeline_block_enforcement.py`

**Functions:**
- `_make_prepared_mock`
- `test_execute_blocked_by_escalation`
- `test_execute_passes_when_not_blocked`

## `tests/test_planner.py`

**Classes:**
- `TestImplementationSteps`
- `TestScopeFileRiskInvestigation`
- `TestStaleTestRiskInvestigation`
- `TestDuplicateFunctionRiskInvestigation`
- `TestConflictingImportRiskInvestigation`
- `TestLongFunctionRiskInvestigation`
- `TestAssumptionRiskContractRegression`
- `TestComplexityRiskInvestigation`
- `TestNestingDepthRiskInvestigation`

**Functions:**
- `_spec`
- `_premortem`
- `_risk`
- `test_plan_step_to_dict_keys`
- `test_executable_plan_to_dict_keys`
- `test_executable_plan_is_empty_true`
- `test_executable_plan_is_empty_false`
- `test_test_file_for_core_module`
- `test_test_file_for_scripts_module`
- `test_test_file_for_non_python`
- `test_test_file_for_root_py`
- `test_collect_verification_commands_excludes_comments`
- `test_collect_verification_commands_empty`
- `test_collect_verification_commands_multiple_risks`
- `test_collect_approval_points_from_policy`
- `test_collect_approval_points_from_approval_risk`
- `test_collect_approval_points_empty`
- `test_unresolved_risks_gap_not_in_scope`
- `test_unresolved_risks_gap_resolved_by_scope`
- `test_unresolved_risks_non_gap_ignored`
- `test_unresolved_risks_boilerplate_prefix_does_not_cause_false_negative`
- `test_build_plan_empty_spec_empty_premortem`
- `test_build_plan_scope_generates_implementation_steps`
- `test_build_plan_impl_steps_have_test_suggestions`
- `test_build_plan_no_test_for_root_py`
- `test_build_plan_core_py_includes_blueprint_in_artifacts`
- `test_build_plan_non_core_py_excludes_blueprint`
- `test_build_plan_reference_artifacts_includes_companion_test`
- `test_build_plan_reference_artifacts_empty_when_no_findings`
- `test_build_plan_reference_artifacts_per_scope_item`
- `test_build_plan_reference_artifacts_ignores_unrelated`
- `test_build_plan_reference_artifacts_no_stem_collision`
- `test_build_plan_reference_artifacts_dedup_path_separator`
- `test_build_plan_reference_artifacts_scope_backslash_excludes_self`
- `test_build_plan_gap_risks_become_investigation_steps`
- `test_build_plan_investigation_steps_come_first`
- `test_build_plan_implementation_depends_on_investigation`
- `test_build_plan_premortem_risk_generates_verification_step`
- `test_build_plan_verification_step_depends_on_impl`
- `test_build_plan_fallback_pytest_when_only_comment_risks`
- `test_build_plan_verification_requirements_populated`
- `test_build_plan_verification_step_commands_stored_on_step`
- `test_build_plan_investigation_step_no_commands`
- `test_build_plan_single_assumption_risk_becomes_investigation_step`
- `test_build_plan_two_assumption_risks_become_two_investigation_steps`
- `test_build_plan_no_assumption_risks_no_assumption_investigation_steps`
- `test_build_plan_step_ids_unique`
- `test_build_plan_step_ids_start_at_s1`
- `test_build_plan_completion_criteria_from_spec`
- `test_build_plan_approval_from_policy`
- `test_build_plan_to_dict_round_trip`

## `tests/test_policy_runtime.py`

**Classes:**
- `_ModelDumpOnlyConfig`

**Functions:**
- `test_resolve_quality_gate_policy_prefers_model_dump`
- `test_policy_runtime_resolve_agent_policy_prefers_model_dump`

## `tests/test_premortem.py`

**Classes:**
- `TestDetectScopeFileRisk`
- `TestDetectStaleTestRisk`
- `TestDuplicateFunctionRisk`
- `TestConflictingImportRisk`
- `TestLongFunctionRisk`
- `TestComplexityRisk`
- `TestNestingDepthRisk`

**Functions:**
- `_spec`
- `test_verification_step_to_dict`
- `test_premortem_risk_to_dict_has_all_keys`
- `test_premortem_result_has_risks_true`
- `test_premortem_result_has_risks_false`
- `test_premortem_result_to_dict_shape`
- `test_blueprint_risk_fires_for_core_py_scope`
- `test_blueprint_risk_fires_for_core_py_in_risk_hints`
- `test_blueprint_risk_no_fire_for_non_core`
- `test_blueprint_risk_command_includes_file`
- `test_blueprint_risk_command_is_comment_when_no_scope_files`
- `test_blueprint_risk_command_has_no_placeholder_when_scope_files_present`
- `test_packaging_risk_fires_for_core_py`
- `test_packaging_risk_fires_for_cli_entry`
- `test_packaging_risk_fires_for_af_spec`
- `test_packaging_risk_no_fire_for_tests_only`
- `test_workspace_risk_fires_for_dogfood_scope`
- `test_workspace_risk_fires_for_worktree_hint`
- `test_workspace_risk_case_insensitive`
- `test_workspace_risk_no_fire_for_unrelated`
- `test_destructive_risk_fires_for_policy`
- `test_destructive_risk_fires_for_constraint`
- `test_destructive_risk_no_fire_when_absent`
- `test_assumption_risk_fires_for_low_confidence`
- `test_assumption_risk_fires_for_unknown_confidence`
- `test_assumption_risk_fires_for_missing_confidence`
- `test_assumption_risk_skips_medium_confidence`
- `test_assumption_risk_skips_high_confidence`
- `test_assumption_risks_counter_sequential`
- `test_gap_risk_fires_for_each_gap`
- `test_gap_risk_no_risks_for_empty`
- `test_gap_risk_description_contains_question`
- `test_run_premortem_empty_spec_no_risks`
- `test_run_premortem_core_py_triggers_r1_r2`
- `test_run_premortem_dogfood_scope_triggers_r3`
- `test_run_premortem_destructive_policy_triggers_r4`
- `test_run_premortem_gaps_become_risks`
- `test_run_premortem_low_confidence_assumptions_become_risks`
- `test_run_premortem_to_dict_has_all_keys`
- `test_run_premortem_full_pipeline_no_duplicate_ids`
- `test_run_premortem_no_duplicate_ids_with_many_assumptions`
- `test_gap_start_shifts_when_many_assumptions`
- `test_pattern_risk_fires_on_scope_overlap`
- `test_pattern_risk_skips_when_no_overlap`
- `test_pattern_risk_skips_empty_findings`
- `test_pattern_risk_skips_finding_without_path`
- `test_pattern_risk_has_two_verification_steps`
- `test_pattern_risk_id_r10_no_collision_with_assumptions`
- `test_run_premortem_with_research_findings_adds_r10`

## `tests/test_project_context_sync.py`

**Functions:**
- `_write`
- `test_collect_snapshot_excludes_docs_task_by_default`
- `test_collect_snapshot_excludes_docs_archive_by_default`
- `test_collect_snapshot_applies_env_excludes`
- `test_collect_snapshot_applies_env_exclude_glob`
- `test_resolve_project_root_prefers_local_project_when_repo_name_collides`
- `test_resolve_project_root_supports_explicit_repo_alias`
- `test_resolve_project_root_supports_powershell_safe_repo_alias`
- `test_resolve_project_root_normalizes_project_path_to_collision_safe_sync_id`
- `test_normalize_newlines_variants`
- `test_normalize_newlines_does_not_duplicate_lines`
- `test_write_text_emits_lf_only`
- `test_write_text_normalizes_crlf_input`
- `test_read_write_round_trip_is_stable`

## `tests/test_project_overrides.py`

**Functions:**
- `_load_launcher`
- `_load_keyless_modules`
- `test_project_skill_override_priority`
- `test_agent_override_merge`
- `test_config_paths_supports_keyless_cli_bootstrap`
- `test_agent_manager_falls_back_without_engine_api_keys`

## `tests/test_project_pipeline.py`

**Functions:**
- `_load_launcher`
- `test_factory_routes_complex_task_to_project_pipeline`
- `test_factory_routes_project_pipeline_directly_in_fsa_mode`
- `test_project_pipeline_writes_planning_artifacts_and_roles`
- `test_project_pipeline_routes_runtime_workspace_to_orchestrator`
- `test_factory_single_run_auto_creates_todo_for_complex_task`
- `test_factory_single_run_keeps_existing_todo_file`

## `tests/test_project_policy_defaults.py`

**Functions:**
- `_load_launcher`
- `test_project_scaffold_policies_include_external_skill_defaults`

## `tests/test_project_scope.py`

**Functions:**
- `_load_launcher`
- `test_project_scaffold_files_created`
- `test_register_built_updates_skill_lock`
- `test_context_schema_validation_blocks_run`

## `tests/test_project_task_board_dispatch.py`

**Functions:**
- `_make_task`
- `test_next_board_tasks_prefers_same_module_build_after_scope_completes`
- `test_next_board_tasks_module_numeric_suffix_sorted_as_int`
- `test_next_board_tasks_falls_through_completed_module_to_next`
- `test_project_pipeline_imports_without_nameerror`
- `test_module_sort_key_handles_id_without_numeric_suffix`
- `test_compute_max_cycles_pending_zero_falls_back_to_floor`
- `test_compute_max_cycles_scales_with_pending_count`
- `test_compute_max_cycles_counts_only_open_tasks`
- `test_compute_max_cycles_defends_against_malformed_board`
- `test_dependency_satisfied_module_dep_uses_task_level_when_status_is_stale`
- `test_dependency_satisfied_module_dep_blocks_when_any_task_pending`
- `test_compute_max_cycles_logs_on_load_failure`
- `_role_plan_with_tasks`
- `test_build_project_board_injects_verification_focus_into_acceptance`
- `test_build_project_board_without_structured_evidence_keeps_acceptance`
- `test_build_project_board_acceptance_injection_is_idempotent`
- `test_board_prompt_digest_exposes_task_id_phase_and_acceptance`
- `test_board_prompt_digest_bounds_acceptance_length`
- `test_board_prompt_digest_empty_board_unchanged`
- `test_build_project_board_caps_verification_focus_count`
- `test_build_project_board_trims_long_verification_focus_item`
- `test_write_task_execution_plan_includes_injected_verification_focus`
- `test_clean_list_string_not_split_into_chars`
- `test_clean_list_list_input_unchanged`
- `test_clean_list_none_returns_empty`
- `_write_board`
- `_completed_build`
- `test_inject_review_tasks_single_available_provider_no_cross_validate`
- `test_inject_review_tasks_two_available_providers_sets_review_provider`

## `tests/test_provider_detect.py`

**Functions:**
- `isolated_cache`
- `fresh_cache`
- `test_t01_not_installed_no_ping`
- `test_t02_installed_ping_ok`
- `test_t03_ping_auth_fail`
- `test_t04_ping_timeout`
- `test_t05_fresh_cache_no_ping`
- `test_t06_expired_cache_re_ping`
- `test_t07_force_refresh_ignores_fresh_cache`
- `test_t08_skip_provider_masks_as_not_installed`
- `test_t08b_skip_does_not_pollute_cache`
- `test_t09_skip_provider_alias_normalization`
- `test_t10_corrupt_cache_ignored`
- `test_t10b_partial_corrupt_state_re_probed`
- `test_t11_cache_write_permission_error`
- `test_t12_concurrent_cache_writes`
- `test_cli_json_output_fan_out_blocked`
- `test_cli_command_env_override_used_in_ping`
- `test_cli_skip_gives_empty_fan_out`
- `test_t13_installed_set_computed_once_before_threadpool`
- `test_t14_concurrent_detect_provider_states`
- `_future_iso`
- `_past_iso`
- `test_inv1_mark_rate_limited_detected`
- `test_inv2_expired_rate_limit_recovers`
- `test_inv3_cli_json_includes_rate_limited`
- `test_inv4_detect_rate_limit_signal_with_pattern`
- `test_inv4b_detect_rate_limit_signal_with_iso_reset`
- `test_inv5_detect_rate_limit_signal_normal_text`
- `test_inv6_detect_rate_limit_signal_fallback`
- `test_inv7_backward_compat_no_rate_limited_until`
- `test_inv8_run_provider_limit_calls_mark`
- `test_inv8_non_limit_error_does_not_mark`
- `test_inv9b_use_cache_false_preserves_rate_limited`
- `test_inv9_force_refresh_preserves_rate_limited`

## `tests/test_provider_instruction_sync.py`

**Functions:**
- `_read`
- `_hook_text`
- `_markers`
- `_extract_between_markers`
- `test_inv1_start_marker_present`
- `test_inv1_end_marker_present`
- `test_inv2_no_drift`
- `test_inv3_idempotent`
- `test_inv4_agents_md_has_roster_section`
- `test_inv4_agents_md_has_common_block`
- `test_inv4_agents_yaml_ids_in_roster`
- `test_inv5_missing_start_marker_raises`
- `test_inv5_missing_end_marker_raises`
- `test_inv5_no_instructions_file_returns_error`
- `test_inv6_no_redeclare_agent_record`
- `test_inv6_no_redeclare_collect_records`
- `test_inv6_sync_imports_from_generate_agents_md`
- `test_inv7_precommit_calls_sync_script`
- `test_inv7_precommit_triggers_on_instructions_md`
- `test_inv7_precommit_triggers_on_agents_yaml`
- `test_inv7_no_or_true_on_sync_call`
- `test_inv7_exit_1_path_exists_after_sync_failure`
- `test_inv8_render_roster_function_exists`
- `test_inv8_render_roster_no_markers`
- `test_inv8_main_does_not_write_agents_md_directly`

## `tests/test_q_s3_path_c.py`

**Classes:**
- `TestBriefBackedCaller`
- `TestPathCNoHitlOnSkip`
- `TestQuestionResultProvenance`
- `TestProjectGoalArtifactQaFields`
- `TestWriteProjectGoalQaFields`
- `TestGenerateWorkItemsPassesQuestionRouter`
- `TestSynthesizeResearchAnswers`
- `TestSynthesizeViaResearch`

**Functions:**
- `_make_rs_question`
- `_make_llm_question`

## `tests/test_qa_report.py`

**Classes:**
- `TestRenderHtmlFileOutput`
- `TestVerifiedSection`
- `TestFailedSection`
- `TestCannotVerifySection`
- `TestUnverifiedSection`
- `TestConfirmRequiredSection`
- `TestBuildEvidenceLedgerProvenance`

**Functions:**
- `_ledger`
- `_goal`

## `tests/test_quality_contract.py`

**Classes:**
- `TestQualityContractBuilder`
- `TestChecklistMerger`

**Functions:**
- `test_non_empty_contract_for_all_domains`
- `test_poker_overlay_applied_only_for_poker`

## `tests/test_registry.py`

**Functions:**
- `test_registry_yaml_format`
- `test_registry_normalizes_list_form_install_candidates_source_id`
- `test_registry_preserves_external_candidate_metadata`

## `tests/test_registry_manager_codex_skills.py`

**Functions:**
- `_load_registry_manager`
- `test_registry_manager_installs_codex_markdown_skill_directory`
- `test_registry_manager_iter_install_candidates_preserves_source_metadata`
- `test_registry_manager_init_falls_back_to_read_only_on_permission_error`
- `test_install_skill_file_blocked_when_registry_write_disabled`
- `test_install_skill_file_blocked_leaves_no_registry_entry`
- `test_workflow_apply_skipped_when_registry_write_disabled`
- `test_register_built_skipped_when_registry_write_disabled`

## `tests/test_repo_shortcuts.py`

**Functions:**
- `test_resolve_repo_path_prefers_sibling_repo`
- `test_resolve_repo_path_falls_back_to_env_root`

## `tests/test_request_router.py`

**Classes:**
- `_Classifier`

**Functions:**
- `test_router_selects_project_pipeline_for_complex_build_request`
- `test_router_keeps_single_pipeline_for_simple_fix_request`

## `tests/test_requirement_llm.py`

**Functions:**
- `test_model_router_requirement_compares_multiple_engine_candidates`
- `test_requirement_analyzer_uses_cli_provider_when_engine_api_keys_disabled`

## `tests/test_research_brief.py`

**Functions:**
- `_interview_artifact`
- `_bare_brief`
- `test_build_from_interview_full_artifact`
- `test_build_from_interview_bare_dict`
- `test_build_from_interview_empty_fields`
- `test_build_from_interview_strips_blanks`
- `test_tag_evidence_matching`
- `test_tag_evidence_empty_brief_all_on_brief`
- `test_tag_evidence_does_not_mutate_originals`
- `test_split_evidence_separates_correctly`
- `test_split_evidence_all_on_brief_when_empty_brief`
- `test_split_evidence_preserves_on_brief_false_tag`

## `tests/test_research_depth.py`

**Classes:**
- `TestResearchDepth`

## `tests/test_research_p1_quality_gate.py`

**Classes:**
- `TestB2PokerYamlExists`
- `TestB3LoadDomainManifest`
- `TestB1IdentifyUnmetGaps`
- `TestB1RecoveryLoopCap`
- `TestB4EmitEvidenceFiles`
- `TestB5EmitCoverageReport`
- `TestB1RecoveryLoopIntegration`

## `tests/test_research_router_modes.py`

**Classes:**
- `TestResearchRouterInitialMode`
- `TestResearchRouterFinalMode`
- `TestResearchRouterSecondaryModes`
- `TestResearchRouterWebNotebook`
- `TestResearchRouterAccuracyGate`
- `TestEvidenceFnKwargs`
- `TestGapToMode`
- `TestDetectComplexityGaps`

**Functions:**
- `_simulate_final_mode`

## `tests/test_research_router_phase1b.py`

**Classes:**
- `TestWebSearchFieldSplit`
- `TestBuildSourcePack`
- `TestSynthesizeStructuredEvidence`
- `TestVerifier4Metric`
- `TestQualityTierGapNoJump`

## `tests/test_research_system_regression.py`

**Classes:**
- `TestG1KoreanFreshnessTokenMatch`
- `TestG1KoreanPlayerCountMatch`
- `TestG2FastSynthesisSecondaryFreshLookup`
- `TestG3TavilyUnsetFallbackPath`
- `TestG4EvidenceParallelRunsWithinBudget`
- `TestG5ClaimCountMinimumWhenSourcesPresent`
- `TestG4LocalWebNoPipelineRace`
- `TestB1MaxRoundsCapPreventsInfiniteLoop`
- `TestC1DomainSpecGate`
- `TestC3AdrGenerator`
- `TestC4TraceabilityGenerator`

## `tests/test_researcher_feedback_ranking.py`

**Functions:**
- `test_researcher_applies_feedback_aware_ranking_to_evidence`

## `tests/test_resume_brief.py`

**Functions:**
- `test_write_resume_brief_summarizes_manifest_todo_and_latest_session`
- `test_refresh_resume_briefs_resolves_collision_safe_project_root`

## `tests/test_resume_brief_session_adapter.py`

**Functions:**
- `test_finalize_cli_session_updates_resume_brief`

## `tests/test_review_bundle.py`

**Functions:**
- `_bundle`
- `test_grep_risks_detects_subprocess`
- `test_grep_risks_detects_shell_true`
- `test_grep_risks_clean_file`
- `test_grep_risks_missing_file`
- `test_build_returns_dict`
- `test_build_engine_field`
- `test_build_empty_list`
- `test_save_creates_file`
- `test_save_includes_risk`
- `test_save_new_format_contains_desc`
- `test_save_dynamic_import_desc`
- `test_grep_risks_dynamic_import`
- `test_grep_risks_with_windows_style_path`
- `test_load_returns_none_when_missing`
- `test_load_returns_raw_after_save`

## `tests/test_review_consensus.py`

**Classes:**
- `TestConsensusSidecarAbsent`
- `TestCollectEvidenceNoLlm`
- `TestUnverifiedNoFileLine`
- `TestNoProviderBranch`
- `TestSurroundingCode`
- `TestEnclosingFunction`
- `TestFindCallees`
- `TestFindCallers`
- `TestMain`

**Functions:**
- `_make_py`
- `_make_findings_json`

## `tests/test_review_gate.py`

**Functions:**
- `ws`
- `_write_state`
- `_base_state`
- `_full_reviews`
- `test_a_empty_queue_pass`
- `test_b_missing_tier1_block`
- `test_c_missing_tier2_block`
- `test_d_missing_tier3_block`
- `test_e_stale_review_block`
- `test_f_new_files_added_block`
- `test_g_all_tiers_pass`
- `test_g2_t3_skip_requires_only_tier1_and_tier2`
- `test_g2b_t3_skip_requires_critic_no_advisory`
- `test_g2c_critic_t3_escalation_rearms_pending_prompt`
- `test_g3_t3_skip_ignored_for_blast_tier3`
- `test_g4_t3_skip_requires_matching_decision_files`
- `test_h_verdict_block_without_env`
- `test_h2_verdict_fail_without_env`
- `test_i_verdict_block_with_env`
- `test_j_skip_gate_env`
- `test_record_and_clear`
- `test_no_py_files_pass`
- `test_staged_py_not_queued_no_queue`
- `test_staged_py_not_queued_empty_py_in_queue`
- `test_staged_non_review_py_no_queue_passes`
- `test_staged_py_not_in_snap_blocks_even_if_queue_fully_reviewed`
- `test_staged_skills_skill_py_blocks`
- `test_staged_skills_nested_not_review_target`
- `test_clear_stale_reset_when_round_passed_and_idle`
- `test_clear_no_stale_reset_when_round_in_flight`
- `test_clear_stale_reset_at_round_count_one`
- `test_clear_no_stale_reset_when_round_count_corrupt`
- `test_clear_no_stale_reset_when_last_round_had_block`
- `test_c1_fence_inner_single_verdict_line`
- `test_c2_body_quote_outside_fence_uses_fence_only`
- `test_c3_no_fence_two_patterns_last_position_wins`
- `test_c3b_no_fence_symmetric_swap_position_wins`
- `test_c4_no_fence_critic_format_compat`
- `test_c5_no_fence_no_verdict_line_returns_none`
- `test_c6_multiple_fences_last_pair_wins`
- `test_c7_no_fence_trailing_body_quote_known_limitation`
- `test_t3_advisory_parser_uses_last_value`
- `test_t3_advisory_parser_missing_is_unknown`
- `test_t3_advisory_parser_fence_only`
- `test_t3_advisory_parser_conflicting_values_fail_closed`
- `test_t3_advisory_parser_multiple_values_without_section_unknown`
- `test_workspace_path_consistency_via_log_event`
- `test_cli_record_with_t3_required_advisory`
- `test_cli_record_without_t3_required_defaults_to_unknown`
- `test_cli_record_t3_required_invalid_choice_rejected`
- `test_t3_skip_classifier_version_single_source`
- `test_cli_record_non_critic_does_not_persist_t3_required`
- `test_is_always_tier3_risk_files`
- `test_is_always_tier3_non_risk_files`
- `_telemetry_state`
- `test_telemetry_skip_enacted_true`
- `test_telemetry_skip_enacted_false_when_decision_false`
- `test_telemetry_skip_enacted_false_blast3`
- `test_telemetry_skip_enacted_false_risk_file`
- `test_telemetry_skip_enacted_false_no_decision`
- `test_required_tiers_telemetry_skip`
- `test_required_tiers_always_tier3_overrides_telemetry`
- `test_required_tiers_blast3_no_telemetry_skip`
- `test_required_tiers_no_skip_default`
- `test_required_tiers_blast1`

## `tests/test_review_gate_phase0.py`

**Functions:**
- `ws`
- `_write_state`
- `test_t1_tier1_only_test_runner_required`
- `test_t1b_tier1_no_test_runner_blocks`
- `test_t2_round_count_increments_on_full_completion`
- `test_t3_has_block_true_on_block_verdict`
- `test_t3b_has_block_true_on_fail_verdict`
- `test_t4_claim_id_present`
- `test_t5_classify_tier3_known_paths`
- `test_t5f_path_normalization`
- `test_t5g_tier3_paths_exist_on_disk`
- `test_t5h_regex_call_patterns_only`
- `test_t5i_regex_literal_exec_eval`
- `test_t5j_invalid_tier_raises`
- `test_t6_round_count_no_double_increment_on_same_round_re_record`
- `test_t7_clear_resets_round_metadata`
- `test_t8_block_verdict_checked_even_when_rounds_capped`
- `test_t9_claim_id_includes_round_and_uses_utc`
- `test_t5b_classify_tier1_docs`
- `test_t5c_classify_tier2_default`
- `test_t5d_required_agents_per_tier`
- `test_t5e_classify_with_content_promotes_to_tier3`

## `tests/test_review_metrics_logger.py`

**Functions:**
- `metrics_mod`
- `ws`
- `test_findings_count_empty`
- `test_findings_count_single_accept_star`
- `test_findings_count_warn`
- `test_findings_count_block`
- `test_findings_count_multiple`
- `test_findings_count_no_false_positive`
- `test_findings_count_rejected`
- `test_findings_count_case_insensitive`
- `test_findings_count_accept_adv`
- `test_findings_count_bonus`
- `test_findings_count_mixed_labels`
- `test_findings_count_legacy_labels_still_match`
- `test_findings_count_false_positive_in_markdown_fence`
- `test_findings_count_false_positive_in_prose_quote`
- `test_ext_log_none_korean`
- `test_ext_log_none_english`
- `test_ext_log_scope_creep`
- `test_ext_log_items`
- `test_ext_log_single_item`
- `test_ext_log_absent`
- `test_ext_log_colon_variants`
- `test_append_metric_creates_file`
- `test_append_metric_valid_json`
- `test_append_metric_multiple_records`
- `test_append_metric_required_fields`
- `test_append_metric_evidence_defaults`
- `test_append_metric_evidence_values`
- `test_append_metric_extension_log`
- `test_append_skip_audit`
- `test_compute_report_empty`
- `test_compute_report_single_t3_block_only`
- `test_compute_report_t3_rate_zero`
- `test_compute_report_t3_rate_100`
- `test_compute_report_verdict_distribution`
- `test_compute_report_phase4_guidance_low`
- `test_compute_report_phase4_guidance_sufficient`
- `test_compute_report_phase4_skip_suppresses_guidance`
- `test_post_agent_record_writes_metric`
- `_stub_hook_env`
- `test_post_agent_record_duration_ms_passed`
- `test_post_agent_record_duration_ms_absent`
- `_write_t3_commits`
- `test_telemetry_skip_no_data`
- `test_telemetry_skip_insufficient_commits`
- `test_telemetry_skip_insufficient_span`
- `test_telemetry_skip_all_clean`
- `test_telemetry_skip_high_block_only_rate`
- `test_telemetry_skip_recent_block`
- `test_telemetry_skip_prior_skip_caught_block`
- `test_telemetry_skip_span_uses_t3_records_not_all`
- `test_telemetry_block_only_matches_compute_report`
- `test_telemetry_skip_block_only_requires_t1t2_clean`

## `tests/test_review_runner_execute_cli.py`

**Classes:**
- `TestRunProviderExecuteCliChat`
- `TestProviderIdMap`

**Functions:**
- `_make_ok_result`
- `_make_fail_result`

## `tests/test_review_runner_vendor_label.py`

**Functions:**
- `test_critic_role_always_same_vendor`
- `test_cross_role_single_vendor_marker`
- `test_cross_role_single_vendor_korean_phrase`
- `test_cross_role_multi_vendor_default`
- `test_cross_role_block_with_multi_provider`
- `test_reviewer_result_default_vendor_mode`
- `test_reviewer_result_vendor_mode_explicit`
- `test_verdict_parsing_unaffected_by_vendor_label`
- `test_aggregation_notice_text_present_in_module`

## `tests/test_review_skill_router.py`

**Functions:**
- `_ctx`
- `test_blueprint_impact_core_file`
- `test_blueprint_impact_master_blueprint`
- `test_blueprint_impact_af_spec`
- `test_blueprint_impact_scripts_no`
- `test_blueprint_impact_docs_no`
- `test_blueprint_impact_backslash_normalized`
- `test_worktree_work_dogfood_kind`
- `test_worktree_work_self_modifying`
- `test_worktree_work_risk_token`
- `test_worktree_work_filename_contains_dogfood`
- `test_worktree_work_filename_contains_worktree`
- `test_worktree_work_plain_feature_no`
- `test_dedup_preserves_order`
- `test_dedup_empty`
- `test_tier1_only_test_runner`
- `test_tier1_base_skills_only`
- `test_tier1_ignores_packaging_flag`
- `test_tier2_core_dogfood_all_tiers`
- `test_tier2_core_dogfood_blueprint_sync_on_runner`
- `test_tier2_core_dogfood_blueprint_sync_on_critic`
- `test_tier2_core_dogfood_worktree_skills_on_critic`
- `test_tier2_core_dogfood_worktree_skills_on_cross`
- `test_tier2_non_dogfood_no_worktree_skills`
- `test_tier2_packaging_adds_architecture_to_runner`
- `test_tier2_no_packaging_no_architecture_on_runner`
- `test_tier3_adds_verification_to_critic`
- `test_tier3_adds_context_optimization_to_cross`
- `test_tier2_does_not_have_tier3_extras`
- `test_self_modifying_triggers_worktree_skills_even_without_dogfood_file`
- `test_self_modifying_cross_review_skills`
- `test_risk_token_worktree_triggers_worktree_skills`
- `test_no_duplicate_skills_in_tier2_dogfood`
- `test_no_duplicate_skills_in_tier3`
- `test_to_dict_structure`
- `test_tier_profile_to_dict`

## `tests/test_right_sized_router.py`

**Classes:**
- `_StubLLM`

**Functions:**
- `_stub`
- `test_r_light`
- `test_r_full_stage`
- `test_r_lowconf`
- `test_r_floor_tier3`
- `test_r_floor_selfmod`
- `test_r_fb_empty`
- `test_r_fb_exc`
- `test_r_fb_badschema`
- `test_r_fb_noscope`

## `tests/test_rse_router_decoupling.py`

**Classes:**
- `_StubLLM`
- `TestEmptyScopeLLMPath`
- `TestLightAllowed`
- `TestMergePolicyTier3Floor`
- `TestTier3FloorObservation`

**Functions:**
- `_stub`

## `tests/test_rse_slice2.py`

**Functions:**
- `test_e_ssot_member`
- `test_e_import_identity`
- `test_e_no_magic`
- `test_e_floor_const`
- `test_g_none`
- `test_g_empty`
- `test_g_nokey`
- `test_g_in`
- `test_g_out`
- `test_g_or_hit`
- `test_g_or_miss`
- `_make_passthrough_guard`
- `_minimal_pipeline`
- `test_inv_research_skip`
- `test_inv_research_run`
- `_prepared_brief`
- `_run_prepare_documents_with_mocks`
- `test_inv_review_skip`
- `test_inv_review_run`
- `test_inv_norm`
- `test_inv_starter`
- `_make_dogfood_state`
- `test_inv_wire`
- `test_inv_wire_fallback`

## `tests/test_run_build_separation.py`

**Functions:**
- `_load_launcher`
- `test_run_default_skips_build`
- `test_run_with_build_executes_builder`

## `tests/test_run_event_evolution_split.py`

**Classes:**
- `TestRunEventTypeSplit`
- `TestEvolutionDecisionRouting`

## `tests/test_run_factory_cli.py`

**Functions:**
- `_install_fake_agent_launcher`
- `test_run_factory_cli_sets_provider_and_projects_root`
- `test_run_factory_cli_rejects_provider_command_without_provider`
- `test_run_factory_cli_chat_passes_pipeline_options`

## `tests/test_runner_contracts.py`

**Functions:**
- `_load_launcher`
- `_module_from_code`
- `test_tool_filter_and_ctx_merge`
- `test_runtime_rule_default_deny`
- `test_system_prompt_and_signature_resolution`
- `test_load_skills_uses_cache_and_invalidates_on_file_change`
- `test_load_skills_collects_knowledge_markdown`
- `test_load_skills_collects_official_codex_markdown`
- `test_resolve_runtime_feedback_targets_prefers_used_skills`
- `test_resolve_runtime_feedback_targets_uses_only_safe_single_fallback`

## `tests/test_safe_optional_id.py`

**Functions:**
- `test_empty_returns_empty`
- `test_differs_from_safe_id_on_empty`
- `test_non_empty_normalizes`
- `test_both_versions_match_on_short_inputs`
- `test_utils_truncates_at_60`
- `test_ext_no_truncation`

## `tests/test_sandbox_config.py`

**Classes:**
- `TestSandboxDefault`
- `TestSandboxPrecedence`
- `TestSandboxOffArgv`
- `TestSandboxOnArgvUnchanged`
- `TestDeployParity`
- `TestAfSandboxOffWritesBoth`
- `TestGeminiYoloPreserved`
- `TestSetSandboxEnabled`

**Functions:**
- `_make_request`
- `_cmd`

## `tests/test_session_bridge.py`

**Functions:**
- `_write_json`
- `_write_jsonl`
- `_read_json`
- `test_provider_registry_exposes_codex_claude_and_gemini`
- `test_run_bridge_mirrors_codex_sessions_into_global_memory`
- `test_run_bridge_recovers_from_stale_cursor`
- `test_run_bridge_supports_generic_role_content_jsonl`

## `tests/test_setup_wizard_gate.py`

**Functions:**
- `isolated_state`
- `_write_state`
- `test_ensure_tavily_configured_no_prompt`
- `test_ensure_tavily_interactive_input_saves_env`
- `test_ensure_tavily_skip_reconfirm_yes`
- `test_ensure_tavily_skip_reconfirm_no_loop`
- `test_ensure_tavily_noninteractive_mode`
- `test_ensure_notebooklm_module_missing_in_source_mode`
- `test_ensure_notebooklm_chrome_missing_branch`
- `test_ensure_notebooklm_auth_status_parsing_not_authenticated`
- `test_ensure_notebooklm_auth_status_parsing_success`
- `test_ensure_notebooklm_login_subprocess_mock_success`
- `test_ensure_notebooklm_login_failure_retry_then_skip`
- `test_setup_state_atomic_write_crash_simulation`
- `test_setup_state_schema_v1_to_v2_migration`
- `test_setup_state_schema_corrupted_recovery`
- `test_setup_state_filelock_contention`
- `no_side_effects`
- `test_setup_gate_skips_setup_subcommand`
- `test_setup_gate_skips_nlm_internal_subcommand`
- `test_setup_gate_skips_worker_subcommand`
- `test_setup_gate_skips_version_flag`
- `test_setup_gate_skips_invalid_flag`
- `test_setup_gate_skips_help_flag`
- `test_is_meta_arg_matches_help_and_version`
- `test_invoke_nlm_app_standalone_mode_false`
- `test_find_or_create_archive_notebook_parses_uuid`

## `tests/test_signatures.py`

**Functions:**
- `test_signatures`

## `tests/test_skill_eval_harness.py`

**Functions:**
- `_write_skill`
- `_make_report`
- `test_skill_eval_harness_runs_contract_hidden_shadow_and_writes_report`
- `test_skill_promotion_moves_draft_only_to_candidate`
- `test_skill_promotion_moves_candidate_to_canary_when_shadow_nonnegative`
- `test_skill_promotion_demotes_active_skill_on_negative_shadow`
- `test_skill_promotion_demotes_active_skill_on_partial_external_eval_failure`
- `test_skill_eval_harness_replays_runtime_traces_for_shadow_eval`
- `test_skill_eval_harness_replay_compares_against_replayed_baseline_not_recorded_runtime`
- `test_skill_eval_harness_respects_disabled_replay`
- `test_skill_eval_harness_rejects_non_dict_return_values`
- `test_infer_workspace_root_prefers_workspace_for_runs_trace_path`

## `tests/test_skill_evolution_controller.py`

**Classes:**
- `_FakeGateResult`
- `TestSubmitPublished`
- `TestSubmitRejected`
- `TestSubmitDeferred`
- `TestSubmitError`
- `TestPublishRollback`
- `TestRunBudget`
- `TestLedgerNoOp`
- `TestRunEventEmission`

**Functions:**
- `_make_controller`
- `_setup_live_dir`
- `_setup_candidate_dir`

## `tests/test_skill_evolution_safety.py`

**Classes:**
- `TestVerifyEvolvedSkillSandbox`
- `TestRollbackEvolvedSkill`

## `tests/test_skill_evolution_trigger_routing.py`

**Classes:**
- `TestWhitelistConstants`
- `TestOnSkillEvolvedBranching`

## `tests/test_skill_feedback.py`

**Functions:**
- `_read_events`
- `_make_report`
- `test_skill_feedback_loop_records_selection_build_runtime`
- `test_skill_feedback_loop_summarizes_historical_score`
- `test_skill_promotion_emits_feedback_event`
- `test_skill_promotion_prefers_workspace_feedback_log`
- `test_skill_feedback_loop_batches_multiple_summaries`
- `test_skill_promotion_keeps_canary_without_runtime_evidence`
- `test_skill_promotion_promotes_canary_with_runtime_evidence`
- `test_skill_promotion_demotes_active_skill_on_runtime_regression`
- `test_skill_promotion_rejects_skill_id_mismatch`

## `tests/test_skill_forge.py`

**Functions:**
- `test_skill_forge_runs_repair_pass_when_critic_requests_it`
- `test_skill_forge_falls_back_to_local_critic_when_text_output_is_invalid`

## `tests/test_skill_loader_phase2.py`

**Functions:**
- `test_skill_loader_initialization`
- `test_12_cap_enforcement`
- `test_conflict_resolution`
- `test_keyword_matching`
- `test_auto_invocable_skips_archived_and_manual_skills`

## `tests/test_skill_loader_phase4.py`

**Classes:**
- `TestSkillContextConfig`
- `TestAdaptiveSkillLoader`

## `tests/test_skill_lock_utils.py`

**Functions:**
- `_load_utils`
- `test_read_skill_lock_defaults_when_missing`
- `test_lock_skill_state_sets_defaults_and_normalizes_id`
- `test_lock_skill_state_merges_patch_without_dropping_existing_fields`

## `tests/test_skill_metadata_adapter.py`

**Classes:**
- `TestAutoDetectDescriptionFallback`

**Functions:**
- `_write`

## `tests/test_skill_metadata_phase1.py`

**Classes:**
- `TestSkillMetadataSchema`
- `TestSkillMetadataDecorator`
- `TestSkillRegistry`

## `tests/test_skill_metadata_v2_compat.py`

**Functions:**
- `test_convert_skill_md_supports_claude_style_frontmatter`
- `test_convert_skill_yaml_supports_v2_package_fields`
- `test_auto_detect_prefers_skill_yaml_over_skill_md`

## `tests/test_skill_procurer_exact_reuse.py`

**Functions:**
- `_load_launcher`
- `test_procure_multiple_prefers_exact_skill_reuse`

## `tests/test_skill_procurer_external_fallback.py`

**Classes:**
- `_Research`
- `_Registry`
- `_AgentMgr`

**Functions:**
- `_load_skill_procurer`
- `test_procure_multiple_passes_external_attempts_to_builder`
- `test_procure_multiple_denied_external_install_can_still_build`
- `test_procure_multiple_legacy_external_miss_stays_as_miss`

## `tests/test_skill_procurer_logging.py`

**Classes:**
- `_Research`
- `_Registry`
- `_AgentMgr`

**Functions:**
- `_load_skill_procurer`
- `test_procure_multiple_logs_no_key_builder_guidance`
- `test_procure_multiple_logs_cli_builder_failure_detail`

## `tests/test_skill_procurer_reuse_gate.py`

**Classes:**
- `_AgentMgr`

**Functions:**
- `_load_skill_procurer`
- `test_procure_multiple_reuses_high_confidence_candidate`
- `test_shadow_reuse_approval_denied_records_manifest_entry`
- `test_procure_multiple_medium_confidence_candidate_prefers_adaptation_build`
- `test_procure_multiple_writes_feedback_events_for_shadow_reuse`
- `test_procure_multiple_promotes_built_skill_before_install`
- `test_manifest_entry_includes_reuse_decision_for_ranked_reuse`
- `test_manifest_entry_includes_reuse_decision_for_forge`
- `test_manifest_entry_has_no_reuse_decision_for_exact_match`
- `test_shadow_reuse_manifest_installed_reflects_is_installable_false`
- `test_forge_manifest_installed_reflects_is_installable_false`

## `tests/test_skill_quality_gate.py`

**Functions:**
- `_shadow`
- `_report`
- `_make_gate`
- `_skill_dir`
- `test_inv1_delta_positive_passes`
- `test_inv2_delta_negative_rejected`
- `test_inv2b_delta_zero_rejected`
- `test_inv3_no_baseline_passes_contract_only`
- `test_inv4_small_sample_not_blocked`
- `test_inv5_quality_delta_filled`
- `test_inv5b_quality_delta_none_when_no_baseline`
- `test_inv6_baseline_dir_normalized_to_file_path`
- `test_inv7_knowledge_skill_passes_without_harness`

## `tests/test_skill_retrieval_engine.py`

**Functions:**
- `test_retrieval_engine_reuses_high_confidence_verified_candidate`
- `test_retrieval_engine_uses_shadow_reuse_for_medium_confidence_candidate`
- `test_retrieval_engine_forges_when_candidate_is_too_weak`
- `test_retrieval_engine_reranks_candidates_with_feedback_history`
- `test_analyze_capability_gap_full_overlap`
- `test_analyze_capability_gap_partial_missing`
- `test_analyze_capability_gap_boundary_enhance_vs_forge`
- `test_decide_reuse_researcher_candidate_shape_normalizes_capability_meta`
- `test_decide_reuse_empty_required_caps_uses_score_based_enhance`
- `test_skill_gap_capabilities_map_contract`
- `test_skill_gap_capabilities_map_normalizes_safe_id`
- `test_skill_gap_capabilities_map_normalizes_cap_values`
- `test_skill_gap_capabilities_map_skips_blank_need_id`
- `test_decide_reuse_ranked_reuse_downgraded_when_caps_missing`
- `test_decide_reuse_ranked_reuse_preserved_when_no_gap`
- `test_retrieval_engine_uses_batched_feedback_summaries`

## `tests/test_skill_self_evolution_hook_runid.py`

**Classes:**
- `TestRunIdInit`

## `tests/test_skill_spec_synthesizer.py`

**Functions:**
- `test_skill_spec_synthesizer_writes_spec_and_shadow_eval`

## `tests/test_spec_compiler.py`

**Functions:**
- `_interview_artifact`
- `_evidence_bundle`
- `test_compile_spec_extracts_interview_fields`
- `test_compile_spec_no_evidence`
- `test_compile_spec_to_dict_has_all_keys`
- `test_compile_spec_splits_evidence_by_brief`
- `test_compile_spec_gaps_for_unanswered_questions`
- `test_compile_spec_no_gap_when_question_answered`
- `test_compile_spec_empty_brief_no_split`
- `test_compile_spec_clarification_log_fallback_when_scope_absent`
- `test_compile_spec_explicit_scope_takes_priority_over_clarification_log`
- `test_scope_from_clarification_log_excludes_non_goals`
- `test_scope_from_clarification_log_excludes_descriptive_answers`
- `test_scope_from_clarification_log_empty`
- `test_compile_spec_bare_brief_dict`
- `test_str_list_from_list`
- `test_str_list_from_none`
- `test_str_list_from_string`
- `test_detect_gaps_all_answered`
- `test_detect_gaps_unanswered`
- `test_detect_gaps_empty_questions`
- `test_scope_from_intent_extracts_paths`
- `test_scope_from_intent_no_paths`
- `test_scope_from_intent_deduplicates`
- `test_scope_from_intent_excludes_urls`
- `test_scope_from_intent_json_extension_not_truncated`
- `test_scope_from_clarification_log_slash_in_type_hint_excluded`
- `test_scope_from_clarification_log_real_path_included`

## `tests/test_stage0_question_router.py`

**Classes:**
- `TestVerdicts`
- `TestStageArtifacts`
- `TestYAMLValidation`
- `_FakeLLM`
- `_FailLLM`
- `TestQuestionRouterRouting`
- `TestStageRouterCrossYamlUniqueness`
- `TestApprovalGateInitializeSignature`
- `TestLightContextScanner`
- `TestStageRouterWorkKind`
- `TestActiveYamlFiles`
- `TestResearchSynthesizeRoute`
- `TestMergeClarificationProvenance`

**Functions:**
- `_make_schema`

## `tests/test_stage4_7_knowledge_pipeline.py`

**Classes:**
- `TestKeywordSimilarity`
- `TestEpisodeMatcher`
- `TestKnowledgeForger`
- `TestExtractTags`
- `TestKnowledgeInjectionHook`
- `TestJaccardSimilarity`
- `TestMemoryConsolidationForge`

**Functions:**
- `_make_episode`
- `_make_graph_adapter`

## `tests/test_strategy_ledger.py`

**Functions:**
- `ledger`
- `test_batch_increments_pass`
- `test_batch_increments_fail`
- `test_batch_same_key_accumulates`
- `test_batch_empty_is_noop`
- `test_batch_multiple_patterns`
- `test_batch_persists_and_reloads`
- `test_eviction_on_overflow`
- `test_lookup_returns_role_after_enough_samples`
- `test_lookup_returns_none_below_sample_threshold`
- `test_lookup_returns_none_on_low_score`
- `test_pick_owner_role_uses_ledger_after_batch`
- `test_batch_duplicate_entries_accumulate`
- `_make_board_fixture`
- `_make_role_plan`
- `_new_pipeline`
- `test_ledger_skips_on_crashed`
- `test_ledger_skips_on_unknown`
- `test_ledger_skips_on_empty_board`
- `test_ledger_per_module_completed`
- `test_ledger_skips_pending_module`
- `test_ledger_mixed_module_status`
- `test_ledger_seen_dedup_first_outcome_wins`
- `test_ledger_module_missing_in_board`
- `test_ledger_empty_owner_role_skip`
- `test_ledger_4word_truncation`
- `test_ledger_skips_infra_failure`
- `test_ledger_skips_on_owner_drift`

## `tests/test_summary_schema_repeat_count.py`

**Functions:**
- `test_build_summary_schema_with_repeat_count_max_and_any_override`

## `tests/test_sync_claude_memory.py`

**Functions:**
- `test_normalize_newlines_variants`
- `test_write_atomic_emits_lf_only`
- `test_write_atomic_normalizes_crlf_and_multi_cr`

## `tests/test_sync_skill_registry.py`

**Functions:**
- `_load_sync_skill_registry`
- `test_sync_normalize_install_candidates_preserves_legacy_list_form`
- `test_sync_normalize_install_candidates_canonicalizes_legacy_external_keys`

## `tests/test_sync_wrappers.py`

**Classes:**
- `TestStartDbResolveTarget`
- `TestStartDbCommandArgs`
- `TestStartSyncBackendDispatch`

## `tests/test_t3_7_run_event_integration.py`

**Classes:**
- `_CapturingStore`
- `TestRunBudgetCostEvent`
- `TestApprovalGateRunEvent`
- `TestW3IsExecutionOpen`

**Functions:**
- `_make_gate`
- `_write_doc`

## `tests/test_t3_classifier.py`

**Functions:**
- `_mock_file_change`
- `test_docstring_change_skips_t3`
- `test_annotation_change_requires_t3`
- `test_deleted_risk_token_requires_t3`
- `test_deleted_extended_risk_tokens_require_t3`
- `test_function_body_change_requires_t3`
- `test_hard_guard_path_requires_t3_even_for_comment_only`
- `test_t3_policy_files_are_hard_guarded`
- `test_skip_telemetry_jsonl_written`

## `tests/test_t3_skip_report.py`

**Functions:**
- `test_load_records_skips_invalid_json`
- `test_build_report_groups_reason_version_and_files`

## `tests/test_task_template_e2e_command.py`

**Functions:**
- `test_task_template_build_has_todo_marker`
- `test_task_template_scope_has_no_e2e_command`
- `test_task_template_verify_has_todo_marker`

## `tests/test_test_gap_analyzer.py`

**Functions:**
- `test_subprocess_shlex_change_requires_cross_platform_quoted_path_cases`
- `test_cross_platform_quoted_path_cases_satisfy_subprocess_gap`
- `test_cli_packaging_change_requires_frozen_build_evidence`
- `test_frozen_build_evidence_satisfies_packaging_gap`
- `test_subprocess_gap_only_triggers_when_risk_is_in_changed_hunk`
- `test_subprocess_gap_output_is_readable_korean`
- `test_test_file_changes_do_not_trigger_production_gap_gate`
- `test_untracked_python_file_is_analyzed_as_added_diff`
- `test_frozen_build_evidence_requires_meaningful_parity_check`
- `test_meaningful_frozen_build_parity_check_satisfies_gap`
- `test_find_related_tests_by_module_stem_and_import`

## `tests/test_text_integrity.py`

**Functions:**
- `_git`
- `test_detect_newline_style`
- `test_write_text_preserving_format_keeps_bom_and_crlf`
- `test_find_suspicious_markers_detects_common_mojibake`
- `test_find_suspicious_markers_allows_normal_crlf`
- `test_find_suspicious_markers_detects_trailing_control_cr`
- `test_check_paths_against_revision_flags_new_mojibake`
- `test_check_paths_against_revision_flags_new_trailing_control_cr`
- `test_check_script_returns_nonzero_for_new_mojibake`

## `tests/test_triad.py`

**Functions:**
- `_finding`
- `_critical`
- `test_finding_to_dict_keys`
- `test_finding_from_dict_roundtrip`
- `test_report_has_critical_true`
- `test_report_has_critical_false`
- `test_report_critical_findings_filter`
- `test_report_from_dict_roundtrip`
- `test_validate_drops_invalid_evidence_type`
- `test_validate_drops_empty_evidence`
- `test_validate_keeps_valid_finding`
- `test_validate_coerces_unknown_severity`
- `test_validate_all_evidence_types_accepted`
- `test_coerce_verdict_critical_forces_block`
- `test_coerce_verdict_no_critical_unchanged`
- `test_coerce_verdict_unknown_becomes_warn`
- `test_decision_to_dict_roundtrip`
- `test_run_triad_pass_returns_result`
- `test_run_triad_pass_no_findings`
- `_critic_with_high`
- `test_run_triad_high_finding_approved`
- `_critic_with_critical`
- `test_run_triad_critical_raises_blocked_error`
- `test_run_triad_critical_architect_rejects_approved`
- `test_run_triad_critical_architect_hold_still_blocked`
- `test_run_triad_critical_architect_accept_still_blocked`
- `test_run_triad_strips_evidence_free_findings`
- `test_run_triad_uses_module_executor`
- `test_triad_result_to_dict_keys`

## `tests/test_utils.py`

**Classes:**
- `TestTruncateText`
- `TestClamp`
- `TestClampRatio`
- `TestMedian`
- `TestMode`
- `TestVariance`
- `TestStdDev`
- `TestMeanAbsoluteDeviation`
- `TestZscore`
- `TestRangeSpan`
- `TestChunks`
- `TestFlatten`
- `TestTestFileFor`
- `TestNormalize`
- `TestPercentile`
- `TestCumsum`
- `TestRunningMax`
- `TestRunningMin`
- `TestMovingAverage`
- `TestGeometricMean`
- `TestHarmonicMean`
- `TestWeightedMean`
- `TestInterquartileRange`
- `TestCovariance`
- `TestPearsonCorrelation`
- `TestGetExternalSkillRoots`
- `TestSpearmanCorrelation`
- `TestKurtosis`
- `TestSkewness`
- `TestRootMeanSquare`
- `TestExponentialMovingAverage`

## `tests/test_utils_cache.py`

**Functions:**
- `_load_utils`
- `test_read_yaml_cache_returns_copy_and_refreshes`
- `test_append_dashboard_run_keeps_recent_300`
- `test_append_dashboard_run_normalizes_path_fields`
- `test_append_dashboard_run_uses_current_config_after_config_reload`
- `test_read_yaml_cache_hash_verify_detects_same_stat_change`
- `test_read_yaml_cache_eviction_lru`

## `tests/test_warning_override_cli.py`

**Functions:**
- `_run_cli`
- `test_warning_override_add_and_summary`
- `test_warning_override_remove_restores_block`
- `test_dispatch_dict_has_warning_override`

## `tests/test_warning_registry.py`

**Functions:**
- `test_record_creates_jsonl`
- `test_summarize_by_phase`
- `test_concurrent_record`
- `test_registry_requires_workspace`
- `test_record_id_idempotency`
- `test_normalize_phase_alias`
- `test_normalize_phase_unknown`
- `test_normalize_phase_canonical`
- `test_normalize_phase_empty`
- `test_repeat_count_persists`
- `test_summarize_atomic_write`

## `tests/test_warning_registry_cli.py`

**Functions:**
- `test_warning_summary_missing_workspace`
- `test_warning_repair_rebuilds_summary`
- `test_warning_subcommands_in_dispatch`
- `test_warning_summary_dedup_idempotent`

## `tests/test_warning_registry_migration_callsites.py`

**Functions:**
- `test_e2e_command_missing_records_by_phase`
- `test_detect_owner_drift_returns_list`
- `test_detect_owner_drift_no_mismatch_returns_empty`
- `test_evidence_quality_warn_record_on_failure`
- `test_plan_verifier_warn_empty_phase`

## `tests/test_warning_registry_p4a.py`

**Functions:**
- `test_summarize_writes_escalation_phase_from_yaml`
- `test_summarize_falls_back_to_p2_when_yaml_missing_phase`
- `test_write_error_decision_uses_dynamic_phase`

## `tests/test_warning_registry_schema_evolution.py`

**Functions:**
- `test_schema_round_trip`

## `tests/test_warning_stats.py`

**Functions:**
- `_write_jsonl`
- `_warnings_dir`
- `_make_record`
- `test_empty_workspace`
- `test_single_slug_single_record`
- `test_multi_slug_distribution`
- `test_rule_filter`
- `test_phase_filter_record_level`
- `test_malformed_jsonl_skip_warnings_sot`
- `test_slug_filter_core_with_traversal_guard`

## `tests/test_warning_stats_cli.py`

**Functions:**
- `_write_jsonl`
- `_warnings_dir`
- `_make_record`
- `_run_cli`
- `test_cli_workspace_required`
- `test_cli_top_truncation_meta`
- `test_cli_export_csv_affected_ids_json`
- `test_cli_export_json_records_format`
- `test_cli_export_summary_csv_rejected`
- `test_cli_slug_filter_and_sanitization`
- `test_cli_export_phase_filter`
- `test_cli_export_out_atomic`
- `test_cli_warning_stats_unknown_rule_keeps_data`

## `tests/test_watcher_portability.py`

**Classes:**
- `TestProcessAliveUnix`
- `TestProcessAliveWindows`
- `TestIsWatcherAlive`
- `TestStartWatcherWindows`

## `tests/test_web_project_scope.py`

**Functions:**
- `_write_agent`
- `test_project_catalog_prefers_project_copy`
- `test_patch_agent_creates_project_local_copy`

## `tests/test_wig_summarize_wiring.py`

**Functions:**
- `test_summarize_wiring_creates_decision_files`

## `tests/test_wiring_parity.py`

**Functions:**
- `_make_diff`
- `_has_wiring_warn`
- `test_w_param_dead_warns_when_caller_omits_new_param`
- `test_w_param_wired_no_warn_when_caller_passes_param`
- `test_w_new_dead_warns_and_suggests_deferred`
- `test_w_deferred_no_warn_when_marker_present`
- `test_w_util_exempt_no_warn_for_utils`
- `test_w_testonly_warns_when_only_test_caller`
- `test_w_multiline_no_crash`
- `test_w_parse_fail_no_crash`
- `test_w_hunk_split_no_crash`
- `test_w_init_param_skipped_no_false_positive`
- `test_w_test_files_not_checked`

## `tests/test_work_item_generator_backfill.py`

**Functions:**
- `_board_with_tasks`
- `test_backfill_normal_match`
- `test_backfill_no_task_id`
- `test_backfill_todo_marker`
- `test_backfill_duplicate_task_id`
- `test_backfill_exception_returns_original`
- `test_backfill_task_without_e2e_field`
- `test_backfill_task_id_after_e2e`
- `test_backfill_multiple_phases`
- `test_backfill_pass_count`

## `tests/test_work_item_generator_references.py`

**Functions:**
- `test_llm_prior_references_appear_in_bullets`
- `test_llm_prior_only_still_renders`
- `test_d2_fallback_impl_design_contains_phase_flow_section`
- `test_d2_fallback_uses_state_machine_from_domain_specs_summary`
- `test_d2_fallback_generic_phases_when_no_state_machine`

## `tests/test_work_item_generator_structured_evidence.py`

**Functions:**
- `_count_h2`
- `_minimal_brief`
- `_minimal_role_plan`
- `_minimal_task_board`
- `test_spec_fallback_h2_count_unchanged`
- `test_spec_fallback_outline_parseable`
- `test_plan_evidence_has_structured_labels`
- `test_spec_evidence_has_structured_labels`
- `test_design_evidence_has_structured_labels`
- `test_plan_no_new_h2_added`
- `test_inline_strips_newlines`
- `test_structured_evidence_block_no_h2_injection`
- `test_spec_with_injected_newlines_keeps_h2_count`
- `test_skill_gap_bullets_skips_non_dict`
- `test_skill_gap_bullets_empty_on_missing_field`
- `test_structured_evidence_block_empty_brief`

## `tests/test_workflow_autonomy.py`

**Functions:**
- `_load_launcher`
- `test_workflow_state_failed_and_stops_next_stage`
- `test_workflow_persists_portable_paths`

## `tests/test_workspace_scoped_storage.py`

**Functions:**
- `test_storage_for_writes_under_workspace`
- `test_storage_for_isolated_between_workspaces`
- `test_storage_for_same_workspace_returns_same_instance`
- `test_store_for_writes_under_workspace`
- `test_store_for_isolated_between_workspaces`
- `test_store_for_same_workspace_returns_same_instance`

## `tests/verify_aee_cli.py`

**Functions:**
- `test_ultra_flag`
- `test_execution_branch`

## `tests/verify_audit_hash.py`

**Functions:**
- `verify_audit_log`

## `tmp_measure_wiring.py`

**Functions:**
- `_spy`

## `utils/audit_logger.py`

**Functions:**
- `log_audit_event`

## `verify_project_memory.py`

**Functions:**
- `verify_project_memory`

## `verify_project_memory_quick.py`

**Functions:**
- `verify_project_memory_only`

## `version.py`

_(no top-level symbols)_

## `web/api/__init__.py`

_(no top-level symbols)_

## `web/api/agents.py`

**Classes:**
- `AgentCreateRequest`
- `AgentPatchRequest`

**Functions:**
- `_safe_id`
- `_project_root`
- `_project_agents_dir`
- `_agent_file`
- `_scan_agent_items`
- `_effective_agent_items`
- `_resolve_agent_file`
- `_ensure_editable_agent_file`
- `_extract_role`
- `_extract_system_prompt`
- `_to_catalog_item`
- `_load_agent_yaml`
- `_load_agent_dir`
- `list_agents`
- `list_agent_catalog`
- `create_agent`
- `patch_agent`
- `get_agent_model_info`
- `update_agent_model`
- `backfill_preferred_models`

## `web/api/run.py`

**Classes:**
- `RunRequest`

**Functions:**
- `_safe_id`
- `run_agent`

## `web/api/settings.py`

**Classes:**
- `KeyUpdate`

**Functions:**
- `get_engine_status`
- `update_api_key`

## `web/app.py`

**Functions:**
- `lifespan`
- `get_i18n`
- `index`

