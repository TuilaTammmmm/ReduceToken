# Architecture Map & Dependency Network
> **AI Token-Saving Notice**: This repository is indexed by ReduceToken. Do NOT scan the full folder. Consult this map or run `rt query <symbol>` (or `reducetoken query`) to find exact code paths.

## 1. Quick Stats
- **Indexed Files**: 40
- **Indexed Symbols**: 123
- **Entry Points**: reducetoken/cli.py
- **Core Modules**: `reducetoken/parsers/__init__.py` (6 refs), `reducetoken/graph.py` (4 refs), `reducetoken/cache.py` (3 refs), `reducetoken/generator.py` (3 refs), `reducetoken/parsers/python_parser.py` (3 refs), `reducetoken/parsers/js_ts_parser.py` (3 refs), `reducetoken/parsers/generic_parser.py` (3 refs), `reducetoken/scanner.py` (2 refs)

## 2. Module Directory Structure
### `(root)` (9 files)
- `.gitattributes`
- `setup.py`
- `.cursorrules`
- `.gitignore`
- `AGENTS.md`
- `CLAUDE.md`
- `GEMINI.md`
- `LICENSE`
- `README.md`
### `.agents` (6 files)
- `.agents/rules/token-saver.md`
- `.agents/skills/reduce-token/examples/sample_workflow.md`
- `.agents/skills/reduce-token/references/aliases_and_monorepos.md`
- `.agents/skills/reduce-token/references/dsl_spec.md`
- `.agents/skills/reduce-token/references/memory_guide.md`
- `.agents/skills/reduce-token/SKILL.md`
### `.github` (1 files)
- `.github/copilot-instructions.md`
### `plugins` (8 files)
- `plugins/reduce-token/mcp_config.json`
- `plugins/reduce-token/plugin.json`
- `plugins/reduce-token/rules/AGENTS.md`
- `plugins/reduce-token/skills/reduce-token/examples/sample_workflow.md`
- `plugins/reduce-token/skills/reduce-token/references/aliases_and_monorepos.md`
- `plugins/reduce-token/skills/reduce-token/references/dsl_spec.md`
- `plugins/reduce-token/skills/reduce-token/references/memory_guide.md`
- `plugins/reduce-token/skills/reduce-token/SKILL.md`
### `reducetoken` (13 files)
- `reducetoken/__init__.py` — ReduceToken - Code Knowledge Graph and Token Saver
- `reducetoken/agent_adapters.py` — defines: `AgentAdapterManager, GlobalAdapterManager, __init__, is_global_active`
- `reducetoken/cache.py` — defines: `CacheManager, calculate_sha256, analysis_to_dict, dict_to_analysis`
- `reducetoken/cli.py` — defines: `run_pipeline, install_git_hook, cmd_init, cmd_update`
- `reducetoken/generator.py` — defines: `Generator, __init__, generate_all, _get_top_symbols`
- `reducetoken/graph.py` — defines: `CodeGraph, __init__, _load_path_aliases, add_analysis`
- `reducetoken/mcp_server.py` — defines: `McpServer, __init__, _ensure_graph_loaded, get_architecture_map`
- `reducetoken/memory.py` — defines: `SessionMemoryManager, __init__, load, save`
- `reducetoken/parsers/__init__.py` — defines: `SymbolInfo, ImportInfo, FileAnalysis`
- `reducetoken/parsers/generic_parser.py` — defines: `parse_generic_file`
- *(+3 more files)*
### `tests` (3 files)
- `tests/test_adapters.py` — defines: `TestAgentAdapters, test_clean_mode_no_files, test_cursor_modern_encapsulation, test_agents_standard_hidden_encapsulation`
- `tests/test_graph.py` — defines: `TestGraphAndCache, test_graph_resolution_and_query, test_cache_incremental, test_path_alias_resolution`
- `tests/test_parsers.py` — defines: `TestParsers, test_python_parser, test_js_ts_parser, test_unicode_vietnamese`

## 3. How to Query
- Find where a symbol/function is: `rt query <symbol_name>` (or `reducetoken query`)
- Find callers/dependencies of a file: `rt query <file_path>`
- Force refresh graph if needed: `rt update`
