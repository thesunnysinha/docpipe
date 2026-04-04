#!/bin/bash
# Release script for docpipe
# Usage: ./scripts/release.sh 0.2.0

set -euo pipefail

VERSION="${1:?Usage: $0 <version>}"

echo "Releasing docpipe v${VERSION}..."

# Update version in source
sed -i.bak "s/__version__ = \".*\"/__version__ = \"${VERSION}\"/" src/docpipe/_version.py
rm -f src/docpipe/_version.py.bak

# Update version in pyproject.toml
sed -i.bak "s/^version = \".*\"/version = \"${VERSION}\"/" pyproject.toml
rm -f pyproject.toml.bak

# Stage changes
git add src/docpipe/_version.py pyproject.toml

# Commit
git commit -m "release: v${VERSION}"

# Tag
git tag -a "v${VERSION}" -m "Release v${VERSION}"

echo ""
echo "Done! To publish:"
echo "  git push origin main --tags"
echo ""
echo "GitHub Actions will automatically publish to PyPI."
