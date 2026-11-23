---
name: babysit-pr
description: Used automatically after making a new PR.
---

# Babysit PR

Keep looping over a PR until CI passes and an Greptile gives 5/5, if it approves at all

Find the PR first: use the number or URL the user gave, or else the PR for the
current branch (`gh pr view --json number,url,headRefName,baseRefName`).
Check out its head branch before you change anything. If no PR exists, create one

## The loop

Run every step on each pass, then wait for new CI or review activity and start again.

1. Update to the latest base only when the PR has merge conflicts or a CI
   failure that master already fixed. Don't merge master in just because it
   moved: each merge re-runs CI and Greptile. babysit-merge updates the branch
   once, right before merging.
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

Record the reviewer's latest score. For Greptile run
`~/skills/babysit-pr/greptile-status.sh <pr>`: it prints the score, impact and
every unresolved Greptile thread as plain text. Don't scrape the HTML comment
yourself.

4. Wait, then repeat. To wait for Greptile, always use the shared poller:
   `~/skills/babysit-pr/greptile-status.sh --wait <pr>`. Every waiter on the
   machine registers its PR with one background poller, which fetches the
   "Greptile Review" check run for all watched PRs in a single GraphQL call
   every 30s, so parallel sessions don't each hit the API. It follows new
   pushes to the PR, and when the review of the head completes (or the PR is
   merged or closed) it prints the same status as above and exits 0. It gives
   up after 30 minutes (`--timeout SECS`), or after 5 minutes if Greptile never
   starts on the head, and then exits 2. Run it as a background Bash task and
   pass its returned ID to `t3_background_wait` (or your harness's
   equivalent). Don't write your own sleep loops or re-run the status script by
   hand to poll. For CI, use your harness's PR-watch tool if it has one.

## Stop

- **Done:** CI is all green, the score is 5/5 (or the bot approved with nothing
  actionable left), and there are no merge conflicts. Being behind master is
  fine. Report the PR URL, what you
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
