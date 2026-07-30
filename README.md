**A `curses`-based interactive Text User Interface (TUI) for real-time code analysis, security pentesting, and developer joy—complete with a virtual terminal companion.**[cite: 1]

Cherm is a powerful, entirely local static analysis and security toolkit designed to catch bugs, vulnerabilities, and messy code before you ever commit. It runs directly in your terminal and features a live virtual pet that reacts to your code's health and your activity.[cite: 1]

---

## Key Features

### Full Penetration Test Engine & Security
*   **OWASP Vulnerability Scanner:** Built-in detection for SQL Injection, Command Injection, XSS, SSRF, Path Traversal, and more[cite: 1].
*   **Hardcoded Secret Scanner:** Scans for over 20 types of exposed secrets, including AWS Keys, GitHub PATs, Stripe keys, and DB passwords[cite: 1].
*   **Automated Integration:** Automatically installs and runs `bandit` (Python deep scan), `semgrep` (Multi-language rules), and `safety` (Dependency CVEs)[cite: 1].

### Code Quality & Performance
*   **Speed & Complexity Analysis:** Calculates Cyclomatic Complexity score and estimates Big-O Time & Space complexity[cite: 1].
*   **Dead Code Detector:** Uses Python AST (and regex for other languages) to find unused functions and methods[cite: 1].
*   **Magic Number Detector:** Flags bare numeric literals that should be replaced with named constants[cite: 1].
*   **Python Auto-Fuzzer:** Automatically injects mock arguments into Python functions to test for crashes and infinite loops[cite: 1].

### Developer Utilities
*   **Interactive Git Command Center:** A scrollable menu of over 40 Git commands to check status, stage, commit, diff, and branch directly from the TUI[cite: 1].
*   **API Health Monitor:** Automatically detects HTTP/HTTPS URLs in your code and pings them to check connection status and latency[cite: 1].
*   **Diff Viewer:** Unified visual diff viewer to compare your working tree against Git `HEAD` or against another file[cite: 1].
*   **Multi-File Batch Checker:** Run universal syntax and connection checks across multiple selected files simultaneously[cite: 1].

### The Virtual Companion
*   **Reactive Emotions:** The built-in companion face changes emotions based on your actions[cite: 1].
*   **State Management:** Becomes "happy" on success, "angry" or "sad" when finding issues, "error" when processes fail, and "tired" (Zzz) if you leave the terminal idle for 30 minutes[cite: 1].

---

## Supported Languages

Cherm supports syntax checking, structure scanning, and analysis for a massive array of languages[cite: 1]:
*   Python, JavaScript, TypeScript, Java, C, C++, Go, Rust, Ruby, PHP, Kotlin, Swift, Bash/Shell, PowerShell, Perl, R, HTML, CSS, JSON, YAML, Markdown, SQL[cite: 1].

---

## Installation & Usage

**Prerequisites:** Python 3.x installed on your system.

1.  Clone the repository and navigate to the folder.
2.  Run the application:
    ```bash
    python cherm.py
    ```
    *(Alternatively, you can pass a specific file directly: `python cherm.py my_script.py`)*[cite: 1]

---

## ⌨️ Keyboard Shortcuts

Cherm is designed for fast, mouse-free navigation[cite: 1].

| Key | Action |
| :--- | :--- |
| **Up / Down** | Navigate menus, files, or scroll output[cite: 1] |
| **Enter** | Open file or run selected action[cite: 1] |
| **Left / Backspace** | Go to parent directory[cite: 1] |
| **Space** | Toggle multi-select (in multi-picker mode)[cite: 1] |
| **B** | Toggle bookmark for the selected file[cite: 1] |
| **?** | Open the Help panel[cite: 1] |
| **Q / ESC** | Go back, cancel, or exit[cite: 1] |

---

## File Browser & Bookmarks

*   **Bookmarks:** Press `B` on any file to bookmark it for quick access later. Bookmarks are saved persistently to `cherm_bookmarks.json`[cite: 1].
*   **Multi-Select:** Press `M` or `Space` to select multiple files to run batch security and syntax checks across your project[cite: 1].
