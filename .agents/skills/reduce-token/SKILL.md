---
name: reduce-token
description: Code Knowledge Graph, Session Memory & Token Saver. Use whenever exploring, navigating, diagnosing, or modifying a codebase to avoid reading entire directories or re-reading long chat histories. Queries compact subgraphs, architecture maps, and session memory, saving up to 95% tokens.
---

# ReduceToken: Code Knowledge Graph, Session Memory & Token Saver

Guides the AI agent to navigate codebases and manage context via a lightweight Code Knowledge Graph (`.codegraph/`) and Session Memory, avoiding full-directory scans.

## Core Rules for Token Saving

> [!IMPORTANT]
> **GOLDEN RULE**: Never read full directory trees with `read_file` or run recursive listing commands (`ls -R`, `Get-ChildItem -Recurse`, `tree`). Prefer native MCP tools when available. When using CLI, use `rt` (or `reducetoken`).

---

### Step 1: Check High-Level Architecture (<1,000 tokens)
* **Via MCP (Preferred)**: Call `get_architecture_map()` or `get_session_memory()`.
* **Direct File Read (Zero Shell Overhead)**: Read `.codegraph/architecture_map.md` and `.codegraph/session_context.md` with `read_file`.
* If `.codegraph/` does not exist, run:
  ```bash
  rt init   # (fallback: reducetoken init)
  ```

---

### Step 2: Targeted Subgraph Query (~60 tokens)
Locate specific symbols, functions, classes, or endpoints:
* **Via MCP (Preferred)**: Call `query_code_graph(query="<symbol_or_keyword>")`.
* **Via CLI**: Run `rt query <symbol_or_keyword>` (or `reducetoken query <symbol_or_keyword>`).

*(Delta sync runs automatically in <10ms before returning results. See [dsl_spec.md](references/dsl_spec.md) for output format).*

#### ⚠️ Edge Cases (Query Misses & Ambiguity)
* **If query returns no match** (symbol not indexed or typo):
  - Do NOT revert to directory scans. Query by candidate file/module name (e.g. `query_code_graph(query="auth")`) or check directory clusters in `.codegraph/architecture_map.md`.
* **If query returns multiple matches** (e.g. `login` in multiple modules):
  - Use user intent (API vs UI) and 1-hop callers (`IMPORTED BY`) in the DSL block to pick the right target file.

---

### Step 3: Targeted Line-Bound Reading
* Inspect ONLY the file identified in `TARGET FILE`.
* Use the line indicators (`[Lxx]`) with `read_file(Path, StartLine, EndLine)` to read only the specific target lines (saving 90%+ tokens).
* If 1-hop dependencies or callers are needed, inspect only the files listed in `IMPORTS` or `IMPORTED BY`.
* *(See [sample_workflow.md](examples/sample_workflow.md) for a full end-to-end example).*

---

### Step 4: Autonomous Maintenance & Memory Guard
1. **Zero Tool Overhead**: **Do NOT run `rt update` after code edits**. Delta-sync runs automatically on the next query or git commit.
2. **Save Key Decisions**: When agreeing on architecture or conventions, call `add_memory_decision(topic, content)` or `rt memory add` (or `reducetoken memory add`).
3. **Memory Drift Guard**: If `session_context.md` exceeds 50 lines (>500 tokens), autonomously run `rt compact` (or `reducetoken compact`). (See [memory_guide.md](references/memory_guide.md)).
4. **Path Aliases / Monorepos**: If encountering virtual path aliases (`@/*`, `~/*`, `workspace:*`), inspect `tsconfig.json` or `package.json` workspaces. (See [aliases_and_monorepos.md](references/aliases_and_monorepos.md)).
