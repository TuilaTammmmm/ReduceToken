import json
from pathlib import Path
from typing import List, Optional, Dict


COPILOT_INSTRUCTION = """# AI Token-Saving Guidelines for GitHub Copilot
This repository uses **ReduceToken** to optimize context and save tokens.
- **NEVER** scan the entire directory tree or read dozens of files indiscriminately.
- **ALWAYS** check `.codegraph/architecture_map.md` first to understand repository structure and module responsibilities.
- Check `.codegraph/session_context.md` for project conventions and past architectural decisions.
- Use `rt query <symbol_or_keyword>` to locate exact files, definitions, and dependencies.
- If import aliases (@/*, ~/*) or monorepo packages are used, inspect tsconfig.json / package.json to resolve real paths before querying.
- Only inspect the specific target file and its direct 1-hop dependencies.
- Keep responses compact with minimal tokens (targeted diffs, no full-file dumps).
"""

CURSOR_RULES = """# ReduceToken - Cursor Rules
- Rule 1: Before browsing files or making multi-file searches, read `.codegraph/architecture_map.md`.
- Rule 2: Read `.codegraph/session_context.md` to recall past project conventions and agreed decisions.
- Rule 3: Execute `rt query <symbol>` in terminal to find the exact file and callers.
- Rule 4: If import aliases (@/*) are used, resolve paths via tsconfig.json / package.json before reading.
- Rule 5: Only read files that are directly related to the user query.
- Rule 6 (Auto-Memory): Silently record any new architecture decision into `.codegraph/session_context.md`. If it exceeds 50 lines, run `rt compact`.
- Rule 7: Keep chat responses concise to prevent context token explosion.
"""

CLAUDE_INSTRUCTION = """# Claude Code - Token Saving Guidelines
- Repository architecture map: `.codegraph/architecture_map.md`
- Project memory & agreed decisions: `.codegraph/session_context.md`
- Use `rt query <symbol>` to find exact definitions and dependencies.
- If path aliases (@/*) or monorepo packages are used, check tsconfig.json / package.json to resolve real paths.
- Do NOT run full-directory recursive scans.
- Run `rt update` after modifying code to sync the graph.
- If session_context.md exceeds 50 lines, run `rt compact`.
- Keep chat responses concise; output targeted diffs instead of re-printing full files.
"""

AGENTS_INSTRUCTION = """# Agent Guidelines (Antigravity & OpenCode)
## Token Optimization & Code Knowledge Graph (100% Autonomous)
- **First Step**: Always consult `.codegraph/architecture_map.md` and `.codegraph/session_context.md` to understand module overview and past architectural decisions without wasting tokens.
- **Targeted Lookup**: Run `rt query <keyword_or_symbol>` to get the exact subgraph (target file, dependencies, callers).
- **Import Aliases & Monorepo**: When navigating virtual aliases (`@/*`, `~/*`, `workspace:*`), inspect `tsconfig.json` (`paths`) or `package.json` workspaces to resolve real paths instead of full-directory searches.
- **Zero Full-Scan**: Never run commands that list or read all files across the repository.
- **Autonomous Silent Maintenance (Zero User Effort)**:
  * Do NOT spam `rt update` after every micro-edit. Run `rt update` once upon completing a task batch or logical feature.
  * When you make an important technical decision or convention, automatically record it in `.codegraph/session_context.md`.
  * If `.codegraph/session_context.md` exceeds 50 lines (or ~500 tokens), automatically run `rt compact` to maintain token budget.
- **Chat Token Minimization**:
  * Keep responses concise and focused. Do not repeat full files or long logs.
  * Point directly to file line ranges with `file://` links and targeted diffs.
  * All persistent project state lives in `.codegraph/session_context.md`, so even in fresh chat tabs you pick up context in < 150 tokens.
"""


class AgentAdapterManager:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)

    def setup_all(self):
        self.setup_copilot()
        self.setup_cursor()
        self.setup_claude()
        self.setup_agents()

    def setup_copilot(self) -> Path:
        p = self.root_dir / ".github" / "copilot-instructions.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(COPILOT_INSTRUCTION, encoding="utf-8")
        return p

    def setup_cursor(self) -> Path:
        p = self.root_dir / ".cursorrules"
        p.write_text(CURSOR_RULES, encoding="utf-8")
        return p

    def setup_claude(self) -> Path:
        p = self.root_dir / "CLAUDE.md"
        p.write_text(CLAUDE_INSTRUCTION, encoding="utf-8")
        return p

    def setup_agents(self) -> List[Path]:
        files = []
        for name in ("AGENTS.md", "GEMINI.md"):
            p = self.root_dir / name
            p.write_text(AGENTS_INSTRUCTION, encoding="utf-8")
            files.append(p)
        return files


class GlobalAdapterManager:
    """Installs ReduceToken skills and rules globally across all major AI coding agents."""
    def __init__(self, home_dir: Optional[Path] = None):
        self.home = Path(home_dir) if home_dir else Path.home()
        self.pkg_root = Path(__file__).resolve().parent.parent

    def get_plugin_dir(self) -> Path:
        for cand in (
            self.pkg_root / "plugins" / "reduce-token",
            self.pkg_root / "plugin",
        ):
            if (cand / "plugin.json").is_file():
                return cand
        return self.pkg_root / "plugins" / "reduce-token"

    def get_skill_content(self) -> str:
        plugin_dir = self.get_plugin_dir()
        skill_p = plugin_dir / "skills" / "reduce-token" / "SKILL.md"
        if skill_p.is_file():
            return skill_p.read_text(encoding="utf-8")
        local_p = self.pkg_root / ".agents" / "skills" / "reduce-token" / "SKILL.md"
        if local_p.is_file():
            return local_p.read_text(encoding="utf-8")
        return ""

    def detect_environments(self) -> Dict[str, Dict]:
        """Detects which AI tools/environments are installed or present on this machine."""
        return {
            "gemini": {
                "name": "Google Antigravity & Gemini CLI",
                "detected": (self.home / ".gemini").is_dir(),
                "path": str(self.home / ".gemini" / "config" / "plugins" / "reduce-token"),
            },
            "cursor": {
                "name": "Cursor IDE (Global MCP)",
                "detected": (self.home / ".cursor").is_dir() or (self.home / ".cursorrules").is_file(),
                "path": str(self.home / ".cursor" / "mcp.json"),
            },
            "claude": {
                "name": "Claude Code",
                "detected": (self.home / ".claude").is_dir(),
                "path": str(self.home / ".claude" / "skills" / "reduce-token"),
            },
            "opencode": {
                "name": "OpenCode",
                "detected": (self.home / ".config" / "opencode").is_dir(),
                "path": str(self.home / ".config" / "opencode" / "skills" / "reduce-token"),
            },
            "agents": {
                "name": "Agent Skills Standard (Codex / Universal)",
                "detected": (self.home / ".agents").is_dir() or (self.home / ".codex").is_dir(),
                "path": str(self.home / ".agents" / "skills" / "reduce-token"),
            },
        }

    def copy_skill_bundle(self, dest_skill_dir: Path):
        """Copies SKILL.md and references/ directory to the destination."""
        import shutil
        dest_skill_dir.mkdir(parents=True, exist_ok=True)
        plugin_skill_dir = self.get_plugin_dir() / "skills" / "reduce-token"
        if not (plugin_skill_dir / "SKILL.md").is_file():
            plugin_skill_dir = self.pkg_root / ".agents" / "skills" / "reduce-token"

        if plugin_skill_dir.is_dir():
            shutil.copytree(plugin_skill_dir, dest_skill_dir, dirs_exist_ok=True)
        else:
            (dest_skill_dir / "SKILL.md").write_text(self.get_skill_content(), encoding="utf-8")

    def setup_gemini(self) -> str:
        target = self.home / ".gemini" / "config" / "plugins" / "reduce-token"
        (target / "rules").mkdir(parents=True, exist_ok=True)
        plugin_json = self.get_plugin_dir() / "plugin.json"
        if plugin_json.is_file():
            (target / "plugin.json").write_text(plugin_json.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            default_manifest = {"name": "reduce-token", "displayName": "ReduceToken", "version": "1.0.0"}
            (target / "plugin.json").write_text(json.dumps(default_manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        self.copy_skill_bundle(target / "skills" / "reduce-token")
        (target / "rules" / "AGENTS.md").write_text(AGENTS_INSTRUCTION, encoding="utf-8")
        mcp_conf = self.get_plugin_dir() / "mcp_config.json"
        if mcp_conf.is_file():
            (target / "mcp_config.json").write_text(mcp_conf.read_text(encoding="utf-8"), encoding="utf-8")
        return str(target)

    def setup_cursor(self) -> str:
        target = self.home / ".cursor"
        target.mkdir(parents=True, exist_ok=True)
        mcp_file = target / "mcp.json"
        mcp_conf = {}
        if mcp_file.is_file():
            try:
                mcp_conf = json.loads(mcp_file.read_text(encoding="utf-8"))
            except Exception:
                mcp_conf = {}
        if "mcpServers" not in mcp_conf:
            mcp_conf["mcpServers"] = {}
        mcp_conf["mcpServers"]["reducetoken"] = {
            "command": "python",
            "args": ["-m", "reducetoken.cli", "mcp"]
        }
        mcp_file.write_text(json.dumps(mcp_conf, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(mcp_file)

    def setup_claude(self) -> str:
        target = self.home / ".claude"
        skill_dir = target / "skills" / "reduce-token"
        self.copy_skill_bundle(skill_dir)
        claude_md = target / "CLAUDE.md"
        if not claude_md.is_file():
            claude_md.write_text(CLAUDE_INSTRUCTION, encoding="utf-8")
        return str(skill_dir)

    def setup_opencode(self) -> str:
        target = self.home / ".config" / "opencode"
        skill_dir = target / "skills" / "reduce-token"
        self.copy_skill_bundle(skill_dir)
        conf_file = target / "opencode.json"
        conf = {}
        if conf_file.is_file():
            try:
                conf = json.loads(conf_file.read_text(encoding="utf-8"))
            except Exception:
                conf = {}
        if "mcp" not in conf:
            conf["mcp"] = {}
        conf["mcp"]["reducetoken"] = {
            "type": "local",
            "command": "python",
            "args": ["-m", "reducetoken.cli", "mcp"],
            "enabled": True
        }
        conf_file.write_text(json.dumps(conf, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(skill_dir)

    def setup_agents_standard(self) -> str:
        target = self.home / ".agents"
        skill_dir = target / "skills" / "reduce-token"
        rules_dir = target / "rules"
        rules_dir.mkdir(parents=True, exist_ok=True)
        self.copy_skill_bundle(skill_dir)
        (rules_dir / "token-saver.md").write_text(AGENTS_INSTRUCTION, encoding="utf-8")
        return str(skill_dir)

    def setup_all_global(self) -> Dict[str, str]:
        results = {}
        try:
            results["Google Antigravity"] = self.setup_gemini()
        except Exception as e:
            results["Google Antigravity"] = f"Failed: {e}"

        try:
            results["Agent Skills Standard (Codex)"] = self.setup_agents_standard()
        except Exception as e:
            results["Agent Skills Standard"] = f"Failed: {e}"

        try:
            results["Claude Code"] = self.setup_claude()
        except Exception as e:
            results["Claude Code"] = f"Failed: {e}"

        try:
            results["OpenCode"] = self.setup_opencode()
        except Exception as e:
            results["OpenCode"] = f"Failed: {e}"

        try:
            results["Cursor IDE (Global MCP)"] = self.setup_cursor()
        except Exception as e:
            results["Cursor IDE"] = f"Failed: {e}"

        return results
