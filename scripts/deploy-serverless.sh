#!/usr/bin/env bash
# Deploy Promptory serverless stack via AWS SAM.
# Usage: ./scripts/deploy-serverless.sh [--guided]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
INFRA_DIR="$REPO_ROOT/infra"

echo "==> Building SAM package..."
cd "$INFRA_DIR"
sam build

if [[ "${1:-}" == "--guided" ]]; then
    echo "==> Deploying (guided)..."
    sam deploy --guided
else
    echo "==> Deploying..."
    sam deploy
fi

echo ""
echo "==> Deployment complete. Stack outputs:"
sam list stack-outputs --stack-name "$(grep stack_name samconfig.toml | head -1 | cut -d'"' -f2)" 2>/dev/null || \
    echo "(Run 'sam list stack-outputs --stack-name <name>' to view outputs)"
