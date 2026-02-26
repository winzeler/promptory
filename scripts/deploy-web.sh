#!/usr/bin/env bash
# Build and deploy the Promptdis web UI to S3 + CloudFront.
# Usage: ./scripts/deploy-web.sh --stack <stack-name>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# ── Parse args ──────────────────────────────────────────────────────────────
STACK_NAME=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --stack) STACK_NAME="$2"; shift 2 ;;
        *) echo "Usage: $0 --stack <stack-name>"; exit 1 ;;
    esac
done

if [[ -z "$STACK_NAME" ]]; then
    echo "Error: --stack <stack-name> is required"
    echo "Usage: $0 --stack promptdis-dev"
    exit 1
fi

# ── Read stack outputs ──────────────────────────────────────────────────────
echo "==> Reading stack outputs from $STACK_NAME..."

WEB_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='WebBucketName'].OutputValue" \
    --output text)

DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='WebDistributionId'].OutputValue" \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text)

echo "  Web bucket:      $WEB_BUCKET"
echo "  Distribution ID: $DISTRIBUTION_ID"
echo "  API URL:         $API_URL"

# ── Build web UI ────────────────────────────────────────────────────────────
echo ""
echo "==> Building web UI..."
cd "$REPO_ROOT/web"
export VITE_API_BASE_URL="$API_URL"
npm ci
npm run build

# ── Sync to S3 ──────────────────────────────────────────────────────────────
echo ""
echo "==> Syncing dist/ to s3://$WEB_BUCKET/..."
aws s3 sync dist/ "s3://$WEB_BUCKET/" --delete

# ── Invalidate CloudFront ───────────────────────────────────────────────────
echo ""
echo "==> Invalidating CloudFront cache..."
aws cloudfront create-invalidation \
    --distribution-id "$DISTRIBUTION_ID" \
    --paths "/*" \
    --query "Invalidation.Id" \
    --output text

echo ""
echo "==> Web UI deployed."
echo "  URL: https://$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='WebDistributionUrl'].OutputValue" \
    --output text)"
