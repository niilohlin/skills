#!/bin/sh
# Symlink every skill in this repo into the folders agents read from.
set -e
cd "$(dirname "$0")"
for dir in "$HOME/.agents/skills" "$HOME/.claude/skills"; do
  mkdir -p "$dir"
  for skill in */; do
    [ -f "$skill/SKILL.md" ] || continue
    ln -sfn "$PWD/${skill%/}" "$dir/${skill%/}"
  done
done
echo "Installed: $(ls -d */ 2>/dev/null | tr -d / | tr '\n' ' ')"
