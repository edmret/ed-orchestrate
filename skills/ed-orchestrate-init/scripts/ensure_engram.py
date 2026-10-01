#!/usr/bin/env python3
"""Check Engram is reachable from every harness a roster uses, and pin the Engram
project name so every Orca worktree resolves the same project.

Read-only for user-global harness configs: it only REPORTS what is missing and the
exact `engram setup <agent>` command that fixes it (those edit files outside the
project, so the init flow asks before running them). The one thing it may write is
the project-local `.engram/config.json` (only with --project, never overwritten).

Usage:
  ensure_engram.py --harnesses claude,opencode,agy [--project NAME] [--config-dir .engram]

Prints one line per harness: `ok` / `MISSING` / `manual`, then the fix. Exit 0 always
(a missing harness is a finding, not an error); exit 2 only on bad arguments.
"""
import argparse
import json
import os
import shutil
import sys

HOME = os.path.expanduser("~")

# ed-orchestrate harness -> `engram setup` agent slug (None = no installer).
SETUP_SLUG = {
    "claude": "claude-code",
    "opencode": "opencode",
    "codex": "codex",
    "agy": "antigravity-cli",
    "gemini": "gemini-cli",
    "cursor": "cursor",
    "droid": None,
}


def _load_json(path):
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _text(path):
    try:
        with open(os.path.expanduser(path), "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def installed(harness):
    """True / False when checkable, None when this script can't tell."""
    if harness == "claude":
        s = _load_json("~/.claude/settings.json") or {}
        plugins = s.get("enabledPlugins") or {}
        if any("engram" in k and v for k, v in plugins.items()):
            return True
        c = _load_json("~/.claude.json") or {}
        return "engram" in (c.get("mcpServers") or {})
    if harness == "opencode":
        d = _load_json("~/.config/opencode/opencode.json") or {}
        return "engram" in (d.get("mcp") or {})
    if harness == "agy":
        d = _load_json("~/.gemini/antigravity-cli/settings.json") or {}
        allow = (d.get("permissions") or {}).get("allow") or []
        return any(isinstance(a, str) and a.startswith("mcp(engram/") for a in allow)
    if harness == "gemini":
        d = _load_json("~/.gemini/settings.json") or {}
        return "engram" in (d.get("mcpServers") or {})
    if harness == "cursor":
        d = _load_json("~/.cursor/mcp.json") or {}
        return "engram" in (d.get("mcpServers") or {})
    if harness == "codex":
        return "engram" in _text("~/.codex/config.toml")
    return None


def pin_project(config_dir, name):
    path = os.path.join(config_dir, "config.json")
    if os.path.exists(path):
        return f"already exists (left as is): {path}"
    os.makedirs(config_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"project_name": name}, f, indent=2)
        f.write("\n")
    return f"created: {path} (commit it — a tracked file appears in every worktree)"


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--harnesses", required=True, help="comma-separated ed-orchestrate harness names")
    p.add_argument("--project", help="pin this Engram project name in <config-dir>/config.json")
    p.add_argument("--config-dir", default=".engram")
    a = p.parse_args()

    harnesses = []
    for h in a.harnesses.split(","):
        h = h.strip()
        if h and h not in harnesses:
            harnesses.append(h)
    unknown = [h for h in harnesses if h not in SETUP_SLUG]
    if unknown:
        print(f"unknown harness(es): {', '.join(unknown)}", file=sys.stderr)
        return 2

    if shutil.which("engram"):
        print("engram binary: ok")
    else:
        print("engram binary: MISSING — install it first (e.g. `brew install engram`), then re-run")

    for h in harnesses:
        slug = SETUP_SLUG[h]
        state = installed(h)
        if slug is None:
            print(f"{h}: manual — no `engram setup` for it; add an MCP server running "
                  "`engram mcp --tools=agent` in that harness's config")
        elif state is True:
            print(f"{h}: ok")
        elif state is False:
            print(f"{h}: MISSING — run: engram setup {slug}")
        else:
            print(f"{h}: unknown — run `engram setup {slug}` if mem_* tools don't show up")
        if h == "agy" and state is not False and slug:
            print("  note: headless agy needs mcp(engram/mem_search) / mcp(engram/mem_save) on "
                  "permissions.allow in ~/.gemini/antigravity-cli/settings.json (engram setup adds them)")

    if a.project:
        print(f"project pin: {pin_project(a.config_dir, a.project)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
