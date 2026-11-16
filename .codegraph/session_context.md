# Project Memory & Session Context
> **Compact Context**: This file stores key project conventions and decisions. AI reads this to understand past agreements without needing full chat transcripts.

## 1. Project Conventions & Rules
- All internal functions must have type hints

## 2. Key Architecture Decisions
- **Architecture**: Used Directed Graph for dependency tracking *(2026-11-16)*
- **Clean Workspace**: `rt init` defaults to clean mode: if global AI plugin is detected, zero rule files are created at root; otherwise uses hidden `.agents/rules/` and `.cursor/rules/` to avoid root directory pollution. *(2026-11-16)*

