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

  codex <agents.json> --memory-dir DIR
      Headless Codex runs in a sandbox that blocks writes through the worktree-shared
      memory symlink (it resolves outside the worktree): "operation not permitted".
      Verified fix: `--add-dir "$(readlink -f DIR)"` — the target must be the RESOLVED
      real path (Codex rejects a symlinked writable root), hence the shell
      substitution, evaluated in the worktree the command runs in. Adds that pair to
      `cliFlags` of every codex binding (role-level for the primary and same-harness
      fallbacks, entry-level for cross-harness codex fallbacks) in agents.json.
      Edits the roster only; re-validate and re-splice afterwards.

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


def codex_flags(memory_dir):
    return ["--add-dir", '"$(readlink -f %s)"' % memory_dir.rstrip("/")]


def _ensure_flags(owner, flags):
    """Append the flag pair to owner['cliFlags'] unless an --add-dir is already there."""
    cur = owner.get("cliFlags")
    cur = list(cur) if isinstance(cur, list) else []
    if "--add-dir" in cur:
        return False
    owner["cliFlags"] = cur + flags
    return True


def cmd_codex(a):
    data, existed = load_json(a.agents_json, None)
    if not existed or data is None:
        sys.exit(f"ERROR: {a.agents_json} not found")
    flags = codex_flags(a.memory_dir)
    changed = []
    for name, role in (data.get("roles") or {}).items():
        if role.get("harness") == "codex" and _ensure_flags(role, flags):
            changed.append(f"roles.{name}.cliFlags")
        for i, fb in enumerate(role.get("fallbacks") or []):
            fb_harness = fb.get("harness")
            if fb_harness == "codex":
                if _ensure_flags(fb, flags):
                    changed.append(f"roles.{name}.fallbacks[{i}].cliFlags")
            # same-harness fallbacks (no harness key) inherit the role's flags
    if not changed:
        print(f"{a.agents_json}: no codex binding needs --add-dir (already set or none use codex)")
        return
    write_json(a.agents_json, data)
    print(f"{a.agents_json}: updated")
    for c in changed:
        print(f"  + {c}: {' '.join(flags)}")
    print("Re-validate agents.json and re-splice the AGENTS.md roster block.")


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
    p = sub.add_parser("codex")
    p.add_argument("agents_json", nargs="?", default=".orchestrate/agents.json")
    p.add_argument("--memory-dir", default=".ai-memory")
    p.set_defaults(fn=cmd_codex)
    a = parser.parse_args()
    if hasattr(a, "settings"):
        a.settings = os.path.expanduser(a.settings)
    a.fn(a)


if __name__ == "__main__":
    main()
