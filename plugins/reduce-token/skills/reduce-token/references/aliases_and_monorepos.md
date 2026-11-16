# Resolving Import Aliases & Monorepos

## 1. Automatic Engine Resolution
ReduceToken automatically loads path aliases from:
* `tsconfig.json` / `jsconfig.json`: `compilerOptions.paths` and `baseUrl`.
* Monorepo workspaces: `packages/*/package.json`, `apps/*/package.json`.

All standard `@/*` or workspace package imports are automatically connected in the dependency graph.

## 2. Agent Fallback Resolution
If an unconventional path alias is encountered (e.g., `~/utils`, `@shared/db`):
1. **TypeScript / JavaScript**:
   - Inspect `tsconfig.json` or `jsconfig.json`.
   - Check `compilerOptions.paths` to map the alias prefix to the real directory (e.g. `@/*` -> `src/*`).
2. **Monorepos (pnpm, yarn, lerna, npm workspaces)**:
   - Inspect `pnpm-workspace.yaml` or root `package.json` `workspaces`.
   - Map package names directly to their physical folder (e.g., `@repo/ui` -> `packages/ui`).
3. **Targeted Lookup**:
   - Once the real path is resolved, query `query_code_graph(query="packages/ui/...")` or inspect that single file directly.
   - **Never scan the entire monorepo**.
