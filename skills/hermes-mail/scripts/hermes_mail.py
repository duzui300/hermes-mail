#!/usr/bin/env python3
"""Hermes Mail v2 — File-based async mailbox with status tracking, reply quoting, and board.

Set HERMES_MAIL_ROOT env var to your mail directory, or edit MAIL_ROOT below.
"""

import json, os, sys
from datetime import datetime, timezone
from pathlib import Path

MAIL_ROOT = Path(os.getenv("HERMES_MAIL_ROOT", "/your/mail/dir"))
AGENTS = ["main", "espinoza"]


def _msg_path(agent: str, folder: str = "inbox") -> Path:
    return MAIL_ROOT / agent / folder


def _gen_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")


def _quote_body(text: str) -> str:
    return "\n".join("> " + line for line in text.splitlines())


def _add_inbox_footer(body: str, sender: str) -> str:
    return body + f"\n\n---\n📬 回复请发至: {sender}/inbox/"


def _read_msg_file(fpath: Path) -> dict | None:
    try:
        return json.loads(fpath.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_msg_file(fpath: Path, msg: dict):
    fpath.write_text(json.dumps(msg, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Board ──
BOARD_PATH = MAIL_ROOT / ".board.json"
LOG_PATH = MAIL_ROOT / ".mail_log.json"


def _load_board() -> dict:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    board = {}
    if BOARD_PATH.exists():
        try:
            board = json.loads(BOARD_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    if board.get("today_date") != today:
        board["today_date"] = today
        board["global_sent_today"] = 0
    for agent in AGENTS:
        if agent not in board:
            board[agent] = {"unread": [], "replied": 0, "archived": 0}
        for key in ("unread", "replied", "archived"):
            if key not in board[agent]:
                board[agent][key] = [] if key == "unread" else 0
    return board


def _save_board(board: dict):
    BOARD_PATH.write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding="utf-8")


def _board_send(recipient: str, msg_id: str):
    board = _load_board()
    if recipient in board:
        board[recipient]["unread"].append(msg_id)
    board["global_sent_today"] = board.get("global_sent_today", 0) + 1
    _save_board(board)


def _board_status_change(agent: str, msg_id: str, old_status: str, new_status: str):
    board = _load_board()
    entry = board.get(agent, {})
    if msg_id in entry.get("unread", []):
        entry["unread"].remove(msg_id)
    if new_status in ("replied", "archived"):
        entry[new_status] = entry.get(new_status, 0) + 1
    _save_board(board)


def _update_log(msg: dict, action: str):
    entries = []
    if LOG_PATH.exists():
        try:
            entries = json.loads(LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            entries = []
    entries.append({
        "id": msg["id"], "from": msg["from"], "to": msg["to"],
        "subject": msg["subject"], "sent": msg.get("sent", ""),
        "status": msg.get("status", "unread"), "action": action,
        "action_time": datetime.now(timezone.utc).isoformat(),
    })
    if len(entries) > 100:
        entries = entries[-100:]
    LOG_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Core operations ──

def send(to: str, subject: str, body: str = "", sender: str = None,
         reply_to_id: str = None) -> str:
    sender = sender or os.getenv("HERMES_MAIL_SENDER", "unknown")
    if reply_to_id:
        orig = find_msg(reply_to_id)
        if orig:
            body = body + "\n\n--- 原文 ---\n" + _quote_body(orig["body"])
            mark_status(orig, "replied")
    body = _add_inbox_footer(body, sender)
    msg_id = _gen_id()
    msg = {
        "id": msg_id, "from": sender, "to": to,
        "sent": datetime.now(timezone.utc).isoformat(),
        "subject": subject, "body": body, "status": "unread",
    }
    targets = AGENTS if to == "broadcast" else [to]
    for target in targets:
        if target != "broadcast":
            inbox = _msg_path(target, "inbox")
            inbox.mkdir(parents=True, exist_ok=True)
            _write_msg_file(inbox / f"{msg_id}.json", msg)
    if sender != "unknown":
        sent = _msg_path(sender, "sent")
        sent.mkdir(parents=True, exist_ok=True)
        _write_msg_file(sent / f"{msg_id}.json", msg)
    _board_send(to, msg_id)
    _update_log(msg, "sent")
    return msg_id


def find_msg(msg_id: str) -> dict | None:
    for agent in AGENTS:
        for folder in ("inbox", "sent"):
            fpath = _msg_path(agent, folder) / f"{msg_id}.json"
            if fpath.exists():
                return _read_msg_file(fpath)
    return None


def mark(msg_id: str, new_status: str) -> bool:
    msg = find_msg(msg_id)
    if not msg:
        return False
    return mark_status(msg, new_status)


def mark_status(msg: dict, new_status: str) -> bool:
    old_status = msg.get("status", "unread")
    msg["status"] = new_status
    updated = False
    for agent in AGENTS:
        for folder in ("inbox", "sent"):
            fpath = _msg_path(agent, folder) / f"{msg['id']}.json"
            if fpath.exists():
                _write_msg_file(fpath, msg)
                updated = True
    if updated and old_status != new_status:
        _board_status_change(msg["to"], msg["id"], old_status, new_status)
    _update_log(msg, new_status)
    return updated


def get_unread(agent: str) -> list:
    board = _load_board()
    ids = board.get(agent, {}).get("unread", [])
    msgs = []
    inbox = _msg_path(agent, "inbox")
    for msg_id in reversed(ids):
        fpath = inbox / f"{msg_id}.json"
        msg = _read_msg_file(fpath)
        if msg:
            msgs.append(msg)
    return msgs


def dashboard(agent: str) -> str:
    board = _load_board()
    entry = board.get(agent, {})
    return (
        f"📊 {agent} 收件箱状况 (数据版)\n"
        f"   未读: {len(entry.get('unread', []))}  |  "
        f"已回复: {entry.get('replied', 0)}  |  "
        f"已归档: {entry.get('archived', 0)}\n"
        f"   今日全局发信: {board.get('global_sent_today', 0)} 封\n"
    )


# ── CLI ──
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hermes Mail v2")
    sub = parser.add_subparsers(dest="cmd")

    s = sub.add_parser("send")
    s.add_argument("--to", required=True)
    s.add_argument("--subject", required=True)
    s.add_argument("--body", default="")
    s.add_argument("--sender", default=None)
    s.add_argument("--reply-to", default=None, dest="reply_to_id")

    m = sub.add_parser("mark")
    m.add_argument("--id", required=True, dest="msg_id")
    m.add_argument("--status", required=True, choices=["replied", "archived", "unread"])

    d = sub.add_parser("dashboard")
    d.add_argument("--agent", required=True)

    c = sub.add_parser("check")
    c.add_argument("--agent", required=True)

    r = sub.add_parser("read")
    r.add_argument("--agent", required=True)
    r.add_argument("--id", required=True, dest="msg_id")

    ls = sub.add_parser("list")
    ls.add_argument("--agent", required=True)

    log = sub.add_parser("log")
    log.add_argument("--limit", type=int, default=20)
    log.add_argument("--agent", default=None)

    args = parser.parse_args()

    if args.cmd == "send":
        msg_id = send(to=args.to, subject=args.subject, body=args.body,
                      sender=args.sender, reply_to_id=args.reply_to_id)
        print(f"📨 已发送 → {args.to}\n   ID: {msg_id}")

    elif args.cmd == "mark":
        ok = mark(args.msg_id, args.status)
        icon = {"replied": "✅", "archived": "📦", "unread": "📬"}.get(args.status, "")
        print(f"{icon} {args.msg_id} → {args.status}" if ok else f"❌ Not found: {args.msg_id}")

    elif args.cmd == "dashboard":
        print(dashboard(args.agent))

    elif args.cmd == "check":
        unread = get_unread(args.agent)
        if not unread:
            print(f"📭 {args.agent} 的收件箱没有未读邮件~")
        else:
            print(f"📬 {args.agent} 有 {len(unread)} 封待处理：\n")
            for msg in unread:
                print(f"━━━ {msg['id']} ━━━")
                print(f"📨 {msg['from']}  |  {msg['subject']}")
                print(f"📅 {msg['sent'][:19]}")
                print(f"\n{msg['body']}\n")

    elif args.cmd == "read":
        msg = find_msg(args.msg_id)
        if msg:
            print(f"📨 {msg['from']} → {msg['to']}  |  {msg['subject']}")
            print(f"📅 {msg['sent'][:19]}  |  [{msg.get('status', '?')}]")
            print(f"\n{msg['body']}")
        else:
            print(f"❌ Not found: {args.msg_id}")

    elif args.cmd == "list":
        inbox = _msg_path(args.agent, "inbox")
        files = sorted(inbox.glob("*.json"), reverse=True)
        print(f"📬 {args.agent} 收件箱 ({len(files)} 封)：\n")
        for f in files:
            msg = _read_msg_file(f)
            if msg:
                s = msg.get("status", "unread")
                icon = {"unread": "✉", "replied": "✅", "archived": "📦"}.get(s, "?")
                print(f"  {icon} [{msg['id']}] {msg['from']}: {msg['subject']}")

    elif args.cmd == "log":
        if not LOG_PATH.exists():
            print("📭 尚无邮件记录。")
        else:
            entries = json.loads(LOG_PATH.read_text(encoding="utf-8"))
            if args.agent:
                entries = [e for e in entries if e.get("from") == args.agent or e.get("to") == args.agent]
            entries = entries[-args.limit:]
            print(f"📋 邮件日志 (最近 {len(entries)} 条):\n")
            for e in reversed(entries):
                icon = {"sent": "📨", "replied": "✅", "archived": "📦", "unread": "✉"}.get(e["action"], "·")
                print(f"  {icon} [{e['id'][:17]}] {e['from']} → {e['to']} | {e['action']:>8} | {e['subject']}")
