import argparse
import sys
import time
from pathlib import Path

from reducetoken.scanner import FileScanner
from reducetoken.cache import CacheManager
from reducetoken.graph import CodeGraph
from reducetoken.generator import Generator
from reducetoken.agent_adapters import AgentAdapterManager
from reducetoken.memory import SessionMemoryManager
from reducetoken.parsers.python_parser import parse_python_file
from reducetoken.parsers.js_ts_parser import parse_js_ts_file
from reducetoken.parsers.generic_parser import parse_generic_file


def run_pipeline(root_dir: Path, force: bool = False, verbose: bool = False) -> CodeGraph:
    start_time = time.perf_counter()
    scanner = FileScanner(root_dir)
    files = scanner.scan()

    cache_file = root_dir / ".codegraph" / "cache.json"
    cache_manager = CacheManager(cache_file)
    git_switched = cache_manager.check_and_update_git_head(root_dir)
    if git_switched and verbose:
        print("[Git Branch / Commit Switch Detected] Auto-synchronizing cache for new branch state...")

    graph = CodeGraph(root_dir)

    parsed_count = 0
    cached_count = 0
    valid_paths = set()

    for f_info in files:
        rel = f_info["path"]
        valid_paths.add(rel)
        full = Path(f_info["full_path"])

        analysis = None
        if not force:
            analysis = cache_manager.get_analysis(rel)

        if force or not analysis or not cache_manager.is_cached_and_valid(rel, full):
            try:
                code = full.read_text(encoding="utf-8", errors="ignore")
                lang = f_info["lang"]
                if lang == "python":
                    analysis = parse_python_file(rel, code)
                elif lang in ("javascript", "typescript"):
                    analysis = parse_js_ts_file(rel, code, language=lang)
                else:
                    analysis = parse_generic_file(rel, code, language=lang)
                cache_manager.update_entry(rel, full, analysis)
                parsed_count += 1
            except Exception as e:
                if verbose:
                    print(f"Error parsing {rel}: {e}", file=sys.stderr)
                continue
        else:
            cached_count += 1

        if analysis:
            graph.add_analysis(rel, analysis)

    cache_manager.remove_missing(valid_paths)
    cache_manager.save()
    graph.build()

    generator = Generator(root_dir, graph)
    generator.generate_all()

    elapsed = (time.perf_counter() - start_time) * 1000
    if verbose:
        print(f"ReduceToken Sync: {parsed_count} parsed, {cached_count} from cache in {elapsed:.1f}ms")

    return graph


def install_git_hook(root_dir: Path) -> bool:
    hook_dir = root_dir / ".git" / "hooks"
    if hook_dir.is_dir():
        hook_file = hook_dir / "post-commit"
        hook_content = (
            "#!/bin/sh\n"
            "# Auto-sync ReduceToken Code Graph\n"
            "reducetoken update > /dev/null 2>&1 &\n"
        )
        try:
            hook_file.write_text(hook_content, encoding="utf-8")
            return True
        except Exception:
            return False
    return False


def cmd_init(args):
    root_dir = Path(args.dir).resolve()
    print(f"Initializing ReduceToken in: {root_dir}")
    graph = run_pipeline(root_dir, force=args.force, verbose=True)

    # Setup agent rules
    adapters = AgentAdapterManager(root_dir)
    adapters.setup_all()

    # Initialize memory context
    mem = SessionMemoryManager(root_dir)
    mem.export_markdown()

    # Automatically install git hook if .git exists (Zero manual setup)
    if install_git_hook(root_dir):
        print("  - Git post-commit hook auto-installed (Zero-effort background sync)")

    print("Generated AI rule files:")
    print("  - .github/copilot-instructions.md (GitHub Copilot)")
    print("  - .cursorrules (Cursor IDE)")
    print("  - CLAUDE.md (Claude Code)")
    print("  - AGENTS.md & GEMINI.md (Antigravity & OpenCode)")
    print("Architecture map created at: .codegraph/architecture_map.md")
    print("Session context memory at: .codegraph/session_context.md")
    print("Initialization complete! 100% automated — your AI now saves up to 95% tokens.")


def cmd_update(args):
    root_dir = Path(args.dir).resolve()
    run_pipeline(root_dir, force=False, verbose=True)


def cmd_query(args):
    root_dir = Path(args.dir).resolve()
    # Fast delta sync first (<10ms)
    graph = run_pipeline(root_dir, force=False, verbose=False)
    res = graph.query(args.query)
    dsl_output = Generator.format_agent_dsl(res)
    print(dsl_output)


def cmd_overview(args):
    root_dir = Path(args.dir).resolve()
    arch_file = root_dir / ".codegraph" / "architecture_map.md"
    if not arch_file.is_file():
        run_pipeline(root_dir, force=False, verbose=False)
    if arch_file.is_file():
        print(arch_file.read_text(encoding="utf-8"))


def cmd_compact(args):
    root_dir = Path(args.dir).resolve()
    mem = SessionMemoryManager(root_dir)
    summary_path = mem.compact()
    print(f"Compact session context updated at: {summary_path}")
    print(mem.get_compact_summary())


def cmd_memory(args):
    root_dir = Path(args.dir).resolve()
    mem = SessionMemoryManager(root_dir)
    if args.action == "add":
        topic = args.topic
        content = args.content or ""
        mem.add_decision(topic, content)
        print(f"Added decision '{topic}' to project memory.")
    elif args.action == "conv":
        mem.add_convention(args.topic)
        print(f"Added convention to project memory.")
    elif args.action == "show":
        print(mem.get_compact_summary())


def cmd_git_hook(args):
    root_dir = Path(args.dir).resolve()
    hook_dir = root_dir / ".git" / "hooks"
    if not hook_dir.is_dir():
        print("Error: .git/hooks directory not found.", file=sys.stderr)
        sys.exit(1)

    hook_file = hook_dir / "post-commit"
    hook_content = (
        "#!/bin/sh\n"
        "# Auto-sync ReduceToken Code Graph\n"
        "reducetoken update > /dev/null 2>&1 &\n"
    )
    hook_file.write_text(hook_content, encoding="utf-8")
    print(f"Installed Git post-commit hook at: {hook_file}")


def cmd_install(args):
    from reducetoken.agent_adapters import GlobalAdapterManager
    manager = GlobalAdapterManager()

    if getattr(args, "global_plugin", False):
        print("--> Installing ReduceToken globally across all major AI Coding Agents...")
        results = manager.setup_all_global()
        for agent, path in results.items():
            print(f"  [OK] {agent:35}: {path}")
        print("\nGlobal installation complete! All supported AI agents will now auto-discover ReduceToken.")
        return

    # Interactive Selector
    envs = manager.detect_environments()
    print("""
===================================================================
      ReduceToken - AI Coding Agent Setup & Installer
===================================================================
""")
    print("Detected AI environments on your system:")
    keys = list(envs.keys())
    for idx, key in enumerate(keys, 1):
        info = envs[key]
        status = "[DETECTED]" if info["detected"] else "[Available]"
        print(f"  [{idx}] {info['name']:38} {status}")
    print(f"  [{len(keys) + 1}] Current Project Directory Only (.codegraph/)  [Local]")
    print("  -------------------------------------------------------------")
    print("  [A] Install for ALL agents (Recommended)")
    print("  [Q] Cancel\n")

    try:
        raw_choice = input("Select targets (e.g. 'A' for all, or '1, 2'): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return

    if not raw_choice or raw_choice.upper() == "A":
        print("\n--> Installing globally for ALL agents...")
        results = manager.setup_all_global()
        for agent, path in results.items():
            print(f"  [OK] {agent:35}: {path}")
        print("\nSetup complete!")
        return
    elif raw_choice.upper() == "Q":
        print("Aborted.")
        return

    selected_indices = set()
    for token in raw_choice.replace(",", " ").split():
        if token.isdigit():
            selected_indices.add(int(token))

    if not selected_indices:
        print("No valid option selected. Aborted.")
        return

    for idx in sorted(selected_indices):
        if 1 <= idx <= len(keys):
            key = keys[idx - 1]
            if key == "gemini":
                path = manager.setup_gemini()
                print(f"  [OK] Google Antigravity & Gemini CLI : {path}")
            elif key == "cursor":
                path = manager.setup_cursor()
                print(f"  [OK] Cursor IDE (Global MCP)         : {path}")
            elif key == "claude":
                path = manager.setup_claude()
                print(f"  [OK] Claude Code                     : {path}")
            elif key == "opencode":
                path = manager.setup_opencode()
                print(f"  [OK] OpenCode                        : {path}")
            elif key == "agents":
                path = manager.setup_agents_standard()
                print(f"  [OK] Agent Skills Standard (Codex)   : {path}")
        elif idx == len(keys) + 1:
            cmd_init(args)

    print("\nSetup complete for selected target(s)!")


def main():
    parser = argparse.ArgumentParser(
        prog="reducetoken",
        description="ReduceToken - Code Knowledge Graph and Token Saver for AI Agents"
    )
    parser.add_argument("--dir", "-d", default=".", help="Root directory of the repository (default: current dir)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # init
    p_init = subparsers.add_parser("init", help="Scan repository, build graph, and setup AI instructions")
    p_init.add_argument("--force", "-f", action="store_true", help="Force reparse all files ignoring cache")

    # update
    subparsers.add_parser("update", help="Incrementally update graph for changed files")

    # query
    p_query = subparsers.add_parser("query", help="Query graph for a symbol, function, class, or file")
    p_query.add_argument("query", help="Symbol or keyword to search")

    # overview
    subparsers.add_parser("overview", help="Print the high-level architecture map")

    # compact
    subparsers.add_parser("compact", help="Update and print the compact project session context")

    # memory
    p_mem = subparsers.add_parser("memory", help="Manage long-term project memory & decisions")
    p_mem.add_argument("action", choices=["add", "conv", "show"], help="Memory action")
    p_mem.add_argument("topic", help="Decision topic or convention description")
    p_mem.add_argument("content", nargs="?", default="", help="Detailed decision content (for add)")

    # mcp
    subparsers.add_parser("mcp", help="Run as Model Context Protocol (MCP) server")

    # git-hook
    subparsers.add_parser("git-hook", help="Install Git post-commit hook for auto-sync")

    # install
    p_inst = subparsers.add_parser("install", help="Install global Antigravity plugin or local rules")
    p_inst.add_argument("--global", "-g", dest="global_plugin", action="store_true", help="Install global Antigravity plugin to ~/.gemini/config/plugins")
    p_inst.add_argument("--force", "-f", action="store_true", help="Force reparse all files ignoring cache (for local init)")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "query":
        cmd_query(args)
    elif args.command == "overview":
        cmd_overview(args)
    elif args.command == "compact":
        cmd_compact(args)
    elif args.command == "memory":
        cmd_memory(args)
    elif args.command == "mcp":
        from reducetoken.mcp_server import McpServer
        server = McpServer(Path(args.dir).resolve())
        server.run_stdio()
    elif args.command == "git-hook":
        cmd_git_hook(args)


if __name__ == "__main__":
    main()
