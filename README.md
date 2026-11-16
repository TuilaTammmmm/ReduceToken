# ReduceToken

**English** | **[Tiếng Việt](README_VI.md)**

A lightweight, autonomous Code Knowledge Graph and Persistent Session Memory for AI coding agents, following the [Agent Skills](https://agentskills.io) open standard. Compatible with **Google Antigravity**, **Cursor IDE**, **Claude Code**, **OpenCode**, **Codex**, and **GitHub Copilot**.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-success.svg)](https://docs.python.org/3/library/)
[![Agent Skills](https://img.shields.io/badge/standard-Agent_Skills-orange.svg)](https://agentskills.io)
[![MCP Ready](https://img.shields.io/badge/MCP-Ready-purple.svg)](https://modelcontextprotocol.io)
[![Token Savings](https://img.shields.io/badge/Token_Savings-up_to_95%25-brightgreen.svg)](#-token-economics-before-vs-after)

> **Eliminates context window bloat, stops wasteful full-directory scans (`ls -R`, indiscriminate file reading), and cuts token consumption by up to 95%.**

---

## ⚡ Quick Start

> **Choose ONE of the two options below (You do NOT need to do both):**

### 🌟 Option A: Smart Multi-Agent Installer (Recommended)
Installs the `rt` CLI and auto-detects which AI coding agents are present on your machine:

```bash
# 1. Install CLI from Git
pip install git+https://github.com/TuilaTammmmm/ReduceToken.git

# 2. Run smart installer (Auto-detects and lets you pick target agents or install all)
rt install
```

**Interactive Selector Preview:**
```text
Detected AI environments on your system:
  [1] Google Antigravity & Gemini CLI        [DETECTED]
  [2] Cursor IDE (Global MCP)                [DETECTED]
  [3] Claude Code                            [DETECTED]
  [4] OpenCode                               [DETECTED]
  [5] Agent Skills Standard (Codex)          [DETECTED]
  [6] Current Project Directory Only (.codegraph/)  [Local]
  -------------------------------------------------------------
  [A] Install for ALL agents (Recommended)
  [Q] Cancel
```
*(Tip: You can pass `rt install --global` to automatically configure all detected agents without prompting).*

---

### 📦 Option B: Install via Agent Package Managers (Alternative)
If you prefer not using Python/pip, you can add ReduceToken directly through your agent's package manager:

* **Agent Skills CLI**:
  ```bash
  npx skills add TuilaTammmmm/ReduceToken
  ```
* **Codex Marketplace**:
  ```bash
  codex plugin marketplace add TuilaTammmmm/ReduceToken --ref main
  ```
* **OpenCode**:
  ```bash
  # Copy skill folder directly:
  cp -R plugins/reduce-token/skills/reduce-token .opencode/skills/
  ```

---

### 🚀 Enable in Any Project
Once installed, open a terminal in any repository where you want your AI to save tokens:

```bash
rt init
```
*Scans your code and generates `.codegraph/` (clean & clutter-free: automatically detects global AI plugins so zero rule files are dumped into your project root!).*
*Options: `rt init --clean` (pure `.codegraph/`), `rt init --agent cursor` (target specific tool), or `rt init --agent all`.*

---

### 🔄 How to Update (For Existing Users)
When a new version or bug fix is released, upgrade everything in **1 single command**:

```bash
rt upgrade
```
*This automatically pulls the latest Git package via pip AND synchronizes all global AI plugins (Antigravity, Cursor, Claude Code, OpenCode, Codex).*

*(Or update manually via pip: `pip install -U git+https://github.com/TuilaTammmmm/ReduceToken.git && rt install --global`)*

---

## 🎯 Core Capabilities & Prompt Examples

| Skill / Feature | Description | Prompt Example |
|---|---|---|
| **Targeted Subgraph Query** | Pinpoints exact symbol location, line number, and 1-hop dependencies in ~60 tokens | *"Find where `AuthManager` is defined and show what files import it."*<br>*"Locate the route handler for `/api/v1/checkout` without scanning the whole folder."* |
| **Architecture Discovery** | Bird's-eye view of all modules, entry points, and directory clusters (<1,000 tokens) | *"Give me an architectural overview of this codebase."*<br>*"Which module handles token verification and database migrations?"* |
| **Persistent Session Memory** | Long-term memory for architectural decisions and coding conventions (~150 tokens) | *"Record our decision to use WebSockets instead of polling in project memory."*<br>*"Add a coding convention: All coordinate variables must be in millimeters."* |
| **Memory Compaction** | Summarizes project decisions and updates compact context for fresh chat tabs | *"Compact our session memory so we can start a clean conversation."* |
| **Autonomous Background Sync** | Sub-10ms delta check and graph update on modified files | *"Refactor the auth middleware."* *(AI autonomously executes `rt update` in the background).* |

---

## 🔄 Autonomous Agent Workflow

ReduceToken operates in an **autonomous, zero-user-effort loop**:

```mermaid
flowchart TD
    User([User Prompt / Bug Fix]) --> Discovery
    
    subgraph Discovery ["1. High-Level Discovery (<1,000 tokens)"]
        ReadMap["read_file('.codegraph/architecture_map.md')\nInstant overview of modules & entry points"]
        ReadMem["read_file('.codegraph/session_context.md')\nPast conventions & architectural agreements"]
    end

    Discovery --> Query

    subgraph Query ["2. Subgraph Query (~60 tokens)"]
        ExecQuery["rt query <symbol_or_keyword>"]
        DSLOutput["Returns Agent DSL Block:\n- TARGET FILE & Line [Lxx]\n- 1-hop IMPORTS & IMPORTED BY"]
    end

    Query --> TargetedRead

    subgraph TargetedRead ["3. Targeted Line-Bound Reading"]
        ReadExact["read_file(Path, StartLine, EndLine)\nReads only [L40-L75], never loads entire 1,000-line file"]
        EditCode["Modify Code"]
    end

    TargetedRead --> AutoSync

    subgraph AutoSync ["4. Autonomous Background Maintenance (<100ms)"]
        SyncGraph["rt update\n(Incremental cache & graph sync)"]
        SaveMem["rt memory add / conv\n(Auto-records architectural decisions)"]
    end

    AutoSync --> Done([Concise Diff & Solution Output])
```

### Agent DSL Example Output
When querying a symbol, the agent receives an ultra-compact context block:
```text
=== REDUCETOKEN SUBGRAPH (Compact Context) ===
TARGET FILE: src/auth/jwt.py
DEFINES: class AuthManager() [L12], function verify_token() [L42]
IMPORTS (1): src/config.py
IMPORTED BY (2): src/api/middleware.py, src/routes/user.py
RECOMMENDED ACTION: Read only 'src/auth/jwt.py'. Do NOT read entire directory.
==============================================
```

---

## 📊 Token Economics: Before vs After

| Operation | Traditional Agent Behavior | With ReduceToken | Token Savings |
| :--- | :--- | :--- | :--- |
| **Project Orientation** | Full directory walk (`ls -R`, multi-read) (~8,000 tokens) | Read `architecture_map.md` (~900 tokens) | **~88%** |
| **Locating a Symbol** | Grep entire repo & read 5–10 files (~12,000 tokens) | Subgraph Query DSL (~60 tokens) | **~99%** |
| **Reading Code** | Ingesting entire 500-line file (~2,500 tokens) | Bounded lines via `[Lxx]` (~150 tokens) | **~94%** |
| **New Chat Session** | Ingesting 20+ turns of chat history (~15,000 tokens) | Read `session_context.md` (~150 tokens) | **~98%** |
| **Average Task Total** | **~37,500 tokens** | **~1,260 tokens** | **~96.6%** |

---

## 📂 Repository & Customization Layout

```text
ReduceToken/
├── plugins/
│   └── reduce-token/          — Global Antigravity Plugin bundle
│       ├── plugin.json        — Manifest ("displayName": "ReduceToken")
│       ├── rules/AGENTS.md    — Autonomous token-saving rules
│       └── skills/
│           └── reduce-token/
│               └── SKILL.md   — Standard Agent Skill (SKILL.md)
├── .agents/
│   └── skills/reduce-token/   — Agent Skills open standard discoverable path
│       └── SKILL.md
├── reducetoken/               — Core Engine (Zero external dependencies)
│   ├── parsers/               — Python AST, JS/TS, and generic parsers
│   ├── scanner.py             — High-speed file & ignore scanner
│   ├── graph.py               — Directed Dependency Graph
│   ├── cache.py               — SHA-256 incremental cache (<10ms)
│   ├── generator.py           — Architecture map & Agent DSL generator
│   ├── memory.py              — Long-term session memory manager
│   ├── mcp_server.py          — Native Model Context Protocol server
│   └── cli.py                 — Command-line interface
├── .codegraph/                — Generated Knowledge Graph (Git-tracked)
│   ├── architecture_map.md    — High-level structural overview (<1,000 tokens)
│   ├── session_context.md     — Persistent conventions & agreements (~150 tokens)
│   └── cache.json             — Machine-local delta cache
├── setup.py                   — Package entry point (`rt`, `reducetoken`)
└── README.md                  — Documentation
```

Each skill adheres to the Agent Skills standard:
```text
skills/reduce-token/
└── SKILL.md                   — The "Mission Control" guide for the AI Agent
```

---

## 🛠️ CLI Reference

You can use the short alias **`rt`** (or `reducetoken`) anywhere in your terminal:

| Command (`rt` or `reducetoken`) | Action |
|---|---|
| `rt init [--force]` | Scans repository, builds `.codegraph/`, and generates AI rule files |
| `rt query <symbol>` | Queries graph for a symbol/file with sub-10ms delta sync |
| `rt update` | Incrementally re-indexes modified files (<100ms) |
| `rt overview` | Outputs high-level architecture map |
| `rt memory add "<Topic>" "<Details>"` | Records an architectural decision in `session_context.md` |
| `rt memory conv "<Rule>"` | Records a persistent coding convention |
| `rt compact` | Updates and prints compact session context |
| `rt install --global` | Installs global plugin across all AI environments |
| `rt mcp` | Runs as a native Model Context Protocol (MCP) server |
| `rt git-hook` | Installs Git post-commit hook for auto-syncing |

> **💡 Aliases**: Both `rt` and `reducetoken` are registered globally (`rd` is also registered for Linux/macOS; on Windows PowerShell `rt` is used to prevent collisions with the built-in `Remove-Item` alias).  
> **Portable fallback**: `python -m reducetoken.cli <command>`.

---

## 🔌 Model Context Protocol (MCP) Integration

ReduceToken includes a built-in MCP server for native integration with MCP-compatible agents (Antigravity, Claude Desktop, Cursor, OpenCode):

```json
{
  "mcpServers": {
    "reducetoken": {
      "command": "python",
      "args": ["-m", "reducetoken.cli", "mcp"]
    }
  }
}
```

### Exposed MCP Tools
* `get_architecture_map`: Returns the high-level system structure.
* `query_symbol`: Returns the compact Subgraph DSL for any symbol or file.
* `get_session_context`: Returns project conventions and architectural decisions.

---

## 🌐 Supported Languages & Parsers

* **Python**: Full AST parsing (`ast`) with class, function, method, decorator, and import resolution.
* **JavaScript / TypeScript**: Fast AST-like regex parsing for ESM imports, CommonJS `require`, classes, arrow functions, and exports.
* **Go, Rust, Java, C/C++**: Generic symbol and structural parser fallback.

---

## 📄 License

MIT License. Copyright (c) 2026 TuilaTammmmm (ReduceToken). Free for personal and commercial use.
