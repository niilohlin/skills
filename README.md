# skills

My agent skills (Claude Code, Codex, T3 Code, ...).

## Install on a machine

```sh
git clone git@github.com:niilohlin/skills.git ~/skills && ~/skills/install.sh
```

Re-run `install.sh` after adding a skill. Updates are just `git pull` (symlinks).

`install.sh` also links `CLAUDE.md` (global instructions) and `hooks/` (the comment
stripper, check it with `hooks/test-strip.sh`) into `~/.claude`. A SessionStart hook
in each machine's `~/.claude/settings.json` pulls this repo, so edits pushed from
one machine reach the others on their next session.

## Add a skill

Create `<name>/SKILL.md`:

```markdown
---
name: <name>
description: What it does and when to use it.
---

Instructions.
```
