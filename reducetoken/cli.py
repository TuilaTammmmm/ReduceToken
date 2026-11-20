import argparse
import subprocess
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
            with open(hook_file, "w", newline="\n", encoding="utf-8") as f:
                f.write(hook_content)
            return True
        except Exception:
            return False
    return False


def cmd_init(args):
    root_dir = Path(args.dir).resolve()
    print(f"Initializing ReduceToken in: {root_dir}")
    graph = run_pipeline(root_dir, force=args.force, verbose=True)

    # Initialize memory context
    mem = SessionMemoryManager(root_dir)
    mem.export_markdown()

    # Automatically install git hook if .git exists (Zero manual setup)
    if install_git_hook(root_dir):
        print("  - Git post-commit hook auto-installed (Zero-effort background sync)")

    # Setup agent rules with clean encapsulation
    adapters = AgentAdapterManager(root_dir)
    agent_target = "clean" if getattr(args, "clean", False) else getattr(args, "agent", "auto")
    root_rules = getattr(args, "root_rules", False)

    created_rules = []
    if agent_target in ("clean", "none"):
        print("  - Clean mode: zero rule files generated in project root.")
    elif agent_target == "auto":
        if adapters.is_global_active() and not root_rules:
            print("  [✓] Global AI Plugin detected — zero root file clutter needed!")
        else:
            # Safe clean default: use hidden directories to avoid polluting root
            created_rules.extend(adapters.setup_agents(hidden_only=not root_rules))
            if (root_dir / ".cursor").is_dir():
                created_rules.append(adapters.setup_cursor(modern=not root_rules))
            if (root_dir / ".git").is_dir() and (root_dir / ".github").is_dir():
                created_rules.append(adapters.setup_copilot())
    else:
        created_rules = adapters.setup_by_agent(agent_target, root_rules=root_rules)

    if created_rules:
        print("Generated AI rule files:")
        for r in created_rules:
            try:
                rel = r.relative_to(root_dir)
            except ValueError:
                rel = r
            print(f"  - {rel}")

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
    if getattr(args, "visual", False):
        from reducetoken.tui import GraphVisualizer
        print(GraphVisualizer.draw_subgraph(res))
    else:
        dsl_output = Generator.format_agent_dsl(res)
        print(dsl_output)


def cmd_ui(args):
    from reducetoken.tui import TerminalUI
    ui = TerminalUI(Path(args.dir).resolve())
    ui.run()


def cmd_tree(args):
    from reducetoken.tui import GraphVisualizer
    root_dir = Path(args.dir).resolve()
    graph = run_pipeline(root_dir, force=False, verbose=False)
    filter_dir = getattr(args, "filter", None)
    print(GraphVisualizer.draw_dependency_tree(graph, filter_dir=filter_dir))


def cmd_doctor(args):
    from reducetoken.tui import GraphVisualizer
    root_dir = Path(args.dir).resolve()
    graph = run_pipeline(root_dir, force=False, verbose=False)
    print(GraphVisualizer.draw_doctor(root_dir, graph))


def cmd_web(args):
    from reducetoken.web_visualizer import open_web_graph
    root_dir = Path(args.dir).resolve()
    html_p = open_web_graph(root_dir)
    print(f"[OK] Interactive Web Graph generated and opened: {html_p}")


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
    with open(hook_file, "w", newline="\n", encoding="utf-8") as f:
        f.write(hook_content)
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


HELP_OVERVIEW = """
================================================================================
                    ReduceToken CLI Reference Guide
     Offline Code Knowledge Graph & Token Saver for AI Coding Agents
================================================================================

USAGE:
  rt <command> [arguments] [options]
  rt                          Launch interactive OpenCode-style Terminal UI

EXPLORATION & VISUALIZATION:
  rt ui                       Interactive Terminal UI with 60fps cursor navigation
  rt web (or rt html)         Open interactive HTML5 Canvas Web Graph in browser
  rt tree [filter]            Display repository dependency tree in ASCII
  rt overview                 Print high-level Architecture Map & God Nodes
  rt query <symbol>           Query exact subgraph (callers, deps, definitions)
  rt graph <symbol>           Render visual ASCII dependency box graph for a symbol

MEMORY & CONTEXT OPTIMIZATION:
  rt compact                  Sync and display compact project session memory (<150 tokens)
  rt memory show              Display all recorded architecture decisions and conventions
  rt memory add <topic> <txt> Record a new architecture decision or convention
  rt memory conv <rule>       Record a new project coding convention / guideline

AI AGENT ADAPTERS & CONTROL:
  rt adapters                 List status of all AI agent integrations (Antigravity, Cursor, etc.)
  rt adapters enable <names>  Enable auto-sync for specific AI agents (e.g. rt adapters enable gemini)
  rt adapters disable <names> Disable auto-sync for AI agents (e.g. rt adapters disable cursor claude)
  rt adapters remove <names>  Uninstall ReduceToken skill/MCP from specified AI platforms
  rt adapters sync            Synchronize all enabled AI platforms now
  rt install                  Interactive AI agent skill installer & local initializer

MAINTENANCE & UPGRADES:
  rt update                   Fast incremental sync (<150ms) for changed files
  rt init [--clean] [--force] Full project scan, build graph cache (.codegraph/)
  rt doctor                   Check system health, cache integrity, git-hook, and AI plugins
  rt git-hook                 Install Git post-commit hook for silent auto-sync
  rt upgrade                  Self-upgrade package from Git and sync enabled AI agents
     --only <agents>          Only sync specific AI agents (e.g. --only antigravity,opencode)
     --skip <agents>          Skip specific AI agents (e.g. --skip cursor,claude)
     --no-agents              Upgrade python package only without modifying AI configs
  rt mcp                      Run Model Context Protocol (MCP) server over standard I/O

HELP & DOCUMENTATION:
  rt help                     Display this command reference guide
  rt help <command>           Display detailed help, flags, and examples for a command

EXAMPLES:
  rt query calculate_sum      Locate calculate_sum, file path, line numbers, callers
  rt graph reducetoken/cli.py Draw ASCII visual dependency graph for cli.py
  rt web                      View interactive node graph in Chrome with folder clusters
  rt adapters disable cursor  Never sync Cursor MCP when running rt upgrade
  rt upgrade --skip cursor    Upgrade ReduceToken while skipping Cursor configuration
  rt upgrade --no-agents      Upgrade ReduceToken core without touching agent skills
================================================================================
"""

COMMAND_DETAILS = {
    "ui": """
Command: rt ui (or rt dashboard)
Launch the interactive Terminal UI with 60fps flicker-free keyboard navigation.
Keys:
  ↑ / ↓         Navigate menu options
  Enter / 1-8   Execute selected option
  q             Exit
""",
    "web": """
Command: rt web (or rt html)
Generate and open the self-contained interactive Web Graph in Google Chrome (or default browser).
Features:
  - Folder enclosure clustering (bounding boxes by directory)
  - Interactive canvas physics with anti-collision clearance halos
  - Keyboard shortcuts: Esc, /, Space, r, c, i, g, ?
""",
    "query": """
Command: rt query <symbol_or_keyword>
Search the Code Knowledge Graph for a symbol, function, class, or file.
Options:
  --visual, -v  Render visual ASCII dependency box diagram instead of compact DSL.
Example:
  rt query calculate_sum
  rt query reducetoken/cli.py
""",
    "graph": """
Command: rt graph <symbol_or_file>
Render a visual ASCII dependency graph box for a specific symbol or file.
Example:
  rt graph reducetoken/graph.py
""",
    "tree": """
Command: rt tree [filter]
Draw the project dependency tree in ASCII text.
Example:
  rt tree
  rt tree parsers
""",
    "adapters": """
Command: rt adapters [action] [names...] (alias: rt agents)
View and manage which AI coding agents ReduceToken integrates with.
Actions:
  rt adapters                 List all AI platforms, detection status, and enabled state
  rt adapters enable <names>  Enable auto-sync for specific agents (e.g. rt adapters enable gemini)
  rt adapters disable <names> Disable auto-sync for specific agents (e.g. rt adapters disable cursor)
  rt adapters remove <names>  Remove/uninstall skill or MCP from specified AI platforms
  rt adapters sync            Synchronize all enabled AI platforms immediately
Supported agent names:
  antigravity (gemini), cursor, claude, opencode, agents (codex)
""",
    "upgrade": """
Command: rt upgrade
Self-upgrade the ReduceToken package from GitHub and refresh global AI plugins.
Options:
  --only <agents>   Only sync specified agents (comma-separated, e.g. --only gemini,opencode)
  --skip <agents>   Skip specified agents (comma-separated, e.g. --skip cursor,claude)
  --no-agents       Upgrade the python package only; do not touch or sync AI agent configs
Example:
  rt upgrade
  rt upgrade --skip cursor,claude
  rt upgrade --only antigravity
  rt upgrade --no-agents
""",
    "update": """
Command: rt update
Perform an incremental delta-sync of the code graph for files modified since last scan.
Runs in <150ms using cached SHA-256 hashes.
""",
    "init": """
Command: rt init
Scan the repository from scratch and initialize .codegraph/ metadata.
Options:
  --force, -f       Force reparse all files ignoring cache
  --clean, -c       Clean mode: only create .codegraph/, no agent rule files
  --agent <name>    Generate rule files for specific agent (auto, antigravity, cursor, claude, etc.)
  --root-rules      Generate legacy rule files in project root (AGENTS.md, GEMINI.md)
""",
    "memory": """
Command: rt memory <action> [topic] [content]
Record and inspect project conventions and architectural decisions for AI agents.
Actions:
  rt memory show              Display all recorded decisions
  rt memory add <topic> <txt> Record an architecture decision
  rt memory conv <rule>       Record a coding convention
""",
    "doctor": """
Command: rt doctor
Inspect system health, cache integrity, Git post-commit hooks, and global AI plugin status.
"""
}


def cmd_help(args):
    target = getattr(args, "help_command", None)
    if target:
        target = target.lower().strip()
        if target in COMMAND_DETAILS:
            print(COMMAND_DETAILS[target])
            return
        else:
            print(f"\nNo specific guide found for '{target}'. Showing full reference guide:\n")
    print(HELP_OVERVIEW)


def cmd_adapters(args):
    from reducetoken.agent_adapters import GlobalAdapterManager
    manager = GlobalAdapterManager()

    action = getattr(args, "adapter_action", None)
    names = getattr(args, "adapter_names", [])

    if not action or action == "list":
        envs = manager.detect_environments()
        print("\n===================================================================")
        print("                 ReduceToken AI Agent Adapters                     ")
        print("===================================================================")
        print(f"{'Agent / Platform':35} {'Detected':12} {'Auto-Sync Status':18}")
        print("-" * 67)
        for key, info in envs.items():
            det = "[Yes]" if info["detected"] else "[No]"
            status = "[ENABLED]" if info.get("enabled", True) else "[DISABLED]"
            print(f"  {info['name']:33} {det:12} {status:18}")
        print("-" * 67)
        print("Management Commands:")
        print("  rt adapters disable <names...> : Stop auto-syncing during upgrades")
        print("  rt adapters enable <names...>  : Re-enable auto-syncing")
        print("  rt adapters remove <names...>  : Completely uninstall from AI tool directory")
        print("  rt adapters sync               : Sync all enabled AI tools right now\n")
        return

    action = action.lower()
    if action == "enable":
        if not names:
            print("Please specify agent names to enable (e.g. 'rt adapters enable gemini cursor')")
            return
        for name in names:
            manager.set_adapter_status(name, True)
            print(f"  [OK] Enabled auto-sync for {name}")
        print("\nUpdated adapter configuration in ~/.reducetoken/config.json")
    elif action == "disable":
        if not names:
            print("Please specify agent names to disable (e.g. 'rt adapters disable cursor claude')")
            return
        for name in names:
            manager.set_adapter_status(name, False)
            print(f"  [OK] Disabled auto-sync for {name} (will be skipped during rt upgrade)")
        print("\nUpdated adapter configuration in ~/.reducetoken/config.json")
    elif action in ("remove", "uninstall"):
        if not names:
            print("Please specify agent names to remove (e.g. 'rt adapters remove cursor')")
            return
        for name in names:
            msg = manager.uninstall_adapter(name)
            print(f"  [OK] {msg}")
    elif action == "sync":
        print("--> Synchronizing enabled AI plugins & skills...")
        results = manager.setup_all_global(respect_config=True)
        for agent, path in results.items():
            prefix = "[OK]" if "Skipped" not in path and "Failed" not in path else "[-]"
            print(f"  {prefix} {agent:35}: {path}")
        print("\nSync complete!")


def cmd_upgrade(args):
    print("--> Upgrading ReduceToken CLI from Git...")
    repo_url = "git+https://github.com/TuilaTammmmm/ReduceToken.git"
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", repo_url]
    ret = subprocess.run(cmd)
    if ret.returncode != 0:
        print("\n[Error] Failed to upgrade via pip. Please verify internet connection or Git access.", file=sys.stderr)
        return

    print("\n[OK] ReduceToken package upgraded successfully.")

    if getattr(args, "no_agents", False):
        print("--> Skipping AI agent synchronization (--no-agents specified).")
        print("\nUpgrade complete! You are running the latest version of ReduceToken.")
        return

    only = getattr(args, "only", None)
    skip = getattr(args, "skip", None)

    only_list = [x.strip() for x in only.split(",")] if only else None
    skip_list = [x.strip() for x in skip.split(",")] if skip else None

    print("--> Synchronizing AI plugins & skills...")
    from reducetoken.agent_adapters import GlobalAdapterManager
    manager = GlobalAdapterManager()
    results = manager.setup_all_global(only=only_list, skip=skip_list, respect_config=True)
    for agent, path in results.items():
        prefix = "[OK]" if "Skipped" not in path and "Failed" not in path else "[-]"
        print(f"  {prefix} {agent:35}: {path}")
    print("\nUpgrade complete! You are running the latest version of ReduceToken.")


def main():
    if len(sys.argv) == 1 and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
        from reducetoken.tui import TerminalUI
        ui = TerminalUI(Path(".").resolve())
        ui.run()
        return

    # Direct help interception for rt help / rt --help / rt -h
    if len(sys.argv) > 1 and sys.argv[1] in ("help", "--help", "-h"):
        target_cmd = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else None
        class FakeHelpArgs:
            help_command = target_cmd
        cmd_help(FakeHelpArgs())
        return

    parser = argparse.ArgumentParser(
        prog="reducetoken",
        description="ReduceToken - Code Knowledge Graph and Token Saver for AI Agents"
    )
    parser.add_argument("--dir", "-d", default=".", help="Root directory of the repository (default: current dir)")

    subparsers = parser.add_subparsers(dest="command", required=True)

    # help
    p_help = subparsers.add_parser("help", help="Display ReduceToken command reference guide")
    p_help.add_argument("help_command", nargs="?", default=None, help="Command name to get detailed help for")

    # ui / dashboard
    subparsers.add_parser("ui", help="Launch interactive Terminal UI & Graph Explorer")
    subparsers.add_parser("dashboard", help="Alias for ui")

    # init
    p_init = subparsers.add_parser("init", help="Scan repository, build graph, and setup AI instructions")
    p_init.add_argument("--force", "-f", action="store_true", help="Force reparse all files ignoring cache")
    p_init.add_argument("--clean", "-c", action="store_true", help="Clean mode: only create .codegraph/, no rule files")
    p_init.add_argument(
        "--agent", "-a",
        default="auto",
        choices=["auto", "clean", "none", "antigravity", "cursor", "claude", "copilot", "all"],
        help="Target AI agent for rule generation (default: auto detect, zero clutter if global plugin exists)"
    )
    p_init.add_argument("--root-rules", action="store_true", help="Generate legacy rule files directly in project root")

    # update
    subparsers.add_parser("update", help="Incrementally update graph for changed files")

    # query
    p_query = subparsers.add_parser("query", help="Query graph for a symbol, function, class, or file")
    p_query.add_argument("query", help="Symbol or keyword to search")
    p_query.add_argument("--visual", "-v", action="store_true", help="Draw ASCII visual box graph instead of compact DSL")

    # graph (alias for query --visual)
    p_graph = subparsers.add_parser("graph", help="Draw ASCII visual dependency graph for a symbol or file")
    p_graph.add_argument("query", help="Symbol or file to draw graph for")

    # tree
    p_tree = subparsers.add_parser("tree", help="Draw ASCII visual dependency tree of the repository")
    p_tree.add_argument("filter", nargs="?", default=None, help="Optional directory name filter")

    # web / html
    subparsers.add_parser("web", help="Generate and open interactive Web Graph in browser")
    subparsers.add_parser("html", help="Alias for web")

    # doctor
    subparsers.add_parser("doctor", help="Check system health, cache, Git hooks, and AI integrations")

    # overview
    subparsers.add_parser("overview", help="Print the high-level architecture map")

    # compact
    subparsers.add_parser("compact", help="Update and print the compact project session context")

    # memory
    p_mem = subparsers.add_parser("memory", help="Manage long-term project memory & decisions")
    p_mem.add_argument("action", choices=["add", "conv", "show"], help="Memory action")
    p_mem.add_argument("topic", nargs="?", default="", help="Decision topic or convention description")
    p_mem.add_argument("content", nargs="?", default="", help="Detailed decision content (for add)")

    # mcp
    subparsers.add_parser("mcp", help="Run as Model Context Protocol (MCP) server")

    # git-hook
    subparsers.add_parser("git-hook", help="Install Git post-commit hook for auto-sync")

    # adapters / agents
    p_adap = subparsers.add_parser("adapters", help="View and manage AI agent integrations (Antigravity, Cursor, etc.)")
    p_adap.add_argument("adapter_action", nargs="?", default="list", choices=["list", "enable", "disable", "remove", "uninstall", "sync"], help="Action to perform")
    p_adap.add_argument("adapter_names", nargs="*", default=[], help="Target agent names (e.g. cursor, claude, gemini)")

    p_agents = subparsers.add_parser("agents", help="Alias for adapters")
    p_agents.add_argument("adapter_action", nargs="?", default="list", choices=["list", "enable", "disable", "remove", "uninstall", "sync"], help="Action to perform")
    p_agents.add_argument("adapter_names", nargs="*", default=[], help="Target agent names")

    # install
    p_inst = subparsers.add_parser("install", help="Install global Antigravity plugin or local rules")
    p_inst.add_argument("--global", "-g", dest="global_plugin", action="store_true", help="Install global Antigravity plugin to ~/.gemini/config/plugins")
    p_inst.add_argument("--force", "-f", action="store_true", help="Force reparse all files ignoring cache (for local init)")

    # upgrade
    p_upg = subparsers.add_parser("upgrade", help="Self-upgrade ReduceToken package and refresh global AI plugins from Git")
    p_upg.add_argument("--only", default=None, help="Only sync specific AI agents (comma-separated, e.g. antigravity,opencode)")
    p_upg.add_argument("--skip", default=None, help="Skip specific AI agents (comma-separated, e.g. cursor,claude)")
    p_upg.add_argument("--no-agents", action="store_true", help="Upgrade python package only without modifying AI agent configs")

    args = parser.parse_args()

    if args.command == "help":
        cmd_help(args)
    elif args.command in ("ui", "dashboard"):
        cmd_ui(args)
    elif args.command in ("web", "html"):
        cmd_web(args)
    elif args.command == "tree":
        cmd_tree(args)
    elif args.command == "doctor":
        cmd_doctor(args)
    elif args.command in ("adapters", "agents"):
        cmd_adapters(args)
    elif args.command == "graph":
        args.visual = True
        cmd_query(args)
    elif args.command == "init":
        cmd_init(args)
    elif args.command == "install":
        cmd_install(args)
    elif args.command == "upgrade":
        cmd_upgrade(args)
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
