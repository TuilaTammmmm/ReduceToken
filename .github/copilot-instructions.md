# AI Token-Saving Guidelines for GitHub Copilot
This repository uses **ReduceToken** to optimize context and save tokens.
- **NEVER** scan the entire directory tree or read dozens of files indiscriminately.
- **ALWAYS** check `.codegraph/architecture_map.md` first to understand repository structure and module responsibilities.
- Check `.codegraph/session_context.md` for project conventions and past architectural decisions.
- Use `rt query <symbol_or_keyword>` to locate exact files, definitions, and dependencies.
- If import aliases (@/*, ~/*) or monorepo packages are used, inspect tsconfig.json / package.json to resolve real paths before querying.
- Only inspect the specific target file and its direct 1-hop dependencies.
- Keep responses compact with minimal tokens (targeted diffs, no full-file dumps).
