---
name: hillclimb
disable-model-invocation: true
description: Hillclimb towards a measure with multiple agents in parallel
---

If an objective measure is given, use that as an objective goal. If a subjective
measure is given, generate subagents without your context to score your
solution, and try to optimize for that solution. Generate 3 judges and
try to go for 10/10.

Create wacky and crazy ideas, don't be afraid to boil the ocean. Create
subagents in separate worktrees that implements those ideas and then hillclimb
towards the goal. For every pass combine the learnings from the different
subagents and come up with new ones. Do at most 10 passes or stop when you don't
see meaningful improvement.
