# Hermes Mail — Architecture Reference

## Data Flow

```
send/mark operation
    │
    ├─→ Write JSON to inbox/sent/
    ├─→ Update .board.json (status index)
    └─→ Append .mail_log.json (audit trail)

Cron tick
    │
    ├─→ mail_check_*.py reads .board.json
    ├─→ Outputs unread messages to stdout
    ├─→ Agent LLM processes (reply or archive)
    └─→ Each reply/mark triggers the flow above
```

## Files

| File | Purpose | Auto-updated? |
|------|---------|---------------|
| `{agent}/inbox/*.json` | Individual messages | Yes, on send |
| `{agent}/sent/*.json` | Outgoing copy | Yes, on send |
| `.board.json` | Status index (fast lookup) | Yes, every send/mark |
| `.mail_log.json` | Human audit trail | Yes, every send/mark |
| `scripts/mail_check_*.py` | Cron wrapper scripts | No, static |

## Board Schema

```json
{
  "today_date": "20260706",
  "global_sent_today": 5,
  "main": {
    "unread": ["msg_id_1", "msg_id_2"],
    "replied": 10,
    "archived": 3
  },
  "espinoza": {
    "unread": [],
    "replied": 5,
    "archived": 2
  }
}
```

- `today_date` resets `global_sent_today` on new day
- `unread`: list of message IDs (appended on send, removed on mark)
- `replied` / `archived`: lifetime counters

## Message JSON Schema

```json
{
  "id": "20260706_133045_123456",
  "from": "main",
  "to": "espinoza",
  "sent": "2026-07-06T13:30:45Z",
  "subject": "Hello",
  "body": "Message body...\n\n---\n📬 Reply to: <inbox-path>/",
  "status": "unread"
}
```

Status values: `unread` | `replied` | `archived`

## Key Invariants

1. Every `send()` writes TWO copies: recipient inbox + sender sent folder
2. `mark_status()` updates ALL copies (inbox + sent) before updating the board
3. `.board.json` is the single source of truth for status queries
4. Cron scripts only read `.board.json` — they never scan files
5. `.mail_log.json` is append-only, capped at 100 entries, never read by agents
