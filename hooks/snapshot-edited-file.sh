#!/usr/bin/env bash
# PreToolUse hook for Write|Edit|MultiEdit|Bash.
# Write/Edit: saves the pre-edit content of every file Claude touches, so the
# Stop hook can tell which comments Claude added from which were already there.
# First snapshot of a path wins; the Stop hook clears the directory when it runs.
# Bash: records the directories the turn works in, so the Stop hook knows which
# git repos to check for commits made this turn. Before `git push` and
# `gh pr create` it runs the stripper and blocks the command if it removed
# anything (prefix the command with CLAUDE_KEEP_COMMENTS=1 to skip that).

payload=$(cat)

sid=$(printf '%s' "$payload" | jq -r '.session_id // "nosession"')
tool=$(printf '%s' "$payload" | jq -r '.tool_name // empty')

dir="$HOME/.claude/comment-stripper/$sid"
mkdir -p "$dir" || exit 0
[ -e "$dir/start" ] || date +%s >"$dir/start"

if [ "$tool" = Bash ]; then
  cwd=$(printf '%s' "$payload" | jq -r '.cwd // empty')
  cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')
  {
    printf '%s\n' "$cwd"
    printf '%s' "$cmd" | grep -oE '\b(cd|git -C) +[^ ;&|)]+' | awk '{print $NF}' | tr -d "'\"" |
      while IFS= read -r t; do
        case "$t" in /* | "~"* | '$'*) printf '%s\n' "$t" ;; *) printf '%s\n' "$cwd/$t" ;; esac
      done
  } >>"$dir/dirs"

  if printf '%s' "$cmd" | grep -qE '\b(git push|gh pr create)\b' &&
    ! printf '%s' "$cmd" | grep -q 'CLAUDE_KEEP_COMMENTS=1'; then
    export PATH="/opt/homebrew/bin:$PATH"
    command -v uv >/dev/null 2>&1 || exit 0
    printf '%s' "$payload" | uv run --quiet --script "$(dirname "$0")/strip-added-comments.py" --gate
    exit $?
  fi
  exit 0
fi

fp=$(printf '%s' "$payload" | jq -r '.tool_input.file_path // empty')

[ -n "$fp" ] || exit 0

key=$(printf '%s' "$fp" | shasum -a 256 | cut -d' ' -f1)
[ -e "$dir/$key.path" ] && exit 0

printf '%s' "$fp" >"$dir/$key.path"
if [ -f "$fp" ]; then
  cp "$fp" "$dir/$key.orig" 2>/dev/null || : >"$dir/$key.orig"
else
  # New file: empty baseline means every line counts as added.
  : >"$dir/$key.orig"
fi

exit 0
