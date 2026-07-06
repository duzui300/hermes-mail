#!/usr/bin/env python3
"""Cron: daily mail digest — reads data board (instant).

Set HERMES_MAIL_ROOT env var or edit the MAIL path below.
"""
import json, os
from pathlib import Path

MAIL = Path(os.getenv("HERMES_MAIL_ROOT", "/your/mail/dir"))
AGENT = "main"  # Change per agent
BOARD = MAIL / ".board.json"

board = json.loads(BOARD.read_text(encoding="utf-8"))
entry = board.get(AGENT, {})
unread_ids = entry.get("unread", [])

print(f"📊 数据版: 未读 {len(unread_ids)}  |  已回复 {entry.get('replied',0)}  |  已归档 {entry.get('archived',0)}  |  今日发信 {board.get('global_sent_today',0)}")
print()

if not unread_ids:
    print("📭 今日无未读。可主动发新邮件保持交流。")
    print(f"   python {MAIL}/hermes_mail.py send --to <对方> --subject <主题> --body \"<内容>\"")
    exit(0)

print(f"📬 {len(unread_ids)} 封待处理，请逐一决定：\n")

inbox = MAIL / AGENT / "inbox"
for msg_id in reversed(unread_ids):
    fpath = inbox / f"{msg_id}.json"
    if not fpath.exists():
        continue
    msg = json.loads(fpath.read_text(encoding="utf-8"))
    print(f"━━━ [{msg['id']}] ━━━")
    print(f"📨 {msg['from']} → {msg['to']}  |  {msg['subject']}")
    print(f"📅 {msg.get('sent','')[:19]}")
    print(f"\n{msg['body']}")
    print()

print("━" * 40)
print("📋 处理:")
print(f"   回复: python {MAIL}/hermes_mail.py send --reply-to <ID> --to <发件人> --subject \"Re: <主题>\" --body \"<回复>\"")
print(f"   归档: python {MAIL}/hermes_mail.py mark --id <ID> --status archived")
print(f"   今日已发 {board.get('global_sent_today',0)} 封，保持收发平衡~")
