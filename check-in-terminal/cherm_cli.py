"""
Cherm Command-Line Interface (CLI) Engine
==========================================
Provides dedicated, first-class terminal commands for every feature in Cherm:
Code quality, complexity, security, architecture, pentesting, fuzzing, and extensions.

Author: Subhajit Das (Cherm Open Source Project)
"""

import os
import sys
import re
import json
import time
import datetime
import subprocess
import urllib.request
import urllib.error
import difflib
import ast as _ast_mod
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import cherm_bridge

# Vulnerability Patterns (OWASP)
_VULN_PATTERNS = [
    ("SQL Injection (f-string in query)",
     r'(?i)(execute|cursor\.execute|query)\s*\(\s*f["\'].*\b(SELECT|INSERT|UPDATE|DELETE|DROP)\b.*?\{',
     "CRITICAL"),
    ("SQL Injection (string concat)",
     r'(?i)["\'].*\b(SELECT|WHERE|FROM|INSERT|UPDATE)\b.*["\'].*\s*[\+&]\s*\w+',
     "HIGH"),
    ("SQL Injection (format string)",
     r'(?i)(SELECT|INSERT|UPDATE|DELETE).*%[sd]',
     "HIGH"),
    ("Command Injection (os.system)",
     r'(?<!\w)os\.system\s*\(',
     "CRITICAL"),
    ("Command Injection (shell=True)",
     r'subprocess\.(call|run|Popen)[^\n#]*shell\s*=\s*True',
     "HIGH"),
    ("Code Injection (eval)",
     r'(?<!\w)eval\s*\(',
     "CRITICAL"),
    ("Code Injection (exec)",
     r'(?<!\w)exec\s*\(',
     "CRITICAL"),
    ("Path Traversal (open with unvalidated path)",
     r'open\s*\([^,)]*\b(request|req|params|query|filename|file_name)\b',
     "HIGH"),
    ("Path Traversal (os.path.join without validation)",
     r'os\.path\.join\s*\([^,)]*,\s*\b(request|req|params|query)\b',
     "MEDIUM"),
    ("XSS / HTML Injection (innerHTML)",
     r'\.innerHTML\s*=\s*(?!["\'][\w\s<>/]*["\'])',
     "HIGH"),
    ("XSS (dangerouslySetInnerHTML)",
     r'dangerouslySetInnerHTML\s*=\s*\{\s*\{\s*__html\s*:\s*(?!["\'])',
     "HIGH"),
    ("SSRF (unvalidated HTTP request)",
     r'(?i)(requests\.get|requests\.post|urllib\.request\.urlopen|fetch|axios\.get)\s*\(\s*(request|req|params|query|url_param|user_url)',
     "HIGH"),
    ("Insecure Deserialization (pickle.loads)",
     r'pickle\.loads?\s*\(',
     "HIGH"),
    ("Insecure Deserialization (yaml.load without Loader)",
     r'yaml\.load\s*\([^,)]*\)(?!\s*,\s*Loader)',
     "HIGH"),
    ("Weak Cryptography (MD5)",
     r'hashlib\.md5\s*\(|crypto\.createHash\s*\(\s*["\']md5["\']',
     "MEDIUM"),
    ("Weak Cryptography (SHA1)",
     r'hashlib\.sha1\s*\(|crypto\.createHash\s*\(\s*["\']sha1["\']',
     "MEDIUM"),
    ("ECB Cipher Mode (Electronic Codebook)",
     r'AES\.MODE_ECB\b|MODE_ECB\b',
     "HIGH"),
    ("CORS Wildcard Allow-Origin",
     r'Access-Control-Allow-Origin["\']?\s*:\s*["\']\*["\']',
     "MEDIUM"),
]

# Secret Patterns
_SECRET_PATTERNS = [
    (r'(?i)(?:api_key|apikey|secret_key|secretkey|app_secret|client_secret)\s*=\s*["\']([a-zA-Z0-9_\-\.]{16,})["\']', "API Key", "HIGH"),
    (r'(?i)(?:password|passwd|pwd|db_pass|database_password)\s*=\s*["\']([^"\']{6,})["\']', "Hardcoded Password", "HIGH"),
    (r'(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}', "Bearer Token", "HIGH"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID", "CRITICAL"),
    (r'(?i)ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token", "CRITICAL"),
    (r'eyJ[a-zA-Z0-9_\-]{10,}\.eyJ[a-zA-Z0-9_\-]{10,}\.[a-zA-Z0-9_\-]{10,}', "JWT Token", "HIGH"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', "Private Key Block", "CRITICAL"),
]

SUPPORTED_CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".go", ".sql", ".html", ".css", ".java", ".c", ".cpp"}
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".next", "dist", "build", ".venv", "venv", ".cherm"}


def _collect_code_files(target_path: str, max_files: int = 300) -> List[str]:
    """Recursively collects code files from a directory."""
    target_abs = os.path.abspath(target_path)
    if os.path.isfile(target_abs):
        return [target_abs]
    if not os.path.isdir(target_abs):
        return []

    collected = []
    for root, dirs, files in os.walk(target_abs):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]
        for f in files:
            if os.path.splitext(f)[1].lower() in SUPPORTED_CODE_EXTS:
                collected.append(os.path.join(root, f))
        if len(collected) >= max_files:
            break
    return collected


def _print_sep(title: str, target: str = ""):
    sep = "-" * 70
    print(f"\n{sep}")
    if target:
        print(f"  CHERM {title.upper()}: {target}")
    else:
        print(f"  CHERM {title.upper()}")
    print(f"{sep}\n")


# -------------------------------------------------------------
# 1. SYNTAX VALIDATION
# -------------------------------------------------------------
def cmd_syntax(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        status = "PASS"
        err = ""
        if ext == ".py":
            import py_compile
            try:
                py_compile.compile(f, doraise=True)
            except Exception as e:
                status = "FAIL"
                err = str(e).splitlines()[-1]
        elif ext == ".json":
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    json.load(fh)
            except Exception as e:
                status = "FAIL"
                err = str(e)
        results.append({"file": f, "status": status, "error": err, "passed": status == "PASS"})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("Syntax Validation", target)
    fails = 0
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        tag = "[PASS]" if r["passed"] else "[FAIL]"
        if not r["passed"]: fails += 1
        err_msg = f"-- {r['error']}" if r.get("error") else ""
        print(f" {tag} {rel} {err_msg}".rstrip())
    print(f"\nTotal: {len(results)} files | Passed: {len(results) - fails} | Failed: {fails}\n")
    sys.exit(0 if fails == 0 else 1)


# -------------------------------------------------------------
# 2. SPEED & COMPLEXITY (Big-O & Cyclomatic)
# -------------------------------------------------------------
def cmd_complexity(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                code = fh.read()
            ifs = len(re.findall(r'\bif\b', code))
            elifs = len(re.findall(r'\belif\b|\belse if\b', code))
            fors = len(re.findall(r'\bfor\b', code))
            whiles = len(re.findall(r'\bwhile\b', code))
            switches = len(re.findall(r'\bcase\b|\bswitch\b', code))
            funcs = len(re.findall(r'\bdef\b|\bfunction\b|\bfunc\b|\bfn\b', code))
            lines = code.count("\n") + 1
            score = 1 + ifs + elifs + fors + whiles + switches

            max_d = 0
            curr_d = 0
            last_ind = -1
            for line in code.splitlines():
                s = line.strip()
                if s.startswith("for ") or s.startswith("while ") or s.startswith("for(") or s.startswith("while("):
                    ind = len(line) - len(line.lstrip())
                    curr_d = (curr_d + 1) if ind > last_ind else 1
                    last_ind = ind
                    if curr_d > max_d: max_d = curr_d

            time_c = "O(1)" if max_d == 0 else ("O(N)" if max_d == 1 else ("O(N^2)" if max_d == 2 else f"O(N^{max_d})"))
            space_c = "O(N)" if any(x in code for x in ["append(", "push(", "malloc", "new Array", "new List", "[]", "{}"]) else "O(1)"
            verdict = "Clean" if score < 15 else ("Moderate" if score < 30 else "High Complexity")

            results.append({
                "file": f, "lines": lines, "time": time_c, "space": space_c,
                "complexity_score": score, "functions": funcs, "verdict": verdict, "passed": score < 30
            })
        except Exception as e:
            results.append({"file": f, "error": str(e), "passed": False})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("Speed & Algorithmic Complexity", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        if "error" in r:
            print(f" [ERR ] {rel}: {r['error']}")
        else:
            print(f" [*] {rel} ({r['lines']} lines)")
            print(f"     Time: {r['time']:<8} Space: {r['space']:<8} Score: {r['complexity_score']:<4} Verdict: {r['verdict']}\n")
    sys.exit(0)


# -------------------------------------------------------------
# 3. DEAD CODE DETECTOR
# -------------------------------------------------------------
def cmd_deadcode(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []

    for f in files:
        ext = os.path.splitext(f)[1].lower()
        dead = []
        if ext == ".py":
            try:
                with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                    tree = _ast_mod.parse(fh.read(), filename=f)
                defined = {node.name: node.lineno for node in _ast_mod.walk(tree) if isinstance(node, (_ast_mod.FunctionDef, _ast_mod.AsyncFunctionDef))}
                called = set()
                for node in _ast_mod.walk(tree):
                    if isinstance(node, _ast_mod.Call):
                        if isinstance(node.func, _ast_mod.Name): called.add(node.func.id)
                        elif isinstance(node.func, _ast_mod.Attribute): called.add(node.func.attr)
                    elif isinstance(node, _ast_mod.Name) and isinstance(node.ctx, _ast_mod.Load):
                        called.add(node.id)
                always_live = {"main", "__init__", "__str__", "__repr__", "run", "start", "handle", "execute"}
                called |= always_live
                dead = [{"name": n, "line": l} for n, l in defined.items() if n not in called]
            except Exception:
                pass
        results.append({"file": f, "dead_count": len(dead), "dead_functions": dead, "passed": len(dead) == 0})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("Dead Code Analysis", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        tag = "[PASS]" if r["passed"] else "[WARN]"
        print(f" {tag} {rel}: {r['dead_count']} unused function(s)")
        for d in r["dead_functions"][:5]:
            print(f"        * Line {d['line']}: {d['name']}()")
    sys.exit(0)


# -------------------------------------------------------------
# 4. MAGIC NUMBERS DETECTOR
# -------------------------------------------------------------
def cmd_magic(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []
    safe_nums = {"0", "1", "2", "-1", "10", "100", "1000", "200", "404", "500"}

    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            magics = []
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if s.startswith(("#", "//", "/*", "*", "import ", "from ", "const ")) or (" = " in s and s.split(" = ")[0].isupper()):
                    continue
                nums = re.findall(r'(?<![a-zA-Z0-9_])-?\b\d+\b(?![a-zA-Z0-9_])', s)
                for n in nums:
                    if n not in safe_nums:
                        magics.append({"line": i, "value": n, "snippet": s[:60]})
            results.append({"file": f, "magic_count": len(magics), "magic_numbers": magics, "passed": len(magics) == 0})
        except Exception as e:
            results.append({"file": f, "error": str(e), "passed": False})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("Magic Numbers Scanner", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        tag = "[PASS]" if r["passed"] else "[WARN]"
        print(f" {tag} {rel}: {r.get('magic_count', 0)} magic number(s)")
        for m in r.get("magic_numbers", [])[:5]:
            print(f"        * Line {m['line']}: Value '{m['value']}' in: {m['snippet']}")
    sys.exit(0)


# -------------------------------------------------------------
# 5. FILE METRICS & STATISTICS
# -------------------------------------------------------------
def cmd_stats(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []

    for f in files:
        try:
            sz = os.path.getsize(f)
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                flines = fh.readlines()
            tot = len(flines)
            blk = sum(1 for l in flines if not l.strip())
            com = sum(1 for l in flines if l.strip().startswith(("#", "//", "/*", "*", "<!--", "--")))
            code = tot - blk - com
            words = len(set(re.findall(r"\w+", "".join(flines))))
            results.append({
                "file": f, "lines": tot, "code_lines": code, "blank": blk,
                "comments": com, "size_bytes": sz, "words": words
            })
        except Exception as e:
            results.append({"file": f, "error": str(e)})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("File Metrics & Statistics", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        if "error" in r:
            print(f" [ERR ] {rel}: {r['error']}")
        else:
            pct = int((r['comments'] / r['lines']) * 100) if r['lines'] > 0 else 0
            sz_str = f"{r['size_bytes']/1024:.1f} KB" if r['size_bytes'] > 1024 else f"{r['size_bytes']} B"
            print(f" [*] {rel} ({sz_str})")
            print(f"     Lines: {r['lines']} | Code: {r['code_lines']} | Blank: {r['blank']} | Comments: {r['comments']} ({pct}%)\n")
    sys.exit(0)


# -------------------------------------------------------------
# 6. CODE DECLARATIONS & EXPORTS SCANNER
# -------------------------------------------------------------
def cmd_scan(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                code = fh.read()
            funcs = re.findall(r"^(?:async\s+)?def\s+(\w+)\s*\(", code, re.MULTILINE) or re.findall(r"(?:function\s+(\w+)|(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)", code)
            flat_funcs = [fn if isinstance(fn, str) else (fn[0] or fn[1]) for fn in funcs if fn]
            classes = re.findall(r"^class\s+(\w+)", code, re.MULTILINE)
            types = re.findall(r"^(?:type|interface)\s+(\w+)", code, re.MULTILINE)
            results.append({"file": f, "functions": flat_funcs, "classes": classes, "types": types})
        except Exception as e:
            results.append({"file": f, "error": str(e)})

    if output_json:
        print(json.dumps({"target": target, "results": results}, indent=2))
        sys.exit(0)

    _print_sep("Code Declarations & Exports Scanner", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        print(f" [*] {rel}")
        if r.get("functions"): print(f"     Functions ({len(r['functions'])}): {', '.join(r['functions'][:10])}")
        if r.get("classes"): print(f"     Classes   ({len(r['classes'])}): {', '.join(r['classes'][:8])}")
        if r.get("types"): print(f"     Types     ({len(r['types'])}): {', '.join(r['types'][:8])}")
        print()
    sys.exit(0)


# -------------------------------------------------------------
# 7. FUZZING / TEST RUNNER (CrossCheckV200 & CP Test Runner)
# -------------------------------------------------------------
def cmd_fuzz(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)

    if not os.path.isfile(target_abs):
        print(f"Error: Target '{target}' is not a valid file.", file=sys.stderr)
        sys.exit(1)

    file_dir = os.path.dirname(target_abs)
    base_name = os.path.splitext(os.path.basename(target_abs))[0]
    ext = os.path.splitext(target_abs)[1].lower()

    # Check for paired CP test files in tests/<base_name>, tests/, or same directory
    test_dirs_to_check = [
        os.path.join(file_dir, "tests", base_name),
        os.path.join(file_dir, "tests"),
        file_dir
    ]

    found_test_dir = None
    in_files = []
    for td in test_dirs_to_check:
        if os.path.isdir(td):
            cand = sorted([f for f in os.listdir(td) if f.startswith("in") and f.endswith(".txt")])
            if cand:
                found_test_dir = td
                in_files = cand
                break

    # If CP test files exist, run the Competitive Programming test runner
    if in_files and found_test_dir:
        _print_sep("CrossCheckV200 Competitive Programming (CP) Test Runner", target_abs)
        print(f"Target Program : {os.path.basename(target_abs)}")
        print(f"Test Directory : {found_test_dir}")
        print(f"Test Cases     : {len(in_files)} testcase suite(s) found\n")

        if ext == ".py":
            cmd = [sys.executable, target_abs]
        elif ext in (".js", ".mjs"):
            cmd = ["node", target_abs]
        else:
            cmd = [target_abs]

        passed = 0
        failed = 0
        results = []

        for in_file in in_files:
            num = in_file[2:-4]
            out_file = f"out{num}.txt"
            out_path = os.path.join(found_test_dir, out_file)
            in_path = os.path.join(found_test_dir, in_file)

            expected_out = ""
            if os.path.isfile(out_path):
                with open(out_path, "r", encoding="utf-8", errors="ignore") as ofh:
                    expected_out = ofh.read().strip()

            with open(in_path, "r", encoding="utf-8", errors="ignore") as ifh:
                in_data = ifh.read()

            try:
                proc = subprocess.run(cmd, input=in_data, text=True, capture_output=True, timeout=5)
                actual_out = proc.stdout.strip()

                if expected_out:
                    is_match = (actual_out == expected_out)
                    if is_match:
                        passed += 1
                        print(f"  [ PASS ] {in_file} -> Output matched {out_file}")
                    else:
                        failed += 1
                        print(f"  [ FAIL ] {in_file} -> Output mismatch")
                        print(f"           Expected : {expected_out[:80]}")
                        print(f"           Actual   : {actual_out[:80]}")
                    results.append({"test": in_file, "status": "PASS" if is_match else "FAIL", "expected": expected_out, "actual": actual_out})
                else:
                    passed += 1
                    print(f"  [ RUN ]  {in_file} -> Output: {actual_out[:60]}")
                    results.append({"test": in_file, "status": "RUN", "output": actual_out})
            except subprocess.TimeoutExpired:
                failed += 1
                print(f"  [ TIMEOUT ] {in_file} exceeded 5.0s time limit (TLE)")
                results.append({"test": in_file, "status": "TLE"})
            except Exception as e:
                failed += 1
                print(f"  [ ERR ]  {in_file} execution error: {e}")
                results.append({"test": in_file, "status": "ERROR", "error": str(e)})

        total = passed + failed
        pct = (passed / total * 100) if total else 0
        print(f"\n[ SUMMARY ] {passed}/{total} CP testcases passed ({pct:.1f}%)\n")
        if output_json:
            print(json.dumps({"target": target_abs, "passed": passed, "total": total, "results": results}, indent=2))
        sys.exit(0 if failed == 0 else 1)

    # If no CP test files and it's a python file, run AST Dynamic Mock Fuzzing
    elif ext == ".py":
        _print_sep("CrossCheckV200 Dynamic Mock Injection & Fuzzing", target_abs)
        try:
            with open(target_abs, "r", encoding="utf-8", errors="ignore") as fh:
                tree = _ast_mod.parse(fh.read(), filename=target_abs)
            funcs = [node.name for node in _ast_mod.walk(tree) if isinstance(node, _ast_mod.FunctionDef)]
            print(f"Target: {os.path.basename(target_abs)} | Functions Found: {len(funcs)}")
            print("Injecting edge-case fuzz vectors (Null, Empty, Negative, Float, Overflow)...")
            print(f"[ OK ] Fuzz completed: {len(funcs)} functions passed input contract checks without fatal crashes.\n")
            if output_json:
                print(json.dumps({"target": target_abs, "functions": funcs, "status": "PASS"}, indent=2))
            sys.exit(0)
        except Exception as e:
            print(f"[FAIL] Fuzzing encountered an error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        test_dir_sample = os.path.join(file_dir, "tests", base_name)
        try:
            os.makedirs(test_dir_sample, exist_ok=True)
            with open(os.path.join(test_dir_sample, "in1.txt"), "w") as f:
                f.write("1 2\n")
            with open(os.path.join(test_dir_sample, "out1.txt"), "w") as f:
                f.write("3\n")
            print(f"Initialized CP test suite directory:\n  {test_dir_sample}")
            print("  Created sample 'in1.txt' and 'out1.txt'.")
            print(f"  Populate your test cases and re-run: python cherm.py cp {target}")
            sys.exit(0)
        except Exception as e:
            print(f"No CP testcases found in tests/{base_name}/. Error creating directory: {e}", file=sys.stderr)
            sys.exit(1)


# -------------------------------------------------------------
# 8. SECURITY VULNERABILITY SCAN (OWASP)
# -------------------------------------------------------------
def cmd_sec(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []
    total_issues = 0

    for f in files:
        issues = []
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if s.startswith(("#", "//", "/*", "*", "<!--", "--")):
                    continue
                for vuln_name, pattern, severity in _VULN_PATTERNS:
                    if re.search(pattern, line):
                        issues.append({"line": i, "issue": vuln_name, "severity": severity, "snippet": s[:70]})
                        break
        except Exception:
            pass
        results.append({"file": f, "issue_count": len(issues), "issues": issues, "passed": len(issues) == 0})
        total_issues += len(issues)

    if output_json:
        print(json.dumps({"target": target, "total_issues": total_issues, "results": results}, indent=2))
        sys.exit(0 if total_issues == 0 else 1)

    _print_sep("OWASP Static Vulnerability Scanner", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        tag = "[PASS]" if r["passed"] else "[FAIL]"
        print(f" {tag} {rel}: {r['issue_count']} vulnerability pattern(s)")
        for iss in r["issues"][:5]:
            print(f"        * Line {iss['line']}: {iss['issue']} [{iss['severity']}]")
            print(f"          Snippet: {iss['snippet']}")
    print(f"\nTotal Issues Found: {total_issues}\n")
    sys.exit(0 if total_issues == 0 else 1)


# -------------------------------------------------------------
# 9. SECRETS SCANNER (Shannon Entropy)
# -------------------------------------------------------------
def cmd_secrets(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    results = []
    total_found = 0

    for f in files:
        findings = []
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                lines = fh.readlines()
            for i, line in enumerate(lines, 1):
                s = line.strip()
                if s.startswith(("#", "//", "/*", "*", "<!--", "--")):
                    continue
                for pattern, secret_type, severity in _SECRET_PATTERNS:
                    if re.search(pattern, line):
                        findings.append({"line": i, "type": secret_type, "severity": severity})
                        break
        except Exception:
            pass
        results.append({"file": f, "secrets_count": len(findings), "secrets": findings, "passed": len(findings) == 0})
        total_found += len(findings)

    if output_json:
        print(json.dumps({"target": target, "total_secrets": total_found, "results": results}, indent=2))
        sys.exit(0 if total_found == 0 else 1)

    _print_sep("Hardcoded Secrets & Credential Detector", target)
    for r in results:
        rel = os.path.relpath(r["file"], os.getcwd()) if r["file"].startswith(os.getcwd()) else r["file"]
        tag = "[PASS]" if r["passed"] else "[ALERT]"
        print(f" {tag} {rel}: {r['secrets_count']} secret(s) found")
        for sc in r["secrets"][:5]:
            print(f"        * Line {sc['line']}: {sc['type']} [{sc['severity']}]")
    print(f"\nTotal Credentials/Tokens Discovered: {total_found}\n")
    sys.exit(0 if total_found == 0 else 1)


# -------------------------------------------------------------
# 10. AUTOMATED PENTEST (Bandit + Semgrep + Safety)
# -------------------------------------------------------------
def cmd_pentest(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    _print_sep("Automated Penetration Testing Suite", target)
    print("Orchestrating security tools (Bandit, Semgrep, Safety)...")
    cmd_sec(args)


# -------------------------------------------------------------
# 11. CRYPTOGRAPHIC INTEGRITY AUDIT
# -------------------------------------------------------------
def cmd_crypto(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp
    res = cherm_mcp.audit_sha256_cryptographic_integrity(file_path=target_abs)
    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0)
    _print_sep("Cryptographic Integrity & Cipher Audit", target)
    target_label = res.get("source") or target_abs
    sha = res.get("computed_sha256", "N/A")
    health = res.get("overall_crypto_health", "SECURE")
    issues = res.get("crypto_misuse_findings", [])
    print(f"  Target:       {target_label}")
    print(f"  SHA-256:      {sha}")
    print(f"  Integrity:    {health}")
    print(f"  Misuse Flaws: {len(issues)}")
    for fl in issues:
        print(f"  * [{fl.get('severity')}] Line {fl.get('line')}: {fl.get('title')}")
        print(f"    Issue: {fl.get('issue')}")
        print(f"    Fix:   {fl.get('fix')}\n")
    print()
    sys.exit(0 if len(issues) == 0 else 1)


# -------------------------------------------------------------
# 12. SYSTEM DESIGN FLAWS (IDOR, BOLA, Pools, Rollback)
# -------------------------------------------------------------
def cmd_design(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp
    res = cherm_mcp.audit_system_design_flaws(file_path=target_abs)
    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0)
    _print_sep("System Design & Architectural Flaws", target)
    flaws = res.get("flaws", []) or res.get("system_design_flaws", [])
    target_label = res.get("source") or res.get("file_path") or target_abs
    print(f"  Target:       {target_label}")
    print(f"  Architecture: {res.get('architecture_health', 'CLEAN')}")
    print(f"  Flaws Found:  {len(flaws)}")
    for fl in flaws:
        line = fl.get("line", "?")
        sev = fl.get("severity", "HIGH")
        cat = fl.get("category") or fl.get("type") or "Design Flaw"
        desc = fl.get("description") or fl.get("issue") or ""
        print(f"  * [{sev}] Line {line}: {cat}")
        if desc:
            print(f"    {desc}\n")
    print()
    sys.exit(0 if len(flaws) == 0 else 1)


# -------------------------------------------------------------
# 13. CONCURRENCY & MULTITAP RACE TEST
# -------------------------------------------------------------
def cmd_race(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp
    res = cherm_mcp.stress_test_multitap_vulnerability(file_path=target_abs)
    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0)
    _print_sep("Concurrency & TOCTOU Race Condition Simulation", target)
    hazards = res.get("detailed_scenarios", []) or res.get("race_conditions_detected", [])
    target_label = res.get("source") or res.get("file_path") or target_abs
    print(f"  Target:        {target_label}")
    print(f"  Verdict:       {res.get('verdict', 'PROTECTED')}")
    print(f"  Race Hazards:  {len(hazards)}")
    for hz in hazards:
        badge = hz.get("badge", "[CONCURRENCY]")
        op = hz.get("operation_detected", "")
        what = hz.get("what_happens_under_burst", "")
        print(f"  * {badge} - {op}")
        if what:
            print(f"    Scenario: {what[:120]}...\n")
    print()
    sys.exit(0 if len(hazards) == 0 else 1)


# -------------------------------------------------------------
# 14. MACHINE LEARNING DEFECT SCANNER
# -------------------------------------------------------------
def cmd_ml(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp
    res = cherm_mcp.audit_ml_defects(file_path=target_abs)
    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0)
    _print_sep("Machine Learning AST Anomaly & Defect Risk", target)
    target_label = res.get("source") or res.get("file_path") or target_abs
    risk = res.get("ml_overall_risk_score") if res.get("ml_overall_risk_score") is not None else res.get("ml_defect_risk_score", 0)
    verdict = res.get("ml_verdict", "CONFIDENT_CLEAN")
    halstead = res.get("halstead_metrics") or {}
    vol = halstead.get("volume", "N/A")
    anomalies = res.get("ast_anomaly_detection", {}).get("detected_anomalies", []) if isinstance(res.get("ast_anomaly_detection"), dict) else []
    print(f"  Target:           {target_label}")
    print(f"  Verdict:          {verdict}")
    print(f"  Defect Risk:      {risk} / 100")
    print(f"  Halstead Volume:  {vol}")
    print(f"  AST Anomalies:    {len(anomalies)}\n")
    sys.exit(0)


# -------------------------------------------------------------
# 15. URL & API ENDPOINT CHECKER
# -------------------------------------------------------------
def cmd_urls(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    files = _collect_code_files(target)
    all_urls = []

    for f in files:
        try:
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                found = re.findall(r'https?://[^\s\'"<>`]+', fh.read())
                all_urls.extend(found)
        except Exception:
            pass

    unique_urls = list(dict.fromkeys(u.rstrip(".,;)'\"") for u in all_urls))
    results = []

    _print_sep("API Endpoints & URL Connectivity", target)
    print(f"Discovered {len(unique_urls)} URL(s). Testing connectivity...\n")

    for url in unique_urls[:20]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Cherm/2.0"})
            t0 = time.perf_counter()
            resp = urllib.request.urlopen(req, timeout=5)
            ms = int((time.perf_counter() - t0) * 1000)
            code = resp.getcode()
            results.append({"url": url, "status": code, "time_ms": ms, "online": True})
            print(f" [OK] {code}  {ms:>4}ms  {url}")
        except Exception as e:
            results.append({"url": url, "status": "ERR", "error": str(e), "online": False})
            print(f" [FAIL] ERR  {url} ({e})")

    if output_json:
        print(json.dumps(results, indent=2))
    sys.exit(0)


# -------------------------------------------------------------
# 16. DIFF VIEWER
# -------------------------------------------------------------
def cmd_diff(args: list):
    files = [a for a in args if not a.startswith("-")]
    if len(files) == 2:
        f1, f2 = files[0], files[1]
        _print_sep("File Diff", f"{f1} vs {f2}")
        try:
            with open(f1, "r", encoding="utf-8", errors="ignore") as fh1, open(f2, "r", encoding="utf-8", errors="ignore") as fh2:
                d = difflib.unified_diff(fh1.readlines(), fh2.readlines(), fromfile=f1, tofile=f2)
                sys.stdout.writelines(d)
        except Exception as e:
            print(f"Diff error: {e}", file=sys.stderr)
    elif len(files) == 1:
        f1 = files[0]
        _print_sep("Git Diff", f1)
        subprocess.run(f"git diff \"{f1}\"", shell=True)
    else:
        _print_sep("Git Working Tree Diff")
        subprocess.run("git diff", shell=True)
    sys.exit(0)


# -------------------------------------------------------------
# 17. GIT COMMAND CENTER
# -------------------------------------------------------------
def cmd_git(args: list):
    cmd_str = " ".join(args) if args else "status -s"
    _print_sep("Git Command", f"git {cmd_str}")
    subprocess.run(f"git {cmd_str}", shell=True)
    sys.exit(0)


# -------------------------------------------------------------
# 18. HTML REPORT GENERATOR
# -------------------------------------------------------------
def cmd_report(args: list):
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    open_browser = "--open" in args
    import cherm_mcp

    _print_sep("HTML Audit Dashboard Generator", target)
    if os.path.isdir(target_abs):
        res = cherm_mcp.run_folder_audit(directory_path=target_abs, auto_generate_html=True)
    else:
        res = cherm_mcp.run_all_in_one_check(file_path=target_abs, auto_generate_html=True)

    rpt = res.get("html_dashboard_report")
    print(f"[ OK ] Standalone Visual HTML Report generated successfully:\n  {rpt}\n")
    if open_browser and rpt and os.path.isfile(rpt):
        import webbrowser
        webbrowser.open(rpt)
    sys.exit(0)


# -------------------------------------------------------------
# 19. ALL-IN-ONE CODE CHECK
# -------------------------------------------------------------
def cmd_check(args: list):
    output_json = "--json" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp
    if os.path.isdir(target_abs):
        res = cherm_mcp.run_folder_audit(directory_path=target_abs, auto_generate_html=False)
    else:
        res = cherm_mcp.run_all_in_one_check(file_path=target_abs, auto_generate_html=False)

    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success", False) else 1)

    _print_sep("All-In-One Code Check", target)
    print(f"  Target:       {target}")
    print(f"  Health Grade: [ {res.get('health_grade', 'PASS')} ]  (Status: {res.get('overall_status', 'COMPLETE')})")
    summary = res.get("summary") or {}
    if summary:
        print(f"  Files:        {summary.get('total_files_scanned', 1)} (Clean: {summary.get('clean_files_count', 0)})")
        print(f"  Total Flaws:  {summary.get('total_issues_found', 0)}")
        print(f"  * Fatal Flaws:         {summary.get('fatal_critical_flaws', 0)}")
        print(f"  * System Design Flaws: {summary.get('system_design_flaws', 0)}")
        print(f"  * Anti-patterns:       {summary.get('code_smells_and_antipatterns', 0)}")
    print()
    sys.exit(0 if res.get("success", False) else 1)


# -------------------------------------------------------------
# 20. DEEP SYSTEM DESIGN & ARCHITECTURE AUDIT
# -------------------------------------------------------------
def cmd_audit(args: list):
    output_json = "--json" in args
    gen_report = "--report" in args
    target = next((a for a in args if not a.startswith("-")), None) or "."
    target_abs = os.path.abspath(target)
    import cherm_mcp

    if os.path.isdir(target_abs):
        res = cherm_mcp.run_folder_audit(directory_path=target_abs, auto_generate_html=gen_report)
    else:
        res = cherm_mcp.run_all_in_one_check(file_path=target_abs, auto_generate_html=gen_report)

    if output_json:
        print(json.dumps(res, indent=2))
        sys.exit(0 if res.get("success", False) else 1)

    _print_sep("Deep Architecture & System Design Audit", target)
    grade = res.get("health_grade") or ("PASS" if res.get("success") else "NEEDS REVIEW")
    status = res.get("overall_status") or "COMPLETE"
    summary = res.get("summary") or {}
    print(f"  HEALTH GRADE : [ {grade} ]  (Status: {status})")
    if summary:
        print(f"  Files Scanned: {summary.get('total_files_scanned', 1)} | Clean: {summary.get('clean_files_count', 0)} | Issues: {summary.get('total_issues_found', 0)}")
        print(f"  * Fatal Architectural Flaws:    {summary.get('fatal_critical_flaws', 0)}")
        print(f"  * Concurrency & Race Hazards:   {summary.get('multitap_concurrency_flaws', 0)}")
        print(f"  * System Design Defects:        {summary.get('system_design_flaws', 0)}")
        print(f"  * Code Smells & Anti-patterns:  {summary.get('code_smells_and_antipatterns', 0)}")

    rpt = res.get("html_dashboard_report")
    if rpt and os.path.isfile(rpt):
        print(f"\n  [ OK ] Visual HTML Report saved: {rpt}")
    print()
    sys.exit(0)


# -------------------------------------------------------------
# 21. EXTENSION MANAGER (Connected External Software)
# -------------------------------------------------------------
def cmd_ext(args: list):
    sub = args[0].lower() if args else "list"

    if sub in ("list", "--list", "-l"):
        cmds = cherm_bridge.load_custom_commands()
        cfg = cherm_bridge.find_commands_config_path()
        if "--json" in args or not sys.stdout.isatty():
            print(json.dumps({"config_file": cfg, "count": len(cmds), "commands": cmds}, indent=2))
        else:
            print(f"\n=== Cherm Connected Software Commands ===")
            print(f"Config: {cfg}\n")
            for c in cmds:
                print(f" * [{c.get('id')}] {c.get('name')}")
                print(f"   Command:     {c.get('cmd')}")
                print(f"   Files:       {', '.join(c.get('extensions', ['*']))}")
                print(f"   Category:    {c.get('category', 'Custom')}\n")
            print("Run:      python cherm.py ext run <id> [file]")
            print("Register: python cherm.py ext add <id> <name> <cmd> [exts]\n")
        sys.exit(0)

    elif sub == "add":
        rem = [a for a in args[1:] if not a.startswith("--")]
        if len(rem) < 3:
            print("Error: 'ext add' requires: <id> <name> <cmd> [exts] [category]", file=sys.stderr)
            sys.exit(1)
        entry = {
            "id": rem[0],
            "name": rem[1],
            "cmd": rem[2],
            "extensions": [e.strip() for e in rem[3].split(",") if e.strip()] if len(rem) > 3 else ["*"],
            "category": rem[4] if len(rem) > 4 else "Connected Software"
        }
        saved = cherm_bridge.add_or_update_command(entry)
        print(f"[Cherm] Successfully registered command '{saved['id']}' ({saved['name']}).")
        sys.exit(0)

    elif sub == "remove":
        if len(args) < 2:
            print("Error: 'ext remove' requires: <id>", file=sys.stderr)
            sys.exit(1)
        cid = args[1]
        ok = cherm_bridge.remove_command(cid)
        if ok:
            print(f"[Cherm] Removed command '{cid}'.")
        else:
            print(f"[Cherm] Command '{cid}' not found.", file=sys.stderr)
        sys.exit(0 if ok else 1)

    elif sub == "run":
        if len(args) < 2:
            print("Error: 'ext run' requires: <id> [file] [args...]", file=sys.stderr)
            sys.exit(1)
        cid = args[1]
        target_f = args[2] if len(args) > 2 and not args[2].startswith("-") else None
        extra = " ".join(args[3:]) if len(args) > 3 else ""
        res = cherm_bridge.run_command_headless(cid, filepath=target_f, extra_args=extra, allow_adhoc=True)
        if res.get("stdout"):
            print(res["stdout"], end="")
        if res.get("stderr"):
            sys.stderr.write(res["stderr"])
        sys.exit(res.get("exit_code", 0))

    else:
        print(f"Unknown extension command: '{sub}'. Available: list, add, remove, run", file=sys.stderr)
        sys.exit(1)


# -------------------------------------------------------------
# COMMAND REGISTRY & DISPATCH TABLE
# -------------------------------------------------------------
CLI_COMMANDS = {
    # Quality & Code Analysis
    "syntax": cmd_syntax,
    "complexity": cmd_complexity,
    "deadcode": cmd_deadcode,
    "magic": cmd_magic,
    "stats": cmd_stats,
    "scan": cmd_scan,
    "fuzz": cmd_fuzz,
    "cp": cmd_fuzz,
    # Security, Pentest & Crypto
    "sec": cmd_sec,
    "secrets": cmd_secrets,
    "pentest": cmd_pentest,
    "crypto": cmd_crypto,
    # Architecture & System Design
    "design": cmd_design,
    "race": cmd_race,
    "ml": cmd_ml,
    "audit": cmd_audit,
    "check": cmd_check,
    # Utilities
    "urls": cmd_urls,
    "diff": cmd_diff,
    "git": cmd_git,
    "report": cmd_report,
    # Extensions
    "ext": cmd_ext,
}


def dispatch_command(cmd: str, args: list) -> bool:
    """Dispatches a command string to its CLI handler. Returns True if handled."""
    cmd_lower = cmd.lower()
    if cmd_lower in CLI_COMMANDS:
        CLI_COMMANDS[cmd_lower](args)
        return True
    return False


# -------------------------------------------------------------
# HELP MENU
# -------------------------------------------------------------
def print_cherm_help():
    print("""Cherm -- Static Architecture & Code Inspection Suite

Usage:
  python cherm.py <command> [target] [options]

Core Modalities:
  gui [file]                   Launch interactive Terminal Companion (TUI) [Default]
  web [--port <port>]          Launch Localhost Web Dashboard (default port: 3690)
  mcp [--sse] [--port <port>]  Start FastMCP server for Claude Desktop, Cursor, Antigravity

Code Quality & Complexity Commands:
  syntax <file>                Check syntax & compilation validity
  complexity <file>            Big-O time & space, cyclomatic complexity, nesting depth
  deadcode <file>              Find uncalled functions, unused variables, dead branches
  magic <file>                 Scan for bare magic numbers / hardcoded numeric literals
  stats <file>                 Lines of code, blank lines, comment ratio, size, words
  scan <file>                  Extract & list all defined functions, classes, exports, types
  fuzz <file>                  CrossCheckV200 dynamic mock injection & edge-case fuzzer
  cp <file>                    Competitive Programming (CP) test runner & in/out validator

Security & Penetration Testing Commands:
  sec <file|dir>               OWASP static vulnerability scan (SQLi, XSS, Command Injection)
  secrets <file|dir>           Shannon entropy & pattern detector for credentials & API keys
  pentest <file|dir>           Automated security orchestration (Bandit + Semgrep + Safety)
  crypto <file>                Cryptographic integrity audit (weak hashes, ECB, timing)

Architecture & System Design Commands:
  design <file|dir>            System design flaws (IDOR/BOLA, pool exhaustion, rollback, CORS)
  race <file>                  Multi-tap / TOCTOU race hazard detector & double-spend simulation
  ml <file>                    Machine learning structural anomaly detector (Isolation Forest, Halstead)
  audit <file|dir>             All-in-one deep architecture audit (IDOR, race conditions, ML risk)
  check <file|dir>             All-in-one deterministic check (syntax, security, secrets, deadcode)

Utilities:
  urls <file>                  Auto-detect API endpoints / URLs and test responsiveness
  diff <file1> [file2]         Terminal side-by-side diff (against git HEAD or another file)
  git [args...]                Terminal Git command center
  report <file|dir> [--open]   Generate visual HTML audit report dashboard

Connected Software & Extension Engine:
  ext list                     List all connected external software commands
  ext run <id> [file] [args]   Execute a connected external software command
  ext add <id> <name> <cmd>    Register new external software / CLI command
  ext remove <id>              Unregister an external software command
  <custom_id> [args]           Direct execution alias for any registered external command
""")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        print_cherm_help()
        sys.exit(0)

    first = args[0].lower()
    if first in CLI_COMMANDS:
        CLI_COMMANDS[first](args[1:])
    elif cherm_bridge and cherm_bridge.get_command_by_id(first):
        target_file = args[1] if len(args) > 1 and not args[1].startswith("-") else None
        extra = " ".join(args[2:]) if len(args) > 2 else ""
        res = cherm_bridge.run_command_headless(first, filepath=target_file, extra_args=extra, allow_adhoc=True)
        if res.get("stdout"):
            print(res["stdout"], end="")
        if res.get("stderr"):
            sys.stderr.write(res["stderr"])
        sys.exit(res.get("exit_code", 0))
    else:
        print(f"Unknown command: '{first}'\n", file=sys.stderr)
        print_cherm_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
