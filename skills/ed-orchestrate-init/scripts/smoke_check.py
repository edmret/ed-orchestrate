#!/usr/bin/env python3
"""Ground-truth check for the post-setup smoke test: did each harness's worker
actually WRITE into the shared memory dir from its own worktree?

The orchestrator delegates one trivial task per harness ("append the line
`smoke-test <harness>` to <memory-dir>/tasks/SMOKE.md"); this script then reads that
file and reports per harness ok / MISSING with the usual cause. It never trusts a
worker's exit code or self-report — only the file.

Usage:
  smoke_check.py <memory-dir> --harnesses claude,opencode,codex,agy [--reset]
  --reset   delete <memory-dir>/tasks/SMOKE.md afterwards (run once all are ok)

Exit 0 if every harness wrote its line, 1 otherwise.
"""
import argparse
import os
import sys

HINTS = {
    "claude": "trust dialog not accepted in that worktree, or a settings.json deny rule "
              "blocks the write (use settings.local.json; see harness-claude.md)",
    "opencode": "opencode.json permission.external_directory is not \"allow\" "
                "(ensure_harness_permissions.py opencode)",
    "codex": "sandbox blocked the symlink write: cliFlags need --add-dir \"$(readlink -f <dir>)\" "
             "and -s workspace-write (ensure_harness_permissions.py codex)",
    "agy": "needs --dangerously-skip-permissions in cliFlags plus read_file/write_file and "
           "trustedWorkspaces entries (ensure_harness_permissions.py agy)",
    "gemini": "folder not trusted, or GEMINI.md/context.fileName not loading AGENTS.md "
              "(ensure_gemini_context.py)",
    "cursor": "folder not trusted, or workspace write not approved",
    "droid": "no known fix — check the worker's terminal output",
}

TASK_TEXT = (
    'Append exactly one line `smoke-test {harness}` to `{path}` (create the file if '
    'missing), change nothing else, then reply DONE, or FAILED with the exact error.'
)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("memory_dir")
    p.add_argument("--harnesses", required=True)
    p.add_argument("--reset", action="store_true")
    p.add_argument("--print-task", action="store_true",
                   help="print the delegation text per harness instead of checking")
    a = p.parse_args()

    harnesses = [h.strip() for h in a.harnesses.split(",") if h.strip()]
    path = os.path.join(a.memory_dir, "tasks", "SMOKE.md")

    if a.print_task:
        for h in harnesses:
            print(f"{h}: {TASK_TEXT.format(harness=h, path=path)}")
        return 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = {ln.strip() for ln in f}
    except OSError:
        lines = set()

    bad = 0
    for h in harnesses:
        if f"smoke-test {h}" in lines:
            print(f"{h}: ok")
        else:
            bad += 1
            print(f"{h}: MISSING — {HINTS.get(h, 'check the worker output')}")

    if a.reset and not bad and os.path.exists(path):
        os.remove(path)
        print(f"removed {path}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
