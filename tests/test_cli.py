import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path

from reducetoken.cli import main
from reducetoken.memory import SessionMemoryManager


class TestCliCommands(unittest.TestCase):
    def test_cli_query_and_graph(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            (tmp / "sample.py").write_text("def calculate_sum(a, b): return a + b\n", encoding="utf-8")
            
            # Run init
            ret = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "init", "--clean"], capture_output=True, text=True)
            self.assertEqual(ret.returncode, 0)

            # Query
            ret_q = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "query", "calculate_sum"], capture_output=True, text=True)
            self.assertEqual(ret_q.returncode, 0)
            self.assertIn("TARGET FILE: sample.py", ret_q.stdout)

            # Graph
            ret_g = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "graph", "calculate_sum"], capture_output=True, text=True)
            self.assertEqual(ret_g.returncode, 0)
            self.assertIn("TARGET FILE: sample.py", ret_g.stdout)

            # Tree
            ret_t = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "tree"], capture_output=True, text=True)
            self.assertEqual(ret_t.returncode, 0)
            self.assertIn("sample.py", ret_t.stdout)

            # Overview
            ret_o = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "overview"], capture_output=True, text=True)
            self.assertEqual(ret_o.returncode, 0)
            self.assertIn("Architecture Map", ret_o.stdout)

            # Doctor
            ret_d = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "doctor"], capture_output=True, text=True)
            self.assertEqual(ret_d.returncode, 0)
            self.assertIn("REDUCETOKEN SYSTEM DIAGNOSTICS", ret_d.stdout)

            # Help command
            ret_h = subprocess.run([sys.executable, "-m", "reducetoken.cli", "help"], capture_output=True, text=True)
            self.assertEqual(ret_h.returncode, 0)
            self.assertIn("ReduceToken CLI Reference Guide", ret_h.stdout)

            # Help for specific command
            ret_hu = subprocess.run([sys.executable, "-m", "reducetoken.cli", "help", "upgrade"], capture_output=True, text=True)
            self.assertEqual(ret_hu.returncode, 0)
            self.assertIn("--skip", ret_hu.stdout)

            # Adapters list
            ret_ad = subprocess.run([sys.executable, "-m", "reducetoken.cli", "adapters"], capture_output=True, text=True)
            self.assertEqual(ret_ad.returncode, 0)
            self.assertIn("ReduceToken AI Agent Adapters", ret_ad.stdout)

            # Memory add & show
            ret_m1 = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "memory", "add", "TestRule", "Details"], capture_output=True, text=True)
            self.assertEqual(ret_m1.returncode, 0)

            ret_m2 = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "memory", "show"], capture_output=True, text=True)
            self.assertEqual(ret_m2.returncode, 0)
            self.assertIn("TestRule", ret_m2.stdout)

            # Compact
            ret_c = subprocess.run([sys.executable, "-m", "reducetoken.cli", "--dir", str(tmp), "compact"], capture_output=True, text=True)
            self.assertEqual(ret_c.returncode, 0)


if __name__ == "__main__":
    unittest.main()
