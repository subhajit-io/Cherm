
import curses
import subprocess
import os
import sys
import urllib.request
import urllib.error
import re
import time
import shutil
import json
import difflib
import datetime
import ast as _ast_mod
import threading
import random

LAST_INTERACTION_TIME = time.time()
LAST_ERROR_TIME = 0.0

CURRENT_EMOTION = "neutral"
CURRENT_SUGGESTION = ""
COMPANION_RUNNING = True

GLOBAL_STDSCR = None

# Block until a key is pressed, redrawing the companion face each second
def smart_getch(win):
    win.timeout(1000)
    while True:
        if GLOBAL_STDSCR:
            draw_companion_face(GLOBAL_STDSCR)
            GLOBAL_STDSCR.refresh()
        win.refresh()
        k = win.getch()
        if k != -1:
            record_interaction()
            return k
# record interaction
def record_interaction():
    global LAST_INTERACTION_TIME
    LAST_INTERACTION_TIME = time.time()

# record error
def record_error():
    global LAST_ERROR_TIME
    LAST_ERROR_TIME = time.time()

LAST_EMOTION_TRIGGER_TIME = 0.0
EMOTION_TIMEOUT = 0.0

# Override the companion's emotion for a fixed duration, then let it revert naturally
def trigger_emotion(emo, duration=5.0, suggestion=""):
    global CURRENT_EMOTION, CURRENT_SUGGESTION, LAST_EMOTION_TRIGGER_TIME, EMOTION_TIMEOUT
    CURRENT_EMOTION = emo
    CURRENT_SUGGESTION = suggestion
    LAST_EMOTION_TRIGGER_TIME = time.time()
    EMOTION_TIMEOUT = duration

# Background thread that manages the companion's emotional state
def companion_thread():
    global CURRENT_EMOTION, CURRENT_SUGGESTION, COMPANION_RUNNING

    while COMPANION_RUNNING:
        now = time.time()

        if now - LAST_ERROR_TIME < 5.0:
            CURRENT_EMOTION = "error"
            CURRENT_SUGGESTION = "Whoops! An error occurred! Fixing it up..."

        elif now - LAST_EMOTION_TRIGGER_TIME < EMOTION_TIMEOUT:
            pass

        else:
            idle_time = now - LAST_INTERACTION_TIME
            if idle_time > 1800:
                CURRENT_EMOTION = "tired"
                CURRENT_SUGGESTION = "Zzz... take a break... or write code..."
            elif idle_time > 600:
                CURRENT_EMOTION = "sad"
                CURRENT_SUGGESTION = "I'm bored... are you still there?"
            else:
                CURRENT_EMOTION = "happy"
                CURRENT_SUGGESTION = ""

        time.sleep(1.0)



IS_WIN = os.name == "nt"
BOOKMARKS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "cherm_bookmarks.json"
)
START_TIME = time.time()



# load bookmarks
def load_bookmarks() -> list:
    try:
        if os.path.exists(BOOKMARKS_FILE):
            with open(BOOKMARKS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return [p for p in data if isinstance(p, str)]
    except Exception:
        pass
    return []


# save bookmarks
def save_bookmarks(bookmarks: list) -> None:
    try:
        with open(BOOKMARKS_FILE, "w", encoding="utf-8") as f:
            json.dump(bookmarks, f, indent=2)
    except Exception:
        pass



# shell cmd
def shell_cmd(cmd: str) -> str:
    if IS_WIN:
        return f'cmd /c "{cmd}"'
    return cmd


# exe
def exe(base: str) -> str:
    return f"{base}.exe" if IS_WIN else base


# null dev
def null_dev() -> str:
    return "NUL" if IS_WIN else "/dev/null"


# run prefix
def run_prefix(name: str) -> str:
    return f".\\{name}" if IS_WIN else f"./{name}"



# Write text at (y, x), silently clipping or skipping if out of bounds
def safe_addstr(stdscr, y: int, x: int, text: str, attr=curses.A_NORMAL):
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= width:
        return
    max_len = width - x - 1
    if max_len <= 0:
        return
    try:
        stdscr.addstr(y, x, text[:max_len], attr)
    except curses.error:
        pass


# draw centered
def draw_centered(stdscr, y: int, text: str, attr=curses.A_NORMAL):
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height:
        return
    x = max(0, (width - len(text)) // 2)
    safe_addstr(stdscr, y, x, text, attr)


# draw hline
def draw_hline(stdscr, y: int, char: str = "-"):
    height, width = stdscr.getmaxyx()
    if y < 0 or y >= height:
        return
    try:
        stdscr.addstr(y, 0, char * (width - 1))
    except curses.error:
        pass



# Return the curses color pair attribute, or A_BOLD as a monochrome fallback
def color(pair_num: int) -> int:
    if curses.has_colors():
        return curses.color_pair(pair_num)
    return curses.A_BOLD



# file icon
def _file_icon(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    icons = {
        ".py": "[py]", ".js": "[js]", ".ts": "[ts]", ".java": "[java]",
        ".c": "[c] ", ".cpp": "[cpp]", ".go": "[go]", ".rs": "[rs]",
        ".rb": "[rb]", ".php": "[php]", ".kt": "[kt]", ".swift": "[swift]",
        ".sh": "[sh]", ".bash": "[bash]", ".ps1": "[ps1]", ".pl": "[pl]",
        ".r": "[r] ", ".html": "[html]", ".htm": "[htm]", ".css": "[css]",
        ".json": "[json]", ".yaml": "[yaml]", ".yml": "[yml]", ".md": "[md]",
        ".sql": "[sql]", ".xml": "[xml]", ".txt": "[txt]",
    }
    return icons.get(ext, "[file]")


# File browser with bookmark support and optional multi-select
def select_target_file(stdscr, multi_select: bool = False):
    current_dir = os.path.abspath(".")
    history_back: list = []
    history_forward: list = []
    current_row = 0
    bookmarks = load_bookmarks()
    selected_files: list = []
    _SEP = "__sep__"
    stdscr.timeout(1000)
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        try:
            raw_items = os.listdir(current_dir)
        except PermissionError:
            raw_items = []

        dirs  = sorted([f for f in raw_items if os.path.isdir(os.path.join(current_dir, f))])
        files = sorted([f for f in raw_items if os.path.isfile(os.path.join(current_dir, f))])

        bm_display, bm_actual = [], []
        for bp in bookmarks:
            short  = os.path.basename(bp)
            parent = os.path.dirname(bp)
            bm_display.append(f"[*] {short}  ({parent})")
            bm_actual.append(bp)

        has_bm = bool(bm_display)
        display_items = (
            (["--- Bookmarks ---"] if has_bm else []) +
            bm_display +
            (["--- Directory ---"] if has_bm else []) +
            [".. (Parent Directory)"] +
            [f"[dir] {d}" for d in dirs] +
            [f"{_file_icon(f)} {f}" for f in files]
        )
        actual_items = (
            ([_SEP] if has_bm else []) +
            bm_actual +
            ([_SEP] if has_bm else []) +
            [".."] +
            dirs +
            files
        )

        if not dirs and not files and not bm_actual:
            display_items.append("  (Empty Directory)")
            actual_items.append(None)


        mode_label = ("MULTI-SELECT FILES  [SPACE=toggle  Enter=confirm]"
                      if multi_select else "BROWSE FILES")
        if height > 5:
            draw_centered(stdscr, 1, mode_label, color(5) | curses.A_BOLD)
            draw_hline(stdscr, 2)
            path_display = (current_dir if len(current_dir) < width - 10
                            else "..." + current_dir[-(width - 13):])
            safe_addstr(stdscr, 3, 2, f"  Path: {path_display}", color(6))
            draw_hline(stdscr, 4)

            if multi_select:
                sel_info = f"  [check] {len(selected_files)} selected"
                hint = "Up/Down:Nav  SPACE:Select  Enter:Confirm  M:Single-File  B:Bookmark  Q:Cancel  ESC:Exit"
                safe_addstr(stdscr, height - 2, 2, hint, color(6))
                safe_addstr(stdscr, height - 2, width - len(sel_info) - 2,
                            sel_info, color(2) | curses.A_BOLD)
            else:
                safe_addstr(stdscr, height - 2, 2,
                            "Up/Down:Navigate  Left/BS:Back  Right:Fwd  Enter:Open  M:Multi-Select  B:Bookmark  ?:Help  Q:Cancel  ESC:Exit",
                            color(6))
            draw_hline(stdscr, height - 3)

        max_visible = max(1, height - 9)
        visible_items = min(len(display_items), max_visible)

        if current_row >= len(display_items):
            current_row = max(0, len(display_items) - 1)

        start_idx = max(0, min(current_row - visible_items // 2,
                               len(display_items) - visible_items))
        end_idx = start_idx + visible_items
        start_y = 5

        for i in range(start_idx, end_idx):
            y = start_y + (i - start_idx)
            if y >= height - 3:
                break
            actual = actual_items[i] if i < len(actual_items) else None

            if actual == _SEP:
                safe_addstr(stdscr, y, 4, display_items[i], color(6))
                continue

            full_path = (actual if (actual and os.path.isabs(str(actual)))
                         else os.path.join(current_dir, str(actual)) if actual else "")
            is_bm = full_path in bookmarks
            is_multi_sel = (multi_select and full_path in selected_files
                            and os.path.isfile(full_path))

            prefix = "[v] " if is_multi_sel else "    "
            row_text = f"{prefix} {display_items[i]}"

            if i == current_row:
                attr = color(1) | curses.A_BOLD
            elif is_bm:
                attr = color(4) | curses.A_BOLD
            else:
                attr = curses.A_NORMAL

            draw_centered(stdscr, y, row_text, attr)

        if len(display_items) > max_visible:
            pct = int((current_row / max(1, len(display_items) - 1)) * 100)
            safe_addstr(stdscr, height - 3, width - 8, f"[{pct:3d}%]", color(6))

        stdscr.refresh()
        key = smart_getch(stdscr)

        if key == -1:
            continue


        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
            while current_row > 0 and actual_items[current_row] == _SEP:
                current_row -= 1

        elif key == curses.KEY_DOWN and current_row < len(display_items) - 1:
            current_row += 1
            while (current_row < len(display_items) - 1
                   and actual_items[current_row] == _SEP):
                current_row += 1

        elif key in (ord('m'), ord('M')):
            multi_select = not multi_select
            selected_files.clear()

        elif key in (curses.KEY_LEFT, curses.KEY_BACKSPACE, 8, 127):
            if history_back:
                history_forward.append(current_dir)
                current_dir = history_back.pop()
                current_row = 0
            else:
                parent = os.path.dirname(current_dir)
                if parent != current_dir:
                    history_back.append(current_dir)
                    history_forward.clear()
                    current_dir = parent
                    current_row = 0

        elif key == curses.KEY_RIGHT:
            if history_forward:
                history_back.append(current_dir)
                current_dir = history_forward.pop()
                current_row = 0

        elif key in (ord('b'), ord('B')):
            if current_row < len(actual_items):
                sel = actual_items[current_row]
                if sel and sel not in (_SEP, "..") and sel is not None:
                    fp = (sel if os.path.isabs(str(sel))
                          else os.path.join(current_dir, str(sel)))
                    if os.path.isfile(fp):
                        if fp in bookmarks:
                            bookmarks.remove(fp)
                        else:
                            bookmarks.append(fp)
                        save_bookmarks(bookmarks)

        elif key == ord(' ') and multi_select:
            if current_row < len(actual_items):
                sel = actual_items[current_row]
                if sel and sel not in (_SEP, "..") and sel is not None:
                    fp = (sel if os.path.isabs(str(sel))
                          else os.path.join(current_dir, str(sel)))
                    if os.path.isfile(fp):
                        if fp in selected_files:
                            selected_files.remove(fp)
                        else:
                            selected_files.append(fp)

        elif key == ord('?'):
            show_help_panel(stdscr)

        elif key in (curses.KEY_ENTER, 10, 13):
            if multi_select and selected_files:
                return selected_files

            if current_row >= len(actual_items):
                continue
            selected = actual_items[current_row]
            if selected is None or selected == _SEP:
                continue

            if selected == "..":
                history_back.append(current_dir)
                history_forward.clear()
                current_dir = os.path.dirname(current_dir)
                current_row = 0
            else:
                fp = (selected if os.path.isabs(str(selected))
                      else os.path.join(current_dir, str(selected)))
                if os.path.isdir(fp):
                    history_back.append(current_dir)
                    history_forward.clear()
                    current_dir = fp
                    current_row = 0
                else:
                    return [fp] if multi_select else fp

        elif key in (ord('q'), ord('Q')):
            return [] if multi_select else None

        elif key == 27:
            sys.exit(0)




# Return a list of menu-entry dicts for the given file's language
def get_commands_for_file(filepath: str) -> list:
    ext      = os.path.splitext(filepath)[1].lower()
    filename = os.path.basename(filepath)
    file_dir = os.path.dirname(os.path.abspath(filepath))
    cmds: list = []

    # Build a single menu-entry dict, forwarding any extra keyword args
    def entry(name, action, cmd, **kw):
        return {"name": name, "action": action, "cmd": cmd, **kw}

    if ext == ".py":
        run = f'python "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",            "code",       shell_cmd(f'python -m py_compile "{filepath}"')),
            entry(f"Check Functions -- Auto-Fuzzer ({filename})", "fuzz", filepath),
            entry(f"Execute File ({filename})",            "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",      "complexity", run, file=filepath),
        ]
    elif ext == ".js":
        run = f'node "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",       "code",       shell_cmd(f'node --check "{filepath}"')),
            entry(f"Scan Functions ({filename})",     "scan",       filepath),
            entry(f"Execute File ({filename})",       "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})", "complexity", run, file=filepath),
        ]
    elif ext == ".ts":
        run = f'ts-node "{filepath}"'
        cmds += [
            entry(f"Type Check ({filename})",         "code",       shell_cmd(f'tsc --noEmit "{filepath}"')),
            entry(f"Scan Functions ({filename})",     "scan",       filepath),
            entry(f"Execute File ({filename})",       "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})", "complexity", run, file=filepath),
        ]
    elif ext == ".java":
        class_name = filename.replace(".java", "")
        compile_c  = f'javac -Xlint "{filepath}"'
        run_c      = f'cd "{file_dir}" && javac "{filename}" && java "{class_name}"'
        syntax_c   = f'cd "{file_dir}" && {compile_c}'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(syntax_c)),
            entry(f"Scan Methods ({filename})",        "scan",       filepath),
            entry(f"Compile & Execute ({filename})",   "code",       shell_cmd(run_c)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run_c, file=filepath),
        ]
    elif ext == ".cpp":
        out_bin = exe("out_prog")
        run = f'g++ "{filepath}" -o {out_bin} && {run_prefix(out_bin)}'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'g++ -fsyntax-only "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Compile & Execute ({filename})",   "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".c":
        out_bin = exe("out_prog")
        run = f'gcc "{filepath}" -o {out_bin} && {run_prefix(out_bin)}'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'gcc -fsyntax-only "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Compile & Execute ({filename})",   "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".go":
        run = f'go run "{filepath}"'
        cmds += [
            entry(f"Vet / Lint ({filename})",          "code",       shell_cmd(f'go vet "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".rs":
        out_bin = exe("out_prog")
        run = f'rustc "{filepath}" -o {out_bin} && {run_prefix(out_bin)}'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'rustc --emit=metadata "{filepath}" -o {null_dev()}')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Compile & Execute ({filename})",   "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".rb":
        run = f'ruby "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'ruby -c "{filepath}"')),
            entry(f"Scan Methods ({filename})",        "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".php":
        run = f'php "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'php -l "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".kt":
        jar_name = filename.replace(".kt", ".jar")
        run = (f'cd "{file_dir}" && kotlinc "{filename}" -include-runtime -d {jar_name}'
               f' && kotlin {jar_name}')
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'kotlinc -nowarn "{filepath}" -include-runtime -d {null_dev()}')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Compile & Execute ({filename})",   "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".swift":
        run = f'swift "{filepath}"'
        cmds += [
            entry(f"Type Check ({filename})",          "code",       shell_cmd(f'swiftc -typecheck "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext in (".sh", ".bash"):
        run = f'bash "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'bash -n "{filepath}"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext == ".ps1":
        run = f'pwsh -File "{filepath}"'
        syntax_check = f'pwsh -Command "Get-Command -Syntax (Get-Item \'{filepath}\').FullName"'
        cmds += [
            entry(f"Parse / Lint ({filename})",        "code",       shell_cmd(syntax_check)),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext in (".pl", ".pm"):
        run = f'perl "{filepath}"'
        cmds += [
            entry(f"Check Syntax ({filename})",        "code",       shell_cmd(f'perl -c "{filepath}"')),
            entry(f"Scan Subs ({filename})",           "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext in (".r",):
        run = f'Rscript "{filepath}"'
        cmds += [
            entry(f"Parse / Check ({filename})",       "code",       shell_cmd(f'Rscript --vanilla -e "parse(\\"{filepath}\\")"')),
            entry(f"Scan Functions ({filename})",      "scan",       filepath),
            entry(f"Execute File ({filename})",        "code",       shell_cmd(run)),
            entry(f"Speed & Complexity ({filename})",  "complexity", run, file=filepath),
        ]
    elif ext in (".html", ".htm"):
        cmds += [entry(f"Scan Tags / Structure ({filename})", "scan", filepath)]
    elif ext == ".css":
        cmds += [entry(f"Scan Selectors ({filename})", "scan", filepath)]
    elif ext == ".json":
        cmds += [entry(f"Validate JSON ({filename})", "code", shell_cmd(f'python -m json.tool "{filepath}" > {null_dev()}'))]
    elif ext in (".yaml", ".yml"):
        cmds += [entry(f"Validate YAML ({filename})", "code", shell_cmd(f'python -c "import yaml,sys; yaml.safe_load(open(\'{filepath}\'))"'))]
    elif ext == ".sql":
        cmds += [entry(f"Scan Statements ({filename})", "scan", filepath)]
    elif ext in (".md", ".markdown"):
        cmds += [entry(f"Scan Headings ({filename})", "scan", filepath)]
    else:
        run = f'"{filepath}"' if IS_WIN else f'bash "{filepath}"'
        cmds += [
            entry(f"Scan Contents ({filename})",   "scan",       filepath),
            entry(f"Execute File ({filename})",    "code",       shell_cmd(run)),
            entry(f"Speed Benchmark ({filename})", "complexity", run, file=filepath),
        ]

    return cmds



# scan functions
def scan_functions(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Scanning file structure...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        show_results(stdscr, False, "Scanner", "ERR", str(e))
        return

    ext = os.path.splitext(filepath)[1].lower()
    items_found: list = []
    label = "functions"

    if ext == ".py":
        items_found = re.findall(r"^(?:async\s+)?def\s+(\w+)\s*\(", content, re.MULTILINE)
        label = "functions"
    elif ext in (".c", ".cpp", ".java"):
        pattern = (r"(?:int|void|char|double|float|bool|String|long|short|unsigned|"
                   r"auto|public|private|protected|static|override|final)\s+(\w+)\s*\([^)]*\)\s*(?:const\s*)?\{?")
        items_found = list(dict.fromkeys(re.findall(pattern, content)))
        label = "functions/methods"
    elif ext == ".js":
        named   = re.findall(r"function\s+(\w+)\s*\(", content)
        arrow   = re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(", content)
        class_m = re.findall(r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", content, re.MULTILINE)
        items_found = list(dict.fromkeys(named + arrow + class_m))
        label = "functions/arrows"
    elif ext == ".ts":
        pattern = r"(?:function\s+(\w+)|(?:async\s+)?(\w+)\s*\([^)]*\)\s*:\s*\w+\s*\{)"
        raw = re.findall(pattern, content)
        items_found = list(dict.fromkeys([g[0] or g[1] for g in raw if g[0] or g[1]]))
        label = "functions/methods"
    elif ext == ".go":
        items_found = re.findall(r"^func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", content, re.MULTILINE)
        label = "functions"
    elif ext == ".rs":
        items_found = re.findall(r"^(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*", content, re.MULTILINE)
        label = "functions"
    elif ext == ".rb":
        items_found = re.findall(r"^\s*def\s+(\w+[\?!]?)", content, re.MULTILINE)
        label = "methods"
    elif ext == ".php":
        items_found = re.findall(r"function\s+(\w+)\s*\(", content)
        label = "functions"
    elif ext == ".kt":
        items_found = re.findall(r"(?:fun|override fun)\s+(\w+)\s*\(", content)
        label = "functions"
    elif ext == ".swift":
        items_found = re.findall(r"(?:func|init)\s+(\w+)\s*[(<]", content)
        label = "functions"
    elif ext in (".sh", ".bash"):
        items_found = re.findall(r"^(\w+)\s*\(\)\s*\{", content, re.MULTILINE)
        label = "shell functions"
    elif ext == ".ps1":
        items_found = re.findall(r"function\s+(\w[\w-]*)\s*\{?", content, re.IGNORECASE)
        label = "cmdlets/functions"
    elif ext in (".pl", ".pm"):
        items_found = re.findall(r"^sub\s+(\w+)", content, re.MULTILINE)
        label = "subroutines"
    elif ext == ".r":
        items_found = re.findall(r"(\w+)\s*<-\s*function\s*\(", content)
        label = "functions"
    elif ext in (".html", ".htm"):
        tags = re.findall(r"<([a-zA-Z][a-zA-Z0-9]*)\b[^>]*>", content)
        unique_tags = list(dict.fromkeys(tags))
        items_found = [f"<{t}> tag" for t in unique_tags[:30]]
        if len(unique_tags) > 30:
            items_found.append(f"... and {len(unique_tags) - 30} more unique tags")
        label = "HTML tags"
    elif ext == ".css":
        selectors = re.findall(r"^([^{}\n/][^{}\n]*)\s*\{", content, re.MULTILINE)
        items_found = [s.strip() for s in selectors[:30]]
        if len(selectors) > 30:
            items_found.append(f"... and {len(selectors) - 30} more selectors")
        label = "CSS selectors"
    elif ext == ".sql":
        tables = re.findall(r"(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+(\w+)", content, re.IGNORECASE)
        items_found = list(dict.fromkeys(tables))
        label = "table references"
    elif ext in (".md", ".markdown"):
        items_found = re.findall(r"^#{1,6}\s+(.+)", content, re.MULTILINE)
        label = "headings"

    if not items_found:
        show_results(stdscr, True, "Structure Scanner", "N/A",
                     f"[ OK ] No {label} detected in this file.")
        return

    out_lines = [f"Found {len(items_found)} {label}:", ""]
    suffix = "()" if label in ("functions", "functions/methods", "functions/arrows",
                               "methods", "subroutines", "shell functions",
                               "cmdlets/functions") else ""
    for item in items_found:
        out_lines.append(f"[ OK ] {item}{suffix}")

    show_results(stdscr, True, "Structure Scanner", "DONE", "\n".join(out_lines))



# auto fuzz functions
def auto_fuzz_functions(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Generating AST Pre-Scanner & Mocks...", color(5) | curses.A_BOLD)
    stdscr.refresh()


    temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_temp_fuzzer.py")
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(fuzzer_code)
        cmd = f'python "{temp_file}" "{filepath}"'
        result = subprocess.run(shell_cmd(cmd), shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=15)
        success = result.returncode == 0
        output_text = ((result.stderr + "\n" + result.stdout).strip()
                       if (not success and result.stderr) else result.stdout)
    except subprocess.TimeoutExpired:
        success = False
        output_text = "[FAIL] GLOBAL TIMEOUT: The fuzzer took too long to complete."
    except Exception as e:
        success = False
        output_text = str(e)
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

    show_results(stdscr, success, "Auto-Fuzzer", "DONE", output_text)



# run complexity analysis
def run_complexity_analysis(stdscr, filepath: str, run_cmd_str: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Testing Speed & Code Quality...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    out: list = []

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            code = f.read()

        ifs      = len(re.findall(r'\bif\b',               code))
        elifs    = len(re.findall(r'\belif\b|\belse if\b', code))
        fors     = len(re.findall(r'\bfor\b',              code))
        whiles   = len(re.findall(r'\bwhile\b',            code))
        switches = len(re.findall(r'\bcase\b|\bswitch\b',  code))
        funcs    = len(re.findall(r'\bdef\b|\bfunction\b|\bfunc\b|\bfn\b', code))
        lines    = code.count("\n") + 1
        score    = 1 + ifs + elifs + fors + whiles + switches

        max_loop_depth = 0
        curr_depth = 0
        last_ind = -1
        for line in code.splitlines():
            sline = line.strip()
            if sline.startswith("for ") or sline.startswith("while ") or sline.startswith("for(") or sline.startswith("while("):
                ind = len(line) - len(line.lstrip())
                if ind > last_ind:
                    curr_depth += 1
                else:
                    curr_depth = 1
                last_ind = ind
                if curr_depth > max_loop_depth:
                    max_loop_depth = curr_depth

        time_c = "O(1) - Constant Time"
        if max_loop_depth == 1: time_c = "O(N) - Linear Time"
        elif max_loop_depth == 2: time_c = "O(N²) - Quadratic Time (Nested loops)"
        elif max_loop_depth > 2: time_c = f"O(N^{max_loop_depth}) - Polynomial Time (Deeply nested)"

        space_c = "O(1) - Constant Space"
        if any(x in code for x in ["append(", "push(", "malloc", "new Array", "new List", "[]", "{}"]):
            space_c = "O(N) - Linear Space (Dynamic allocations detected)"
        if funcs > 0 and re.search(r'\b(\w+)\s*\(.*?\).*?\1\s*\(', code, re.DOTALL):
            space_c = "O(N) - Linear Space (Recursion detected)"

        out.append("=== BIG-O ALGORITHMIC COMPLEXITY ===")
        out.append(f"[*] Estimated Time  : {time_c}")
        out.append(f"[*] Estimated Space : {space_c}")
        out.append("")

        out.append("=== CODE MESSINESS CHECK ===")
        out.append(f"[ OK ] Lines of code        : {lines}")
        out.append(f"[ OK ] Functions/defs        : {funcs}")
        out.append(f"[ OK ] Decisions (if/elif)   : {ifs + elifs + switches}")
        out.append(f"[ OK ] Loops (for/while)     : {fors + whiles}")
        out.append(f"[ OK ] Complexity score      : {score}")

        if score < 10:
            out.append("[ OK ] Verdict: Great! Simple, clean, easy to read.")
        elif score < 25:
            out.append("[WARN] Verdict: Moderate complexity. Consider splitting into smaller functions.")
        elif score < 50:
            out.append("[WARN] Verdict: High complexity. Refactoring recommended.")
        else:
            out.append("[FAIL] Verdict: Very high complexity! Spaghetti code risk.")

    except Exception as e:
        out.append(f"[FAIL] Could not analyse file: {e}")

    out.append("")
    out.append("=== SPEED TEST ===")

    try:
        actual_run = run_cmd_str
        if "&&" in run_cmd_str:
            steps = run_cmd_str.rsplit("&&", 1)
            compile_part = steps[0].strip()
            run_part     = steps[1].strip()
            out.append("[...] Compiling first... (not timed)")
            comp = subprocess.run(shell_cmd(compile_part), shell=True,
                                  capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
            if comp.returncode != 0:
                out.append("[FAIL] Compilation failed!")
                out.append(f"[ERR ] {comp.stderr.strip()[:200]}")
                show_results(stdscr, False, "Speed & Quality", "ERR", "\n".join(out))
                return
            out.append("[ OK ] Compiled successfully.")
            actual_run = run_part

        stdin_data = ("1\n" * 50).encode("utf-8")
        start = time.perf_counter()
        result = subprocess.run(
            actual_run, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            input=stdin_data, timeout=15,
        )
        elapsed = time.perf_counter() - start
        stderr_text = (result.stderr.decode("utf-8", errors="replace").strip()
                       if isinstance(result.stderr, bytes) else result.stderr.strip())

        if result.returncode == 0:
            out.append(f"[ OK ] Execution time: {elapsed:.4f}s")
            if elapsed < 0.05:
                out.append("[ OK ] Speed: Blazing Fast!")
            elif elapsed < 0.5:
                out.append("[ OK ] Speed: Fast -- well within acceptable range.")
            elif elapsed < 2.0:
                out.append("[WARN] Speed: Moderate. Check for inefficient loops.")
            else:
                out.append("[FAIL] Speed: Slow. Consider optimising your algorithm.")
        else:
            err = stderr_text
            if "setupterm" in err or "TERM" in err:
                out.append("[WARN] Cannot time a terminal UI program in the background.")
            elif "Redirection is not supported" in err or not err:
                out.append(f"[ OK ] Execution time: {elapsed:.4f}s  (exit code {result.returncode})")
                out.append("[WARN] Program exited with a non-zero code (may need user input).")
            else:
                out.append(f"[FAIL] Program exited with error (code {result.returncode}).")
                out.append(f"[ERR ] {err[:200]}")

    except subprocess.TimeoutExpired:
        out.append("[FAIL] Timeout: Execution took longer than 15 seconds.")
    except Exception as e:
        out.append(f"[FAIL] Speed test error: {e}")

    show_results(stdscr, True, "Speed & Quality Test", "DONE", "\n".join(out))


# execute command
def execute_command(stdscr, cmd: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    display_cmd = cmd[:width - 14] + "..." if len(cmd) > width - 13 else cmd
    draw_centered(stdscr, height // 2, f"Running: {display_cmd}...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    result = None
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        success = result.returncode == 0
        output_text = ((result.stderr + "\n" + result.stdout).strip()
                       if (not success and result.stderr) else result.stdout)
    except subprocess.TimeoutExpired:
        success = False
        output_text = "[FAIL] Command timed out after 60 seconds."
    except Exception as e:
        success = False
        output_text = str(e)

    exit_code = result.returncode if result is not None else "ERR"
    show_results(stdscr, success, cmd[:60], exit_code, output_text)


# auto check apis
def auto_check_apis(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Scanning code for URLs...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        show_results(stdscr, False, "Read File Error", "ERR", str(e))
        return

    raw_urls = re.findall(r'https?://[^\s\'"<>`]+', content)
    urls = list(dict.fromkeys(url.rstrip(".,;)'\"") for url in raw_urls))

    if not urls:
        show_results(stdscr, True, "API Scanner", "N/A",
                     "[ OK ] No HTTP/HTTPS URLs were found in this file.")
        return

    stdscr.clear()
    draw_centered(stdscr, height // 2, f"Found {len(urls)} URLs. Testing...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    out: list = []
    all_ok = True
    for url in urls:
        try:
            req  = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            t0   = time.perf_counter()
            resp = urllib.request.urlopen(req, timeout=8)
            ms   = int((time.perf_counter() - t0) * 1000)
            code = resp.getcode()
            out.append(f"[ OK ] {code}  {ms:>5}ms  {url[:width - 22]}")
        except urllib.error.HTTPError as e:
            out.append(f"[FAIL] {e.code}     N/A  {url[:width - 22]}")
            all_ok = False
        except urllib.error.URLError as e:
            out.append(f"[ERR ] DNS/Net -- {url[:width - 22]}  ({e.reason})")
            all_ok = False
        except Exception as e:
            out.append(f"[ERR ] {url[:width - 22]}  ({e})")
            all_ok = False

    header = [f"Tested {len(urls)} URL(s):", ""]
    show_results(stdscr, all_ok, f"API Scanner -- {len(urls)} URLs", "DONE",
                 "\n".join(header + out))


# show file stats
def show_file_stats(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Calculating file statistics...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        size_bytes = os.path.getsize(filepath)
        mtime      = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(filepath)))

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        total      = len(lines)
        blank      = sum(1 for l in lines if l.strip() == "")
        comments   = sum(1 for l in lines if l.strip().startswith(("#", "//", "*", "<!--", "--", "%")))
        code_lines = total - blank - comments
        unique_words = len(set(re.findall(r"\w+", "".join(lines))))

        size_str = (f"{size_bytes} B" if size_bytes < 1024
                    else f"{size_bytes/1024:.1f} KB" if size_bytes < 1_048_576
                    else f"{size_bytes/1_048_576:.2f} MB")
        comment_pct = int(comments / total * 100) if total > 0 else 0

        out = [
            "=== FILE STATISTICS ===", "",
            f"[ OK ] File          : {os.path.basename(filepath)}",
            f"[ OK ] Extension     : {os.path.splitext(filepath)[1].lower() or '(none)'}",
            f"[ OK ] Size          : {size_str}",
            f"[ OK ] Last modified : {mtime}", "",
            f"[ OK ] Total lines   : {total}",
            f"[ OK ] Code lines    : {code_lines}",
            f"[ OK ] Blank lines   : {blank}",
            f"[ OK ] Comment lines : {comments}  ({comment_pct}%)",
            f"[ OK ] Unique words  : {unique_words}", "",
        ]

        if comment_pct >= 20:
            out.append("[ OK ] Documentation: Well-documented!")
        elif comment_pct >= 5:
            out.append("[WARN] Documentation: Moderate comments. Add more docs.")
        else:
            out.append("[FAIL] Documentation: Very few comments! Document your code.")

        show_results(stdscr, True, "File Statistics", "DONE", "\n".join(out))
    except Exception as e:
        show_results(stdscr, False, "File Statistics", "ERR", str(e))


# view raw file
def view_raw_file(stdscr, filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "File Viewer", "ERR", str(e))
        return

    scroll = 0
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        max_vis = max(1, height - 4)

        draw_centered(stdscr, 0, f"{os.path.basename(filepath)} -- {len(lines)} lines",
                      color(5) | curses.A_BOLD)
        draw_hline(stdscr, 1)

        for i in range(max_vis):
            lnum = scroll + i
            if lnum >= len(lines):
                break
            raw = lines[lnum].rstrip("\n\r")
            num_str = f"{lnum + 1:>4} | "
            safe_addstr(stdscr, 2 + i, 0, num_str, color(6))
            safe_addstr(stdscr, 2 + i, len(num_str), raw[:max(0, width - len(num_str) - 1)])

        draw_hline(stdscr, height - 2)
        pct = int(scroll / max(1, len(lines) - max_vis) * 100) if len(lines) > max_vis else 100
        safe_addstr(stdscr, height - 1, 2, "Up/Down/PgUp/PgDn:Scroll  Q:Back  ESC:Exit", color(6))
        safe_addstr(stdscr, height - 1, width - 8, f"[{pct:3d}%]", color(6))
        stdscr.refresh()

        key = smart_getch(stdscr)
        if key == 27:
            sys.exit(0)
        elif key in (ord("q"), ord("Q")):
            break
        elif key == curses.KEY_UP and scroll > 0:
            scroll -= 1
        elif key == curses.KEY_DOWN and scroll < max(0, len(lines) - max_vis):
            scroll += 1
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max_vis)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, len(lines) - max_vis), scroll + max_vis)
        elif key in (curses.KEY_HOME, ord("g")):
            scroll = 0
        elif key in (curses.KEY_END, ord("G")):
            scroll = max(0, len(lines) - max_vis)


# search in file
def search_in_file(stdscr, filepath: str):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, 2, f"Search in: {os.path.basename(filepath)}", color(5) | curses.A_BOLD)
    safe_addstr(stdscr, 4, 2, "Enter search term (case-insensitive): ")
    stdscr.refresh()

    try:
        query_bytes = stdscr.getstr(4, 40, width - 42)
        query = query_bytes.decode("utf-8", errors="replace").strip()
    except Exception:
        query = ""
    finally:
        curses.noecho()
        curses.curs_set(0)

    if not query:
        return

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "Search", "ERR", str(e))
        return

    matches = [(i, line.rstrip()) for i, line in enumerate(lines, 1)
               if query.lower() in line.lower()]

    if not matches:
        show_results(stdscr, True, "Search", "N/A",
                     f"[ OK ] No matches found for: '{query}'")
        return

    out = [f"Found {len(matches)} match(es) for '{query}':", ""]
    for lineno, text in matches[:200]:
        out.append(f"[ OK ] Line {lineno:>4}: {text[:max(0, width - 20)]}")
    if len(matches) > 200:
        out.append(f"[WARN] ... and {len(matches) - 200} more matches (truncated).")

    show_results(stdscr, True, f"Search '{query}'", "DONE", "\n".join(out))


# copy path to clipboard
def copy_path_to_clipboard(stdscr, filepath: str):
    abs_path = os.path.abspath(filepath)
    success = False
    msg = ""
    try:
        if IS_WIN:
            subprocess.run(f'echo {abs_path}| clip', shell=True, check=True)
            success = True
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=abs_path.encode(), check=True)
            success = True
        elif shutil.which("xsel"):
            subprocess.run(["xsel", "--clipboard", "--input"], input=abs_path.encode(), check=True)
            success = True
        elif shutil.which("pbcopy"):
            subprocess.run(["pbcopy"], input=abs_path.encode(), check=True)
            success = True
        else:
            msg = "[WARN] No clipboard tool found (xclip/xsel/pbcopy/clip)."
    except Exception as e:
        msg = f"[FAIL] Clipboard error: {e}"

    out = f"[ OK ] Copied to clipboard:\n  {abs_path}" if success else msg
    show_results(stdscr, success, "Copy Path", "DONE", out)



# Show an input prompt inside the TUI and return the user's text
def _git_prompt(stdscr, prompt_text: str, max_len: int = 120) -> str:
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2 - 2, "GIT INPUT", color(5) | curses.A_BOLD)
    draw_hline(stdscr, height // 2 - 1)
    safe_addstr(stdscr, height // 2 + 1, 4, prompt_text, color(4) | curses.A_BOLD)
    safe_addstr(stdscr, height // 2 + 3, 4, "> ")
    stdscr.refresh()
    try:
        raw = stdscr.getstr(height // 2 + 3, 6, min(max_len, width - 8))
        result = raw.decode("utf-8", errors="replace").strip()
    except Exception:
        result = ""
    finally:
        curses.noecho()
        curses.curs_set(0)
    return result


# Run a git command. Returns (output_str, success_bool)
def _git_run(cwd: str, *args, timeout: int = 30) -> tuple:
    try:
        r = subprocess.run(
            ["git"] + list(args),
            cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
        )
        out = (r.stdout.strip() + ("\n" + r.stderr.strip() if r.stderr.strip() else "")).strip()
        return out, r.returncode == 0
    except FileNotFoundError:
        return "[FAIL] git is not installed or not found in PATH.\n[WARN] Install Git from https://git-scm.com", False
    except subprocess.TimeoutExpired:
        return f"[FAIL] git {' '.join(args)} timed out after {timeout}s.", False
    except Exception as e:
        return str(e), False


# Interactive Git Command Center
def git_command_center(stdscr, filepath: str):
    file_dir  = os.path.dirname(os.path.abspath(filepath))
    file_name = os.path.basename(filepath)

    _, ok = _git_run(file_dir, "--version")
    if not ok:
        show_results(stdscr, False, "Git Command Center", "ERR",
                     "[FAIL] git is not installed or not in PATH.\n"
                     "[WARN] Download Git from  https://git-scm.com/downloads")
        return

    _, in_repo = _git_run(file_dir, "rev-parse", "--is-inside-work-tree")

    SEP = None
    cmds = [
        ("── STATUS & INFO ─────────────────────",  SEP,  None),
        ("git status",                              "status",             ["status", "-sb"]),
        ("git log  (last 15 commits)",              "log",                ["log", "--oneline", "-15"]),
        ("git log  (full, last 8)",                 "log_full",           ["log", "-8", "--pretty=format:%h  %an  %ar%n  %s%n"]),
        ("git log --graph  (branch tree)",          "log_graph",          ["log", "--all", "--oneline", "--graph", "--decorate", "-25"]),
        ("git show HEAD  (last commit detail)",     "show_head",          ["show", "HEAD", "--stat"]),
        ("git show <commit hash>  (prompt)",        "show_commit",        "PROMPT:Commit hash to show:"),
        ("git diff  (unstaged changes)",            "diff",               ["diff"]),
        ("git diff --cached  (staged changes)",     "diff_cached",        ["diff", "--cached"]),
        ("git diff HEAD  (all changes)",            "diff_head",          ["diff", "HEAD"]),
        ("git diff <branch>  (prompt)",             "diff_branch",        "PROMPT:Branch to diff against:"),
        ("git blame <this file>",                   "blame",              ["blame", "-l", "--", file_name]),
        ("git reflog  (recovery history)",          "reflog",             ["reflog", "--oneline", "-20"]),
        ("git shortlog -s  (commit leaderboard)",   "shortlog",           ["shortlog", "-s", "-n", "HEAD"]),
        ("── STAGING ───────────────────────────",  SEP,  None),
        ("git add .  (stage ALL changes)",          "add_all",            ["add", "."]),
        ("git add <this file>",                     "add_file",           ["add", "--", file_name]),
        ("git add <path>  (prompt)",                "add_path",           "PROMPT:File or path to add:"),
        ("git reset HEAD .  (unstage all)",         "reset_all",          ["reset", "HEAD", "."]),
        ("git reset HEAD <this file>",              "reset_file",         ["reset", "HEAD", "--", file_name]),
        ("git restore <this file>  (discard edits)","restore_file",       "CONFIRM:This DISCARDS all unsaved edits to this file. Continue?:[restore, --, file_name]"),
        ("git restore --staged <this file>",        "restore_staged",     ["restore", "--staged", "--", file_name]),
        ("git stash  (save work-in-progress)",      "stash",              ["stash", "push", "-m", "WIP stash by cherm"]),
        ("git stash pop  (restore last stash)",     "stash_pop",          ["stash", "pop"]),
        ("git stash list",                          "stash_list",         ["stash", "list"]),
        ("git stash drop  (delete top stash)",      "stash_drop",         "CONFIRM:Delete the top stash entry?:[stash, drop]"),
        ("── COMMITTING ────────────────────────",  SEP,  None),
        ("git commit -m <message>  (prompt)",       "commit",             "COMMIT_MSG"),
        ("git commit --amend  (edit last commit)",  "amend",              "AMEND"),
        ("git revert HEAD  (undo last commit safely)","revert",           "CONFIRM:Create a revert commit for HEAD (safe undo)?:[revert, HEAD, --no-edit]"),
        ("git reset --soft HEAD~1  (undo commit, keep changes)","reset_soft","CONFIRM:Move HEAD back 1 commit (changes kept)?:[reset, --soft, HEAD~1]"),
        ("git reset --hard HEAD~1  (DANGER: discard commit)","reset_hard","CONFIRM:DANGER -- permanently discard last commit?:[reset, --hard, HEAD~1]"),
        ("git tag <name>  (prompt)",                "tag",                "PROMPT:Tag name (e.g. v1.0.0):"),
        ("git tag --list",                          "tag_list",           ["tag", "--list", "--sort=-version:refname"]),
        ("── BRANCHING ─────────────────────────",  SEP,  None),
        ("git branch  (list local branches)",       "branch_list",        ["branch", "-vv"]),
        ("git branch -a  (list ALL branches)",      "branch_all",         ["branch", "-a"]),
        ("git checkout <branch>  (prompt)",         "checkout",           "PROMPT:Branch to switch to:"),
        ("git checkout -b <new branch>  (prompt)",  "checkout_new",       "PROMPT:New branch name:"),
        ("git merge <branch>  (prompt)",            "merge",              "PROMPT:Branch to merge into current:"),
        ("git rebase <branch>  (prompt)",           "rebase",             "PROMPT:Branch to rebase onto:"),
        ("git branch -d <branch>  (safe delete, prompt)","branch_del",    "PROMPT:Branch name to delete (safe):"),
        ("git branch -D <branch>  (FORCE delete, prompt)","branch_del_f", "PROMPT:Branch name to FORCE delete:"),
        ("── REMOTE ────────────────────────────",  SEP,  None),
        ("git remote -v  (show remotes)",           "remote_v",           ["remote", "-v"]),
        ("git fetch  (download changes, no merge)", "fetch",              ["fetch", "--all", "--prune"]),
        ("git pull  (fetch + merge)",               "pull",               ["pull"]),
        ("git pull --rebase",                       "pull_rebase",        ["pull", "--rebase"]),
        ("git push  (push current branch)",         "push",               ["push"]),
        ("git push -u origin <branch>  (prompt)",   "push_branch",        "PROMPT:Branch name to push:"),
        ("git push --tags",                         "push_tags",          ["push", "--tags"]),
        ("git clone <url>  (prompt)",               "clone",              "PROMPT:Repository URL to clone:"),
        ("── REPO SETUP ────────────────────────",  SEP,  None),
        ("git init  (initialise repo here)",        "init",               ["init"]),
        ("git config --list  (show all config)",    "config_list",        ["config", "--list"]),
        ("git config user.name <name>  (prompt)",   "config_name",        "PROMPT:Your name for commits:"),
        ("git config user.email <email>  (prompt)", "config_email",       "PROMPT:Your email for commits:"),
        ("git remote add origin <url>  (prompt)",   "remote_add",         "PROMPT:Remote origin URL:"),
        ("git remote remove origin",                "remote_rm",          "CONFIRM:Remove origin remote?:[remote, remove, origin]"),
        ("git clean -fd  (delete untracked files)", "clean",              "CONFIRM:DANGER -- delete all untracked files and dirs?:[clean, -fd]"),
        ("git gc  (garbage collect / optimise)",    "gc",                 ["gc", "--auto"]),
        ("── ──────────────────────────────────",   SEP,  None),
        ("Back to main menu",                       "back",               None),
    ]

    current_row = 0
    for i, (_, key, _) in enumerate(cmds):
        if key is not None:
            current_row = i
            break

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        draw_centered(stdscr, 0, " GIT COMMAND CENTER ", color(5) | curses.A_BOLD)
        draw_hline(stdscr, 1)

        branch_out, _ = _git_run(file_dir, "rev-parse", "--abbrev-ref", "HEAD")
        status_out, _ = _git_run(file_dir, "status", "--short")
        changed       = len([l for l in status_out.splitlines() if l.strip()])
        repo_bar = (f"  Branch: {branch_out or '(not a repo)'}" +
                    (f"  |  {changed} changed file(s)" if changed else "  |  clean") +
                    f"  |  File: {file_name}")
        safe_addstr(stdscr, 2, 2, repo_bar[:width - 4], color(4) | curses.A_BOLD)
        draw_hline(stdscr, 3)

        draw_hline(stdscr, height - 3)
        safe_addstr(stdscr, height - 2, 2,
                    "Up/Down:Navigate  Enter:Run  Q:Back  ESC:Exit", color(6))

        max_vis = max(1, height - 8)
        selectable = [i for i, (_, k, _) in enumerate(cmds) if k is not None]

        vis_start = max(0, min(current_row - max_vis // 2, len(cmds) - max_vis))
        vis_end   = vis_start + max_vis
        start_y   = 4

        for i in range(vis_start, min(vis_end, len(cmds))):
            label, key, _ = cmds[i]
            y = start_y + (i - vis_start)
            if y >= height - 3:
                break

            if key is None:
                safe_addstr(stdscr, y, 2, label[:width - 4], color(5) | curses.A_BOLD)
            elif i == current_row:
                draw_centered(stdscr, y, f"  {label}  ", color(1) | curses.A_BOLD)
            elif key == "back":
                draw_centered(stdscr, y, f"  {label}  ", color(4))
            else:
                draw_centered(stdscr, y, f"  {label}  ")

        stdscr.refresh()
        key_press = smart_getch(stdscr)

        if key_press == 27:
            sys.exit(0)
        elif key_press in (ord("q"), ord("Q")):
            break

        elif key_press == curses.KEY_UP:
            prev = [i for i in selectable if i < current_row]
            if prev:
                current_row = prev[-1]

        elif key_press == curses.KEY_DOWN:
            nxt = [i for i in selectable if i > current_row]
            if nxt:
                current_row = nxt[0]

        elif key_press == curses.KEY_PPAGE:
            prev_far = [i for i in selectable if i < max(0, current_row - max_vis)]
            current_row = prev_far[-1] if prev_far else (selectable[0] if selectable else 0)

        elif key_press == curses.KEY_NPAGE:
            nxt_far = [i for i in selectable if i > min(len(cmds) - 1, current_row + max_vis)]
            current_row = nxt_far[0] if nxt_far else (selectable[-1] if selectable else 0)

        elif key_press in (curses.KEY_ENTER, 10, 13):
            label, cmd_key, cmd_args = cmds[current_row]
            if cmd_key == "back" or cmd_args is None:
                break

            final_args = None
            title = label.strip()

            if isinstance(cmd_args, list):
                final_args = [file_name if a == file_name else a for a in cmd_args]

            elif isinstance(cmd_args, str):
                if cmd_args == "COMMIT_MSG":
                    msg = _git_prompt(stdscr, "Enter commit message:")
                    if not msg:
                        continue
                    final_args = ["commit", "-m", msg]

                elif cmd_args == "AMEND":
                    msg = _git_prompt(stdscr, "New message for amended commit (leave blank to keep old):")
                    if msg:
                        final_args = ["commit", "--amend", "-m", msg]
                    else:
                        final_args = ["commit", "--amend", "--no-edit"]

                elif cmd_args.startswith("PROMPT:"):
                    prompt_text = cmd_args[len("PROMPT:"):]
                    user_input  = _git_prompt(stdscr, prompt_text)
                    if not user_input:
                        continue
                    arg_map = {
                        "show_commit":  ["show", user_input, "--stat"],
                        "diff_branch":  ["diff", user_input],
                        "add_path":     ["add", user_input],
                        "checkout":     ["checkout", user_input],
                        "checkout_new": ["checkout", "-b", user_input],
                        "merge":        ["merge", user_input],
                        "rebase":       ["rebase", user_input],
                        "branch_del":   ["branch", "-d", user_input],
                        "branch_del_f": ["branch", "-D", user_input],
                        "push_branch":  ["push", "-u", "origin", user_input],
                        "clone":        ["clone", user_input],
                        "tag":          ["tag", user_input],
                        "config_name":  ["config", "user.name", user_input],
                        "config_email": ["config", "user.email", user_input],
                        "remote_add":   ["remote", "add", "origin", user_input],
                    }
                    final_args = arg_map.get(cmd_key)
                    if not final_args:
                        continue

                elif cmd_args.startswith("CONFIRM:"):
                    rest       = cmd_args[len("CONFIRM:"):]
                    question   = rest[:rest.rfind(":")]
                    args_str   = rest[rest.rfind(":") + 1:]
                    parsed = [a.strip().strip("'\"") for a in
                              args_str.strip("[]").split(",") if a.strip()]
                    parsed = [file_name if a == "file_name" else a for a in parsed]

                    stdscr.clear()
                    height2, width2 = stdscr.getmaxyx()
                    draw_centered(stdscr, height2 // 2 - 2, "CONFIRM", color(3) | curses.A_BOLD)
                    draw_hline(stdscr, height2 // 2 - 1)
                    draw_centered(stdscr, height2 // 2 + 1, question, color(4) | curses.A_BOLD)
                    draw_centered(stdscr, height2 // 2 + 3,
                                  "Press  Y  to confirm     ESC / N  to cancel", color(6))
                    stdscr.refresh()
                    confirm = smart_getch(stdscr)
                    if confirm == 27:
                        sys.exit(0)
                    elif confirm not in (ord("y"), ord("Y")):
                        continue
                    final_args = parsed

            if final_args is None:
                continue

            stdscr.clear()
            height2, width2 = stdscr.getmaxyx()
            cmd_display = "git " + " ".join(final_args)
            draw_centered(stdscr, height2 // 2,
                          f"Running: {cmd_display[:width2 - 14]}...",
                          color(5) | curses.A_BOLD)
            stdscr.refresh()

            out, success = _git_run(file_dir, *final_args, timeout=60)

            if not out:
                out = "[ OK ] Command completed with no output."

            pretty: list = [f"=== {title} ===", ""]
            for line in out.splitlines():
                stripped = line.rstrip()
                if not stripped:
                    pretty.append("")
                elif stripped.startswith(("[FAIL]", "error", "fatal", "ERR", "CONFLICT")):
                    pretty.append(f"[FAIL] {stripped}")
                elif stripped.startswith(("warning", "WARN")):
                    pretty.append(f"[WARN] {stripped}")
                elif stripped.startswith("|") or stripped.startswith("*") or stripped.startswith("\\\\"):
                    pretty.append(f"       {stripped}")
                else:
                    pretty.append(f"[ OK ] {stripped}")

            show_results(stdscr, success, f"git {' '.join(final_args[:3])}",
                         0 if success else 1, "\n".join(pretty))




_SECRET_PATTERNS = [
    (r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']',         "Hardcoded Password",    "CRITICAL"),
    (r'(?i)(api_key|apikey|api_secret)\s*=\s*["\'][^"\']{6,}["\']',   "API Key",               "CRITICAL"),
    (r'(?i)(secret|secret_key)\s*=\s*["\'][^"\']{6,}["\']',           "Secret Key",            "CRITICAL"),
    (r'(?i)(token|auth_token|access_token)\s*=\s*["\'][^"\']{6,}["\']',"Auth Token",           "HIGH"),
    (r'(?i)aws_access_key_id\s*=\s*["\']?[A-Z0-9]{16,}',              "AWS Access Key",        "CRITICAL"),
    (r'(?i)aws_secret_access_key\s*=\s*["\'][^"\']{20,}["\']',        "AWS Secret Access Key", "CRITICAL"),
    (r'AKIA[0-9A-Z]{16}',                                               "AWS Key ID Pattern",   "CRITICAL"),
    (r'(?i)(db_password|database_password|mysql_pass)\s*=\s*["\'][^"\']+["\']',"DB Password", "CRITICAL"),
    (r'(?i)private_key\s*=\s*["\'][^"\']{10,}["\']',                  "Private Key",           "CRITICAL"),
    (r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',                   "Private Key Block",     "CRITICAL"),
    (r'(?i)(slack_token|slack_webhook)\s*=\s*["\'][^"\']{10,}["\']',  "Slack Token",           "HIGH"),
    (r'(?i)github_token\s*=\s*["\'][^"\']{10,}["\']',                 "GitHub Token",          "HIGH"),
    (r'ghp_[A-Za-z0-9]{36}',                                            "GitHub PAT",           "CRITICAL"),
    (r'(?i)stripe_(secret|publishable)_key\s*=\s*["\'][^"\']+',       "Stripe Key",            "CRITICAL"),
    (r'SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}',                     "SendGrid Key Pattern", "CRITICAL"),
    (r'(?i)twilio_(account_sid|auth_token)\s*=\s*["\'][^"\']+',       "Twilio Secret",         "HIGH"),
    (r'(?i)heroku_api_key\s*=\s*["\'][^"\']+',                        "Heroku API Key",        "HIGH"),
    (r'(?i)bearer\s+[A-Za-z0-9\-_.]{20,}',                            "Bearer Token",          "HIGH"),
    (r'(?i)(ftp_password|smtp_password)\s*=\s*["\'][^"\']+',          "FTP/SMTP Password",     "HIGH"),
    (r'(?i)sendgrid_api_key\s*=\s*["\'][^"\']+',                      "SendGrid API Key",      "HIGH"),
]


# scan secrets
def scan_secrets(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Scanning for Hardcoded Secrets...",
                  color(7) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "Secret Scanner", "ERR", str(e))
        return

    findings: list = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--")):
            continue
        for pattern, secret_type, severity in _SECRET_PATTERNS:
            if re.search(pattern, line):
                redacted = re.sub(r'["\'][^"\']{3,}["\']', '"[REDACTED]"', stripped)
                findings.append((i, secret_type, severity, redacted[:72]))
                break

    out: list = ["=== HARDCODED SECRET SCANNER ===", ""]
    sev_tag = {"CRITICAL": "[FAIL]", "HIGH": "[WARN]", "MEDIUM": "[WARN]"}

    if not findings:
        out.append("[ OK ] No hardcoded secrets detected.")
        out.append("[ OK ] Always use environment variables or a secrets manager.")
    else:
        crit = sum(1 for _, _, s, _ in findings if s == "CRITICAL")
        high = sum(1 for _, _, s, _ in findings if s == "HIGH")
        out.append(f"[FAIL] Found {len(findings)} potential secret(s):")
        out.append(f"[FAIL]   CRITICAL : {crit}")
        out.append(f"[WARN]   HIGH     : {high}")
        out.append("")
        for lineno, secret_type, severity, ctx in findings:
            tag = sev_tag.get(severity, "[WARN]")
            out.append(f"{tag} Line {lineno:>4}  [{severity}]  {secret_type}")
            out.append(f"         {ctx}")
            out.append("")
        out.append("[FAIL] ACTION REQUIRED: Move secrets to env vars or .env files!")
        out.append("[WARN] Never commit secrets to version control (use .gitignore).")

    show_results(stdscr, len(findings) == 0, "Secret Scanner", "DONE", "\n".join(out))



# detect magic numbers
def detect_magic_numbers(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Detecting Magic Numbers...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "Magic Number Detector", "ERR", str(e))
        return

    ALLOWED = {"0", "1", "2", "-1", "0.0", "1.0", "100", "255", "0x0", "0xFF",
               "0.5", "3.14", "360", "365", "24", "60", "1000"}

    findings: list = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--", "--", "%", '"', "'")):
            continue
        cleaned = re.sub(r'["\'].*?["\']', '""', stripped)
        numbers = re.findall(r'(?<![.\w])(-?\d+(?:\.\d+)?)(?![.\w])', cleaned)
        for num in numbers:
            if num not in ALLOWED and len(num) <= 10:
                findings.append((i, num, stripped[:65]))

    out: list = ["=== MAGIC NUMBER DETECTION ===", ""]
    if not findings:
        out.append("[ OK ] No magic numbers detected!")
        out.append("[ OK ] Code uses named constants properly -- great practice!")
    else:
        out.append(f"[WARN] Found {len(findings)} magic number(s):")
        out.append("")
        prev_line = -1
        for lineno, num, ctx in findings[:100]:
            if lineno != prev_line:
                out.append(f"[WARN] Line {lineno:>4}: {num:>12}  |  {ctx}")
                prev_line = lineno
        if len(findings) > 100:
            out.append(f"[WARN] ... and {len(findings) - 100} more (truncated).")
        out.append("")
        out.append("[WARN] Tip: Replace magic numbers with named constants.")
        out.append("[WARN] Example:  MAX_RETRIES = 5  instead of bare  5")

    show_results(stdscr, len(findings) == 0, "Magic Number Detector", "DONE", "\n".join(out))



# show help panel
def show_help_panel(stdscr):
    help_lines = [
        "=== CHERM v2.0 -- KEYBOARD SHORTCUTS ===",
        "",
        "[ GLOBAL ]",
        "  ?            Show this help panel",
        "  B            Toggle bookmark for current file",
        "  ESC          Back / Cancel",
        "  Q / q        Close results view",
        "",
        "[ MAIN MENU ]",
        "  Up / Down    Navigate menu items",
        "  Enter        Run selected action",
        "  ESC          Back to file browser",
        "",
        "[ FILE BROWSER ]",
        "  Up / Down    Navigate files and directories",
        "  Enter        Open file or enter directory",
        "  Left / BS    Go to parent directory",
        "  SPACE        Toggle multi-select (in multi-picker mode)",
        "  B            Toggle bookmark for selected file",
        "  ?            Show this help panel",
        "  ESC          Cancel",
        "",
        "[ RESULTS VIEW ]",
        "  Up / Down    Scroll one line",
        "  PgUp / PgDn  Scroll one page",
        "  G / End      Jump to bottom",
        "  g / Home     Jump to top",
        "  Enter / ESC  Go back to menu",
        "",
        "[ FILE VIEWER (Raw) ]",
        "  Up / Down    Scroll lines",
        "  PgUp / PgDn  Scroll pages",
        "  G / End      Jump to bottom",
        "  g / Home     Jump to top",
        "  Q / ESC      Back",
        "",
        "[ DIFF VIEWER ]",
        "  Up/Down/PgUp/PgDn  Scroll diff",
        "  Green (+)    Added lines",
        "  Red   (-)    Removed lines",
        "  Cyan  (@@)   Diff chunk header",
        "  Q / ESC      Back",
        "",
        "=== ALL FEATURES ===",
        "",
        "  Git Info              git log/status/blame/diff for current file",
        "  Secret Scanner        find hardcoded passwords, tokens, keys (20+)",
        "  Magic Numbers         find bare numeric literals that need naming",
        "  Security Scan         OWASP-style vulnerability detection (30+ checks)",
        "  Dead Code Detector    find unused functions via Python AST or regex",
        "  Diff Viewer           unified diff vs git HEAD or vs another file",
        "  Multi-File Picker     run syntax + secret checks across N files at once",
        "  Bookmarks             star frequently used files for quick access",
        "  Live Clock            HH:MM:SS always shown top-right in header",
        "  Auto-Detect URLs      test all HTTP/HTTPS links in the file",
        "  Auto-Fuzzer           inject mock args into Python functions",
        "  Speed & Complexity    cyclomatic score + execution timing",
        "  File Statistics       lines / blanks / comments / size",
        "  Structure Scanner     list functions / methods / tags / headings",
        "  Search in File        case-insensitive text search with line numbers",
    ]

    scroll = 0
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        max_vis = max(1, height - 4)

        draw_centered(stdscr, 0, "======  HELP PANEL  ======", color(5) | curses.A_BOLD)
        draw_hline(stdscr, 1)

        for i in range(max_vis):
            li = scroll + i
            if li >= len(help_lines):
                break
            line = help_lines[li]
            y = 2 + i
            if line.startswith("==="):
                safe_addstr(stdscr, y, 2, line[:width - 3], color(5) | curses.A_BOLD)
            elif line.startswith("  [ ") or line.strip().startswith("[ "):
                safe_addstr(stdscr, y, 2, line[:width - 3], color(2) | curses.A_BOLD)
            elif line.strip().startswith("?") or line.strip().startswith("Up") or line.strip().startswith("G /"):
                safe_addstr(stdscr, y, 2, line[:width - 3], color(4))
            else:
                safe_addstr(stdscr, y, 2, line[:width - 3])

        draw_hline(stdscr, height - 2)
        pct = int(scroll / max(1, len(help_lines) - max_vis) * 100) if len(help_lines) > max_vis else 100
        safe_addstr(stdscr, height - 1, 2,
                    "Up/Down/PgUp/PgDn:Scroll  ?/Q:Close  ESC:Exit", color(6))
        safe_addstr(stdscr, height - 1, width - 8, f"[{pct:3d}%]", color(6))
        stdscr.refresh()

        key = smart_getch(stdscr)
        if key == 27:
            sys.exit(0)
        elif key in (ord("q"), ord("Q"), ord("?")):
            break
        elif key == curses.KEY_UP and scroll > 0:
            scroll -= 1
        elif key == curses.KEY_DOWN and scroll < max(0, len(help_lines) - max_vis):
            scroll += 1
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max_vis)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, len(help_lines) - max_vis), scroll + max_vis)
        elif key in (curses.KEY_HOME, ord("g")):
            scroll = 0
        elif key in (curses.KEY_END, ord("G")):
            scroll = max(0, len(help_lines) - max_vis)



# show diff screen
def _show_diff_screen(stdscr, diff_lines: list, title: str):
    scroll = 0
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        max_vis = max(1, height - 4)

        draw_centered(stdscr, 0, title[:width - 2], color(5) | curses.A_BOLD)
        draw_hline(stdscr, 1)

        for i in range(max_vis):
            li = scroll + i
            if li >= len(diff_lines):
                break
            line = diff_lines[li][:max(0, width - 2)]
            y = 2 + i
            if line.startswith("+") and not line.startswith("+++"):
                safe_addstr(stdscr, y, 1, line, color(2) | curses.A_BOLD)
            elif line.startswith("-") and not line.startswith("---"):
                safe_addstr(stdscr, y, 1, line, color(3) | curses.A_BOLD)
            elif line.startswith("@@"):
                safe_addstr(stdscr, y, 1, line, color(5) | curses.A_BOLD)
            elif line.startswith(("---", "+++")):
                safe_addstr(stdscr, y, 1, line, color(6) | curses.A_BOLD)
            else:
                safe_addstr(stdscr, y, 1, line)

        draw_hline(stdscr, height - 2)
        total = len(diff_lines)
        pct = int(scroll / max(1, total - max_vis) * 100) if total > max_vis else 100
        added   = sum(1 for l in diff_lines if l.startswith("+") and not l.startswith("+++"))
        removed = sum(1 for l in diff_lines if l.startswith("-") and not l.startswith("---"))
        summary = f"+{added} / -{removed} lines"
        safe_addstr(stdscr, height - 1, 2, "Up/Down/PgUp/PgDn:Scroll  Q:Back  ESC:Exit", color(6))
        safe_addstr(stdscr, height - 1, width - len(summary) - 10, summary, color(2) | curses.A_BOLD)
        safe_addstr(stdscr, height - 1, width - 8, f"[{pct:3d}%]", color(6))
        stdscr.refresh()

        key = smart_getch(stdscr)
        if key == 27:
            sys.exit(0)
        elif key in (ord("q"), ord("Q")):
            break
        elif key == curses.KEY_UP and scroll > 0:
            scroll -= 1
        elif key == curses.KEY_DOWN and scroll < max(0, total - max_vis):
            scroll += 1
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max_vis)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, total - max_vis), scroll + max_vis)
        elif key in (curses.KEY_HOME, ord("g")):
            scroll = 0
        elif key in (curses.KEY_END, ord("G")):
            scroll = max(0, total - max_vis)


# diff vs git
def _diff_vs_git(stdscr, filepath: str):
    file_dir  = os.path.dirname(os.path.abspath(filepath))
    file_name = os.path.basename(filepath)
    try:
        result = subprocess.run(
            ["git", "show", f"HEAD:{file_name}"],
            cwd=file_dir, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10
        )
        if result.returncode != 0:
            show_results(stdscr, False, "Diff vs Git HEAD", "ERR",
                         "[FAIL] Could not retrieve HEAD version.\n"
                         "[WARN] Is this file tracked and committed to git?")
            return
        old_lines = result.stdout.splitlines(keepends=True)
    except FileNotFoundError:
        show_results(stdscr, False, "Diff vs Git HEAD", "ERR",
                     "[FAIL] git is not installed or not in PATH.")
        return
    except Exception as e:
        show_results(stdscr, False, "Diff vs Git HEAD", "ERR", str(e))
        return

    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            new_lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "Diff vs Git HEAD", "ERR", str(e))
        return

    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"HEAD:{file_name}",
        tofile=f"Working: {file_name}",
        lineterm=""
    ))

    if not diff:
        show_results(stdscr, True, "Diff vs Git HEAD", "DONE",
                     "[ OK ] File matches HEAD -- no differences.")
        return

    _show_diff_screen(stdscr, diff, f"Diff: {file_name}  HEAD <> Working Tree")


# diff two files
def _diff_two_files(stdscr, file_a: str, file_b: str):
    try:
        with open(file_a, "r", encoding="utf-8", errors="replace") as f:
            lines_a = f.readlines()
        with open(file_b, "r", encoding="utf-8", errors="replace") as f:
            lines_b = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "File Diff", "ERR", str(e))
        return

    diff = list(difflib.unified_diff(
        lines_a, lines_b,
        fromfile=os.path.basename(file_a),
        tofile=os.path.basename(file_b),
        lineterm=""
    ))

    if not diff:
        show_results(stdscr, True, "File Diff", "DONE", "[ OK ] The two files are identical!")
        return

    _show_diff_screen(stdscr, diff,
                      f"Diff: {os.path.basename(file_a)}  <vs>  {os.path.basename(file_b)}")


# diff viewer
def diff_viewer(stdscr, filepath: str):
    options = [
        ("Diff vs Git HEAD",     "git"),
        ("Diff vs Another File", "file"),
        ("--- Cancel ---",       "cancel"),
    ]
    current_row = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        draw_centered(stdscr, 1, "DIFF VIEWER", color(5) | curses.A_BOLD)
        draw_hline(stdscr, 2)
        safe_addstr(stdscr, 3, 2, f"  File: {os.path.basename(filepath)}", color(6))
        draw_hline(stdscr, 4)

        for i, (label, _) in enumerate(options):
            attr = (color(1) | curses.A_BOLD) if i == current_row else curses.A_NORMAL
            draw_centered(stdscr, 6 + i * 2, f"  {label}  ", attr)

        safe_addstr(stdscr, height - 2, 2, "Up/Down:Choose  Enter:Select  Q:Back  ESC:Exit", color(6))
        stdscr.refresh()

        key = smart_getch(stdscr)
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(options) - 1:
            current_row += 1
        elif key in (curses.KEY_ENTER, 10, 13):
            action = options[current_row][1]
            if action == "git":
                _diff_vs_git(stdscr, filepath)
            elif action == "file":
                other = select_target_file(stdscr)
                if other:
                    _diff_two_files(stdscr, filepath, other)
            break
        elif key == 27:
            sys.exit(0)
        elif key in (ord('q'), ord('Q')):
            break



# dead code detector
def dead_code_detector(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, "Analysing for Dead Code...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    ext = os.path.splitext(filepath)[1].lower()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        show_results(stdscr, False, "Dead Code Detector", "ERR", str(e))
        return

    out: list = []

    if ext == ".py":
        try:
            tree = _ast_mod.parse(content)
        except SyntaxError as e:
            show_results(stdscr, False, "Dead Code Detector", "ERR",
                         f"[FAIL] Syntax Error: {e}")
            return

        defined: dict = {}
        for node in _ast_mod.walk(tree):
            if isinstance(node, (_ast_mod.FunctionDef, _ast_mod.AsyncFunctionDef)):
                defined[node.name] = node.lineno

        called: set = set()
        for node in _ast_mod.walk(tree):
            if isinstance(node, _ast_mod.Call):
                if isinstance(node.func, _ast_mod.Name):
                    called.add(node.func.id)
                elif isinstance(node.func, _ast_mod.Attribute):
                    called.add(node.func.attr)
            elif isinstance(node, _ast_mod.Name) and isinstance(node.ctx, _ast_mod.Load):
                called.add(node.id)
        for node in _ast_mod.walk(tree):
            if isinstance(node, _ast_mod.Constant) and isinstance(node.value, str):
                called.add(node.value)

        ALWAYS_LIVE = {
            "main", "__init__", "__str__", "__repr__", "__len__", "__eq__",
            "__hash__", "__enter__", "__exit__", "__iter__", "__next__",
            "__call__", "__getitem__", "__setitem__", "__del__", "__contains__",
            "setUp", "tearDown", "setUpClass", "tearDownClass",
            "run", "start", "handle", "execute",
        }
        called |= ALWAYS_LIVE

        dead = [(name, lineno) for name, lineno in defined.items()
                if name not in called]

        out.append("=== DEAD CODE ANALYSIS  (Python AST) ===")
        out.append("")
        out.append(f"[ OK ] Functions defined   : {len(defined)}")
        out.append(f"[ OK ] Functions called    : {len(defined) - len(dead)} / {len(defined)}")
        out.append(f"[ OK ] Possibly unused     : {len(dead)}")
        out.append("")

        if dead:
            out.append("=== POSSIBLY UNUSED FUNCTIONS ===")
            for name, lineno in sorted(dead, key=lambda x: x[1]):
                out.append(f"[WARN] Line {lineno:>4}:  def {name}()")
            out.append("")
            out.append("[WARN] Note: functions called via reflection may show as false positives.")
            out.append("[WARN] Review each entry manually before deletion.")
        else:
            out.append("[ OK ] No obviously dead functions found -- great!")

    else:
        lang_cfg = {
            ".js":  (r"function\s+(\w+)\s*\(|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(",
                     r"\b(\w+)\s*\("),
            ".ts":  (r"function\s+(\w+)\s*\(",    r"\b(\w+)\s*\("),
            ".rb":  (r"def\s+([\w!?]+)",          r"\b([\w!?]+)\s*[\(\.]"),
            ".go":  (r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", r"\b(\w+)\s*\("),
            ".rs":  (r"fn\s+(\w+)\s*[(<]",        r"\b(\w+)\s*[(!<]"),
            ".php": (r"function\s+(\w+)\s*\(",    r"\b(\w+)\s*\("),
            ".kt":  (r"fun\s+(\w+)\s*\(",         r"\b(\w+)\s*\("),
        }

        if ext not in lang_cfg:
            show_results(stdscr, True, "Dead Code Detector", "N/A",
                         f"[WARN] Full dead code analysis is available for Python (.py).\n"
                         f"[ OK ] Basic regex support: .js .ts .rb .go .rs .php .kt\n"
                         f"[WARN] {ext} files are not yet supported.")
            return

        def_pat, call_pat = lang_cfg[ext]
        raw_defs = re.findall(def_pat, content)
        defined_names = []
        for item in raw_defs:
            if isinstance(item, tuple):
                defined_names.extend([g for g in item if g])
            else:
                defined_names.append(item)

        called = set(re.findall(call_pat, content))
        dead_names = [n for n in defined_names if n and n not in called]

        out.append(f"=== DEAD CODE ANALYSIS  (Regex, {ext}) ===")
        out.append("")
        out.append(f"[ OK ] Functions defined   : {len(defined_names)}")
        out.append(f"[ OK ] Possibly unused     : {len(dead_names)}")
        out.append("")
        if dead_names:
            out.append("=== POSSIBLY UNUSED FUNCTIONS ===")
            for name in dead_names[:50]:
                out.append(f"[WARN] Possibly unused:  {name}()")
            if len(dead_names) > 50:
                out.append(f"[WARN] ... and {len(dead_names) - 50} more.")
            out.append("")
            out.append("[WARN] Regex analysis may have false positives.")
        else:
            out.append("[ OK ] No obviously unused functions found.")

    show_results(stdscr, True, "Dead Code Detector", "DONE", "\n".join(out))



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
     "HIGH"),
    ("Hardcoded Password",
     r'(?i)(password|passwd|pwd)\s*=\s*["\'][^"\']{3,}["\']',
     "CRITICAL"),
    ("Hardcoded API Key",
     r'(?i)(api_key|apikey)\s*=\s*["\'][^"\']{6,}["\']',
     "CRITICAL"),
    ("Hardcoded Token",
     r'(?i)(token|secret)\s*=\s*["\'][^"\']{6,}["\']',
     "HIGH"),
    ("AWS Key Exposed",
     r'AKIA[0-9A-Z]{16}',
     "CRITICAL"),
    ("Exposed Private Key",
     r'-----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----',
     "CRITICAL"),
    ("Insecure Deserialization (pickle)",
     r'pickle\.loads?\s*\(',
     "CRITICAL"),
    ("Insecure YAML Load",
     r'yaml\.load\s*\([^)]*\)',
     "HIGH"),
    ("Marshal Deserialization",
     r'marshal\.loads?\s*\(',
     "HIGH"),
    ("Weak Hash -- MD5",
     r'(?i)\bhashlib\.md5\b|\bMD5\s*\(',
     "HIGH"),
    ("Weak Hash -- SHA1",
     r'(?i)\bhashlib\.sha1\b|\bSHA1\s*\(',
     "MEDIUM"),
    ("Weak Cipher -- DES / RC4",
     r'(?i)\b(DES|RC4|Blowfish)\b',
     "HIGH"),
    ("Insecure Random (use secrets module instead)",
     r'(?i)\brandom\.(random|randint|randrange|choice)\b',
     "LOW"),
    ("XSS -- innerHTML",
     r'\.innerHTML\s*=',
     "HIGH"),
    ("XSS -- document.write",
     r'document\.write\s*\(',
     "HIGH"),
    ("XSS -- dangerouslySetInnerHTML",
     r'dangerouslySetInnerHTML',
     "HIGH"),
    ("Path Traversal (../)",
     r'(\.\./|\.\.\\)',
     "HIGH"),
    ("Debug Mode Enabled",
     r'(?i)\bDEBUG\s*=\s*True',
     "HIGH"),
    ("Flask Debug Mode",
     r'(?i)app\.run\s*\([^\)]*debug\s*=\s*True',
     "HIGH"),
    ("Stack Trace Exposed",
     r'traceback\.(print_exc|print_exception)',
     "MEDIUM"),
    ("XXE Risk -- xml.etree",
     r'xml\.etree\.ElementTree\.(parse|fromstring)',
     "MEDIUM"),
    ("XXE Risk -- lxml",
     r'lxml\.etree\.(parse|fromstring)',
     "MEDIUM"),
    ("Open Redirect",
     r'(?i)redirect\s*\(\s*request\.(args|form|values|get|POST|GET)',
     "HIGH"),
    ("SSRF Risk",
     r'(?i)requests?\.(get|post|put|delete)\s*\([^\)]*\+[^\)]*\)',
     "HIGH"),
    ("Insecure Temp File (race condition risk)",
     r'(?i)tempfile\.mktemp\s*\(',
     "MEDIUM"),
    ("Timing Attack Risk",
     r'(?i)(password|token|secret|hmac)\s*==\s*',
     "MEDIUM"),
    ("Hardcoded IP Address",
     r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b',
     "LOW"),
]


# OWASP Top-10 style static security vulnerability scanner
def security_scan(stdscr, filepath: str):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2,
                  "Running Security Vulnerability Scan...",
                  color(7) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        show_results(stdscr, False, "Security Scan", "ERR", str(e))
        return

    findings: list = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--", "--")):
            continue
        for vuln_type, pattern, severity in _VULN_PATTERNS:
            if re.search(pattern, line):
                findings.append((i, vuln_type, severity, stripped[:72]))

    _order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    findings.sort(key=lambda x: (_order.get(x[2], 9), x[0]))

    critical = [f for f in findings if f[2] == "CRITICAL"]
    high     = [f for f in findings if f[2] == "HIGH"]
    medium   = [f for f in findings if f[2] == "MEDIUM"]
    low      = [f for f in findings if f[2] == "LOW"]

    out: list = ["=== SECURITY VULNERABILITY SCAN  (OWASP Top-10 Style) ===", ""]

    if not findings:
        out.append("[ OK ] No obvious vulnerabilities detected.")
        out.append("[ OK ] Scan covered: SQLi, CMDi, XSS, secrets, weak crypto,")
        out.append("[ OK ]              SSRF, deserialization, path traversal, XXE,")
        out.append("[ OK ]              open redirect, timing attacks, debug mode")
        out.append("")
        out.append("[ OK ] Always follow up with a manual security review.")
    else:
        out.append(f"[FAIL] Found {len(findings)} potential issue(s) across {len(set(f[0] for f in findings))} line(s):")
        out.append(f"[FAIL]   CRITICAL : {len(critical)}")
        out.append(f"[WARN]   HIGH     : {len(high)}")
        out.append(f"[WARN]   MEDIUM   : {len(medium)}")
        out.append(f"[ OK ]   LOW      : {len(low)}")
        out.append("")

        sev_tag = {"CRITICAL": "[FAIL]", "HIGH": "[WARN]", "MEDIUM": "[WARN]", "LOW": "[ OK ]"}
        for sev_label in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            group = [f for f in findings if f[2] == sev_label]
            if not group:
                continue
            out.append(f"=== {sev_label} ===")
            for lineno, vuln_type, severity, ctx in group:
                tag = sev_tag.get(severity, "[WARN]")
                out.append(f"{tag} Line {lineno:>4}:  [{severity}]  {vuln_type}")
                out.append(f"         {ctx}")
            out.append("")

        if critical:
            out.append("[FAIL] CRITICAL vulnerabilities found -- this code may be exploitable!")
        elif high:
            out.append("[WARN] HIGH severity issues found. Fix before deploying to production.")
        out.append("[WARN] Static analysis only. Always perform a manual security audit.")

    is_safe = len(critical) == 0 and len(high) == 0
    show_results(stdscr, is_safe,
                 f"Security Scan -- {len(findings)} issue(s) found",
                 "DONE", "\n".join(out))





# Paginated results viewer with syntax-colored output prefixes
def show_results(stdscr, success: bool, target: str, status_code, output_text: str):
    neutral_targets = ["File Statistics", "Search", "File Viewer", "Structure Scanner", "Copy Path", "Diff", "Read File Error"]
    is_neutral = any(target.startswith(n) for n in neutral_targets)

    if is_neutral:
        trigger_emotion("neutral", duration=4.0, suggestion="Here you go.")
    elif success:
        trigger_emotion("surprise", duration=4.0, suggestion="All good! Great job!")
    else:
        trigger_emotion("angry", duration=4.0, suggestion="Found some issues here...")

    lines = output_text.strip().splitlines() if output_text else ["(No output returned)"]
    scroll = 0

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        status_msg = (f"  [ OK ] SUCCESS  (exit: {status_code})" if success
                      else f"  [FAIL] FAILED   (exit: {status_code})")
        hdr_attr = color(2) | curses.A_BOLD if success else color(3) | curses.A_BOLD
        safe_addstr(stdscr, 0, 0, " " * (width - 1), hdr_attr)
        safe_addstr(stdscr, 0, 0, status_msg[:width - 1], hdr_attr)
        safe_addstr(stdscr, 1, 2, f"Target : {target}"[:width - 3])
        draw_hline(stdscr, 2)
        safe_addstr(stdscr, 3, 2, "--- Output ---", curses.A_BOLD)

        max_vis = max(1, height - 7)
        for i in range(max_vis):
            li = scroll + i
            if li >= len(lines):
                break
            raw = lines[li][:max(0, width - 4)]
            y   = 4 + i
            try:
                if curses.has_colors():
                    if raw.startswith("[ OK ]"):
                        safe_addstr(stdscr, y, 2, "[ OK ]", color(2) | curses.A_BOLD)
                        safe_addstr(stdscr, y, 8, raw[6:])
                    elif raw.startswith(("[FAIL]", "[ERR ]")):
                        safe_addstr(stdscr, y, 2, raw[:6], color(3) | curses.A_BOLD)
                        safe_addstr(stdscr, y, 8, raw[6:])
                    elif raw.startswith(("[WARN]", "[SKIP]", "[...]")):
                        safe_addstr(stdscr, y, 2, raw[:6], color(4) | curses.A_BOLD)
                        safe_addstr(stdscr, y, 8, raw[6:])
                    elif raw.startswith("==="):
                        safe_addstr(stdscr, y, 2, raw, color(5) | curses.A_BOLD)
                    elif raw.startswith("--"):
                        safe_addstr(stdscr, y, 2, raw, color(6) | curses.A_BOLD)
                    else:
                        safe_addstr(stdscr, y, 2, raw)
                else:
                    safe_addstr(stdscr, y, 2, raw)
            except curses.error:
                pass

        if len(lines) > max_vis:
            pct = int(scroll / max(1, len(lines) - max_vis) * 100)
            draw_hline(stdscr, height - 3)
            safe_addstr(stdscr, height - 3, width - 8, f"[{pct:3d}%]", color(6))

        draw_hline(stdscr, height - 2)
        safe_addstr(stdscr, height - 1, 2,
                    "Up/Down/PgUp/PgDn:Scroll  Enter/Q:Back  ?:Help  ESC:Exit", color(6))
        stdscr.refresh()

        key = smart_getch(stdscr)
        if key == 27:
            sys.exit(0)
        elif key in (curses.KEY_ENTER, 10, 13, ord("q"), ord("Q")):
            break
        elif key == ord("?"):
            show_help_panel(stdscr)
        elif key == curses.KEY_UP and scroll > 0:
            scroll -= 1
        elif key == curses.KEY_DOWN and scroll < max(0, len(lines) - max_vis):
            scroll += 1
        elif key == curses.KEY_PPAGE:
            scroll = max(0, scroll - max_vis)
        elif key == curses.KEY_NPAGE:
            scroll = min(max(0, len(lines) - max_vis), scroll + max_vis)
        elif key in (curses.KEY_HOME, ord("g")):
            scroll = 0
        elif key in (curses.KEY_END, ord("G")):
            scroll = max(0, len(lines) - max_vis)
        elif key == curses.KEY_RESIZE:
            pass



# Return True if a CLI tool is on PATH
def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


# Install a pip package if not present. Returns True on success
def _pip_install(stdscr, package: str, check_cmd: str) -> bool:
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2,
                  f"Installing {package} via pip...",
                  color(5) | curses.A_BOLD)
    stdscr.refresh()
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package, "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        return result.returncode == 0
    except Exception:
        return False


# Run bandit on filepath. Returns (critical, high, medium, low, output_lines)
def _run_bandit(stdscr, filepath: str) -> tuple:
    out: list = []
    if not _tool_available("bandit"):
        draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                      "bandit not found -- installing...", color(4) | curses.A_BOLD)
        stdscr.refresh()
        ok = _pip_install(stdscr, "bandit", "bandit")
        if not ok:
            return 0, 0, 0, 0, ["[WARN] bandit: could not install (pip failed)."]

    draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                  "Running bandit...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "bandit", "-r", filepath, "-f", "text", "-ll"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
        raw = (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return 0, 0, 0, 0, ["[WARN] bandit: timed out after 60s."]
    except Exception as e:
        return 0, 0, 0, 0, [f"[WARN] bandit: {e}"]

    critical = high = medium = low = 0
    for line in raw.splitlines():
        ll = line.lower()
        if "severity: high" in ll:     high += 1
        elif "severity: medium" in ll: medium += 1
        elif "severity: low" in ll:    low += 1

    out.append("=== BANDIT RESULTS ===")
    if not raw or "no issues identified" in raw.lower():
        out.append("[ OK ] bandit: No issues found.")
    else:
        if high:   out.append(f"[FAIL] bandit: {high} HIGH severity issue(s)")
        if medium: out.append(f"[WARN] bandit: {medium} MEDIUM severity issue(s)")
        if low:    out.append(f"[ OK ] bandit: {low} LOW severity issue(s)")
        out.append("")
        for line in raw.splitlines()[:30]:
            if line.strip():
                if "severity: high" in line.lower():
                    out.append(f"[FAIL] {line.strip()[:80]}")
                elif "severity: medium" in line.lower():
                    out.append(f"[WARN] {line.strip()[:80]}")
                else:
                    out.append(f"[ OK ] {line.strip()[:80]}")
        if len(raw.splitlines()) > 30:
            out.append(f"[WARN] ... and {len(raw.splitlines()) - 30} more lines (run bandit manually for full output)")

    return critical, high, medium, low, out


# Run semgrep on filepath with auto ruleset. Returns (critical, high, medium, low, output_lines)
def _run_semgrep(stdscr, filepath: str) -> tuple:
    out: list = []
    if not _tool_available("semgrep"):
        draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                      "semgrep not found -- installing...", color(4) | curses.A_BOLD)
        stdscr.refresh()
        ok = _pip_install(stdscr, "semgrep", "semgrep")
        if not ok:
            return 0, 0, 0, 0, ["[WARN] semgrep: could not install (pip failed)."]

    draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                  "Running semgrep (auto rules)...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        result = subprocess.run(
            ["semgrep", "--config=auto", filepath,
             "--text", "--no-rewrite-rule-ids", "--quiet"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
        )
        raw = (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return 0, 0, 0, 0, ["[WARN] semgrep: timed out after 120s."]
    except FileNotFoundError:
        try:
            result = subprocess.run(
                [sys.executable, "-m", "semgrep", "--config=p/security-audit",
                 filepath, "--text", "--quiet"],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
            )
            raw = (result.stdout + result.stderr).strip()
        except Exception as e:
            return 0, 0, 0, 0, [f"[WARN] semgrep: {e}"]
    except Exception as e:
        return 0, 0, 0, 0, [f"[WARN] semgrep: {e}"]

    finding_lines = [l for l in raw.splitlines() if filepath.replace("\\", "/") in l or ">" in l]
    total_findings = len([l for l in raw.splitlines() if l.strip().startswith(">")])
    high   = total_findings
    medium = low = critical = 0

    has_issues = ("findings" in raw.lower() and "0 findings" not in raw.lower()) \
                  or total_findings > 0

    out.append("=== SEMGREP RESULTS ===")
    if not has_issues or not raw:
        out.append("[ OK ] semgrep: No security findings.")
        high = 0
    else:
        out.append(f"[WARN] semgrep: {total_findings} finding(s) detected")
        out.append("")
        for line in raw.splitlines()[:35]:
            if line.strip():
                tag = "[WARN]" if ">" in line else "[ OK ]"
                out.append(f"{tag} {line.strip()[:80]}")
        if len(raw.splitlines()) > 35:
            out.append(f"[WARN] ... and {len(raw.splitlines()) - 35} more lines")

    return critical, high, medium, low, out


# Run safety check on requirements.txt / pyproject.toml in the same directory
def _run_safety(stdscr, filepath: str) -> tuple:
    out: list = []
    file_dir = os.path.dirname(os.path.abspath(filepath))

    req_candidates = [
        os.path.join(file_dir, "requirements.txt"),
        os.path.join(file_dir, "requirements-dev.txt"),
        os.path.join(file_dir, "pyproject.toml"),
    ]
    req_file = next((r for r in req_candidates if os.path.exists(r)), None)

    if not req_file:
        return 0, 0, 0, 0, [
            "[WARN] safety: No requirements.txt or pyproject.toml found in project directory.",
            "[WARN] safety: Create requirements.txt to check for vulnerable dependencies."
        ]

    if not _tool_available("safety"):
        draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                      "safety not found -- installing...", color(4) | curses.A_BOLD)
        stdscr.refresh()
        ok = _pip_install(stdscr, "safety", "safety")
        if not ok:
            return 0, 0, 0, 0, ["[WARN] safety: could not install (pip failed)."]

    draw_centered(stdscr, stdscr.getmaxyx()[0] // 2,
                  f"Running safety on {os.path.basename(req_file)}...",
                  color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        result = subprocess.run(
            [sys.executable, "-m", "safety", "check",
             "-r", req_file, "--output", "text"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60
        )
        raw = (result.stdout + result.stderr).strip()
    except subprocess.TimeoutExpired:
        return 0, 0, 0, 0, ["[WARN] safety: timed out after 60s."]
    except Exception as e:
        return 0, 0, 0, 0, [f"[WARN] safety: {e}"]

    vuln_count = raw.lower().count("vulnerability found")
    if "no known security" in raw.lower() or result.returncode == 0:
        vuln_count = 0

    out.append("=== SAFETY (Dependency Vulnerabilities) ===")
    out.append(f"[ OK ] Checked: {os.path.basename(req_file)}")
    if vuln_count == 0:
        out.append("[ OK ] safety: No known vulnerable dependencies found!")
    else:
        out.append(f"[FAIL] safety: {vuln_count} vulnerable dependency/dependencies found!")
        out.append("")
        for line in raw.splitlines()[:25]:
            if line.strip():
                tag = "[FAIL]" if "vulnerability" in line.lower() else "[ OK ]"
                out.append(f"{tag} {line.strip()[:80]}")

    return 0, vuln_count, 0, 0, out


# Full penetration test pipeline:
def run_pentest(stdscr, filepath: str):
    ext = os.path.splitext(filepath)[1].lower()
    is_python = ext == ".py"

    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2 - 2,
                  "FULL PENETRATION TEST", color(7) | curses.A_BOLD)
    draw_centered(stdscr, height // 2,
                  "Initialising tools...", color(5) | curses.A_BOLD)
    draw_centered(stdscr, height // 2 + 2,
                  "This may take a moment on first run.", color(6))
    stdscr.refresh()
    time.sleep(0.8)

    all_out: list = [
        "=== FULL PENETRATION TEST REPORT ===",
        f"[ OK ] Target file : {os.path.basename(filepath)}",
        f"[ OK ] Started at  : {datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}",
        ""
    ]

    total_critical = total_high = total_medium = total_low = 0

    stdscr.clear()
    draw_centered(stdscr, height // 2, "Phase 1/4 -- Built-in OWASP scan...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        all_out.append(f"[FAIL] Could not read file: {e}")
        lines = []

    owasp_findings: list = []
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(("#", "//", "/*", "*", "<!--", "--")):
            continue
        for vuln_type, pattern, severity in _VULN_PATTERNS:
            if re.search(pattern, line):
                owasp_findings.append((i, vuln_type, severity, stripped[:70]))

    _sev_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    owasp_findings.sort(key=lambda x: (_sev_order.get(x[2], 9), x[0]))

    o_crit = len([f for f in owasp_findings if f[2] == "CRITICAL"])
    o_high = len([f for f in owasp_findings if f[2] == "HIGH"])
    o_med  = len([f for f in owasp_findings if f[2] == "MEDIUM"])
    o_low  = len([f for f in owasp_findings if f[2] == "LOW"])
    total_critical += o_crit
    total_high     += o_high
    total_medium   += o_med
    total_low      += o_low

    all_out.append("=== Phase 1: Built-in OWASP Scan ===")
    if not owasp_findings:
        all_out.append("[ OK ] No OWASP vulnerability patterns found.")
    else:
        all_out.append(f"[FAIL] CRITICAL: {o_crit}  HIGH: {o_high}  MEDIUM: {o_med}  LOW: {o_low}")
        _sev_tag = {"CRITICAL": "[FAIL]", "HIGH": "[WARN]", "MEDIUM": "[WARN]", "LOW": "[ OK ]"}
        for lineno, vuln_type, severity, ctx in owasp_findings[:20]:
            tag = _sev_tag.get(severity, "[WARN]")
            all_out.append(f"{tag} L{lineno:<4} [{severity}] {vuln_type}")
            all_out.append(f"       {ctx}")
        if len(owasp_findings) > 20:
            all_out.append(f"[WARN] ... and {len(owasp_findings) - 20} more issues.")
    all_out.append("")

    all_out.append("=== Phase 2: Bandit (Python Deep Scan) ===")
    if is_python:
        stdscr.clear()
        draw_centered(stdscr, height // 2,
                      "Phase 2/4 -- Running Bandit...", color(5) | curses.A_BOLD)
        stdscr.refresh()
        b_c, b_h, b_m, b_l, b_out = _run_bandit(stdscr, filepath)
        total_critical += b_c
        total_high     += b_h
        total_medium   += b_m
        total_low      += b_l
        all_out.extend(b_out)
    else:
        all_out.append(f"[WARN] Bandit only supports Python files. Skipped for {ext}.")
    all_out.append("")

    all_out.append("=== Phase 3: Semgrep (Multi-Language Rules) ===")
    stdscr.clear()
    draw_centered(stdscr, height // 2,
                  "Phase 3/4 -- Running Semgrep...", color(5) | curses.A_BOLD)
    stdscr.refresh()
    s_c, s_h, s_m, s_l, s_out = _run_semgrep(stdscr, filepath)
    total_critical += s_c
    total_high     += s_h
    total_medium   += s_m
    total_low      += s_l
    all_out.extend(s_out)
    all_out.append("")

    all_out.append("=== Phase 4: Safety (Dependency CVE Check) ===")
    if is_python:
        stdscr.clear()
        draw_centered(stdscr, height // 2,
                      "Phase 4/4 -- Running Safety...", color(5) | curses.A_BOLD)
        stdscr.refresh()
        sf_c, sf_h, sf_m, sf_l, sf_out = _run_safety(stdscr, filepath)
        total_critical += sf_c
        total_high     += sf_h
        all_out.extend(sf_out)
    else:
        all_out.append(f"[WARN] Safety checks Python dependencies only. Skipped for {ext}.")
    all_out.append("")

    all_out.append("=" * 50)
    all_out.append("=== FINAL VERDICT ===")
    all_out.append("=" * 50)
    all_out.append("")
    all_out.append(f"[ OK ] CRITICAL issues : {total_critical}")
    all_out.append(f"[ OK ] HIGH issues     : {total_high}")
    all_out.append(f"[ OK ] MEDIUM issues   : {total_medium}")
    all_out.append(f"[ OK ] LOW issues      : {total_low}")
    all_out.append("")

    if total_critical == 0 and total_high == 0 and total_medium == 0:
        verdict = "HACKPROOF"
        all_out.append("[ OK ] ==========================================")
        all_out.append("[ OK ]   VERDICT: HACKPROOF  -- No major issues!")
        all_out.append("[ OK ] ==========================================")
        all_out.append("")
        all_out.append("[ OK ] Your code passed all security checks.")
        all_out.append("[ OK ] Only LOW-level informational findings.")
        all_out.append("[ OK ] Keep following secure coding practices!")
        is_safe = True
    elif total_critical > 0:
        verdict = "CRITICAL RISK -- NOT HACKPROOF"
        all_out.append("[FAIL] =========================================")
        all_out.append("[FAIL]   VERDICT: CRITICAL RISK                ")
        all_out.append("[FAIL]   THIS CODE IS HACKABLE!                ")
        all_out.append("[FAIL] =========================================")
        all_out.append("")
        all_out.append(f"[FAIL] {total_critical} CRITICAL vulnerability/vulnerabilities found!")
        all_out.append("[FAIL] An attacker can likely exploit these directly.")
        all_out.append("[WARN] Fix ALL CRITICAL issues before deploying.")
        is_safe = False
        record_error()
    elif total_high > 0:
        verdict = "HIGH RISK -- LIKELY HACKABLE"
        all_out.append("[WARN] =========================================")
        all_out.append("[WARN]   VERDICT: HIGH RISK                    ")
        all_out.append("[WARN]   CODE MAY BE EXPLOITABLE               ")
        all_out.append("[WARN] =========================================")
        all_out.append("")
        all_out.append(f"[WARN] {total_high} HIGH severity issue(s) found.")
        all_out.append("[WARN] These are serious issues requiring immediate attention.")
        all_out.append("[WARN] Do not deploy to production until resolved.")
        is_safe = False
    else:
        verdict = "LOW RISK -- MOSTLY SECURE"
        all_out.append("[WARN] =========================================")
        all_out.append("[WARN]   VERDICT: LOW RISK                     ")
        all_out.append("[WARN]   Generally secure with minor concerns   ")
        all_out.append("[WARN] =========================================")
        all_out.append("")
        all_out.append(f"[WARN] {total_medium} MEDIUM + {total_low} LOW issues found.")
        all_out.append("[WARN] Review medium issues before production deployment.")
        is_safe = True

    all_out.append("")
    all_out.append("[ OK ] Tools used: Built-in OWASP + Bandit + Semgrep + Safety")
    all_out.append("[WARN] Note: No automated tool catches 100%% of vulnerabilities.")
    all_out.append("[WARN] Always combine with manual code review and penetration testing.")

    show_results(stdscr, is_safe, f"Full Pentest -- {verdict}", "DONE",
                 "\n".join(all_out))



# draw companion face
def draw_companion_face(stdscr):
    height, width = stdscr.getmaxyx()
    if height < 20: return

    faces = {
        "happy": [
            " (\_/) ",
            " (^.^) ",
            " >   < "
        ],
        "sad": [
            " (\_/) ",
            " (T.T) ",
            " >   < "
        ],
        "angry": [
            " (\__/) ",
            " (◣_◢) ",
            "  >  <  "
        ],
        "neutral": [
            " (\_/) ",
            " (-.-) ",
            " >   < "
        ],
        "surprise": [
            " (\_/) ",
            " (o.o) ",
            " >   < "
        ],
        "tired": [
            " (\_/) ",
            " (-.-) ",
            " >   < "
        ],
        "error": [
            " (\_/) ",
            " (x_x) ",
            " >   < "
        ],
        "unknown": [
            " (\_/) ",
            " (?.?) ",
            " >   < "
        ]
    }

    emo = CURRENT_EMOTION.lower()
    if emo in ['fear', 'disgust']: emo = 'sad'
    if emo not in faces: emo = 'unknown'

    now = time.time()
    if emo == 'happy' and (int(now * 10) % 20) < 5:
        face_art = faces["neutral"]
    else:
        face_art = faces[emo]

    for j in range(1, 6):
        safe_addstr(stdscr, j, 0, " " * (width - 1))

    for i, line in enumerate(face_art):
        draw_centered(stdscr, 1 + i, line, color(5) | curses.A_BOLD)

    draw_centered(stdscr, 5, " " * (width - 1))
    if CURRENT_SUGGESTION:
        draw_centered(stdscr, 5, f"[{CURRENT_SUGGESTION}]", color(4) | curses.A_BOLD)
    draw_hline(stdscr, 6)



# Construct the three-panel main menu for the given file (or batch list)
def build_menu(filepath) -> list:
    if isinstance(filepath, list):
        lang_items = [{"name": f"Run Universal Syntax & Connection Check", "action": "multibatch", "cmd": None}]
    else:
        lang_items = get_commands_for_file(filepath)
    if lang_items:
        lang_items.append({"name": "-" * 32, "action": "separator", "cmd": None})
    lang_items.append({"name": "<-- Back to Main Menu", "action": "back", "cmd": None})

    gen_items = [
        {"name": "Auto-Detect & Test URLs",        "action": "api",        "cmd": filepath},
        {"name": "File Statistics",                "action": "stats",      "cmd": filepath},
        {"name": "View Raw File",                  "action": "view",       "cmd": filepath},
        {"name": "Search in File",                 "action": "search",     "cmd": filepath},
        {"name": "Copy Path to Clipboard",         "action": "copy",       "cmd": filepath},
        {"name": "-" * 32,                        "action": "separator",  "cmd": None},
        {"name": "<-- Back to Main Menu",          "action": "back",       "cmd": None},
    ]

    sec_items = [
        {"name": "[*] Git Command Center",           "action": "git",       "cmd": filepath},
        {"name": "[*] Scan for Hardcoded Secrets", "action": "secrets",    "cmd": filepath},
        {"name": "[*] Detect Magic Numbers",       "action": "magic",      "cmd": filepath},
        {"name": "[*] Dead Code Detector",         "action": "deadcode",   "cmd": filepath},
        {"name": "[*] Diff Viewer  (git / file)",  "action": "diff",       "cmd": filepath},
        {"name": "[*] Security Vulnerability Scan","action": "security",   "cmd": filepath},
        {"name": "[*] Multi-File Batch Checker",   "action": "multibatch", "cmd": None},
        {"name": "[*] FULL PENTEST  (Hackproof?)",  "action": "pentest",    "cmd": filepath},
        {"name": "-" * 32,                        "action": "separator",  "cmd": None},
        {"name": "<-- Back to Main Menu",          "action": "back",       "cmd": None},
    ]

    main_menu = [
        {"name": "Language / Execution Tools",     "action": "submenu",    "items": lang_items},
        {"name": "General File Tools",             "action": "submenu",    "items": gen_items},
        {"name": "Advanced Analysis & Security",   "action": "submenu",    "items": sec_items},
        {"name": "-" * 32,                        "action": "separator",  "cmd": None},
        {"name": "Select Different File",          "action": "file",       "cmd": None},
        {"name": "Help  (?)",                      "action": "help",       "cmd": None},
        {"name": "Exit",                           "action": "exit",       "cmd": None},
    ]
    return main_menu


# analyze file integrity
def _analyze_file_integrity(filepath: str) -> tuple:
    ext = os.path.splitext(filepath)[1].lower()
    base_dir = os.path.dirname(filepath)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return True, ""

    errors = []

    if ext == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            return False, f"JSON Error"

    links_to_check = []
    if ext in (".html", ".htm"):
        links_to_check.extend(re.findall(r'(?:src|href)\s*=\s*["\']([^"\'>]+)["\']', content, re.IGNORECASE))
    elif ext == ".css":
        links_to_check.extend(re.findall(r'url\s*\(\s*["\']?([^"\'\)]+)["\']?\s*\)', content, re.IGNORECASE))
        links_to_check.extend(re.findall(r'@import\s+["\']([^"\']+)["\']', content, re.IGNORECASE))
    elif ext in (".js", ".ts", ".jsx", ".tsx"):
        links_to_check.extend(re.findall(r'from\s+["\']([^"\']+)["\']', content))
        links_to_check.extend(re.findall(r'require\s*\(\s*["\']([^"\']+)["\']\s*\)', content))

    for link in links_to_check:
        if link.startswith("http://") or link.startswith("https://") or link.startswith("data:") or link.startswith("#"):
            continue

        clean_link = link.split("?")[0].split("#")[0]
        if not clean_link:
            continue

        target_path = os.path.join(base_dir, clean_link)
        if ext in (".js", ".ts", ".jsx", ".tsx") and not os.path.exists(target_path):
            if os.path.exists(target_path + ".js") or os.path.exists(target_path + ".ts"):
                continue

        if not os.path.exists(target_path):
            errors.append(clean_link)

    if errors:
        return False, f"Broken links: {', '.join(errors[:2])}" + ("..." if len(errors)>2 else "")

    return True, ""


# run multi file check
def _run_multi_file_check(stdscr, files):
    stdscr.clear()
    height, width = stdscr.getmaxyx()
    draw_centered(stdscr, height // 2, f"Analyzing {len(files)} files...", color(5) | curses.A_BOLD)
    stdscr.refresh()

    results = []
    all_success = True
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        cmd = None
        if ext == ".py":
            cmd = f'python -m py_compile "{f}"'
        elif ext == ".js":
            cmd = f'node --check "{f}"'
        elif ext == ".php":
            cmd = f'php -l "{f}"'

        file_ok = True
        err_msg = ""

        if cmd:
            try:
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    file_ok = False
                    err_msg = "Syntax Error"
            except Exception:
                file_ok = False
                err_msg = "Command failed"

        if file_ok:
            conn_ok, conn_err = _analyze_file_integrity(f)
            if not conn_ok:
                file_ok = False
                err_msg = conn_err

        if file_ok:
            results.append(f"[ OK ] {os.path.basename(f)}")
        else:
            results.append(f"[FAIL] {os.path.basename(f)} ({err_msg})")
            all_success = False

    summary = "\n".join(results)
    show_results(stdscr, all_success, f"Batch Checked {len(files)} files",
                 0 if all_success else 1, summary)

# multi file checker
def multi_file_checker(stdscr):
    files = select_target_file(stdscr, multi_select=True)
    if not files:
        return
    if isinstance(files, str):
        files = [files]
    _run_multi_file_check(stdscr, files)



# main
def main(stdscr):
    global GLOBAL_STDSCR
    GLOBAL_STDSCR = stdscr

    height, width = stdscr.getmaxyx()
    app_win = stdscr.subwin(max(1, height - 7), width, 7, 0)
    app_win.keypad(True)

    if curses.has_colors():
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_BLACK,   curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_GREEN,   -1)
        curses.init_pair(3, curses.COLOR_RED,     -1)
        curses.init_pair(4, curses.COLOR_YELLOW,  -1)
        curses.init_pair(5, curses.COLOR_CYAN,    -1)
        curses.init_pair(6, curses.COLOR_BLUE,    -1)
        curses.init_pair(7, curses.COLOR_MAGENTA, -1)

    curses.curs_set(0)
    app_win.keypad(True)
    app_win.timeout(1000)

    target_filepath = None
    if len(sys.argv) > 1:
        arg = os.path.abspath(sys.argv[1])
        if os.path.isfile(arg):
            target_filepath = arg

    while True:
        if not target_filepath:
            target_filepath = select_target_file(app_win)

        if not target_filepath:
            return


        break

    main_menu   = build_menu(target_filepath)
    menu_stack  = [main_menu]
    current_row = 0
    bookmarks   = load_bookmarks()

    while True:
        menu = menu_stack[-1]
        app_win.clear()
        height, width = app_win.getmaxyx()


        banner = "TERMINAL CLOCK -- "
        draw_centered(app_win, 1, banner, color(5) | curses.A_BOLD)

        clock_str = datetime.datetime.now().strftime("__%H:%M:%S")
        safe_addstr(app_win, 1, width - len(clock_str) - 2, clock_str, color(4) | curses.A_BOLD)

        draw_hline(app_win, 2)

        if isinstance(target_filepath, list):
            fname = f"Batch: {len(target_filepath)} files"
            fdir  = "Multi-Select"
            icon  = "[B]"
            is_bm = False
        else:
            fname = os.path.basename(target_filepath)
            fdir  = os.path.dirname(target_filepath)
            icon  = _file_icon(fname)
            is_bm = target_filepath in bookmarks
        bm_indicator = " [*]" if is_bm else ""

        safe_addstr(app_win, 3, 2, f"  {icon}  {fname}{bm_indicator}  ", color(5))
        dir_display = fdir if len(fdir) < width - 6 else "..." + fdir[-(width - 9):]
        safe_addstr(app_win, 3, len(fname) + 3 + len(bm_indicator), f"  ({dir_display})", color(6))
        draw_hline(app_win, 4)

        safe_addstr(app_win, height - 2, 2,
                    "Up/Down:Nav  Enter:Run  B:Bookmark  ?:Help  Q:Back  ESC:Exit", color(6))
        draw_hline(app_win, height - 3)

        selectable = [i for i, m in enumerate(menu) if m["action"] != "separator"]
        if current_row not in selectable and selectable:
            current_row = selectable[0]

        max_menu_h = height - 9
        vis_start = 0
        if len(menu) > max_menu_h:
            vis_start = max(0, min(current_row - max_menu_h // 2,
                                   len(menu) - max_menu_h))
        vis_end = vis_start + max_menu_h

        start_y = 5
        for idx in range(vis_start, min(vis_end, len(menu))):
            item = menu[idx]
            y    = start_y + (idx - vis_start)
            if y >= height - 3:
                break

            if item["action"] == "separator":
                draw_centered(app_win, y, item["name"], color(6))
                continue

            display = f"  {item['name']}  "
            if idx == current_row:
                attr = color(1) | curses.A_BOLD
            elif item["name"].startswith("[*]"):
                attr = curses.A_NORMAL
            else:
                attr = curses.A_NORMAL
            draw_centered(app_win, y, display, attr)

        app_win.refresh()
        key = smart_getch(app_win)

        if key == -1:
            continue


        if key == curses.KEY_UP:
            prev_sel = [i for i in selectable if i < current_row]
            if prev_sel:
                current_row = prev_sel[-1]

        elif key == curses.KEY_DOWN:
            next_sel = [i for i in selectable if i > current_row]
            if next_sel:
                current_row = next_sel[0]

        elif key == ord("?"):
            show_help_panel(app_win)

        elif key in (ord("b"), ord("B")):
            if not isinstance(target_filepath, list):
                if target_filepath in bookmarks:
                    bookmarks.remove(target_filepath)
                else:
                    bookmarks.append(target_filepath)
                save_bookmarks(bookmarks)

        elif key == 27:
            sys.exit(0)

        elif key in (ord('q'), ord('Q')):
            if len(menu_stack) > 1:
                menu_stack.pop()
                current_row = 0
            else:
                new_file = select_target_file(app_win)
                if new_file:
                    target_filepath = new_file
                    main_menu = build_menu(target_filepath)
                    menu_stack = [main_menu]
                    current_row = 0
                    bookmarks = load_bookmarks()

        elif key in (curses.KEY_ENTER, 10, 13):
            if current_row not in selectable:
                continue

            item   = menu[current_row]
            action = item["action"]

            if action == "exit":
                break
            elif action == "submenu":
                menu_stack.append(item["items"])
                current_row = 0
                continue
            elif action == "back":
                if len(menu_stack) > 1:
                    menu_stack.pop()
                current_row = 0
                continue
            elif action == "file":
                new_file = select_target_file(app_win)
                if new_file:
                    target_filepath = new_file
                    main_menu = build_menu(target_filepath)
                    menu_stack = [main_menu]
                    current_row = 0
                    bookmarks = load_bookmarks()
            elif action == "help":
                show_help_panel(app_win)
            cmd = item.get("cmd")
            # Map an action string to the right feature function
            def _execute_action(scmd, sfile):
                if action == "api": auto_check_apis(app_win, scmd)
                elif action == "fuzz": auto_fuzz_functions(app_win, scmd)
                elif action == "scan": scan_functions(app_win, scmd)
                elif action == "complexity": run_complexity_analysis(app_win, item.get("file", sfile), scmd)
                elif action == "code": execute_command(app_win, scmd)
                elif action == "stats": show_file_stats(app_win, scmd)
                elif action == "view": view_raw_file(app_win, scmd)
                elif action == "search": search_in_file(app_win, scmd)
                elif action == "copy": copy_path_to_clipboard(app_win, scmd)
                elif action == "git": git_command_center(app_win, scmd)
                elif action == "secrets": scan_secrets(app_win, scmd)
                elif action == "magic": detect_magic_numbers(app_win, scmd)
                elif action == "deadcode": dead_code_detector(app_win, scmd)
                elif action == "diff": diff_viewer(app_win, scmd)
                elif action == "security": security_scan(app_win, scmd)
                elif action == "pentest": run_pentest(app_win, scmd)
                elif action == "multibatch":
                    if isinstance(target_filepath, list): _run_multi_file_check(app_win, target_filepath)
                    else: multi_file_checker(app_win)

            if isinstance(cmd, list):
                for f in cmd:
                    _execute_action(f, f)
            else:
                sfile = target_filepath if isinstance(target_filepath, str) else cmd
                _execute_action(cmd, sfile)



if __name__ == "__main__":
    t = threading.Thread(target=companion_thread)
    t.daemon = True
    t.start()
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n[cherm] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
