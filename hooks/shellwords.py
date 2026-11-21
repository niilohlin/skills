import re
import shlex

OPS = ";&|()\n`"
WRAPPERS = {"sudo", "time", "timeout", "watch", "xargs", "env", "nice", "exec", "command", "!"}


def commands(cmd):
    lx = shlex.shlex(cmd, posix=True, punctuation_chars=OPS)
    lx.whitespace = " \t\r"
    lx.whitespace_split = True
    cur = []
    try:
        for tok in lx:
            if tok and all(c in OPS for c in tok):
                if cur:
                    yield cur
                cur = []
            elif tok.endswith("$"):
                if tok[:-1]:
                    cur.append(tok[:-1])
                if cur:
                    yield cur
                cur = []
            else:
                cur.append(tok)
    except ValueError:
        pass
    if cur:
        yield cur


def head(words):
    i = 0
    while i < len(words) and re.match(r"^\w+=", words[i]):
        i += 1
    while i < len(words) and words[i] in WRAPPERS:
        i += 1
        while i < len(words) and (words[i].startswith("-") or re.match(r"^\d", words[i])):
            i += 1
    return i
