#!/usr/bin/env python3
"""通过 SSH 在白名单服务器上执行只读 SQL，返回 JSON。

本机出口 IP 不在 tech-api 网关白名单里，所以 SQL 交给 8.152.222.232 代发。
只用 ssh 管道传脚本，不用 scp。

用法:
  python nba_sql.py "SELECT ..."                 # 打印 JSON
  python nba_sql.py "SELECT ..." --db nba_data_biz
  python nba_sql.py -f query.sql -o out.json

代码里:
  from nba_sql import query
  rows = query("SELECT ...")
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

SSH_HOST = "root@8.152.222.232"
ENDPOINT = "https://tech-api.nbadata.cn/dev/sql"

_REMOTE = r'''
import json, sys, urllib.request, urllib.parse
req = json.loads(sys.stdin.readline())
p = {"sql": req["sql"]}
if req.get("db"):
    p["db"] = req["db"]
try:
    with urllib.request.urlopen(req["endpoint"] + "?" + urllib.parse.urlencode(p), timeout=req["timeout"]) as r:
        sys.stdout.write(r.read().decode())
except Exception as e:
    sys.stdout.write(json.dumps({"code": -2, "msg": repr(e)}))
'''


class NbaSqlError(RuntimeError):
    pass


def query(sql: str, *, db: str | None = None, timeout: int = 90) -> list[dict]:
    payload = json.dumps({"sql": sql, "db": db, "endpoint": ENDPOINT, "timeout": timeout})
    script = _REMOTE.replace("'", "'\"'\"'")
    proc = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", SSH_HOST, f"python3 -c '{script}'"],
        input=payload + "\n",
        capture_output=True,
        text=True,
        timeout=timeout + 30,
    )
    if proc.returncode != 0:
        raise NbaSqlError(f"ssh failed ({proc.returncode}): {proc.stderr.strip()[:500]}")
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise NbaSqlError(f"non-JSON response: {proc.stdout[:500]}") from e
    if obj.get("code") != 0:
        raise NbaSqlError(f"SQL error: {obj.get('msg')}")
    rows = obj.get("data") or []
    return [{str(k).lower(): v for k, v in r.items()} for r in rows]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sql", nargs="?")
    ap.add_argument("-f", "--file")
    ap.add_argument("--db")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    sql = open(a.file, encoding="utf-8").read() if a.file else a.sql
    if not sql:
        ap.error("need SQL or -f")
    rows = query(sql, db=a.db)
    text = json.dumps(rows, ensure_ascii=False, indent=1, default=str)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(text)
        print(f"{len(rows)} rows -> {a.out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
