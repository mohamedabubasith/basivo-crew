---
name: crew-cost
description: Report how many tokens each agent actually used in a session — per agent, from the transcript. Use when asked what a run cost, which agent is expensive, or where the tokens went.
argument-hint: "[session-id or transcript path]"
---

# /crew-cost

Report what each agent ate.

Run the script; do not estimate. An agent cannot see its own subagents' usage, so any
number you produce from memory or from reading the conversation is invented. The
transcript is the only ground truth available.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/crew-cost.py" $1 --format text
```

With no argument it reports the newest session. `--session <id>` picks one by id, or pass
a transcript path directly. Show the table as it comes back.

## Reading it

- **Input** and **output** are what the run was billed for at full rate.
- **Cache read** is charged at a fraction of input, **cache write** at a premium. They
  are separate columns on purpose: adding them into one "total tokens" number reads as
  ten times the real cost and is the most common way these reports mislead.
- **Runs** is how many times that agent was spawned. An agent with runs but zero messages
  was started and produced nothing — usually a failure worth looking into.
- **unattributed** means a message's usage could not be tied to an agent. A few are
  normal; a large share means the transcript is partial, so say so rather than presenting
  the split as exact.

## If someone wants the money figure

Say that this reports tokens, not dollars, and why: prices change, and a hardcoded price
table in a plugin goes stale silently and quotes someone a wrong number. For the actual
spend, point them at `total_cost_usd` in the Claude Code report — in CI it is in the job
summary when `display_report: true` is set, which the crew's workflows do.
