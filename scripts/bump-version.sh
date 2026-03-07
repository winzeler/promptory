#!/usr/bin/env bash
set -euo pipefail

# bump-version.sh — Update version across all Promptdis components
#
# Usage:
#   ./scripts/bump-version.sh 0.2.0        # explicit version
#   ./scripts/bump-version.sh patch         # 0.1.0 → 0.1.1
#   ./scripts/bump-version.sh minor         # 0.1.0 → 0.2.0
#   ./scripts/bump-version.sh major         # 0.1.0 → 1.0.0

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/VERSION"

current_version=$(cat "$VERSION_FILE" | tr -d '[:space:]')

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version|patch|minor|major>"
  echo "Current version: $current_version"
  exit 1
fi

arg="$1"

bump_semver() {
  local version="$1" part="$2"
  IFS='.' read -r major minor patch <<< "$version"
  case "$part" in
    major) echo "$((major + 1)).0.0" ;;
    minor) echo "$major.$((minor + 1)).0" ;;
    patch) echo "$major.$minor.$((patch + 1))" ;;
  esac
}

case "$arg" in
  patch|minor|major)
    new_version=$(bump_semver "$current_version" "$arg")
    ;;
  *)
    if [[ ! "$arg" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
      echo "Error: version must be semver (e.g., 1.2.3) or patch|minor|major"
      exit 1
    fi
    new_version="$arg"
    ;;
esac

echo "Bumping version: $current_version → $new_version"
echo ""

# 1. VERSION file (source of truth)
echo "$new_version" > "$VERSION_FILE"
echo "  Updated VERSION"

# 2. Root pyproject.toml — uses dynamic versioning, reads VERSION file automatically
echo "  Root pyproject.toml — reads VERSION dynamically (no change needed)"

# 3. SDK pyproject.toml (sdk-py)
sed -i.bak "s/^version = \".*\"/version = \"$new_version\"/" "$REPO_ROOT/sdk-py/pyproject.toml"
rm -f "$REPO_ROOT/sdk-py/pyproject.toml.bak"
echo "  Updated sdk-py/pyproject.toml"

# 4. package.json files (web, sdk-js, sdk-ts)
for pkg in web sdk-js sdk-ts; do
  (cd "$REPO_ROOT/$pkg" && npm version "$new_version" --no-git-tag-version --allow-same-version) > /dev/null 2>&1
  echo "  Updated $pkg/package.json"
done

echo ""
echo "Version bumped to $new_version in:"
echo "  - VERSION"
echo "  - sdk-py/pyproject.toml"
echo "  - web/package.json"
echo "  - sdk-js/package.json"
echo "  - sdk-ts/package.json"
echo ""
echo "Next steps:"
echo "  git add -A && git commit -m \"Bump version to $new_version\""
echo "  git push origin main"
