# Project Memory & Session Context
> **Compact Context**: This file stores key project conventions and decisions. AI reads this to understand past agreements without needing full chat transcripts.

## 1. Project Conventions & Rules
- All internal functions must have type hints

## 2. Key Architecture Decisions
- **Terminal UI & Visual Graph**: Added interactive Terminal UI (tui.py), ASCII/Unicode dependency graph visualizer, dependency tree, and system doctor. *(2026-11-20)*
- **Interactive TUI & Web Graph (Graphify parity)**: Implemented OpenCode-style interactive arrow-key TUI, eliminated Vietnamese strings from developer UI, added standalone interactive web graph (rt web), and God Nodes / chokepoint centrality analysis. *(2026-11-20)*
- **Zero-CDN Standalone Web Graph & Zero-Truncation**: Replaced external CDN with self-contained HTML5 Canvas Force-Directed engine in graph.html, eliminated terminal screen flickering via ANSI in-place buffer, removed all symbol and file truncations in architecture_map and TUI, and added line-bound reading rules for AI. *(2026-11-20)*
- **Web Graph Layout Optimization & Independent Sync Action**: Enhanced web visualizer with hard circle collision avoidance, adjustable spacing slider, hide-isolated toggle, and type/connection filters. Split Update (incremental) and Rebuild (clean cache) into distinct menu items, and updated README documentation. *(2026-11-20)*
- **Direct Chrome Launch**: Enhanced launch_browser to directly locate and spawn Google Chrome executable on Windows, macOS, and Linux before falling back to default shell association. *(2026-11-20)*
- **Fix print_header & Web Launch**: Restored print_header method in TerminalUI to fix AttributeError on option 1. Updated launch_browser with Windows shell start chrome and explicit URL printout in _handle_web. *(2026-11-20)*
- **Web Graph Sidebar Wheel Isolation & Keyboard Shortcuts**: Isolated mouse wheel events on #sidebar and modals using stopPropagation and closest check to ensure scrolling symbol definitions never zooms canvas. Added keyboard shortcuts (Esc, /, Space, r, i, g, ?) with interactive cheat sheet modal. *(2026-11-20)*
- **Folder Enclosure Clustering, Dynamic Languages & Node Clearance Halo**: Implemented toggleable folder regions (dashed rounded enclosures with badges), eliminated cross-folder spring pull to keep clusters stable without jitter, replaced bouncy drag physics with high-friction damping (0.56) and velocity clamps, converted Spacing slider to strict node clearance buffer (invisible protective circle), and supported dynamic language coloring (Python, JS, TS, Rust, Go, HTML, CSS, C/C++, JSON, Markdown). *(2026-11-20)*
- **Command Reference Guide (rt help) & Granular AI Adapters Control**: Added comprehensive `rt help [cmd]` command guide, added `rt adapters` management (enable/disable/remove/sync), and updated `rt upgrade` with `--only`, `--skip`, and `--no-agents` flags respecting user configuration in `~/.reducetoken/config.json`. *(2026-11-20)*
- **Zero-Drift Folder Grid Layout & Whole-Folder Dragging**: In folder mode, disabled continuous physics forces and anchor collapses completely (0% drift, 0% cross-pull). Implemented structured multi-column collision-free grid layout per folder (160x95px spacing, God nodes first), and added full folder dragging by header badge or enclosure box. *(2026-11-20)*

