---
name: babysit-merge
description: Use when the user says "babysit merge", "merge and watch the deploy" or "/babysit-merge".
---

Merge the PR for the current branch, if it needs to be updated first, then
merge in the latest base, fix any eventual merge conflicts first. Then
watch it deploy, confirm nothing broke. Revert on trouble, settle the
thread when it's clean.

Work out how this repo deploys: read `.github/workflows/` (look for jobs
triggered on push to the base branch), and any `deploy`/`helm`/`argocd`
references. At Volumental, services usually build an image on merge, and
ArgoCD deploys tags from the `helm-chart-values` GitOps repo.

Once the new version is live, watch it for ~15 minutes (longer for
low-traffic services) and compare against the baseline.

Also look at any error tracker or alerts the repo/README points to, and any
smoke or e2e checks the repo has for deployed environments.

Never force-push, never bypass branch protection or required reviews.
