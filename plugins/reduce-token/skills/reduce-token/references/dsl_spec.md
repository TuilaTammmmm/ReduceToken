# Agent DSL Specification & Subgraph Output

The query tool (`query_code_graph` via MCP or `rt query` via CLI) returns an ultra-compact context block (~60 tokens):

```text
=== REDUCETOKEN SUBGRAPH (Compact Context) ===
TARGET FILE: src/auth/jwt.py
DEFINES: class AuthManager() [L12], function verify_token() [L42]
IMPORTS (1): src/config.py
IMPORTED BY (2): src/api/middleware.py, src/routes/user.py
RECOMMENDED ACTION: Read only 'src/auth/jwt.py'. Do NOT read entire directory.
==============================================
```

## How to Act on Results

1. **Target File Inspection**:
   - Inspect ONLY the file indicated in `TARGET FILE`.
   - Never open sibling or adjacent files unless explicitly requested.

2. **Line Bounds Optimization**:
   - Extract the line numbers from `[Lxx]` (e.g. `[L42]`).
   - Call `read_file` with `StartLine` and `EndLine` bounded to that specific function or class (e.g., `StartLine=42, EndLine=75`).
   - This saves 90%+ tokens compared to loading the entire 500-line file.

3. **1-Hop Neighbor Inspection**:
   - If caller context or interface contracts are required, inspect ONLY the files explicitly listed in `IMPORTS` (dependencies) or `IMPORTED BY` (callers).
