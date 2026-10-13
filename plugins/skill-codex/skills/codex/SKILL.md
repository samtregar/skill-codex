---
name: codex
description: Use when the user asks to run Codex CLI (codex exec, codex resume) or references OpenAI Codex for code analysis, refactoring, or automated editing
---

# Codex Skill Guide

## Running a Task
1. For a new session (resumes inherit the prior model/effort — see step 5), first list the models Codex offers with the user's setup:
   ```bash
   python3 <skill-dir>/scripts/codex_models.py
   ```
   Model IDs depend on the configured provider. With OpenAI they are bare (`gpt-6-astra`); on Amazon Bedrock they carry a prefix (`openai.gpt-6-astra`, or `global.openai.gpt-6-astra` / `us.openai.gpt-6-astra` for cross-region). **Always pass `-m` an ID exactly as the script prints it**, never a bare name from this file. (`<skill-dir>` is explained in *Viewing Past Codex Output*.)

   Then ask the user (via `AskUserQuestion`) which **model** AND which **reasoning effort** to use, in a **single prompt with two questions**, offering only what the script listed. When the user expresses no preference, use the model the script marks `[default]` (the provider's `gpt-6-astra`) at `high`.
   - **Model** — label options by tier: `astra` is frontier / most capable (**default**), `sol` a reliable agentic workhorse, `terra` balanced for everyday work, `luna` fast & affordable.
     - If the user names a model by its bare name (e.g. `gpt-6-sol`), use the listed ID that ends in it (`openai.gpt-6-sol` on Bedrock). If more than one matches (the `global.` and `us.` cross-region variants), ask which.
     - If the user names a model that isn't listed, rerun the script with `--all`, which includes models Codex hides from its picker. If it is still missing, tell the user Codex doesn't list it for their provider and ask before trying it anyway.
   - **Reasoning effort** — default `high`. Offer only the efforts the script lists for the chosen model; they vary by model and provider (e.g. Bedrock has no `ultra`).
     - `ultra` = maximum reasoning **with automatic task delegation** (slowest and most expensive — reserve for the hardest jobs).
     - If the chosen effort isn't listed for the chosen model, fall back to that model's highest listed effort and tell the user.
   - If the user runs Codex with a profile (`-p`), pass the profile's `model_provider` to the script as `-c model_provider=<id>`, since `codex debug models` ignores profiles.
   - If the script fails (e.g. a Codex too old to have `codex debug models`), tell the user, then fall back to the OpenAI defaults: models `gpt-6-astra` (default), `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`; efforts `low`, `medium`, `high`, `xhigh`, `max`, `ultra`, where `luna` caps at `max`.
2. Select the sandbox mode required for the task; default to `--sandbox read-only` unless edits or network access are necessary.
3. Assemble the command with the appropriate options:
   - `-m, --model <MODEL>` (the model ID exactly as `codex_models.py` printed it — see step 1)
   - `--config model_reasoning_effort="<low|medium|high|xhigh|max|ultra>"` (only an effort `codex_models.py` listed for that model)
   - `--sandbox <read-only|workspace-write|danger-full-access>`
   - `--full-auto`
   - `-C, --cd <DIR>`
   - `--skip-git-repo-check`
   - `"your prompt here"` (as final positional argument)
4. Always use --skip-git-repo-check.
5. When continuing a previous session, use `codex exec --skip-git-repo-check resume --last` via stdin. When resuming don't use any configuration flags unless explicitly requested by the user e.g. if he species the model or the reasoning effort when requesting to resume a session (resolve a requested model to its listed ID as in step 1). Resume syntax: `echo "your prompt here" | codex exec --skip-git-repo-check resume --last 2>/dev/null`. All flags have to be inserted between exec and resume.
6. **IMPORTANT**: By default, append `2>/dev/null` to all `codex exec` commands to suppress thinking tokens (stderr). Only show stderr if the user explicitly requests to see thinking tokens or if debugging is needed.
7. **IMPORTANT (stdin)**: `codex exec` always reads stdin and concatenates it with the positional prompt -- even when the prompt is fully supplied as a positional argument. If stdin is not closed, codex blocks forever. When invoking from a harness (background tasks, hooks, scripts where stdin is not a TTY but also not closed), explicitly redirect stdin: append `</dev/null` to the command, e.g. `codex exec ... "prompt" </dev/null 2>/dev/null`. Symptom of getting this wrong: zero bytes of stdout, zero CPU accumulated, process appears hung indefinitely.
8. Run the command and wait for it to finish (for a background run, wait for its completion notice; launching is not finishing). With `2>/dev/null`, stdout is exactly Codex's final message.
9. **Show Codex's output to the user verbatim** after every `codex exec` run, including resumes. Tool output is collapsed in the user's view, so this is how they see what Codex actually said. Under a `### Codex's response` heading, reproduce stdout exactly as written: no summarizing, trimming, reordering, or rewording. Then, under a separate `### Claude's take` heading, give your own assessment (see *Critical Evaluation of Codex Output*). Skip the verbatim copy only if the user asked for just a summary.
   - If the captured output was truncated (Claude Code marks long tool output as truncated) or a background run's output file is empty, recover the full text with `codex_review.py` (see *Viewing Past Codex Output*). Redirect it to a file and read that file in parts with the Read tool, so the recovery can't be cut off too. Never present a truncated capture as complete.
   - Before showing recovered text, confirm it is from this run: in `codex_review.py --list`, the session's directory, time and first prompt must match the run you just made. If none matches (e.g. Codex failed before it saved a session), tell the user the output is missing rather than showing another session's answer.
   - If the response is too long to reproduce in one reply, tell the user how long it is and where the full text is saved, and ask whether to paste it in full or in parts.
   - If Codex failed or returned partial output, show whatever it produced verbatim, say plainly that it is incomplete, then follow *Error Handling*.
10. **After Codex completes**, inform the user: "You can resume this Codex session at any time by saying 'codex resume' or asking me to continue with additional analysis or changes."

### Quick Reference
| Use case | Sandbox mode | Key flags |
| --- | --- | --- |
| Read-only review or analysis | `read-only` | `--sandbox read-only 2>/dev/null` |
| Apply local edits | `workspace-write` | `--sandbox workspace-write --full-auto 2>/dev/null` |
| Permit network or broad access | `danger-full-access` | `--sandbox danger-full-access --full-auto 2>/dev/null` |
| Resume recent session | Inherited from original | `echo "prompt" \| codex exec --skip-git-repo-check resume --last 2>/dev/null` (no flags allowed) |
| Run from another directory | Match task needs | `-C <DIR>` plus other flags `2>/dev/null` |

## Execution timeouts

Codex produces **no intermediate output** — it writes the result only at completion. If the process is killed before finishing, the output file is silently empty (no error).

**Preferred approach:** run synchronously — eliminates timeout risk entirely and the conversation waits for the result anyway.

**If running in background**, set the execution timeout based on reasoning effort:

| Reasoning effort | Timeout |
|---|---|
| `low` | 150s |
| `medium` | 300s |
| `high` | 600s |
| `xhigh` | 1200s |
| `max` | 1800s |
| `ultra` | 1800s |

## Following Up
- After every `codex` command, once you have shown Codex's response and your take (step 9), use `AskUserQuestion` to confirm next steps, collect clarifications, or decide whether to resume with `codex exec resume --last`.
- When resuming, pipe the new prompt via stdin: `echo "new prompt" | codex exec resume --last 2>/dev/null`. The resumed session automatically uses the same model, reasoning effort, and sandbox mode from the original session.
- Restate the chosen model, reasoning effort, and sandbox mode when proposing follow-up actions.

## Viewing Past Codex Output
Codex saves every session, including ones run in the Codex TUI, under `~/.codex/sessions/` (or `$CODEX_HOME/sessions`). When the user asks to see an earlier Codex response, or a captured output was truncated or lost (step 9), run the bundled script and show its output verbatim, as in step 9.

Call the script by its absolute path: `<skill-dir>` below is the "Base directory for this skill" shown when this skill loaded. Run it from the user's project; do not `cd` into the skill directory. For `--cwd`, pass the directory Codex ran in: the `-C` directory if one was used, otherwise the current project directory.

```bash
python3 <skill-dir>/scripts/codex_review.py --cwd <codex-dir>        # last answer from the latest session run in that directory
python3 <skill-dir>/scripts/codex_review.py --cwd <codex-dir> --all  # every turn of that session (the original review plus each resume)
python3 <skill-dir>/scripts/codex_review.py --list                   # recent sessions: index, time, directory, first prompt
python3 <skill-dir>/scripts/codex_review.py -n 3                     # session #3 from --list (pass the same --cwd to both, if any)
```

Turns that were interrupted or never finished are labeled as such, and the script warns on stderr when the last turn is not complete. Codex's internal sessions (e.g. the auto-approval "guardian") are skipped; add `--internal` to include them.

## Critical Evaluation of Codex Output

Codex is powered by OpenAI models with their own knowledge cutoffs and limitations. Treat Codex as a **colleague, not an authority**.

### Guidelines
- **Trust your own knowledge** when confident. If Codex claims something you know is incorrect, push back directly.
- **Research disagreements** using WebSearch or documentation before accepting Codex's claims. Share findings with Codex via resume if needed.
- **Remember knowledge cutoffs** - Codex may not know about recent releases, APIs, or changes that occurred after its training data.
- **Don't defer blindly** - Codex can be wrong. Evaluate its suggestions critically, especially regarding:
  - Model names and capabilities
  - Recent library versions or API changes
  - Best practices that may have evolved

### When Codex is Wrong
1. State your disagreement clearly to the user
2. Provide evidence (your own knowledge, web search, docs)
3. Optionally resume the Codex session to discuss the disagreement. **Identify yourself as Claude** so Codex knows it's a peer AI discussion. Use your actual model name (e.g., the model you are currently running as) instead of a hardcoded name:
   ```bash
   echo "This is Claude (<your current model name>) following up. I disagree with [X] because [evidence]. What's your take on this?" | codex exec --skip-git-repo-check resume --last 2>/dev/null
   ```
4. Frame disagreements as discussions, not corrections - either AI could be wrong
5. Let the user decide how to proceed if there's genuine ambiguity

## Error Handling
- Stop and report failures whenever `codex --version` or a `codex exec` command exits non-zero; request direction before retrying.
- Before you use high-impact flags (`--full-auto`, `--sandbox danger-full-access`, `--skip-git-repo-check`) ask the user for permission using AskUserQuestion unless it was already given.
- When output includes warnings or partial results, show the output verbatim as in step 9, summarize the warnings, and ask how to adjust using `AskUserQuestion`.
