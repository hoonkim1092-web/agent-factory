# safe_id() Call-Site Audit — Optional-ID Contract Bug

Scope: `core/*.py`, `scripts/project_context_git_sync.py`, `extract_phase3.py`, `run_factory_cli.py`,
`antigravity_link.py`, `agent_launcher.py`, `web/api/run.py`, `web/api/agents.py` (NOT `tests/`).

Categories:
- **A** = skill-id generation; `"skill"` fallback intended/harmless. Keep `safe_id`.
- **B** = optional-id; empty→`"skill"` causes a real defect. MIGRATE to `safe_optional_id`.
- **C** = no change needed (provably non-empty, or `"skill"` immaterial).

Helper-definition notes (different functions, NOT `core.utils.safe_id`):
- `core/utils.py:60` `safe_id` — the canonical function (def, not a call).
- `core/external_skill_source_ids.py:4` `safe_id` — local copy, `"skill"` fallback (same bug shape).
- `core/install_candidate_utils.py:6` `safe_id` — local copy, `"skill"` fallback (same bug shape).
- `core/memory.py:118` `_safe_id` — local copy IDENTICAL to utils.safe_id (`"skill"`).
- `core/config_paths.py:7` `_boot_safe_id` — local, `"default"` fallback (separate function, distinct contract; its 3 calls are NOT in this audit's `safe_id(` scope).
- `core/skill_creator.py:98` `_safe_id` — local, NO fallback (returns `""`) — already safe-optional.
- `scripts/project_context_git_sync.py:19` `_safe_id` — local, NO fallback — already safe-optional.
- `web/api/run.py:28` `_safe_id` — local, `"default"` fallback.
- `web/api/agents.py:58` `_safe_id` — local, `"agent"` fallback.
- `antigravity_link.py:43` `safe_id(text, fallback="")` — local, parameterized fallback — already safe-optional capable.

---

## core/utils.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 60 | `def safe_id` | — | function definition, not a call site |
| 158/233/319 | `sid = safe_id(skill_id)` | A | skill-id minting helpers (skill path/dir resolution) |
| 359 | `key = safe_id(role_spec)` | C | role_spec required for agent override resolution |
| 364/366 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded by `.strip()` — empty filtered out |

## core/agent_specializer.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 47 | `agent["_task_id"] = safe_id(task_meta.get("task_id") or task_meta.get("id",""))` | **B** | optional task_id; empty→"skill" persisted as specialized-agent `_task_id` identity |
| 79 | `task_id = safe_id(task_meta.get("task_id") or task_meta.get("id",""))` | **B** | optional; flows to `mailbox_prompt_digest(task_id=...)` (line ~114) → wrong mailbox scope |
| 111 | `owner_role = safe_id(task_meta.get("owner_role",""))` | **B** | optional owner_role; empty→"skill"; `or safe_id(base_agent role)` (line 113) is DEAD CODE; used as mailbox role |
| 113 | `... or safe_id(str(base_agent.get("role","")))` | C | dead branch (never reached); the `role` value itself non-empty if reached |
| 174 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded |
| 219 | `tid = safe_id(str(task.get("task_id","")))` | **B** | board task_id as dict key; missing id→"skill" key collision; lookup at 225 |
| 225 | `dep_key = safe_id(dep_id)` | **B** | dependency key; empty dep_id→"skill" false-matches task_map keyed "skill" |

## core/bootstrap_roles.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 105 | `sid = safe_id(role_id)` | **B** (doubt) | role_id param; empty→"skill" persisted as agent `id`; uncertain (callers usually pass real role) |
| 135 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded |
| 215 | `role_id = safe_id(... or "role")` | C | literal `"role"` fallback; `if not role_id` dead guard (flag) |
| 224/229 | guarded comprehensions | C | guarded |
| 247 | `step_id = safe_id(... or f"step_{index}")` | C | f-string fallback non-empty; `if not step_id` dead guard (flag) |
| 270 | `module_id = safe_id(... or f"module_{index}")` | C | f-string fallback; `if not module_id` dead guard (flag) |
| 277 | `task_id = safe_id(... or f"{module_id}_task_{task_index}")` | C | f-string fallback; `if not task_id` dead guard (flag) |
| 285 | `"owner_role": safe_id(str(raw_task.get("owner_role") or item.get("owner_role") or ""))` | **B** | optional owner_role; empty→"skill" persisted as task owner identity |
| 286 | `"phase": safe_id(str(... or "build")) or "build"` | C | `or "build"` input non-empty; outer `or "build"` dead (flag) |
| 288 | guarded depends_on comprehension | C | guarded |
| 303 | `"owner_role": safe_id(str(item.get("owner_role") or ""))` | **B** | optional module owner_role; empty→"skill" persisted as identity |
| 305 | guarded depends_on comprehension | C | guarded |
| 323 | `safe_id(str(r.get("id",""))) in qa_ids` | C | membership vs fixed set; "skill"∉qa_ids, ""∉qa_ids — outcome identical |
| 334 | `safe_id(str(r.get("id",""))) == "qa_engineer"` | C | equality vs literal; "skill"≠it, ""≠it — outcome identical |
| 365/367 | `safe_id(str(m.get("id","")))` (module id, filter+collect) | **B** | empty module id→"skill" passes `if safe_id(...)` filter → "skill" enters depends_on list |
| 379/381 | `safe_id(str(m.get("id","")))` (module id, filter+collect) | **B** | same — "skill" enters qa verify-task depends_on |

## core/agent_runner.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 160/161/163/164/165/166/167 | skill/tool id set comprehensions | C | all guarded by `if safe_id(...)` / `if str(x).strip()` |
| 207/208 | `sid`/`tname` in `_is_tool_allowed` | C | followed by `if sid and sid in <set>` membership; "skill" won't be in real-id sets |
| 236/237 | `sid`/`tname` in `_requires_tool_approval` | C | same membership-guarded pattern |
| 258 | `sid = safe_id(str(getattr(fn,"_skill_id","")))` | **B** | builtin tool w/o `_skill_id`→"skill"; `needs.append((sid or "unknown",...))` — `or "unknown"` DEAD |
| 648 | `sid = safe_id(str(sid))` | A | skill-id normalization for `resolve_skill_paths` |
| 719/723 | skill ids in `_collect_loaded_skill_ids` | A | loaded-module skill ids; `"skill"` fallback in skill-id domain |
| 734/742/743 | feedback-target skill ids | C | guarded by `if safe_id(...)` |
| 753 | `safe_id(agent.get("id") or ... or "agent")` | C | literal `"agent"` fallback — safe_id never sees empty |
| 759 | `current_task_id = safe_id(str(ctx.get("task_id") or ""))` | **B** | ctx task_id (set at 967, may be "skill"); flows to `read_mailbox`/`send` task scope |
| 855/856 | `project_id = safe_id(os.path.basename(workspace))` | C | abspath basename non-empty |
| 866 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded |
| 948 | `"task_id": safe_id(task_id)` (chat_trace.json) | **B** | `run()` param `task_id=""`; empty→"skill" persisted as trace identity |
| 967 | `"task_id": safe_id(task_id)` (ctx) | **B** | empty→"skill" pollutes ctx identity (validated + downstream) |
| 1131 | `"task_id": safe_id(task_id)` (agent_state) | **B** | empty→"skill" persisted as agent_state identity |
| 1184 | `skill_ids = [safe_id(str(s)) for s in agent.get("skills",[])]` | C | unguarded but only feeds `if "core_memory" in skill_ids`; "skill"≠"core_memory" |
| 1459 | `safe_id(str(getattr(tool_func,"_skill_id","")))` | C | feeds approval membership check; "skill"/"" both fail membership — immaterial |

## core/builder.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 145/197 | `run_id=f"{run_id}_{safe_id(provider_id)}"` | C | provider_id iterated from provider list — always non-empty |
| 282 | `mode = safe_id(str(decision.get("mode") or ""))` | C | `if mode != "shadow_reuse"` — "skill" and "" both ≠ it; outcome identical |
| 286 | `candidate_skill_id = safe_id(str(... or ""))` | **B** | optional; `if not candidate_skill_id` DEAD guard; empty→"skill"→`resolve_skill_paths("skill")` |
| 320 | `skill_id = safe_id(skill_name)` | A | skill-id minting (skill dir) |

## core/dynamic_orchestrator.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 186 | `task_id = safe_id(item.get("task_id"))` | **B** | CALIB #3 — missing task_id→"skill"→`if task_id` truthy→"skill" in completed-key set |
| 191 | `safe_id(text)` | C | guarded by `if text:` at 190 |
| 198 | `tid = safe_id(task.get("task_id"))` | **B** | board task missing id→"skill"→`if tid` truthy→"skill" in completed keys |
| 210 | `tid = safe_id(ev.step_id)` | C | guarded by `if ... and ev.step_id` |
| 219 | `safe_id(prefix) == safe_id(role)` | C | malformed prefix→"skill" won't equal a real role's id — immaterial |
| 226 | `safe_id(prefix)` | C | malformed prefix→"skill"; "skill"/"" both fail real-role match |
| 237 | `safe_id(t.get("task_id")) == safe_id(task_id)` | **B** (doubt) | equality match; empty task_id→"skill"=="skill" false-match copies wrong module_id |
| 271 | `safe_id(item) not in completed` | C | `item` from todo list filtered non-empty (line 178) |
| 430 | `safe_id(item) for item in _completed_todo_items(...)` | C | items pre-filtered non-empty |
| 436 | `task_key = safe_id(str(task.get("task_id") or task.get("subtask_instruction") or ""))` | **B** | LLM task both absent→"skill"; `if task_key and task_key in completed` membership |
| 484/491 line 484 is docstring | — | docstring text, not a call |
| 491 | `target_id = safe_id(task_id)` | **B** | CALIB #2 — empty task_id→"skill" passes `if not target_id` guard → pointless scan |
| 498 | `safe_id(str(task.get("task_id",""))) == target_id` | **B** | stored side paired with 491; board task missing id→"skill"=="skill" false-match |
| 741 | `safe_id(task_id) in _completed` | C | guarded by `if task_id:` at 739 |

## core/capability_intent.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 33 | `skill_id = safe_id(skill_name)` | A | skill-id minting for intent |
| 56 | `cap_id = safe_id(str(raw_value.get("id") or ""))` | **B** | optional capability id; `if not cap_id` DEAD guard; "skill" persisted as CapabilityNeed id |
| 68 | `cap_id = safe_id(str(raw_value))` | **B** | optional; `if cap_id` truthy guard defeated; "skill" CapabilityNeed appended |
| 74 | `missing_id = safe_id(str(raw_missing))` | **B** | optional; `if not missing_id` DEAD guard; "skill" appended as need |
| 102 | `safe_id(...) if evidence.get("top_candidate") else ""` | C | outer guard ensures non-empty input |
| 121 | `cap_id = safe_id(item.id)` | **B** | `if not cap_id` DEAD guard; "skill" survives dedupe as capability id |
| 139 | `text = safe_id(str(value or ""))` | **B** (doubt) | tokenize; empty value→"skill" token injected into token set → spurious overlap |

## core/config_paths.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 7 | `def _boot_safe_id` | — | separate function (`"default"` fallback); 47/51/57 calls are `_boot_safe_id`, out of `safe_id(` scope |

## core/external_skill_source_ids.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 4 | `def safe_id` | — | local function definition (`"skill"` fallback) |
| 52 | `sid = safe_id(str(raw or ""))` | **B** | `if not sid: return default` is DEAD; empty raw→"skill" returned instead of `default` param |

## core/external_skill_sources.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 92 | `repo_name = safe_id(os.path.basename(entry)...) or f"external_{i}"` | C | basename of non-empty repo path; `or` branch dead (flag) |
| 97 | `kind = safe_id(str(entry.get("kind") or "repo_cache"))` | C | literal default; `if kind != "repo_cache"` outcome identical |
| 149 | `return safe_id(name)` | C | guarded by `if name:` |
| 150 | `return safe_id(os.path.basename(skill_dir))` | A | skill-id from dir name |
| 223 | `repo_name = safe_id(os.path.basename(url)...) or f"repo_{i}"` | C | basename of non-empty url; `or` dead (flag) |
| 267 | `skill_id = safe_id(str(item.get("id") or ""))` | **B** | `if not skill_id` DEAD guard; "skill" persisted as ExternalSkillCandidate id |
| 277 | guarded capabilities comprehension | C | guarded |
| 384 | `skill_id = safe_id(str(item.get("id") or ""))` | **B** | `if not skill_id` DEAD guard; "skill" candidate id |
| 394 | guarded capabilities comprehension | C | guarded |
| 425 | `skill_id = safe_id(str(item.get("id") or ""))` | **B** | `if not skill_id` DEAD guard; "skill" candidate id |
| 435 | guarded capabilities comprehension | C | guarded |
| 470 | `top_candidate = safe_id(str(target.get("top_candidate") or ""))` | **B** | `if top_candidate` truthy guard defeated; "skill" appended to preferred list |
| 476 | `candidate_id = safe_id(str(... or ""))` | **B** | `if candidate_id` truthy guard defeated; "skill" appended to preferred |
| 487 | `candidate_id = safe_id(candidate.skill_id)` | **B** (doubt) | paired consistency; candidate skill_id "skill"→false `in preferred_ids` |
| 507 | guarded needs comprehension | C | guarded |

## core/memory.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 118 | `def _safe_id` | — | local def (identical to utils.safe_id) |
| 125 | `aid = _safe_id(agent_id) if agent_id else "general"` | C | outer `if agent_id` ensures non-empty input |

## core/external_skill_candidate_importer.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 33 | `default=safe_id(str(source_id or ""))` | **B** | empty source_id→"skill" as source identity (cache root segment, persisted) |
| 39 | `safe_id(f"{source_id}_{skill_id}")` | C | f-string; callers guard skill_id; realistic inputs non-empty |
| 130 | `skill_id = safe_id(str(item.get("id") or ""))` | **B** | `if not skill_id` DEAD guard; "skill" persisted as candidate `id` |
| 146 | guarded capabilities comprehension | C | guarded |
| 196 | `skill_id = safe_id(os.path.splitext(filename)[0])` | A | skill-id from `.py` filename |
| 211 | `skill_id = safe_id(os.path.basename(dir_path))` | A | skill-id from dir name |
| 263 | `skill_id = safe_id(str(item.get("id") or ""))` | **B** | `if not skill_id` DEAD guard; bogus "skill" candidate keyed |

## core/install_candidate_utils.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 6 | `def safe_id` | — | local def (`"skill"` fallback) |
| 22 | `key = safe_id(str(raw_key or ""))` | **B** | `if not key` DEAD guard |
| 23 | `sid = safe_id(str(skill_id or ""))` | **B** | `if not sid` DEAD guard |
| 40 | `sid = safe_id(str(skill_id or ""))` | **B** | empty skill_id→"skill" in canonical candidate key (identity) |
| 43 | `return safe_id(str(raw_key or sid))` | C | `sid` non-empty at worst "skill"; identity issue is at line 40 |
| 44 | `return safe_id(f"{source}__{sid}")` | C | f-string non-empty; identity issue is at 40 |
| 48 | `sid = safe_id(str(skill_id or ""))` | **B** | `if not sid: return []` DEAD guard |
| 54 | `legacy_key = safe_id(f"{legacy_source_id}__{sid}")` | C | f-string non-empty |
| 68 | `skill_id = safe_id(raw_key)` | **B** | `if not skill_id: return None` DEAD guard |
| 82 | `skill_id = safe_id(str(... or raw_key))` | **B** | `if not skill_id: return None` (line 85) DEAD guard |

## core/interactive_chat.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 84 | `self.project_id = safe_id(os.path.basename(workspace))` | C | workspace basename non-empty |
| 746 | `role_id = safe_id(role) or "agent"` | **B** | `or "agent"` DEAD; empty role→"skill"→`skill.yaml` agent file under wrong identity |

## core/project_task_board.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 268 | `text = safe_id(deliverable)` | C | only used for keyword `in` matching; "skill"/"" both fail to match tokens |
| 278 | `valid_ids = {safe_id(r.get("id") or "")...}` | C | malformed role→"skill"; ledger_role would need to be "skill" to false-match |
| 296 | `role_id = safe_id(role.get("id") or "")` | C | `if bucket in role_id` — "skill" won't contain bucket tokens |
| 299 | `safe_id(roles[0].get("id") or "general_dev")` | C | literal `"general_dev"` fallback |
| 307 | `role_id = safe_id(... or "role")` | C | literal `"role"` fallback; `if not role_id` dead guard (flag) |
| 315/316 | guarded comprehensions | C | guarded |
| 331 | `step_id = safe_id(... or f"step_{index}")` | C | f-string fallback; `if not step_id` dead guard (flag) |
| 443/464 | `safe_id(f"{...}_module_{index}")` | C | f-string always non-empty |
| 494 | `phase = safe_id(... or "build") or "build"` | C | `or "build"` input; outer `or` dead (flag) |
| 495 | `task_id = safe_id(... or f"{module['id']}_{phase}_{index}")` | C | f-string fallback; `if not task_id` dead guard (flag) |
| 505 | `safe_id(raw.get("owner_role") or owner_role)` | C | `owner_role` provably non-empty (from `_pick_owner_role`, which always returns non-empty) |
| 507 | guarded depends_on comprehension | C | guarded |
| 541 | `owner_role = safe_id(raw_module.get("owner_role") or _pick_owner_role(...))` | C | `_pick_owner_role` always non-empty |
| 550 | `module_id = safe_id(... or f"{owner_role}_module_{index}")` | C | f-string fallback; `if not module_id` dead guard (flag) |
| 553 | guarded depends_on comprehension | C | guarded |
| 618 | `"owner_role": safe_id(raw_task.get("owner_role") or module.get("owner_role"))` | **B** | both optional→"skill"; persisted as task owner_role + `role_index` dict key (line 642) |
| 620 | `"phase": safe_id(... or "build") or "build"` | C | `or "build"` input; outer `or` dead (flag) |
| 621 | guarded depends_on comprehension | C | guarded |
| 649 | `"owner_role": safe_id(module.get("owner_role"))` | **B** | optional module owner_role→"skill" persisted as module identity |
| 650 | guarded depends_on comprehension | C | guarded |
| 748 | `dependency = safe_id(dep)` | **B** | `if not dependency: return True` — empty dep should be "satisfied"; "skill" defeats it |
| 755 | `safe_id(task.get("task_id")) == dependency` | **B** | stored side paired with 748; missing task id→"skill"=="skill" |
| 764 | `safe_id(module.get("id")) != dependency` | **B** | stored module id paired with 748 |
| 766 | guarded comprehension | C | guarded |
| 770 | `task_map = {safe_id(t.get("task_id")): t for t in tasks}` | **B** | board task ids as dict keys; missing-id tasks collide into "skill" key |
| 785 | guarded comprehension | C | guarded |
| 803 | `role = safe_id(task.get("owner_role"))` | C | empty→"skill" still caught by `role not in available_roles` → continue; same outcome as "" |
| 808 | `task_key = safe_id(task.get("task_id") or task.get("instruction"))` | **B** | both absent→"skill"; `if task_key in completed` membership false-match |
| 811 | guarded depends_on comprehension | C | guarded |
| 832 | `target_task_id = safe_id(task_id)` | **B** | CALIB #1 — empty task_id→"skill"→`if target_task_id` truthy→instruction/role fallback skipped |
| 833 | `target_instruction = safe_id(instruction)` | C | all callers of `update_project_board_task` pass non-empty instruction |
| 834 | `target_role = safe_id(role)` | C | all callers pass non-empty role |
| 839 | `task_key = safe_id(str(task.get("task_id") or ""))` | **B** | stored side paired with 832 for `task_key==target_task_id` consistency |
| 840 | `instruction_key = safe_id(str(task.get("instruction") or ""))` | C | board instruction is a required field (always populated) |
| 844 | `safe_id(str(task.get("owner_role") or ""))` | C | else-branch only; compared to `target_role` (non-empty C) |
| 892 | `target_task_id = safe_id(task_id)` | **B** | `append_project_board_note` task_id optional; CALIB #1 sibling — empty→"skill"→note lost |
| 893 | `target_instruction = safe_id(instruction)` | **B** | `instruction` param defaults `""` (optional here); `elif target_instruction` truthy guard defeated |
| 894 | `target_role = safe_id(role)` | **B** | `role` param defaults `""` (optional); `not target_role` guard defeated |
| 900 | `task_key = safe_id(str(task.get("task_id") or ""))` | **B** | stored side paired with 892 |
| 901 | `instruction_key = safe_id(str(task.get("instruction") or ""))` | **B** | stored side paired with 893 |
| 906 | `safe_id(str(task.get("owner_role") or ""))` | **B** | stored side paired with 894 |
| 1039 | `role_lookup = {safe_id(role.get("id")): role ...}` | C | role-id dict keys; malformed empty role rare |
| 1043 | `role_lookup.get(safe_id(module.get("owner_role")), {})` | C | result feeds display-only markdown digest line |
| 1103 | `existing_ids = {safe_id(t.get("task_id")) ...}` | C | board task ids always populated; membership target is f-string |
| 1107/1142 | `safe_id(cr_task_id/cv_task_id) not in existing_ids` | C | `cr/cv_task_id` are f-strings always non-empty |

## core/registry_manager.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 62 | `{t for t in safe_id(text).split("_") if t}` | **B** | empty text→"skill" token; defeats `if not need_tokens` empty-guard → spurious scoring |
| 73 | `if safe_id(need) == safe_id(candidate_text)` | **B** | equality; both empty→"skill"=="skill" → false +40 exact-match bonus |
| 94 | `n_item["id"] = safe_id(str(n_item.get("id") or cid))` | C | `cid` (dict key) non-empty fallback |
| 111 | `capability = safe_id(str(raw_value))` | **B** | `if capability` truthy guard defeated; "skill" enters capabilities list |
| 128 | `key = safe_id(str(sid))` | C | `sid` is a registry skill dict key — always populated |
| 165 | `sid = safe_id(str(item.get("id") or cid))` | C | `cid` non-empty fallback |
| 176 | guarded capabilities comprehension | C | guarded |
| 184 | `sid = safe_id(need_id)` | A | skill-id for `_install_skill_file` |
| 353/354 | `[safe_id(str(s)) for s in (... or [literals])]` | C | status-name lists; malformed empty entry→"skill" harmless extra |
| 360 | `explicit_stage = safe_id(str(... or ""))` | **B** | empty→"skill"; `if explicit_stage and explicit_stage != "draft"` → "skill" persisted as lifecycle stage |
| 364 | `stage = safe_id(qg.get("default_stage_on_build","draft"))` | C | literal `"draft"` default |
| 373 | `(lock...).get(safe_id(skill_id), {})` | C | empty→"skill" key absent → `{}`; same as "" |
| 374 | `status = safe_id(str(item.get("status","")))` | C | empty→"skill"; `status in ["active"]` False — same outcome as "" |
| 379 | `sid = safe_id(skill_id)` | A | skill-id for lock |
| 412 | `k = safe_id(str(cap))` | **B** | empty capability→"skill" persisted as `capability_to_skill` mapping key |

## core/manager.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 18 | `agent_id = safe_id(role_text) or "agent"` | C | `role_text` always non-empty (`... or "General Assistant"`); `or "agent"` dead-unreachable |
| 37/45 | `f"{safe_id(role_spec)}.yaml"` | **B** (doubt) | role_spec used as agent-file identity; empty→`skill.yaml` wrong file read/write |
| 76 | `data["name"] = data.get("name") or f"agent_{safe_id(role_spec)}"` | C | display name only, guarded by `data.get("name") or` |
| 99 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded |
| 100 | `[safe_id(s) for s in skill_ids]` | C | `skill_ids` from upstream procurement (real skill ids); skill-id domain |
| 121 | `[safe_id(s) for s in picks]` | C | `picks` are literal skill-id strings |
| 167 | `[safe_id(str(s)) for ... if str(s).strip()]` | C | guarded |

## core/researcher.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 89 | `key = safe_id(str(sid))` | C | `sid` is a registry skill dict key — populated |
| 90 | `caps = [safe_id(str(c)) for c in (meta.get("capabilities") or [])]` | **B** | UNGUARDED; empty capability→"skill" stored in idx + token corpus pollution |
| 100 | `set(t for t in safe_id(need).split("_") if t)` | **B** | empty need→"skill" token defeats `if need_tokens` empty-guard → spurious match |
| 103 | `safe_id(item.get("name",""))` | **B** (doubt) | empty name→"skill" token in match corpus → spurious overlap |
| 110 | `set(t for t in safe_id(need).split("_") if t)` | **B** | same as 100 |
| 111 | `caps = [safe_id(str(c)) for c in (item.get("capabilities") or [])]` | **B** | UNGUARDED; same as 90 |
| 112 | `[safe_id(item.get("id","")), safe_id(item.get("name",""))]` | **B** (doubt) | `name` call: empty→"skill" corpus token; `id` call is non-empty (C) |
| 185 | `need_id = safe_id(raw_need)` | C | `raw_need` guarded `if not raw_need: continue` (line 183) |
| 187 | guarded comprehension | C | guarded |
| 1118 | `_slug = safe_id(task_input)[:40]` | C | `task_input` is the pipeline's primary input — always non-empty |
| 1154/1155 | guarded comprehensions | C | guarded |
| 1328 | guarded comprehension | C | guarded |
| 1417 | `k = safe_id(str(need))` | **B** | LLM suggestion need key; empty→"skill" as `suggestions[k]` mapping key |
| 1418 | `[safe_id(str(c)) for ... if safe_id(str(c)) in idx]` | C | filtered by `in idx` registry membership |
| 1458 | `feedback_skill_id = safe_id(str(entry.get("skill_id") or ""))` | **B** | `if feedback_skill_id` truthy guard defeated; "skill" enters dedup set |
| 1484 | guarded comprehension | C | guarded |

## core/pdca_commands.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 523 | `run_id=f"pdca_do_{safe_id(self.state.project_id)}"` | C | run-id label component; project_id always set in pdca state |

## core/project_pipeline.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 154 | `rid = safe_id(role_id)` | C | `role_id` provably non-empty (callers pass from `_materialize_roles` line 585 `... or "role"`) |
| 237/239 | docstring text | — | not call sites |
| 244 | `evidence_slug = safe_id(task_input)[:40]` | C | `task_input` primary pipeline input — non-empty |
| 540 | `f"{safe_id(role_id)}.yaml"` | C | `role_id` provably non-empty (from `_materialize_roles`) |
| 544/551 | guarded comprehensions | C | guarded |
| 585 | `role_id = safe_id(str(... or "role"))` | C | literal `"role"` fallback; `if not role_id` dead guard (flag) |
| 590 | guarded comprehension | C | guarded |
| 594 | `safe_id(str(module.get("owner_role") or "")) == role_id` | C | empty owner_role→"skill"≠role_id → module excluded; same as "" outcome |
| 774 | `_ev_slug = safe_id(task_input)[:40]` | C | `task_input` primary input — non-empty |

## core/project_mailbox.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 152 | `sender = safe_id(from_role) or "unknown_sender"` | **B** | CALIB #6 — `or "unknown_sender"` DEAD; empty from_role→"skill" sender persisted |
| 153 | `recipient = safe_id(to_role)` | **B** | CALIB #6 — `if not recipient: raise` (line 159) NEVER FIRES; empty to_role→"skill" |
| 154 | `kind = safe_id(message_type)` | C | empty→"skill" still fails `_ALLOWED_MESSAGE_TYPES` membership → raises (same outcome) |
| 156 | `task_key = safe_id(task_id)` | **B** | CALIB #5 — `task_id=""` optional; empty→"skill" persisted as message task scope; `if task_key` truthy |
| 168 | `thread_id = safe_id(f"{task_key or 'general'}_{pair}")` | C | f-string always non-empty |
| 191 | `safe_id(in_reply_to)` | C | guarded by `if in_reply_to:` (line 190) |
| 216 | `recipient = safe_id(role)` | **B** | `read_inbox` filter; empty role→"skill" matches messages whose to_role normalizes to "skill" |
| 217 | `task_key = safe_id(task_id)` | **B** | `task_id=""` optional; `if task_key and ...` truthy guard defeated → wrong task filter |
| 222 | `safe_id(str(message.get("to_role") or ""))` | C | stored to_role always populated (send forces non-falsy recipient) |
| 224 | `safe_id(str(message.get("task_id") or ""))` | **B** | stored side paired with 217 for filter consistency |
| 245 | `target_id = safe_id(message_id)` | **B** | `if not target_id: return False` (line 247) NEVER FIRES; guard-bug |
| 246 | `actor_role = safe_id(role)` | **B** | `role=""` optional; `if actor_role and ...` (258) truthy guard defeated; `actor_role or ...` (262) |
| 256 | `safe_id(str(message.get("message_id") or ""))` | C | stored message_id always set |
| 258 | `safe_id(str(message.get("to_role") or ""))` | C | stored to_role always set |
| 262 | `actor_role or safe_id(str(message.get("to_role") or ""))` | C | the `safe_id(...)` arg here is stored to_role (set); `actor_role` issue is line 246 |
| 276 | `safe_id(role)` | C | inside `if role:` block — non-empty |
| 297 | `safe_id(str(message.get("type") or "message")) or "message"` | C | literal `"message"` input; outer `or "message"` dead (flag) |

## core/skill_registry.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 545 | `skill_id = _safe_id(skill_name) or skill_name.lower().replace(" ","_")` | A | skill-id minting; `or ...` DEAD (flag) but skill-id domain |

## core/skill_spec_synthesizer.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 95 | `skill_id = safe_id(str(intent.get("skill_id") or "skill"))` | C | literal `"skill"` input — redundant but harmless; skill-id domain |
| 97 | `role = safe_id(str(intent.get("role") or ""))` | **B** (doubt) | optional role; empty→"skill" persisted as spec `role` identity |
| 100 | guarded capabilities comprehension | C | guarded |
| 223 | `candidate_id = safe_id(str(... or ""))` | **B** | `if not candidate_id` DEAD guard; empty→"skill"→`resolve_skill_paths("skill")` baseline |
| 224 | `safe_id(skill_id)` (comparison RHS) | C | `skill_id` is the skill being synthesized — always real |

## core/skill_promotion.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 152 | `requested_skill_id = safe_id(skill_id)` | **B** (doubt) | `if requested_skill_id and ...` guard defeated; absent skill_id + real report → false `skill_id_mismatch` raise |
| 153 | `report_skill_id = safe_id(eval_report.skill_id)` | **B** | paired with 152; report skill_id empty→"skill" defeats `if report_skill_id` guard |
| 237 | `(read_skill_lock()...).get(safe_id(skill_id), {})` | C | empty→"skill" key absent → `{}`; same as "" |
| 263 | `normalized = safe_id(stage) or "draft"` | **B** | `or "draft"` DEAD; empty stage→"skill" returned/used as lifecycle stage |

## core/skill_retrieval_engine.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 80 | `candidate_skill_id = safe_id(str(... or ""))` | **B** | when mode="forge" (no candidate) empty→"skill" persisted in ReuseDecision identity |
| 153 | `need_skill_id=safe_id(need_skill_id)` | **B** (doubt) | need_skill_id persisted as ReuseDecision identity; empty→"skill" |
| 187 | `candidate_skill_id = safe_id(str(... or ""))` | **B** | `if not candidate_skill_id` DEAD guard; "skill" in ranked row |
| 201 | `candidate_skill_id == safe_id(str(payload.get("top_candidate") or ""))` | **B** | equality; both empty→"skill"=="skill" → false `verified` boost |
| 233 | `candidate_skill_id = safe_id(str(... or ""))` | **B** | `if candidate_skill_id` truthy guard defeated; "skill" added to candidate_ids |
| 261 | `payload["skill_id"] = safe_id(str(payload.get("skill_id") or candidate_skill_id))` | **B** (doubt) | both empty→"skill" persisted as feedback-summary skill identity |
| 286 | `candidate_skill_id = safe_id(str(payload.get("top_candidate") or ""))` | **B** | `if not candidate_skill_id` DEAD guard; synthetic candidate id "skill" |

## core/skill_eval_harness.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 693 | `safe_id(os.path.basename(os.path.dirname(skill_path)))` | A | skill-id from skill dir path |

## core/skill_creator.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 98 | `def _safe_id` | — | local def — NO fallback (returns `""`) — already safe-optional |
| 230/371/815 | `skill_id = _safe_id(skill_name)` | C | calls the local NO-fallback `_safe_id` — already returns `""` for empty; not the buggy function |

## core/skill_feedback.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 65 | `safe_id(raw_project_id if raw_project_id else "project")` | C | literal `"project"` fallback; input always non-empty |
| 93 | `skill_id=safe_id(skill_id)` | **B** | optional skill_id; empty→"skill" persisted as SkillFeedbackEvent identity + filter match (217) |
| 98 | `lifecycle_stage=safe_id(lifecycle_stage) if lifecycle_stage else ""` | C | outer guard |
| 99 | `source=safe_id(source) if source else ""` | C | outer guard |
| 121 | `"decision_mode": safe_id(decision_mode)` | **B** (doubt) | optional mode label persisted in payload; empty→"skill" |
| 122 | `"candidate_skill_id": safe_id(candidate_skill_id) if candidate_skill_id else ""` | C | outer guard |
| 195 | `"from_stage": safe_id(from_stage)` | **B** (doubt) | optional stage persisted in payload; empty→"skill" |
| 196 | `"to_stage": safe_id(to_stage)` | **B** | optional stage persisted; `to_stage` also flows to `lifecycle_stage` |
| 211 | `skill_filter = safe_id(skill_id) if skill_id else ""` | C | outer guard |
| 212 | `event_filter = safe_id(event_type) if event_type else ""` | C | outer guard |
| 226 | `normalized_skill_id = safe_id(str(raw_skill_id))` | **B** | `if normalized_skill_id` truthy guard defeated; "skill" enters requested_ids + summary key |
| 247 | `normalized_skill_id = safe_id(skill_id)` | **B** | `if not normalized_skill_id` DEAD guard; empty→summarizes phantom "skill" |
| 258 | `status = safe_id(str(event.get("status") or ""))` | C | empty→"skill" matches no status branch; same as "" |
| 260 | `lifecycle_stage = safe_id(str(... or ""))` | **B** | all-empty→"skill"; `if lifecycle_stage` truthy → `current_stage="skill"` persisted |
| 285 | `promoted_stage = safe_id(str(payload.get("to_stage") or ""))` | **B** | `if promoted_stage` truthy guard defeated; `current_stage="skill"` |
| 355 | `"event_type": safe_id(str(... or ""))` | **B** (doubt) | persisted normalized event_type; used in equality filter (218) |
| 356 | `"skill_id": safe_id(str(... or ""))` | **B** | persisted loaded-event skill_id identity; used in filter (216); paired with 93 |
| 358 | `safe_id(...) if payload.get("project_id") else ""` | C | outer guard |
| 361 | `safe_id(...) if payload.get("lifecycle_stage") else ""` | C | outer guard |
| 362 | `safe_id(...) if payload.get("source") else ""` | C | outer guard |

## core/skill_procurer.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 124 | `read_skill_lock()...get(safe_id(skill_name), {})` | C | skill_name required in procurement; "skill"/"" key both absent → `{}` |
| 182 | `skill_id = safe_id(skill_name)` | A | skill-id minting |
| 381 | `skill_id=safe_id(skill_name)` | A | skill-id minting for SkillMetadata |
| 562/586 | `installed_skill_id = safe_id(raw_installed) if raw_installed else ""` | C | outer guard |
| 621 | `source_id = safe_id(str(... or "external")) or "external"` | C | literal `"external"` input; outer `or` dead (flag) |
| 661 | `built_id = safe_id(str(meta.get("id") or skill_name))` | C | `or skill_name` non-empty fallback; result used in log message (display) |
| 698 | `stage = safe_id(str(... or ""))` | **B** | all-empty→"skill"; `if stage and stage != "draft"` → `return "skill"` as build stage |
| 708 | `gated_stage = safe_id(str(... or ""))` | **B** | `if gated_stage` truthy guard defeated; `return "skill"` as stage |
| 718 | `safe_id(str(... or "draft")) or "draft"` | C | literal `"draft"` input; outer `or` dead (flag) |
| 737 | `reference_candidate_id = safe_id(str(... or ""))` | **B** | empty→"skill"; feeds `if reference_candidate_id:` in evaluate_and_promote → bogus baseline |
| 751 | `next_stage = safe_id(str(result.get("next_stage") or current_stage)) or current_stage` | C | `current_stage` non-empty → input non-empty |
| 871 | `"requested_skill_id": safe_id(skill_name)` | C | skill_name required in build context |
| 884 | `return safe_id(str(meta.get("id") or skill_name))` | C | `or skill_name` non-empty fallback |
| 987 | `enhanced_id = safe_id(str(enhanced.get("skill_id") or candidate_id))` | C | `or candidate_id` fallback; skill-id minting domain |

## core/tool_runtime.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 56 | `tool_name = safe_id(f"{module_name}_{func_name}")` | C | f-string; `func_name` always non-empty for a real tool |

## core/work_item_parser.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 133 | `"task_id": safe_id(title)` | **B** (doubt) | whitespace-only title→"skill" persisted as task identity; matched in existing_by_id (224) |
| 154 | `current["task_id"] = safe_id(val)` | C | guarded by `and val` |
| 156 | `current["owner_role"] = safe_id(val)` | C | guarded by `and val` |
| 158 | `current["phase"] = safe_id(val) or "build"` | C | guarded by `and val` |
| 160 | guarded depends_on comprehension | C | guarded |
| 224 | `tid = safe_id(str(task.get("task_id") or ""))` | **B** | `if tid` truthy guard defeated; "skill" used as `existing_by_id` dict key |
| 227 | `title_key = safe_id(str(task.get("title") or task.get("instruction") or ""))` | **B** | `if title_key` guard defeated; "skill" as `existing_by_title` dict key |
| 236 | `pt_title_key = safe_id(_clean(pt.get("title") or ""))` | **B** | empty parsed title→"skill"→false match against existing_by_title["skill"] |
| 256 | `pt_id or safe_id(pt.get("title") or "task")` | C | literal `"task"` fallback |
| 286 | `role = safe_id(str(task.get("owner_role") or ""))` | **B** | `if role` truthy guard defeated; "skill" used as `role_index` dict key |

## extract_phase3.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 37/93 | `"def _boot_safe_id..."` / `lines[i].startswith("def _boot_safe_id(")` | — | string literals (source-code generator text), NOT call sites |

## web/api/run.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 28 | `def _safe_id` | — | local def (`"default"` fallback) |
| 104 | `workspace = str(ROOT_DIR / "projects" / _safe_id(req.project_id))` | C | calls local `_safe_id` (`"default"`, not `"skill"`); FastAPI `req.project_id` is a required body field |

## web/api/agents.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 58 | `def _safe_id` | — | local def (`"agent"` fallback) |
| 73 | `pid = _safe_id(project_id or "")` | C | local `_safe_id` (`"agent"` fallback, not `"skill"`); separate function out of utils scope |
| 90/117/128 | `f"{_safe_id(agent_id)}.yaml"` | C | local `_safe_id`; agent_id is a required path param |
| 286/338/381 | `f"agent not found: {_safe_id(agent_id)}"` | C | local `_safe_id`; error-message display only |

## scripts/project_context_git_sync.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 19 | `def _safe_id` | — | local def — NO fallback (returns `""`) — already safe-optional |
| 100 | `agent_id = _safe_id(args.agent) if args.agent else ""` | C | local NO-fallback `_safe_id` + outer guard — already safe |

## antigravity_link.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 43 | `def safe_id(text, fallback="")` | — | local def — parameterized fallback (already safe-optional capable) |
| 66 | `user_key = safe_id(raw_user, fallback="")` | C | explicit `fallback=""` — already correct (returns "" for empty) |
| 100 | `safe_id(key_base, fallback='entry')` | C | `key_base` from `safe_key(...)` always non-empty; filename component |

## run_factory_cli.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 194 | `os.path.join(projects_root, safe_id(args.project))` | **B** (doubt) | CLI `args.project` used as workspace directory identity; empty→`skill` workspace silently |

## agent_launcher.py

| line | call | cat | rationale |
|------|------|-----|-----------|
| 184 | `sid = safe_id(str(sid_raw))` | **B** | `if not sid` DEAD guard; empty skill entry→"skill" treated as a missing skill |
| 605 | `[safe_id(s) for s in skills]` | **B** | UNGUARDED; empty `missing_skills` entry→"skill" becomes a build target |
