import os
import re
from pathlib import Path
from typing import List, Set, Optional, Dict

# Directories that should always be ignored
DEFAULT_IGNORE_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "venv", ".venv", "env", ".env",
    "dist", "build", "__pycache__", ".pytest_cache", ".codegraph", ".idea",
    ".vscode", ".next", ".nuxt", "out", "coverage", ".tox", ".mypy_cache",
    ".ruff_cache", "target", "bin", "obj", ".gradle", "vendor"
}

# File names that are lockfiles or machine-generated data
DEFAULT_IGNORE_FILES = {
    "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "cargo.lock",
    "poetry.lock", "gemfile.lock", "composer.lock", "mix.lock",
    ".ds_store", "thumbs.db"
}

# Binary and non-code extensions to skip
IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov",
    ".zip", ".tar", ".gz", ".7z", ".rar", ".bz2",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".exe", ".dll", ".so", ".dylib", ".wasm", ".bin",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".pyc", ".pyo", ".pyd", ".class",
    ".map", ".min.js", ".min.css", ".log", ".db", ".sqlite"
}

# Supported code extensions and their language labels
EXT_TO_LANG = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c_header",
    ".hpp": "cpp_header",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell"
}


class FileScanner:
    def __init__(self, root_dir: Path, custom_ignore_patterns: Optional[List[str]] = None):
        self.root_dir = Path(root_dir).resolve()
        self.ignore_patterns: List[re.Pattern] = []
        self._load_ignore_files(custom_ignore_patterns)

    def _load_ignore_files(self, custom_patterns: Optional[List[str]] = None):
        patterns = []
        
        # Load .gitignore if present
        gitignore_path = self.root_dir / ".gitignore"
        if gitignore_path.is_file():
            patterns.extend(self._parse_ignore_file(gitignore_path))

        # Load .codegraphignore if present
        codegraph_ignore_path = self.root_dir / ".codegraphignore"
        if codegraph_ignore_path.is_file():
            patterns.extend(self._parse_ignore_file(codegraph_ignore_path))

        if custom_patterns:
            patterns.extend(custom_patterns)

        for pat in patterns:
            pat = pat.strip()
            if not pat or pat.startswith("#"):
                continue
            # Simple glob to regex translation
            regex_str = pat.replace(".", r"\.").replace("*", ".*").replace("?", ".")
            if regex_str.endswith("/"):
                regex_str += ".*"
            try:
                self.ignore_patterns.append(re.compile(regex_str, re.IGNORECASE))
            except re.error:
                pass

    @staticmethod
    def _parse_ignore_file(file_path: Path) -> List[str]:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return [line.strip() for line in f if line.strip() and not line.startswith("#")]
        except Exception:
            return []

    def should_ignore(self, rel_path: Path, is_dir: bool = False) -> bool:
        parts = rel_path.parts
        name = rel_path.name.lower()

        # Check default ignore dirs
        for part in parts:
            p_lower = part.lower()
            if p_lower in DEFAULT_IGNORE_DIRS or p_lower.endswith(".egg-info"):
                return True

        if is_dir:
            return False

        # Check lockfiles & common ignore files
        if name in DEFAULT_IGNORE_FILES:
            return True

        # Check extensions
        ext = rel_path.suffix.lower()
        if ext in IGNORE_EXTENSIONS:
            return True

        if name.endswith(".min.js") or name.endswith(".min.css") or name.endswith(".bundle.js"):
            return True

        # Check regex patterns
        rel_str = str(rel_path).replace("\\", "/")
        for pattern in self.ignore_patterns:
            if pattern.search(rel_str) or pattern.search(name):
                return True

        return False

    def is_minified_or_binary(self, full_path: Path) -> bool:
        """Check if file has extremely long lines (>1000 chars) or binary bytes."""
        try:
            with open(full_path, "rb") as f:
                chunk = f.read(4096)
                if b"\x00" in chunk:
                    return True
                # Check for long lines in first lines
                lines = chunk.split(b"\n")
                for line in lines[:10]:
                    if len(line) > 1000:
                        return True
        except Exception:
            return True
        return False

    def scan(self) -> List[Dict[str, str]]:
        """
        Scan workspace and return a list of file dicts:
        [{'path': 'relative/path', 'full_path': '...', 'lang': 'python', 'ext': '.py'}]
        """
        results = []
        for root, dirs, files in os.walk(self.root_dir):
            rel_root = Path(root).relative_to(self.root_dir)
            
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if not self.should_ignore(rel_root / d, is_dir=True)]

            for file_name in files:
                rel_path = rel_root / file_name
                if self.should_ignore(rel_path, is_dir=False):
                    continue

                full_path = Path(root) / file_name
                ext = rel_path.suffix.lower()
                lang = EXT_TO_LANG.get(ext, "unknown")

                # Skip files larger than 1.5MB to save memory and tokens
                try:
                    if full_path.stat().st_size > 1.5 * 1024 * 1024:
                        continue
                except OSError:
                    continue

                if self.is_minified_or_binary(full_path):
                    continue

                results.append({
                    "path": str(rel_path).replace("\\", "/"),
                    "full_path": str(full_path),
                    "lang": lang,
                    "ext": ext
                })

        return results
