#!/usr/bin/env -S uv run --quiet --script
# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["tree-sitter>=0.23", "tree-sitter-language-pack>=0.9"]
# ///
"""Stop hook: delete the comments Claude added during the turn.

Pairs with snapshot-edited-file.sh, which stores each touched file's pre-edit
content under ~/.claude/comment-stripper/<session>/. Here we diff old vs new,
parse the new file with tree-sitter, and remove only those comment nodes that
sit entirely inside lines the diff marks as added. Comments that were already in
the file survive, as do load-bearing ones (linter pragmas, build tags, licenses).

Edits made through the shell (python heredocs, sed -i) never pass the snapshot
hook, so a second pass covers git: in every repo the turn worked in, lines that
`git blame` attributes to commits you authored and committed since the turn
started are treated as added. Only committed lines are touched there, so
nothing it removes is unrecoverable. Uncommitted shell edits are picked up once
they are committed.

With --gate (run by snapshot-edited-file.sh before `git push` / `gh pr create`)
the state is kept and the exit code is 2 when anything was stripped, which
blocks the command until the result is committed.

Set CLAUDE_KEEP_COMMENTS=1 to turn the whole thing off for a session.
"""

import difflib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

KEEP_TODOS = False

STATE_ROOT = Path.home() / ".claude" / "comment-stripper"
STALE_AFTER = 3 * 24 * 3600

EXT_LANG = {
    ".py": "python", ".pyi": "python",
    ".ts": "typescript", ".mts": "typescript", ".cts": "typescript",
    ".tsx": "tsx", ".jsx": "javascript",
    ".js": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".go": "go", ".rs": "rust",
    ".tf": "hcl", ".tfvars": "hcl", ".hcl": "hcl",
    ".yaml": "yaml", ".yml": "yaml",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".c": "c", ".h": "c",
    ".cc": "cpp", ".cpp": "cpp", ".cxx": "cpp", ".hpp": "cpp", ".hh": "cpp",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin", ".swift": "swift",
    ".rb": "ruby", ".php": "php", ".lua": "lua", ".scala": "scala",
    ".cs": "csharp", ".ex": "elixir", ".exs": "elixir", ".zig": "zig",
    ".css": "css", ".scss": "scss", ".sql": "sql", ".toml": "toml",
    ".proto": "proto", ".graphql": "graphql", ".gql": "graphql",
    ".vue": "vue", ".svelte": "svelte", ".dart": "dart", ".hs": "haskell",
    ".nix": "nix", ".pl": "perl", ".r": "r", ".sol": "solidity",
    ".gradle": "groovy", ".groovy": "groovy", ".erl": "erlang",
    ".clj": "clojure", ".cljs": "clojure", ".ml": "ocaml",
}

NAME_LANG = {
    "dockerfile": "dockerfile",
    "makefile": "make",
    "justfile": "just",
}

_KEEP = [
    r"^#!",
    r"coding[:=]\s*[-\w.]+",
    r"\bnoqa\b",
    r"\btype:\s*ignore\b",
    r"\b(pragma|pylint|mypy|ruff|flake8|pyright|pytype):",
    r"\b(nosec|nosemgrep|noinspection)\b",
    r"\bfmt:\s*(on|off|skip)\b",
    r"\beslint-(disable|enable)",
    r"\bts-(ignore|expect-error|nocheck|check)\b",
    r"\b(prettier-ignore|biome-ignore|dprint-ignore|deno-lint-ignore|deno-fmt-ignore)\b",
    r"\b(istanbul|c8|v8)\s+ignore\b",
    r"\bgo:[a-z]+",
    r"\+build\b",
    r"\bnolint\b",
    r"\b(tflint-ignore|tfsec:|checkov:skip|terraform:)\b",
    r"\bshellcheck\s+(disable|source|shell|enable)\b",
    r"\bSPDX-License-Identifier\b",
    r"\bcopyright\b",
    r"\blicen[cs]ed under\b",
    r"@(jsx|jsxImportSource|jsxRuntime|flow|license|preserve|generated)\b",
    r"^\s*/\*\s*(global|eslint|exported)\b",
    r"<reference\s",
    r"\bsourceMappingURL\b",
    r"\bcodegen\b|\bDO NOT EDIT\b|\bauto-?generated\b",
    r"\blanguage=\w+",
    r"\bcspell:|\bspell-checker:",
]
if KEEP_TODOS:
    _KEEP.append(r"\b(TODO|FIXME|XXX|HACK|NOTE!|WARNING!)\b")

KEEP_RE = re.compile("|".join(_KEEP), re.IGNORECASE)

PEP723_RE = re.compile(r"^# /// \w+$.*?^# ///$", re.MULTILINE | re.DOTALL)
BLAME_HEADER_RE = re.compile(r"^([0-9a-f]{40}) \d+ (\d+)")


def language_for(path: Path) -> str | None:
    lang = EXT_LANG.get(path.suffix.lower())
    if lang:
        return lang
    return NAME_LANG.get(path.name.lower())


def added_rows(old_text: str, new_text: str) -> set[int]:
    """0-indexed rows of new_text that the diff considers new."""
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    rows: set[int] = set()
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines, autojunk=False)
    for tag, _i1, _i2, j1, j2 in matcher.get_opcodes():
        if tag in ("insert", "replace"):
            rows.update(range(j1, j2))
    return rows


def comment_nodes(root):
    """Top-level comment nodes; nested ones are already covered by their parent."""
    out = []
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type.endswith("comment"):
            out.append(node)
            continue
        stack.extend(node.children)
    return out


def normalize(text: str) -> str:
    return " ".join(text.split())


def previous_comments(old_text: str, parser) -> Counter:
    """Comment texts already in the file before Claude touched it."""
    try:
        root = parser.parse(old_text.encode("utf-8")).root_node
    except Exception:
        return Counter()
    src = old_text.encode("utf-8")
    return Counter(
        normalize(src[n.start_byte:n.end_byte].decode("utf-8", "replace"))
        for n in comment_nodes(root)
    )


def error_count(root) -> int:
    if not root.has_error:
        return 0
    n = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if node.type == "ERROR" or node.is_missing:
            n += 1
        stack.extend(node.children)
    return n


def strip_file(path: Path, old_text: str, parser_for, only_rows: set[int] | None = None) -> int:
    """Rewrite path without Claude's new comments. Returns comments removed.

    only_rows, when given, narrows the added rows to that set.
    """
    try:
        new_text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return 0
    if new_text == old_text:
        return 0

    lang = language_for(path)
    if lang is None:
        return 0
    parser = parser_for(lang)
    if parser is None:
        return 0

    src = new_text.encode("utf-8")
    tree = parser.parse(src)
    before_errors = error_count(tree.root_node)

    fresh = added_rows(old_text, new_text)
    if only_rows is not None:
        fresh &= only_rows
    for block in PEP723_RE.finditer(new_text):
        first = new_text.count("\n", 0, block.start())
        fresh -= set(range(first, first + block.group().count("\n") + 1))
    if not fresh:
        return 0
    # Editing a line that already carried a comment makes difflib call that row
    # added. Anything whose text was in the file before is the user's, not ours.
    preexisting = previous_comments(old_text, parser)

    lines = new_text.splitlines(keepends=True)
    line_start = []
    offset = 0
    for line in lines:
        line_start.append(offset)
        offset += len(line.encode("utf-8"))

    drop_rows: set[int] = set()
    edits: dict[int, list[tuple[int, int]]] = {}
    removed = 0

    for node in comment_nodes(tree.root_node):
        r0, r1 = node.start_point[0], node.end_point[0]
        if r1 >= len(lines):
            continue
        if any(r not in fresh for r in range(r0, r1 + 1)):
            continue
        text = src[node.start_byte:node.end_byte].decode("utf-8", "replace")
        if KEEP_RE.search(text):
            continue
        key = normalize(text)
        if preexisting[key]:
            preexisting[key] -= 1
            continue

        head = src[line_start[r0]:node.start_byte]
        tail_end = line_start[r1] + len(lines[r1].encode("utf-8"))
        tail = src[node.end_byte:tail_end]
        standalone = head.strip() == b"" and tail.strip() == b""

        if standalone:
            drop_rows.update(range(r0, r1 + 1))
            removed += 1
        elif r0 == r1:
            edits.setdefault(r0, []).append((node.start_byte, node.end_byte))
            removed += 1
        # Inline block comment spanning several lines: rare, not worth the risk.

    if not removed:
        return 0

    for row, spans in edits.items():
        raw = lines[row].encode("utf-8")
        base = line_start[row]
        for start, end in sorted(spans, reverse=True):
            raw = raw[: start - base] + raw[end - base :]
        rebuilt = raw.decode("utf-8")
        body, sep, eol = rebuilt.partition("\n")
        body = body.rstrip()
        if body.strip() == "":
            drop_rows.add(row)
        else:
            lines[row] = body + sep + eol

    kept = [(i, l) for i, l in enumerate(lines) if i not in drop_rows]
    result: list[str] = []
    for idx, (row, line) in enumerate(kept):
        blank = line.strip() == ""
        if blank and result and result[-1].strip() == "" and row - kept[idx - 1][0] > 1:
            continue  # blank / removed comment / blank -> single blank
        result.append(line)

    out = "".join(result)
    if out == new_text:
        return 0
    if error_count(parser.parse(out.encode("utf-8")).root_node) > before_errors:
        return 0

    path.write_text(out, encoding="utf-8")
    return removed


def sweep_stale():
    now = time.time()
    for d in STATE_ROOT.iterdir():
        if d.is_dir() and now - d.stat().st_mtime > STALE_AFTER:
            shutil.rmtree(d, ignore_errors=True)


def git(repo, *args) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.decode("utf-8", "replace") if r.returncode == 0 else None


def session_repos(state: Path, cwd: str | None) -> list[Path]:
    """Git roots of the directories the turn's shell commands ran in."""
    dirs = [cwd] if cwd else []
    try:
        dirs += (state / "dirs").read_text(encoding="utf-8").splitlines()
    except OSError:
        pass
    roots: dict[str, None] = {}
    for d in dict.fromkeys(dirs):
        d = os.path.expandvars(os.path.expanduser(d.strip()))
        if not os.path.isdir(d):
            continue
        top = git(d, "rev-parse", "--show-toplevel")
        if top:
            roots[top.strip()] = None
    return [Path(r) for r in roots]


def turn_commits(repo: Path, start: int) -> tuple[list[str], set[str]]:
    """Commits on HEAD made here since the turn started, newest first, and their files.

    Author and committer must both be the local user: that leaves out pulled
    and merged work, squash merges made on GitHub, and other people's commits
    that a rebase rewrote.
    """
    me = (git(repo, "config", "user.email") or "").strip()
    out = git(repo, "log", "--no-merges", "-n", "200", "--name-only", "--format=%x00%H %at %ae %ce")
    shas: list[str] = []
    files: set[str] = set()
    if not me or not out:
        return shas, files
    for block in out.split("\0")[1:]:
        head, _, names = block.partition("\n")
        try:
            sha, at, ae, ce = head.split(" ")
            mine = ae == me and ce == me and int(at) >= start
        except ValueError:
            continue
        if mine:
            shas.append(sha)
            files.update(n for n in names.splitlines() if n)
    return shas, files


def git_pass(state: Path, cwd: str | None, parser_for) -> list[tuple[str, int]]:
    try:
        start = int((state / "start").read_text().strip())
    except (OSError, ValueError):
        return []
    touched: list[tuple[str, int]] = []
    for repo in session_repos(state, cwd):
        shas, files = turn_commits(repo, start)
        if not shas:
            continue
        mine = set(shas)
        for rel in sorted(files):
            path = repo / rel
            if not path.is_file() or language_for(path) is None:
                continue
            blame = git(repo, "blame", "--porcelain", "--", rel)
            if blame is None:
                continue
            rows = {
                int(m.group(2)) - 1
                for line in blame.splitlines()
                if (m := BLAME_HEADER_RE.match(line)) and m.group(1) in mine
            }
            if not rows:
                continue
            old_text = git(repo, "show", f"{shas[-1]}^:{rel}") or ""
            try:
                n = strip_file(path, old_text, parser_for, rows)
            except Exception:
                continue
            if n:
                touched.append((path.name, n))
    return touched


def snapshot_pass(state: Path, parser_for) -> list[tuple[str, int]]:
    touched: list[tuple[str, int]] = []
    for marker in sorted(state.glob("*.path")):
        orig = marker.with_suffix(".orig")
        if not orig.exists():
            continue
        path = Path(marker.read_text(encoding="utf-8"))
        if not path.is_file():
            continue
        try:
            old_text = orig.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            n = strip_file(path, old_text, parser_for)
        except Exception:
            continue
        if n:
            touched.append((path.name, n))
    return touched


def main() -> int:
    if os.environ.get("CLAUDE_KEEP_COMMENTS"):
        return 0
    gate = "--gate" in sys.argv
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}
    session = payload.get("session_id") or "nosession"
    state = STATE_ROOT / session
    if not state.is_dir():
        return 0

    from tree_sitter_language_pack import get_parser

    cache: dict[str, object] = {}

    def parser_for(lang: str):
        if lang not in cache:
            try:
                cache[lang] = get_parser(lang)
            except Exception:
                cache[lang] = None
        return cache[lang]

    touched = snapshot_pass(state, parser_for) + git_pass(state, payload.get("cwd"), parser_for)

    if not gate:
        shutil.rmtree(state, ignore_errors=True)
        try:
            sweep_stale()
        except OSError:
            pass

    if not touched:
        return 0
    total = sum(n for _, n in touched)
    where = ", ".join(f"{name} ({n})" for name, n in touched[:6])
    if len(touched) > 6:
        where += f", +{len(touched) - 6} more"
    message = f"Stripped {total} added comment(s): {where}"
    if gate:
        print(
            f"{message}. Commit that, then run the command again "
            "(prefix it with CLAUDE_KEEP_COMMENTS=1 to keep the comments).",
            file=sys.stderr,
        )
        return 2
    print(json.dumps({"systemMessage": message, "suppressOutput": True}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
