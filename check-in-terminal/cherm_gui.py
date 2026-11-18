"""
Cherm Web GUI — Minimalist Drag & Drop Code & Project Auditor
Fast, distraction-free code auditor supporting single files, snippets, and entire folders/projects.
Provides file tree exploration, code preview, project-wide security audits, and per-file diagnostics.
"""

import os
import sys
import json
import time
import socket
import webbrowser
import threading
from urllib.parse import urlparse
from http.server import BaseHTTPRequestHandler

try:
    from http.server import ThreadingHTTPServer as BaseServer
except ImportError:
    from http.server import HTTPServer as BaseServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    import cherm_mcp
except ImportError:
    cherm_mcp = None

INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cherm — Code & Project Auditor</title>
    <style>
        :root {
            --bg: #f8fafc;
            --surface: #ffffff;
            --border: #e2e8f0;
            --border-hover: #94a3b8;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --btn-bg: #0f172a;
            --btn-hover: #1e293b;
            --success: #059669;
            --success-bg: #ecfdf5;
            --warning: #d97706;
            --warning-bg: #fffbeb;
            --danger: #dc2626;
            --danger-bg: #fef2f2;
            --radius: 8px;
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            min-height: 100vh;
            padding: 36px 20px;
        }

        .container {
            max-width: 900px;
            margin: 0 auto;
        }

        /* Top Header */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .brand h1 {
            font-size: 20px;
            font-weight: 700;
            letter-spacing: -0.5px;
            color: var(--text-main);
        }

        .brand p {
            font-size: 13px;
            color: var(--text-muted);
        }

        .port-badge {
            font-size: 12px;
            color: var(--text-muted);
            background: #ffffff;
            padding: 4px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            font-family: var(--font-mono);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background-color: var(--success);
        }

        /* Mode Switcher */
        .tabs {
            display: flex;
            gap: 8px;
            margin-bottom: 18px;
            flex-wrap: wrap;
        }

        .tab-btn {
            background: #ffffff;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 7px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.12s ease;
        }

        .tab-btn.active {
            background: var(--text-main);
            color: #ffffff;
            border-color: var(--text-main);
            font-weight: 600;
        }

        /* Card Container */
        .card {
            background-color: var(--surface);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            margin-bottom: 24px;
        }

        /* Drag & Drop Area */
        .dropzone {
            border: 2px dashed #cbd5e1;
            border-radius: 10px;
            padding: 40px 20px;
            text-align: center;
            background-color: #fafbfc;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .dropzone:hover {
            border-color: #64748b;
            background-color: #f1f5f9;
        }

        .dropzone.dragover {
            border-color: var(--text-main);
            background-color: #f1f5f9;
            transform: scale(0.998);
        }

        .dropzone-icon {
            width: 44px;
            height: 44px;
            margin: 0 auto 12px;
            color: #64748b;
        }

        .dropzone-title {
            font-size: 16px;
            font-weight: 600;
            margin-bottom: 4px;
            color: var(--text-main);
        }

        .dropzone-sub {
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 18px;
        }

        .dropzone-actions {
            display: flex;
            justify-content: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        .btn-browse {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background-color: #ffffff;
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 8px 18px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.12s ease;
        }

        .btn-browse:hover {
            background-color: #f1f5f9;
            border-color: #94a3b8;
        }

        /* Loaded Single File Box */
        .file-loaded-panel {
            display: none;
            margin-top: 18px;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
        }

        .file-loaded-panel.active {
            display: block;
        }

        .file-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .file-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .ext-badge {
            background: var(--text-main);
            color: #ffffff;
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            padding: 4px 8px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .file-title {
            font-family: var(--font-mono);
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
        }

        .file-stats {
            font-size: 12px;
            color: var(--text-muted);
            font-family: var(--font-mono);
            margin-top: 2px;
        }

        .btn-clear {
            background: none;
            border: 1px solid var(--border);
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            color: var(--text-muted);
            cursor: pointer;
        }

        .btn-clear:hover {
            color: var(--danger);
            border-color: var(--danger);
        }

        /* Loaded Folder Panel */
        .folder-loaded-panel {
            display: none;
            margin-top: 18px;
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 16px;
        }

        .folder-loaded-panel.active {
            display: block;
        }

        .folder-toolbar {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
            align-items: center;
        }

        .search-input {
            flex: 1;
            padding: 7px 12px;
            border: 1px solid var(--border);
            border-radius: 6px;
            font-size: 12px;
            font-family: var(--font-mono);
            outline: none;
            background: #ffffff;
        }

        .search-input:focus {
            border-color: var(--text-main);
        }

        .folder-files-container {
            display: grid;
            grid-template-columns: 320px 1fr;
            gap: 12px;
            margin-bottom: 14px;
        }

        @media (max-width: 768px) {
            .folder-files-container {
                grid-template-columns: 1fr;
            }
        }

        .folder-file-list {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            max-height: 220px;
            overflow-y: auto;
        }

        .folder-file-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 7px 10px;
            border-bottom: 1px solid #f1f5f9;
            font-size: 12px;
            font-family: var(--font-mono);
            cursor: pointer;
            transition: background 0.1s ease;
        }

        .folder-file-item:last-child {
            border-bottom: none;
        }

        .folder-file-item:hover {
            background-color: #f8fafc;
        }

        .folder-file-item.active {
            background-color: #f1f5f9;
            font-weight: 600;
        }

        .item-left {
            display: flex;
            align-items: center;
            gap: 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .tag-badge {
            font-size: 10px;
            padding: 2px 5px;
            border-radius: 3px;
            background: #e2e8f0;
            color: #334155;
            font-weight: 700;
        }

        .item-stats {
            color: var(--text-muted);
            font-size: 11px;
            white-space: nowrap;
        }

        /* Preview box */
        .preview-box {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            max-height: 220px;
            overflow-y: auto;
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.6;
            color: #334155;
            white-space: pre-wrap;
            word-break: break-all;
        }

        /* Action Row */
        .action-row {
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }

        .btn-check {
            background-color: var(--btn-bg);
            color: #ffffff;
            border: none;
            padding: 11px 24px;
            border-radius: var(--radius);
            font-size: 13px;
            font-weight: 700;
            cursor: pointer;
            transition: background-color 0.15s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-check:hover {
            background-color: var(--btn-hover);
        }

        .btn-check:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Local Mode Panel */
        .local-panel {
            display: none;
        }

        .local-panel.active {
            display: block;
        }

        .local-input-row {
            display: flex;
            gap: 10px;
            margin-bottom: 12px;
        }

        .local-path-input {
            flex: 1;
            padding: 10px 14px;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            font-family: var(--font-mono);
            font-size: 13px;
            outline: none;
            background: #ffffff;
        }

        .local-path-input:focus {
            border-color: var(--text-main);
        }

        /* Paste Mode Area */
        .paste-panel {
            display: none;
        }

        .paste-panel.active {
            display: block;
        }

        textarea {
            width: 100%;
            height: 220px;
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px;
            font-family: var(--font-mono);
            font-size: 13px;
            line-height: 1.5;
            color: var(--text-main);
            outline: none;
            resize: vertical;
            margin-bottom: 14px;
        }

        textarea:focus {
            border-color: var(--text-main);
        }

        /* Loading */
        .loading-state {
            display: none;
            text-align: center;
            padding: 36px 20px;
        }

        .loading-state.active {
            display: block;
        }

        .spinner {
            width: 28px;
            height: 28px;
            border: 2px solid #e2e8f0;
            border-top-color: var(--btn-bg);
            border-radius: 50%;
            animation: spin 0.6s linear infinite;
            margin: 0 auto 12px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Results */
        .results-panel {
            display: none;
            margin-top: 24px;
        }

        .results-panel.active {
            display: block;
        }

        .grade-banner {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px 22px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .grade-badge {
            font-size: 14px;
            font-weight: 700;
            padding: 6px 14px;
            border-radius: 6px;
            font-family: var(--font-mono);
        }

        .grade-a {
            background-color: var(--success-bg);
            color: var(--success);
            border: 1px solid rgba(5, 150, 105, 0.25);
        }

        .grade-b {
            background-color: var(--warning-bg);
            color: var(--warning);
            border: 1px solid rgba(217, 119, 6, 0.25);
        }

        .grade-c {
            background-color: var(--danger-bg);
            color: var(--danger);
            border: 1px solid rgba(220, 38, 38, 0.25);
        }

        .grade-f {
            background-color: var(--danger-bg);
            color: var(--danger);
            border: 1px solid rgba(220, 38, 38, 0.4);
            font-weight: 800;
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
        }

        @media (max-width: 600px) {
            .metrics-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        .metric-box {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 14px 16px;
        }

        .metric-val {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-main);
            font-family: var(--font-mono);
        }

        .metric-label {
            font-size: 12px;
            color: var(--text-muted);
            margin-top: 2px;
        }

        /* Findings Card */
        .findings-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 22px;
            margin-bottom: 16px;
        }

        .findings-card h3 {
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 12px;
            color: var(--text-main);
        }

        .finding-item {
            padding: 12px 14px;
            border-radius: 6px;
            border: 1px solid var(--border);
            margin-bottom: 8px;
            font-size: 13px;
            line-height: 1.5;
            background: #ffffff;
        }

        .finding-item.fatal {
            border-left: 3px solid var(--danger);
            background: #fffafa;
        }

        .finding-item.warning {
            border-left: 3px solid var(--warning);
            background: #fffdf5;
        }

        .finding-item.clean {
            border-left: 3px solid var(--success);
            background: #f6fdf9;
            color: var(--success);
            font-weight: 500;
        }

        /* Per-file results table */
        .file-results-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 22px;
            margin-bottom: 16px;
        }

        .file-results-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
            flex-wrap: wrap;
            gap: 8px;
        }

        .filter-pills {
            display: flex;
            gap: 6px;
        }

        .filter-pill {
            background: #f1f5f9;
            border: 1px solid var(--border);
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 11px;
            cursor: pointer;
            color: var(--text-muted);
            font-weight: 500;
        }

        .filter-pill.active {
            background: var(--text-main);
            color: #ffffff;
            border-color: var(--text-main);
        }

        .file-result-row {
            border: 1px solid var(--border);
            border-radius: 6px;
            margin-bottom: 8px;
            overflow: hidden;
            background: #ffffff;
        }

        .file-result-summary {
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            background: #fafbfc;
            transition: background 0.1s ease;
        }

        .file-result-summary:hover {
            background: #f1f5f9;
        }

        .file-res-path {
            font-family: var(--font-mono);
            font-size: 13px;
            font-weight: 600;
        }

        .file-res-status {
            font-family: var(--font-mono);
            font-size: 11px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
        }

        .file-res-status.passed {
            background: var(--success-bg);
            color: var(--success);
        }

        .file-res-status.warning {
            background: var(--warning-bg);
            color: var(--warning);
        }

        .file-res-status.critical {
            background: var(--danger-bg);
            color: var(--danger);
        }

        .file-result-body {
            display: none;
            padding: 14px;
            border-top: 1px solid var(--border);
            background: #ffffff;
        }

        .file-result-body.open {
            display: block;
        }

        .finding-detail-item {
            padding: 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
            margin-bottom: 8px;
            font-size: 12px;
            line-height: 1.5;
        }

        .finding-detail-item pre {
            background: #f8fafc;
            border: 1px solid var(--border);
            padding: 8px;
            border-radius: 4px;
            font-family: var(--font-mono);
            font-size: 11px;
            margin-top: 6px;
            overflow-x: auto;
        }

        .report-link {
            display: inline-block;
            margin-top: 6px;
            font-size: 12px;
            color: var(--text-muted);
            text-decoration: underline;
        }

        .report-link:hover {
            color: var(--text-main);
        }
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="brand">
            <h1>Cherm</h1>
            <p>Static Architecture & Security Auditor (Python, Node.js, Next.js, Go, SQL)</p>
        </div>
        <div class="port-badge">
            <span class="dot"></span>
            <span>localhost:3690</span>
        </div>
    </header>

    <!-- Mode Tabs -->
    <div class="tabs">
        <button id="tab-drop" class="tab-btn active" onclick="switchMode('drop')">Drag & Drop (File or Folder)</button>
        <button id="tab-local" class="tab-btn" onclick="switchMode('local')">Local Directory Scanner</button>
        <button id="tab-paste" class="tab-btn" onclick="switchMode('paste')">Paste Snippet</button>
    </div>

    <!-- Main Container Card -->
    <div class="card">
        <!-- 1. Drag & Drop Mode (File or Folder) -->
        <div id="drop-mode">
            <div id="dropzone" class="dropzone">
                <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                </svg>
                <div class="dropzone-title">Drag & drop your code file OR full project folder here</div>
                <div class="dropzone-sub">Drop any single file (.py, .js, .tsx, etc.) or drag an entire folder into this box</div>
                
                <div class="dropzone-actions">
                    <button type="button" class="btn-browse" onclick="openFolderPicker(event)" style="background:var(--text-main); color:#ffffff; border-color:var(--text-main); font-weight:700;">
                        📁 Choose Full Folder
                    </button>
                    <button type="button" class="btn-browse" onclick="openFilePicker(event)">
                        📄 Choose Single File
                    </button>
                </div>
                
                <div style="margin-top: 14px; font-size: 12px; color: var(--text-muted); display: flex; align-items: center; justify-content: center; gap: 8px;">
                    <span>Or scan local directory:</span>
                    <input type="text" id="quick-dir-path" value="." style="padding: 5px 10px; border: 1px solid var(--border); border-radius: 4px; font-family: var(--font-mono); font-size: 12px; width: 140px; background:#fff;">
                    <button type="button" class="btn-browse" style="padding: 5px 12px; font-size: 12px;" onclick="loadQuickPath(event)">Load Folder</button>
                </div>
                
                <input type="file" id="file-input" style="display:none" onchange="onFileChosen(event)">
                <input type="file" id="folder-input" webkitdirectory directory multiple style="display:none" onchange="onFolderChosen(event)">
            </div>

            <!-- Single File Loaded Box -->
            <div id="file-loaded-panel" class="file-loaded-panel">
                <div class="file-header">
                    <div class="file-info">
                        <span id="ext-badge" class="ext-badge">FILE</span>
                        <div>
                            <div id="file-name" class="file-title">code.py</div>
                            <div id="file-stats" class="file-stats">0 Bytes • 0 lines</div>
                        </div>
                    </div>
                    <button class="btn-clear" onclick="clearLoadedTarget()">✕ Remove</button>
                </div>

                <div class="preview-box" id="code-preview"></div>

                <div class="action-row" style="margin-top: 14px;">
                    <button id="btn-run-check" class="btn-check" onclick="runSingleFileAudit()">
                        ⚡ Run Cherm Security Audit
                    </button>
                    <span id="audit-timing" style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);"></span>
                </div>
            </div>

            <!-- Folder Loaded Box (Multi-file project) -->
            <div id="folder-loaded-panel" class="folder-loaded-panel">
                <div class="file-header">
                    <div class="file-info">
                        <span class="ext-badge" style="background:#0284c7;">FOLDER</span>
                        <div>
                            <div id="folder-name" class="file-title">project</div>
                            <div id="folder-stats" class="file-stats">0 files • 0 lines</div>
                        </div>
                    </div>
                    <button class="btn-clear" onclick="clearLoadedTarget()">✕ Remove</button>
                </div>

                <div class="folder-toolbar">
                    <input type="text" id="folder-search" class="search-input" placeholder="Search files in loaded project..." oninput="filterFolderFiles()">
                    <span id="folder-filter-count" style="font-size: 11px; color: var(--text-muted); font-family: var(--font-mono); white-space: nowrap;"></span>
                </div>

                <div class="folder-files-container">
                    <div id="folder-file-list" class="folder-file-list"></div>
                    <div id="folder-code-preview" class="preview-box">Select a file from the list to preview code.</div>
                </div>

                <div class="action-row">
                    <button id="btn-folder-check" class="btn-check" onclick="runFolderAuditAction()">
                        ⚡ Run Full Project Audit
                    </button>
                    <span id="folder-timing" style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);"></span>
                </div>
            </div>
        </div>

        <!-- 2. Local Path Scan Mode -->
        <div id="local-mode" class="local-panel">
            <div style="font-size: 14px; font-weight: 600; margin-bottom: 6px;">Scan Local Folder from Disk</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 14px;">
                Enter a local directory path (e.g. <code>.</code> for current folder, or an absolute path like <code>C:\Projects\my-app</code>) to load all code files instantly.
            </div>
            <div class="local-input-row">
                <input type="text" id="local-dir-path" class="local-path-input" placeholder="Enter path e.g. . or C:\path\to\my-app" value=".">
                <button type="button" class="btn-browse" onclick="loadFromLocalPath()">Scan & Load</button>
            </div>
        </div>

        <!-- 3. Paste Snippet Mode -->
        <div id="paste-mode" class="paste-panel">
            <textarea id="paste-code" placeholder="Paste source code snippet here (e.g. Next.js component, Node.js server route, Python function, SQL queries)..."></textarea>
            <div class="action-row">
                <button id="btn-paste-check" class="btn-check" onclick="runPasteAudit()">
                    ⚡ Run Cherm Security Audit
                </button>
                <span id="paste-timing" style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);"></span>
            </div>
        </div>

        <!-- Loading State -->
        <div id="loading-state" class="loading-state">
            <div class="spinner"></div>
            <div id="loading-text" style="font-weight: 600; font-size: 14px;">Analyzing code architecture...</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Testing race conditions, IDOR, AST code smells & ML defect risk</div>
        </div>
    </div>

    <!-- Results Panel -->
    <div id="results-panel" class="results-panel">
        <div class="grade-banner">
            <div>
                <div id="res-target-sub" style="font-size: 12px; color: var(--text-muted); margin-bottom: 2px;">Architecture Health</div>
                <div id="res-status" style="font-size: 15px; font-weight: 600; color: var(--text-main);">PASS</div>
            </div>
            <div id="res-badge" class="grade-badge grade-a">GRADE A</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-box">
                <div id="m-total" class="metric-val">0</div>
                <div id="m-total-label" class="metric-label">Total Issues</div>
            </div>
            <div class="metric-box">
                <div id="m-fatal" class="metric-val" style="color: var(--danger);">0</div>
                <div id="m-fatal-label" class="metric-label">Fatal Flaws</div>
            </div>
            <div class="metric-box">
                <div id="m-race" class="metric-val">0</div>
                <div class="metric-label">Race Conditions</div>
            </div>
            <div class="metric-box">
                <div id="m-design" class="metric-val">0</div>
                <div class="metric-label">Design Bottlenecks</div>
            </div>
            <div class="metric-box">
                <div id="m-smell" class="metric-val">0</div>
                <div id="m-smell-label" class="metric-label">Code Smells</div>
            </div>
            <div class="metric-box">
                <div id="m-risk" class="metric-val">0%</div>
                <div id="m-risk-label" class="metric-label">ML Defect Risk</div>
            </div>
        </div>

        <!-- Priority Action Recommendations -->
        <div class="findings-card">
            <h3>Audit Findings & Recommendations</h3>
            <div id="findings-list"></div>
            <a class="report-link" href="/report" target="_blank">View detailed HTML audit report &rarr;</a>
        </div>

        <!-- Per-File Breakdown (For Folder / Project Audits) -->
        <div id="folder-results-card" class="file-results-card" style="display:none;">
            <div class="file-results-header">
                <div style="font-weight:600; font-size:14px;">Project Files Breakdown</div>
                <div class="filter-pills">
                    <button class="filter-pill active" onclick="filterResults('all')">All</button>
                    <button class="filter-pill" onclick="filterResults('vulnerable')">With Issues</button>
                    <button class="filter-pill" onclick="filterResults('clean')">Clean</button>
                </div>
            </div>
            <div id="file-results-list"></div>
        </div>
    </div>
</div>

<script>
    const IGNORED_DIRS = ['node_modules', '.git', '.next', 'dist', 'build', 'out', 'venv', '.venv', 'env', '__pycache__', '.idea', '.vscode', 'coverage', '.turbo', '.cache', '.sst', 'target', 'vendor'];
    const ALLOWED_EXTS = ['.py', '.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs', '.go', '.rs', '.java', '.sql', '.html', '.css', '.json', '.yaml', '.yml', '.c', '.cpp', '.h', '.sh', '.bash', '.ps1', '.md'];

    let currentMode = 'drop'; // drop | local | paste
    let singleFile = null;    // { name, content, size, lines }
    let loadedFiles = [];     // Array of { path, name, size, lines, content }
    let activeFolderName = '';
    let selectedFileIndex = 0;
    let latestFolderResults = null;

    // Elements
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const folderInput = document.getElementById('folder-input');
    const fileLoadedPanel = document.getElementById('file-loaded-panel');
    const folderLoadedPanel = document.getElementById('folder-loaded-panel');
    const fileNameEl = document.getElementById('file-name');
    const fileStatsEl = document.getElementById('file-stats');
    const extBadgeEl = document.getElementById('ext-badge');
    const previewEl = document.getElementById('code-preview');
    const folderNameEl = document.getElementById('folder-name');
    const folderStatsEl = document.getElementById('folder-stats');
    const folderFileListEl = document.getElementById('folder-file-list');
    const folderCodePreviewEl = document.getElementById('folder-code-preview');
    const btnRunCheck = document.getElementById('btn-run-check');
    const btnFolderCheck = document.getElementById('btn-folder-check');
    const auditTimingEl = document.getElementById('audit-timing');
    const folderTimingEl = document.getElementById('folder-timing');
    const loadingState = document.getElementById('loading-state');
    const loadingText = document.getElementById('loading-text');
    const resultsPanel = document.getElementById('results-panel');

    function switchMode(mode) {
        currentMode = mode;
        document.getElementById('tab-drop').classList.toggle('active', mode === 'drop');
        document.getElementById('tab-local').classList.toggle('active', mode === 'local');
        document.getElementById('tab-paste').classList.toggle('active', mode === 'paste');

        document.getElementById('drop-mode').style.display = (mode === 'drop') ? 'block' : 'none';
        document.getElementById('local-mode').classList.toggle('active', mode === 'local');
        document.getElementById('paste-mode').classList.toggle('active', mode === 'paste');
    }

    function formatBytes(bytes) {
        if (!bytes || bytes === 0) return '0 Bytes';
        if (bytes < 1024) return bytes + ' Bytes';
        const kb = bytes / 1024;
        if (kb < 1024) return kb.toFixed(1) + ' KB';
        return (kb / 1024).toFixed(2) + ' MB';
    }

    function getBadgeForFile(name, content) {
        const lower = name.toLowerCase();
        if (lower.endsWith('.tsx') || lower.endsWith('.jsx')) return 'NEXT';
        if (lower.endsWith('.ts')) return 'TS';
        if (lower.endsWith('.js') || lower.endsWith('.mjs') || lower.endsWith('.cjs')) {
            if (content && (content.includes("'use client'") || content.includes('"use client"') || content.includes('next/'))) {
                return 'NEXT';
            }
            return 'NODE';
        }
        if (lower.endsWith('.py')) return 'PY';
        if (lower.endsWith('.go')) return 'GO';
        if (lower.endsWith('.sql')) return 'SQL';
        if (lower.endsWith('.rs')) return 'RUST';
        if (lower.endsWith('.java')) return 'JAVA';
        if (lower.endsWith('.json')) return 'JSON';
        return (name.split('.').pop() || 'FILE').toUpperCase().substring(0, 4);
    }

    function isAllowedCodeFile(relPath, fileName) {
        const lower = fileName.toLowerCase();
        const parts = relPath.toLowerCase().replace(/\\/g, '/').split('/');
        if (parts.some(p => IGNORED_DIRS.includes(p))) return false;
        const ext = '.' + lower.split('.').pop();
        return ALLOWED_EXTS.includes(ext);
    }

    // Window-level drag/drop safety to prevent browser default navigation
    window.addEventListener('dragover', (e) => e.preventDefault());
    window.addEventListener('drop', (e) => e.preventDefault());

    // Drag & Drop
    ['dragenter', 'dragover'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', async (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');

        const items = e.dataTransfer.items;
        if (items && items.length > 0) {
            let entries = [];
            for (let i = 0; i < items.length; i++) {
                try {
                    const entry = items[i].webkitGetAsEntry ? items[i].webkitGetAsEntry() : null;
                    if (entry) entries.push(entry);
                } catch (err) {}
            }

            const hasDir = entries.some(ent => ent && ent.isDirectory);
            if (hasDir || entries.length > 1) {
                await loadFolderFromEntries(entries);
                return;
            } else if (entries.length === 1 && entries[0].isFile) {
                entries[0].file(f => loadSingleFileObject(f));
                return;
            }
        }

        if (e.dataTransfer.files && e.dataTransfer.files.length > 1) {
            await loadFolderFromFileList(e.dataTransfer.files, 'Dropped Files');
        } else if (e.dataTransfer.files && e.dataTransfer.files.length === 1) {
            loadSingleFileObject(e.dataTransfer.files[0]);
        }
    });

    function openFilePicker(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        fileInput.value = '';
        fileInput.click();
    }

    function openFolderPicker(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        folderInput.value = '';
        folderInput.click();
    }

    function onFileChosen(e) {
        const files = e.target.files;
        if (files && files.length > 0) {
            loadSingleFileObject(files[0]);
        }
    }

    async function onFolderChosen(e) {
        const files = e.target.files;
        if (files && files.length > 0) {
            const first = files[0];
            const folderName = first.webkitRelativePath ? first.webkitRelativePath.split('/')[0] : 'Project Folder';
            await loadFolderFromFileList(files, folderName);
        }
    }

    function loadQuickPath(e) {
        if (e) { e.preventDefault(); e.stopPropagation(); }
        const p = (document.getElementById('quick-dir-path').value || '.').trim();
        loadLocalPath(p);
    }

    function readFileAsText(file) {
        return new Promise((resolve) => {
            if (file.size > 2500000) {
                resolve('// [Large file skipped for memory safety]');
                return;
            }
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result || '');
            reader.onerror = () => resolve('');
            reader.readAsText(file);
        });
    }

    // Traversal for dropped directory entries
    async function traverseDirectoryEntry(entry, path = '') {
        if (!entry) return [];
        if (entry.isFile) {
            return new Promise((resolve) => {
                entry.file(async (file) => {
                    const relPath = path + file.name;
                    if (isAllowedCodeFile(relPath, file.name)) {
                        const content = await readFileAsText(file);
                        resolve([{
                            path: relPath,
                            name: file.name,
                            size: file.size,
                            lines: content.split('\n').length,
                            content: content
                        }]);
                    } else {
                        resolve([]);
                    }
                }, () => resolve([]));
            });
        } else if (entry.isDirectory) {
            const dirName = entry.name.toLowerCase();
            if (IGNORED_DIRS.includes(dirName)) {
                return [];
            }
            const dirReader = entry.createReader();
            let entries = [];
            const readEntries = async () => {
                const batch = await new Promise((resolve) => {
                    dirReader.readEntries(resolve, () => resolve([]));
                });
                if (batch && batch.length > 0) {
                    entries = entries.concat(batch);
                    await readEntries();
                }
            };
            await readEntries();
            let results = [];
            for (const child of entries) {
                const sub = await traverseDirectoryEntry(child, path + entry.name + '/');
                results = results.concat(sub);
                if (results.length >= 500) break;
            }
            return results;
        }
        return [];
    }

    async function loadFolderFromEntries(entries) {
        loadingState.classList.add('active');
        loadingText.textContent = 'Reading folder files...';
        resultsPanel.classList.remove('active');

        let collected = [];
        let rootName = 'Project';

        for (const entry of entries) {
            if (!entry) continue;
            if (entry.isDirectory && rootName === 'Project') {
                rootName = entry.name;
            }
            const res = await traverseDirectoryEntry(entry, '');
            collected = collected.concat(res);
            if (collected.length >= 500) break;
        }

        loadingState.classList.remove('active');
        if (collected.length === 0) {
            alert('No supported code files found in the dropped folder.');
            return;
        }
        setLoadedFolder(rootName, collected);
    }

    async function loadFolderFromFileList(fileList, folderName) {
        loadingState.classList.add('active');
        loadingText.textContent = 'Loading project files...';
        resultsPanel.classList.remove('active');

        let collected = [];
        for (let i = 0; i < fileList.length; i++) {
            const f = fileList[i];
            const relPath = f.webkitRelativePath || f.name;
            if (isAllowedCodeFile(relPath, f.name)) {
                const content = await readFileAsText(f);
                collected.push({
                    path: relPath,
                    name: f.name,
                    size: f.size,
                    lines: content.split('\n').length,
                    content: content
                });
            }
            if (collected.length >= 500) break;
        }

        loadingState.classList.remove('active');
        if (collected.length === 0) {
            alert('No supported code files found in the selected folder.');
            return;
        }
        setLoadedFolder(folderName, collected);
    }

    function setLoadedFolder(name, files) {
        singleFile = null;
        loadedFiles = files;
        activeFolderName = name;

        let totalLines = 0;
        let totalBytes = 0;
        files.forEach(f => {
            totalLines += f.lines;
            totalBytes += f.size;
        });

        folderNameEl.textContent = name;
        folderStatsEl.textContent = files.length + ' code files • ' + totalLines.toLocaleString() + ' lines • ' + formatBytes(totalBytes);
        btnFolderCheck.textContent = '⚡ Run Full Project Audit (' + files.length + ' files)';
        folderTimingEl.textContent = 'Folder loaded. Ready to audit.';

        renderFolderFilesList(files);
        selectFolderFile(0);

        folderLoadedPanel.classList.add('active');
        fileLoadedPanel.classList.remove('active');
        resultsPanel.classList.remove('active');
    }

    function renderFolderFilesList(filesToRender) {
        folderFileListEl.innerHTML = '';
        filesToRender.forEach((f, idx) => {
            const row = document.createElement('div');
            row.className = 'folder-file-item' + (idx === selectedFileIndex ? ' active' : '');
            row.onclick = () => selectFolderFile(idx);

            const left = document.createElement('div');
            left.className = 'item-left';

            const badge = document.createElement('span');
            badge.className = 'tag-badge';
            badge.textContent = getBadgeForFile(f.name, f.content);

            const name = document.createElement('span');
            name.textContent = f.path;

            left.appendChild(badge);
            left.appendChild(name);

            const stats = document.createElement('span');
            stats.className = 'item-stats';
            stats.textContent = f.lines + ' L';

            row.appendChild(left);
            row.appendChild(stats);
            folderFileListEl.appendChild(row);
        });
        document.getElementById('folder-filter-count').textContent = filesToRender.length + ' files';
    }

    function filterFolderFiles() {
        const query = document.getElementById('folder-search').value.toLowerCase().trim();
        const filtered = loadedFiles.filter(f => f.path.toLowerCase().includes(query) || f.name.toLowerCase().includes(query));
        renderFolderFilesList(filtered);
    }

    function selectFolderFile(idx) {
        if (!loadedFiles[idx]) return;
        selectedFileIndex = idx;
        const file = loadedFiles[idx];

        const rows = folderFileListEl.querySelectorAll('.folder-file-item');
        rows.forEach((r, i) => r.classList.toggle('active', i === idx));

        const previewLines = file.content.split('\n').slice(0, 20).join('\n');
        folderCodePreviewEl.textContent = '// ' + file.path + ' (' + file.lines + ' lines)\n' + previewLines + (file.lines > 20 ? '\n... [' + (file.lines - 20) + ' more lines]' : '');
    }

    function loadSingleFileObject(file) {
        loadedFiles = [];
        const reader = new FileReader();
        reader.onload = function(evt) {
            const content = evt.target.result || '';
            const lines = content.split('\n').length;
            singleFile = {
                name: file.name,
                size: file.size,
                lines: lines,
                content: content
            };

            fileNameEl.textContent = file.name;
            fileStatsEl.textContent = formatBytes(file.size) + ' • ' + lines + ' lines';
            extBadgeEl.textContent = getBadgeForFile(file.name, content);

            const previewLines = content.split('\n').slice(0, 15).join('\n');
            previewEl.textContent = previewLines + (lines > 15 ? '\n... [' + (lines - 15) + ' more lines]' : '');

            fileLoadedPanel.classList.add('active');
            folderLoadedPanel.classList.remove('active');
            resultsPanel.classList.remove('active');
            auditTimingEl.textContent = 'File loaded. Click "Run Cherm Security Audit" to inspect.';
        };
        reader.readAsText(file);
    }

    function clearLoadedTarget() {
        singleFile = null;
        loadedFiles = [];
        fileInput.value = '';
        folderInput.value = '';
        fileLoadedPanel.classList.remove('active');
        folderLoadedPanel.classList.remove('active');
        resultsPanel.classList.remove('active');
        auditTimingEl.textContent = '';
        folderTimingEl.textContent = '';
    }

    // Local Directory Scan
    async function loadLocalPath(pathVal) {
        if (!pathVal) pathVal = '.';
        loadingState.classList.add('active');
        loadingText.textContent = 'Scanning local directory: ' + pathVal;
        resultsPanel.classList.remove('active');

        try {
            const res = await fetch('/api/scan-local-dir', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ path: pathVal })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: 'HTTP ' + res.status }));
                throw new Error(err.error || 'Failed scanning directory');
            }

            const data = await res.json();
            if (!data.files || data.files.length === 0) {
                alert('No supported code files found in directory: ' + pathVal);
                return;
            }

            // Switch to drop mode to show the loaded folder view
            switchMode('drop');
            setLoadedFolder(data.folder_name, data.files);
        } catch (err) {
            alert('Directory scan failed: ' + err.message);
        } finally {
            loadingState.classList.remove('active');
        }
    }

    function loadFromLocalPath() {
        const pathVal = (document.getElementById('local-dir-path').value || '.').trim();
        loadLocalPath(pathVal);
    }

    // Single File Audit
    function runSingleFileAudit() {
        if (!singleFile || !singleFile.content) {
            alert('No file content loaded to audit.');
            return;
        }
        executeAuditSingle(singleFile.content, singleFile.name, btnRunCheck, auditTimingEl);
    }

    function runPasteAudit() {
        const code = document.getElementById('paste-code').value;
        if (!code || !code.trim()) {
            alert('Please paste some code to audit.');
            return;
        }
        executeAuditSingle(code, 'snippet.py', document.getElementById('btn-paste-check'), document.getElementById('paste-timing'));
    }

    async function executeAuditSingle(code, filename, btn, timingElem) {
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Auditing...';
        loadingState.classList.add('active');
        loadingText.textContent = 'Auditing file: ' + filename;
        resultsPanel.classList.remove('active');
        timingElem.textContent = 'Auditing...';

        const t0 = performance.now();
        try {
            const res = await fetch('/api/audit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code: code, filename: filename, file_path: filename })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: 'HTTP error ' + res.status }));
                throw new Error(err.error || 'Server error');
            }

            const data = await res.json();
            const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
            timingElem.textContent = 'Audit completed in ' + elapsed + 's';
            displaySingleResults(data, filename);
        } catch (err) {
            timingElem.textContent = 'Error: ' + err.message;
            alert('Audit failed: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
            loadingState.classList.remove('active');
        }
    }

    function displaySingleResults(data, filename) {
        if (!data.success) {
            alert('Audit Error: ' + (data.error || 'Failed to analyze code'));
            return;
        }

        const s = data.summary || {};
        const grade = data.health_grade || 'GRADE A';
        const badgeEl = document.getElementById('res-badge');
        const statusEl = document.getElementById('res-status');
        const targetSubEl = document.getElementById('res-target-sub');

        targetSubEl.textContent = 'Architecture Health • ' + filename;
        statusEl.textContent = (data.status || 'PASS') + ' • ' + grade;
        badgeEl.textContent = grade;
        badgeEl.className = 'grade-badge ' + (grade.includes('A') ? 'grade-a' : (grade.includes('B') ? 'grade-b' : 'grade-c'));

        document.getElementById('m-total-label').textContent = 'Total Issues';
        document.getElementById('m-fatal-label').textContent = 'Fatal Flaws';
        document.getElementById('m-smell-label').textContent = 'Code Smells';
        document.getElementById('m-risk-label').textContent = 'ML Defect Risk';

        document.getElementById('m-total').textContent = s.total_issues_found || 0;
        document.getElementById('m-fatal').textContent = s.fatal_critical_flaws || 0;
        document.getElementById('m-race').textContent = s.multitap_concurrency_flaws || 0;
        document.getElementById('m-design').textContent = s.system_design_flaws || 0;
        document.getElementById('m-smell').textContent = s.code_smells_and_antipatterns || 0;
        document.getElementById('m-risk').textContent = (s.ml_risk_score || 0) + '%';

        const list = document.getElementById('findings-list');
        list.innerHTML = '';
        const items = data.quick_action_items || [];
        if (items.length === 0) {
            const cleanDiv = document.createElement('div');
            cleanDiv.className = 'finding-item clean';
            cleanDiv.textContent = 'Clean code — zero race conditions, design bottlenecks, or code smells detected.';
            list.appendChild(cleanDiv);
        } else {
            items.forEach(it => {
                const itemDiv = document.createElement('div');
                const isFatal = it.includes('[FATAL]') || it.includes('[CRITICAL]') || it.includes('SECURITY') || it.includes('RACE');
                itemDiv.className = 'finding-item ' + (isFatal ? 'fatal' : 'warning');
                itemDiv.textContent = it;
                list.appendChild(itemDiv);
            });
        }

        document.getElementById('folder-results-card').style.display = 'none';
        resultsPanel.classList.add('active');
    }

    // Folder / Project Audit
    async function runFolderAuditAction() {
        if (!loadedFiles || loadedFiles.length === 0) {
            alert('No folder files loaded to audit.');
            return;
        }

        btnFolderCheck.disabled = true;
        const originalText = btnFolderCheck.textContent;
        btnFolderCheck.textContent = 'Auditing ' + loadedFiles.length + ' files...';
        loadingState.classList.add('active');
        loadingText.textContent = 'Running full project audit across ' + loadedFiles.length + ' files...';
        resultsPanel.classList.remove('active');
        folderTimingEl.textContent = 'Auditing project...';

        const t0 = performance.now();
        try {
            const res = await fetch('/api/audit-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_name: activeFolderName,
                    files: loadedFiles
                })
            });

            if (!res.ok) {
                const err = await res.json().catch(() => ({ error: 'HTTP error ' + res.status }));
                throw new Error(err.error || 'Server error');
            }

            const data = await res.json();
            const elapsed = ((performance.now() - t0) / 1000).toFixed(2);
            folderTimingEl.textContent = 'Project audit completed in ' + elapsed + 's (' + loadedFiles.length + ' files)';
            latestFolderResults = data;
            displayFolderResults(data);
        } catch (err) {
            folderTimingEl.textContent = 'Error: ' + err.message;
            alert('Project audit failed: ' + err.message);
        } finally {
            btnFolderCheck.disabled = false;
            btnFolderCheck.textContent = originalText;
            loadingState.classList.remove('active');
        }
    }

    function displayFolderResults(data) {
        if (!data.success) {
            alert('Audit Error: ' + (data.error || 'Failed to analyze project'));
            return;
        }

        const s = data.summary || {};
        const grade = data.health_grade || 'GRADE A';
        const badgeEl = document.getElementById('res-badge');
        const statusEl = document.getElementById('res-status');
        const targetSubEl = document.getElementById('res-target-sub');

        targetSubEl.textContent = 'Project Health • ' + data.folder_name + ' (' + s.total_files_scanned + ' files)';
        statusEl.textContent = s.clean_files_count + ' / ' + s.total_files_scanned + ' Files Clean • ' + (data.overall_status || 'PASS');
        badgeEl.textContent = grade;
        badgeEl.className = 'grade-badge ' + (grade.includes('A') ? 'grade-a' : (grade.includes('B') ? 'grade-b' : (grade.includes('C') ? 'grade-c' : 'grade-f')));

        document.getElementById('m-total-label').textContent = 'Files Audited';
        document.getElementById('m-fatal-label').textContent = 'Vulnerable Files';
        document.getElementById('m-smell-label').textContent = 'Code Smells';
        document.getElementById('m-risk-label').textContent = 'Fatal Flaws';

        document.getElementById('m-total').textContent = s.total_files_scanned || 0;
        document.getElementById('m-fatal').textContent = s.vulnerable_files_count || 0;
        document.getElementById('m-race').textContent = s.multitap_concurrency_flaws || 0;
        document.getElementById('m-design').textContent = s.system_design_flaws || 0;
        document.getElementById('m-smell').textContent = s.code_smells_and_antipatterns || 0;
        document.getElementById('m-risk').textContent = s.fatal_critical_flaws || 0;

        // Findings list (Top project recommendations)
        const list = document.getElementById('findings-list');
        list.innerHTML = '';
        const items = data.quick_action_items || [];
        if (items.length === 0) {
            const cleanDiv = document.createElement('div');
            cleanDiv.className = 'finding-item clean';
            cleanDiv.textContent = 'Zero critical vulnerabilities or design bottlenecks found across the entire project.';
            list.appendChild(cleanDiv);
        } else {
            items.forEach(it => {
                const itemDiv = document.createElement('div');
                const isFatal = it.includes('[FATAL]') || it.includes('[CRITICAL]') || it.includes('SECURITY') || it.includes('RACE');
                itemDiv.className = 'finding-item ' + (isFatal ? 'fatal' : 'warning');
                itemDiv.textContent = it;
                list.appendChild(itemDiv);
            });
        }

        // Per-file breakdown
        renderFileResultsList(data.file_results || [], 'all');
        document.getElementById('folder-results-card').style.display = 'block';

        resultsPanel.classList.add('active');
    }

    function renderFileResultsList(fileResults, filterType) {
        const container = document.getElementById('file-results-list');
        container.innerHTML = '';

        const filtered = fileResults.filter(f => {
            if (filterType === 'vulnerable') return f.status !== 'PASSED';
            if (filterType === 'clean') return f.status === 'PASSED';
            return true;
        });

        if (filtered.length === 0) {
            container.innerHTML = '<div style="padding:14px; text-align:center; color:var(--text-muted); font-size:13px;">No files match the selected filter.</div>';
            return;
        }

        filtered.forEach((f, idx) => {
            const row = document.createElement('div');
            row.className = 'file-result-row';

            const summary = document.createElement('div');
            summary.className = 'file-result-summary';
            summary.onclick = () => toggleFileDetail(idx);

            const pathSpan = document.createElement('span');
            pathSpan.className = 'file-res-path';
            pathSpan.textContent = f.path + ' (' + f.lines + ' lines)';

            const rightSpan = document.createElement('div');
            rightSpan.style.display = 'flex';
            rightSpan.style.alignItems = 'center';
            rightSpan.style.gap = '10px';

            const countSpan = document.createElement('span');
            countSpan.style.fontSize = '12px';
            countSpan.style.color = 'var(--text-muted)';
            countSpan.textContent = f.total_issues === 0 ? 'Clean' : f.total_issues + ' issues (' + f.fatal_flaws + ' fatal)';

            const statusBadge = document.createElement('span');
            statusBadge.className = 'file-res-status ' + (f.status === 'PASSED' ? 'passed' : (f.status === 'WARNING' ? 'warning' : 'critical'));
            statusBadge.textContent = f.status;

            rightSpan.appendChild(countSpan);
            rightSpan.appendChild(statusBadge);

            summary.appendChild(pathSpan);
            summary.appendChild(rightSpan);
            row.appendChild(summary);

            // Collapsible details
            const body = document.createElement('div');
            body.className = 'file-result-body';
            body.id = 'file-detail-' + idx;

            if (!f.findings || f.findings.length === 0) {
                body.innerHTML = '<div style="color:var(--success); font-size:12px;">✓ Clean file — no architectural flaws or code smells found.</div>';
            } else {
                f.findings.forEach(find => {
                    const item = document.createElement('div');
                    item.className = 'finding-detail-item';
                    item.style.borderLeft = '3px solid ' + (find.severity === 'CRITICAL' ? 'var(--danger)' : 'var(--warning)');

                    let html = '<strong>' + (find.badge || '[ISSUE]') + ' Line ' + find.line + ': ' + find.title + '</strong><br>' +
                               '<span style="color:#475569;">' + (find.plain_english || '') + '</span>';
                    if (find.risk) {
                        html += '<br><strong style="color:var(--danger); font-size:11px;">Risk:</strong> <span style="font-size:11px;">' + find.risk + '</span>';
                    }
                    if (find.fix) {
                        html += '<pre>' + find.fix + '</pre>';
                    }
                    item.innerHTML = html;
                    body.appendChild(item);
                });
            }

            row.appendChild(body);
            container.appendChild(row);
        });
    }

    function toggleFileDetail(idx) {
        const body = document.getElementById('file-detail-' + idx);
        if (body) {
            body.classList.toggle('open');
        }
    }

    function filterResults(type) {
        const pills = document.querySelectorAll('.filter-pill');
        pills.forEach(p => p.classList.toggle('active', p.textContent.toLowerCase().includes(type) || (type === 'all' && p.textContent.includes('All'))));
        if (latestFolderResults && latestFolderResults.file_results) {
            renderFileResultsList(latestFolderResults.file_results, type);
        }
    }
</script>
</body>
</html>
"""

FAVICON_SVG = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100" rx="20" fill="#0f172a"/><text x="50" y="66" font-size="52" font-weight="700" text-anchor="middle" fill="#ffffff">C</text></svg>'


class ChermRequestHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        pass

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_bytes(self, content: bytes, mime: str = "text/html; charset=utf-8", status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self._send_bytes(body, "application/json; charset=utf-8", status)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            self._send_bytes(INDEX_HTML.encode("utf-8"), "text/html; charset=utf-8")
            return

        elif path == "/favicon.ico":
            self._send_bytes(FAVICON_SVG, "image/svg+xml")
            return

        elif path == "/report":
            report_file = os.path.join(BASE_DIR, "cherm_audit_report.html")
            fallback = "<html><body style='font-family:sans-serif;padding:30px;color:#0f172a'><h3>No audit report generated yet. Run an audit on a file or folder first.</h3></body></html>"
            if os.path.isfile(report_file):
                try:
                    with open(report_file, "rb") as f:
                        self._send_bytes(f.read(), "text/html; charset=utf-8")
                    return
                except Exception:
                    pass
            self._send_bytes(fallback.encode("utf-8"), "text/html; charset=utf-8")
            return

        elif path == "/api/status":
            self._send_json({
                "status": "online",
                "version": "2.0.0",
                "mcp_ready": cherm_mcp is not None
            })
            return

        else:
            self._send_bytes(b"Not Found", "text/plain", 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/audit":
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                self._send_json({"error": "Empty request body"}, 400)
                return
            if length > 25000000:
                self._send_json({"error": "Payload exceeds 25MB limit"}, 413)
                return

            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            code = data.get("code")
            file_path = data.get("file_path") or data.get("filename")

            if not code and not file_path:
                self._send_json({"error": "No code content provided"}, 400)
                return

            if not cherm_mcp:
                self._send_json({"error": "Cherm MCP analysis engine not loaded."}, 500)
                return

            try:
                result = cherm_mcp.run_all_in_one_check(file_path=file_path, code_content=code)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        elif path == "/api/audit-folder":
            length = int(self.headers.get("Content-Length", 0))
            if length == 0:
                self._send_json({"error": "Empty request body"}, 400)
                return
            if length > 50000000:
                self._send_json({"error": "Payload exceeds 50MB limit"}, 413)
                return

            body = self.rfile.read(length).decode("utf-8", errors="replace")
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            directory_path = data.get("directory_path")
            folder_name = data.get("folder_name")
            files_data = data.get("files")

            if not directory_path and not files_data:
                self._send_json({"error": "No directory_path or files provided"}, 400)
                return

            if not cherm_mcp:
                self._send_json({"error": "Cherm MCP analysis engine not loaded."}, 500)
                return

            try:
                result = cherm_mcp.run_folder_audit(
                    directory_path=directory_path,
                    files_data=files_data,
                    folder_name=folder_name,
                    auto_generate_html=True
                )
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
            return

        elif path == "/api/scan-local-dir":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else "{}"
            try:
                data = json.loads(body)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            dir_input = (data.get("path") or ".").strip()
            abs_dir = os.path.abspath(dir_input)
            if not os.path.isdir(abs_dir):
                self._send_json({"error": f"Path is not a valid directory: {dir_input}"}, 400)
                return

            folder_name = os.path.basename(abs_dir) or "Project"
            from cherm_mcp import FOLDER_IGNORE_DIRS, FOLDER_ALLOWED_EXTS

            collected = []
            for root, dirs, files in os.walk(abs_dir):
                dirs[:] = [d for d in dirs if d.lower() not in FOLDER_IGNORE_DIRS and not d.startswith(".")]
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in FOLDER_ALLOWED_EXTS:
                        full_p = os.path.join(root, f)
                        rel_p = os.path.relpath(full_p, abs_dir).replace("\\", "/")
                        try:
                            with open(full_p, "r", encoding="utf-8", errors="ignore") as fh:
                                content = fh.read()
                            collected.append({
                                "path": rel_p,
                                "name": f,
                                "size": os.path.getsize(full_p),
                                "lines": len(content.splitlines()),
                                "content": content
                            })
                        except Exception:
                            pass
                if len(collected) >= 500:
                    break

            self._send_json({
                "success": True,
                "folder_name": folder_name,
                "abs_path": abs_dir,
                "files": collected
            })
            return

        self._send_bytes(b"Not Found", "text/plain", 404)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_free_port(start_port: int = 3690) -> int:
    if is_port_available(start_port):
        return start_port

    for port in [3690, 8080, 5050]:
        if is_port_available(port):
            return port

    for port in range(3691, 3750):
        if is_port_available(port):
            return port

    return start_port


def create_dual_stack_server(port: int):
    try:
        class DualStackServer(BaseServer):
            allow_reuse_address = True
            daemon_threads = True
            address_family = socket.AF_INET6

            def server_bind(self):
                try:
                    self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                except (AttributeError, OSError):
                    pass
                super().server_bind()

        return DualStackServer(("::", port), ChermRequestHandler)
    except Exception:
        class IPv4Server(BaseServer):
            allow_reuse_address = True
            daemon_threads = True
            address_family = socket.AF_INET

        return IPv4Server(("127.0.0.1", port), ChermRequestHandler)


def start_gui_server(port: int = 3690, open_browser: bool = True, in_background: bool = False):
    actual_port = find_free_port(port)
    httpd = create_dual_stack_server(actual_port)

    url = f"http://localhost:{actual_port}"
    direct_url = f"http://127.0.0.1:{actual_port}"

    print("=" * 64)
    print("                CHERM DRAG & DROP CODE AUDITOR                  ")
    print("=" * 64)
    print(f"  Localhost URL:   {url}")
    print(f"  Direct IPv4:     {direct_url}")
    print("  Engine:          Cherm Auditor Pro v2.0")
    print("  Capabilities:    Single File, Full Folder, Local Directory")
    print("  Status:          Listening for file/folder uploads...")
    print("=" * 64)

    if open_browser:
        def _open():
            time.sleep(0.3)
            webbrowser.open(direct_url)
        threading.Thread(target=_open, daemon=True).start()

    if in_background:
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return httpd, url
    else:
        try:
            print("Press Ctrl+C to stop the GUI server.\n")
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down Cherm GUI server...")
            httpd.shutdown()


if __name__ == "__main__":
    port_arg = 3690
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_arg = int(sys.argv[1])
    start_gui_server(port=port_arg)
