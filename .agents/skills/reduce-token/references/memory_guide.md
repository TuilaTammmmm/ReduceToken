# Project Session Memory & Compaction Guide

## 1. Criteria: What to Save vs What NOT to Save

Record technical decisions into `.codegraph/session_context.md` (via `add_memory_decision` or `rt memory add` / `reducetoken memory add`):

### ✅ What to Save:
* **Architecture & Technology choices**: (e.g. "Using WebSockets for telemetry instead of HTTP polling").
* **Project-wide coding conventions**: (e.g. "All coordinates must use millimeters", "Use snake_case for event payloads").
* **Major API contracts & state patterns**: (e.g. "Auth middleware expects Bearer JWT in Authorization header").
* **Breaking schema or dependency changes**.

### ❌ What NOT to Save:
* Minor bug fixes, typo corrections, or routine line edits.
* Temporary debug logs or short-lived troubleshooting steps.
* Code implementation details already clearly visible in source files.

---

## 2. Memory Drift Guard (Compaction Rule)

Over extended multi-day coding sessions, `session_context.md` may accumulate stale entries.

> [!IMPORTANT]
> **Threshold Rule**: Whenever `.codegraph/session_context.md` exceeds **50 lines** (or ~500 tokens), autonomously run:
> ```bash
> rt compact   # (or: reducetoken compact)
> ```
> This automatically prunes deleted files, deduplicates conventions, and retains only recent decisions to maintain context permanently < 250 tokens.
