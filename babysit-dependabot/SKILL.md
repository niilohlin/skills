---
name: babysit-dependabot
description: Work through open Dependabot PRs one at a time. For each, judges whether the bump is safe, runs /babysit-pr to get it green, fixes breakages, validates locally and in staging (via a `/deploy` PR comment) when the change is risky, approves it, then merges with /babysit-merge. Use when the user says "babysit dependabot", "go through the dependabot PRs", "merge the dependabot PRs", "clear the dependency bumps", or "/babysit-dependabot".
---

# Babysit Dependabot

Process open Dependabot PRs **one at a time**, oldest first. Finish (merged,
skipped or handed back) one PR before starting the next: each merge changes
the base, and the next PR must be rebased on it.

Repo: the one the user named, else the current repo (`gh repo view --json nameWithOwner`).

## 0. List the PRs

```sh
gh pr list --author app/dependabot --state open \
  --json number,title,url,createdAt,labels,headRefName --jq 'sort_by(.createdAt)'
```

Show the user the list, then start with the first.

## 1. Judge the risk

```sh
gh pr view <pr> --json title,body,files,additions,deletions
gh pr diff <pr>
```

Work out, for every package in the PR:

- **Version jump**: patch / minor / major (semver from the title or body).
- **What changed**: read the release notes and changelog that Dependabot
  inlines in the PR body. If they are truncated, open the upstream
  CHANGELOG/releases between the two versions. Look for breaking changes,
  deprecations removed, changed defaults, new minimum runtime versions,
  and security fixes.
- **How it's used here**: `grep -rn` the package name/imports in the repo.
  Is it a dev/test/build-only dependency, or does it run in production?
  Does our code touch any API listed as changed?
- **Lockfile sanity**: the diff should only touch manifests/lockfiles for
  these packages. Unexpected transitive churn, new packages, or changed
  registries/sources are red flags.
- **Supply-chain sanity**: a very fresh release (days old), a new
  maintainer, or a package-name change deserves extra suspicion. Never
  merge something that looks like a hijacked or typo-squatted package; flag
  it to the user.

Classify:

- **Low risk**: patch/minor, dev-only, or no used API changed.
- **Needs validation**: major bump, a production runtime dependency whose
  changed APIs we use, framework/runtime/build tooling (React, Django,
  Node/Python base images, bundlers, ORMs, auth/crypto libs, HTTP clients),
  or GitHub Actions bumps that change behaviour.
- **Unsafe / skip**: requires a migration or design decision you can't make
  from the code alone. Comment on the PR why, leave it open, report it, move on.

## 2. Get it green

Run `/babysit-pr <pr>` (invoke the `babysit-pr` skill). It updates the branch,
fixes CI, and handles bot reviews. Fixes for breaking changes go on the
Dependabot branch as normal commits: adapt our code to the new API, don't
pin back the version.

Gotcha: pushing your own commits to a Dependabot branch makes Dependabot stop
rebasing it. That's fine; keep it up to date yourself (`gh pr update-branch`).
Never comment `@dependabot recreate` after you pushed fixes (it wipes them).

## 3. Validate (only for "needs validation")

- **Locally**: check out the branch, install deps, run the full test suite,
  build, and run the app/the affected code path (use `/run` if helpful).
  Exercise what the changelog says changed.
- **Staging**: if the repo has a comment-triggered deploy workflow (grep
  `.github/workflows/` for `issue_comment` and `/deploy`), comment:

  ```sh
  gh pr comment <pr> --body "/deploy"          # or "/deploy <service>" to deploy one unit
  ```

  Read the workflow to learn the exact syntax and which services it deploys.
  Follow the triggered run (`gh run list --event issue_comment`, `gh run watch <id>`),
  then confirm the new build is live in staging (cosmos `get_deploy_state`)
  and check staging logs for new errors, plus any staging e2e runs. A failed
  deploy or new errors means it isn't safe: fix and repeat, or skip.

If the repo has no `/deploy` workflow, say so and rely on local validation.

## 4. Approve

Once CI is green and you're confident it is safe:

```sh
gh pr review <pr> --approve --body "<one line: what changed, risk level, how it was validated>"
```

If the approving account is also the author of fix commits and branch
protection rejects the self-approval, say so and hand back for a human
approval rather than bypassing it.

## 5. Merge

Run `/babysit-merge <pr>` (invoke the `babysit-merge` skill). It merges,
follows the deploy, and opens a revert PR if anything breaks. Don't start the
next PR until it reports the deploy is healthy; if it opened a revert, stop
and hand back.

## 6. Next

Go back to step 1 with the next PR. Other Dependabot PRs may now be
conflicting or superseded (Dependabot closes superseded ones itself); refresh
the list before picking.

## Report

At the end, list each PR with its outcome: merged (risk level, how
validated), skipped (why), or handed back (what's blocking).

## Rules

- One PR at a time; never batch-merge.
- Never merge without green CI, and never skip, disable or weaken checks.
- Never bypass branch protection or required human reviews.
- Never deploy to production beyond what `/babysit-merge` does on its own.
- Stop and hand back on anything that smells like a compromised package.
