#!/usr/bin/env python3
"""Unified ops script for docpipe."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent


def run(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, cwd=ROOT)


def venv_python() -> str:
    venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.exists() else sys.executable


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_release(version: str) -> None:
    """Bump version, commit, tag. Push with: git push origin main --tags"""
    version = version.lstrip("v")

    version_file = ROOT / "src" / "docpipe" / "_version.py"
    pyproject = ROOT / "pyproject.toml"

    version_file.write_text(f'__version__ = "{version}"\n')

    content = pyproject.read_text()
    content = re.sub(r'^version = ".*"', f'version = "{version}"', content, flags=re.MULTILINE)
    pyproject.write_text(content)

    run("git", "add", str(version_file), str(pyproject))
    run("git", "commit", "-m", f"release: v{version}")
    run("git", "tag", "-a", f"v{version}", "-m", f"Release v{version}")

    print(f"\nReleased v{version}. Publish with:")
    print("  git push origin main --tags")


def cmd_test(*args: str) -> None:
    """Run pytest."""
    run(venv_python(), "-m", "pytest", *args)


def cmd_lint() -> None:
    """Run ruff check + format check."""
    run(venv_python(), "-m", "ruff", "check", "src", "tests")
    run(venv_python(), "-m", "ruff", "format", "--check", "src", "tests")


def cmd_build() -> None:
    """Build wheel + sdist."""
    run(venv_python(), "-m", "hatchling", "build")


def cmd_serve(*args: str) -> None:
    """Start docpipe FastAPI server."""
    run(venv_python(), "-m", "uvicorn", "docpipe.server.app:app", "--reload", *args)


def usage() -> None:
    print("Usage: python run.py <command> [args]")
    print()
    print("Commands:")
    print("  release <version>   Bump version, commit, tag (e.g. 0.4.3)")
    print("  test [pytest args]  Run pytest")
    print("  lint                Run ruff check + format check")
    print("  build               Build wheel + sdist")
    print("  serve               Start FastAPI dev server")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        usage()
        sys.exit(1)

    cmd, *rest = args

    if cmd == "release":
        if not rest:
            print("Error: version required. Example: python run.py release 0.4.3")
            sys.exit(1)
        cmd_release(rest[0])
    elif cmd == "test":
        cmd_test(*rest)
    elif cmd == "lint":
        cmd_lint()
    elif cmd == "build":
        cmd_build()
    elif cmd == "serve":
        cmd_serve(*rest)
    else:
        print(f"Unknown command: {cmd}")
        usage()
        sys.exit(1)
