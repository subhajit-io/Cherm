**A `curses`-based interactive Text User Interface (TUI) for real-time code analysis, security pentesting, and developer joy—complete with a virtual terminal companion.**

Cherm is a powerful, entirely local static analysis and security toolkit designed to catch bugs, vulnerabilities, and messy code before you ever commit. It runs directly in your terminal and features a live virtual pet that reacts to your code's health and your activity.

---

## ⚡ Key Features

### 🛡️ Full Penetration Test Engine & Security
*   **OWASP Vulnerability Scanner:** Built-in detection for SQL Injection, Command Injection, XSS, SSRF, Path Traversal, and more.
*   **Hardcoded Secret Scanner:** Scans for over 20 types of exposed secrets, including AWS Keys, GitHub PATs, Stripe keys, and DB passwords.
*   **Automated Integration:** Automatically installs and runs `bandit` (Python deep scan), `semgrep` (Multi-language rules), and `safety` (Dependency CVEs).

### 🧠 Code Quality & Performance
*   **Speed & Complexity Analysis:** Calculates Cyclomatic Complexity score and estimates Big-O Time & Space complexity.
*   **Dead Code Detector:** Uses Python AST (and regex for other languages) to find unused functions and methods.
*   **Magic Number Detector:** Flags bare numeric literals that should be replaced with named constants.
*   **Python Auto-Fuzzer:** Automatically injects mock arguments into Python functions to test for crashes and infinite loops.

### 🛠️ Developer Utilities
*   **Advanced File Viewer & Line Targeting:** View massive files without terminal cut-offs. Seamlessly paginate through code or jump directly to specific lines for precise debugging.
*   **Interactive Git Command Center:** A scrollable menu of over 40 Git commands to check status, stage, commit, diff, and branch directly from the TUI.
*   **API Health Monitor:** Automatically detects HTTP/HTTPS URLs in your code and pings them to check connection status and latency.
*   **Diff Viewer:** Unified visual diff viewer to compare your working tree against Git `HEAD` or against another file.
*   **Multi-File Batch Checker:** Run universal syntax and connection checks across multiple selected files simultaneously.

### 🐶 The Virtual Companion
*   **Reactive Emotions:** The built-in companion face changes emotions based on your actions.
*   **State Management:** Becomes "happy" on success, "angry" or "sad" when finding issues, "error" when processes fail, and "tired" (Zzz) if you leave the terminal idle for 30 minutes.

---

## 🌐 Supported Languages

Cherm supports syntax checking, structure scanning, and analysis for a massive array of languages:
*   Python, JavaScript, TypeScript, Java, C, C++, Go, Rust, Ruby, PHP, Kotlin, Swift, Bash/Shell, PowerShell, Perl, R, HTML, CSS, JSON, YAML, Markdown, SQL.

---

## 🚀 Installation & Usage

**Prerequisites:** Python 3.x installed on your system.

1.  Clone the repository and navigate to the folder.
2.  Run the application:
    ```bash
    python cherm.py
    ```
    *(Alternatively, you can pass a specific file directly: `python cherm.py my_script.py`)*

---

## ⌨️ Keyboard Shortcuts

Cherm is designed for fast, mouse-free navigation.

| Key | Action |
| :--- | :--- |
| **Up / Down Arrow** | Navigate menus, files, or scroll through file/output lines |
| **PgUp / PgDn** | Scroll through large files and outputs quickly |
| **L** | Jump to a specific line number (in File Viewer) |
| **Enter** | Open file or run selected action |
| **Left / Backspace** | Go to parent directory |
| **Space** | Toggle multi-select (in multi-picker mode) |
| **B** | Toggle bookmark for the selected file |
| **?** | Open the Help panel |
| **Q / ESC** | Go back, cancel, or exit |

---

## 📁 File Browser & Bookmarks

*   **Bookmarks:** Press `B` on any file to bookmark it for quick access later. Bookmarks are saved persistently to `cherm_bookmarks.json`.
*   **Multi-Select:** Press `M` or `Space` to select multiple files to run batch security and syntax checks across your project.

---

## 🏗️ Development Process & Architecture

Cherm was built using a modern AI-assisted workflow ("vibe coding"). I acted as the system architect—designing the TUI layout, defining the security logic, and structuring the state management—while leveraging AI to accelerate the boilerplate syntax and implementation. All features were manually tested and verified for production-ready local use.
