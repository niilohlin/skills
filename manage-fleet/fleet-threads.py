#!/usr/bin/env python3
"""Search or read T3 Code threads on every fleet machine (read-only).

  fleet-threads.py [--days N] [--limit N] [QUERY]   threads whose title or messages contain QUERY
  fleet-threads.py --show THREAD_ID [--chars N]      messages of one thread, from whichever machine has it

Runs itself on each host over ssh (aliases mac / omarchy / dellbox) and opens
~/.t3/userdata/statev2.sqlite read-only.
"""
import argparse
import json
import shlex
import socket
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

HOSTS = {"mac": ("niils-m5-pro", "mac"), "omarchy": ("niils-omarchy",), "dellbox": ("dellburk",)}
DB = Path.home() / ".t3/userdata/statev2.sqlite"


def local(args):
    db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=10)
    env = (Path.home() / ".t3/userdata/environment-id").read_text().strip()
    out = []
    if args.show:
        rows = db.execute(
            "SELECT created_at, role, json_extract(payload_json, '$.text') FROM orchestration_v2_projection_messages "
            "WHERE thread_id = ? AND streaming = 0 ORDER BY created_at",
            (args.show,),
        ).fetchall()
        for at, role, text in rows:
            if text:
                out.append({"at": at, "role": role, "text": text[: args.chars]})
        return {"env": env, "rows": out}
    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()
    q = f"%{args.query or ''}%"
    rows = db.execute(
        """
        SELECT t.thread_id, t.updated_at, t.title, COALESCE(p.title, t.project_id),
               json_extract(t.payload_json, '$.lineage.relationshipToParent'),
               (SELECT json_extract(m.payload_json, '$.text') FROM orchestration_v2_projection_messages m
                 WHERE m.thread_id = t.thread_id AND m.streaming = 0
                   AND json_extract(m.payload_json, '$.text') LIKE :q
                 ORDER BY m.created_at LIMIT 1)
        FROM orchestration_v2_projection_threads t
        LEFT JOIN projection_projects p ON p.project_id = t.project_id
        WHERE t.deleted_at IS NULL AND t.updated_at >= :since
          AND (t.title LIKE :q OR EXISTS (
                SELECT 1 FROM orchestration_v2_projection_messages m
                 WHERE m.thread_id = t.thread_id AND json_extract(m.payload_json, '$.text') LIKE :q))
        ORDER BY t.updated_at DESC LIMIT :limit
        """,
        {"q": q, "since": since, "limit": args.limit},
    ).fetchall()
    for tid, at, title, project, rel, hit in rows:
        snippet = ""
        if hit and args.query:
            i = hit.lower().find(args.query.lower())
            snippet = " ".join(hit[max(0, i - 60): i + 100].split())
        out.append({"id": tid, "at": at, "title": title, "project": project, "child": bool(rel), "hit": snippet})
    return {"env": env, "rows": out}


def me():
    name = socket.gethostname().split(".")[0]
    return next((h for h, names in HOSTS.items() if name in names or name.lower() == "mac"), None)


def remote(host, argv):
    if host == me():
        return subprocess.run([sys.executable, __file__, "--local", *argv], capture_output=True, text=True)
    return subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5", host, "python3 - --local " + " ".join(map(shlex.quote, argv))],
        input=Path(__file__).read_text(), capture_output=True, text=True, timeout=120,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="?")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--limit", type=int, default=30)
    ap.add_argument("--show")
    ap.add_argument("--chars", type=int, default=2000)
    ap.add_argument("--local", action="store_true")
    args = ap.parse_args()
    if args.local:
        print(json.dumps(local(args)))
        return
    argv = [a for a in sys.argv[1:]]
    with ThreadPoolExecutor() as pool:
        results = dict(zip(HOSTS, pool.map(lambda h: remote(h, argv), HOSTS)))
    for host, r in results.items():
        if r.returncode:
            print(f"== {host}: unreachable or failed: {r.stderr.strip()[-300:]}")
            continue
        data = json.loads(r.stdout)
        rows = data["rows"]
        if args.show:
            if not rows:
                continue
            print(f"== {host} (environment {data['env']})")
            for m in rows:
                print(f"--- {m['at'][:16]} {m['role']}\n{m['text']}")
            continue
        print(f"== {host} (environment {data['env']}): {len(rows)} thread(s)")
        for t in rows:
            kind = " [child]" if t["child"] else ""
            print(f"{t['at'][:16]}  {t['title']}{kind}  ({t['project']})\n    id: {t['id']}")
            if t["hit"]:
                print(f"    …{t['hit']}…")


if __name__ == "__main__":
    main()
