# Architecture Map & Dependency Network
> **AI Token-Saving Notice**: This repository is indexed by ReduceToken. Do NOT scan the full folder. Consult this map or run `rt query <symbol>` (or `reducetoken query`) to find exact code paths.

## 1. Quick Stats
- **Indexed Files**: 42
- **Indexed Symbols**: 173
- **Entry Points**: reducetoken/cli.py

## 2. Critical God Nodes & Architectural Chokepoints
> **Blast-Radius Alert**: Modifying these central nodes affects many downstream modules.

- `reducetoken/graph.py` — **Foundational Core** (In: 8 callers, Out: 1 deps)
- `reducetoken/parsers/__init__.py` — **Foundational Core** (In: 8 callers, Out: 0 deps)
- `reducetoken/cli.py` — **Central Orchestrator** (In: 3 callers, Out: 12 deps)
- `reducetoken/web_visualizer.py` — **Foundational Core** (In: 4 callers, Out: 3 deps)
- `reducetoken/generator.py` — **Foundational Core** (In: 4 callers, Out: 2 deps)
- `reducetoken/tui.py` — **Central Orchestrator** (In: 2 callers, Out: 6 deps)

## 3. Module Directory Structure
### `(root)` (6 files)
- `.gitattributes`
- `setup.py`
- `.gitignore`
- `LICENSE`
- `README.md`
- `README_VI.md`
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
### `reducetoken` (15 files)
- `reducetoken/__init__.py` — ReduceToken - Code Knowledge Graph and Token Saver
- `reducetoken/agent_adapters.py` — defines: `AgentAdapterManager, GlobalAdapterManager, __init__, is_global_active`
- `reducetoken/cache.py` — defines: `CacheManager, calculate_sha256, analysis_to_dict, dict_to_analysis`
- `reducetoken/cli.py` — defines: `FakeHelpArgs, run_pipeline, install_git_hook, cmd_init`
- `reducetoken/generator.py` — defines: `Generator, __init__, generate_all, _get_top_symbols`
- `reducetoken/graph.py` — defines: `CodeGraph, __init__, _load_path_aliases, add_analysis`
- `reducetoken/mcp_server.py` — defines: `McpServer, __init__, _ensure_graph_loaded, get_architecture_map`
- `reducetoken/memory.py` — defines: `SessionMemoryManager, __init__, load, save`
- `reducetoken/parsers/__init__.py` — defines: `SymbolInfo, ImportInfo, FileAnalysis`
- `reducetoken/parsers/generic_parser.py` — defines: `parse_generic_file`
- `reducetoken/parsers/js_ts_parser.py` — defines: `clean_args, parse_js_ts_file`
- `reducetoken/parsers/python_parser.py` — defines: `PythonAstVisitor, __init__, visit_Module, visit_Import`
- `reducetoken/scanner.py` — defines: `FileScanner, __init__, _load_ignore_files, _parse_ignore_file`
- `reducetoken/tui.py` — defines: `Colors, GraphVisualizer, TerminalUI, __init__`
- `reducetoken/web_visualizer.py` — defines: `generate_web_graph_html, find_chrome_binary, launch_browser, open_web_graph`
### `tests` (6 files)
- `tests/test_adapters.py` — defines: `TestAgentAdapters, test_clean_mode_no_files, test_cursor_modern_encapsulation, test_agents_standard_hidden_encapsulation`
- `tests/test_cli.py` — defines: `TestCliCommands, test_cli_query_and_graph`
- `tests/test_graph.py` — defines: `TestGraphAndCache, test_graph_resolution_and_query, test_cache_incremental, test_path_alias_resolution`
- `tests/test_parsers.py` — defines: `TestParsers, test_python_parser, test_js_ts_parser, test_unicode_vietnamese`
- `tests/test_tui.py` — defines: `TestTuiAndVisualizer, test_draw_subgraph, test_draw_dependency_tree, test_draw_architecture_and_doctor`
- `tests/test_web_visualizer.py` — defines: `TestWebVisualizerAndGodNodes, test_god_nodes_calculation, test_generate_web_graph_html`

## 4. How AI Agents Query & Fast Read (Token Saving Guide)
To avoid reading full multi-hundred line files and save up to 95% tokens:
1. **Locate Target**: Run `rt query <symbol_or_keyword>` (or MCP `query_code_graph`).
   - Returns `TARGET FILE: path/to/file.py` and exact line numbers (e.g. `[L42]`).
2. **Targeted Line Read**: Call `read_file(Path='path/to/file.py', StartLine=35, EndLine=70)` to read only the target function.
   - **NEVER** read the entire file if you only need one class or method.
3. **Inspect Callers & Deps**: Inspect only the 1-hop files listed in `IMPORTS` or `IMPORTED BY`.
4. **Open Visual Web Graph**: Run `rt web` to explore the complete dependency network in browser.
