---
name: babysit-merge
description: Use when the user says "babysit merge", "merge and watch the deploy" or "/babysit-merge".
---

Merge the PR for the current branch, then watch it deploy, confirm nothing
broke. Revert on trouble.

To merge: if the branch is behind the base (visa requires branches to be up to
date), merge the latest base in once and push, fixing any conflicts. Then
queue the merge with `gh pr merge <pr> --auto --merge` (use the repo's usual
merge method) and watch the PR with `watch_pull_request` until it merges. If
master moves again before it merges, update once more; don't loop on it by
hand.

Work out how this repo deploys: read `.github/workflows/` (look for jobs
triggered on push to the base branch), and any `deploy`/`helm`/`argocd`
references. At Volumental, a merge or a GitHub release only builds an image;
nothing is deployed until the tag lands in `helm-chart-values`. Deploy with
the Cosmos MCP (service ids are in the service map in `~/work/CLAUDE.md`):

1. `mcp__cosmos__get_deploy_state` to see the requested, running and newly
   published tags.
2. `mcp__cosmos__deploy` with the new tag. Staging deploys straight away;
   production returns `pending_review` and a helm-chart-values PR that a
   human must merge. Give the user that PR's URL.
3. Poll `get_deploy_state` until the running tag is the new one and ArgoCD
   reports Synced/Healthy. If it stays OutOfSync after the PR merged, tell
   the user (it may need a manual Sync) instead of waiting it out.

Never hand-write helm-chart-values PRs, and never start a rollout watcher
before the deploy has been requested. If the Cosmos tools aren't available,
stop and tell the user to add the MCP
(`claude mcp add --transport http --scope user cosmos https://platform-api.volumental.dev/mcp`).
If master has other people's unreleased PRs, ask before cutting a release.

Once the new version is live, watch it for ~15 minutes (longer for
low-traffic services) and compare against the baseline.

Also look at any error tracker or alerts the repo/README points to, and any
smoke or e2e checks the repo has for deployed environments.

Never force-push, never bypass branch protection or required reviews.

## Watching

Never tell the user you are watching, waiting or monitoring unless something
is actually registered to wake you: a PR watch (`watch_pull_request`), a
`Monitor`, or a background Bash task whose ID the tool returned. Name it when
you say it ("watching via background task bxyz123"). Pass that exact returned
ID to `t3_background_wait`; never a guessed or old one. If nothing is
registered, say what you'll check and end the turn instead.

Settle the t3code thread when everything is merged and no issues have been
detected unless the user specifies otherwise

If a linear issue is associated with the issue then change its status to 'done'
