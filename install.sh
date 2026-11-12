#!/bin/sh
# Symlink this repo's skills, hooks and CLAUDE.md into the folders agents read from.
set -e
cd "$(dirname "$0")"
for dir in "$HOME/.agents/skills" "$HOME/.claude/skills"; do
  mkdir -p "$dir"
  for skill in */; do
    [ -f "$skill/SKILL.md" ] || continue
    ln -sfn "$PWD/${skill%/}" "$dir/${skill%/}"
  done
done
link() {
  if [ -e "$2" ] && [ ! -L "$2" ]; then mv "$2" "$2.bak"; fi
  ln -sfn "$1" "$2"
}
link "$PWD/hooks" "$HOME/.claude/hooks"
link "$PWD/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
echo "Installed: $(ls -d */ 2>/dev/null | tr -d / | tr '\n' ' ')"
