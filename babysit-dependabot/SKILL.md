---
name: babysit-dependabot
disable-model-invocation: true
description: Clears Dependabot PRs, used when called "/babysit-dependabot".
---

0. Preflight
   - Take the lock: if `~/.cache/babysit-dependabot.lock` exists and its
     mtime is under 30 minutes old, another run owns the queue; report its
     contents (thread id, current PR) and stop. Otherwise write your thread
     id and the PR you're on into it, `touch` it at every step, and delete it
     when you finish or stop.
   - Finish what the previous run left: for the Dependabot PRs merged in the
     last 24h (`gh pr list --author app/dependabot --state merged`), check
     their deploy (step 6) before starting anything new.
1. List the open PRs and judge the risk
2. Get it green - fix CI etc. If the PR is behind or conflicted, comment
   `@dependabot rebase`; never use GitHub's "Update branch" or push to the
   branch yourself, that makes Dependabot treat the PR as edited and stop
   maintaining it. If Dependabot answers "already up-to-date" while GitHub
   still shows a conflict, merge the base in, run `pnpm install
   --lockfile-only`, commit and push.
3. Validate (only if judged to be risky)
4. Approve (any comments, sign with -- <your model>)
5. Merge
6. Monitor: first check that the deploy succeeded with
   `kubectl --context <ctx> -n argocd get applications` (sync/health and the
   image tag; the argocd CLI needs SSO and is usually logged out), then for
   10 minutes check the logs through gcloud and the alert channels in Slack:
   #hq-alerts, #monitoring-infra, #instore-monitoring-alerts, #solo-ui-alerts,
   #specialty-ui-alerts. Read them with `oldest` set to the merge time, as Unix
   seconds from `date -u +%s` taken at merge, never typed by hand. If
   everything is green and the logs look normal, continue; else make a revert
   PR and stop. Use your harness' builtin watch tool to monitor the gh status
7. Go back to step 1 with the next PR
8. list each PR with its outcome, release the lock

## Rules

- One PR at a time; never batch-merge.
- Never merge without green CI, and never skip, disable or weaken checks.
- Never bypass branch protection or required human reviews.
- Stop and hand back on anything that smells like a compromised package.
- Never end the run with a merged PR whose deploy you haven't checked.
