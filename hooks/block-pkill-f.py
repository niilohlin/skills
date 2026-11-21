#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shellwords import commands, head  # noqa: E402

MSG = """Blocked: `{cmd}` matches the full command line, so it also matches the shell running it (and other sessions' processes). The shell dies with exit 144 and anything chained after it never runs.
Instead:
- start long-running processes with `cmd & echo $! > .<name>.pid` and stop them with `kill "$(cat .<name>.pid)"`
- or kill by port: `kill $(lsof -ti:PORT)` (macOS) / `fuser -k PORT/tcp` (Linux)
- or, if you must match by command line, use the bracket trick: `pkill -f "[v]ite --port 4003"`"""

FULL_FLAG = re.compile(r"^(?:-[a-zA-Z]*f[a-zA-Z]*|--full)$")


def offending(command):
    for w in commands(command):
        i = head(w)
        if i >= len(w) or w[i].rsplit("/", 1)[-1] not in ("pkill", "pgrep"):
            continue
        args = w[i + 1:]
        if any(FULL_FLAG.match(a) for a in args) and not any("[" in a for a in args):
            return " ".join(w[i:])
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    if data.get("tool_name") != "Bash":
        return 0
    hit = offending((data.get("tool_input") or {}).get("command") or "")
    if hit:
        print(MSG.format(cmd=hit), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        bad = [
            'pkill -f "vite --port 4003"; git commit -am x',
            "kill $(pgrep -f tilt)",
            "pgrep -af 'react-router dev'",
            "cd x && pkill --full fastapi",
            "ls\npkill -f vite",
            "sudo pkill -f vite",
            "echo `pkill -f a`",
        ]
        good = [
            'pkill -f "[v]ite --port 4003"',
            "pkill node",
            "pgrep -l vite",
            'kill "$(cat .vite.pid)"',
            "echo pkill-free -f",
            'git commit -m "- block pkill -f/pgrep -f; and pkill -f x" && git push',
            "grep -n 'pkill -f' notes.md",
        ]
        for c in bad:
            assert offending(c), c
        for c in good:
            assert not offending(c), c
        print("ok")
        sys.exit(0)
    sys.exit(main())
