# Example Workflow: Targeted Bug Fix & Feature Update

A step-by-step walkthrough demonstrating how an AI Agent handles a user request using ReduceToken with zero directory scanning.

---

## Scenario: User Request
> **User Prompt**: *"Fix token expiration verification in `AuthManager` and add refresh token rotation check."*

---

### Step 1: Subgraph Query (~60 tokens)
Instead of walking directory trees (`ls -R`, multi-grep) or reading 10 files in `src/`:

* **Agent Action**:
  ```python
  # Via Native MCP Tool (Preferred):
  query_code_graph(query="AuthManager")
  # Or via Shell CLI fallback:
  # rt query AuthManager
  ```

* **Received Agent DSL Block**:
  ```text
  === REDUCETOKEN SUBGRAPH (Compact Context) ===
  TARGET FILE: src/auth/jwt.py
  DEFINES: class AuthManager() [L12], function verify_token() [L42], function rotate_refresh() [L80]
  IMPORTS (2): src/config.py, src/db/session.py
  IMPORTED BY (1): src/api/middleware.py
  RECOMMENDED ACTION: Read only 'src/auth/jwt.py'. Do NOT read entire directory.
  ==============================================
  ```

---

### Step 2: Targeted Line-Bounded Reading (~150 tokens)
The Agent notices `AuthManager` defines `verify_token()` at line 42 and `rotate_refresh()` at line 80. Instead of reading the entire 450-line file:

* **Agent Action**:
  ```python
  read_file(Path="src/auth/jwt.py", StartLine=40, EndLine=95)
  ```
* **Benefit**: Ingests only ~55 lines instead of 450 lines, saving 85%+ tokens.

---

### Step 3: Targeted Code Modification
Agent modifies `verify_token()` using `edit_file`.
* **Zero Overhead**: The agent does **NOT** call `rt update` after editing; delta-sync is automatically handled lazily by the engine when needed.

---

### Step 4: Record Architectural Agreement (~40 tokens)
The user and agent agree on a new security decision:

* **Agent Action**:
  ```python
  # Via MCP:
  add_memory_decision(
      topic="JWT Refresh Rotation",
      content="AuthManager now revokes parent refresh token upon reuse."
  )
  # Or via CLI:
  # rt memory add "JWT Refresh Rotation" "AuthManager now revokes parent refresh token upon reuse."
  ```

---

### Step 5: Deliver Solution
Agent outputs a concise diff and links directly to [src/auth/jwt.py](file:///src/auth/jwt.py#L42-L95).
* **Total Tokens Consumed for Code Navigation**: **~250 tokens** (Compared to 15,000+ tokens traditionally).
