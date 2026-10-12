Note: If you want a more autonomous setup for agentic workflows, check out [klaudworks/ralph-meets-rex](https://github.com/klaudworks/ralph-meets-rex).

# Codex Integration for Claude Code

<img width="2288" height="808" alt="skillcodex" src="https://github.com/user-attachments/assets/85336a9f-4680-479e-b3fe-d6a68cadc051" />


## Purpose
Enable Claude Code to invoke the Codex CLI (`codex exec` and session resumes) for automated code analysis, refactoring, and editing workflows.

This is a fork of [skills-directory/skill-codex](https://github.com/skills-directory/skill-codex). It shows you Codex's output verbatim instead of only Claude's summary, and adds a script for viewing earlier Codex sessions. The install steps below install this fork.

## Prerequisites
- `codex` CLI installed and available on `PATH`.
- Codex configured with valid credentials and settings.
- Confirm the installation by running `codex --version`; resolve any errors before using the skill.
- Python 3, for viewing earlier Codex output (`scripts/codex_review.py`).

## Installation

This repository is structured as a [Claude Code Plugin](https://code.claude.com/docs/en/plugins) with a marketplace. You can install it as a **plugin** (recommended) or extract it as a **standalone skill**.

### Option 1: Plugin Installation (Recommended)

Install via Claude Code's plugin system for automatic updates:

```
/plugin marketplace add samtregar/skill-codex
/plugin install skill-codex@skill-codex
```

If you already added the upstream `skills-directory/skill-codex` marketplace, remove it first with `/plugin marketplace remove skill-codex`. Both marketplaces use the name `skill-codex`.

### Option 2: Standalone Skill Installation

Extract the skill folder manually:

```
git clone --depth 1 https://github.com/samtregar/skill-codex.git /tmp/skills-temp && \
mkdir -p ~/.claude/skills && \
cp -r /tmp/skills-temp/plugins/skill-codex/skills/codex ~/.claude/skills/codex && \
rm -rf /tmp/skills-temp
```

## Usage

### Important: Thinking Tokens
By default, this skill suppresses thinking tokens (stderr output) using `2>/dev/null` to avoid bloating Claude Code's context window. If you want to see the thinking tokens for debugging or insight into Codex's reasoning process, explicitly ask Claude to show them.

### Example Workflow

**User prompt:**
```
Use codex to analyze this repository and suggest improvements for my claude code skill.
```

**Claude Code response:**
Claude will activate the Codex skill and:
1. Ask which model to use (`gpt-6-astra` by default; `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`; or a legacy model such as `gpt-5.5`) unless already specified in your prompt.
2. Ask which reasoning effort level (`low`, `medium`, `high`, `xhigh`, `max`, or `ultra`, subject to the model's ceiling) unless already specified in your prompt.
3. Select appropriate sandbox mode (defaults to `read-only` for analysis)
4. Run a command like:
```bash
codex exec -m gpt-6-astra \
  --config model_reasoning_effort="high" \
  --sandbox read-only \
  --full-auto \
  --skip-git-repo-check \
  "Analyze this Claude Code skill repository comprehensively..." 2>/dev/null
```

**Result:**
Claude will show Codex's response verbatim, then give its own assessment separately and ask if you'd like to continue with follow-up actions.

### Viewing Earlier Codex Output
Codex saves every session under `~/.codex/sessions/` (or `$CODEX_HOME/sessions` if `CODEX_HOME` is set). Ask Claude to "show me Codex's last review" (or a list of recent Codex sessions) and it will run the bundled `scripts/codex_review.py` to print the response verbatim. You can also run it yourself:

```bash
python3 plugins/skill-codex/skills/codex/scripts/codex_review.py --list         # recent sessions
python3 plugins/skill-codex/skills/codex/scripts/codex_review.py -n 2 --all     # every turn of session #2
```

### Detailed Instructions
See [`plugins/skill-codex/skills/codex/SKILL.md`](plugins/skill-codex/skills/codex/SKILL.md) for complete operational instructions, CLI options, and workflow guidance.
