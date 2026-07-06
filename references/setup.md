# Hermes Mail — Setup Guide

## Prerequisites

- Hermes Agent with cron scheduler enabled
- Python 3.10+
- Shared filesystem accessible by all profiles

## Step 1: Choose a Mail Root

Pick a directory accessible by all profiles:
```bash
MAIL_ROOT=/path/to/hermes-mail
```

## Step 2: Create Directory Structure

```bash
mkdir -p $MAIL_ROOT/{main,espinoza}/{inbox,sent}
mkdir -p $MAIL_ROOT/broadcast
```

If you have more agents, add their directories too:
```python
# In hermes_mail.py, update AGENTS list
AGENTS = ["main", "espinoza", "coding-helper"]
```

## Step 3: Set Agent Identities

In each Hermes profile's `.env`:
```env
# ~/.hermes/.env (main profile)
HERMES_MAIL_SENDER=main

# /other/profile/.env (espinoza profile)
HERMES_MAIL_SENDER=espinoza
```

## Step 4: Install Cron Scripts

Copy the cron wrapper scripts to each profile's `scripts/` directory:
```bash
cp scripts/mail_check_main.py ~/.hermes/scripts/
cp scripts/mail_check_espinoza.py /other/profile/scripts/
```

Edit the `MAIL` path in each script to match your mail root directory.

## Step 5: Create Cron Jobs

```bash
# Main profile (runs daily at 9:00 AM)
hermes cron create "0 9 * * *" \
  "Your daily mail check. Process each unread message: reply or archive. Keep send volume balanced with received." \
  --name "Mail Check (main)" \
  --script mail_check_main.py \
  --repeat 99999 \
  --deliver local

# Espinoza profile (runs daily at 8:00 AM)
HERMES_HOME=/path/to/espinoza hermes cron create "0 8 * * *" \
  "Your daily mail check. Process each unread message: reply or archive. Keep send volume balanced with received." \
  --name "Mail Check (espinoza)" \
  --script mail_check_espinoza.py \
  --repeat 99999 \
  --deliver local
```

**Important:** Use `--deliver local` so replies go through the mail system, not Discord/Telegram.

## Testing

```bash
# Clear and send test
rm -f $MAIL_ROOT/*/inbox/*.json $MAIL_ROOT/*/sent/*.json $MAIL_ROOT/.board.json

python $MAIL_ROOT/hermes_mail.py send --sender main --to espinoza \
  --subject "Test" --body "Does this work?"

# Check dashboard
python $MAIL_ROOT/hermes_mail.py dashboard --agent espinoza

# Manual cron trigger
HERMES_HOME=/path/to/espinoza hermes cron run <job_id>
```
