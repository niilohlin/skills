---
name: babysit-merge
description: Merge a GitHub PR and babysit the deploy. Updates the branch with the latest base (fixing merge conflicts) if needed, merges once green, follows the deployment until it is live and healthy, and checks for new errors. If something breaks, opens a revert PR; if all is fine, settles the thread. Use when the user says "babysit merge", "merge and watch the deploy", "merge and monitor", "ship this PR", or "/babysit-merge".
---

# Babysit Merge

Merge the PR, watch it deploy, confirm nothing broke. Revert on trouble,
settle the thread when it's clean.

Find the PR: the number or URL the user gave, else the PR for the current
branch (`gh pr view --json number,url,headRefName,baseRefName`).

## 1. Get the PR mergeable

```sh
gh pr view <pr> --json state,mergeable,mergeStateStatus,reviewDecision,baseRefName,headRefName
gh pr checks <pr>
```

- **Behind or conflicting** (`BEHIND`, `DIRTY`, `mergeable: CONFLICTING`):
  check out the head branch and merge the latest base into it:

  ```sh
  git fetch origin
  git checkout <head> && git pull
  git merge origin/<base>      # base is usually master or main
  ```

  Resolve every conflict by understanding both sides (read the base commits
  that touched the file with `git log -p origin/<base> -- <file>`), never by
  blindly picking one side. Run the build and relevant tests, commit the merge,
  push. Never force-push.
- **CI failing**: fix it the way `/babysit-pr` does (read logs, fix the root
  cause, push). Never skip or weaken checks.
- **CI pending**: wait for it (PR-watch tool if you have one, otherwise poll
  `gh pr checks <pr>` every few minutes).
- **Needs review / changes requested**: stop and hand back. Don't merge
  around a human reviewer.

## 2. Record the baseline, then merge

Before merging, note the current error picture so you can compare after:
the services this repo deploys and their current deploy state (step 3), and
the recent error rate for them (step 4). Then merge using the repo's usual
method (check `gh repo view --json squashMergeAllowed,mergeCommitAllowed,rebaseMergeAllowed`
and what recent PRs used):

```sh
gh pr merge <pr> --squash      # or --merge / --rebase per repo convention
```

Record the merge commit SHA: `gh pr view <pr> --json mergeCommit`.

## 3. Follow the deployment

Work out how this repo deploys: read `.github/workflows/` (look for jobs
triggered on push to the base branch), and any `deploy`/`helm`/`argocd`
references. At Volumental, services usually build an image on merge, and
ArgoCD deploys tags from the `helm-chart-values` GitOps repo.

- Watch the post-merge workflow runs to completion:
  `gh run list --branch <base> --commit <sha>` then `gh run watch <run-id>`.
  A failed deploy/build run after merge counts as an issue (step 5).
- For catalog services use the cosmos MCP tools: `list_services` to find the
  service id, then `get_deploy_state` (service, env) until the running tag
  contains the merge SHA and ArgoCD reports `Synced` + `Healthy`.
- If staging deploys automatically but production needs a deploy PR (cosmos
  `deploy` returns `pending_review`), say so and only follow environments that
  actually deploy. Don't deploy to production unless the user asked.
- Also check rollout health directly when you have access:
  `kubectl rollout status deploy/<name> -n <ns>` and look for crash loops or
  restarts (`kubectl get pods -n <ns>`).

## 4. Check for new errors

Once the new version is live, watch it for ~15 minutes (longer for
low-traffic services) and compare against the baseline:

```sh
gcloud logging read 'severity>=ERROR AND resource.labels.container_name="<name>"' \
  --project <project> --freshness=20m --limit 50
```

Also look at any error tracker or alerts the repo/README points to, and any
smoke or e2e checks the repo has for deployed environments.

An **issue** is any of: deploy/build run failed, rollout not healthy, crash
loops, new error types that weren't in the baseline, or a clear jump in error
rate. Pre-existing errors at the same rate are not an issue; say they exist.

## 5a. Issue found: revert PR

```sh
git fetch origin && git checkout -b revert-<pr> origin/<base>
git revert -m 1 <merge-sha>    # drop -m 1 for squash/rebase merges
git push -u origin revert-<pr>
gh pr create --base <base> --title "Revert \"<original title>\"" \
  --body "Reverts #<pr>. <what broke, with log excerpts / links>"
```

Don't merge the revert yourself unless the user said to; tell them it's
ready and why, with the evidence. Leave the thread active.

## 5b. All good: settle the thread

Report: PR URL, merge SHA, where it deployed (env + running tag), and that no
new errors showed up in the watch window. Then settle the thread (T3:
`t3_thread_organize` with `action: "settle"`).

## Rules

- Never force-push, never bypass branch protection or required reviews.
- Stop and hand back when: a human requested changes, a conflict needs a
  product decision, you lack access to deploy state or logs (say exactly what
  you couldn't check), or the deploy is stuck for 30+ minutes.
- Don't settle the thread if anything is unverified; say what's left.
