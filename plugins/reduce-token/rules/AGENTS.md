# Agent Guidelines (Antigravity & OpenCode)
## Token Optimization & Code Knowledge Graph (100% Autonomous)
- **First Step**: Always consult `.codegraph/architecture_map.md` and `.codegraph/session_context.md` to understand module overview and past architectural decisions without wasting tokens.
- **Targeted Lookup**: Run `rt query <keyword_or_symbol>` to get the exact subgraph (target file, dependencies, callers).
- **Import Aliases & Monorepo**: When navigating virtual aliases (`@/*`, `~/*`, `workspace:*`), inspect `tsconfig.json` (`paths`) or `package.json` workspaces to resolve real paths instead of full-directory searches.
- **Zero Full-Scan**: Never run commands that list or read all files across the repository.
- **Autonomous Silent Maintenance (Zero User Effort)**:
  * Do NOT spam `rt update` after every micro-edit. Run `rt update` once upon completing a task batch or logical feature.
  * When you make an important technical decision or convention, automatically record it in `.codegraph/session_context.md`.
  * If `.codegraph/session_context.md` exceeds 50 lines (or ~500 tokens), automatically run `rt compact` to maintain token budget.
- **Chat Token Minimization**:
  * Keep responses concise and focused. Do not repeat full files or long logs.
  * Point directly to file line ranges with `file://` links and targeted diffs.
  * All persistent project state lives in `.codegraph/session_context.md`, so even in fresh chat tabs you pick up context in < 150 tokens.
