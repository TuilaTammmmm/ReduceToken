import unittest
import tempfile
from pathlib import Path

from reducetoken.graph import CodeGraph
from reducetoken.parsers import FileAnalysis, SymbolInfo, ImportInfo
from reducetoken.web_visualizer import generate_web_graph_html


class TestWebVisualizerAndGodNodes(unittest.TestCase):
    def test_god_nodes_calculation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)

            # Node A is imported by B, C, D (High In-degree -> God Node)
            analysis_a = FileAnalysis(
                file_path="core/engine.py",
                language="python",
                symbols=[SymbolInfo(name="Engine", kind="class", line=10)],
                exports=["Engine"]
            )
            analysis_b = FileAnalysis(
                file_path="services/auth.py",
                language="python",
                imports=[ImportInfo(source="core.engine", symbols=["Engine"])]
            )
            analysis_c = FileAnalysis(
                file_path="services/billing.py",
                language="python",
                imports=[ImportInfo(source="core.engine", symbols=["Engine"])]
            )
            analysis_d = FileAnalysis(
                file_path="services/orders.py",
                language="python",
                imports=[ImportInfo(source="core.engine", symbols=["Engine"])]
            )

            graph.add_analysis("core/engine.py", analysis_a)
            graph.add_analysis("services/auth.py", analysis_b)
            graph.add_analysis("services/billing.py", analysis_c)
            graph.add_analysis("services/orders.py", analysis_d)
            graph.build()

            god_nodes = graph.get_god_nodes()
            self.assertTrue(len(god_nodes) > 0)
            top_node = god_nodes[0]
            self.assertEqual(top_node["file"], "core/engine.py")
            self.assertEqual(top_node["in_degree"], 3)
            self.assertEqual(top_node["role"], "Foundational Core")

    def test_generate_web_graph_html(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            graph = CodeGraph(tmp_path)
            analysis = FileAnalysis(file_path="app.py", language="python")
            graph.add_analysis("app.py", analysis)
            graph.build()

            out_html = tmp_path / "graph.html"
            generate_web_graph_html(graph, out_html)

            self.assertTrue(out_html.is_file())
            content = out_html.read_text(encoding="utf-8")
            self.assertIn("graph-canvas", content)
            self.assertIn("ReduceToken", content)
            self.assertIn("app.py", content)
            self.assertIn("shortcuts-modal", content)
            self.assertIn("stopPropagation", content)
            self.assertIn("Escape", content)
            self.assertIn("spacing-slider", content)
            self.assertIn("group-folders", content)
            self.assertIn("nodeClearance", content)
            self.assertIn("languageStyles", content)
            self.assertIn("recalculateFolderAnchors", content)
            self.assertIn("layoutFolderNodes", content)
            self.assertIn("findFolderAt", content)
            self.assertIn("draggedFolder", content)


if __name__ == "__main__":
    unittest.main()
