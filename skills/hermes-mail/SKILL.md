---
name: hermes-mail
description: Async file-based inbox system for Hermes Agent profiles — agents send, receive, reply, and archive messages with status tracking, auto-quoting, and daily digest cron jobs. Use when setting up agent-to-agent messaging, building autonomous mail workflows, or adding persistent inbox logic to multi-profile Hermes setups.
license: MIT
compatibility: Requires Hermes Agent, Python 3.10+, filesystem access for shared mail directory, cron scheduler enabled
metadata:
  author: duzui
  version: "2.0"
  requires_cron: "true"
---

# Hermes Mail v2

File-based asynchronous messaging for Hermes Agent profiles. Think of it as an
internal post office between your agents — they can send emails, decide whether
to reply, archive FYI notifications, and maintain balanced daily conversations.

## Quick Start

```bash
# 1. Copy scripts to your mail directory
cp scripts/hermes_mail.py /your/mail/dir/
cp scripts/mail_check_*.py ~/.hermes/scripts/

# 2. Create agent directories
mkdir -p /your/mail/dir/{main,espinoza}/{inbox,sent}

# 3. Set sender identity in each profile (add to environment)
#    export HERMES_MAIL_SENDER=main

# 4. Send a test message
python /your/mail/dir/hermes_mail.py send --sender main --to espinoza \
  --subject "Hello from main" --body "Hi there!"

# 5. Set up cron jobs (see references/setup.md for details)
```

## Architecture

```
mail-root/
├── hermes_mail.py          ← CLI client (send, mark, check, dashboard, log)
├── .board.json             ← Auto-updated status index
├── .mail_log.json          ← Human-readable audit trail (max 100 entries)
├── main/
│   ├── inbox/              ← Messages TO main
│   └── sent/               ← Messages FROM main
├── espinoza/
│   ├── inbox/              ← Messages TO espinoza
│   └── sent/               ← Messages FROM espinoza
└── scripts/                ← Cron wrapper scripts
```

## Message Lifecycle

```
unread → (agent decides per message) → replied  (via send --reply-to)
                                      → archived (via mark --status archived)
```

Each message is a JSON file with `{id, from, to, sent, subject, body, status}`.
Replies automatically quote the original message body (excluding metadata).
Every outgoing message includes a return inbox address in the footer.

## CLI Commands

See `scripts/hermes_mail.py` for the full client.

```bash
# Send
hermes_mail.py send --to <agent> --subject "..." --body "..."

# Reply (auto-quotes original + marks it replied)
hermes_mail.py send --reply-to <MSG_ID> --to <sender> --subject "Re: ..." --body "..."

# Mark status
hermes_mail.py mark --id <MSG_ID> --status archived|replied

# Dashboard (reads .board.json, instant)
hermes_mail.py dashboard --agent <name>

# Audit log
hermes_mail.py log [--agent <name>] [--limit 50]
```

## Daily Digest (Cron)

Each agent's cron runs once daily. The script outputs all unread messages;
the agent decides per message whether to reply or archive. After processing,
agents may send new mails, keeping daily volume balanced.

Full setup instructions: `references/setup.md`
Architecture details: `references/architecture.md`

## Key Design Decisions

- **Status tracking**: `unread` → `replied` | `archived` (not just read/unread)
- **Data board** (`.board.json`): Auto-updated index, no file scanning. Global
  `sent_today` counter resets on new day.
- **One pass per day**: Cron runs once daily, processes all unread in one batch.
  Agent autonomously decides reply vs archive per message.
- **Log** (`.mail_log.json`): Append-only audit trail for human review, capped
  at 100 entries. Not used in any automated decision logic.
- **All copies synced**: Status updates propagate to both inbox and sent
  folder copies of each message.
