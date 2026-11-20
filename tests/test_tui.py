import unittest
import tempfile
from pathlib import Path

from reducetoken.graph import CodeGraph
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo
from reducetoken.tui import GraphVisualizer


class TestTuiAndVisualizer(unittest.TestCase):
    def test_draw_subgraph(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)

            analysis = FileAnalysis(
                file_path="service.py",
                language="python",
                symbols=[SymbolInfo(name="fetch_data", kind="function", line=15, doc="Fetches remote data.")],
                exports=["fetch_data"]
            )
            graph.add_analysis("service.py", analysis)
            graph.build()

            res = graph.query("fetch_data")
            output = GraphVisualizer.draw_subgraph(res)

            self.assertIn("TARGET FILE: service.py", output)
            self.assertIn("fetch_data", output)
            self.assertIn("INCOMING CALLERS", output)
            self.assertIn("OUTGOING DEPENDENCIES", output)

    def test_draw_dependency_tree(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)

            analysis_a = FileAnalysis(file_path="src/a.py", language="python")
            analysis_b = FileAnalysis(
                file_path="src/b.py",
                language="python",
                imports=[ImportInfo(source="a", symbols=[], is_relative=True)]
            )
            graph.add_analysis("src/a.py", analysis_a)
            graph.add_analysis("src/b.py", analysis_b)
            graph.build()

            tree_output = GraphVisualizer.draw_dependency_tree(graph)
            self.assertIn("Project Knowledge Graph Dependency Tree", tree_output)
            self.assertIn("src", tree_output)
            self.assertIn("a.py", tree_output)
            self.assertIn("b.py", tree_output)

    def test_draw_architecture_and_doctor(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)
            analysis = FileAnalysis(file_path="main.py", language="python")
            graph.add_analysis("main.py", analysis)
            graph.build()

            arch_output = GraphVisualizer.draw_architecture_overview(graph)
            self.assertIn("ARCHITECTURE OVERVIEW", arch_output)
            self.assertIn("Total Indexed Files", arch_output)

            doc_output = GraphVisualizer.draw_doctor(tmp_path, graph)
            self.assertIn("REDUCETOKEN SYSTEM DIAGNOSTICS", doc_output)
            self.assertIn("Graph & Cache Integrity", doc_output)


if __name__ == "__main__":
    unittest.main()
