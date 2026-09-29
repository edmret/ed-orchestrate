# opencode agent file template

`render_opencode_agent_file.py` generates `.opencode/agent/<role>.md` for every
`opencode`-harness role. The schema is identical to the one documented in
`ed-orchestrate/references/harness-opencode.md` — cross-referenced here rather
than restated, so the two docs can't drift apart. See that file for the full
schema explanation; the template itself is:

```markdown
---
description: <role.description>
mode: all
model: <role.provider>/<role.model>
tools:
  bash: <role.tools.bash, default true if role.tools is null>
  read: <role.tools.read, default true if role.tools is null>
  edit: <role.tools.edit, default true if role.tools is null>
  glob: <role.tools.glob, default true if role.tools is null>
  grep: <role.tools.grep, default true if role.tools is null>
---
<role.systemPromptSeed, or a one-line fallback "You are the <role> agent for this project." if null>
```
