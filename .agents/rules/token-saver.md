---
trigger: always_on
---

# Token-Saving Golden Rules (ReduceToken - 100% Autonomous)

1. **Check Graph First**: Always check `.codegraph/architecture_map.md` and `.codegraph/session_context.md` instead of exploring directories from scratch.
2. **Use Query Tool**: Always use `reducetoken query <keyword>` (or `rt query`) to locate exact files, line numbers `[Lxx]`, and dependencies.
3. **Targeted Line-Bound Reading**: Use `read_file(Path, StartLine, EndLine)` to read ONLY the specific target 20-50 lines around `[Lxx]`. Never read entire files or entire directories.
4. **Autonomous Silent Update**: Delta-sync runs automatically in <10ms on queries. Maintain `.codegraph/session_context.md` in the background for new architectural decisions.
5. **Chat Token Minimization**: Keep responses compact. Never print entire files; output concise diffs only.
