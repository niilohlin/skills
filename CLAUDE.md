When referencing a GitHub PR, issue, or commit, always write the full URL. Never write just the number or a bare `owner/repo#123`.

Username on my 2 other machines (dellburk, niils-omarchy) is niilohlin.

Before making a PR. Let the stop hook run and commit the comment remover
changes.

You can attach videos to PRs via `gh pr edit --attach`

Don't write code comments. A hook strips the ones you add anyway, which
costs an extra commit. Put explanations in the commit message or PR.

Always pass an explicit kube context: `kubectl --context <ctx>`, `helm
--kube-context <ctx>`. Never rely on or change the current context
(`kubectl config use-context`). A hook blocks commands without one.

Never use `pkill -f` / `pgrep -f`: the pattern matches your own shell and
kills it (exit 144). When starting a long-running process (vite, tilt, dev
servers), save its PID: `cmd > log 2>&1 & echo $! > .name.pid`, and stop it
with `kill "$(cat .name.pid)"`.
