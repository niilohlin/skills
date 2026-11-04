---
name: whatever-it-takes
description: Go all out on a hard problem. Brainstorm many wild, unconventional ideas, spawn a subagent per idea to actually try it (each in its own worktree), then take the learnings and combine the best parts into one solution. Full rewrites and boiling the ocean are allowed. Use when the user says "whatever it takes", "go crazy", "try everything", "boil the ocean", or is stuck after normal approaches failed.
---

# Whatever It Takes

Do whatever crazy, wacky ideas you can. Try many of them for real, learn from
all of them, and combine the best into one result. Don't be afraid to boil the
ocean or do a full rewrite.

## 1. Understand the goal

Read the task and the code it touches. Write down, in one or two lines, what
"done" means and how you'll measure it (a test, a benchmark, a script, a
screenshot). Every experiment is judged against that.

## 2. Go wide on ideas

Brainstorm at least 5–8 genuinely different approaches. Include:

- The obvious fix.
- The full rewrite from scratch.
- A different language, library, algorithm, or architecture.
- Deleting the feature/layer and solving it somewhere else.
- The "that's insane, but what if…" idea.
- Inverting the problem (do it at build time, at the DB, in the client, never).

No idea is too big. Don't filter for effort, filter only for "could this
plausibly win?"

## 3. Try them all in parallel

Spawn one subagent per idea, all in a single message so they run concurrently.
Give each its own isolated checkout (`isolation: "worktree"` or equivalent) so
they can rewrite freely without stepping on each other.

Each brief should state: the goal, the success check, the one idea to commit
to fully (no hedging back to the safe option), and what to report back:

- Did it work? Measured result against the success check.
- What was surprisingly good or bad.
- The key insight, even if the idea failed.
- Branch/worktree with the code.

## 4. Combine the learnings

Read every report. Lay out results side by side. Then build the final solution
by taking the winning core and grafting on the best insights from the others.
If two ideas combine into something better than either, spawn another round
of subagents to try the combinations. Repeat until results stop improving.

## 5. Ship it

Implement the combined solution on the main branch, run the success check,
and report: what was tried, what won, what was stolen from the losers, and
the measured result. Clean up experiment worktrees/branches you don't need.
