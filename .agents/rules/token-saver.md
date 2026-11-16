---
trigger: always_on
---

# Token-Saving Golden Rules (ReduceToken - 100% Autonomous)

1. **Check Graph First**: Always check `.codegraph/architecture_map.md` and `.codegraph/session_context.md` instead of exploring directories from scratch.
2. **Use Query Tool**: Always use `reducetoken query <keyword>` to locate exact files and their direct dependencies.
3. **Targeted Reading**: Only read the specific file and lines identified by the query tool. Never read entire directories.
4. **Autonomous Silent Update**: Silently run `reducetoken update` and maintain `.codegraph/session_context.md` in the background after editing code. Never require manual user commands.
5. **Chat Token Minimization**: Keep responses compact. Never print entire files; output concise diffs only.
