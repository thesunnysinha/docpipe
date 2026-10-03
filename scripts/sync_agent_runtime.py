"""Copy the shared agent runtime into ``src/docpipe/agents/_runtime``.

The runtime lives in master-project-template (``blueprints/shared/services/agent``). docpipe is a
published package, so it carries a copy with the import prefix rewritten instead of depending on
that repository. Change the runtime in the template, then run this script again.

    python scripts/sync_agent_runtime.py /path/to/master-project-template
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

SOURCE_PREFIX = "shared.services.agent"
TARGET_PREFIX = "docpipe.agents._runtime"
FILES = (
    "__init__.py",
    "errors.py",
    "telemetry.py",
    "tool_agent.py",
    "tool_logging.py",
    "guardrails/__init__.py",
    "guardrails/base.py",
    "guardrails/loop_guard.py",
    "guardrails/pii.py",
    "guardrails/security.py",
)
TARGET = Path(__file__).resolve().parents[1] / "src" / "docpipe" / "agents" / "_runtime"


def _source_commit(template: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(template), "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() or "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="path to master-project-template")
    args = parser.parse_args()
    source = args.template / "blueprints" / "shared" / "services" / "agent"
    for relative in FILES:
        text = (source / relative).read_text(encoding="utf-8")
        destination = TARGET / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text.replace(SOURCE_PREFIX, TARGET_PREFIX), encoding="utf-8")
    commit = _source_commit(args.template)
    (TARGET / "README.md").write_text(
        "# Vendored agent runtime\n\n"
        "Copied from master-project-template (`blueprints/shared/services/agent`) at commit "
        f"`{commit}` by `scripts/sync_agent_runtime.py`, with the import prefix "
        f"`{SOURCE_PREFIX}` rewritten to `{TARGET_PREFIX}`. Do not edit these files here: change "
        "them in the template and run the script again. The folder is excluded from ruff and "
        "mypy for that reason, and it is only imported by the optional `runtime` agent backend "
        "(`pip install docpipe-sdk[agents]`).\n",
        encoding="utf-8",
    )
    print(f"synced {len(FILES)} files from {commit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
