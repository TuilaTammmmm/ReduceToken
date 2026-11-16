import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional


class SessionMemoryManager:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir)
        self.codegraph_dir = self.root_dir / ".codegraph"
        self.memory_file = self.codegraph_dir / "memory.json"
        self.context_file = self.codegraph_dir / "session_context.md"
        self.memory_data: Dict[str, Any] = {
            "decisions": [],
            "touched_files": [],
            "conventions": [],
            "last_updated": ""
        }
        self.load()

    def load(self):
        if self.memory_file.is_file():
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    self.memory_data = json.load(f)
            except Exception:
                pass

    def save(self):
        self.codegraph_dir.mkdir(parents=True, exist_ok=True)
        self.memory_data["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.memory_data, f, indent=2, ensure_ascii=False)
            self.export_markdown()
        except Exception:
            pass

    def add_decision(self, topic: str, content: str):
        # Avoid duplicate topics
        self.memory_data["decisions"] = [
            d for d in self.memory_data.get("decisions", []) if d.get("topic") != topic
        ]
        self.memory_data["decisions"].append({
            "topic": topic,
            "content": content,
            "date": time.strftime("%Y-%m-%d")
        })
        self.save()

    def add_convention(self, convention: str):
        convs = self.memory_data.get("conventions", [])
        if convention not in convs:
            convs.append(convention)
            self.memory_data["conventions"] = convs
            self.save()

    def record_touched_file(self, rel_path: str):
        touched = self.memory_data.get("touched_files", [])
        if rel_path in touched:
            touched.remove(rel_path)
        touched.insert(0, rel_path)
        self.memory_data["touched_files"] = touched[:10]  # Keep top 10 recent
        self.save()

    def compact(self, max_decisions: int = 6, max_touched: int = 5) -> Path:
        """Compact session memory to prevent memory drift and maintain sub-250 token budget."""
        # Clean up stale touched files that no longer exist
        existing_touched = []
        for rel in self.memory_data.get("touched_files", []):
            if (self.root_dir / rel).is_file():
                existing_touched.append(rel)
        self.memory_data["touched_files"] = existing_touched[:max_touched]

        # Deduplicate conventions
        convs = list(dict.fromkeys(self.memory_data.get("conventions", [])))
        self.memory_data["conventions"] = convs[-8:]

        # Keep only the most recent/important decisions
        decs = self.memory_data.get("decisions", [])
        self.memory_data["decisions"] = decs[-max_decisions:]

        self.save()
        return self.context_file

    def export_markdown(self) -> Path:
        """Export compact markdown summary (~150-250 tokens) for AI context."""
        lines = [
            "# Project Memory & Session Context",
            "> **Compact Context**: This file stores key project conventions and decisions. "
            "AI reads this to understand past agreements without needing full chat transcripts.\n"
        ]

        convs = self.memory_data.get("conventions", [])
        if convs:
            lines.append("## 1. Project Conventions & Rules")
            for c in convs:
                lines.append(f"- {c}")
            lines.append("")

        decs = self.memory_data.get("decisions", [])
        if decs:
            lines.append("## 2. Key Architecture Decisions")
            for d in decs[-8:]:  # Last 8 decisions
                lines.append(f"- **{d['topic']}**: {d['content']} *({d.get('date', '')})*")
            lines.append("")

        touched = self.memory_data.get("touched_files", [])
        if touched:
            lines.append("## 3. Recently Touched Files")
            lines.append(", ".join([f"`{f}`" for f in touched[:6]]))
            lines.append("")

        content = "\n".join(lines) + "\n"
        with open(self.context_file, "w", encoding="utf-8") as f:
            f.write(content)
        return self.context_file

    def get_compact_summary(self) -> str:
        if self.context_file.is_file():
            try:
                return self.context_file.read_text(encoding="utf-8")
            except Exception:
                pass
        self.export_markdown()
        return self.context_file.read_text(encoding="utf-8")
