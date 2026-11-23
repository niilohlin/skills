---
name: full-send
description: Use when asked to do a task "full send".
---

# Full send

Do a task until completion, then:

1. If the repo has a verify skill (e.g. visa's `.claude/skills/verify`), run
   it against the real app and fix what it finds. Unit tests alone aren't
   enough.
2. Commit (including any comment-remover changes).
3. Review it with the astra-review skill and handle the findings as it says.
   This applies whichever agent you are (Claude or Codex).
4. Push, open the PR, and babysit it with the babysit-pr skill.
