---
name: astra-review
description: Use before opening or updating a PR, or when asked for an "Astra review" / "Astra reviewer" / pre-PR review.
---

# Astra review

An independent read-only review of your committed change by a Codex model, run
before the PR is opened.

## 1. Pin what gets reviewed

Commit everything first (including the comment-remover's changes). Then:

```sh
git fetch origin
BASE=$(git merge-base origin/<default-branch> HEAD)
HEAD_SHA=$(git rev-parse HEAD)
```

Never brief with bare `HEAD` or local `master`: you may commit again while the
review runs, and local `master` is often stale.

## 2. Start it

Call `delegate_task` (load it with ToolSearch first) with:

- `target`: `{ providerInstanceId: "codex", model: "gpt-6.2-astra", options: { reasoningEffort: "high" } }`
- `role`: `"review"`, `title`: `"Astra review: <topic>"`
- `task`: the brief below

Run `orchestrator_capabilities` first only if the call errors. If Astra is
unavailable (out of credits, provider error), use a fresh Claude reviewer (the
`Agent` tool, general-purpose) with the same brief, and say so in your report.

## 3. The brief

Give it the code, not your conclusion. Fill in every line:

```
Act as the review sub-agent. Read-only: no edits, commits, pushes or writes in the checkout.
Checkout: <absolute worktree path>
Diff: git diff <BASE>...<HEAD_SHA>   (commit <HEAD_SHA>; ignore later commits)
Repo rules: read CLAUDE.md / AGENTS.md at the repo root.
Sibling repos, if relevant: <absolute paths>
You may run: <exact test/lint/typecheck commands; say if deps are installed>
Do not run: <staging, e2e, docker, anything that writes outside the checkout>

Goal: <one paragraph: what the change is for, linked issue/alert/spec URLs>
Treat my description as a claim to verify, not a fact. If the change is justified by an
incident or bug cause, check that cause yourself from the raw evidence.

Standing checks: silent fallbacks/skips that swallow real failures, unbounded waits,
async races, set without unset / create without teardown, input validation at the
boundary, secrets, shared resources across worktrees/users, idempotent automation,
native a11y, docs or comments the diff makes false.

Output: findings ranked P0 (breaks prod/data) / P1 (real bug) / P2 (risk) / P3 (nit).
Each: repo-relative file:line, the concrete failure scenario, the smallest fix.
Then a "Not verified" section. If there is nothing, say "No findings" plainly.
```

## 4. Handle the result

- **Empty or missing result** (null final message, an error, or only a status
  line): the review failed. Run it once more; if it fails again, tell the user
  and don't present the change as reviewed.
- Read only the reviewer's final message; mid-run remarks may be retracted.
- **Fix** every P0 and P1, and any finding about blast radius or errors/telemetry
  being hidden. To dismiss one of those, ask the user first.
- P2/P3: use your judgement. Don't ask about these.
- If you fixed anything non-trivial, re-review the new commit with the same brief.

## 5. Report

In your message to the user (and the PR description), list every finding as:

- **Fixed:** <finding> — <commit or one-line what changed>
- **Dismissed:** <finding> — <one-line reason>

Never write "taking all of them" unless every one is under Fixed.
