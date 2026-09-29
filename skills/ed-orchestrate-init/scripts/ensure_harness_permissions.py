#!/usr/bin/env python3
"""Pre-grant the file/command permissions sub-agents need to actually WRITE in a
new project — the recurring "the worker ran but changed nothing" failure.

Two harness-specific gates, each an idempotent merge that preserves every other
key in the file:

  opencode <opencode.json>
      In an Orca worktree the shared task-memory dir is a symlink resolving OUTSIDE
      the worktree, so opencode classifies it as `external_directory` and, in
      `opencode run` (no TTY), auto-rejects the read/write. Sets
      `permission.external_directory: "allow"` in the PROJECT's opencode.json.
      Leaves an explicit different value alone (warns).

  agy <~/.gemini/antigravity-cli/settings.json> --path P [--path P ...]
      [--from-git-worktrees] [--baseline-commands]
      agy's USER-GLOBAL settings gate every project path: adds `read_file(P)`,
      `write_file(P)` to permissions.allow and P to trustedWorkspaces, for the repo
      and for the directory its Orca worktrees live in (--from-git-worktrees adds
      the parent dir of each linked worktree `git worktree list` reports).
      --baseline-commands also allow-lists the common first-words headless agents
      need (agy denies any command whose first word is not listed).
      Note: headless `agy -p` additionally needs `--dangerously-skip-permissions`
      (a role `cliFlags` entry) — this file alone doesn't lift that gate.

Prints what changed; re-running is a no-op.
"""
import argparse
import json
import os
import subprocess
import sys

BASELINE_COMMANDS = [
    "git", "npm", "npx", "node", "python3", "ls", "cat", "grep", "find", "head", "tail",
    "wc", "pwd", "sort", "uniq", "diff", "awk", "jq", "basename", "dirname", "tr", "cut",
    "mkdir", "touch", "cp", "mv", "test", "echo", "which", "cd", "orca", "codegraph",
]


def load_json(path, default):
    if not os.path.exists(path):
        return default, False
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    if not raw.strip():
        return default, True
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: {path} is not valid JSON ({e}); fix it or add the entries by hand.")
    if not isinstance(data, dict):
        sys.exit(f"ERROR: {path} is not a JSON object; leaving it alone.")
    return data, True


def write_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def cmd_opencode(a):
    data, existed = load_json(a.config, {"$schema": "https://opencode.ai/config.json"})
    perm = data.setdefault("permission", {})
    if not isinstance(perm, dict):
        sys.exit(f"ERROR: {a.config} `permission` is not an object (a global shorthand?); "
                 'set "external_directory": "allow" by hand.')
    current = perm.get("external_directory")
    if current == "allow":
        print(f"{a.config}: external_directory already allowed")
        return
    if current is not None:
        print(f"WARN: {a.config} sets permission.external_directory = {json.dumps(current)}; "
              "left as is. Workers in Orca worktrees can't write the symlinked shared "
              "memory dir unless it allows it.", file=sys.stderr)
        return
    perm["external_directory"] = "allow"
    write_json(a.config, data)
    print(f"{a.config}: {'updated' if existed else 'created'} (permission.external_directory = allow)")


def git_worktree_parents():
    try:
        out = subprocess.check_output(["git", "worktree", "list", "--porcelain"], text=True,
                                      stderr=subprocess.DEVNULL)
    except Exception:
        return []
    paths = [l.split(" ", 1)[1] for l in out.splitlines() if l.startswith("worktree ")]
    # First entry is the primary checkout; the rest are linked worktrees.
    return sorted({os.path.dirname(p) for p in paths[1:]})


def cmd_agy(a):
    paths = [os.path.abspath(os.path.expanduser(p)) for p in (a.path or [])]
    if a.from_git_worktrees:
        paths += git_worktree_parents()
    paths = list(dict.fromkeys(p.rstrip("/") for p in paths))
    if not paths and not a.baseline_commands:
        sys.exit("ERROR: nothing to add — pass --path, --from-git-worktrees, or --baseline-commands.")

    data, existed = load_json(a.settings, {})
    perms = data.setdefault("permissions", {})
    allow = perms.setdefault("allow", [])
    trusted = data.setdefault("trustedWorkspaces", [])
    if not isinstance(allow, list) or not isinstance(trusted, list):
        sys.exit(f"ERROR: {a.settings} has an unexpected permissions/trustedWorkspaces shape; "
                 "add the entries by hand.")

    added = []
    for p in paths:
        for entry in (f"read_file({p})", f"write_file({p})"):
            if entry not in allow:
                allow.append(entry)
                added.append(entry)
        if p not in trusted:
            trusted.append(p)
            added.append(f"trustedWorkspaces += {p}")
    if a.baseline_commands:
        for c in BASELINE_COMMANDS:
            entry = f"command({c})"
            if entry not in allow:
                allow.append(entry)
                added.append(entry)

    if not added:
        print(f"{a.settings}: already grants everything requested")
        return
    write_json(a.settings, data)
    print(f"{a.settings}: {'updated' if existed else 'created'}")
    for entry in added:
        print(f"  + {entry}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("opencode")
    p.add_argument("config", nargs="?", default="opencode.json")
    p.set_defaults(fn=cmd_opencode)
    p = sub.add_parser("agy")
    p.add_argument("settings", nargs="?", default="~/.gemini/antigravity-cli/settings.json")
    p.add_argument("--path", action="append")
    p.add_argument("--from-git-worktrees", action="store_true")
    p.add_argument("--baseline-commands", action="store_true")
    p.set_defaults(fn=cmd_agy)
    a = parser.parse_args()
    if hasattr(a, "settings"):
        a.settings = os.path.expanduser(a.settings)
    a.fn(a)


if __name__ == "__main__":
    main()
