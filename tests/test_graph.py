import unittest
import tempfile
import os
from pathlib import Path

from reducetoken.graph import CodeGraph
from reducetoken.generator import Generator
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo
from reducetoken.cache import CacheManager


class TestGraphAndCache(unittest.TestCase):
    def test_graph_resolution_and_query(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)

            # File A: utils.py
            analysis_a = FileAnalysis(
                file_path="utils.py",
                language="python",
                symbols=[SymbolInfo(name="hash_password", kind="function", line=10)],
                exports=["hash_password"]
            )
            # File B: auth.py (imports utils.py)
            analysis_b = FileAnalysis(
                file_path="auth.py",
                language="python",
                imports=[ImportInfo(source="utils", symbols=["hash_password"], is_relative=False)],
                symbols=[SymbolInfo(name="login", kind="function", line=25)],
                exports=["login"]
            )

            graph.add_analysis("utils.py", analysis_a)
            graph.add_analysis("auth.py", analysis_b)
            graph.build()

            # Verify edge: auth.py depends on utils.py
            self.assertIn("utils.py", graph.file_dependencies["auth.py"])
            # Verify reverse edge: utils.py is depended on by auth.py
            self.assertIn("auth.py", graph.file_dependents["utils.py"])

            # Query symbol 'hash_password'
            q_res = graph.query("hash_password")
            self.assertEqual(q_res["target_file"], "utils.py")
            self.assertIn("auth.py", q_res["dependents"])

            # Format DSL
            dsl = Generator.format_agent_dsl(q_res)
            self.assertIn("TARGET FILE: utils.py", dsl)
            self.assertIn("IMPORTED BY", dsl)
            self.assertIn("auth.py", dsl)

    def test_cache_incremental(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            cache_file = tmp_path / "cache.json"
            cm = CacheManager(cache_file)

            test_file = tmp_path / "sample.py"
            test_file.write_text("def hello(): pass\n", encoding="utf-8")

            analysis = FileAnalysis(file_path="sample.py", language="python")
            cm.update_entry("sample.py", test_file, analysis)
            cm.save()

            # Second instance loads cache
            cm2 = CacheManager(cache_file)
            self.assertTrue(cm2.is_cached_and_valid("sample.py", test_file))

            # Modify file
            test_file.write_text("def hello_world(): pass\n", encoding="utf-8")
            self.assertFalse(cm2.is_cached_and_valid("sample.py", test_file))

    def test_path_alias_resolution(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            # Create a mock tsconfig.json with path alias
            tsconfig = tmp_path / "tsconfig.json"
            tsconfig.write_text('{"compilerOptions": {"paths": {"@/*": ["src/*"]}}}', encoding="utf-8")

            graph = CodeGraph(tmp_path)
            # Component file in src/components/button.tsx
            analysis_btn = FileAnalysis(
                file_path="src/components/button.tsx",
                language="typescript",
                symbols=[SymbolInfo(name="Button", kind="function", line=5)]
            )
            # Page file importing using alias: @/components/button
            analysis_page = FileAnalysis(
                file_path="src/pages/index.tsx",
                language="typescript",
                imports=[ImportInfo(source="@/components/button", symbols=["Button"], is_relative=False)],
                symbols=[SymbolInfo(name="HomePage", kind="function", line=10)]
            )

            graph.add_analysis("src/components/button.tsx", analysis_btn)
            graph.add_analysis("src/pages/index.tsx", analysis_page)
            graph.build()

            # Verify that @/components/button was resolved to src/components/button.tsx
            self.assertIn("src/components/button.tsx", graph.file_dependencies["src/pages/index.tsx"])
            self.assertIn("src/pages/index.tsx", graph.file_dependents["src/components/button.tsx"])

    def test_git_head_tracking(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            git_dir = tmp_path / ".git"
            git_dir.mkdir()
            head_file = git_dir / "HEAD"
            head_file.write_text("ref: refs/heads/main\n", encoding="utf-8")

            cm = CacheManager(tmp_path / "cache.json")
            # First check -> detected head changed (from None to main)
            self.assertTrue(cm.check_and_update_git_head(tmp_path))
            # Second check -> unchanged
            self.assertFalse(cm.check_and_update_git_head(tmp_path))

            # Simulate branch switch
            head_file.write_text("ref: refs/heads/feature-login\n", encoding="utf-8")
            self.assertTrue(cm.check_and_update_git_head(tmp_path))

    def test_utf8_preservation_in_json(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)
            analysis = FileAnalysis(
                file_path="kho_duoc.py",
                language="python",
                symbols=[SymbolInfo(name="KhoThuoc", kind="class", line=1, doc="Hệ thống quản lý kho dược phẩm")],
                summary="HỆ THỐNG QUẢN LÝ KHO DƯỢC PHẨM"
            )
            graph.add_analysis("kho_duoc.py", analysis)
            graph.build()

            gen = Generator(tmp_path, graph)
            sym_file = gen.write_symbols_json()
            graph_file = gen.write_graph_json()

            # Verify that Vietnamese characters are saved as UTF-8 directly, NOT escaped as \uXXXX
            sym_content = sym_file.read_text(encoding="utf-8")
            self.assertIn("Hệ thống quản lý kho dược phẩm", sym_content)
            self.assertNotIn("\\u1ec6", sym_content)

            graph_content = graph_file.read_text(encoding="utf-8")
            self.assertIn("HỆ THỐNG QUẢN LÝ KHO DƯỢC PHẨM", graph_content)
            self.assertNotIn("\\u1ec6", graph_content)


if __name__ == "__main__":
    unittest.main()
