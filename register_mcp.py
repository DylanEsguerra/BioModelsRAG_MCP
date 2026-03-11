#!/usr/bin/env python3
"""
Registers the biomodels_mcp server with Claude Code and/or Claude Desktop.

Run this after `venv/bin/pip install -r requirements.txt`:

    venv/bin/python3 register_mcp.py

Then:
  - Claude Code VSCode: reload window with Cmd+Shift+P → 'Developer: Reload Window'
  - Claude Code CLI:    restart your 'claude' session
  - Claude Desktop:     quit and reopen Claude Desktop
"""

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PYTHON = HERE / "venv" / "bin" / "python3"
SERVER = HERE / "mcp_server.py"

# Claude Code — VSCode extension reads ~/.claude.json
# Claude Code — CLI reads ~/.claude/claude.json
# Claude Desktop — reads ~/Library/Application Support/Claude/claude_desktop_config.json
CONFIGS = [
    (
        Path.home() / ".claude.json",
        "Claude Code (VSCode extension)",
        "reload window with Cmd+Shift+P → 'Developer: Reload Window', then type /mcp to verify.",
    ),
    (
        Path.home() / ".claude" / "claude.json",
        "Claude Code (CLI)",
        "restart your 'claude' session.",
    ),
    (
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
        "Claude Desktop",
        "quit and reopen Claude Desktop.",
    ),
]

MCP_ENTRY = {
    "type": "stdio",
    "command": str(PYTHON),
    "args": [str(SERVER)],
}
SERVER_KEY = "biomodels-rag"


def register(config_path: Path, label: str) -> bool:
    """Add or update the biomodels-rag entry in a Claude config file.

    Returns True if the file was found and written successfully.
    Creates the file (with an empty mcpServers dict) if it doesn't exist yet
    but its parent directory does — this handles a fresh Claude Desktop install
    that has never had an MCP server added before.
    """
    if not config_path.exists():
        if config_path.parent.exists():
            # Parent dir exists (app is installed) but config not yet created
            data: dict = {}
        else:
            print(f"  {label}: not installed (config not found) — skipping")
            return False
    else:
        with open(config_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                print(f"  {label}: {config_path} is not valid JSON — skipping")
                return False

    servers = data.setdefault("mcpServers", {})

    if SERVER_KEY in servers:
        old = servers[SERVER_KEY]
        if old.get("command") == str(PYTHON) and old.get("args") == [str(SERVER)]:
            print(f"  {label}: already up to date")
            return True
        print(f"  {label}: updating existing entry")
    else:
        print(f"  {label}: adding entry")

    servers[SERVER_KEY] = MCP_ENTRY

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return True


def main():
    print("\nbiomodels_mcp — registration\n")

    if not PYTHON.exists():
        print("ERROR: venv not found. Run this first:")
        print("  python3 -m venv venv && venv/bin/pip install -r requirements.txt")
        sys.exit(1)

    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Are you in the right directory?")
        sys.exit(1)

    results = []
    for config_path, label, next_step in CONFIGS:
        ok = register(config_path, label)
        results.append((label, next_step, ok))

    any_ok = any(ok for _, _, ok in results)

    if not any_ok:
        print("\nNo Claude clients found on this machine.")
        print("Install Claude Code (https://code.claude.ai) or Claude Desktop (https://claude.ai/download)")
        print("\nOr add this JSON manually to your client's config file:")
        print(json.dumps({"mcpServers": {SERVER_KEY: MCP_ENTRY}}, indent=2))
        sys.exit(1)

    print("\nDone. Next steps:")
    for label, next_step, ok in results:
        if ok:
            print(f"  {label}: {next_step}")


if __name__ == "__main__":
    main()
