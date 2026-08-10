<div align="center">
  <div style="background-color: #000000; padding: 25px 50px; border-radius: 8px; display: inline-block; margin-bottom: 10px;">
    <span style="color: #00FF00; font-family: monospace; font-size: 22px; font-weight: 900; letter-spacing: 3px; text-shadow: 0 0 5px #00FF00, 0 0 10px #00FF00;">( | - | [ - | ~ | \ / | ;</span>
  </div>
  <h1>Cherm</h1>
</div>

> **A terminal-based code inspection suite built for developers who want real analysis, fast — without loading a graphical IDE.**

Cherm is a powerful, entirely local static analysis and security toolkit designed to catch bugs, vulnerabilities, and messy code before you ever commit. It runs directly in your terminal using the `curses` library and features a live virtual companion that reacts to your code's health and your activity.

**Note on Development:** I am actively working on and updating this project. While the deepest analysis features (like the AST-based CrossCheckV200 and Bandit) are heavily optimized for Python right now, the application is built to support structural scanning, execution, and syntax checking for many other languages too.

---

## The Cherm Philosophy

Cherm is built to answer a specific frustration: *"I have a file I'm about to commit. Is it safe? Is it efficient? Does it have dead code?"* You can answer all of those questions in under 60 seconds without leaving your terminal workflow. 

**CRITICAL NOTE: No Artificial Intelligence.** 
Every analysis engine inside Cherm operates using **Abstract Syntax Tree (AST) parsing**, **Regular Expressions (Regex)**, or **rigid algorithmic heuristics**. Cherm is a static inspector—it does not use AI to read your code. Always apply your own developer judgment, as rigid rules can occasionally produce false positives or false negatives.

---

## Core Features

### Full Penetration Test & Security
*   **Full Security Pentest:** Automatically orchestrates `bandit` (Python deep scan), `semgrep` (Multi-language rules), and `safety` (Dependency CVEs) for a comprehensive sweep.
*   **Security Audit (OWASP):** A zero-dependency regex audit for critical web vulnerabilities like SQL Injection, Command Injection, XSS, and SSRF.
*   **Scan for Secrets:** Detects over 20 types of hardcoded API keys, passwords, and credentials (e.g., AWS Keys, GitHub PATs, Stripe keys) using structural patterns and Shannon Entropy analysis.

### Code Quality & Performance
*   **CrossCheckV200 Engine:** Automated function-level fuzz testing. It dynamically injects mock arguments into your Python functions to find edge-case crashes without writing a single test case.
*   **Speed & Complexity Analysis:** Calculates a Messiness Score and estimates Big-O Time & Space complexity via AST structural analysis, combined with a real runtime execution benchmark.
*   **Dead Code Detector:** Uses Python AST (and regex for other languages) to detect assigned-but-unused variables, unreachable logic, and uncalled functions.
*   **Magic Number Detector:** Flags bare numeric literals that lack domain context and should be extracted into named constants.

### Developer Utilities
*   **Shadow Copy Architecture:** *Your original files are never locked or corrupted.* Cherm silently duplicates your file into a temporary `%TEMP%` directory and runs all analysis tools on the copy.
*   **Interactive Git Command Center:** Stage files, restore changes, and write commit messages directly from the file browser without opening a separate terminal pane.
*   **API Health Monitor:** Extracts all HTTP/HTTPS URLs from your code and fires concurrent health checks to verify which endpoints are alive and responsive.
*   **Diff & Raw Viewers:** Review your working tree against Git `HEAD`, or use the integrated terminal pager to read files instantly.
*   **Multi-File Batch Checker:** Run universal syntax and connection checks across multiple selected files simultaneously.

### The Virtual Companion
Cherm features a reactive ASCII companion face in the header. It becomes "happy" on success, "angry" or "sad" when finding vulnerabilities, "error" when processes fail, and "tired" (Zzz) if you leave the terminal idle for 30 minutes.

---

## Supported Languages

Cherm supports syntax checking, structure scanning, and analysis for a massive array of languages:
**Python, JavaScript, TypeScript, Java, C, C++, Go, Rust, Ruby, PHP, Kotlin, Swift, Bash/Shell, PowerShell, Perl, R, HTML, CSS, JSON, YAML, Markdown, SQL**.

---

## Installation & Usage

### Option 1: Standalone Executable (Windows) - Easiest
No Python installation or terminal setup is required to run the standalone executable.

1. Navigate to the **Releases** section on the right side of this GitHub repository.
2. Download the `Cherm.zip` file attached to the latest release.
3. Extract the `.zip` file to your computer.
4. Double-click `cherm.exe` to run the application.
5. **Note for Windows Users:** Because this is an indie open-source project, Windows SmartScreen may flag the `.exe` as an unrecognized app. If you see a blue "Windows protected your PC" screen, simply click **More info** and then **Run anyway** to launch Cherm.

### Option 2: Run via Python (Development / IDE)
**Prerequisites:** Python 3.x installed on your system.

1. Clone the repository and navigate to the folder.
2. Run the application via your terminal or IDE:
   ```bash
   python cherm.py
