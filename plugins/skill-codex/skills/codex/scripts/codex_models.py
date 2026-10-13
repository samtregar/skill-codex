#!/usr/bin/env python3
"""List the models Codex can use with the current config, by their exact IDs.

Model IDs depend on the configured model provider. With OpenAI they are bare
(gpt-6-astra); with Amazon Bedrock they carry a prefix (openai.gpt-6-astra,
or global.openai.gpt-6-astra / us.openai.gpt-6-astra for cross-region).
Pass an ID to `codex exec -m` exactly as printed here.

The supported reasoning efforts also vary by provider (e.g. no ultra on
Bedrock), so each model's efforts are listed with it.

  codex_models.py                 models offered for the current config
  codex_models.py --all           ...including ones Codex hides from its picker
  codex_models.py -c KEY=VALUE    pass a config override to Codex (repeatable),
                                  e.g. -c model_provider=amazon-bedrock

Models marked [default] are the provider's gpt-6-astra, if it offers one.
With amazon-bedrock-runtime there are several (global. and us. variants).
"""
import argparse
import json
import subprocess
import sys

DEFAULT_MODEL = "gpt-6-astra"


def catalog(overrides):
    cmd = ["codex", "debug", "models"]
    for kv in overrides:
        cmd += ["-c", kv]
    try:
        # codex reads stdin when it is open, so close it.
        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=120)
    except FileNotFoundError:
        sys.exit("codex is not on PATH.")
    except subprocess.TimeoutExpired:
        sys.exit("`codex debug models` timed out.")
    if proc.returncode != 0:
        sys.exit(f"`codex debug models` failed (exit {proc.returncode}):\n{proc.stderr.strip()}")
    try:
        models = json.loads(proc.stdout)["models"]
    except (ValueError, KeyError, TypeError):
        models = None
    if not isinstance(models, list):
        sys.exit("Could not parse the output of `codex debug models`.")
    return [m for m in models if isinstance(m, dict) and isinstance(m.get("slug"), str)]


def efforts(model):
    levels = model.get("supported_reasoning_levels")
    if not isinstance(levels, list):
        return []
    return [lv["effort"] for lv in levels if isinstance(lv, dict) and isinstance(lv.get("effort"), str)]


def is_default(slug):
    # Match gpt-6-astra under any provider prefix, but not e.g. gpt-6-astra-mini.
    return slug == DEFAULT_MODEL or slug.endswith("." + DEFAULT_MODEL)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="include models Codex hides from its picker")
    ap.add_argument("-c", dest="overrides", action="append", default=[], metavar="KEY=VALUE",
                    help="config override passed to codex (repeatable)")
    args = ap.parse_args()

    models = [m for m in catalog(args.overrides) if args.all or m.get("visibility") == "list"]
    if not models:
        sys.exit("Codex reported no models for this config.")

    defaults = [m["slug"] for m in models if is_default(m["slug"])]
    width = max(len(m["slug"]) for m in models)
    name_width = max(len(str(m.get("display_name") or "")) for m in models)
    print("Pass the model ID to `codex exec -m` exactly as shown.\n")
    for m in models:
        name = str(m.get("display_name") or "")
        flags = "  [default]" if m["slug"] in defaults else ""
        if m.get("visibility") != "list":
            flags += "  [hidden]"
        print(f"  {m['slug']:<{width}}  {name:<{name_width}}  efforts: {' '.join(efforts(m))}{flags}")
    if not defaults:
        print(f"\nNo {DEFAULT_MODEL} model is offered with this config; there is no [default].")
    elif len(defaults) > 1:
        # e.g. the global. and us. cross-region variants on Bedrock.
        print(f"\nSeveral {DEFAULT_MODEL} variants are offered; ask the user which [default] to use.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
