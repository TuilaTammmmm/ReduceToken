import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from collections import defaultdict
from reducetoken.parsers import FileAnalysis


class CodeGraph:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.analyses: Dict[str, FileAnalysis] = {}
        # file_path -> set of file_paths it imports
        self.file_dependencies: Dict[str, Set[str]] = defaultdict(set)
        # file_path -> set of file_paths that import it
        self.file_dependents: Dict[str, Set[str]] = defaultdict(set)
        # symbol_name -> list of definitions
        self.symbol_index: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # file_path -> list of symbols defined
        self.file_symbols: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # All known file paths in the graph
        self.all_files: Set[str] = set()
        # Path alias mappings: (alias_prefix, target_prefix)
        self.path_aliases: List[tuple] = []
        self._load_path_aliases()

    def _load_path_aliases(self):
        """Loads tsconfig/jsconfig paths and monorepo workspace packages to resolve virtual imports."""
        self.path_aliases = []

        # 1. Check tsconfig.json / jsconfig.json
        for conf_name in ("tsconfig.json", "jsconfig.json"):
            conf_path = self.root_dir / conf_name
            if conf_path.is_file():
                try:
                    text = conf_path.read_text(encoding="utf-8", errors="ignore")
                    lines = [l for l in text.splitlines() if not l.strip().startswith("//")]
                    data = json.loads("\n".join(lines))
                    co = data.get("compilerOptions", {})
                    base_url = co.get("baseUrl", ".").rstrip("/\\")
                    paths = co.get("paths", {})
                    for alias, targets in paths.items():
                        if targets and isinstance(targets, list):
                            target = targets[0]
                            alias_prefix = alias.rstrip("*")
                            target_prefix = target.rstrip("*")
                            if base_url and base_url != ".":
                                target_prefix = f"{base_url}/{target_prefix}".lstrip("./")
                            self.path_aliases.append((alias_prefix, target_prefix))
                except Exception:
                    pass

        # 2. Check monorepo packages (packages/*/package.json, apps/*/package.json)
        for cand_dir in ("packages", "apps", "modules"):
            p_dir = self.root_dir / cand_dir
            if p_dir.is_dir():
                try:
                    for sub in p_dir.iterdir():
                        if sub.is_dir():
                            pkg_json = sub / "package.json"
                            if pkg_json.is_file():
                                pkg_data = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
                                pkg_name = pkg_data.get("name")
                                if pkg_name:
                                    rel_sub = f"{cand_dir}/{sub.name}"
                                    self.path_aliases.append((pkg_name, rel_sub))
                except Exception:
                    pass

    def add_analysis(self, rel_path: str, analysis: FileAnalysis):
        self.analyses[rel_path] = analysis
        self.all_files.add(rel_path)

    def build(self):
        """Build edges, resolve dependencies, and index symbols."""
        self.file_dependencies.clear()
        self.file_dependents.clear()
        self.symbol_index.clear()
        self.file_symbols.clear()

        # 1. Index all defined symbols
        for rel_path, analysis in self.analyses.items():
            for sym in analysis.symbols:
                sym_entry = {
                    "name": sym.name,
                    "kind": sym.kind,
                    "file": rel_path,
                    "line": sym.line,
                    "doc": sym.doc,
                    "args": sym.args,
                    "methods": sym.methods
                }
                self.symbol_index[sym.name.lower()].append(sym_entry)
                self.file_symbols[rel_path].append(sym_entry)

        # 2. Resolve imports and build dependency edges
        for rel_path, analysis in self.analyses.items():
            curr_dir = Path(rel_path).parent

            for imp in analysis.imports:
                resolved_target = self._resolve_import(rel_path, imp.source, imp.is_relative)
                if resolved_target and resolved_target in self.all_files:
                    if resolved_target != rel_path:
                        self.file_dependencies[rel_path].add(resolved_target)
                        self.file_dependents[resolved_target].add(rel_path)

    def _resolve_import(self, from_file: str, source: str, is_relative: bool) -> Optional[str]:
        """Try to resolve import source to an existing file in the graph."""
        if not source:
            return None

        from_dir = Path(from_file).parent
        possible_targets = []

        # Relative import resolution (JS/TS ./module or Python .module)
        if is_relative or source.startswith("."):
            clean_source = source.lstrip("./").lstrip(".\\")
            base_cand = (from_dir / source).resolve()
            try:
                rel_cand = base_cand.relative_to(self.root_dir)
                cand_str = str(rel_cand).replace("\\", "/")
                possible_targets.append(cand_str)
            except ValueError:
                pass

        # Check path aliases (tsconfig @/*, monorepo packages)
        for alias_pfx, target_pfx in self.path_aliases:
            if source.startswith(alias_pfx):
                resolved_sub = source.replace(alias_pfx, target_pfx, 1).lstrip("./\\")
                possible_targets.append(resolved_sub)

        # Python dot module: reducetoken.scanner -> reducetoken/scanner
        py_path = source.replace(".", "/")
        possible_targets.append(py_path)
        possible_targets.append(source)

        extensions = ["", ".py", ".ts", ".js", ".tsx", ".jsx", "/index.ts", "/index.js", "/__init__.py"]

        for cand in possible_targets:
            cand_norm = cand.replace("\\", "/")
            for ext in extensions:
                test_path = f"{cand_norm}{ext}"
                if test_path in self.all_files:
                    return test_path

        return None

    def query(self, query_str: str) -> Dict[str, Any]:
        """
        Query the graph by symbol, keyword, or file path.
        Returns a compact subgraph structure.
        """
        q = query_str.strip().lower()
        matched_symbols = []
        matched_files = []

        # Exact or partial symbol matches
        for sym_name, defs in self.symbol_index.items():
            if q == sym_name:
                matched_symbols.extend(defs)
            elif q in sym_name and len(matched_symbols) < 10:
                matched_symbols.extend(defs)

        # File matches
        for f in self.all_files:
            if q in f.lower():
                matched_files.append(f)

        # Determine target primary file
        target_file = None
        if matched_symbols:
            target_file = matched_symbols[0]["file"]
        elif matched_files:
            target_file = matched_files[0]

        dependencies = list(self.file_dependencies.get(target_file, [])) if target_file else []
        dependents = list(self.file_dependents.get(target_file, [])) if target_file else []
        symbols_in_file = self.file_symbols.get(target_file, []) if target_file else []
        analysis = self.analyses.get(target_file) if target_file else None

        return {
            "query": query_str,
            "target_file": target_file,
            "matched_symbols": matched_symbols[:5],
            "matched_files": matched_files[:5],
            "dependencies": dependencies,
            "dependents": dependents,
            "symbols_in_target": symbols_in_file,
            "summary": analysis.summary if analysis else "",
            "exports": analysis.exports if analysis else []
        }

    def get_overview_stats(self) -> Dict[str, Any]:
        """Rank central files and entry points for the high-level architecture map."""
        # Central files = highest dependents (most imported by others)
        sorted_by_dependents = sorted(
            self.file_dependents.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        core_modules = [
            {"file": f, "dependent_count": len(deps)}
            for f, deps in sorted_by_dependents[:8] if len(deps) > 0
        ]

        # Entry points = files with common entry names or high dependencies but 0 dependents
        entry_points = []
        for f in sorted(self.all_files):
            name_lower = Path(f).name.lower()
            if any(name_lower.startswith(ep) for ep in ("main.", "index.", "app.", "server.", "cli.", "manage.")):
                entry_points.append(f)

        return {
            "total_files": len(self.all_files),
            "total_symbols": sum(len(defs) for defs in self.symbol_index.values()),
            "entry_points": entry_points[:6],
            "core_modules": core_modules
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize full graph."""
        nodes = []
        for f in sorted(self.all_files):
            analysis = self.analyses.get(f)
            nodes.append({
                "id": f,
                "type": "file",
                "language": analysis.language if analysis else "unknown",
                "summary": analysis.summary if analysis else "",
                "symbols_count": len(self.file_symbols.get(f, [])),
                "exports": analysis.exports if analysis else []
            })

        edges = []
        for src, targets in self.file_dependencies.items():
            for tgt in targets:
                edges.append({"source": src, "target": tgt, "relation": "imports"})

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": self.get_overview_stats()
        }
