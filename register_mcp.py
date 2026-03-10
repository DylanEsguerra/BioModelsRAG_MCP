#!/usr/bin/env python3
"""
Registers the biomodels-rag MCP server with Claude Code.

Run this after `venv/bin/pip install -r requirements.txt`:

    venv/bin/python3 register_mcp.py

Then reload your VSCode window (Cmd+Shift+P → Developer: Reload Window)
and verify with /mcp in the Claude Code chat.
"""

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = HERE / "venv" / "bin" / "python3"
SERVER = HERE / "mcp_server.py"

# ~/.claude.json  — read by the VSCode extension
# ~/.claude/claude.json — read by the CLI (claude mcp add)
VSCODE_CONFIG = Path.home() / ".claude.json"
CLI_CONFIG = Path.home() / ".claude" / "claude.json"

MCP_ENTRY = {
    "type": "stdio",
    "command": str(PYTHON),
    "args": [str(SERVER)],
}


def register(config_path: Path, label: str) -> bool:
    if not config_path.exists():
        print(f"  {label}: {config_path} not found — skipping")
        return False

    with open(config_path) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"  {label}: {config_path} is not valid JSON — skipping")
            return False

    servers = data.setdefault("mcpServers", {})
    if "biomodels-rag" in servers:
        old = servers["biomodels-rag"]
        if old.get("command") == str(PYTHON) and old.get("args") == [str(SERVER)]:
            print(f"  {label}: already registered at {config_path}")
            return True
        print(f"  {label}: updating existing entry in {config_path}")
    else:
        print(f"  {label}: adding entry to {config_path}")

    servers["biomodels-rag"] = MCP_ENTRY

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
    return True


def main():
    print("\nbiomodels-rag MCP — registration\n")

    if not PYTHON.exists():
        print("ERROR: venv not found. Run this first:")
        print("  python3 -m venv venv && venv/bin/pip install -r requirements.txt")
        sys.exit(1)

    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Are you in the right directory?")
        sys.exit(1)

    vscode_ok = register(VSCODE_CONFIG, "VSCode extension")
    cli_ok = register(CLI_CONFIG, "Claude CLI")

    if not vscode_ok and not cli_ok:
        print("\nNeither config file found.")
        print("Make sure Claude Code (VSCode extension or CLI) is installed first.")
        print("\nOr register manually — paste this into ~/.claude.json:")
        print(json.dumps({"mcpServers": {"biomodels-rag": MCP_ENTRY}}, indent=2))
        sys.exit(1)

    print("\nDone.")
    if vscode_ok:
        print("  VSCode: reload window with Cmd+Shift+P → 'Developer: Reload Window'")
        print("          then type /mcp in Claude Code chat to verify.")
    if cli_ok:
        print("  CLI: restart your 'claude' session.")


if __name__ == "__main__":
    main()
