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
- **Targeted Lookup & Fast Reading**:
  * Run `rt query <keyword_or_symbol>` (or MCP `query_code_graph`) to get the exact subgraph (`TARGET FILE`, line numbers `[Lxx]`, dependencies, callers).
  * **Line-Bound Reading**: Use `read_file(Path, StartLine, EndLine)` to read ONLY the target 20-50 lines around `[Lxx]`. NEVER read the entire file if you only need one function or class.
- **Import Aliases & Monorepo**: When navigating virtual aliases (`@/*`, `~/*`, `workspace:*`), inspect `tsconfig.json` (`paths`) or `package.json` workspaces to resolve real paths instead of full-directory searches.
- **Zero Full-Scan**: Never run commands that list or read all files across the repository (`ls -R`, `find`, recursive glob).
- **Autonomous Silent Maintenance (Zero User Effort)**:
  * Do NOT spam `rt update` after every micro-edit. Delta sync runs automatically on next query or commit.
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

    def is_global_active(self) -> bool:
        """Check if ReduceToken plugin is already installed globally."""
        home = Path.home()
        candidates = [
            home / ".gemini" / "config" / "plugins" / "reduce-token",
            home / ".agents" / "skills" / "reduce-token",
            home / ".config" / "opencode" / "skills" / "reduce-token",
        ]
        return any(c.is_dir() for c in candidates)

    def setup_copilot(self) -> Path:
        p = self.root_dir / ".github" / "copilot-instructions.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(COPILOT_INSTRUCTION, encoding="utf-8")
        return p

    def setup_cursor(self, modern: bool = True) -> Path:
        if modern:
            rules_dir = self.root_dir / ".cursor" / "rules"
            rules_dir.mkdir(parents=True, exist_ok=True)
            p = rules_dir / "token-saver.mdc"
            p.write_text(CURSOR_RULES, encoding="utf-8")
            return p
        else:
            p = self.root_dir / ".cursorrules"
            p.write_text(CURSOR_RULES, encoding="utf-8")
            return p

    def setup_claude(self) -> Path:
        p = self.root_dir / "CLAUDE.md"
        p.write_text(CLAUDE_INSTRUCTION, encoding="utf-8")
        return p

    def setup_agents(self, hidden_only: bool = True) -> List[Path]:
        files = []
        if hidden_only:
            # Clean standard: store in hidden .agents/rules/
            p = self.root_dir / ".agents" / "rules" / "token-saver.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(AGENTS_INSTRUCTION, encoding="utf-8")
            files.append(p)
        else:
            for name in ("AGENTS.md", "GEMINI.md"):
                p = self.root_dir / name
                p.write_text(AGENTS_INSTRUCTION, encoding="utf-8")
                files.append(p)
        return files

    def setup_all(self, modern: bool = True, root_rules: bool = False) -> List[Path]:
        created = [
            self.setup_copilot(),
            self.setup_cursor(modern=modern and not root_rules),
            self.setup_claude(),
        ]
        created.extend(self.setup_agents(hidden_only=not root_rules))
        return created

    def setup_by_agent(self, agent: str, root_rules: bool = False) -> List[Path]:
        """Set up instructions for specific agent or all."""
        agent = agent.lower().strip()
        created = []
        if agent in ("none", "clean"):
            return created
        if agent == "all":
            return self.setup_all(modern=not root_rules, root_rules=root_rules)
        if agent in ("antigravity", "gemini", "opencode", "agents"):
            created.extend(self.setup_agents(hidden_only=not root_rules))
        elif agent == "cursor":
            created.append(self.setup_cursor(modern=not root_rules))
        elif agent == "claude":
            created.append(self.setup_claude())
        elif agent == "copilot":
            created.append(self.setup_copilot())
        return created


class GlobalAdapterManager:
    """Installs ReduceToken skills and rules globally across all major AI coding agents."""
    ALIAS_MAP = {
        "antigravity": "gemini",
        "gemini": "gemini",
        "cursor": "cursor",
        "claude": "claude",
        "claudecode": "claude",
        "opencode": "opencode",
        "agents": "agents",
        "codex": "agents",
        "universal": "agents",
    }

    def __init__(self, home_dir: Optional[Path] = None):
        self.home = Path(home_dir) if home_dir else Path.home()
        self.pkg_root = Path(__file__).resolve().parent.parent
        self.config_dir = self.home / ".reducetoken"
        self.config_file = self.config_dir / "config.json"

    def normalize_name(self, name: str) -> str:
        cleaned = name.lower().strip()
        return self.ALIAS_MAP.get(cleaned, cleaned)

    def get_config(self) -> Dict:
        if self.config_file.is_file():
            try:
                return json.loads(self.config_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"enabled_adapters": {"gemini": True, "cursor": True, "claude": True, "opencode": True, "agents": True}}

    def save_config(self, cfg: Dict):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    def is_adapter_enabled(self, key: str) -> bool:
        canonical = self.normalize_name(key)
        cfg = self.get_config()
        enabled = cfg.get("enabled_adapters", {})
        return enabled.get(canonical, True)

    def set_adapter_status(self, key: str, enabled: bool):
        canonical = self.normalize_name(key)
        cfg = self.get_config()
        if "enabled_adapters" not in cfg:
            cfg["enabled_adapters"] = {}
        cfg["enabled_adapters"][canonical] = enabled
        self.save_config(cfg)

    def uninstall_adapter(self, key: str) -> str:
        import shutil
        canonical = self.normalize_name(key)
        self.set_adapter_status(canonical, False)
        if canonical == "gemini":
            target = self.home / ".gemini" / "config" / "plugins" / "reduce-token"
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                return f"Removed {target}"
        elif canonical == "cursor":
            mcp_file = self.home / ".cursor" / "mcp.json"
            if mcp_file.is_file():
                try:
                    data = json.loads(mcp_file.read_text(encoding="utf-8"))
                    if "mcpServers" in data and "reducetoken" in data["mcpServers"]:
                        del data["mcpServers"]["reducetoken"]
                        mcp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                        return f"Removed reducetoken entry from {mcp_file}"
                except Exception:
                    pass
        elif canonical == "claude":
            target = self.home / ".claude" / "skills" / "reduce-token"
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                return f"Removed {target}"
        elif canonical == "opencode":
            target = self.home / ".config" / "opencode" / "skills" / "reduce-token"
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
            conf_file = self.home / ".config" / "opencode" / "opencode.json"
            if conf_file.is_file():
                try:
                    data = json.loads(conf_file.read_text(encoding="utf-8"))
                    if "mcp" in data and "reducetoken" in data["mcp"]:
                        del data["mcp"]["reducetoken"]
                        conf_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                except Exception:
                    pass
            return "Removed OpenCode skills and MCP configuration"
        elif canonical == "agents":
            target = self.home / ".agents" / "skills" / "reduce-token"
            if target.is_dir():
                shutil.rmtree(target, ignore_errors=True)
                return f"Removed {target}"
        return f"Disabled {canonical}"

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
        cfg = self.get_config().get("enabled_adapters", {})
        return {
            "gemini": {
                "name": "Google Antigravity & Gemini CLI",
                "detected": (self.home / ".gemini").is_dir(),
                "enabled": cfg.get("gemini", True),
                "path": str(self.home / ".gemini" / "config" / "plugins" / "reduce-token"),
            },
            "cursor": {
                "name": "Cursor IDE (Global MCP)",
                "detected": (self.home / ".cursor").is_dir() or (self.home / ".cursorrules").is_file(),
                "enabled": cfg.get("cursor", True),
                "path": str(self.home / ".cursor" / "mcp.json"),
            },
            "claude": {
                "name": "Claude Code",
                "detected": (self.home / ".claude").is_dir(),
                "enabled": cfg.get("claude", True),
                "path": str(self.home / ".claude" / "skills" / "reduce-token"),
            },
            "opencode": {
                "name": "OpenCode",
                "detected": (self.home / ".config" / "opencode").is_dir(),
                "enabled": cfg.get("opencode", True),
                "path": str(self.home / ".config" / "opencode" / "skills" / "reduce-token"),
            },
            "agents": {
                "name": "Agent Skills Standard (Codex / Universal)",
                "detected": (self.home / ".agents").is_dir() or (self.home / ".codex").is_dir(),
                "enabled": cfg.get("agents", True),
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

    def setup_all_global(
        self,
        only: Optional[List[str]] = None,
        skip: Optional[List[str]] = None,
        respect_config: bool = True
    ) -> Dict[str, str]:
        results = {}
        only_set = {self.normalize_name(x) for x in only} if only else None
        skip_set = {self.normalize_name(x) for x in skip} if skip else set()

        adapters = [
            ("gemini", "Google Antigravity", self.setup_gemini),
            ("agents", "Agent Skills Standard (Codex)", self.setup_agents_standard),
            ("claude", "Claude Code", self.setup_claude),
            ("opencode", "OpenCode", self.setup_opencode),
            ("cursor", "Cursor IDE (Global MCP)", self.setup_cursor),
        ]

        for key, display_name, setup_fn in adapters:
            if key in skip_set:
                results[display_name] = "Skipped (--skip flag)"
                continue
            if only_set is not None and key not in only_set:
                results[display_name] = "Skipped (not in --only list)"
                continue
            if respect_config and not self.is_adapter_enabled(key):
                results[display_name] = "Skipped (disabled in config: ~/.reducetoken/config.json)"
                continue

            try:
                path = setup_fn()
                results[display_name] = path
            except Exception as e:
                results[display_name] = f"Failed: {e}"

        return results
