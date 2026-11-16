import ast
from typing import List, Optional
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo


class PythonAstVisitor(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: List[ImportInfo] = []
        self.symbols: List[SymbolInfo] = []
        self.calls: List[str] = []
        self.exports: List[str] = []
        self.docstring: str = ""

    def visit_Module(self, node: ast.Module):
        doc = ast.get_docstring(node)
        if doc:
            self.docstring = doc.strip().split("\n")[0]
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(ImportInfo(
                source=alias.name,
                symbols=[alias.asname or alias.name],
                is_relative=False
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        source = node.module or ""
        is_rel = node.level > 0
        dots = "." * node.level
        full_source = f"{dots}{source}"
        symbols = [alias.name for alias in node.names]
        self.imports.append(ImportInfo(
            source=full_source,
            symbols=symbols,
            is_relative=is_rel
        ))
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        doc = ast.get_docstring(node) or ""
        first_line_doc = doc.strip().split("\n")[0] if doc else ""
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(item.name)

        self.symbols.append(SymbolInfo(
            name=node.name,
            kind="class",
            line=node.lineno,
            doc=first_line_doc,
            methods=methods
        ))
        self.exports.append(node.name)
        # Note: we visit class body to extract calls inside methods
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self._handle_function(node)

    def _handle_function(self, node):
        doc = ast.get_docstring(node) or ""
        first_line_doc = doc.strip().split("\n")[0] if doc else ""
        args = [arg.arg for arg in node.args.args if arg.arg != "self" and arg.arg != "cls"]

        self.symbols.append(SymbolInfo(
            name=node.name,
            kind="function",
            line=node.lineno,
            doc=first_line_doc,
            args=args
        ))
        self.exports.append(node.name)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        func_name = self._get_call_name(node.func)
        if func_name and func_name not in self.calls:
            self.calls.append(func_name)
        self.generic_visit(node)

    def _get_call_name(self, func_node) -> Optional[str]:
        if isinstance(func_node, ast.Name):
            return func_node.id
        elif isinstance(func_node, ast.Attribute):
            base = self._get_call_name(func_node.value)
            if base:
                return f"{base}.{func_node.attr}"
            return func_node.attr
        return None


def parse_python_file(file_path: str, code: str) -> FileAnalysis:
    analysis = FileAnalysis(file_path=file_path, language="python")
    try:
        tree = ast.parse(code, filename=file_path)
        visitor = PythonAstVisitor(file_path)
        visitor.visit(tree)
        analysis.imports = visitor.imports
        analysis.symbols = visitor.symbols
        analysis.calls = visitor.calls[:50]  # Cap top 50 calls
        analysis.exports = visitor.exports
        analysis.summary = visitor.docstring
    except Exception:
        # If syntax error in python file, fallback gracefully
        pass
    return analysis
