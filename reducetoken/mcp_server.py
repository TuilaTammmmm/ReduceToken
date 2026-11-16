import sys
import json
from pathlib import Path
from typing import Dict, Any

from reducetoken.scanner import FileScanner
from reducetoken.cache import CacheManager
from reducetoken.graph import CodeGraph
from reducetoken.generator import Generator
from reducetoken.parsers.python_parser import parse_python_file
from reducetoken.parsers.js_ts_parser import parse_js_ts_file
from reducetoken.parsers.generic_parser import parse_generic_file


class McpServer:
    def __init__(self, root_dir: Path):
        self.root_dir = Path(root_dir).resolve()
        self.cache_manager = CacheManager(self.root_dir / ".codegraph" / "cache.json")
        self.graph = CodeGraph(self.root_dir)
        from reducetoken.memory import SessionMemoryManager
        self.memory_manager = SessionMemoryManager(self.root_dir)
        self._ensure_graph_loaded()

    def _ensure_graph_loaded(self):
        # Scan and load
        scanner = FileScanner(self.root_dir)
        files = scanner.scan()
        valid_paths = set()

        for f_info in files:
            rel = f_info["path"]
            valid_paths.add(rel)
            full = Path(f_info["full_path"])

            analysis = self.cache_manager.get_analysis(rel)
            if not analysis or not self.cache_manager.is_cached_and_valid(rel, full):
                try:
                    code = full.read_text(encoding="utf-8", errors="ignore")
                    lang = f_info["lang"]
                    if lang == "python":
                        analysis = parse_python_file(rel, code)
                    elif lang in ("javascript", "typescript"):
                        analysis = parse_js_ts_file(rel, code, language=lang)
                    else:
                        analysis = parse_generic_file(rel, code, language=lang)
                    self.cache_manager.update_entry(rel, full, analysis)
                except Exception:
                    continue

            if analysis:
                self.graph.add_analysis(rel, analysis)

        self.cache_manager.remove_missing(valid_paths)
        self.graph.build()

    def get_architecture_map(self) -> str:
        arch_file = self.root_dir / ".codegraph" / "architecture_map.md"
        if arch_file.is_file():
            return arch_file.read_text(encoding="utf-8")
        gen = Generator(self.root_dir, self.graph)
        gen.generate_all()
        return arch_file.read_text(encoding="utf-8")

    def query_graph(self, query: str) -> str:
        # Fast delta update
        self._ensure_graph_loaded()
        res = self.graph.query(query)
        return Generator.format_agent_dsl(res)

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        msg_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "reducetoken-mcp", "version": "1.0.0"}
                }
            }

        elif method == "notifications/initialized":
            return None

        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": [
                        {
                            "name": "get_architecture_map",
                            "description": "Get high-level architecture overview and dependency network (<1000 tokens). Always call this first.",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "query_code_graph",
                            "description": "Locate exact file, functions, callers, and dependencies by symbol or keyword (~60 tokens).",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "Symbol name, function name, class name, or file path"}
                                },
                                "required": ["query"]
                            }
                        },
                        {
                            "name": "get_session_memory",
                            "description": "Get compact project memory, conventions, and past architectural decisions (<200 tokens).",
                            "inputSchema": {"type": "object", "properties": {}}
                        },
                        {
                            "name": "add_memory_decision",
                            "description": "Save an important architectural decision or convention to long-term memory.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "topic": {"type": "string", "description": "Topic or title of the decision"},
                                    "content": {"type": "string", "description": "Details of the agreed decision"}
                                },
                                "required": ["topic", "content"]
                            }
                        }
                    ]
                }
            }

        elif method == "tools/call":
            tool_name = params.get("name")
            args = params.get("arguments", {})

            if tool_name == "get_architecture_map":
                content = self.get_architecture_map()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": content}]}
                }

            elif tool_name == "query_code_graph":
                q = args.get("query", "")
                content = self.query_graph(q)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": content}]}
                }

            elif tool_name == "get_session_memory":
                content = self.memory_manager.get_compact_summary()
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": content}]}
                }

            elif tool_name == "add_memory_decision":
                topic = args.get("topic", "")
                content_desc = args.get("content", "")
                self.memory_manager.add_decision(topic, content_desc)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"content": [{"type": "text", "text": f"Saved decision '{topic}' to memory."}]}
                }

            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}
            }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }

    def run_stdio(self):
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                resp = self.handle_request(req)
                if resp:
                    sys.stdout.write(json.dumps(resp) + "\n")
                    sys.stdout.flush()
            except Exception as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                sys.stdout.write(json.dumps(err_resp) + "\n")
                sys.stdout.flush()


def main():
    root = Path.cwd()
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    server = McpServer(root)
    server.run_stdio()


if __name__ == "__main__":
    main()
