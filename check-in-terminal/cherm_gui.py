"""
Cherm Web GUI — Minimalist Drag & Drop Code Auditor
Fast, distraction-free code auditor with file preview, explicit check controls,
and comprehensive deterministic security analysis.
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
    <title>Cherm — Code Auditor</title>
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
            padding: 40px 20px;
        }

        .container {
            max-width: 820px;
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
            padding: 44px 20px;
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
            transform: scale(0.997);
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
            margin-bottom: 16px;
        }

        .btn-browse {
            display: inline-block;
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

        /* Loaded File Box */
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

        /* Preview box */
        .preview-box {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 12px;
            max-height: 180px;
            overflow-y: auto;
            font-family: var(--font-mono);
            font-size: 12px;
            line-height: 1.6;
            color: #334155;
            white-space: pre-wrap;
            word-break: break-all;
            margin-bottom: 16px;
        }

        /* Explicit Check Action Row */
        .action-row {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .btn-check {
            background-color: var(--btn-bg);
            color: #ffffff;
            border: none;
            padding: 12px 28px;
            border-radius: var(--radius);
            font-size: 14px;
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

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin-bottom: 16px;
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

        .findings-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 20px 22px;
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

        .report-link {
            display: inline-block;
            margin-top: 14px;
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
        <button id="tab-drop" class="tab-btn active" onclick="switchMode('drop')">Drag & Drop File</button>
        <button id="tab-paste" class="tab-btn" onclick="switchMode('paste')">Paste Code Snippet</button>
    </div>

    <!-- Main Container -->
    <div class="card">
        <!-- 1. Drag & Drop Mode -->
        <div id="drop-mode">
            <div id="dropzone" class="dropzone">
                <svg class="dropzone-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="17 8 12 3 7 8"></polyline>
                    <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <div class="dropzone-title">Drag & drop your code file here</div>
                <div class="dropzone-sub">Supports .py, .js, .jsx, .ts, .tsx, .mjs, .cjs, .go, .sql, .rs, .java (Node.js & Next.js ready)</div>
                <button type="button" class="btn-browse" onclick="openFilePicker(event)">Browse File from Disk</button>
                <input type="file" id="file-input" style="display:none" onchange="onFileChosen(event)">
            </div>

            <!-- Loaded File Box with Preview & Check Button -->
            <div id="file-loaded-panel" class="file-loaded-panel">
                <div class="file-header">
                    <div class="file-info">
                        <span id="ext-badge" class="ext-badge">FILE</span>
                        <div>
                            <div id="file-name" class="file-title">code.py</div>
                            <div id="file-stats" class="file-stats">0 Bytes • 0 lines</div>
                        </div>
                    </div>
                    <button class="btn-clear" onclick="clearSelectedFile()">✕ Remove</button>
                </div>

                <div class="preview-box" id="code-preview"></div>

                <div class="action-row">
                    <button id="btn-run-check" class="btn-check" onclick="runAuditAction()">
                        ⚡ Run Cherm Security Audit
                    </button>
                    <span id="audit-timing" style="font-size: 12px; color: var(--text-muted); font-family: var(--font-mono);"></span>
                </div>
            </div>
        </div>

        <!-- 2. Paste Mode -->
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
            <div style="font-weight: 600; font-size: 14px;">Analyzing code architecture...</div>
            <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Testing race conditions, IDOR, AST code smells & ML defect risk</div>
        </div>
    </div>

    <!-- Results Panel -->
    <div id="results-panel" class="results-panel">
        <div class="grade-banner">
            <div>
                <div style="font-size: 12px; color: var(--text-muted); margin-bottom: 2px;">Architecture Health</div>
                <div id="res-status" style="font-size: 15px; font-weight: 600; color: var(--text-main);">PASS</div>
            </div>
            <div id="res-badge" class="grade-badge grade-a">GRADE A</div>
        </div>

        <div class="metrics-grid">
            <div class="metric-box">
                <div id="m-total" class="metric-val">0</div>
                <div class="metric-label">Total Issues</div>
            </div>
            <div class="metric-box">
                <div id="m-fatal" class="metric-val" style="color: var(--danger);">0</div>
                <div class="metric-label">Fatal Flaws</div>
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
                <div class="metric-label">Code Smells</div>
            </div>
            <div class="metric-box">
                <div id="m-risk" class="metric-val">0%</div>
                <div class="metric-label">ML Defect Risk</div>
            </div>
        </div>

        <div class="findings-card">
            <h3>Audit Findings & Recommendations</h3>
            <div id="findings-list"></div>
            <a class="report-link" href="/report" target="_blank">View detailed HTML audit report &rarr;</a>
        </div>
    </div>
</div>

<script>
    let loadedCode = '';
    let loadedFilename = '';

    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('file-input');
    const loadedPanel = document.getElementById('file-loaded-panel');
    const fileNameEl = document.getElementById('file-name');
    const fileStatsEl = document.getElementById('file-stats');
    const extBadgeEl = document.getElementById('ext-badge');
    const previewEl = document.getElementById('code-preview');
    const loadingState = document.getElementById('loading-state');
    const resultsPanel = document.getElementById('results-panel');
    const timingEl = document.getElementById('audit-timing');
    const btnRunCheck = document.getElementById('btn-run-check');

    function switchMode(mode) {
        document.getElementById('tab-drop').classList.toggle('active', mode === 'drop');
        document.getElementById('tab-paste').classList.toggle('active', mode === 'paste');
        document.getElementById('drop-mode').style.display = (mode === 'drop') ? 'block' : 'none';
        document.getElementById('paste-mode').classList.toggle('active', mode === 'paste');
    }

    // Drag and Drop
    ['dragenter', 'dragover'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropzone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropzone.classList.remove('dragover');
        });
    });

    dropzone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            loadFileObject(files[0]);
        }
    });

    // Clicking anywhere on dropzone (except the browse button which handles its own click)
    dropzone.addEventListener('click', (e) => {
        if (!e.target.closest('.btn-browse')) {
            openFilePicker(e);
        }
    });

    function openFilePicker(e) {
        if (e) e.stopPropagation();
        fileInput.value = '';
        fileInput.click();
    }

    function onFileChosen(e) {
        const files = e.target.files;
        if (files && files.length > 0) {
            loadFileObject(files[0]);
        }
    }

    function formatBytes(bytes) {
        if (bytes === 0) return '0 Bytes';
        if (bytes < 1024) return bytes + ' Bytes';
        const kb = bytes / 1024;
        if (kb < 1024) return kb.toFixed(1) + ' KB';
        return (kb / 1024).toFixed(2) + ' MB';
    }

    function loadFileObject(file) {
        loadedFilename = file.name;
        fileNameEl.textContent = file.name;

        const lowerName = file.name.toLowerCase();
        let badge = 'FILE';
        if (lowerName.endsWith('.tsx') || lowerName.endsWith('.jsx')) {
            badge = 'NEXT';
        } else if (lowerName.endsWith('.ts')) {
            badge = 'TS';
        } else if (lowerName.endsWith('.js') || lowerName.endsWith('.mjs') || lowerName.endsWith('.cjs')) {
            badge = 'NODE';
        } else if (lowerName.endsWith('.py')) {
            badge = 'PY';
        } else if (lowerName.endsWith('.go')) {
            badge = 'GO';
        } else if (lowerName.endsWith('.sql')) {
            badge = 'SQL';
        } else if (lowerName.endsWith('.rs')) {
            badge = 'RUST';
        } else if (lowerName.endsWith('.json')) {
            badge = 'JSON';
        } else {
            badge = (file.name.split('.').pop() || 'FILE').toUpperCase().substring(0, 4);
        }
        extBadgeEl.textContent = badge;

        const reader = new FileReader();
        reader.onload = function(evt) {
            loadedCode = evt.target.result || '';
            const lines = loadedCode.split('\n').length;
            fileStatsEl.textContent = formatBytes(file.size) + ' • ' + lines + ' lines';

            // Check if JavaScript/TypeScript file contains Next.js or React markers
            if (loadedCode.includes("'use client'") || loadedCode.includes('"use client"') ||
                loadedCode.includes("'use server'") || loadedCode.includes('"use server"') ||
                loadedCode.includes('next/')) {
                if (badge === 'NODE' || badge === 'TS' || badge === 'JS') {
                    extBadgeEl.textContent = 'NEXT';
                }
            }

            // Show preview (first 15 lines)
            const previewLines = loadedCode.split('\n').slice(0, 15).join('\n');
            previewEl.textContent = previewLines + (lines > 15 ? '\n... [' + (lines - 15) + ' more lines]' : '');

            loadedPanel.classList.add('active');
            resultsPanel.classList.remove('active');
            timingEl.textContent = 'File loaded. Click "Run Cherm Security Audit" to inspect.';
        };
        reader.readAsText(file);
    }

    function clearSelectedFile() {
        loadedCode = '';
        loadedFilename = '';
        fileInput.value = '';
        loadedPanel.classList.remove('active');
        resultsPanel.classList.remove('active');
        timingEl.textContent = '';
    }

    function runAuditAction() {
        if (!loadedCode || !loadedCode.trim()) {
            alert('No file content loaded to audit.');
            return;
        }
        executeAudit(loadedCode, loadedFilename, btnRunCheck, timingEl);
    }

    function runPasteAudit() {
        const code = document.getElementById('paste-code').value;
        const btn = document.getElementById('btn-paste-check');
        const timing = document.getElementById('paste-timing');
        if (!code || !code.trim()) {
            alert('Please paste some code to audit.');
            return;
        }
        executeAudit(code, 'snippet.py', btn, timing);
    }

    async function executeAudit(code, filename, btn, timingElem) {
        btn.disabled = true;
        const originalText = btn.textContent;
        btn.textContent = 'Auditing...';
        loadingState.classList.add('active');
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
            displayResults(data);
        } catch (err) {
            timingElem.textContent = 'Error: ' + err.message;
            alert('Audit failed: ' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
            loadingState.classList.remove('active');
        }
    }

    function displayResults(data) {
        if (!data.success) {
            alert('Audit Error: ' + (data.error || 'Failed to analyze code'));
            return;
        }

        const s = data.summary || {};
        const grade = data.health_grade || 'GRADE A';
        const badgeEl = document.getElementById('res-badge');
        const statusEl = document.getElementById('res-status');

        statusEl.textContent = (data.status || 'PASS') + ' • ' + grade;
        badgeEl.textContent = grade;
        badgeEl.className = 'grade-badge';

        if (grade.includes('A')) {
            badgeEl.classList.add('grade-a');
        } else if (grade.includes('B')) {
            badgeEl.classList.add('grade-b');
        } else {
            badgeEl.classList.add('grade-c');
        }

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
                const isFatal = it.includes('[FATAL]') || it.includes('[CRITICAL]');
                itemDiv.className = 'finding-item ' + (isFatal ? 'fatal' : 'warning');
                itemDiv.textContent = it;
                list.appendChild(itemDiv);
            });
        }

        resultsPanel.classList.add('active');
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
            fallback = "<html><body style='font-family:sans-serif;padding:30px;color:#0f172a'><h3>No audit report generated yet. Run an audit on a file first.</h3></body></html>"
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
            if length > 10000000:
                self._send_json({"error": "Payload exceeds 10MB limit"}, 413)
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
    print("  Status:          Listening for file uploads...")
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
