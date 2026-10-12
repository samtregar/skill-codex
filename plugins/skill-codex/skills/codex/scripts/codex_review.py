#!/usr/bin/env python3
"""Print Codex's final message (e.g. a review) from a saved session.

Codex saves every session as a JSONL rollout under $CODEX_HOME/sessions
(default ~/.codex/sessions). Sessions are ordered by last activity, so a
resumed session counts as recent. Internal sessions Codex spawns for itself
(e.g. the auto-approval "guardian") are skipped unless --internal is given.

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


def as_dict(value):
    return value if isinstance(value, dict) else {}


def as_str(value):
    return value if isinstance(value, str) else None


def item_text(item):
    if isinstance(item.get("text"), str):
        return item["text"]
    content = item.get("content")
    if not isinstance(content, list):
        return ""
    return "".join(c["text"] for c in content if isinstance(c, dict) and isinstance(c.get("text"), str))


def parse(path):
    """Return the session's metadata and one turn dict per user turn.

    Each turn has the user's prompt, Codex's answer, and a status of
    "complete", "interrupted" (turn_aborted), or "incomplete" (no end event,
    e.g. the process was killed).
    """
    info = {"path": path, "cwd": None, "prompt": None, "internal": False, "turns": []}
    turn = None

    def close(status, final=None):
        nonlocal turn
        if turn is not None:
            # Plan mode leaves last_agent_message empty and puts the answer
            # in a Plan item; otherwise fall back to Codex's last message.
            answer = final or turn["plan"] or turn["message"]
            info["turns"].append({"prompt": turn["prompt"], "answer": answer, "status": status})
        turn = None

    def ensure_turn():
        nonlocal turn
        if turn is None:
            turn = {"prompt": None, "message": None, "plan": None, "started": False}
        return turn

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            rec = as_dict(rec)
            payload = as_dict(rec.get("payload"))
            if rec.get("type") == "session_meta":
                info["cwd"] = as_str(payload.get("cwd"))
                info["internal"] = "subagent" in as_dict(payload.get("source"))
            if rec.get("type") != "event_msg":
                continue
            kind = payload.get("type")
            user = agent = plan = None
            if kind == "item_completed":
                item = as_dict(payload.get("item"))
                user, agent, plan = (
                    item_text(item) if item.get("type") == t else None
                    for t in ("UserMessage", "AgentMessage", "Plan")
                )
            # Codex <= 0.146 logged messages as plain events instead of items.
            elif kind == "user_message":
                user = as_str(payload.get("message"))
            elif kind == "agent_message":
                agent = as_str(payload.get("message"))

            if kind == "task_started":
                # An open turn that already started never got an end event.
                # One that has not started holds this turn's prompt, logged early.
                if turn and (turn["started"] or turn["message"] or turn["plan"]):
                    close("incomplete")
                ensure_turn()["started"] = True
            elif kind == "task_complete":
                ensure_turn()
                close("complete", as_str(payload.get("last_agent_message")))
            elif kind == "turn_aborted":
                close("interrupted")
            elif user:
                t = ensure_turn()
                t["prompt"] = t["prompt"] or user
            elif agent:
                ensure_turn()["message"] = agent
            elif plan:
                ensure_turn()["plan"] = plan
    close("incomplete")

    info["prompt"] = next((t["prompt"] for t in info["turns"] if t["prompt"]), None)
    return info


def sessions(cwd, internal):
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")) / "sessions"
    dated = []
    for path in root.rglob("rollout-*.jsonl"):
        try:
            dated.append((path.stat().st_mtime, path))
        except OSError:
            continue
    for mtime, path in sorted(dated, reverse=True):
        try:
            info = parse(path)
        except OSError as e:
            print(f"Skipping unreadable session {path}: {e}", file=sys.stderr)
            continue
        if info["internal"] and not internal:
            continue
        if cwd is None or (info["cwd"] and os.path.realpath(info["cwd"]) == cwd):
            info["mtime"] = mtime
            yield info


def first_line(text, width=80):
    lines = (text or "").strip().splitlines()
    return lines[0][:width] if lines else ""


def positive(value):
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", type=positive, default=1, help="which session, 1 = most recent")
    ap.add_argument("--all", action="store_true", help="print every turn, not just the last")
    ap.add_argument("--cwd", help="only sessions whose working directory is DIR")
    ap.add_argument("--list", nargs="?", type=positive, const=10, metavar="N", help="list recent sessions")
    ap.add_argument("--internal", action="store_true", help="include Codex's internal sessions (e.g. guardian)")
    args = ap.parse_args()
    cwd = os.path.realpath(args.cwd) if args.cwd else None

    if args.list is not None:
        for i, info in enumerate(sessions(cwd, args.internal), 1):
            if i > args.list:
                break
            when = datetime.fromtimestamp(info["mtime"]).strftime("%Y-%m-%d %H:%M")
            turns = info["turns"]
            flags = f" [{len(turns)} turns]" if len(turns) > 1 else ""
            if turns and turns[-1]["status"] != "complete":
                flags += f" [{turns[-1]['status']}]"
            if info["internal"]:
                flags += " [internal]"
            print(f"{i:>3}  {when}  {info['cwd']}{flags}\n     {first_line(info['prompt'])}")
        return 0

    for i, info in enumerate(sessions(cwd, args.internal), 1):
        if i == args.n:
            break
    else:
        sys.exit("No matching Codex session found.")

    if not info["turns"]:
        sys.exit(f"Session has no turns: {info['path']}")
    last = info["turns"][-1]
    if last["status"] != "complete":
        print(f"(The last turn is {last['status']}; showing Codex's last message from it.)\n", file=sys.stderr)
    turns = info["turns"] if args.all else [last]
    for i, turn in enumerate(turns, 1):
        if args.all:
            status = "" if turn["status"] == "complete" else f" [{turn['status']}]"
            print(f"{'' if i == 1 else chr(10)}===== Turn {i}/{len(turns)}{status}: {first_line(turn['prompt'])}\n")
        print(turn["answer"] or "(Codex produced no response text for this turn.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
