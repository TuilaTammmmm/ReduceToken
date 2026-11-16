# Claude Code - Token Saving Guidelines
- Repository architecture map: `.codegraph/architecture_map.md`
- Project memory & agreed decisions: `.codegraph/session_context.md`
- Use `rt query <symbol>` to find exact definitions and dependencies.
- If path aliases (@/*) or monorepo packages are used, check tsconfig.json / package.json to resolve real paths.
- Do NOT run full-directory recursive scans.
- Run `rt update` after modifying code to sync the graph.
- If session_context.md exceeds 50 lines, run `rt compact`.
- Keep chat responses concise; output targeted diffs instead of re-printing full files.
