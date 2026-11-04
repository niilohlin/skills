---
name: babysit-pr
description: Babysit a GitHub pull request until it is green. Fixes CI failures, acts on or rebuts automated reviews (CodeRabbit, Greptile, etc.), and keeps the branch up to date with its base. Repeats until CI passes and the reviewer gives 5/5. Use when asked to "babysit", "shepherd", "watch" or "get this PR green", or to deal with CI or bot review feedback on a PR.
---

# Babysit PR

Keep looping over a PR until **CI passes and the automated reviewer gives 5/5**
(or approves with no unresolved actionable comments, if it doesn't give a score).

Find the PR first: use the number or URL the user gave, or else the PR for the
current branch (`gh pr view --json number,url,headRefName,baseRefName`).
Check out its head branch before you change anything.

## The loop

Run every step on each pass, then wait for new CI or review activity and start again.

### 1. Update to the latest base

```sh
gh pr view <pr> --json mergeStateStatus,baseRefName
```

If the state is `BEHIND`, or the base has moved on, bring the branch up to date:

```sh
gh pr update-branch <pr>   # merges the base in, no force push
git pull
```

If that hits conflicts, merge the base locally, fix the conflicts, run the
tests, then push. Never force-push unless the user said to. If they did, use
`--force-with-lease`.

### 2. CI

```sh
gh pr checks <pr>
```

- Still pending: wait (step 4).
- Failed: read the logs. Use `gh run view <run-id> --log-failed`; get the run
  id from the check's link, or from `gh run list --branch <branch>`.
- Find the root cause, reproduce it locally if you can, fix it, run the
  relevant tests locally, then commit and push.
- A flaky failure that has nothing to do with the PR: rerun it once with
  `gh run rerun <run-id> --failed`. If it fails again, investigate it like a
  real failure.
- Never skip, disable or weaken tests or checks to get green.

### 3. Automated reviews

Read everything the bots posted since your last pass:

```sh
gh pr view <pr> --json reviews,comments
gh api repos/{owner}/{repo}/pulls/<pr>/comments --paginate   # inline comments
```

For each comment from an automated reviewer (coderabbitai, greptile-apps, ...):

- **Valid** (a real bug, a real risk, or a clear improvement in scope): fix it,
  push, and reply briefly saying what you changed.
- **Not valid** (wrong, out of scope, or a style choice that goes against the
  repo's conventions): don't change code. Reply to the reviewer with a short,
  specific reason. For inline comments:

  ```sh
  gh api repos/{owner}/{repo}/pulls/<pr>/comments/<comment-id>/replies -f body="..."
  ```

  For top-level comments, use `gh pr comment <pr> --body "..."`.

Don't reply to the same comment twice, and don't argue in circles. If the
reviewer pushes back on a point you already answered and you still disagree,
leave it for the human (see Stop).

Record the reviewer's latest score. Greptile, for example, posts a
"Confidence Score: N/5" line.

### 4. Wait, then repeat

If your harness has a PR-watch or notification tool, use it. Otherwise poll
every few minutes with `gh pr checks <pr>` and `gh pr view <pr> --json reviews,comments`.
After a push, give the bots time to re-review before you judge the score.

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
- Run the tests locally before every push when you can.
- Stay inside the PR's scope. Don't refactor unrelated code to please a bot.
- Never merge the PR unless the user asked you to.
