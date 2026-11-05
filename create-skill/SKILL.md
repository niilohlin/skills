---
name: create-skill
description: Create a new agent skill in ~/skills, install it, and commit and push it. Use when the user says "create a skill", "make a skill", "new skill", "/create-skill", or wants to turn a workflow into a reusable skill.
---

# Create Skill

Skills live in `~/skills` (git repo, `git@github.com:niilohlin/skills.git`).
Each skill is `~/skills/<name>/SKILL.md`. `~/skills/install.sh` symlinks them
into `~/.claude/skills` and `~/.agents/skills`.

## 1. Pin down the skill

From the user's request (and the conversation, if they want to capture a
workflow you just did), work out:

- **name**: kebab-case, short, matches the slash command (`/name`).
- **what it does** and **when to trigger it** (phrases the user would say).
- **the steps**: concrete commands, paths, repos, and gotchas. Look things up
  (read the repos, scripts, configs it touches) instead of guessing.

Ask only if the purpose is genuinely unclear. Check `ls ~/skills` so you don't
clobber an existing skill; if it exists, edit it instead.

## 2. Write `~/skills/<name>/SKILL.md`

```markdown
---
name: <name>
description: What it does. Use when <trigger phrases / situations>.
---

# <Title>

Instructions, as numbered steps with real commands.
```

- The `description` is what decides whether the skill triggers: say what it
  does and list the trigger phrases.
- Write instructions to an agent: imperative, specific, no fluff.
- Extra scripts or reference files go next to `SKILL.md` in the same folder;
  reference them by path from `SKILL.md`.

## 3. Install

```sh
~/skills/install.sh
```

Confirm `~/.claude/skills/<name>` is a symlink to `~/skills/<name>`.

## 4. Commit and push

```sh
cd ~/skills
git add <name>
git commit -m "Add <name> skill"   # or "Update <name> skill"
git push
```

Commit only the skill's folder. If the push is rejected, `git pull --rebase`
and push again.

## 5. Report

Tell the user the skill name, the path, and that it's invoked as `/<name>`
(new sessions pick it up; the current one may need a restart).
