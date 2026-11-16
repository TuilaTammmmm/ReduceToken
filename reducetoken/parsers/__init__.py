from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class SymbolInfo:
    name: str
    kind: str  # 'function', 'class', 'method', 'variable', 'interface', 'struct'
    line: int
    doc: str = ""
    args: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)

@dataclass
class ImportInfo:
    source: str          # e.g., 'express', './utils/jwt', 'reducetoken.scanner'
    symbols: List[str]   # e.g., ['Request', 'Response'] or ['*']
    is_relative: bool = False

@dataclass
class FileAnalysis:
    file_path: str
    language: str
    imports: List[ImportInfo] = field(default_factory=list)
    symbols: List[SymbolInfo] = field(default_factory=list)
    calls: List[str] = field(default_factory=list)
    exports: List[str] = field(default_factory=list)
    summary: str = ""
