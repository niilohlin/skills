---
name: retro
disable-model-invocation: true
description: Used to self improve the rest of my skills
---

# Retro

Look through historical t3code threads across the fleet for the last week or
whatever the user specified, and try to find improvements to the environment and
to improve future runs. Consider:

- Navigation: Did the agent find what it was looking for quickly.
- Automated checks: Were there errors that could have been caught by linters,
  tests, or other checks etc.
- Coding standards: should the **reviewer agent** be given a new rule to enforce?
- Global AGENTS.md: are there any steering instructions that should be moved to coding standards (or automated checks) instead?
- Tool economy: did the agent make expensive tool calls that could be streamlined?
- Information access: look for opportunities to increase the agent's access to information. Teeing dev server logs, readonly access to third-party services. _Use when_ a crucial piece of information was not available to the agent.

Present these candidates to the user, in order of severity.
