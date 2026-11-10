---
name: t3-install
description: Use when asked to "install t3 code" or "t3-install".
---

# t3-install

Repo layout: the main checkout is `~/personal/t3code` on `main`.
Remotes: `origin` is the fork `niilohlin/t3code`, `upstream` is `pingdotgg/t3code`.

You are running inside the app you are about to replace. Never kill it. Install the
new bundle and tell the user to quit and relaunch.

1. Commit the worktree
2. Merge into main and push
3. Merge upstream, On conflicts, resolve each file
4. Test it and make sure it works
5. Build and install
6. Report - Tell the user what happened. Do not relaunch it yourself.
