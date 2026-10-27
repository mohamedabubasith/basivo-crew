#!/usr/bin/env python3
"""Per-agent token report for a Basivo Crew run.

Reads a Claude Code session transcript and reports what each agent actually ate,
attributed from the transcript itself rather than asked of the model — an agent
cannot see its own subagents' usage, so anything it told you would be invented.

  python3 crew-cost.py                        # newest transcript in ~/.claude/projects
  python3 crew-cost.py --session <id>         # one session by id
  python3 crew-cost.py path/to/x.jsonl        # an explicit transcript
  python3 crew-cost.py --format text          # plain text instead of markdown

Exits 0 with a note when there is nothing to report, so a CI step can call it
unconditionally without failing a run.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

AGENT_TOOLS = {"Task", "Agent"}
MAIN = "main session"


def find_transcripts(explicit: str | None, session: str | None) -> list[Path]:
    if explicit:
        p = Path(explicit)
        return [p] if p.is_file() else []
    root = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "projects"
    if not root.is_dir():
        return []
    files = sorted(root.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if session:
        return [f for f in files if f.stem == session]
    return files[:1]


def blocks(msg: dict) -> list:
    content = msg.get("content")
    return content if isinstance(content, list) else []


def collect(path: Path) -> tuple[dict, dict, int]:
    """Return (per-agent totals, agent-name-by-tool-id, unattributed message count)."""
    lines = []
    for raw in path.read_text(errors="replace").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            lines.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    by_uuid = {d["uuid"]: d for d in lines if isinstance(d.get("uuid"), str)}

    # Every Agent/Task tool call, by the tool_use id that identifies its run.
    agent_by_tool_id: dict[str, str] = {}
    for d in lines:
        for b in blocks(d.get("message") or {}):
            if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in AGENT_TOOLS:
                inp = b.get("input") or {}
                name = inp.get("subagent_type") or inp.get("agent") or b.get("name")
                if isinstance(b.get("id"), str):
                    agent_by_tool_id[b["id"]] = str(name)

    def owner(d: dict) -> str | None:
        """Which agent's run this message belongs to."""
        # Documented link first: subagent messages name the tool call that started them.
        tid = d.get("parent_tool_use_id") or (d.get("message") or {}).get("parent_tool_use_id")
        if isinstance(tid, str) and tid in agent_by_tool_id:
            return agent_by_tool_id[tid]
        if not d.get("isSidechain"):
            return MAIN
        # Sidechain without that field: walk the parent chain for one that has it.
        seen, cur = set(), d
        while cur is not None:
            pid = cur.get("parentUuid")
            if not isinstance(pid, str) or pid in seen:
                break
            seen.add(pid)
            cur = by_uuid.get(pid)
            if cur is None:
                break
            tid = cur.get("parent_tool_use_id")
            if isinstance(tid, str) and tid in agent_by_tool_id:
                return agent_by_tool_id[tid]
        return None

    totals: dict[str, dict[str, int]] = {}
    unattributed = 0
    for d in lines:
        usage = (d.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        who = owner(d)
        if who is None:
            unattributed += 1
            who = "unattributed"
        t = totals.setdefault(who, {"msgs": 0, "in": 0, "out": 0, "cache_read": 0, "cache_write": 0})
        t["msgs"] += 1
        t["in"] += int(usage.get("input_tokens") or 0)
        t["out"] += int(usage.get("output_tokens") or 0)
        t["cache_read"] += int(usage.get("cache_read_input_tokens") or 0)
        t["cache_write"] += int(usage.get("cache_creation_input_tokens") or 0)

    # A run that was started but produced nothing should still appear, as a zero row.
    for name in agent_by_tool_id.values():
        totals.setdefault(name, {"msgs": 0, "in": 0, "out": 0, "cache_read": 0, "cache_write": 0})

    return totals, agent_by_tool_id, unattributed


def thousands(n: int) -> str:
    return f"{n:,}"


def render(totals: dict, calls: dict, unattributed: int, fmt: str, source: Path) -> str:
    if not totals:
        return "_No token usage found in the transcript._\n"

    counts: dict[str, int] = {}
    for name in calls.values():
        counts[name] = counts.get(name, 0) + 1

    # Main session first, then the agents by spend, then unattributed.
    def sort_key(item):
        name, t = item
        billed = t["in"] + t["out"] + t["cache_write"]
        return (name != MAIN, name == "unattributed", -billed)

    rows = sorted(totals.items(), key=sort_key)
    grand = {k: sum(t[k] for t in totals.values()) for k in ("msgs", "in", "out", "cache_read", "cache_write")}

    def runs_of(name: str) -> str:
        # A run count only means something for an agent that was spawned.
        return "—" if name in (MAIN, "unattributed") else str(counts.get(name, 0))

    if fmt == "text":
        cols = ["agent", "runs", "msgs", "input", "output", "cache r", "cache w"]
        body = [[name, runs_of(name), str(t["msgs"]), thousands(t["in"]), thousands(t["out"]),
                 thousands(t["cache_read"]), thousands(t["cache_write"])] for name, t in rows]
        body.append(["total", "", str(grand["msgs"]), thousands(grand["in"]), thousands(grand["out"]),
                     thousands(grand["cache_read"]), thousands(grand["cache_write"])])
        # Size every column to its widest cell, so a big number can never run into its neighbour.
        width = [max(len(cols[i]), max(len(r[i]) for r in body)) + 2 for i in range(len(cols))]
        width[0] -= 2
        head = cols[0].ljust(width[0]) + "".join(c.rjust(width[i]) for i, c in enumerate(cols) if i)
        out = [f"Per-agent tokens  ({source.name})", "", head, "-" * len(head)]
        for r in body[:-1]:
            out.append(r[0].ljust(width[0]) + "".join(c.rjust(width[i]) for i, c in enumerate(r) if i))
        r = body[-1]
        out += ["-" * len(head),
                r[0].ljust(width[0]) + "".join(c.rjust(width[i]) for i, c in enumerate(r) if i)]
    else:
        out = ["### Token use by agent", "",
               "| Agent | Runs | Messages | Input | Output | Cache read | Cache write |",
               "| :- | -: | -: | -: | -: | -: | -: |"]
        for name, t in rows:
            label = f"`{name}`" if name not in (MAIN, "unattributed") else name
            out.append(
                f"| {label} | {runs_of(name)} | {t['msgs']} | {thousands(t['in'])} | {thousands(t['out'])} "
                f"| {thousands(t['cache_read'])} | {thousands(t['cache_write'])} |"
            )
        out.append(
            f"| **Total** | | **{grand['msgs']}** | **{thousands(grand['in'])}** | "
            f"**{thousands(grand['out'])}** | **{thousands(grand['cache_read'])}** | "
            f"**{thousands(grand['cache_write'])}** |"
        )
        out += ["",
                "Cache reads are charged at a fraction of input, and cache writes at a "
                "premium — so the columns are kept apart rather than summed into one "
                "misleading number. For the run's actual dollar figure see the Claude Code "
                "report in this job's summary; prices change, so this script does not "
                "carry a price table that would quietly go stale."]
        if unattributed:
            out.append(f"\n{unattributed} message(s) could not be attributed to an agent and are "
                       "listed separately rather than spread across the others.")

    return "\n".join(out) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-agent token report for a Claude Code session.")
    ap.add_argument("transcript", nargs="?", help="path to a .jsonl transcript")
    ap.add_argument("--session", help="session id to report on")
    ap.add_argument("--format", choices=["md", "text"], default="md")
    args = ap.parse_args()

    paths = find_transcripts(args.transcript, args.session)
    if not paths:
        print("_No session transcript found, so no per-agent token report._")
        return 0

    path = paths[0]
    totals, calls, unattributed = collect(path)
    sys.stdout.write(render(totals, calls, unattributed, args.format, path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
