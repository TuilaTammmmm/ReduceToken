import unittest
import tempfile
from pathlib import Path
from reducetoken.agent_adapters import AgentAdapterManager


class TestAgentAdapters(unittest.TestCase):
    def test_clean_mode_no_files(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            mgr = AgentAdapterManager(root)
            res = mgr.setup_by_agent("clean")
            self.assertEqual(len(res), 0)
            res = mgr.setup_by_agent("none")
            self.assertEqual(len(res), 0)

    def test_cursor_modern_encapsulation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            mgr = AgentAdapterManager(root)
            # Modern hidden mode (.cursor/rules/)
            res = mgr.setup_by_agent("cursor", root_rules=False)
            self.assertEqual(len(res), 1)
            self.assertTrue((root / ".cursor" / "rules" / "token-saver.mdc").is_file())
            self.assertFalse((root / ".cursorrules").exists())

    def test_agents_standard_hidden_encapsulation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            mgr = AgentAdapterManager(root)
            # Modern hidden mode (.agents/rules/)
            res = mgr.setup_by_agent("antigravity", root_rules=False)
            self.assertEqual(len(res), 1)
            self.assertTrue((root / ".agents" / "rules" / "token-saver.md").is_file())
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "GEMINI.md").exists())

    def test_legacy_root_rules(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            mgr = AgentAdapterManager(root)
            res = mgr.setup_by_agent("antigravity", root_rules=True)
            self.assertEqual(len(res), 2)
            self.assertTrue((root / "AGENTS.md").is_file())
            self.assertTrue((root / "GEMINI.md").is_file())


if __name__ == "__main__":
    unittest.main()
