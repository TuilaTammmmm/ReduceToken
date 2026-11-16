import hashlib
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo


def calculate_sha256(full_path: Path) -> str:
    sha = hashlib.sha256()
    try:
        with open(full_path, "rb") as f:
            while chunk := f.read(65536):
                sha.update(chunk)
        return sha.hexdigest()
    except Exception:
        return ""


def analysis_to_dict(analysis: FileAnalysis) -> Dict[str, Any]:
    return {
        "file_path": analysis.file_path,
        "language": analysis.language,
        "summary": analysis.summary,
        "exports": analysis.exports,
        "calls": analysis.calls,
        "imports": [
            {"source": imp.source, "symbols": imp.symbols, "is_relative": imp.is_relative}
            for imp in analysis.imports
        ],
        "symbols": [
            {
                "name": sym.name,
                "kind": sym.kind,
                "line": sym.line,
                "doc": sym.doc,
                "args": sym.args,
                "methods": sym.methods
            }
            for sym in analysis.symbols
        ]
    }


def dict_to_analysis(d: Dict[str, Any]) -> FileAnalysis:
    imports = [
        ImportInfo(
            source=i["source"],
            symbols=i.get("symbols", []),
            is_relative=i.get("is_relative", False)
        )
        for i in d.get("imports", [])
    ]
    symbols = [
        SymbolInfo(
            name=s["name"],
            kind=s["kind"],
            line=s.get("line", 1),
            doc=s.get("doc", ""),
            args=s.get("args", []),
            methods=s.get("methods", [])
        )
        for s in d.get("symbols", [])
    ]
    return FileAnalysis(
        file_path=d["file_path"],
        language=d.get("language", "unknown"),
        imports=imports,
        symbols=symbols,
        calls=d.get("calls", []),
        exports=d.get("exports", []),
        summary=d.get("summary", "")
    )


class CacheManager:
    def __init__(self, cache_file: Path):
        self.cache_file = Path(cache_file)
        self.cache_data: Dict[str, Dict[str, Any]] = {}
        self.load()

    def load(self):
        if self.cache_file.is_file():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache_data = json.load(f)
            except Exception:
                self.cache_data = {}

    def save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, indent=2)
        except Exception:
            pass

    def get_analysis(self, rel_path: str) -> Optional[FileAnalysis]:
        entry = self.cache_data.get(rel_path)
        if entry and "analysis" in entry:
            return dict_to_analysis(entry["analysis"])
        return None

    def is_cached_and_valid(self, rel_path: str, full_path: Path) -> bool:
        if rel_path.startswith("_"):
            return False
        entry = self.cache_data.get(rel_path)
        if not entry or not isinstance(entry, dict):
            return False

        try:
            stat = full_path.stat()
            # Fast mtime & size check
            if stat.st_mtime == entry.get("mtime") and stat.st_size == entry.get("size"):
                return True

            # If mtime or size differs, verify hash
            current_hash = calculate_sha256(full_path)
            if current_hash and current_hash == entry.get("hash"):
                # Update mtime and size in cache without reparsing
                entry["mtime"] = stat.st_mtime
                entry["size"] = stat.st_size
                return True
        except OSError:
            return False

        return False

    def update_entry(self, rel_path: str, full_path: Path, analysis: FileAnalysis):
        try:
            stat = full_path.stat()
            file_hash = calculate_sha256(full_path)
            self.cache_data[rel_path] = {
                "mtime": stat.st_mtime,
                "size": stat.st_size,
                "hash": file_hash,
                "analysis": analysis_to_dict(analysis)
            }
        except OSError:
            pass

    @staticmethod
    def get_git_head(root_dir: Path) -> Optional[str]:
        """Fast read of .git/HEAD to detect branch switches, merges, or checkouts (<0.2ms)."""
        head_file = root_dir / ".git" / "HEAD"
        if not head_file.is_file():
            return None
        try:
            head_content = head_file.read_text(encoding="utf-8", errors="ignore").strip()
            if head_content.startswith("ref:"):
                ref_rel = head_content[4:].strip()
                ref_file = root_dir / ".git" / ref_rel
                if ref_file.is_file():
                    return f"{ref_rel}:{ref_file.read_text(encoding='utf-8', errors='ignore').strip()[:8]}"
                return ref_rel
            return head_content[:8]
        except Exception:
            return None

    def check_and_update_git_head(self, root_dir: Path) -> bool:
        """Returns True if Git HEAD has changed since last cache write."""
        current_head = self.get_git_head(root_dir)
        if not current_head:
            return False
        cached_head = self.cache_data.get("_git_head")
        if cached_head != current_head:
            self.cache_data["_git_head"] = current_head
            return True
        return False

    def remove_missing(self, valid_rel_paths: set):
        to_remove = [k for k in self.cache_data if not k.startswith("_") and k not in valid_rel_paths]
        for k in to_remove:
            del self.cache_data[k]
