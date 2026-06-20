# AF Source Knowledge Graph Design

## Purpose

AF already has three related capabilities:

- LLM Wiki/Obsidian Markdown generation
- project symbol indexing for Python/C#
- memory-system KnowledgeGraph storage

This document defines how to connect those pieces into a source-code knowledge graph for Unity/C#/Python projects.

The target is not only to generate Markdown. The target is to build a reusable graph of the source itself, then use that graph for LLM Wiki, Obsidian, and request-specific analysis outputs.

Risk reports, dead-code analysis, performance reports, and harness-driven project analysis are optional consumers of the graph. They must be generated only when the user explicitly asks for that kind of analysis.

## Current Implementation

### LLM Wiki

Current flow:

```text
source files
  -> scripts/codebase_symbols.py
  -> scripts/build_llm_wiki.py
  -> docs/generated/llm_wiki/*.md
```

Relevant files:

- `scripts/codebase_symbols.py`
- `scripts/build_llm_wiki.py`
- `agent_launcher.py`

Current behavior:

- `af project symbols <path>` creates a symbol index.
- `af project wiki <path>` creates a Markdown wiki.
- Python symbols are extracted with standard `ast`.
- C# symbols are extracted with conservative declaration patterns.
- The output is currently a flat file-to-symbol view: classes and functions/methods.

This is useful, but it is not yet a full source knowledge graph.

### Obsidian

Current Obsidian support is Markdown-link based.

```text
docs/generated/llm_wiki/*.md
  -> [[links]]
  -> Obsidian graph view
```

Obsidian is a graph viewer/editor for Markdown links. It is not the source graph engine itself.

Therefore, Obsidian should consume generated graph-derived Markdown, not be treated as the graph store.

### KnowledgeGraphAdapter

Current flow:

```text
core/memory_system/models.py
  -> KnowledgeNode / KnowledgeEdge
  -> core/memory_system/adapters/knowledge_graph.py
  -> .system_generated/cache/knowledge_graph.json
```

Relevant files:

- `core/memory_system/models.py`
- `core/memory_system/adapters/knowledge_graph.py`
- `core/memory_system/graph_query.py`
- `core/memory_system/facade.py`

Current behavior:

- Stores nodes and edges as JSON.
- Supports node/edge CRUD.
- Supports traversal through `GraphQuery`.
- Integrated into memory setup in `core/agent_runner.py` and `core/project_pipeline.py`.

Current limitation:

- `NodeType` is centered on memory concepts: `problem`, `cause`, `solution`, `fact`, `pattern`.
- `EdgeType` is centered on memory relationships: `caused_by`, `solved_by`, `related_to`, `depends_on`, `evolved_from`.
- It does not currently model source concepts such as files, namespaces, classes, methods, inheritance, calls, or Unity event methods.

## Design Decision

Reuse `KnowledgeGraphAdapter` as the graph storage layer.

Add a new source graph builder that converts source code into `KnowledgeNode` and `KnowledgeEdge` records.

Target flow:

```text
Unity/C#/Python source
  -> SourceGraphBuilder
  -> KnowledgeNode / KnowledgeEdge
  -> KnowledgeGraphAdapter
  -> .af_index/source_graph.json
  -> default output: LLM Wiki / Obsidian
  -> optional output: request-specific reports
```

This keeps the existing memory graph implementation useful while avoiding pollution of the existing memory graph file.

## Proposed Architecture

### Storage

Extend `KnowledgeGraphAdapter` to accept an optional graph file path.

Proposed interface:

```python
KnowledgeGraphAdapter(
    workspace=".",
    graph_file=".system_generated/cache/knowledge_graph.json",
)
```

Source graph usage:

```python
KnowledgeGraphAdapter(
    workspace=project_root,
    graph_file=".af_index/source_graph.json",
)
```

Reason:

- Existing memory graph remains unchanged.
- Source graph is project-local and portable.
- LLM Wiki can read the same deterministic graph output.
- Optional reports can read the graph when the user explicitly asks for risk, dead-code, performance, or other project analysis.
- AF must not generate risk/dead-code/performance/bottleneck reports as part of the default graph/wiki workflow.

### Source Graph Builder

Add a new module:

```text
scripts/source_graph.py
```

Responsibilities:

- Walk a target project directory.
- Parse supported source files.
- Produce source graph nodes and edges.
- Persist the graph through `KnowledgeGraphAdapter`.
- Optionally emit plain JSON for tools that should not import `core`.

Initial public functions:

```python
def collect_source_graph(directory: str) -> SourceGraph:
    ...

def write_source_graph(directory: str, out_file: str) -> dict:
    ...

def build(directory: str) -> str:
    ...
```

`SourceGraph` can initially be a small dataclass or typed dict containing:

```python
{
    "nodes": [...],
    "edges": [...],
}
```

The first implementation should avoid complex language-server dependencies. It should be deterministic and read-only.

### Model Extension

Extend `NodeType`:

```text
file
namespace
type
method
field
property
feature
```

Extend `EdgeType`:

```text
contains
declares
inherits
implements
calls
references
uses
belongs_to_feature
```

Alternative considered:

- Store all source nodes as `NodeType.FACT` and all source edges as `EdgeType.RELATED_TO`, with detailed metadata.

Decision:

- Prefer enum extension.
- It keeps graph queries simple and avoids hiding important semantics in metadata.
- Existing memory graph values remain backward compatible.

### Node IDs

Node IDs must be stable across runs.

Recommended format:

```text
file:<relpath>
namespace:<name>
type:<relpath>:<qualified_name>
method:<relpath>:<qualified_type>.<method_name>
field:<relpath>:<qualified_type>.<field_name>
property:<relpath>:<qualified_type>.<property_name>
feature:<feature_name>
```

Examples:

```text
file:Player/PlayerController.cs
type:Player/PlayerController.cs:Game.PlayerController
method:Player/PlayerController.cs:Game.PlayerController.Update
feature:Player Movement
```

### Metadata

Each source graph node should keep enough metadata for Markdown generation and optional request-specific reports.

Recommended node metadata:

```json
{
  "language": "csharp",
  "relpath": "Player/PlayerController.cs",
  "line": 42,
  "qualified_name": "Game.PlayerController",
  "kind": "class",
  "unity_kind": "MonoBehaviour"
}
```

Recommended edge metadata:

```json
{
  "language": "csharp",
  "relpath": "Player/PlayerController.cs",
  "line": 58,
  "confidence": "declaration"
}
```

Confidence values:

- `ast`: parsed from a language AST
- `declaration`: parsed from declaration-level patterns
- `heuristic`: inferred from naming or call patterns
- `llm`: inferred by an LLM in a later phase

## Language Coverage

### Phase 1: Deterministic Symbol Graph

Python:

- files
- classes
- functions
- methods
- imports
- `contains`
- `declares`

C#:

- files
- namespaces
- class/interface/struct/enum/record
- methods
- inheritance list
- `contains`
- `declares`
- `inherits`
- `implements`

Unity:

- `MonoBehaviour`
- `ScriptableObject`
- Unity message methods:
  - `Awake`
  - `Start`
  - `Update`
  - `FixedUpdate`
  - `LateUpdate`
  - `OnEnable`
  - `OnDisable`
  - `OnDestroy`
  - `OnTriggerEnter`
  - `OnTriggerExit`
  - `OnCollisionEnter`
  - `OnCollisionExit`

Unity message methods should get metadata:

```json
{
  "unity_message": true,
  "unity_message_name": "Update"
}
```

### Phase 2: Call Graph

Python:

- Use `ast.Call`.
- Resolve simple same-file calls.
- Resolve `self.method()` calls within a class.

C#:

- Start with conservative method-call pattern extraction.
- Resolve calls within the same type first.
- Resolve obvious `Instance.Method()` only when the target type is known.

Do not overclaim call accuracy in Phase 2. Store confidence as `heuristic` unless the resolver is deterministic.

### Phase 3: Unity/Project Feature Graph

Feature nodes can be generated from:

- folder names
- namespaces
- class name clusters
- Unity component conventions
- optional user-provided feature map

Example:

```text
feature:Player Movement
  <- belongs_to_feature
method:PlayerController.Move
type:PlayerController
```

Feature grouping should be best-effort at first. It should not block graph creation.

## CLI Design

Add:

```text
af project graph <path> [--out DIR]
```

Default output:

```text
<path>/.af_index/source_graph.json
```

Expected behavior:

```text
af project graph D:\Client\Assets\SMGameStation\Scripts
```

Outputs:

```text
D:\Client\Assets\SMGameStation\Scripts\.af_index\source_graph.json
```

Then extend:

```text
af project wiki <path> --from-graph
```

Default behavior can remain backward compatible:

- If `.af_index/source_graph.json` exists, Wiki can use it.
- If it does not exist, Wiki falls back to `codebase_symbols.collect_symbols()`.

## LLM Wiki / Obsidian Output

Current wiki pages:

- `index.md`
- `architecture.md`
- `symbols.md`
- `source_refs.md`

Graph-backed pages to add:

```text
graph/index.md
graph/files/*.md
graph/types/*.md
graph/methods/*.md
graph/features/*.md
```

Example type page:

```markdown
# PlayerController

Type: class  
File: [[graph/files/PlayerController.cs]]

## Methods

- [[graph/methods/PlayerController.Awake]]
- [[graph/methods/PlayerController.Update]]
- [[graph/methods/PlayerController.Move]]

## Relations

- inherits -> [[graph/types/MonoBehaviour]]
- declares -> [[graph/methods/PlayerController.Update]]
- belongs_to_feature -> [[graph/features/Player Movement]]
```

This makes Obsidian useful for exploring the source graph without making Obsidian the graph database.

## Optional Reports

Report generation should be a separate consumer of the graph, not part of the default graph/wiki workflow.

Rule:

```text
Do not generate risk/dead-code/performance/bottleneck reports unless the user explicitly asks for them.
```

Default outputs:

```text
.af_index/source_graph.json
docs/generated/llm_wiki/*.md
```

Request-based outputs:

```text
.af_index/reports/source_risks.md
.af_index/reports/dead_code_candidates.md
.af_index/reports/hotspots.md
```

Examples:

```text
"이 프로젝트 소스 지식그래프 만들어줘"
  -> build source graph
  -> build LLM Wiki / Obsidian pages
  -> do not generate risk/dead-code reports

"이 Unity 프로젝트 병목, 위험, 데드코드까지 분석해줘"
  -> build source graph
  -> build LLM Wiki / Obsidian pages
  -> generate requested reports
```

Add report generation later as an opt-in command.

Proposed command:

```text
af project analyze <path> [--graph .af_index/source_graph.json]
```

Initial opt-in reports:

```text
.af_index/reports/source_risks.md
.af_index/reports/dead_code_candidates.md
.af_index/reports/hotspots.md
```

Initial risk rules:

- Unity `Update`/`FixedUpdate` methods with many calls.
- `FindObjectOfType` inside Unity lifecycle methods.
- repeated `GetComponent` inside `Update`.
- empty `catch`.
- `async void`.
- high fan-out method.
- high fan-in dependency hub.
- class with too many methods or fields.

Initial dead-code candidate rules:

- private method with no incoming `calls` edge.
- non-Unity-message method with no incoming `calls` edge.
- type with no incoming reference edge and no Unity/serialization metadata.

Dead-code findings must be labeled as candidates, not final proof, until the call graph is precise enough.

## Implementation Plan

### Step 1: Storage Reuse

Change:

- `core/memory_system/adapters/knowledge_graph.py`
- `core/memory_system/models.py`

Work:

- Add optional `graph_file` parameter to `KnowledgeGraphAdapter`.
- Extend `NodeType`.
- Extend `EdgeType`.
- Add tests for legacy default path and custom source graph path.

Verification:

```text
python -m pytest tests/test_memory_system*.py
```

### Step 2: Source Graph Builder

Add:

- `scripts/source_graph.py`
- `tests/test_source_graph.py`

Work:

- Build file/type/method graph for Python and C#.
- Add `contains`, `declares`, `inherits`, `implements`.
- Write `.af_index/source_graph.json`.

Verification:

```text
python -m pytest tests/test_source_graph.py
```

### Step 3: CLI Wiring

Change:

- `agent_launcher.py`
- `af.spec`

Work:

- Add `af project graph <path>`.
- Print output path and node/edge counts.
- Add PyInstaller hidden import if needed.

Verification:

```text
python -m pytest tests/test_af_project_graph.py
```

### Step 4: Wiki Graph Pages

Change:

- `scripts/build_llm_wiki.py`

Work:

- Detect `.af_index/source_graph.json`.
- Generate graph-backed pages.
- Keep current symbols fallback.

Verification:

```text
python -m pytest tests/test_build_llm_wiki.py
```

### Step 5: Optional Analysis Reports

Add:

- `scripts/source_graph_analyzer.py`
- `tests/test_source_graph_analyzer.py`

Work:

- Generate risk and dead-code candidate reports from graph edges only when explicitly requested by the user.
- Keep all findings evidence-backed by file, symbol, line, node ID, and edge ID.

Verification:

```text
python -m pytest tests/test_source_graph_analyzer.py
```

## Non-Goals

The first version should not try to be a full compiler.

Out of scope for Phase 1:

- complete C# semantic binding
- cross-assembly Unity package resolution
- full Unreal C++ support
- LLM-inferred architecture claims without source evidence
- deleting or rewriting target project source

## Future Extensions

Possible later upgrades:

- Roslyn-based C# parser for precise semantic references.
- tree-sitter fallback for multiple languages.
- Unity `.meta` and prefab/scene reference graph.
- Unreal C++/Blueprint graph adapter.
- LLM feature clustering from graph neighborhoods.
- graph diff between commits.
- harness run traces linked back to source graph nodes.

## Summary

AF should reuse the existing `KnowledgeGraphAdapter` as the graph storage layer.

The missing component is a source graph builder:

```text
source code
  -> SourceGraphBuilder
  -> KnowledgeGraphAdapter
  -> source_graph.json
  -> default: LLM Wiki / Obsidian
  -> optional: request-specific reports
```

This preserves the current LLM Wiki and memory system while turning them into consumers of a real source-code knowledge graph. Reports remain opt-in consumers and must not be generated unless the user's request asks for them.
