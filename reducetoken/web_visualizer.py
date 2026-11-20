import os
import sys
import json
import shutil
import subprocess
import webbrowser
from pathlib import Path
from typing import Dict, Any, Optional

from reducetoken.graph import CodeGraph
from reducetoken.scanner import EXT_TO_LANG

LANGUAGE_STYLES = {
    "python": {"color": "#0284c7", "border": "#38bdf8", "name": "Python"},
    "javascript": {"color": "#eab308", "border": "#fde047", "name": "JavaScript"},
    "typescript": {"color": "#3b82f6", "border": "#93c5fd", "name": "TypeScript"},
    "rust": {"color": "#ea580c", "border": "#fb923c", "name": "Rust"},
    "go": {"color": "#06b6d4", "border": "#22d3ee", "name": "Go"},
    "html": {"color": "#e11d48", "border": "#fb7185", "name": "HTML"},
    "css": {"color": "#ec4899", "border": "#f472b6", "name": "CSS"},
    "scss": {"color": "#ec4899", "border": "#f472b6", "name": "SCSS"},
    "c": {"color": "#6366f1", "border": "#818cf8", "name": "C"},
    "cpp": {"color": "#6366f1", "border": "#818cf8", "name": "C++"},
    "c_header": {"color": "#818cf8", "border": "#a5b4fc", "name": "C Header"},
    "cpp_header": {"color": "#818cf8", "border": "#a5b4fc", "name": "C++ Header"},
    "csharp": {"color": "#10b981", "border": "#34d399", "name": "C#"},
    "java": {"color": "#b45309", "border": "#f59e0b", "name": "Java"},
    "kotlin": {"color": "#7c3aed", "border": "#a78bfa", "name": "Kotlin"},
    "swift": {"color": "#f97316", "border": "#fdba74", "name": "Swift"},
    "ruby": {"color": "#be123c", "border": "#fb7185", "name": "Ruby"},
    "php": {"color": "#4f46e5", "border": "#818cf8", "name": "PHP"},
    "markdown": {"color": "#64748b", "border": "#94a3b8", "name": "Markdown"},
    "json": {"color": "#475569", "border": "#64748b", "name": "JSON"},
    "yaml": {"color": "#475569", "border": "#64748b", "name": "YAML"},
    "toml": {"color": "#475569", "border": "#64748b", "name": "TOML"},
    "shell": {"color": "#14b8a6", "border": "#2dd4bf", "name": "Shell"},
    "unknown": {"color": "#334155", "border": "#475569", "name": "Other"}
}


def generate_web_graph_html(graph: CodeGraph, output_path: Path) -> Path:
    """Generate an advanced standalone, zero-CDN HTML5 Canvas Interactive Graph."""
    graph_dict = graph.to_dict()
    god_nodes = graph.get_god_nodes(top_k=8)
    god_nodes_set = {n["file"] for n in god_nodes}

    node_id_to_idx = {}
    nodes_data = []
    present_langs = {}

    for idx, node in enumerate(graph_dict["nodes"]):
        f_path = node["id"]
        node_id_to_idx[f_path] = idx
        raw_lang = node.get("language", "unknown")
        suffix = Path(f_path).suffix.lower()
        if (raw_lang == "unknown" or not raw_lang) and suffix in EXT_TO_LANG:
            lang = EXT_TO_LANG[suffix]
        else:
            lang = raw_lang
        if lang not in LANGUAGE_STYLES:
            lang = "unknown"

        p_obj = Path(f_path)
        parent_str = str(p_obj.parent).replace("\\", "/")
        if parent_str in (".", ""):
            folder = "root"
        else:
            folder = parent_str.split("/")[0]

        sym_count = node.get("symbols_count", 0)
        is_god = f_path in god_nodes_set
        in_degree = len(graph.file_dependents.get(f_path, set()))
        out_degree = len(graph.file_dependencies.get(f_path, set()))
        is_isolated = (in_degree == 0 and out_degree == 0)

        # Categorize file
        is_test = "test" in f_path.lower()
        is_code = lang in ("python", "javascript", "typescript", "go", "rust", "java", "c", "cpp", "csharp", "php", "ruby", "swift", "kotlin", "scala") and not is_test

        style = LANGUAGE_STYLES[lang]
        if is_god:
            color = "#f59e0b"
            border_color = "#fbbf24"
            radius = 18 + min(in_degree, 8)
            category = "god"
        elif is_test:
            color = "#8b5cf6"
            border_color = "#a78bfa"
            radius = 11 + min(in_degree, 6)
            category = "test"
        else:
            color = style["color"]
            border_color = style["border"]
            radius = 12 + min(in_degree, 8) if is_code else 9
            category = "code" if is_code else "meta"

        present_langs[lang] = present_langs.get(lang, 0) + 1

        symbols_info = graph.file_symbols.get(f_path, [])
        sym_list = []
        for s in symbols_info:
            sym_list.append({
                "name": s.get("name", ""),
                "kind": s.get("kind", ""),
                "line": s.get("line", 1),
                "doc": s.get("doc", "")
            })

        nodes_data.append({
            "id": f_path,
            "label": Path(f_path).name,
            "folder": folder,
            "folder_path": parent_str,
            "language": lang,
            "lang_name": style["name"],
            "summary": node.get("summary", ""),
            "symbols_count": sym_count,
            "symbols": sym_list,
            "is_god": is_god,
            "is_test": is_test,
            "in_degree": in_degree,
            "out_degree": out_degree,
            "is_isolated": is_isolated,
            "category": category,
            "color": color,
            "border_color": border_color,
            "radius": radius,
            "exports": node.get("exports", [])
        })

    links_data = []
    for edge in graph_dict["edges"]:
        src = edge["source"]
        tgt = edge["target"]
        if src in node_id_to_idx and tgt in node_id_to_idx:
            links_data.append({
                "source": node_id_to_idx[src],
                "target": node_id_to_idx[tgt],
                "src_id": src,
                "tgt_id": tgt
            })

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ReduceToken - Interactive Knowledge Graph (Standalone)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: #090d16;
      color: #f1f5f9;
      height: 100vh;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      user-select: none;
    }}
    header {{
      background: #0f172a;
      border-bottom: 1px solid #1e293b;
      padding: 10px 18px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 10px;
      z-index: 20;
    }}
    .logo {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 700;
      font-size: 15px;
      color: #38bdf8;
    }}
    .badge {{
      background: #1e293b;
      border: 1px solid #334155;
      padding: 3px 8px;
      border-radius: 9999px;
      font-size: 11px;
      color: #94a3b8;
      font-weight: 500;
    }}
    .toolbar {{
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }}
    input[type="text"] {{
      background: #1e293b;
      border: 1px solid #334155;
      color: #f8fafc;
      padding: 5px 10px;
      border-radius: 6px;
      font-size: 12px;
      width: 180px;
      outline: none;
    }}
    input[type="text"]:focus {{
      border-color: #38bdf8;
    }}
    select, button {{
      background: #1e293b;
      color: #f1f5f9;
      border: 1px solid #334155;
      padding: 5px 10px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 12px;
      font-weight: 500;
      outline: none;
      transition: all 0.15s;
    }}
    button:hover, select:hover {{
      background: #334155;
      border-color: #38bdf8;
    }}
    .btn-active {{
      background: #0284c7 !important;
      border-color: #38bdf8 !important;
      color: #ffffff !important;
    }}
    .filter-toggle {{
      display: flex;
      align-items: center;
      gap: 5px;
      font-size: 12px;
      color: #cbd5e1;
      cursor: pointer;
      background: #1e293b;
      border: 1px solid #334155;
      padding: 4px 8px;
      border-radius: 6px;
    }}
    .filter-toggle input {{
      cursor: pointer;
    }}
    .slider-control {{
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: #94a3b8;
    }}
    .slider-control input[type="range"] {{
      width: 80px;
      cursor: pointer;
    }}
    #canvas-container {{
      flex: 1;
      position: relative;
      overflow: hidden;
      cursor: grab;
    }}
    #canvas-container:active {{
      cursor: grabbing;
    }}
    canvas {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    #sidebar {{
      position: absolute;
      top: 0;
      right: 0;
      width: 370px;
      height: 100%;
      background: rgba(15, 23, 42, 0.96);
      backdrop-filter: blur(12px);
      border-left: 1px solid #1e293b;
      padding: 18px;
      overflow-y: auto;
      display: none;
      z-index: 30;
      box-shadow: -8px 0 25px rgba(0,0,0,0.5);
    }}
    .sidebar-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
      padding-bottom: 10px;
      border-bottom: 1px solid #334155;
    }}
    .node-title {{
      font-size: 14px;
      font-weight: 700;
      color: #38bdf8;
      word-break: break-all;
      font-family: ui-monospace, monospace;
    }}
    .sec-title {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #94a3b8;
      margin: 14px 0 6px 0;
      font-weight: 700;
    }}
    .item-card {{
      background: #1e293b;
      padding: 6px 10px;
      border-radius: 5px;
      margin-bottom: 5px;
      font-size: 12px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: background 0.15s;
    }}
    .item-card:hover {{
      background: #334155;
      color: #38bdf8;
    }}
    .tag {{
      display: inline-block;
      padding: 2px 6px;
      background: #1e293b;
      border-radius: 4px;
      font-size: 11px;
      margin: 2px 3px 2px 0;
      color: #cbd5e1;
    }}
    .god-badge {{
      background: #78350f;
      color: #fde68a;
      border: 1px solid #d97706;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
    }}
    .legend {{
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: rgba(15, 23, 42, 0.9);
      backdrop-filter: blur(8px);
      border: 1px solid #334155;
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 11px;
      display: flex;
      gap: 12px;
      z-index: 10;
      pointer-events: none;
    }}
    .legend-item {{
      display: flex;
      align-items: center;
      gap: 5px;
    }}
    .dot {{
      width: 9px;
      height: 9px;
      border-radius: 50%;
    }}
    #tooltip {{
      position: absolute;
      background: rgba(15, 23, 42, 0.95);
      border: 1px solid #38bdf8;
      padding: 5px 9px;
      border-radius: 6px;
      font-size: 11px;
      pointer-events: none;
      display: none;
      z-index: 40;
      white-space: nowrap;
    }}
    #shortcuts-modal {{
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(15, 23, 42, 0.98);
      border: 1px solid #334155;
      box-shadow: 0 10px 40px rgba(0,0,0,0.7);
      border-radius: 10px;
      padding: 18px 22px;
      width: 350px;
      display: none;
      z-index: 50;
      backdrop-filter: blur(16px);
    }}
    .modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
      padding-bottom: 8px;
      border-bottom: 1px solid #334155;
      font-weight: 700;
      color: #38bdf8;
      font-size: 14px;
    }}
    .shortcut-row {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 7px 0;
      border-bottom: 1px solid #1e293b;
      font-size: 12px;
    }}
    .kbd {{
      background: #1e293b;
      color: #38bdf8;
      font-family: ui-monospace, monospace;
      padding: 2px 7px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 600;
      border: 1px solid #475569;
    }}
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>⚡ ReduceToken Graph</span>
      <span class="badge" id="visible-stats">{len(nodes_data)} Nodes • {len(links_data)} Edges</span>
    </div>
    <div class="toolbar">
      <input type="text" id="search-box" placeholder="Search file or symbol..." onkeyup="handleSearch(event)">
      
      <label class="filter-toggle" title="Group and enclose files inside their folder regions (c)">
        <input type="checkbox" id="group-folders" onchange="toggleFolderGrouping()" checked>
        📁 Folders
      </label>

      <label class="filter-toggle" title="Hide files with 0 dependencies and 0 callers (i)">
        <input type="checkbox" id="hide-isolated" onchange="updateFilters()" checked>
        Hide Isolated
      </label>

      <select id="category-filter" onchange="updateFilters()">
        <option value="all">All File Types</option>
        <option value="god">★ God Nodes Only</option>
        <option value="test">Tests Only</option>
        <option value="code">All Code Files</option>
        <option value="meta">Docs & Config</option>
        <optgroup id="lang-optgroup" label="By Language">
        </optgroup>
      </select>

      <select id="conn-filter" onchange="updateFilters()">
        <option value="all">All Connections</option>
        <option value="callers">Has Callers</option>
        <option value="deps">Has Dependencies</option>
        <option value="god">★ God Nodes Only</option>
      </select>

      <div class="slider-control" title="Adjust minimum clearance distance between nodes (invisible protective halo)">
        <span>Node Space</span>
        <input type="range" id="spacing-slider" min="30" max="240" value="90" oninput="updateSpacing(this.value)">
      </div>

      <button onclick="resetCamera()">Reset View</button>
      <button id="physics-btn" onclick="togglePhysics()">Pause</button>
      <button onclick="toggleShortcutsModal()" title="Keyboard Shortcuts (?)">⌨ Shortcuts</button>
    </div>
  </header>

  <div id="canvas-container">
    <canvas id="graph-canvas"></canvas>
    <div id="tooltip"></div>

    <div id="shortcuts-modal">
      <div class="modal-header">
        <span>⌨ Keyboard Shortcuts</span>
        <button onclick="toggleShortcutsModal()" style="padding: 2px 7px;">✕</button>
      </div>
      <div class="shortcut-row">
        <span>Close Panel / Modal / Deselect</span>
        <span class="kbd">Esc</span>
      </div>
      <div class="shortcut-row">
        <span>Focus Search Box</span>
        <div><span class="kbd">/</span> <span style="color:#64748b;">or</span> <span class="kbd">f</span></div>
      </div>
      <div class="shortcut-row">
        <span>Pause / Resume Physics</span>
        <span class="kbd">Space</span>
      </div>
      <div class="shortcut-row">
        <span>Reset Camera View</span>
        <span class="kbd">r</span>
      </div>
      <div class="shortcut-row">
        <span>Toggle Folder Regions (Clusters)</span>
        <span class="kbd">c</span>
      </div>
      <div class="shortcut-row">
        <span>Toggle Hide Isolated Files</span>
        <span class="kbd">i</span>
      </div>
      <div class="shortcut-row">
        <span>Toggle God Nodes Filter</span>
        <span class="kbd">g</span>
      </div>
      <div class="shortcut-row">
        <span>Toggle Shortcuts Help</span>
        <span class="kbd">?</span>
      </div>
    </div>

    <div id="sidebar">
      <div class="sidebar-header">
        <div>
          <div id="side-title" class="node-title">File</div>
          <div id="side-badge" style="margin-top: 4px;"></div>
        </div>
        <button onclick="closeSidebar()" style="padding: 2px 7px;">✕</button>
      </div>

      <div id="side-summary" style="font-size: 12px; color: #94a3b8; font-style: italic; margin-bottom: 12px;"></div>

      <div class="sec-title">Centrality Metrics</div>
      <div id="side-metrics" style="font-size: 12px; line-height: 1.6;"></div>

      <div class="sec-title">Incoming Callers (<span id="side-callers-cnt">0</span>)</div>
      <div id="side-callers"></div>

      <div class="sec-title">Outgoing Dependencies (<span id="side-deps-cnt">0</span>)</div>
      <div id="side-deps"></div>

      <div class="sec-title">Defined Symbols (<span id="side-syms-cnt">0</span>)</div>
      <div id="side-symbols" style="max-height: 240px; overflow-y: auto;"></div>
    </div>

    <div class="legend" id="legend"></div>
  </div>

  <script>
    const allNodes = {json.dumps(nodes_data)};
    const allLinks = {json.dumps(links_data)};
    const languageStyles = {json.dumps(LANGUAGE_STYLES)};
    const presentLangs = {json.dumps(present_langs)};

    const canvas = document.getElementById('graph-canvas');
    const ctx = canvas.getContext('2d');
    const container = document.getElementById('canvas-container');
    const tooltip = document.getElementById('tooltip');

    let width = 0, height = 0;
    let cameraX = 0, cameraY = 0, zoom = 1.0;
    let isDragging = false, dragStart = {{ x: 0, y: 0 }};
    let draggedNode = null;
    let selectedNode = null;
    let hoveredNode = null;
    let physicsRunning = true;

    // Filters & Clearance Spacing
    let groupFolders = true;
    let hideIsolated = true;
    let selectedCategory = "all";
    let selectedConn = "all";
    let nodeClearance = 90;

    // Filtered lists
    let activeNodes = [];
    let activeLinks = [];
    let activeFolders = [];
    let folderAnchors = {{}};
    let folderIndexMap = {{}};
    let folderBoxes = {{}};

    // Folder Dragging State
    let draggedFolder = null;
    let hoveredFolder = null;
    let dragFolderStartWorld = {{ x: 0, y: 0 }};
    let dragFolderInitialOffsets = [];
    let dragFolderInitialAnchor = {{ x: 0, y: 0 }};

    const FOLDER_STYLES = [
      {{ stroke: "rgba(56, 189, 248, 0.45)", fill: "rgba(56, 189, 248, 0.04)", text: "#38bdf8" }},  // sky
      {{ stroke: "rgba(167, 139, 250, 0.45)", fill: "rgba(167, 139, 250, 0.04)", text: "#a78bfa" }}, // purple
      {{ stroke: "rgba(52, 211, 153, 0.45)", fill: "rgba(52, 211, 153, 0.04)", text: "#34d399" }},  // emerald
      {{ stroke: "rgba(251, 146, 60, 0.45)", fill: "rgba(251, 146, 60, 0.04)", text: "#fb923c" }},  // orange
      {{ stroke: "rgba(244, 114, 182, 0.45)", fill: "rgba(244, 114, 182, 0.04)", text: "#f472b6" }}, // pink
      {{ stroke: "rgba(45, 212, 191, 0.45)", fill: "rgba(45, 212, 191, 0.04)", text: "#2dd4bf" }},  // teal
      {{ stroke: "rgba(250, 204, 21, 0.45)", fill: "rgba(250, 204, 21, 0.04)", text: "#facc15" }},  // yellow
      {{ stroke: "rgba(148, 163, 184, 0.45)", fill: "rgba(148, 163, 184, 0.04)", text: "#94a3b8" }}  // slate
    ];

    function layoutFolderNodes(f) {{
      const fNodes = activeNodes.filter(n => n.folder === f);
      if (fNodes.length === 0) return;

      // God nodes first, then alphabetical for neat organization
      fNodes.sort((a, b) => {{
        if (a.is_god && !b.is_god) return -1;
        if (!a.is_god && b.is_god) return 1;
        return a.label.localeCompare(b.label);
      }});

      const count = fNodes.length;
      let cols = 1;
      if (count >= 16) cols = 5;
      else if (count >= 10) cols = 4;
      else if (count >= 5) cols = 3;
      else if (count >= 2) cols = 2;

      const rows = Math.ceil(count / cols);
      const gapX = Math.max(160, nodeClearance * 1.5);
      const gapY = Math.max(95, nodeClearance * 0.95);

      const anchor = folderAnchors[f] || {{ x: 0, y: 0 }};

      for (let i = 0; i < count; i++) {{
        const c = i % cols;
        const r = Math.floor(i / cols);
        const offsetX = (c - (cols - 1) / 2) * gapX;
        const offsetY = (r - (rows - 1) / 2) * gapY + 18;
        fNodes[i].x = anchor.x + offsetX;
        fNodes[i].y = anchor.y + offsetY;
        fNodes[i].vx = 0;
        fNodes[i].vy = 0;
      }}
    }}

    function recalculateFolderAnchors() {{
      activeFolders = [...new Set(activeNodes.map(n => n.folder))].sort();
      folderIndexMap = {{}};
      activeFolders.forEach((f, idx) => {{
        folderIndexMap[f] = idx;
      }});

      const oldAnchors = {{ ...folderAnchors }};
      folderAnchors = {{}};
      if (activeFolders.length === 1) {{
        folderAnchors[activeFolders[0]] = oldAnchors[activeFolders[0]] || {{ x: 0, y: 0 }};
      }} else if (activeFolders.length > 1) {{
        const folderRadius = Math.max(480, activeFolders.length * 240 + (nodeClearance * 2.2));
        activeFolders.forEach((f, idx) => {{
          if (oldAnchors[f]) {{
            folderAnchors[f] = oldAnchors[f];
          }} else {{
            const angle = (idx / activeFolders.length) * 2 * Math.PI - (Math.PI / 2);
            folderAnchors[f] = {{
              x: Math.cos(angle) * folderRadius,
              y: Math.sin(angle) * folderRadius
            }};
          }}
        }});
      }}
    }}

    // Initial position partitioned by folder in clean collision-free grids
    activeNodes = allNodes;
    recalculateFolderAnchors();
    activeFolders.forEach(f => layoutFolderNodes(f));

    function resize() {{
      width = container.clientWidth;
      height = container.clientHeight;
      canvas.width = width * window.devicePixelRatio;
      canvas.height = height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    }}
    window.addEventListener('resize', resize);
    resize();
    cameraX = width / 2;
    cameraY = height / 2;

    function initLanguageOptions() {{
      const optGroup = document.getElementById('lang-optgroup');
      if (!optGroup) return;
      optGroup.innerHTML = '';
      for (const [lang, count] of Object.entries(presentLangs)) {{
        const info = languageStyles[lang] || {{ name: lang }};
        const opt = document.createElement('option');
        opt.value = "lang:" + lang;
        opt.textContent = `${{info.name}} (${{count}})`;
        optGroup.appendChild(opt);
      }}
    }}

    function buildLegend() {{
      const legendDiv = document.getElementById('legend');
      if (!legendDiv) return;
      let html = `<div class="legend-item"><span class="dot" style="background:#f59e0b;"></span> God Node</div>`;
      for (const [lang, count] of Object.entries(presentLangs)) {{
        const info = languageStyles[lang] || {{ name: lang, color: "#64748b" }};
        html += `<div class="legend-item"><span class="dot" style="background:${{info.color}};"></span> ${{info.name}}</div>`;
      }}
      const hasTests = allNodes.some(n => n.is_test);
      if (hasTests) {{
        html += `<div class="legend-item"><span class="dot" style="background:#8b5cf6;"></span> Tests</div>`;
      }}
      legendDiv.innerHTML = html;
    }}

    function updateFilters() {{
      hideIsolated = document.getElementById('hide-isolated').checked;
      selectedCategory = document.getElementById('category-filter').value;
      selectedConn = document.getElementById('conn-filter').value;

      activeNodes = allNodes.filter(n => {{
        if (hideIsolated && n.is_isolated) return false;
        if (selectedCategory === "god" && !n.is_god) return false;
        if (selectedCategory === "test" && !n.is_test) return false;
        if (selectedCategory === "code" && n.category !== "code") return false;
        if (selectedCategory === "meta" && n.category !== "meta") return false;
        if (selectedCategory.startsWith("lang:")) {{
          const tLang = selectedCategory.slice(5);
          if (n.language !== tLang) return false;
        }}
        if (selectedConn === "callers" && n.in_degree === 0) return false;
        if (selectedConn === "deps" && n.out_degree === 0) return false;
        if (selectedConn === "god" && !n.is_god) return false;
        return true;
      }});

      const activeSet = new Set(activeNodes.map(n => n.id));
      activeLinks = allLinks.filter(l => activeSet.has(l.src_id) && activeSet.has(l.tgt_id));

      recalculateFolderAnchors();
      if (groupFolders) {{
        activeFolders.forEach(f => layoutFolderNodes(f));
      }}
      document.getElementById('visible-stats').textContent = `${{activeNodes.length}} Nodes • ${{activeLinks.length}} Edges`;
    }}

    initLanguageOptions();
    buildLegend();
    updateFilters();

    function toggleFolderGrouping() {{
      groupFolders = document.getElementById('group-folders').checked;
      recalculateFolderAnchors();
      if (groupFolders) {{
        activeFolders.forEach(f => layoutFolderNodes(f));
      }} else {{
        // Free physics mode: give nodes small initial velocity to start simulation
        activeNodes.forEach(n => {{
          n.vx = (Math.random() - 0.5) * 2;
          n.vy = (Math.random() - 0.5) * 2;
        }});
      }}
    }}

    function updateSpacing(val) {{
      nodeClearance = parseFloat(val);
      if (groupFolders) {{
        activeFolders.forEach(f => layoutFolderNodes(f));
      }}
    }}

    // Physics Simulation with Anti-Collision & Zero-Jitter Damping
    function stepPhysics() {{
      if (!physicsRunning) return;

      // In Folder Grouping Mode: ZERO DRIFT, ZERO INTER-FOLDER PULLING!
      // Folders and nodes remain completely stationary unless dragged manually by the user.
      if (groupFolders) {{
        return;
      }}

      // 1. HARD CLEARANCE SEPARATION (Invisible Protective Circle)
      for (let i = 0; i < activeNodes.length; i++) {{
        const a = activeNodes[i];
        for (let j = i + 1; j < activeNodes.length; j++) {{
          const b = activeNodes[j];
          let dx = b.x - a.x;
          let dy = b.y - a.y;
          let dist = Math.sqrt(dx * dx + dy * dy) || 1;
          let minDist = a.radius + b.radius + nodeClearance;
          if (dist < minDist) {{
            let overlap = minDist - dist;
            let nx = dx / dist;
            let ny = dy / dist;
            // Immediate firm push
            a.x -= nx * overlap * 0.5;
            a.y -= ny * overlap * 0.5;
            b.x += nx * overlap * 0.5;
            b.y += ny * overlap * 0.5;
            // Damping relative velocity on collision
            a.vx *= 0.4;
            a.vy *= 0.4;
            b.vx *= 0.4;
            b.vy *= 0.4;
          }} else if (dist < minDist * 1.5) {{
            // Smooth repulsion zone
            let force = (nodeClearance * 18) / (dist * dist + 80);
            let fx = (dx / dist) * force;
            let fy = (dy / dist) * force;
            a.vx -= fx;
            a.vy -= fy;
            b.vx += fx;
            b.vy += fy;
          }}
        }}
      }}

      // 2. Spring attraction along links
      for (let i = 0; i < activeLinks.length; i++) {{
        const l = activeLinks[i];
        const a = allNodes[l.source];
        const b = allNodes[l.target];

        // When Folder Partitioning is ON: do NOT pull cross-folder edges!
        if (groupFolders && a.folder !== b.folder) {{
          continue;
        }}

        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
        let idealSpring = (a.radius + b.radius + nodeClearance) * 1.35;
        let delta = dist - idealSpring;
        let force = Math.max(-2.0, Math.min(2.0, delta * 0.018));
        let fx = (dx / dist) * force;
        let fy = (dy / dist) * force;
        a.vx += fx;
        a.vy += fy;
        b.vx -= fx;
        b.vy -= fy;
      }}

      // 3. Gravity & high-friction damping (eliminates bounce & jitter)
      const damping = 0.56;
      const maxSpeed = 4.0;
      for (let i = 0; i < activeNodes.length; i++) {{
        const n = activeNodes[i];
        if (n === draggedNode) continue;

        if (groupFolders) {{
          const anchor = folderAnchors[n.folder] || {{ x: 0, y: 0 }};
          n.vx += (anchor.x - n.x) * 0.018;
          n.vy += (anchor.y - n.y) * 0.018;
        }} else {{
          n.vx -= n.x * 0.003;
          n.vy -= n.y * 0.003;
        }}

        n.vx *= damping;
        n.vy *= damping;

        const spd = Math.hypot(n.vx, n.vy);
        if (spd > maxSpeed) {{
          n.vx = (n.vx / spd) * maxSpeed;
          n.vy = (n.vy / spd) * maxSpeed;
        }}

        if (Math.abs(n.vx) < 0.015) n.vx = 0;
        if (Math.abs(n.vy) < 0.015) n.vy = 0;

        n.x += n.vx;
        n.y += n.vy;
      }}
    }}

    // Render Loop
    function render() {{
      stepPhysics();

      ctx.clearRect(0, 0, width, height);
      ctx.save();
      ctx.translate(cameraX, cameraY);
      ctx.scale(zoom, zoom);

      // 0. Draw Folder Enclosures (if groupFolders is active)
      folderBoxes = {{}};
      if (groupFolders && activeFolders.length > 0) {{
        activeFolders.forEach(f => {{
          const fNodes = activeNodes.filter(n => n.folder === f);
          if (fNodes.length === 0) return;

          let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
          for (let i = 0; i < fNodes.length; i++) {{
            const fn = fNodes[i];
            if (fn.x < minX) minX = fn.x;
            if (fn.y < minY) minY = fn.y;
            if (fn.x > maxX) maxX = fn.x;
            if (fn.y > maxY) maxY = fn.y;
          }}

          const padX = 45 + (nodeClearance * 0.15);
          const padY = 38 + (nodeClearance * 0.15);
          const boxX = minX - padX;
          const boxY = minY - padY;
          const boxW = (maxX - minX) + padX * 2;
          const boxH = (maxY - minY) + padY * 2;

          const fIdx = folderIndexMap[f] || 0;
          const fStyle = FOLDER_STYLES[fIdx % FOLDER_STYLES.length];

          // Badge measurements with grab handle indicator
          const badgeText = `📁 ${{f}}/ (${{fNodes.length}} files)  ⠿`;
          const fFontSize = Math.max(12, 13 / zoom);
          ctx.font = `600 ${{fFontSize}}px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
          const textW = ctx.measureText(badgeText).width;
          const pillW = textW + (22 / zoom);
          const pillH = fFontSize * 1.8;
          const pillX = boxX + (14 / zoom);
          const pillY = boxY - (pillH / 2);

          // Save box measurements for exact hit testing
          folderBoxes[f] = {{
            boxX, boxY, boxW, boxH,
            pillX, pillY, pillW, pillH,
            fStyle
          }};

          const isHovered = (hoveredFolder === f);
          const isFolderDragged = (draggedFolder === f);

          // Draw enclosure boundary
          ctx.beginPath();
          if (ctx.roundRect) {{
            ctx.roundRect(boxX, boxY, boxW, boxH, 16);
          }} else {{
            ctx.rect(boxX, boxY, boxW, boxH);
          }}
          ctx.fillStyle = (isHovered || isFolderDragged) ? fStyle.fill.replace("0.04", "0.10") : fStyle.fill;
          ctx.fill();
          ctx.strokeStyle = (isHovered || isFolderDragged) ? fStyle.text : fStyle.stroke;
          ctx.lineWidth = (isHovered || isFolderDragged ? 2.2 : 1.4) / zoom;
          ctx.setLineDash([6 / zoom, 4 / zoom]);
          ctx.stroke();
          ctx.setLineDash([]);

          // Folder Header Badge (Pill)
          ctx.beginPath();
          if (ctx.roundRect) {{
            ctx.roundRect(pillX, pillY, pillW, pillH, 6 / zoom);
          }} else {{
            ctx.rect(pillX, pillY, pillW, pillH);
          }}
          ctx.fillStyle = (isHovered || isFolderDragged) ? "rgba(30, 41, 59, 0.98)" : "rgba(15, 23, 42, 0.94)";
          ctx.fill();
          ctx.strokeStyle = (isHovered || isFolderDragged) ? fStyle.text : fStyle.stroke;
          ctx.lineWidth = (isHovered || isFolderDragged ? 1.8 : 1.0) / zoom;
          ctx.stroke();

          ctx.fillStyle = fStyle.text;
          ctx.textAlign = "left";
          ctx.textBaseline = "middle";
          ctx.fillText(badgeText, pillX + (10 / zoom), pillY + (pillH / 2));
        }});
      }}

      const activeNode = selectedNode || hoveredNode;
      const connectedSet = new Set();
      if (activeNode) {{
        connectedSet.add(activeNode.id);
        allLinks.forEach(l => {{
          if (l.src_id === activeNode.id) connectedSet.add(l.tgt_id);
          if (l.tgt_id === activeNode.id) connectedSet.add(l.src_id);
        }});
      }}

      // Draw Edges
      activeLinks.forEach(l => {{
        const a = allNodes[l.source];
        const b = allNodes[l.target];

        let strokeColor = "#334155";
        let lineWidth = 1.2;

        if (activeNode) {{
          if (l.src_id === activeNode.id) {{
            strokeColor = "#f43f5e"; // Rose = Outbound
            lineWidth = 2.4;
          }} else if (l.tgt_id === activeNode.id) {{
            strokeColor = "#10b981"; // Emerald = Inbound
            lineWidth = 2.4;
          }} else {{
            strokeColor = "#1e293b";
          }}
        }}

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth / zoom;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(b.y - a.y, b.x - a.x);
        const arrowDist = b.radius + 5;
        const arrowX = b.x - Math.cos(angle) * arrowDist;
        const arrowY = b.y - Math.sin(angle) * arrowDist;
        const arrowLen = 6 / zoom;

        ctx.fillStyle = strokeColor;
        ctx.beginPath();
        ctx.moveTo(arrowX, arrowY);
        ctx.lineTo(arrowX - arrowLen * Math.cos(angle - Math.PI / 6), arrowY - arrowLen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(arrowX - arrowLen * Math.cos(angle + Math.PI / 6), arrowY - arrowLen * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();
      }});

      // Draw Nodes
      activeNodes.forEach(n => {{
        const isDimmed = activeNode && !connectedSet.has(n.id);
        const isSelected = (selectedNode && selectedNode.id === n.id);

        ctx.globalAlpha = isDimmed ? 0.2 : 1.0;

        // Hover clearance halo (vòng bảo vệ vô hình)
        if (hoveredNode && hoveredNode.id === n.id) {{
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + (nodeClearance / 2), 0, Math.PI * 2);
          ctx.strokeStyle = "rgba(56, 189, 248, 0.25)";
          ctx.lineWidth = 1.0 / zoom;
          ctx.setLineDash([4 / zoom, 4 / zoom]);
          ctx.stroke();
          ctx.setLineDash([]);
        }}

        // Glow for God nodes or Selected
        if (n.is_god || isSelected) {{
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + (isSelected ? 5 : 3), 0, Math.PI * 2);
          ctx.fillStyle = isSelected ? "rgba(56, 189, 248, 0.45)" : "rgba(245, 158, 11, 0.35)";
          ctx.fill();
        }}

        // Node Circle
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        ctx.strokeStyle = isSelected ? "#ffffff" : n.border_color;
        ctx.lineWidth = (isSelected ? 2.5 : 1.5) / zoom;
        ctx.stroke();

        // Label with background pill for perfect readability
        const labelText = n.is_god ? "★ " + n.label : n.label;
        const fontSize = Math.max(10, 11 / zoom);
        ctx.font = `${{fontSize}}px ui-monospace, monospace`;

        const textMetrics = ctx.measureText(labelText);
        const textW = textMetrics.width;
        const textH = fontSize * 1.2;
        const labelY = n.y + n.radius + (12 / zoom);

        // Draw pill background
        ctx.fillStyle = isDimmed ? "rgba(15, 23, 42, 0.6)" : "rgba(15, 23, 42, 0.85)";
        ctx.fillRect(n.x - textW / 2 - 3, labelY - textH + 2, textW + 6, textH + 2);

        // Draw text
        ctx.fillStyle = isDimmed ? "#64748b" : (n.is_god ? "#fde68a" : "#f8fafc");
        ctx.textAlign = "center";
        ctx.fillText(labelText, n.x, labelY);

        ctx.globalAlpha = 1.0;
      }});

      ctx.restore();
      requestAnimationFrame(render);
    }}
    requestAnimationFrame(render);

    function screenToWorld(sx, sy) {{
      return {{
        x: (sx - cameraX) / zoom,
        y: (sy - cameraY) / zoom
      }};
    }}

    function findNodeAt(sx, sy) {{
      const p = screenToWorld(sx, sy);
      for (let i = activeNodes.length - 1; i >= 0; i--) {{
        const n = activeNodes[i];
        const dx = p.x - n.x;
        const dy = p.y - n.y;
        if (dx * dx + dy * dy <= (n.radius + 4) * (n.radius + 4)) {{
          return n;
        }}
      }}
      return null;
    }}

    function findFolderAt(wx, wy) {{
      if (!groupFolders) return null;
      // 1. Highest priority: folder header badge pill
      for (let i = 0; i < activeFolders.length; i++) {{
        const f = activeFolders[i];
        const b = folderBoxes[f];
        if (!b) continue;
        if (wx >= b.pillX && wx <= b.pillX + b.pillW &&
            wy >= b.pillY && wy <= b.pillY + b.pillH) {{
          return {{ folder: f, isBadge: true }};
        }}
      }}
      // 2. Second priority: folder enclosure box
      for (let i = 0; i < activeFolders.length; i++) {{
        const f = activeFolders[i];
        const b = folderBoxes[f];
        if (!b) continue;
        if (wx >= b.boxX && wx <= b.boxX + b.boxW &&
            wy >= b.boxY && wy <= b.boxY + b.boxH) {{
          return {{ folder: f, isBadge: false }};
        }}
      }}
      return null;
    }}

    // Mouse & Dragging events
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());

    container.addEventListener('mousedown', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const p = screenToWorld(sx, sy);

      // Middle click or Right click: Pan camera
      if (e.button === 1 || e.button === 2) {{
        isDragging = true;
        dragStart.x = e.clientX - cameraX;
        dragStart.y = e.clientY - cameraY;
        return;
      }}

      // Left click:
      // 1. Check if clicking directly on a specific Node
      const hitNode = findNodeAt(sx, sy);
      if (hitNode) {{
        draggedNode = hitNode;
        container.style.cursor = 'grabbing';
        return;
      }}

      // 2. Check if clicking on a Folder (Header Badge or Enclosure Box)
      if (groupFolders) {{
        const hitFolderInfo = findFolderAt(p.x, p.y);
        if (hitFolderInfo) {{
          draggedFolder = hitFolderInfo.folder;
          dragFolderStartWorld = p;
          const fNodes = activeNodes.filter(n => n.folder === draggedFolder);
          dragFolderInitialOffsets = fNodes.map(n => ({{ node: n, initX: n.x, initY: n.y }}));
          dragFolderInitialAnchor = folderAnchors[draggedFolder] ? {{ ...folderAnchors[draggedFolder] }} : {{ x: 0, y: 0 }};
          container.style.cursor = 'grabbing';
          return;
        }}
      }}

      // 3. Otherwise, pan canvas camera view
      isDragging = true;
      dragStart.x = e.clientX - cameraX;
      dragStart.y = e.clientY - cameraY;
      container.style.cursor = 'move';
    }});

    window.addEventListener('mousemove', (e) => {{
      const rect = canvas.getBoundingClientRect();
      const sx = e.clientX - rect.left;
      const sy = e.clientY - rect.top;
      const p = screenToWorld(sx, sy);

      // 1. Dragging a single node
      if (draggedNode) {{
        draggedNode.x = p.x;
        draggedNode.y = p.y;
        draggedNode.vx = 0;
        draggedNode.vy = 0;
        container.style.cursor = 'grabbing';
        return;
      }}

      // 2. Dragging an entire folder (all nodes move together smoothly!)
      if (draggedFolder) {{
        const dx = p.x - dragFolderStartWorld.x;
        const dy = p.y - dragFolderStartWorld.y;
        dragFolderInitialOffsets.forEach(item => {{
          item.node.x = item.initX + dx;
          item.node.y = item.initY + dy;
          item.node.vx = 0;
          item.node.vy = 0;
        }});
        if (folderAnchors[draggedFolder]) {{
          folderAnchors[draggedFolder].x = dragFolderInitialAnchor.x + dx;
          folderAnchors[draggedFolder].y = dragFolderInitialAnchor.y + dy;
        }}
        container.style.cursor = 'grabbing';
        return;
      }}

      // 3. Panning camera
      if (isDragging) {{
        cameraX = e.clientX - dragStart.x;
        cameraY = e.clientY - dragStart.y;
        container.style.cursor = 'move';
        return;
      }}

      // 4. Hover states & tooltips
      const hit = findNodeAt(sx, sy);
      if (hit !== hoveredNode) {{
        hoveredNode = hit;
        if (hoveredNode) {{
          tooltip.style.display = "block";
          tooltip.style.left = (e.clientX + 14) + "px";
          tooltip.style.top = (e.clientY + 14) + "px";
          tooltip.innerHTML = `<b>${{hoveredNode.id}}</b><br><span style="color:#94a3b8">📁 ${{hoveredNode.folder}}/ • ${{hoveredNode.lang_name}} • Callers: ${{hoveredNode.in_degree}} | Deps: ${{hoveredNode.out_degree}} | Symbols: ${{hoveredNode.symbols_count}}</span>`;
          container.style.cursor = 'pointer';
        }} else {{
          tooltip.style.display = "none";
        }}
      }}

      if (!hoveredNode && groupFolders) {{
        const hitFolderInfo = findFolderAt(p.x, p.y);
        const newHoverFolder = hitFolderInfo ? hitFolderInfo.folder : null;
        if (newHoverFolder !== hoveredFolder) {{
          hoveredFolder = newHoverFolder;
        }}
        if (hitFolderInfo) {{
          container.style.cursor = 'grab';
          if (hitFolderInfo.isBadge) {{
            tooltip.style.display = "block";
            tooltip.style.left = (e.clientX + 14) + "px";
            tooltip.style.top = (e.clientY + 14) + "px";
            tooltip.innerHTML = `<b>📁 ${{hitFolderInfo.folder}}/</b><br><span style="color:#38bdf8">Drag to move entire folder</span>`;
          }}
        }} else {{
          container.style.cursor = 'default';
          if (!hoveredNode) tooltip.style.display = "none";
        }}
      }} else if (!hoveredNode) {{
        hoveredFolder = null;
        container.style.cursor = 'default';
      }}
    }});

    window.addEventListener('mouseup', () => {{
      if (draggedNode) {{
        draggedNode.vx = 0;
        draggedNode.vy = 0;
        if (!isDragging && !draggedFolder) {{
          selectNode(draggedNode);
        }}
      }}
      if (draggedFolder) {{
        dragFolderInitialOffsets.forEach(item => {{
          item.node.vx = 0;
          item.node.vy = 0;
        }});
      }}
      draggedNode = null;
      draggedFolder = null;
      dragFolderInitialOffsets = [];
      isDragging = false;
      container.style.cursor = 'default';
    }});

    // Isolate wheel events in sidebar & modal so scrolling definitions does NOT zoom the canvas
    const sidebarEl = document.getElementById('sidebar');
    sidebarEl.addEventListener('wheel', (e) => {{
      e.stopPropagation();
    }}, {{ passive: true }});

    const modalEl = document.getElementById('shortcuts-modal');
    modalEl.addEventListener('wheel', (e) => {{
      e.stopPropagation();
    }}, {{ passive: true }});

    container.addEventListener('wheel', (e) => {{
      if (e.target.closest('#sidebar') || e.target.closest('#shortcuts-modal')) {{
        return;
      }}
      e.preventDefault();
      const zoomFactor = e.deltaY < 0 ? 1.15 : 0.87;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      cameraX = mx - (mx - cameraX) * zoomFactor;
      cameraY = my - (my - cameraY) * zoomFactor;
      zoom *= zoomFactor;
      zoom = Math.max(0.12, Math.min(zoom, 4.0));
    }}, {{ passive: false }});

    function selectNode(node) {{
      selectedNode = node;
      showSidebar(node);
    }}

    function showSidebar(node) {{
      document.getElementById('sidebar').style.display = 'block';
      document.getElementById('side-title').textContent = node.id;
      document.getElementById('side-summary').textContent = node.summary ? `"${{node.summary}}"` : "No top-level docstring.";

      const badgeDiv = document.getElementById('side-badge');
      badgeDiv.innerHTML = '';
      if (node.is_god) {{
        badgeDiv.innerHTML += '<span class="god-badge">★ CRITICAL GOD NODE</span> ';
      }}
      badgeDiv.innerHTML += `<span class="tag">📁 ${{node.folder}}</span> `;
      badgeDiv.innerHTML += `<span class="tag">${{node.lang_name}}</span>`;

      document.getElementById('side-metrics').innerHTML = `
        • <b>Folder:</b> ${{node.folder_path}}<br>
        • <b>In-degree (Callers):</b> ${{node.in_degree}} files<br>
        • <b>Out-degree (Dependencies):</b> ${{node.out_degree}} files<br>
        • <b>Total Symbols Defined:</b> ${{node.symbols_count}}
      `;

      // Callers
      const callers = allLinks.filter(l => l.tgt_id === node.id).map(l => l.src_id);
      document.getElementById('side-callers-cnt').textContent = callers.length;
      const callersDiv = document.getElementById('side-callers');
      callersDiv.innerHTML = callers.length === 0
        ? '<div style="font-size:11px;color:#64748b;">(No incoming callers - Root / Entry point)</div>'
        : callers.map(c => `<div class="item-card" onclick="jumpToNode('${{c}}')"><span>📄 ${{c}}</span><span style="color:#10b981;font-size:10px;">CALLER</span></div>`).join('');

      // Dependencies
      const deps = allLinks.filter(l => l.src_id === node.id).map(l => l.tgt_id);
      document.getElementById('side-deps-cnt').textContent = deps.length;
      const depsDiv = document.getElementById('side-deps');
      depsDiv.innerHTML = deps.length === 0
        ? '<div style="font-size:11px;color:#64748b;">(Zero internal dependencies)</div>'
        : deps.map(d => `<div class="item-card" onclick="jumpToNode('${{d}}')"><span>📦 ${{d}}</span><span style="color:#f43f5e;font-size:10px;">DEPENDENCY</span></div>`).join('');

      // Symbols
      document.getElementById('side-syms-cnt').textContent = node.symbols.length;
      const symDiv = document.getElementById('side-symbols');
      if (node.symbols.length === 0) {{
        symDiv.innerHTML = '<div style="font-size:11px;color:#64748b;">No symbols extracted</div>';
      }} else {{
        symDiv.innerHTML = node.symbols.map(s => `
          <div class="item-card" style="cursor:default;">
            <div>
              <span style="color:#38bdf8;font-weight:600;">[${{s.kind}}]</span> <b>${{s.name}}</b>
              ${{s.doc ? `<div style="font-size:11px;color:#94a3b8;">${{s.doc}}</div>` : ''}}
            </div>
            <span style="color:#64748b;font-family:monospace;font-size:11px;">L${{s.line}}</span>
          </div>
        `).join('');
      }}
    }}

    function closeSidebar() {{
      document.getElementById('sidebar').style.display = 'none';
      selectedNode = null;
    }}

    function jumpToNode(id) {{
      const target = allNodes.find(n => n.id === id);
      if (target) {{
        selectNode(target);
        cameraX = (width / 2) - (target.x * zoom);
        cameraY = (height / 2) - (target.y * zoom);
      }}
    }}

    function resetCamera() {{
      if (activeNodes.length === 0) {{
        cameraX = width / 2;
        cameraY = height / 2;
        zoom = 1.0;
        return;
      }}
      let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      activeNodes.forEach(n => {{
        if (n.x < minX) minX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.x > maxX) maxX = n.x;
        if (n.y > maxY) maxY = n.y;
      }});
      const graphW = (maxX - minX) + 160;
      const graphH = (maxY - minY) + 160;
      const fitZoom = Math.min(width / graphW, height / graphH, 1.2);
      zoom = Math.max(0.18, fitZoom);
      const centerX = (minX + maxX) / 2;
      const centerY = (minY + maxY) / 2;
      cameraX = (width / 2) - (centerX * zoom);
      cameraY = (height / 2) - (centerY * zoom);
    }}

    function togglePhysics() {{
      physicsRunning = !physicsRunning;
      const btn = document.getElementById('physics-btn');
      btn.textContent = physicsRunning ? 'Pause' : 'Resume';
      btn.classList.toggle('btn-active', !physicsRunning);
    }}

    function handleSearch(e) {{
      const q = e.target.value.toLowerCase().trim();
      if (!q) return;

      const hit = activeNodes.find(n => n.id.toLowerCase().includes(q) || n.symbols.some(s => s.name.toLowerCase().includes(q)));
      if (hit && (e.key === 'Enter' || q.length >= 3)) {{
        jumpToNode(hit.id);
      }}
    }}

    function toggleShortcutsModal() {{
      const modal = document.getElementById('shortcuts-modal');
      modal.style.display = (modal.style.display === 'block') ? 'none' : 'block';
    }}

    window.addEventListener('keydown', (e) => {{
      const searchBox = document.getElementById('search-box');
      const isInputFocused = (document.activeElement === searchBox);

      if (e.key === 'Escape') {{
        const modal = document.getElementById('shortcuts-modal');
        if (modal.style.display === 'block') {{
          modal.style.display = 'none';
          return;
        }}
        if (isInputFocused) {{
          searchBox.blur();
          return;
        }}
        if (document.getElementById('sidebar').style.display === 'block') {{
          closeSidebar();
          return;
        }}
        selectedNode = null;
        return;
      }}

      // Avoid capturing regular typing when user is in search input
      if (isInputFocused) return;

      if (e.key === '/' || e.key === 'f' || e.key === 'F') {{
        e.preventDefault();
        searchBox.focus();
        searchBox.select();
      }} else if (e.key === ' ') {{
        e.preventDefault();
        togglePhysics();
      }} else if (e.key === 'r' || e.key === 'R') {{
        e.preventDefault();
        resetCamera();
      }} else if (e.key === 'c' || e.key === 'C') {{
        e.preventDefault();
        const chk = document.getElementById('group-folders');
        chk.checked = !chk.checked;
        toggleFolderGrouping();
      }} else if (e.key === 'i' || e.key === 'I') {{
        e.preventDefault();
        const chk = document.getElementById('hide-isolated');
        chk.checked = !chk.checked;
        updateFilters();
      }} else if (e.key === 'g' || e.key === 'G') {{
        e.preventDefault();
        const connSel = document.getElementById('conn-filter');
        connSel.value = (connSel.value === 'god') ? 'all' : 'god';
        updateFilters();
      }} else if (e.key === '?') {{
        e.preventDefault();
        toggleShortcutsModal();
      }}
    }});
  </script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    return output_path


def find_chrome_binary() -> Optional[str]:
    """Find Google Chrome executable across platforms."""
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    elif sys.platform == "darwin":
        cand = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.isfile(cand):
            return cand
    elif sys.platform.startswith("linux"):
        for cand in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
            if shutil.which(cand):
                return cand
    return None


def launch_browser(target_path: Path):
    """Directly launch Google Chrome (or system default browser) and bring it to foreground."""
    resolved = str(target_path.resolve())

    # 1. Windows: Try launching Chrome via shell start, then direct binary
    if sys.platform == "win32":
        try:
            subprocess.run(f'start chrome "{resolved}"', shell=True, check=False)
            return
        except Exception:
            pass

        chrome = find_chrome_binary()
        if chrome:
            try:
                subprocess.Popen([chrome, resolved], shell=False)
                return
            except Exception:
                pass

        try:
            subprocess.run(f'start "" "{resolved}"', shell=True, check=False)
            return
        except Exception:
            pass

        try:
            os.startfile(resolved)
            return
        except Exception:
            pass

    # 3. macOS
    elif sys.platform == "darwin":
        try:
            subprocess.run(["open", resolved], check=False)
            return
        except Exception:
            pass

    # 4. Linux
    elif sys.platform.startswith("linux"):
        try:
            subprocess.run(["xdg-open", resolved], check=False)
            return
        except Exception:
            pass

    # 5. Standard fallback
    webbrowser.open(target_path.resolve().as_uri())


def open_web_graph(root_dir: Path) -> Path:
    """Regenerate latest Web Graph HTML and immediately open it in default browser."""
    from reducetoken.cli import run_pipeline
    graph = run_pipeline(root_dir, force=False, verbose=False)
    html_file = root_dir / ".codegraph" / "graph.html"
    generate_web_graph_html(graph, html_file)
    launch_browser(html_file)
    return html_file
