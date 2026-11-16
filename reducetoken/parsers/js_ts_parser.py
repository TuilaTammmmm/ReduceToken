import re
from typing import List
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo

# Regex patterns for ES Module / CommonJS imports
RE_ES_IMPORT = re.compile(
    r"""import\s+(?:(?P<default>[a-zA-Z0-9_$]+)\s*,?\s*)?(?:\{\s*(?P<named>[^}]+)\s*\}|\*\s+as\s+(?P<namespace>[a-zA-Z0-9_$]+))?\s*from\s*['"](?P<source>[^'"]+)['"]""",
    re.MULTILINE
)
RE_BARE_IMPORT = re.compile(r"""import\s+['"](?P<source>[^'"]+)['"]""", re.MULTILINE)
RE_REQUIRE = re.compile(
    r"""(?:const|let|var)\s+(?:\{(?P<named>[^}]+)\}|(?P<default>[a-zA-Z0-9_$]+))\s*=\s*require\(\s*['"](?P<source>[^'"]+)['"]\s*\)""",
    re.MULTILINE
)

# Regex patterns for definitions
RE_CLASS = re.compile(
    r"""(?:export\s+(?:default\s+)?)?class\s+(?P<name>[a-zA-Z0-9_$]+)(?:\s+extends\s+[a-zA-Z0-9_$]+)?\s*\{""",
    re.MULTILINE
)
RE_TS_INTERFACE = re.compile(
    r"""(?:export\s+)?interface\s+(?P<name>[a-zA-Z0-9_$]+)""",
    re.MULTILINE
)
RE_TS_TYPE = re.compile(
    r"""(?:export\s+)?type\s+(?P<name>[a-zA-Z0-9_$]+)\s*=""",
    re.MULTILINE
)
RE_EXPORT_FUNC = re.compile(
    r"""(?:export\s+(?:default\s+)?)?(?:async\s+)?function\s+(?P<name>[a-zA-Z0-9_$]+)\s*\((?P<args>[^)]*)\)""",
    re.MULTILINE
)
RE_ARROW_FUNC = re.compile(
    r"""(?:export\s+)?(?:const|let|var)\s+(?P<name>[a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\((?P<args>[^)]*)\)\s*=>""",
    re.MULTILINE
)
RE_CLASS_METHOD = re.compile(
    r"""^\s+(?:async\s+)?(?P<name>[a-zA-Z0-9_$]+)\s*\((?P<args>[^)]*)\)\s*\{""",
    re.MULTILINE
)
RE_EXPORT_NAMED = re.compile(
    r"""export\s*\{\s*(?P<symbols>[^}]+)\s*\}""",
    re.MULTILINE
)
RE_CALL = re.compile(
    r"""\b(?P<func>[a-zA-Z0-9_$]+)\s*\(""",
    re.MULTILINE
)

JS_KEYWORDS = {
    "if", "else", "for", "while", "do", "switch", "case", "return", "throw",
    "try", "catch", "finally", "new", "typeof", "instanceof", "void", "delete",
    "await", "yield", "super", "import", "export", "require", "function",
    "constructor", "get", "set", "static"
}


def clean_args(args_str: str) -> List[str]:
    """Parse function arguments handling destructuring and default values properly."""
    if not args_str.strip():
        return []
    tokens = []
    current = []
    depth_brace = 0
    depth_bracket = 0
    depth_paren = 0

    for ch in args_str:
        if ch == '{':
            depth_brace += 1
        elif ch == '}':
            depth_brace -= 1
        elif ch == '[':
            depth_bracket += 1
        elif ch == ']':
            depth_bracket -= 1
        elif ch == '(':
            depth_paren += 1
        elif ch == ')':
            depth_paren -= 1
        elif ch == ',' and depth_brace == 0 and depth_bracket == 0 and depth_paren == 0:
            tokens.append("".join(current).strip())
            current = []
            continue
        current.append(ch)

    if current:
        tokens.append("".join(current).strip())

    result = []
    for tok in tokens:
        if not tok:
            continue
        # Split default value
        name_part = tok.split("=")[0].strip()
        # Split TypeScript type annotation
        name_part = name_part.split(":")[0].strip()
        if name_part:
            result.append(name_part)
    return result


def parse_js_ts_file(file_path: str, code: str, language: str = "javascript") -> FileAnalysis:
    analysis = FileAnalysis(file_path=file_path, language=language)
    imports_list: List[ImportInfo] = []
    symbols_list: List[SymbolInfo] = []
    exports_list: List[str] = []
    calls_list: List[str] = []

    # 1. Parse ES imports
    for m in RE_ES_IMPORT.finditer(code):
        src = m.group("source")
        syms = []
        if m.group("default"):
            syms.append(m.group("default").strip())
        if m.group("named"):
            for s in m.group("named").split(","):
                s = s.strip().split(" as ")[-1].strip()
                if s:
                    syms.append(s)
        if m.group("namespace"):
            syms.append(m.group("namespace").strip())
        
        is_rel = src.startswith("./") or src.startswith("../")
        imports_list.append(ImportInfo(source=src, symbols=syms, is_relative=is_rel))

    # Bare imports
    for m in RE_BARE_IMPORT.finditer(code):
        src = m.group("source")
        is_rel = src.startswith("./") or src.startswith("../")
        imports_list.append(ImportInfo(source=src, symbols=[], is_relative=is_rel))

    # CommonJS require
    for m in RE_REQUIRE.finditer(code):
        src = m.group("source")
        syms = []
        if m.group("default"):
            syms.append(m.group("default").strip())
        if m.group("named"):
            for s in m.group("named").split(","):
                s = s.strip().split(":")[0].strip()
                if s:
                    syms.append(s)
        is_rel = src.startswith("./") or src.startswith("../")
        imports_list.append(ImportInfo(source=src, symbols=syms, is_relative=is_rel))

    # 2. Parse Classes First (Highest Priority in architecture overview)
    for m in RE_CLASS.finditer(code):
        name = m.group("name")
        line = code[:m.start()].count("\n") + 1
        symbols_list.append(SymbolInfo(name=name, kind="class", line=line))
        exports_list.append(name)

    # 3. Parse Interfaces & Types (TypeScript)
    for m in RE_TS_INTERFACE.finditer(code):
        name = m.group("name")
        line = code[:m.start()].count("\n") + 1
        symbols_list.append(SymbolInfo(name=name, kind="interface", line=line))
        exports_list.append(name)

    for m in RE_TS_TYPE.finditer(code):
        name = m.group("name")
        line = code[:m.start()].count("\n") + 1
        symbols_list.append(SymbolInfo(name=name, kind="type", line=line))
        exports_list.append(name)

    # 4. Parse Functions
    for m in RE_EXPORT_FUNC.finditer(code):
        name = m.group("name")
        if name in JS_KEYWORDS:
            continue
        line = code[:m.start()].count("\n") + 1
        args = clean_args(m.group("args"))
        symbols_list.append(SymbolInfo(name=name, kind="function", line=line, args=args))
        if m.group(0).strip().startswith("export"):
            exports_list.append(name)

    # 5. Parse Arrow Functions
    for m in RE_ARROW_FUNC.finditer(code):
        name = m.group("name")
        if name in JS_KEYWORDS:
            continue
        line = code[:m.start()].count("\n") + 1
        args = clean_args(m.group("args"))
        symbols_list.append(SymbolInfo(name=name, kind="function", line=line, args=args))
        if m.group(0).strip().startswith("export"):
            exports_list.append(name)

    # 6. Parse export { a, b }
    for m in RE_EXPORT_NAMED.finditer(code):
        for s in m.group("symbols").split(","):
            s = s.strip().split(" as ")[0].strip()
            if s and s not in exports_list:
                exports_list.append(s)

    # 7. Collect calls
    for m in RE_CALL.finditer(code):
        fn = m.group("func")
        if fn not in JS_KEYWORDS and fn not in calls_list:
            calls_list.append(fn)

    analysis.imports = imports_list
    analysis.symbols = symbols_list
    analysis.exports = list(set(exports_list))
    analysis.calls = calls_list[:50]
    return analysis
