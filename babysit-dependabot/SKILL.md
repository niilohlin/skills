---
name: babysit-dependabot
disable-model-invocation: true
description: Clears Dependabot PRs, used when called "/babysit-dependabot".
---

0. List the PRs
1. Judge the risk
2. Get it green - update base, fix merge conflicts, fix CI etc.
3. Validate (only if judged to be risky)
4. Approve
5. Merge
6. Monitor: first check in ArgoCD that the deploy succeeded, then for 10 minutes
   check the logs through gcloud and the alerts channels in Slack. If everything
   is green and the logs look normal, continue; else make a revert PR and stop.
7. Go back to step 1 with the next PR
8. list each PR with its outcome

## Rules

- One PR at a time; never batch-merge.
- Never merge without green CI, and never skip, disable or weaken checks.
- Never bypass branch protection or required human reviews.
- Stop and hand back on anything that smells like a compromised package.
