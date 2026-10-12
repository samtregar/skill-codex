#!/usr/bin/env python3
"""Print Codex's final message (e.g. a review) from a saved session.

Codex saves every session as a JSONL rollout under $CODEX_HOME/sessions
(default ~/.codex/sessions). Sessions are ordered by last activity, so a
resumed session counts as recent.

  codex_review.py               final message of the most recent session
  codex_review.py -n 2          ...of the second most recent session
  codex_review.py --all         every turn's final message, not just the last
                                (a resumed session has one turn per resume)
  codex_review.py --cwd DIR     only consider sessions that ran in DIR
  codex_review.py --list [N]    list the N most recent sessions (default 10)
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def parse(path):
    """Return the session's cwd, first prompt, and one (prompt, answer) per turn."""
    info = {"path": path, "cwd": None, "prompt": None, "turns": [], "complete": False}
    prompt = answer = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            payload = rec.get("payload") or {}
            if rec.get("type") == "session_meta":
                info["cwd"] = payload.get("cwd")
            if rec.get("type") != "event_msg":
                continue
            kind = payload.get("type")
            user = agent = None
            if kind == "item_completed":
                item = payload.get("item") or {}
                text = "".join(c.get("text", "") for c in item.get("content") or [])
                if item.get("type") == "UserMessage":
                    user = text
                elif item.get("type") == "AgentMessage":
                    agent = text
            # Codex <= 0.146 logged messages as plain events instead of items.
            elif kind == "user_message":
                user = payload.get("message")
            elif kind == "agent_message":
                agent = payload.get("message")

            if user:
                info["prompt"] = info["prompt"] or user
                prompt = prompt or user
            elif agent:
                answer = agent
            elif kind == "task_started":
                info["complete"] = False
            elif kind == "task_complete":
                info["complete"] = True
                info["turns"].append((prompt, payload.get("last_agent_message") or answer))
                prompt = answer = None
    # A session killed mid-turn has no task_complete; keep the last thing
    # Codex said so there is still something to show.
    if not info["complete"] and answer:
        info["turns"].append((prompt, answer))
    return info


def sessions(cwd):
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
    paths = sorted(root.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    for path in paths:
        info = parse(path)
        if cwd is None or (info["cwd"] and os.path.realpath(info["cwd"]) == cwd):
            yield info


def first_line(text, width=80):
    lines = (text or "").strip().splitlines()
    return lines[0][:width] if lines else ""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=int, default=1, help="which session, 1 = most recent")
    ap.add_argument("--all", action="store_true", help="print every turn, not just the last")
    ap.add_argument("--cwd", help="only sessions whose working directory is DIR")
    ap.add_argument("--list", nargs="?", type=int, const=10, metavar="N", help="list recent sessions")
    args = ap.parse_args()
    cwd = os.path.realpath(args.cwd) if args.cwd else None

    if args.list:
        for i, info in enumerate(sessions(cwd), 1):
            if i > args.list:
                break
            when = datetime.fromtimestamp(info["path"].stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            turns = len(info["turns"])
            flags = (f" [{turns} turns]" if turns > 1 else "") + ("" if info["complete"] else " [incomplete]")
            print(f"{i:>3}  {when}  {info['cwd']}{flags}\n     {first_line(info['prompt'])}")
        return 0

    for i, info in enumerate(sessions(cwd), 1):
        if i == args.n:
            break
    else:
        sys.exit("No matching Codex session found.")

    if not info["turns"]:
        sys.exit(f"Session has no message from Codex: {info['path']}")
    if not info["complete"]:
        print("(Session did not finish; the last answer is Codex's last message.)\n", file=sys.stderr)
    turns = info["turns"] if args.all else info["turns"][-1:]
    for i, (prompt, answer) in enumerate(turns, 1):
        if args.all:
            print(f"{'' if i == 1 else chr(10)}===== Turn {i}/{len(turns)}: {first_line(prompt)}\n")
        print(answer)
    return 0


if __name__ == "__main__":
    sys.exit(main())
