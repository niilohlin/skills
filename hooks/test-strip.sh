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
printf 'package p\n\ntype T struct {\n\tName string\n\thidden int\n\tBase\n}\n\ntype u int\n\nfunc F() {}\n' >g.go
printf 'export const a = 1;\nexport const b = 2;\nexport const c = 3;\n' >h.ts
git add . && git commit -qm base
sleep 1

hook "cd $repo && echo start" || fail "plain command blocked"

printf '# theirs\ny = 2\n' >b.py
git add . && git -c user.email=other@example.com commit -qm theirs

printf 'x = 2  # was here\n# mine\nz = 3  # mine too\n' >a.py
printf '# /// script\n# dependencies = ["x"]\n# ///\n# mine\nprint(1)\n' >c.py
printf '# doc one\n# doc two changed\ndef f():\n    pass\n' >d.py
printf '# untouched\nx = 2\n' >e.py
printf 'package p\n\n// T doc\ntype T struct {\n\t// Name doc\n\tName string\n\t// hidden doc\n\thidden int\n\t// Base doc\n\tBase\n}\n\n// u doc\ntype u int\n\n// F doc\nfunc F() {}\n' >g.go
printf '/** @internal */\nexport const a = 1;\n/** @deprecated use c */\nexport const b = 2;\n/** plain */\nexport const c = 3;\n' >h.ts
git add . && git commit -qm mine

hook "cd $repo && git push" 2>/dev/null && fail "gate let comments through"
[ "$(cat a.py)" = "$(printf 'x = 2  # was here\nz = 3')" ] || fail "a.py: $(cat a.py)"
[ "$(cat b.py)" = "$(printf '# theirs\ny = 2')" ] || fail "b.py: $(cat b.py)"
[ "$(cat d.py)" = "$(printf 'def f():\n    pass')" ] || fail "d.py: edited block not removed whole: $(cat d.py)"
[ "$(cat e.py)" = "$(printf '# untouched\nx = 2')" ] || fail "e.py: $(cat e.py)"
[ "$(cat g.go)" = "$(printf 'package p\n\n// T doc\ntype T struct {\n\t// Name doc\n\tName string\n\thidden int\n\t// Base doc\n\tBase\n}\n\ntype u int\n\nfunc F() {}')" ] || fail "g.go: $(cat g.go)"
[ "$(cat h.ts)" = "$(printf '/** @internal */\nexport const a = 1;\n/** @deprecated use c */\nexport const b = 2;\nexport const c = 3;')" ] || fail "h.ts: $(cat h.ts)"
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
