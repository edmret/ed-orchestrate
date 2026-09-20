#!/usr/bin/env python3
"""Validate a .orchestrate/agents.json file against the ed-orchestrate schema.

Usage: validate_agents_json.py <path-to-agents.json>

Exit 0 and print OK if valid (warnings may still print to stderr).
Exit 1 and print one error per line to stderr if invalid.
"""
import json
import re
import sys

ROLE_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
HARNESSES = {"claude", "codex", "opencode", "agy", "cursor", "gemini", "droid"}
EFFORTS = {"low", "medium", "high", None}
WORKTREE_STRATEGIES = {"current", "new-child", "new-top-level"}
DELEGATION_MODES = {"handoff", "supervised"}
REQUIRED_ROLE_FIELDS = (
    "description",
    "harness",
    "model",
    "provider",
    "effort",
    "tools",
    "systemPromptSeed",
    "worktreeStrategy",
    "delegationMode",
)


def validate(data):
    errors = []
    warnings = []

    if not isinstance(data.get("version"), int):
        errors.append("version: must be an int")

    if "project" in data and data["project"] is not None and not isinstance(data["project"], str):
        errors.append("project: must be a string if present")

    roles = data.get("roles")
    if not isinstance(roles, dict) or not roles:
        errors.append("roles: must be a non-empty object")
        roles = {}

    for name, role in roles.items():
        prefix = f"roles.{name}"
        if not ROLE_NAME_RE.match(name):
            errors.append(f"{prefix}: role name must match ^[a-z][a-z0-9-]*$")
        if not isinstance(role, dict):
            errors.append(f"{prefix}: must be an object")
            continue

        for field in REQUIRED_ROLE_FIELDS:
            if field not in role:
                errors.append(f"{prefix}.{field}: missing")

        if "description" in role and not isinstance(role["description"], str):
            errors.append(f"{prefix}.description: must be a string")

        harness = role.get("harness")
        if harness not in HARNESSES:
            errors.append(f"{prefix}.harness: must be one of {sorted(HARNESSES)}, got {harness!r}")

        if "model" in role and not isinstance(role["model"], str):
            errors.append(f"{prefix}.model: must be a string")

        provider = role.get("provider")
        if provider is not None and not isinstance(provider, str):
            errors.append(f"{prefix}.provider: must be a string or null")
        if provider is not None and harness != "opencode":
            warnings.append(
                f"{prefix}.provider: set to {provider!r} but harness is {harness!r}; "
                "provider is only meaningful for harness == opencode in v1"
            )

        effort = role.get("effort")
        if effort not in EFFORTS:
            errors.append(f"{prefix}.effort: must be one of low|medium|high|null, got {effort!r}")

        tools = role.get("tools")
        if tools is not None:
            if not isinstance(tools, dict) or not all(isinstance(v, bool) for v in tools.values()):
                errors.append(f"{prefix}.tools: must be an object of booleans, or null")

        seed = role.get("systemPromptSeed")
        if seed is not None and not isinstance(seed, str):
            errors.append(f"{prefix}.systemPromptSeed: must be a string or null")

        strategy = role.get("worktreeStrategy")
        if strategy not in WORKTREE_STRATEGIES:
            errors.append(
                f"{prefix}.worktreeStrategy: must be one of {sorted(WORKTREE_STRATEGIES)}, got {strategy!r}"
            )

        mode = role.get("delegationMode")
        if mode not in DELEGATION_MODES:
            errors.append(
                f"{prefix}.delegationMode: must be one of {sorted(DELEGATION_MODES)}, got {mode!r}"
            )

        cli_flags = role.get("cliFlags")
        if cli_flags is not None:
            if not isinstance(cli_flags, list) or not all(isinstance(f, str) for f in cli_flags):
                errors.append(f"{prefix}.cliFlags: must be an array of strings, or absent")

        fallbacks = role.get("fallbacks")
        if fallbacks is not None:
            if not isinstance(fallbacks, list):
                errors.append(f"{prefix}.fallbacks: must be an array or absent")
            else:
                # Keyed by (effective harness, provider) — a fallback entry may
                # omit `harness` to mean "same harness, different provider/model"
                # (a resilience-style fallback, e.g. for the reviewer/validator
                # role: same model family, alternate provider); an explicit
                # `harness` differing from the role's primary means a
                # cross-harness override, resolved at delegation time when the
                # user names a different harness (ed-orchestrate/AGENTS.md
                # step 2a).
                seen = set()
                for i, fb in enumerate(fallbacks):
                    fprefix = f"{prefix}.fallbacks[{i}]"
                    if not isinstance(fb, dict):
                        errors.append(f"{fprefix}: must be an object")
                        continue

                    if "model" not in fb:
                        errors.append(f"{fprefix}.model: missing")
                    elif not isinstance(fb["model"], str):
                        errors.append(f"{fprefix}.model: must be a string")

                    fb_harness = fb.get("harness")
                    if fb_harness is not None and fb_harness not in HARNESSES:
                        errors.append(
                            f"{fprefix}.harness: must be one of {sorted(HARNESSES)}, or absent, got {fb_harness!r}"
                        )
                    elif fb_harness == harness:
                        errors.append(
                            f"{fprefix}.harness: omit this field instead of repeating the role's "
                            f"primary harness ({harness!r}) — absent means same-harness fallback"
                        )

                    effective_harness = fb_harness if fb_harness is not None else harness

                    fb_provider = fb.get("provider")
                    if fb_provider is not None and not isinstance(fb_provider, str):
                        errors.append(f"{fprefix}.provider: must be a string or null")
                    if fb_provider is not None and effective_harness != "opencode":
                        warnings.append(
                            f"{fprefix}.provider: set to {fb_provider!r} but effective harness is "
                            f"{effective_harness!r}; provider is only meaningful for harness == opencode in v1"
                        )

                    dedup_key = (effective_harness, fb_provider)
                    if dedup_key in seen:
                        errors.append(
                            f"{fprefix}: duplicate fallback for (harness={effective_harness!r}, "
                            f"provider={fb_provider!r}); each (harness, provider) pair may appear at most once"
                        )
                    else:
                        seen.add(dedup_key)

                    if "effort" in fb:
                        fb_effort = fb.get("effort")
                        if fb_effort not in EFFORTS:
                            errors.append(
                                f"{fprefix}.effort: must be one of low|medium|high|null, got {fb_effort!r}"
                            )

    defaults = data.get("defaults")
    if defaults is not None:
        if not isinstance(defaults, dict):
            errors.append("defaults: must be an object if present")
        else:
            default_role = defaults.get("role")
            if default_role is not None and default_role not in roles:
                errors.append(f"defaults.role: {default_role!r} does not reference an existing role")
            if "worktreeStrategy" in defaults and defaults["worktreeStrategy"] not in WORKTREE_STRATEGIES:
                errors.append("defaults.worktreeStrategy: invalid enum value")
            if "delegationMode" in defaults and defaults["delegationMode"] not in DELEGATION_MODES:
                errors.append("defaults.delegationMode: invalid enum value")

    return errors, warnings


def main():
    if len(sys.argv) != 2:
        print("usage: validate_agents_json.py <path-to-agents.json>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"{path}: failed to read/parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(data, dict):
        print(f"{path}: top-level value must be an object", file=sys.stderr)
        sys.exit(1)

    errors, warnings = validate(data)

    for w in warnings:
        print(f"WARN: {w}", file=sys.stderr)

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
