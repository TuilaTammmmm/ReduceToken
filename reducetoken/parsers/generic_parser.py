import re
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo

# Go patterns
RE_GO_PACKAGE = re.compile(r"""^package\s+([a-zA-Z0-9_]+)""", re.MULTILINE)
RE_GO_IMPORT = re.compile(r"""import\s+(?:\(\s*([^)]+)\s*\)|"([^"]+)")""", re.MULTILINE)
RE_GO_FUNC = re.compile(r"""func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(""", re.MULTILINE)

# Rust patterns
RE_RS_USE = re.compile(r"""use\s+([^;]+);""", re.MULTILINE)
RE_RS_FN = re.compile(r"""(?:pub\s+)?fn\s+([a-zA-Z0-9_]+)""", re.MULTILINE)
RE_RS_STRUCT = re.compile(r"""(?:pub\s+)?(?:struct|enum)\s+([a-zA-Z0-9_]+)""", re.MULTILINE)

# C/C++ patterns
RE_C_INCLUDE = re.compile(r"""#include\s+[<"]([^>"]+)[>"]""", re.MULTILINE)

# Java / C# patterns
RE_JAVA_PACKAGE = re.compile(r"""package\s+([^;]+);""", re.MULTILINE)
RE_JAVA_IMPORT = re.compile(r"""(?:import|using)\s+([^;]+);""", re.MULTILINE)
RE_JAVA_CLASS = re.compile(r"""(?:public|protected|private)?\s*(?:static\s+)?class\s+([a-zA-Z0-9_]+)""", re.MULTILINE)


def parse_generic_file(file_path: str, code: str, language: str) -> FileAnalysis:
    analysis = FileAnalysis(file_path=file_path, language=language)
    
    if language == "go":
        pkg = RE_GO_PACKAGE.search(code)
        if pkg:
            analysis.summary = f"Go package: {pkg.group(1)}"
        for m in RE_GO_IMPORT.finditer(code):
            block, single = m.groups()
            if single:
                analysis.imports.append(ImportInfo(source=single.strip(), symbols=[]))
            elif block:
                for line in block.split("\n"):
                    line = line.strip().strip('"')
                    if line:
                        analysis.imports.append(ImportInfo(source=line, symbols=[]))
        for m in RE_GO_FUNC.finditer(code):
            fn = m.group(1)
            line = code[:m.start()].count("\n") + 1
            analysis.symbols.append(SymbolInfo(name=fn, kind="function", line=line))
            analysis.exports.append(fn)

    elif language == "rust":
        for m in RE_RS_USE.finditer(code):
            src = m.group(1).strip()
            analysis.imports.append(ImportInfo(source=src, symbols=[]))
        for m in RE_RS_FN.finditer(code):
            fn = m.group(1)
            line = code[:m.start()].count("\n") + 1
            analysis.symbols.append(SymbolInfo(name=fn, kind="function", line=line))
            analysis.exports.append(fn)
        for m in RE_RS_STRUCT.finditer(code):
            st = m.group(1)
            line = code[:m.start()].count("\n") + 1
            analysis.symbols.append(SymbolInfo(name=st, kind="struct", line=line))
            analysis.exports.append(st)

    elif language in ("c", "cpp", "c_header", "cpp_header"):
        for m in RE_C_INCLUDE.finditer(code):
            inc = m.group(1)
            analysis.imports.append(ImportInfo(source=inc, symbols=[], is_relative='"' in m.group(0)))

    elif language in ("java", "csharp"):
        for m in RE_JAVA_IMPORT.finditer(code):
            imp = m.group(1).strip()
            analysis.imports.append(ImportInfo(source=imp, symbols=[]))
        for m in RE_JAVA_CLASS.finditer(code):
            cls = m.group(1)
            line = code[:m.start()].count("\n") + 1
            analysis.symbols.append(SymbolInfo(name=cls, kind="class", line=line))
            analysis.exports.append(cls)

    return analysis
