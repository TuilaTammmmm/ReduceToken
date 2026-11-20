import os
import sys
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from reducetoken.graph import CodeGraph
from reducetoken.generator import Generator
from reducetoken.memory import SessionMemoryManager
from reducetoken.agent_adapters import AgentAdapterManager, GlobalAdapterManager
from reducetoken.web_visualizer import open_web_graph


class Colors:
    """ANSI styling for clean terminal rendering."""
    def __init__(self):
        if sys.platform == "win32":
            os.system("")
        is_tty = hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
        no_color = bool(os.getenv("NO_COLOR", ""))

        self.enabled = is_tty and not no_color
        self.RESET = "\033[0m" if self.enabled else ""
        self.BOLD = "\033[1m" if self.enabled else ""
        self.DIM = "\033[2m" if self.enabled else ""
        self.RED = "\033[91m" if self.enabled else ""
        self.GREEN = "\033[92m" if self.enabled else ""
        self.YELLOW = "\033[93m" if self.enabled else ""
        self.BLUE = "\033[94m" if self.enabled else ""
        self.MAGENTA = "\033[95m" if self.enabled else ""
        self.CYAN = "\033[96m" if self.enabled else ""
        self.WHITE = "\033[97m" if self.enabled else ""
        self.INVERT = "\033[7m" if self.enabled else ""


C = Colors()


def read_key() -> str:
    """Reads a single keypress or arrow key event."""
    if sys.platform == "win32":
        try:
            import msvcrt
            ch = msvcrt.getch()
            if ch in (b'\x00', b'\xe0'):
                sub = msvcrt.getch()
                if sub == b'H':
                    return 'UP'
                elif sub == b'P':
                    return 'DOWN'
                return ''
            if ch in (b'\r', b'\n'):
                return 'ENTER'
            if ch in (b'\x1b', b'q', b'Q'):
                return 'QUIT'
            if ch == b'\x03':
                return 'QUIT'
            return ch.decode("utf-8", errors="ignore").lower()
        except Exception:
            return ''
    else:
        try:
            import termios, tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setcbreak(fd)
                ch = sys.stdin.read(1)
                if ch == '\x1b':
                    seq = sys.stdin.read(2)
                    if seq == '[A':
                        return 'UP'
                    elif seq == '[B':
                        return 'DOWN'
                    return 'QUIT'
                if ch in ('\r', '\n'):
                    return 'ENTER'
                if ch in ('q', 'Q'):
                    return 'QUIT'
                return ch.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            return ''


class GraphVisualizer:
    """ASCII & Unicode Knowledge Graph & Dependency Tree Renderer."""

    @staticmethod
    def draw_subgraph(query_res: Dict[str, Any]) -> str:
        target = query_res.get("target_file")
        if not target:
            return f"{C.YELLOW}No matching files or symbols found for '{query_res.get('query')}'.{C.RESET}"

        matched_symbols = query_res.get("matched_symbols", [])
        dependents = query_res.get("dependents", [])
        dependencies = query_res.get("dependencies", [])
        symbols_in_target = query_res.get("symbols_in_target", [])
        summary = query_res.get("summary", "")

        lines = []
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)

        # 1. Target Node Box
        lines.append(f"{C.CYAN}┌" + "─" * (term_width - 2) + f"┐{C.RESET}")
        title = f" TARGET FILE: {target} "
        lines.append(f"{C.CYAN}│{C.BOLD}{C.WHITE}{title.center(term_width - 2)}{C.RESET}{C.CYAN}│{C.RESET}")

        if summary:
            sum_str = f"\"{summary}\""
            if len(sum_str) > term_width - 6:
                sum_str = sum_str[: term_width - 9] + "..."
            lines.append(f"{C.CYAN}│{C.DIM}{C.YELLOW}{sum_str.center(term_width - 2)}{C.RESET}{C.CYAN}│{C.RESET}")

        if matched_symbols:
            sym_items = []
            for s in matched_symbols[:4]:
                name = s.get("name", "")
                kind = s.get("kind", "")
                line = s.get("line", 1)
                sym_items.append(f"{name} ({kind}:L{line})")
            sym_line = "Matched: " + ", ".join(sym_items)
            if len(sym_line) > term_width - 6:
                sym_line = sym_line[: term_width - 9] + "..."
            lines.append(f"{C.CYAN}│ {C.GREEN}{sym_line.ljust(term_width - 4)}{C.RESET} {C.CYAN}│{C.RESET}")

        lines.append(f"{C.CYAN}└" + "─" * (term_width - 2) + f"┘{C.RESET}")

        # 2. Callers / Inward Flow
        lines.append(f"          {C.GREEN}▲{C.RESET}")
        lines.append(f"          {C.GREEN}│ (imported & called by){C.RESET}")
        lines.append(f"{C.GREEN}┌─ INCOMING CALLERS ({len(dependents)}) " + "─" * (term_width - 25) + f"┐{C.RESET}")
        if dependents:
            for dep in sorted(dependents)[:8]:
                lines.append(f"{C.GREEN}│{C.RESET}  ├── 📄 {dep}")
            if len(dependents) > 8:
                lines.append(f"{C.GREEN}│{C.RESET}  └── {C.DIM}... and {len(dependents) - 8} more callers{C.RESET}")
        else:
            lines.append(f"{C.GREEN}│{C.RESET}  └── {C.DIM}(No incoming callers — Entry point / Root module){C.RESET}")
        lines.append(f"{C.GREEN}└" + "─" * (term_width - 2) + f"┘{C.RESET}")

        # 3. Dependencies / Outward Flow
        lines.append(f"          {C.MAGENTA}│{C.RESET}")
        lines.append(f"          {C.MAGENTA}▼ (requires / imports){C.RESET}")
        lines.append(f"{C.MAGENTA}┌─ OUTGOING DEPENDENCIES ({len(dependencies)}) " + "─" * (term_width - 29) + f"┐{C.RESET}")
        if dependencies:
            for dep in sorted(dependencies)[:8]:
                lines.append(f"{C.MAGENTA}│{C.RESET}  ├── 📦 {dep}")
            if len(dependencies) > 8:
                lines.append(f"{C.MAGENTA}│{C.RESET}  └── {C.DIM}... and {len(dependencies) - 8} more modules{C.RESET}")
        else:
            lines.append(f"{C.MAGENTA}│{C.RESET}  └── {C.DIM}(Zero internal dependencies — Standalone module){C.RESET}")
        lines.append(f"{C.MAGENTA}└" + "─" * (term_width - 2) + f"┘{C.RESET}")

        # 4. Key Symbols Inside Target File (All symbols displayed without truncation)
        if symbols_in_target:
            lines.append(f"\n{C.BOLD}{C.CYAN}Defined Symbols in '{target}' ({len(symbols_in_target)}):{C.RESET}")
            for s in symbols_in_target:
                kind = s.get("kind", "")
                name = s.get("name", "")
                ln = s.get("line", 1)
                doc = s.get("doc", "")
                doc_part = f" — {C.DIM}{doc}{C.RESET}" if doc else ""
                lines.append(f"  {C.YELLOW}•{C.RESET} [{C.BLUE}{kind}{C.RESET}] {C.BOLD}{name}{C.RESET} {C.DIM}(L{ln}){C.RESET}{doc_part}")

        return "\n".join(lines)

    @staticmethod
    def draw_dependency_tree(graph: CodeGraph, filter_dir: Optional[str] = None) -> str:
        """Render a hierarchical tree of files with their dependency connections."""
        lines = []
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)

        folder_groups: Dict[str, List[str]] = {}
        for f in sorted(graph.all_files):
            parts = Path(f).parts
            top_dir = parts[0] if len(parts) > 1 else "(root)"
            if filter_dir and filter_dir.lower() not in f.lower():
                continue
            folder_groups.setdefault(top_dir, []).append(f)

        if not folder_groups:
            return f"{C.YELLOW}No files matched directory filter '{filter_dir}'.{C.RESET}"

        lines.append(f"{C.BOLD}{C.CYAN}📦 Project Knowledge Graph Dependency Tree{C.RESET}")
        lines.append(f"{C.DIM}" + "─" * (term_width - 2) + f"{C.RESET}")

        total_folders = len(folder_groups)
        for f_idx, (folder, files) in enumerate(folder_groups.items()):
            is_last_folder = (f_idx == total_folders - 1)
            f_prefix = "└── " if is_last_folder else "├── "
            lines.append(f"{C.BLUE}{f_prefix}📂 {folder}/{C.RESET}")

            child_indent = "    " if is_last_folder else "│   "
            for file_idx, f_path in enumerate(files):
                is_last_file = (file_idx == len(files) - 1)
                file_prefix = "└── " if is_last_file else "├── "
                analysis = graph.analyses.get(f_path)
                symbols_count = len(graph.file_symbols.get(f_path, []))
                deps = graph.file_dependencies.get(f_path, set())
                callers = graph.file_dependents.get(f_path, set())

                lines.append(
                    f"{child_indent}{C.CYAN}{file_prefix}📄 {Path(f_path).name}{C.RESET} "
                    f"{C.DIM}({symbols_count} syms){C.RESET}"
                )

                sub_indent = child_indent + ("    " if is_last_file else "│   ")

                # Top symbols
                top_syms = Generator._get_top_symbols(analysis)
                if top_syms:
                    sym_names = ", ".join(top_syms[:3])
                    lines.append(f"{sub_indent}├── {C.YELLOW}🔹 def:{C.RESET} {sym_names}")

                # Imports
                if deps:
                    dep_str = ", ".join(Path(d).name for d in sorted(deps)[:4])
                    if len(deps) > 4:
                        dep_str += f" (+{len(deps) - 4})"
                    lines.append(f"{sub_indent}├── {C.MAGENTA}──▶ Imports:{C.RESET} {dep_str}")

                # Callers
                if callers:
                    caller_str = ", ".join(Path(c).name for c in sorted(callers)[:3])
                    if len(callers) > 3:
                        caller_str += f" (+{len(callers) - 3})"
                    lines.append(f"{sub_indent}└── {C.GREEN}◀── Used By:{C.RESET} {caller_str}")
                else:
                    lines.append(f"{sub_indent}└── {C.DIM}◀── (Entry point / root){C.RESET}")

        return "\n".join(lines)

    @staticmethod
    def draw_architecture_overview(graph: CodeGraph) -> str:
        """Render high-level architecture overview, God Nodes, and Centrality Network."""
        stats = graph.get_overview_stats()
        lines = []
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)

        lines.append(f"{C.BOLD}{C.CYAN}🗺️ ARCHITECTURE OVERVIEW & GOD NODES NETWORK{C.RESET}")
        lines.append(f"{C.DIM}" + "─" * (term_width - 2) + f"{C.RESET}")
        lines.append(f"• Total Indexed Files  : {C.BOLD}{stats['total_files']}{C.RESET}")
        lines.append(f"• Total Symbols Defined: {C.BOLD}{stats['total_symbols']}{C.RESET}")

        # God Nodes / Chokepoints
        god_nodes = stats.get("god_nodes", [])
        if god_nodes:
            lines.append(f"\n{C.BOLD}{C.YELLOW}🔥 Critical God Nodes & Architectural Chokepoints:{C.RESET}")
            lines.append(f"{C.DIM}  (Central hubs with highest blast radius if modified){C.RESET}")
            max_score = max((g["score"] for g in god_nodes), default=1)
            bar_width = 16

            for idx, g in enumerate(god_nodes, 1):
                filled = int((g["score"] / max_score) * bar_width) if max_score > 0 else 0
                bar = f"{C.YELLOW}" + "█" * filled + f"{C.DIM}" + "░" * (bar_width - filled) + f"{C.RESET}"
                fname = g["file"]
                role = g["role"]
                in_d = g["in_degree"]
                out_d = g["out_degree"]
                lines.append(f"  {idx}. {fname:36} {bar} [{role} | In:{in_d}, Out:{out_d}]")

        # Entry points
        eps = stats.get("entry_points", [])
        if eps:
            lines.append(f"\n{C.BOLD}{C.GREEN}🚀 Entry Points / CLI Interfaces:{C.RESET}")
            for ep in eps:
                lines.append(f"  • {C.GREEN}{ep}{C.RESET}")

        return "\n".join(lines)

    @staticmethod
    def draw_doctor(root_dir: Path, graph: CodeGraph) -> str:
        """Health-check project status, Git hook, AI integrations, and token savings."""
        lines = []
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)

        lines.append(f"{C.BOLD}{C.CYAN}🩺 REDUCETOKEN SYSTEM DIAGNOSTICS & DOCTOR{C.RESET}")
        lines.append(f"{C.DIM}" + "─" * (term_width - 2) + f"{C.RESET}")

        cache_p = root_dir / ".codegraph" / "cache.json"
        arch_p = root_dir / ".codegraph" / "architecture_map.md"
        mem_p = root_dir / ".codegraph" / "session_context.md"

        cache_ok = cache_p.is_file()
        cache_size = cache_p.stat().st_size if cache_ok else 0
        lines.append(f"{C.BOLD}[1] Graph & Cache Integrity:{C.RESET}")
        lines.append(f"  • Indexed Files     : {C.GREEN}{len(graph.all_files)}{C.RESET} files")
        lines.append(f"  • Cache Status      : {C.GREEN if cache_ok else C.RED}{cache_p.name} ({cache_size / 1024:.1f} KB){C.RESET}")
        lines.append(f"  • Architecture Map  : {C.GREEN if arch_p.is_file() else C.RED}{'Present' if arch_p.is_file() else 'Missing'}{C.RESET}")
        lines.append(f"  • Session Context   : {C.GREEN if mem_p.is_file() else C.RED}{'Active' if mem_p.is_file() else 'Missing'}{C.RESET}")

        hook_p = root_dir / ".git" / "hooks" / "post-commit"
        has_hook = hook_p.is_file() and "reducetoken" in hook_p.read_text(encoding="utf-8", errors="ignore")
        lines.append(f"\n{C.BOLD}[2] Git Background Sync Hook:{C.RESET}")
        if has_hook:
            lines.append(f"  • Git Post-Commit   : {C.GREEN}Active (Zero-Effort Background Sync){C.RESET}")
        else:
            lines.append(f"  • Git Post-Commit   : {C.YELLOW}Not installed (Run 'rt git-hook' to enable){C.RESET}")

        global_mgr = GlobalAdapterManager()
        envs = global_mgr.detect_environments()
        lines.append(f"\n{C.BOLD}[3] AI Agent Integrations:{C.RESET}")
        for k, v in envs.items():
            status_color = C.GREEN if v["detected"] else C.DIM
            status_txt = "DETECTED / ACTIVE" if v["detected"] else "Not installed"
            lines.append(f"  • {v['name']:38}: {status_color}{status_txt}{C.RESET}")

        raw_token_est = len(graph.all_files) * 800
        query_token_est = 60
        savings_pct = ((raw_token_est - query_token_est) / raw_token_est) * 100 if raw_token_est > 0 else 95

        lines.append(f"\n{C.BOLD}[4] Token Economics:{C.RESET}")
        lines.append(f"  • Raw Full-Scan Dump    : ~{raw_token_est:,} tokens / prompt")
        lines.append(f"  • ReduceToken Subgraph  : ~{query_token_est} tokens / query")
        lines.append(f"  • Context Token Savings : {C.BOLD}{C.GREEN}▲ {savings_pct:.1f}% Savings!{C.RESET}")

        return "\n".join(lines)


class TerminalUI:
    """Interactive OpenCode-style Terminal Dashboard for ReduceToken."""

    MENU_ITEMS = [
        ("1", "Search & Subgraph Explorer"),
        ("2", "Visual Dependency Tree"),
        ("3", "Open Web Graph in Browser"),
        ("4", "Architecture Map & God Nodes"),
        ("5", "Session Memory & Decisions"),
        ("6", "Update / Sync Graph (Incremental)"),
        ("7", "Clean Cache & Rebuild (Full)"),
        ("8", "System Diagnostics & Doctor"),
        ("q", "Exit")
    ]

    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir).resolve()
        from reducetoken.cli import run_pipeline
        self.run_pipeline = run_pipeline
        self.graph = run_pipeline(self.root_dir, force=False, verbose=False)
        self.memory = SessionMemoryManager(self.root_dir)
        self.selected_idx = 0

    def clear(self):
        os.system("cls" if sys.platform == "win32" else "clear")

    def print_header(self):
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)
        print(f"{C.CYAN}┌" + "─" * (term_width - 2) + f"┐{C.RESET}")
        title1 = "REDUCETOKEN - CODE KNOWLEDGE GRAPH & TOKEN SAVER"
        print(f"{C.CYAN}│{C.BOLD}{C.WHITE}{title1.center(term_width - 2)}{C.RESET}{C.CYAN}│{C.RESET}")
        print(f"{C.CYAN}└" + "─" * (term_width - 2) + f"┘{C.RESET}")

        stats = self.graph.get_overview_stats()
        decisions_cnt = len(self.memory.memory_data.get("decisions", []))
        god_nodes_cnt = len(stats.get("god_nodes", []))

        info_bar = (
            f" [ Files: {C.BOLD}{stats['total_files']}{C.RESET} | "
            f"Symbols: {C.BOLD}{stats['total_symbols']}{C.RESET} | "
            f"God Nodes: {C.BOLD}{C.YELLOW}{god_nodes_cnt}{C.RESET} | "
            f"Memory: {C.BOLD}{decisions_cnt} decisions{C.RESET} ]"
        )
        print(info_bar + "\n")

    def build_dashboard_str(self) -> str:
        term_width = min(shutil.get_terminal_size((80, 24)).columns, 88)
        lines = []
        lines.append(f"{C.CYAN}┌" + "─" * (term_width - 2) + f"┐{C.RESET}\033[K")
        title1 = "REDUCETOKEN - CODE KNOWLEDGE GRAPH & TOKEN SAVER"
        lines.append(f"{C.CYAN}│{C.BOLD}{C.WHITE}{title1.center(term_width - 2)}{C.RESET}{C.CYAN}│{C.RESET}\033[K")
        lines.append(f"{C.CYAN}└" + "─" * (term_width - 2) + f"┘{C.RESET}\033[K")

        stats = self.graph.get_overview_stats()
        decisions_cnt = len(self.memory.memory_data.get("decisions", []))
        god_nodes_cnt = len(stats.get("god_nodes", []))

        info_bar = (
            f" [ Files: {C.BOLD}{stats['total_files']}{C.RESET} | "
            f"Symbols: {C.BOLD}{stats['total_symbols']}{C.RESET} | "
            f"God Nodes: {C.BOLD}{C.YELLOW}{god_nodes_cnt}{C.RESET} | "
            f"Memory: {C.BOLD}{decisions_cnt} decisions{C.RESET} ]"
        )
        lines.append(info_bar + "\033[K\n")
        lines.append(f"{C.DIM}Use [↑/↓] or [1-7] to navigate, [Enter] to select, [q] to exit:{C.RESET}\033[K\n")

        for idx, (key, label) in enumerate(self.MENU_ITEMS):
            is_selected = (idx == self.selected_idx)
            cursor = f"{C.CYAN}❯{C.RESET} " if is_selected else "  "

            if key == "q":
                color_key = f"{C.RED}[q]{C.RESET}"
            else:
                color_key = f"{C.CYAN}[{key}]{C.RESET}"

            if is_selected:
                lines.append(f"{cursor}{color_key} {C.BOLD}{C.WHITE}{C.INVERT} {label} {C.RESET}\033[K")
            else:
                lines.append(f"{cursor}{color_key} {label}\033[K")
        lines.append("\033[K")
        return "\n".join(lines)

    def run(self):
        is_interactive = hasattr(sys.stdin, "isatty") and sys.stdin.isatty()

        # Initial clean clear
        self.clear()
        if is_interactive:
            # Hide terminal cursor to eliminate blinking
            sys.stdout.write("\033[?25l")
            sys.stdout.flush()

        try:
            while True:
                # Butter-smooth in-place redraw using ANSI cursor home (\033[H)
                dashboard_text = self.build_dashboard_str()
                sys.stdout.write("\033[H" + dashboard_text)
                sys.stdout.flush()

                if not is_interactive:
                    try:
                        choice = input("Enter choice (1-7, q): ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        break
                    self._dispatch_choice(choice)
                    break

                key = read_key()

                if key == 'UP':
                    self.selected_idx = (self.selected_idx - 1) % len(self.MENU_ITEMS)
                elif key == 'DOWN':
                    self.selected_idx = (self.selected_idx + 1) % len(self.MENU_ITEMS)
                elif key == 'ENTER':
                    chosen_key = self.MENU_ITEMS[self.selected_idx][0]
                    if chosen_key == 'q':
                        break
                    # Restore cursor before submenu
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                    self._dispatch_choice(chosen_key)
                    self.clear()
                    sys.stdout.write("\033[?25l")
                    sys.stdout.flush()
                elif key in ('1', '2', '3', '4', '5', '6', '7', '8'):
                    sys.stdout.write("\033[?25h")
                    sys.stdout.flush()
                    self._dispatch_choice(key)
                    self.clear()
                    sys.stdout.write("\033[?25l")
                    sys.stdout.flush()
                elif key in ('q', 'quit'):
                    break
        finally:
            # Always restore cursor
            sys.stdout.write("\033[?25h\n")
            sys.stdout.flush()

        print(f"{C.GREEN}ReduceToken closed.{C.RESET}")

    def _dispatch_choice(self, key: str):
        if key == "1":
            self._handle_query()
        elif key == "2":
            self._handle_tree()
        elif key == "3":
            self._handle_web()
        elif key == "4":
            self._handle_architecture()
        elif key == "5":
            self._handle_memory()
        elif key == "6":
            self._handle_sync()
        elif key == "7":
            self._handle_clean()
        elif key == "8":
            self._handle_doctor()

    def _handle_sync(self):
        self.clear()
        self.print_header()
        print(f"\n{C.CYAN}--> Synchronizing Knowledge Graph incrementally...{C.RESET}")
        self.graph = self.run_pipeline(self.root_dir, force=False, verbose=True)
        print(f"{C.GREEN}[✓] Incremental delta sync completed successfully!{C.RESET}\n")
        input(f"{C.DIM}Press Enter to return...{C.RESET}")

    def _handle_query(self):
        self.clear()
        self.print_header()
        print(f"{C.BOLD}{C.CYAN}🔍 Search Symbol, Function, Class, or File Path:{C.RESET}")
        print(f"{C.DIM}(Examples: 'CodeGraph', 'parse_python_file', 'cli.py', 'cache'){C.RESET}\n")

        try:
            q = input("Search query: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        if not q:
            return

        res = self.graph.query(q)
        print("\n" + GraphVisualizer.draw_subgraph(res))
        print()
        input(f"{C.DIM}Press Enter to return...{C.RESET}")

    def _handle_tree(self):
        self.clear()
        self.print_header()
        print(f"{C.DIM}Directory filter (leave blank for entire codebase):{C.RESET}")
        try:
            f_dir = input("Filter folder: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        print()
        print(GraphVisualizer.draw_dependency_tree(self.graph, filter_dir=f_dir or None))
        print()
        input(f"{C.DIM}Press Enter to return...{C.RESET}")

    def _handle_web(self):
        self.clear()
        self.print_header()
        print(f"{C.BOLD}{C.CYAN}🌐 Launching Interactive Web Graph...{C.RESET}\n")
        html_p = open_web_graph(self.root_dir)
        file_uri = html_p.resolve().as_uri()
        print(f"  • {C.GREEN}Local File{C.RESET} : {html_p.resolve()}")
        print(f"  • {C.GREEN}Browser URL{C.RESET}: {C.CYAN}{file_uri}{C.RESET}")
        print(f"\n{C.GREEN}[✓] Sent launch command to Chrome / Default Browser.{C.RESET}")
        print(f"{C.DIM}(If the browser does not pop up automatically, click or copy the URL above.){C.RESET}\n")
        input(f"{C.DIM}Press Enter to return to menu...{C.RESET}")

    def _handle_architecture(self):
        self.clear()
        self.print_header()
        print(GraphVisualizer.draw_architecture_overview(self.graph))
        print()
        input(f"{C.DIM}Press Enter to return...{C.RESET}")

    def _handle_memory(self):
        while True:
            self.clear()
            self.print_header()
            print(f"{C.BOLD}{C.CYAN}🧠 Session Memory & Architectural Conventions:{C.RESET}")
            print(f"{C.DIM}" + "─" * 60 + f"{C.RESET}")
            summary = self.memory.get_compact_summary()
            print(summary or f"{C.DIM}(No memory recorded yet){C.RESET}")
            print(f"{C.DIM}" + "─" * 60 + f"{C.RESET}\n")

            print(f"  {C.CYAN}[A]{C.RESET} Add Decision")
            print(f"  {C.CYAN}[C]{C.RESET} Add Convention")
            print(f"  {C.CYAN}[K]{C.RESET} Compact Memory (<500 tokens)")
            print(f"  {C.RED}[B]{C.RESET} Back\n")

            try:
                sub_c = input("Action (A/C/K/B) > ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                break

            if sub_c in ("b", "q", ""):
                break
            elif sub_c == "a":
                topic = input("Topic / Title of Decision: ").strip()
                if topic:
                    content = input("Details / Agreed Decision: ").strip()
                    self.memory.add_decision(topic, content)
                    print(f"{C.GREEN}[OK] Saved decision '{topic}'!{C.RESET}")
                    input(f"{C.DIM}Press Enter to continue...{C.RESET}")
            elif sub_c == "c":
                conv = input("Programming convention: ").strip()
                if conv:
                    self.memory.add_convention(conv)
                    print(f"{C.GREEN}[OK] Saved convention!{C.RESET}")
                    input(f"{C.DIM}Press Enter to continue...{C.RESET}")
            elif sub_c == "k":
                self.memory.compact()
                print(f"{C.GREEN}[OK] Memory compacted!{C.RESET}")
                input(f"{C.DIM}Press Enter to continue...{C.RESET}")

    def _handle_doctor(self):
        self.clear()
        self.print_header()
        print(GraphVisualizer.draw_doctor(self.root_dir, self.graph))
        print()
        input(f"{C.DIM}Press Enter to return...{C.RESET}")

    def _handle_clean(self):
        ans = input(f"{C.YELLOW}Clean cache and force full re-index? (y/N): {C.RESET}").strip().lower()
        if ans == "y":
            cache_p = self.root_dir / ".codegraph" / "cache.json"
            if cache_p.is_file():
                cache_p.unlink()
            print(f"\n{C.CYAN}--> Full re-indexing codebase...{C.RESET}")
            self.graph = self.run_pipeline(self.root_dir, force=True, verbose=True)
            print(f"{C.GREEN}[✓] Full re-index complete!{C.RESET}")
        input(f"{C.DIM}Press Enter to return...{C.RESET}")
