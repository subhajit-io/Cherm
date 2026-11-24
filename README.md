<div align="center">
  <div style="background-color: #0b0f19; padding: 24px 40px; border-radius: 12px; display: inline-block; margin-bottom: 12px; border: 1px solid #1e293b; box-shadow: 0 4px 20px rgba(0,255,128,0.15);">
    <span style="color: #38bdf8; font-family: monospace; font-size: 26px; font-weight: 900; letter-spacing: 4px; text-shadow: 0 0 10px rgba(56, 189, 248, 0.7);">( | - | [ - | ~ | \ / | ;</span>
  </div>
  <h1>Cherm</h1>
  <p><b>Interactive Terminal Companion • Model Context Protocol (MCP) Server • Localhost Web GUI</b></p>

  <p>
    <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+">
    <img src="https://img.shields.io/badge/Node.js-18%2B-339933?style=for-the-badge&logo=nodedotjs&logoColor=white" alt="Node.js 18+">
    <img src="https://img.shields.io/badge/Next.js-App%20%2F%20Pages%20Router-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" alt="Next.js">
    <img src="https://img.shields.io/badge/MCP-FastMCP%202.0-8A2BE2?style=for-the-badge&logo=anthropic&logoColor=white" alt="FastMCP 2.0">
    <img src="https://img.shields.io/badge/GUI-Localhost%3A3690-00C781?style=for-the-badge" alt="Localhost 3690">
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-informational?style=for-the-badge" alt="Cross-Platform">
    <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="MIT License">
  </p>
</div>

---

> **A high-speed, local code analysis & system design inspection suite built for developers and AI agents alike — catching architectural flaws, race conditions, IDOR, and code smells before code is ever committed.**

Cherm operates across three flexible modalities:
1. **GUI (Terminal Companion)**: Classic curses-based terminal companion (`cherm gui`) with reactive ASCII avatar, AST fuzzer, and security suite.
2. **Web (Localhost Dashboard)**: Clean, distraction-free browser dashboard (`cherm web`) running on **`http://localhost:3690`** for visual drag & drop code & folder audits.
3. **Commands (Structured CLI Engine)**: Dedicated native CLI commands for CI/CD and terminal workflows:
   * **`check`**: Fast deterministic syntax, OWASP vulnerability, secrets, and dead code checks.
   * **`audit`**: Deep architecture, concurrency TOCTOU, and IDOR analysis with optional HTML report generation.
   * **`mcp`**: Zero-token FastMCP bridge for Claude Desktop, Cursor, Antigravity, and Gemini.
   * **`ext`**: Isolated extension engine for running and registering custom CLI tools and external scripts.

---

## 📸 Snapshots & UI Tour

### 1. Interactive Terminal Companion (TUI)
*Runs fully offline inside your terminal with zero IDE lag, instant keyboard navigation, and shadow copy safety.*

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  (•‿•)   Cherm Terminal Companion                 [Status: Optimal]          │
├──────────────────────────────────────────────────────────────────────────────┤
│  TERMINAL CLOCK --                                                 __21:30:15│
│  [P]  order_controller.py                             (src/api/v1)           │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│                         Language / Execution Tools   >                       │
│                         General File Tools           >                       │
│                         Advanced Analysis & Security >                       │
│                   [*]   Cherm MCP Bridge (AI Server)                         │
│                   [*]   Launch Web GUI (localhost:3690)                      │
│                   ────────────────────────────────────────────               │
│                         Select Different File                                │
│                         Help  (?)                                            │
│                         Exit                                                 │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  Up/Down:Nav  Enter:Run  B:Bookmark  ?:Help  Q:Back  ESC:Exit                │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

### 2. Localhost Web GUI (`http://localhost:3690`)
*Minimalist, zero-slop drag-and-drop code & project auditor running locally in your browser with `python cherm.py --gui`. Supports single files or entire repository folders.*

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│  Cherm — Code & Project Auditor                              localhost:3690  │
├──────────────────────────────────────────────────────────────────────────────┤
│  [ Drag & Drop (File or Folder) ]   [ Local Directory Scan ]   [ Snippet ]   │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│       ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐     │
│                     [ 📁 Drag & Drop File OR Full Folder ]                   │
│                                                                              │
│             Drop any single file or drag an entire project folder            │
│            [ 📄 Browse Single File ]     [ 📁 Browse Full Folder ]           │
│       └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘     │
│                                                                              │
├──────────────────────────────────────────────────────────────────────────────┤
│  📁 PROJECT: my-next-app (16 code files • 2,410 lines • 120 KB)              │
│  [ ⚡ Run Full Project Audit (16 files) ]                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│  PROJECT GRADE: [ GRADE A ]   Status: 16/16 Files Clean • PASS               │
│  • Files Audited: 16     • Vulnerable Files: 0     • Total Issues: 0         │
│  • Fatal Flaws:   0      • Concurrency Flaws: 0    • Design Flaws: 0         │
│                                                                              │
│  FILE BREAKDOWN:                                                             │
│  [PASS]     src/app/checkout/page.tsx                     (140 lines • Clean)│
│  [PASS]     src/lib/auth.ts                               (88 lines • Clean) │
│  [PASS]     src/components/Header.tsx                     (62 lines • Clean) │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 🧠 The 3-Stage Hybrid Review Pipeline

Cherm combines deterministic static rules with external AI agent verification through the **Model Context Protocol (MCP)**:

```mermaid
flowchart TD
    A["Raw Code / Commit Target"] --> B["Stage 1: Cherm Deterministic Engine"]
    
    subgraph S1["Stage 1: Deterministic Static Engine (Zero AI Tokens)"]
        B --> B1["Multi-Tap Race Condition Fuzzer"]
        B --> B2["System Design Flaw Scanner (IDOR, Pool Leaks)"]
        B --> B3["AST Code Smell Detector & Fix Recipes"]
        B --> B4["Halstead Complexity & Shannon Entropy"]
    end
    
    B1 --> C["Consolidated Audit History & HTML Report"]
    B2 --> C
    B3 --> C
    B4 --> C
    
    C --> D["Stage 2: AI Verification via MCP Bridge"]
    
    subgraph S2["Stage 2: Model Context Protocol (FastMCP)"]
        D --> D1["Claude Desktop"]
        D --> D2["Cursor IDE"]
        D --> D3["Google Antigravity / Gemini CLI"]
    end
    
    D1 --> E["Stage 3: Decision Gate & Fix Confirmation"]
    D2 --> E
    D3 --> E
    
    subgraph S3["Stage 3: Developer Control"]
        E --> F["Confirmed Issues & Production Risks"]
        E --> G["Dismissed False Positives"]
        E --> H["Safe, User-Approved Fix Application"]
    end
```

---

## ⚡ Three Primary Modalities & Quick Start

### 1. GUI Mode (Terminal Companion)
Launch the interactive full-terminal companion:
```bash
# Open interactive file picker
python cherm.py gui

# Or launch directly targeted at a file
python cherm.py gui src/auth.py
```

---

### 2. Web Mode (Localhost Browser Dashboard)
Launch the browser dashboard on port **`3690`** (`http://localhost:3690`):
```bash
# Starts server and automatically opens your default browser
python cherm.py web

# Or specify a custom port
python cherm.py web --port 8080
```

---

### 3. Commands Mode (CLI Engine)

Cherm provides cleanly namespaced commands for deterministic checks, system design audits, and external software extensions:

#### A. Deterministic Code Checks (`check`)
Fast static checks without IDE overhead or curses UI:
```bash
# Run all checks (syntax, security, secrets, dead code) on a file or folder
python cherm.py check src/auth.py
python cherm.py check ./src

# Target specific checks
python cherm.py check src/auth.py --syntax      # Syntax compilation check only
python cherm.py check src/auth.py --security    # OWASP pattern scanner only
python cherm.py check src/auth.py --secrets     # Shannon entropy secrets scan only
python cherm.py check src/auth.py --deadcode    # Python AST dead code detector only

# Output machine-readable JSON for CI/CD
python cherm.py check src/auth.py --json
```

#### B. Deep Architecture & System Design Audit (`audit`)
Deep multi-file analysis testing for TOCTOU race hazards, IDOR/BOLA object leaks, and connection pool exhaustion:
```bash
# Audit an entire repository folder or single file
python cherm.py audit ./src

# Generate standalone visual HTML report (cherm_audit_report.html)
python cherm.py audit ./src --report

# Output structured JSON
python cherm.py audit ./src --json
```

#### C. Model Context Protocol Bridge (`mcp`)
Start Cherm as an MCP server for AI assistants:
```bash
# Standard stdio mode (for Claude Desktop, Cursor, Antigravity)
python cherm.py mcp

# SSE mode for web/network integration
python cherm.py mcp --sse --port 8000
```

#### D. Connected Software & Extension Engine (`ext`)
Isolated container for registering and executing custom CLI tools and external scripts:
```bash
# List all registered external commands
python cherm.py ext list

# Execute a connected command
python cherm.py ext run file_details_cli src/main.py

# Register a new external CLI tool
python cherm.py ext add my_linter "Custom Linter" "eslint {file}" ".js,.ts" "Linters"

# Direct alias execution (runs any registered command ID directly)
python cherm.py my_linter src/main.py
```

#### E. Dedicated Feature CLI Commands
Every individual inspection feature in Cherm is available as a standalone first-class terminal command:

| Category | Command | Target | Description |
| :--- | :--- | :--- | :--- |
| **Quality** | `python cherm.py syntax <file>` | File or dir | Validate syntax & compilation without execution |
| **Quality** | `python cherm.py complexity <file>` | File or dir | Calculate Big-O time & space, cyclomatic complexity & nesting |
| **Quality** | `python cherm.py deadcode <file>` | File or dir | AST detection of uncalled functions & unused variables |
| **Quality** | `python cherm.py magic <file>` | File or dir | Scan for bare numeric literals / unexplained magic numbers |
| **Quality** | `python cherm.py stats <file>` | File or dir | Line count, code vs comments vs blank ratio, size, words |
| **Quality** | `python cherm.py scan <file>` | File or dir | Extract & index all defined functions, classes, exports & types |
| **Quality** | `python cherm.py fuzz <file>` | Python file | CrossCheckV200 dynamic mock injection & input boundary fuzzer |
| **Security** | `python cherm.py sec <target>` | File or dir | OWASP static vulnerability detector (SQLi, XSS, Command Injection) |
| **Security** | `python cherm.py secrets <target>` | File or dir | Shannon entropy & pattern scanner for API keys, passwords & tokens |
| **Security** | `python cherm.py pentest <target>` | File or dir | Security orchestration with Bandit, Semgrep, and Safety |
| **Security** | `python cherm.py crypto <file>` | File | SHA-256 integrity check, timing attacks, unsalted password hashes |
| **Architecture** | `python cherm.py design <target>` | File or dir | Audit for BOLA/IDOR, pool exhaustion, missing rollback, CORS |
| **Architecture** | `python cherm.py race <file>` | File | Concurrency multi-tap & TOCTOU double-spend hazard detector |
| **Architecture** | `python cherm.py ml <file>` | File | Machine learning AST structural anomaly scoring & Halstead metrics |
| **Architecture** | `python cherm.py check <target>` | File or dir | Deterministic all-in-one check (syntax, security, secrets, deadcode) |
| **Architecture** | `python cherm.py audit <target>` | File or dir | Deep architectural & concurrency audit with optional `--report` |
| **Utilities** | `python cherm.py urls <target>` | File or dir | Discover HTTP/API endpoints and verify responsiveness |
| **Utilities** | `python cherm.py diff <f1> [f2]` | Files | Unified terminal diff viewer against Git HEAD or baseline file |
| **Utilities** | `python cherm.py git [args]` | Workspace | Terminal Git command center |
| **Utilities** | `python cherm.py report <target>` | File or dir | Generate visual standalone HTML audit report dashboard (`--open`) |

---

### 📖 Complete Command Reference Manual

#### 1. Code Quality & Complexity Commands

##### `syntax` — Syntax & Bytecode Compilation Check
Validates code syntax and parses AST without executing untrusted code.
* **Usage:** `python cherm.py syntax <file|dir> [--json]`
* **Supported files:** Python (`.py`), JSON (`.json`), JavaScript, TypeScript, Go, SQL.
* **Example:**
  ```bash
  python cherm.py syntax src/server.py
  python cherm.py syntax ./src --json
  ```

##### `complexity` — Algorithmic Time, Space & Cyclomatic Complexity
Estimates Big-O time and space complexity, cyclomatic branching score, and maximum loop/nesting depth.
* **Usage:** `python cherm.py complexity <file|dir> [--json]`
* **Metrics:** Big-O Time (`O(1)`, `O(N)`, `O(N²)`, `O(N^k)`), Space complexity, Cyclomatic Score, Verdict (`Clean`, `Moderate`, `High Complexity`).
* **Example:**
  ```bash
  python cherm.py complexity src/algorithms.py
  ```

##### `deadcode` — Unused Function & Dead Branch Detector
Uses AST inspection to discover functions and variables that are defined but never invoked across the module.
* **Usage:** `python cherm.py deadcode <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py deadcode src/utils.py
  ```

##### `magic` — Magic Numbers Scanner
Detects bare, unexplained numeric literals in expressions that should be extracted into named constants for maintainability.
* **Usage:** `python cherm.py magic <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py magic src/pricing_engine.py
  ```

##### `stats` — Source Code Metrics & Ratios
Reports total lines, physical lines of code (SLOC), blank lines, comment ratio (%), byte size, and vocabulary size.
* **Usage:** `python cherm.py stats <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py stats src/main.py
  ```

##### `scan` — Declaration & Symbol Indexer
Scans code and extracts all function signatures, classes, types, interfaces, and module exports.
* **Usage:** `python cherm.py scan <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py scan src/models.py
  ```

##### `fuzz` — CrossCheckV200 Dynamic Mock Injection
Simulates edge-case inputs (null, empty strings, negative numbers, floats, integer overflows, boundary arrays) on functions to verify input contracts.
* **Usage:** `python cherm.py fuzz <file.py> [--json]`
* **Example:**
  ```bash
  python cherm.py fuzz src/parser.py
  ```

---

#### 2. Security & Penetration Testing Commands

##### `sec` — OWASP Static Vulnerability Scanner
Scans source files for top OWASP vulnerability patterns without requiring cloud or network connectivity.
* **Vulnerabilities checked:** SQL Injection (f-strings, concatenation), Command Injection (`os.system`, `subprocess(shell=True)`), Code Injection (`eval`, `exec`), Path Traversal, XSS (`innerHTML`, `dangerouslySetInnerHTML`), SSRF (`urlopen`, `requests.get`), Insecure Deserialization (`pickle.loads`, `yaml.load`), Weak Cryptography (MD5, SHA1), and CORS wildcards (`*`).
* **Usage:** `python cherm.py sec <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py sec src/api/endpoints.py
  python cherm.py sec ./src --json
  ```

##### `secrets` — Shannon Entropy & Hardcoded Credential Detector
Scans code using high-entropy mathematics and regular expression signatures to find exposed secrets before they reach git.
* **Secrets detected:** AWS Access Key IDs, GitHub Personal Access Tokens (PAT), JWT tokens, Stripe secret keys, hardcoded passwords, Bearer tokens, and Private Key blocks (`BEGIN PRIVATE KEY`).
* **Usage:** `python cherm.py secrets <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py secrets src/config.py
  ```

##### `pentest` — Automated Security Tool Orchestration
Orchestrates static analysis and security linters (Bandit for Python, Semgrep for polyglot rules, Safety for vulnerable packages).
* **Usage:** `python cherm.py pentest <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py pentest ./src
  ```

##### `crypto` — SHA-256 Cryptographic Integrity & Cipher Audit
Calculates deterministic SHA-256 checksums, verifies tamper baselines, and inspects code for cryptographic anti-patterns.
* **Checks:** Non-constant-time comparisons (Timing Attacks), raw unsalted SHA-256 password hashing, weak hashing algorithms, and ECB block cipher modes.
* **Usage:** `python cherm.py crypto <file> [--json]`
* **Example:**
  ```bash
  python cherm.py crypto src/auth.py
  ```

---

#### 3. Architecture & System Design Commands

##### `design` — System Design & Scaling Flaw Auditor
Scans for architectural vulnerabilities that bypass unit tests but crash production servers or leak data.
* **Flaws audited:** Broken Object Level Authorization (BOLA/IDOR), database connection pool exhaustion (missing pool close/release), unhandled transaction rollbacks, CORS wildcard permissions, and unbounded query pagination.
* **Usage:** `python cherm.py design <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py design src/controllers/order.py
  ```

##### `race` — Multi-Tap & TOCTOU Race Condition Simulator
Simulates rapid parallel requests (50 simultaneous taps in 1.0s) against critical financial and state-mutation endpoints to detect Check-Then-Act (TOCTOU) race conditions and double-spending vulnerabilities.
* **Checks:** Missing frontend button debounce/disabling, missing backend `Idempotency-Key` headers, and missing database row-level locking (`SELECT ... FOR UPDATE`).
* **Usage:** `python cherm.py race <file> [--json]`
* **Example:**
  ```bash
  python cherm.py race src/payment_processor.py
  ```

##### `ml` — Machine Learning AST Structural Anomaly & Defect Risk
Applies local machine learning algorithms (Isolation Forest for structural AST anomaly detection, Halstead software science metrics, and Shannon entropy) to calculate an aggregate defect propensity score (0-100).
* **Usage:** `python cherm.py ml <file> [--json]`
* **Example:**
  ```bash
  python cherm.py ml src/core.py
  ```

##### `check` — All-In-One Deterministic Code Checker
Fast, lightweight check covering syntax, OWASP vulnerabilities, secrets, and dead code in a single command.
* **Usage:** `python cherm.py check <file|dir> [--syntax] [--security] [--secrets] [--deadcode] [--json]`
* **Example:**
  ```bash
  python cherm.py check src/auth.py
  python cherm.py check ./src --syntax --security
  ```

##### `audit` — Deep Full-System Architectural Audit
Full-scale architectural audit producing overall project Health Grades (Grade A to F), categorized issue counts, and optional standalone visual HTML report generation.
* **Usage:** `python cherm.py audit <file|dir> [--report] [--json]`
* **Example:**
  ```bash
  python cherm.py audit ./src
  python cherm.py audit ./src --report    # Generates cherm_audit_report.html
  ```

---

#### 4. Utilities & Diagnostics

##### `urls` — API Endpoints & URL Connectivity Checker
Discovers all HTTP and HTTPS endpoints declared in source files and sends concurrent lightweight HEAD/GET probes to verify server responsiveness.
* **Usage:** `python cherm.py urls <file|dir> [--json]`
* **Example:**
  ```bash
  python cherm.py urls src/services/api_client.py
  ```

##### `diff` — Terminal Side-by-Side Unified Diff Viewer
Provides formatted unified diff output against Git HEAD or compares two arbitrary files directly in the terminal.
* **Usage:**
  - Compare file against git HEAD: `python cherm.py diff <file>`
  - Compare two files: `python cherm.py diff <file1> <file2>`
  - Git working tree diff: `python cherm.py diff`
* **Example:**
  ```bash
  python cherm.py diff src/auth.py
  python cherm.py diff version1.py version2.py
  ```

##### `git` — Interactive Git Command Center
Runs arbitrary Git operations directly through Cherm's unified CLI runner.
* **Usage:** `python cherm.py git [status|diff|log|branch|...]`
* **Example:**
  ```bash
  python cherm.py git status -s
  python cherm.py git log -n 5 --oneline
  ```

##### `report` — Visual Standalone HTML Dashboard Generator
Compiles an interactive, standalone HTML audit report (`cherm_audit_report.html`) complete with metrics, flaw breakdowns, and fix recommendations.
* **Usage:** `python cherm.py report <file|dir> [--open]`
* **Example:**
  ```bash
  python cherm.py report ./src --open     # Generates report and opens default browser
  ```

---

#### 5. Connected Software & Extension Engine (`ext`)

Cherm enables developers to integrate external tools, custom scripts, and third-party linters cleanly via `cherm_commands.json`:

##### `ext list` — List Connected Software Commands
Displays all registered tools, their command templates, target file extensions, and categories.
* **Usage:** `python cherm.py ext list [--json]`

##### `ext add` — Register an External Tool
Adds or updates a custom tool command definition in the configuration registry.
* **Usage:** `python cherm.py ext add <id> <name> <cmd_template> [extensions] [category]`
* **Example:**
  ```bash
  python cherm.py ext add py_black "Black Formatter" "black {file}" ".py" "Formatters"
  python cherm.py ext add es_lint "ESLint" "npx eslint {file}" ".js,.ts,.tsx" "Linters"
  ```

##### `ext remove` — Unregister an External Tool
Removes a command ID from the configuration registry.
* **Usage:** `python cherm.py ext remove <id>`
* **Example:**
  ```bash
  python cherm.py ext remove py_black
  ```

##### `ext run` — Execute an External Command
Runs a connected command using Cherm's secure execution runner with variable interpolation.
* **Usage:** `python cherm.py ext run <id> [file] [extra_args...]`
* **Example:**
  ```bash
  python cherm.py ext run py_black src/server.py
  ```

##### Direct Command Alias (Top-Level Execution)
Any registered command ID can also be run directly as a top-level command alias:
* **Example:**
  ```bash
  python cherm.py py_black src/server.py
  python cherm.py es_lint src/App.tsx --fix
  ```

#### Template Placeholders Supported in Commands:
* `{file}`: Full absolute path to target file
* `{filename}`: File name with extension (e.g. `auth.ts`)
* `{basename}`: File name without extension (e.g. `auth`)
* `{ext}`: Extension (e.g. `.ts`)
* `{dir}`: Directory containing the target file
* `{cwd}`: Current working directory / project root
* `{python}`: Current Python interpreter executable path
* `{args}`: Additional arguments passed to the command

*Configuration is stored in `cherm_commands.json` (or `.cherm/commands.json`) and editable directly or via TUI and Web GUI!*

---

## 🤖 MCP AI Agent Configuration

Add Cherm to your AI assistant's configuration file:

### Claude Desktop (`claude_desktop_config.json`) / Cursor (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "cherm": {
      "command": "python",
      "args": ["<path-to-cherm>/cherm.py", "--mcp"]
    }
  }
}
```

### Google Antigravity / Gemini CLI (`mcp_config.json`):
```json
{
  "mcpServers": {
    "cherm": {
      "command": "python",
      "args": ["C:/Antigravity program/checkinterminal/cherm.py", "--mcp"]
    }
  }
}
```

---

## 🛠️ The 11 Cherm MCP Tools

| Tool Name | Scope & Detection Capabilities |
| :--- | :--- |
| **`run_folder_audit`** | Full project & folder pipeline: scans entire directories or multi-file uploads (up to 500 files), calculating project health grade, per-file issue breakdown, and comprehensive HTML report. |
| **`run_all_in_one_check`** | Full audit pipeline: system design flaws, race conditions, AST code smells, ML defect risk score, and standalone HTML report. |
| **`audit_system_design_flaws`** | Architectural vulnerabilities: BOLA/IDOR object exposure, database connection pool exhaustion, missing transaction rollbacks, CORS wildcards, and unhandled network timeouts. |
| **`explain_code_issues`** | AST anti-patterns: mutable default arguments (state leakage), bare `except:` clauses swallowing SIGTERM, and silent error suppression (`except: pass`) with exact fix recipes. |
| **`stress_test_multitap_vulnerability`** | Concurrency simulation: checks for Check-Then-Act (TOCTOU) race conditions, double-spend vulnerabilities, and missing row-level locking (`SELECT ... FOR UPDATE`). |
| **`audit_sha256_cryptographic_integrity`** | Cryptographic checks: weak hashing algorithms (MD5/SHA1), ECB block cipher modes, hardcoded IVs/salts, and timing side-channel leaks. |
| **`audit_ml_defects`** | Machine learning metrics: Halstead software complexity, AST structural anomaly detection via Isolation Forest, and Shannon Entropy secret scanning. |
| **`generate_html_audit_report`** | Generates a clean, professional, visual HTML report saved at `cherm_audit_report.html`. |
| **`list_connected_software_commands`** | Lists all custom developer terminal commands and external software connected to Cherm via `cherm_commands.json`. |
| **`run_connected_software_command`** | Executes an external software CLI command or custom developer script, returning stdout, stderr, exit code, and runtime duration. |
| **`register_software_command`** | Programmatically registers a new external software terminal command into Cherm's command hub. |

---

## 🛡️ Core Analysis Features

### Security & Penetration Testing
* **Full Pentest Suite:** Orchestrates `bandit` (Python deep scan), `semgrep` (multi-language security rules), and `safety` (dependency CVE check).
* **OWASP Vulnerability Audit:** Zero-dependency static pattern audit for SQL Injection, Command Injection, XSS, Path Traversal, and SSRF.
* **Shannon Entropy Secrets Detector:** Identifies high-entropy tokens, passwords, and API keys (AWS, GitHub PAT, Stripe, JWT) across source files.

### Node.js & Next.js Full-Stack Architecture Analysis
* **Event Loop Starvation Detection:** Automatically flags synchronous blocking operations (`fs.readFileSync`, `fs.writeFileSync`, `execSync`) on Node.js / Express / Next.js server threads.
* **Next.js `NEXT_PUBLIC_` Leaks:** Intercepts accidental leakage of backend secrets (database credentials, API keys, private tokens) exposed to client browsers via `NEXT_PUBLIC_` variable names.
* **Server Action & Route Guard Auditing:** Analyzes Next.js 14/15 App Router Server Actions (`'use server'`) for missing authentication, authorization, or rate-limiting guards.
* **Client / Server Boundary Validation:** Verifies `'use client'` directive presence on components utilizing React hooks (`useState`, `useEffect`, `useContext`) to avoid build failures and SSR hydration bugs.
* **Command Injection & Directory Traversal:** Discovers unescaped dynamic string interpolation in `child_process.exec` and boundary-breaking `path.join` / `path.resolve` parameters.
* **React XSS Prevention:** Flags unsanitized HTML injections via `dangerouslySetInnerHTML`.
* **Integrated Next.js Tooling:** Built-in TUI commands for `npx next lint`, `npx next build`, `npx tsc --noEmit`, and `npm audit`.

### Code Quality & AST Analysis
* **CrossCheckV200 Engine:** Automated function-level fuzz testing with dynamic mock injection to catch unexpected edge-case crashes.
* **Speed & Complexity Calculator:** Evaluates cyclomatic complexity, maximum nesting depth, and estimated Big-O Time & Space complexity.
* **Dead Code & Magic Number Scanner:** Flags unused variables, unreachable branches, and bare numeric literals that belong in named constants (supporting Python, JS, JSX, TS, TSX).
* **Shadow Copy Safety:** Original files are never modified or locked. All analysis runs inside an isolated shadow directory (`%TEMP%/cherm_shadow`).

---

## 🌐 Supported Languages & Ecosystems

Cherm provides native syntax validation, structure mapping, AST inspection, and security checks across:
* **Python**: Python 3.8+ (`.py`, `.pyw`) with AST parsing, Bandit, Semgrep, and Dead Code detection.
* **Node.js**: Modern JavaScript (`.js`, `.mjs`, `.cjs`) with event loop profiling, sync I/O alerts, and command injection scanning.
* **TypeScript & React**: Modern TS/TSX (`.ts`, `.tsx`, `.jsx`) with `tsc --noEmit` and component structure inspection.
* **Next.js**: App Router & Pages Router (`next.config.*`, Server Actions, SSR/SSG boundary checks, `npx next lint/build`).
* **Polyglot Systems**: Go, Rust, Java, C, C++, SQL, Ruby, PHP, Kotlin, Swift, Shell/Bash, PowerShell, HTML, CSS, JSON, YAML.

---

## 📦 Requirements & Installation

```bash
# Clone the repository
git clone https://github.com/subhajit-io/Cherm.git
cd Cherm/check-in-terminal

# Install dependencies for MCP and ML engines
pip install -r requirements_mcp.txt
```

*Requirements include:* `fastmcp>=2.0.0`, `uvicorn>=0.30.0`, `pydantic>=2.0.0`, `scikit-learn>=1.4.0`, `numpy>=1.26.0`.

---

## ⌨️ Global Keyboard Shortcuts (TUI)

| Key | Action |
| :---: | :--- |
| `Up` / `Down` | Navigate menu items and file lists |
| `Enter` | Select file or run highlighted action |
| `B` | Toggle bookmark on active file |
| `H` | Open generated HTML audit report in browser |
| `?` | Open interactive Help Panel |
| `Q` | Back to previous menu or return from results |
| `ESC` | Exit Cherm / Return to file selection |

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.
Built with ❤️ by [Subhajit Das](https://github.com/subhajit-io).
