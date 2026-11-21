#!/bin/sh
export PATH="$HOME/.local/bin:$HOME/.local/share/mise/shims:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
command -v uv >/dev/null 2>&1 || exit 0
exec uv run --quiet --script "$(dirname "$0")/strip-added-comments.py" "$@"
