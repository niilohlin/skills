---
name: babysit-pr
description: Use when asked to babysit a PR.
---

# Babysit PR

Keep looping over a PR until CI passes and an Greptile gives 5/5, if it approves at all

Find the PR first: use the number or URL the user gave, or else the PR for the
current branch (`gh pr view --json number,url,headRefName,baseRefName`).
Check out its head branch before you change anything. If no PR exists, create one

## The loop

Run every step on each pass, then wait for new CI or review activity and start again.

1. Update to the latest base
2. CI - wait for it to be all green or fix the failing checks.
3. Read everything the Greptile posted since your last pass.
For each comment from an automated reviewer (coderabbitai, greptile-apps, ...):
- **Valid** (a real bug, a real risk, or a clear improvement in scope): fix it,
  push.
- **Not valid** (wrong, out of scope, or a style choice that goes against the
  repo's conventions): don't change code. Reply to the reviewer with a short,
  specific reason, sign with -- <your model name>.

Don't reply to the same comment twice, and don't argue in circles. If the
reviewer pushes back on a point you already answered and you still disagree,
leave it for the human (see Stop).

Record the reviewer's latest score. Greptile, for example, posts a
"Confidence Score: N/5" line.

4. Wait, then repeat - If your harness has a PR-watch or notification tool, use it. Otherwise poll

## Stop

- **Done:** CI is all green, the score is 5/5 (or the bot approved with nothing
  actionable left), and the branch is up to date. Report the PR URL, what you
  fixed, and what you rebutted.
- **Hand back to the user** when: the same CI failure survives 3 fix attempts;
  a fix needs a product or design decision; you need secrets or permissions you
  don't have; a human reviewer asked for changes; or the bot and you are stuck
  disagreeing. Say exactly what is blocking.

## Rules

- Keep commits small, one per fix, with clear messages. Follow the repo's
  commit conventions.
- Run the tests, and lint locally before every push when you can.
- Stay inside the PR's scope. Don't refactor unrelated code to please a bot.
- Never merge the PR unless the user asked you to.
