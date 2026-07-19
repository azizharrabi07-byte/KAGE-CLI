# Troubleshooting

## Discord/Telegram agent won't start
Set the token in the environment (or a git-ignored `.env`): `DISCORD_BOT_TOKEN`,
`TELEGRAM_BOT_TOKEN`. Verify with `kage cli` → `/secrets list`.

## Shell command rejected
The sandbox allow-lists read-only commands and forbids absolute paths,
subshells, and network tools. Allowed: ls, cat, pwd, echo, wc, grep, head,
tail, date, whoami, uname, stat, file, find, sort, uniq, env.

## Workflow stuck
State persists in `.kage/kage.db`. Use `/workflows` to inspect the visited path;
a failed step stops the run (per-step retry re-runs only that step).

## Retry / backoff
`run_with_retry` uses exponential backoff capped at 8s. Simulate a flaky step by
raising inside `fn(attempt)` for the first N attempts (see the tests).

## Logs
Structured JSON lines land in `~/.kage/logs/kage.log`; secrets are scrubbed.
