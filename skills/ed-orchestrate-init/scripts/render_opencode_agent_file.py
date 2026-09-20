#!/usr/bin/env python3
"""Render a .opencode/agent/<role>.md file for one opencode-harness role in
agents.json.

Usage: render_opencode_agent_file.py <agents.json> <role-name> --out <path>
"""
import argparse
import json
import sys

DEFAULT_TOOLS = {"bash": True, "read": True, "edit": True, "glob": True, "grep": True}


def render(role):
    tools = role.get("tools") or DEFAULT_TOOLS
    model = f"{role.get('provider')}/{role.get('model')}"
    description = role.get("description", "")
    seed = role.get("systemPromptSeed") or (
        f"You are the {role.get('_name', 'role')} agent for this project."
    )

    lines = ["---"]
    lines.append(f"description: {description}")
    lines.append("mode: primary")
    lines.append(f"model: {model}")
    lines.append("tools:")
    for key in ("bash", "read", "edit", "glob", "grep"):
        val = tools.get(key, True)
        lines.append(f"  {key}: {'true' if val else 'false'}")
    lines.append("---")
    lines.append("")
    lines.append(seed)
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agents_json")
    parser.add_argument("role_name")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    try:
        with open(args.agents_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"{args.agents_json}: failed to read/parse JSON: {e}", file=sys.stderr)
        sys.exit(1)

    role = (data.get("roles") or {}).get(args.role_name)
    if role is None:
        print(f"role {args.role_name!r} not found in {args.agents_json}", file=sys.stderr)
        sys.exit(1)

    if role.get("harness") != "opencode":
        print(
            f"role {args.role_name!r} has harness {role.get('harness')!r}, expected 'opencode'",
            file=sys.stderr,
        )
        sys.exit(1)

    role = dict(role)
    role["_name"] = args.role_name

    with open(args.out, "w", encoding="utf-8") as f:
        f.write(render(role))

    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
