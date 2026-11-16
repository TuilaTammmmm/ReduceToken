import json
from pathlib import Path
from typing import Dict, Any, List
from reducetoken.graph import CodeGraph

META_RULE_NAMES = {
    ".cursorrules", ".gitignore", "agents.md", "claude.md", "gemini.md",
    "readme.md", ".codegraphignore", "license", "license.md"
}


class Generator:
    def __init__(self, root_dir: Path, graph: CodeGraph):
        self.root_dir = Path(root_dir)
        self.graph = graph
        self.output_dir = self.root_dir / ".codegraph"

    def generate_all(self):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.write_architecture_map()
        self.write_graph_json()
        self.write_symbols_json()

    @staticmethod
    def _get_top_symbols(analysis) -> List[str]:
        if not analysis or not analysis.symbols:
            return []

        # 1. Classes, Interfaces, Structs (highest priority)
        major = [s.name for s in analysis.symbols if s.kind in ("class", "interface", "struct")]
        
        # 2. Exported symbols
        exported = [e for e in analysis.exports if e not in major]

        # 3. Regular functions
        funcs = [s.name for s in analysis.symbols if s.name not in major and s.name not in exported]

        ordered = major + exported + funcs
        return ordered[:4]

    def write_architecture_map(self) -> Path:
        stats = self.graph.get_overview_stats()
        out_file = self.output_dir / "architecture_map.md"

        # Group files by top-level directory
        dir_clusters: Dict[str, List[str]] = {}
        for f in sorted(self.graph.all_files):
            parts = Path(f).parts
            top_dir = parts[0] if len(parts) > 1 else "(root)"
            if top_dir not in dir_clusters:
                dir_clusters[top_dir] = []
            dir_clusters[top_dir].append(f)

        lines = [
            "# Architecture Map & Dependency Network",
            "> **AI Token-Saving Notice**: This repository is indexed by ReduceToken. "
            "Do NOT scan the full folder. Consult this map or run `rt query <symbol>` (or `reducetoken query`) to find exact code paths.\n",
            "## 1. Quick Stats",
            f"- **Indexed Files**: {stats['total_files']}",
            f"- **Indexed Symbols**: {stats['total_symbols']}"
        ]

        if stats["entry_points"]:
            lines.append(f"- **Entry Points**: {', '.join(stats['entry_points'])}")

        if stats["core_modules"]:
            core_str = ", ".join([f"`{m['file']}` ({m['dependent_count']} refs)" for m in stats["core_modules"]])
            lines.append(f"- **Core Modules**: {core_str}")

        lines.append("\n## 2. Module Directory Structure")
        for top_dir, files in sorted(dir_clusters.items()):
            # Sort files: code files first, meta/rule files last
            def file_sort_key(file_path: str):
                name_l = Path(file_path).name.lower()
                is_meta = 1 if (name_l in META_RULE_NAMES or name_l.endswith(".md")) else 0
                return (is_meta, file_path.lower())

            sorted_files = sorted(files, key=file_sort_key)
            lines.append(f"### `{top_dir}` ({len(files)} files)")

            # List up to 10 files per cluster
            for f in sorted_files[:10]:
                analysis = self.graph.analyses.get(f)
                symbols_summary = ""
                top_syms = self._get_top_symbols(analysis)
                if top_syms:
                    symbols_summary = f" — defines: `{', '.join(top_syms)}`"
                elif analysis and analysis.summary:
                    symbols_summary = f" — {analysis.summary[:60]}"
                lines.append(f"- `{f}`{symbols_summary}")

            if len(files) > 10:
                lines.append(f"- *(+{len(files) - 10} more files)*")

        lines.append("\n## 3. How to Query")
        lines.append("- Find where a symbol/function is: `rt query <symbol_name>` (or `reducetoken query`)")
        lines.append("- Find callers/dependencies of a file: `rt query <file_path>`")
        lines.append("- Force refresh graph if needed: `rt update`")

        content = "\n".join(lines) + "\n"
        with open(out_file, "w", encoding="utf-8") as f:
            f.write(content)
        return out_file

    def write_graph_json(self) -> Path:
        out_file = self.output_dir / "graph.json"
        data = self.graph.to_dict()
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return out_file

    def write_symbols_json(self) -> Path:
        out_file = self.output_dir / "symbols.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(self.graph.symbol_index, f, indent=2)
        return out_file

    @staticmethod
    def format_agent_dsl(query_result: Dict[str, Any]) -> str:
        """Format subgraph query result as ultra-compact text (~50-80 tokens)."""
        target = query_result.get("target_file")
        if not target:
            return (
                f"=== REDUCETOKEN QUERY RESULT ===\n"
                f"No exact match found for '{query_result.get('query')}'.\n"
                f"Matched files: {', '.join(query_result.get('matched_files', [])[:5]) or 'none'}\n"
                f"================================"
            )

        lines = [
            "=== REDUCETOKEN SUBGRAPH (Compact Context) ===",
            f"TARGET FILE: {target}"
        ]

        if query_result.get("summary"):
            lines.append(f"SUMMARY: {query_result['summary']}")

        # Symbols: prioritize class then funcs
        syms = query_result.get("symbols_in_target", [])
        if syms:
            # Sort class first
            syms_sorted = sorted(syms, key=lambda s: 0 if s.get("kind") in ("class", "interface") else 1)
            sym_strs = [f"{s['kind']} {s['name']}() [L{s['line']}]" for s in syms_sorted[:6]]
            lines.append(f"DEFINES: {', '.join(sym_strs)}")

        # Dependencies (imports)
        deps = query_result.get("dependencies", [])
        if deps:
            lines.append(f"IMPORTS ({len(deps)}): {', '.join(deps[:6])}")
        else:
            lines.append("IMPORTS: (none / external only)")

        # Dependents (callers / imported by)
        rev_deps = query_result.get("dependents", [])
        if rev_deps:
            lines.append(f"IMPORTED BY ({len(rev_deps)}): {', '.join(rev_deps[:6])}")
        else:
            lines.append("IMPORTED BY: (none / entry point)")

        lines.append(f"RECOMMENDED ACTION: Read only '{target}'. Do NOT read entire directory.")
        lines.append("==============================================")
        return "\n".join(lines)
