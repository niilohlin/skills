#!/usr/bin/env bash
# Self-check for the comment stripper's git pass and push gate. Run: hooks/test-strip.sh
set -u
here=$(cd "$(dirname "$0")" && pwd)
sid="test-strip-$$"
repo=$(mktemp -d)
loose=$(mktemp -d)
trap 'rm -rf "$repo" "$loose" "$HOME/.claude/comment-stripper/$sid"' EXIT
fail() { echo "FAIL: $1"; exit 1; }
hook() { printf '{"session_id":"%s","tool_name":"Bash","cwd":"/","tool_input":{"command":"%s"}}' "$sid" "$1" | "$here/snapshot-edited-file.sh"; }

cd "$repo" && git init -q && git config user.email me@example.com && git config user.name me
printf 'x = 1  # was here\n' >a.py
printf '# doc one\n# doc two\ndef f():\n    pass\n' >d.py
printf '# untouched\nx = 1\n' >e.py
git add . && git commit -qm base
sleep 1

hook "cd $repo && echo start" || fail "plain command blocked"

printf '# theirs\ny = 2\n' >b.py
git add . && git -c user.email=other@example.com commit -qm theirs

printf 'x = 2  # was here\n# mine\nz = 3  # mine too\n' >a.py
printf '# /// script\n# dependencies = ["x"]\n# ///\n# mine\nprint(1)\n' >c.py
printf '# doc one\n# doc two changed\ndef f():\n    pass\n' >d.py
printf '# untouched\nx = 2\n' >e.py
git add . && git commit -qm mine

hook "cd $repo && git push" 2>/dev/null && fail "gate let comments through"
[ "$(cat a.py)" = "$(printf 'x = 2  # was here\nz = 3')" ] || fail "a.py: $(cat a.py)"
[ "$(cat b.py)" = "$(printf '# theirs\ny = 2')" ] || fail "b.py: $(cat b.py)"
[ "$(cat d.py)" = "$(printf 'def f():\n    pass')" ] || fail "d.py: edited block not removed whole: $(cat d.py)"
[ "$(cat e.py)" = "$(printf '# untouched\nx = 2')" ] || fail "e.py: $(cat e.py)"
[ "$(cat c.py)" = "$(printf '# /// script\n# dependencies = ["x"]\n# ///\nprint(1)')" ] || fail "c.py: $(cat c.py)"

git commit -qam stripped
hook "cd $repo && git push" || fail "gate blocked a clean push"
hook "cd $repo && CLAUDE_KEEP_COMMENTS=1 git push" || fail "opt-out ignored"

for f in f1 f2; do
  printf '{"session_id":"%s","tool_name":"Write","tool_input":{"file_path":"%s"}}' "$sid" "$repo/$f.py" | "$here/snapshot-edited-file.sh"
  printf '# new\nv = 1\n' >"$f.py"
done
printf '{"session_id":"%s","tool_name":"Write","tool_input":{"file_path":"%s"}}' "$sid" "$loose/bench.sh" | "$here/snapshot-edited-file.sh"
printf '# scratch note\necho hi\n' >"$loose/bench.sh"
printf '{"session_id":"%s","cwd":"/"}' "$sid" | "$here/run-stripper.sh" || fail "stop hook failed"
[ "$(cat "$loose/bench.sh")" = "$(printf '# scratch note\necho hi')" ] || fail "stripped a file outside git: $(cat "$loose/bench.sh")"
for f in f1 f2; do [ "$(cat $f.py)" = "v = 1" ] || fail "$f.py snapshot pass missed: $(cat $f.py)"; done
[ ! -e "$HOME/.claude/comment-stripper/$sid" ] || fail "stop hook kept state"
echo ok
