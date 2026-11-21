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
python3 - "$HOME/.claude/settings.json" <<'EOF'
import json, os, sys
path = sys.argv[1]
settings = json.load(open(path)) if os.path.exists(path) else {}
pre = settings.setdefault("hooks", {}).setdefault("PreToolUse", [])
changed = False
for name in ("block-pkill-f.py", "require-kube-context.py"):
    cmd = "$HOME/.claude/hooks/" + name
    if not any(h.get("command") == cmd for e in pre for h in e.get("hooks", [])):
        pre.append({"matcher": "Bash", "hooks": [{"type": "command", "command": cmd, "timeout": 10}]})
        changed = True
stop = settings["hooks"].setdefault("Stop", [])
strip = "$HOME/.claude/hooks/run-stripper.sh"
for e in stop:
    for h in e.get("hooks", []):
        if "strip-added-comments.py" in h.get("command", ""):
            h["command"] = strip
            changed = True
if not any(h.get("command") == strip for e in stop for h in e.get("hooks", [])):
    stop.append({"hooks": [{"type": "command", "command": strip}]})
    changed = True
if changed:
    json.dump(settings, open(path, "w"), indent=2)
    print("Updated hooks in", path)
EOF
echo "Installed: $(ls -d */ 2>/dev/null | tr -d / | tr '\n' ' ')"
