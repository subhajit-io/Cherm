# Cherm Architecture & AI Agent Operating Rules

This guide defines how AI coding assistants (Google Antigravity, Gemini CLI, Claude Desktop, Cursor) interact with **Cherm** across its 3 modalities and FastMCP bridge.

---

### The Three Cherm Modalities

1. **GUI (Terminal Companion)**:
   ```bash
   python cherm.py gui [file]
   ```
   Interactive curses-based TUI with real-time ASCII companion, keyboard navigation, and shadow copy isolation.

2. **Web (Localhost Dashboard)**:
   ```bash
   python cherm.py web [--port 3690]
   ```
   Zero-dependency local browser dashboard running at `http://localhost:3690` for drag-and-drop file and whole-directory auditing.

3. **Commands (Dedicated CLI Engine)**:
   ```bash
   python cherm.py <command> [target] [options]
   ```
   First-class terminal commands for CI/CD, scripting, and modular inspection:
   - **Quality**: `syntax`, `complexity`, `deadcode`, `magic`, `stats`, `scan`, `fuzz`
   - **Security**: `sec`, `secrets`, `pentest`, `crypto`
   - **Architecture**: `design`, `race`, `ml`, `check`, `audit`
   - **Utilities**: `urls`, `diff`, `git`, `report`
   - **Extensions**: `ext list`, `ext run`, `ext add`, `ext remove`

---

### Connected Software & Extension Engine

Cherm allows developers to register external CLI tools and software in `cherm_commands.json`:
- `python cherm.py ext list` — List all registered external commands.
- `python cherm.py ext run <id> [file] [args]` — Execute an external command.
- `python cherm.py <custom_id> [args]` — Execute any registered command ID directly as a top-level alias.
- **Variables supported in commands**: `{file}`, `{filename}`, `{basename}`, `{ext}`, `{dir}`, `{cwd}`, `{python}`, `{args}`.

---

### FastMCP Tool Reference (11 Tools)

When communicating via MCP, use the following tools:
1. `run_folder_audit` — Recursively audit an entire project directory (up to 500 files).
2. `run_all_in_one_check` — Full audit pipeline on a single file with HTML report.
3. `audit_system_design_flaws` — Scan for BOLA/IDOR, DB connection pool leaks, missing rollbacks, CORS wildcards.
4. `explain_code_issues` — AST anti-pattern scanner with concrete fix recipes.
5. `stress_test_multitap_vulnerability` — Concurrency fuzzer for TOCTOU and double-spend race hazards.
6. `audit_sha256_cryptographic_integrity` — Cryptographic hash validation, timing attack detection, and cipher checks.
7. `audit_ml_defects` — Machine learning AST anomaly scoring, Halstead complexity metrics, and Shannon entropy.
8. `generate_html_audit_report` — Compile visual audit results into standalone HTML report.
9. `list_connected_software_commands` — Query registered external commands and custom developer tools.
10. `run_connected_software_command` — Execute a connected external tool or script.
11. `register_software_command` — Programmatically add a new command to `cherm_commands.json`.

---

### Hybrid Cherm + AI Review Workflow (`@cherm-audit` / `audit with cherm`)

Whenever auditing or reviewing code with Cherm:

1. **Stage 1 (Cherm Deterministic Static Check):**
   - Run `cherm_mcp.run_all_in_one_check` or `python cherm.py check <target>`.
   - Cherm rapidly scans for multi-tap race conditions, DB pool starvation, BOLA/IDOR, crypto flaws, and code smells without using AI tokens.
   - Automatically compiles findings into `cherm_audit_report.html`.

2. **Stage 2 (AI Verification & Second Opinion Filter):**
   - Inspect each of Cherm's static findings against the actual application logic.
   - Filter out false positives (e.g. static patterns that are safe because of out-of-band middleware, or intentional exceptions).
   - Confirm true positives and provide contextual reasoning on severity.

3. **Stage 3 (User Control & Decision Gate):**
   - Present a concise, prioritized review summary to the user:
     - **Confirmed Issues:** Real bugs/risks with recommended fixes.
     - **Dismissed False Positives:** Flags from Cherm that were safely handled.
   - Ask the user for confirmation: *"Would you like me to apply these fixes to the file now?"*
   - Never overwrite code until the user gives explicit approval.
