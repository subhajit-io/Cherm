"""
Cherm Command Bridge & Integration Hub
======================================
Allows external software, custom CLI tools, CI scripts, and AI agents
to connect and execute terminal commands through Cherm.

Author: Subhajit Das (Cherm Open Source Project)
"""

import os
import sys
import json
import re
import time
import subprocess
from typing import List, Dict, Any, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_NAME = "cherm_commands.json"

DEFAULT_COMMANDS = [
    {
        "id": "file_details_cli",
        "name": "File Inspector CLI",
        "cmd": 'python -c "import os, sys; p = sys.argv[1] if len(sys.argv) > 1 else \'.\'; print(f\'[File Inspector] Target: {p}\\nExists: {os.path.exists(p)}\\nSize: {os.path.getsize(p) if os.path.exists(p) else 0} bytes\')" "{file}"',
        "description": "Inspects target file details using an external Python CLI command",
        "extensions": ["*"],
        "category": "Diagnostics",
        "mode": "interactive"
    },
    {
        "id": "git_quick_status",
        "name": "Git Status One-Liner",
        "cmd": "git status -s",
        "description": "Run fast git status on current workspace from external Git binary",
        "extensions": ["*"],
        "category": "Git & VCS",
        "mode": "interactive"
    },
    {
        "id": "external_software_hook",
        "name": "External Software Hook (Template)",
        "cmd": "echo [External Software Bridge] Processing '{filename}' from dir '{dir}' with args: '{args}'",
        "description": "Customizable hook for connecting your own external tools, scanners, or CLI",
        "extensions": ["*"],
        "category": "Connected Software",
        "mode": "interactive"
    }
]


def find_commands_config_path() -> str:
    """
    Resolves the active configuration path for connected commands in prioritized order:
    1. CHERM_COMMANDS_CONFIG environment variable
    2. Local workspace: ./.cherm/commands.json or ./cherm_commands.json
    3. Cherm installation folder: <BASE_DIR>/cherm_commands.json
    4. User home folder: ~/.cherm/commands.json
    """
    env_path = os.environ.get("CHERM_COMMANDS_CONFIG")
    if env_path and os.path.isfile(env_path):
        return os.path.abspath(env_path)

    local_dot = os.path.join(os.getcwd(), ".cherm", "commands.json")
    if os.path.isfile(local_dot):
        return os.path.abspath(local_dot)

    local_root = os.path.join(os.getcwd(), CONFIG_FILE_NAME)
    if os.path.isfile(local_root):
        return os.path.abspath(local_root)

    base_path = os.path.join(BASE_DIR, CONFIG_FILE_NAME)
    if os.path.isfile(base_path):
        return os.path.abspath(base_path)

    home_path = os.path.join(os.path.expanduser("~"), ".cherm", "commands.json")
    if os.path.isfile(home_path):
        return os.path.abspath(home_path)

    # Default fallback to base directory
    return os.path.abspath(base_path)


def get_default_config() -> Dict[str, Any]:
    """Returns the default configuration structure."""
    return {
        "version": "1.0",
        "description": "Cherm External Software & Custom Terminal Commands Configuration",
        "variables_guide": {
            "{file}": "Full absolute path to the targeted file",
            "{filename}": "File name with extension (e.g. main.py)",
            "{basename}": "File name without extension (e.g. main)",
            "{ext}": "File extension with dot (e.g. .py)",
            "{dir}": "Directory containing the file",
            "{file_dir}": "Alias for {dir}",
            "{cwd}": "Current working directory",
            "{project_dir}": "Alias for {cwd}",
            "{python}": "Current Python interpreter path",
            "{args}": "Extra arguments passed to the command"
        },
        "commands": DEFAULT_COMMANDS
    }


def load_custom_commands(config_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Loads all custom commands from configuration.
    If the file does not exist, writes the default configuration first.
    """
    path = config_path or find_commands_config_path()
    if not os.path.isfile(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(get_default_config(), f, indent=2)
            return list(DEFAULT_COMMANDS)
        except Exception:
            return list(DEFAULT_COMMANDS)

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        cmds = data.get("commands", [])
        if isinstance(cmds, list):
            return cmds
        return []
    except Exception:
        return list(DEFAULT_COMMANDS)


def save_custom_commands(commands: List[Dict[str, Any]], config_path: Optional[str] = None) -> bool:
    """Saves the commands list into the configuration file."""
    path = config_path or find_commands_config_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        config_data = {
            "version": "1.0",
            "description": "Cherm External Software & Custom Terminal Commands Configuration",
            "commands": commands
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2)
        return True
    except Exception:
        return False


def get_command_by_id(command_id: str, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Retrieves a command by its unique ID."""
    cmds = load_custom_commands(config_path)
    for c in cmds:
        if c.get("id") == command_id:
            return c
    return None


def add_or_update_command(cmd_data: Dict[str, Any], config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Adds a new command or updates an existing one by ID.
    Auto-generates an ID if missing.
    """
    name = cmd_data.get("name", "").strip() or "Custom Command"
    cmd_str = cmd_data.get("cmd", "").strip()
    cmd_id = cmd_data.get("id", "").strip()

    if not cmd_id:
        cmd_id = re.sub(r"[^a-zA-Z0-9_]+", "_", name.lower()).strip("_")
        if not cmd_id:
            cmd_id = f"cmd_{int(time.time())}"

    extensions = cmd_data.get("extensions", ["*"])
    if isinstance(extensions, str):
        extensions = [e.strip() for e in extensions.split(",") if e.strip()]
    if not extensions:
        extensions = ["*"]

    clean_entry = {
        "id": cmd_id,
        "name": name,
        "cmd": cmd_str,
        "description": cmd_data.get("description", "").strip(),
        "extensions": extensions,
        "category": cmd_data.get("category", "Connected Software").strip() or "Connected Software",
        "mode": cmd_data.get("mode", "interactive"),
        "cwd": cmd_data.get("cwd", "{file_dir}"),
        "env": cmd_data.get("env", {})
    }

    cmds = load_custom_commands(config_path)
    updated = False
    for i, c in enumerate(cmds):
        if c.get("id") == cmd_id:
            cmds[i] = clean_entry
            updated = True
            break

    if not updated:
        cmds.append(clean_entry)

    save_custom_commands(cmds, config_path)
    return clean_entry


def remove_command(command_id: str, config_path: Optional[str] = None) -> bool:
    """Removes a command by ID."""
    cmds = load_custom_commands(config_path)
    filtered = [c for c in cmds if c.get("id") != command_id]
    if len(filtered) != len(cmds):
        return save_custom_commands(filtered, config_path)
    return False


def filter_commands_for_file(commands: List[Dict[str, Any]], filepath: Optional[str]) -> List[Dict[str, Any]]:
    """Filters commands matching the target file extension (or wildcard '*')."""
    if not filepath or not isinstance(filepath, str):
        return [c for c in commands if "*" in c.get("extensions", ["*"]) or not c.get("extensions")]

    ext = os.path.splitext(filepath)[1].lower()
    matched = []
    for c in commands:
        exts = [e.lower() for e in c.get("extensions", ["*"])]
        if "*" in exts or ext in exts:
            matched.append(c)
    return matched


def interpolate_command(cmd_template: str, filepath: Optional[str] = None, extra_args: str = "") -> Tuple[str, str]:
    """
    Interpolates placeholder variables into a shell command template:
    {file}, {filename}, {basename}, {ext}, {dir}, {file_dir}, {cwd}, {project_dir}, {python}, {args}
    Returns: (interpolated_command, working_directory)
    """
    fp = os.path.abspath(filepath) if filepath and isinstance(filepath, str) else ""
    # Security: strip dangerous shell command injection metacharacters from filepaths
    if fp and any(c in fp for c in (";", "&", "|", "`", "$", "\n", "\r")):
        fp = re.sub(r"[;&|`$\r\n]", "", fp)

    fn = os.path.basename(fp) if fp else ""
    bn = os.path.splitext(fn)[0] if fn else ""
    ext = os.path.splitext(fn)[1] if fn else ""
    fdir = os.path.dirname(fp) if fp else os.getcwd()
    cwd = os.getcwd()
    py = sys.executable

    target_cwd = fdir if fp and os.path.isdir(fdir) else cwd

    # Sanitize extra arguments
    clean_args = extra_args or ""
    if clean_args and any(c in clean_args for c in (";", "&", "|", "`", "$", "\n", "\r")):
        clean_args = re.sub(r"[;&|`$\r\n]", "", clean_args)

    replacements = {
        "{file}": fp,
        "{filename}": fn,
        "{basename}": bn,
        "{ext}": ext,
        "{dir}": fdir,
        "{file_dir}": fdir,
        "{cwd}": cwd,
        "{project_dir}": cwd,
        "{python}": py,
        "{args}": clean_args,
        "{extra_args}": clean_args
    }

    result = cmd_template
    for placeholder, val in replacements.items():
        result = result.replace(placeholder, str(val))

    return result, target_cwd


def run_command_headless(
    cmd_or_id: str,
    filepath: Optional[str] = None,
    extra_args: str = "",
    timeout: int = 60,
    env_vars: Optional[Dict[str, str]] = None,
    allow_adhoc: bool = False
) -> Dict[str, Any]:
    """
    Executes a command non-interactively (headless), capturing stdout, stderr,
    exit code, and duration in milliseconds. Used by MCP tools, Web GUI, and CLI flags.
    Ad-hoc execution is disabled by default for security to prevent arbitrary command injection.
    """
    cmd_entry = get_command_by_id(cmd_or_id)
    if cmd_entry:
        cmd_template = cmd_entry.get("cmd", "")
        cmd_id = cmd_entry.get("id")
        cmd_name = cmd_entry.get("name")
        cfg_env = cmd_entry.get("env") or {}
    else:
        if not allow_adhoc:
            return {
                "success": False,
                "exit_code": 1,
                "stdout": "",
                "stderr": f"Security Policy Violation: Command ID '{cmd_or_id}' is not registered in cherm_commands.json. Ad-hoc command execution is blocked.",
                "duration_ms": 0.0,
                "cmd": cmd_or_id,
                "cwd": os.getcwd()
            }
        cmd_template = cmd_or_id
        cmd_id = "ad_hoc"
        cmd_name = "Custom Shell Command"
        cfg_env = {}

    if not cmd_template.strip():
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": "Error: Command template or ID is empty.",
            "duration_ms": 0.0,
            "cmd": "",
            "cwd": os.getcwd()
        }

    interpolated_cmd, target_cwd = interpolate_command(cmd_template, filepath, extra_args)

    run_env = os.environ.copy()
    run_env.update(cfg_env)
    if env_vars:
        run_env.update(env_vars)

    start_time = time.time()
    try:
        proc = subprocess.run(
            interpolated_cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=target_cwd,
            timeout=timeout,
            env=run_env
        )
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "duration_ms": duration_ms,
            "cmd": interpolated_cmd,
            "command_id": cmd_id,
            "command_name": cmd_name,
            "cwd": target_cwd
        }
    except subprocess.TimeoutExpired:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "exit_code": 124,
            "stdout": "",
            "stderr": f"Execution timed out after {timeout} seconds.",
            "duration_ms": duration_ms,
            "cmd": interpolated_cmd,
            "command_id": cmd_id,
            "command_name": cmd_name,
            "cwd": target_cwd
        }
    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "success": False,
            "exit_code": 1,
            "stdout": "",
            "stderr": f"Execution failed with exception: {e}",
            "duration_ms": duration_ms,
            "cmd": interpolated_cmd,
            "command_id": cmd_id,
            "command_name": cmd_name,
            "cwd": target_cwd
        }
