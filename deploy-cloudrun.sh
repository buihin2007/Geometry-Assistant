#!/usr/bin/env bash
# Deploy 2 backend lên Google Cloud Run (scale-to-zero, ~$0 khi rảnh).
# Dùng:  ! gcloud auth login            (đăng nhập 1 lần)
#        ! bash deploy-cloudrun.sh <GCP_PROJECT_ID>
# Secret đọc từ .env (gitignored) → truyền qua --set-env-vars (KHÔNG nằm trong script).
# Frontend KHÔNG ở đây (deploy Cloudflare Pages riêng; dùng ORCH_URL in ra cuối).
set -euo pipefail
cd "$(dirname "$0")"

PROJECT="${1:-${GCP_PROJECT:-}}"
REGION="${REGION:-asia-southeast1}"   # gần VN; đổi nếu muốn
[ -z "$PROJECT" ] && { echo "Usage: bash deploy-cloudrun.sh <GCP_PROJECT_ID>"; exit 1; }
[ -f .env ] || { echo "Thiếu .env (chứa key LLM/Supabase)"; exit 1; }

val(){ grep -E "^$1=" .env | head -1 | cut -d= -f2-; }
ANTH=$(val LLM_API_KEY)
MODEL=$(val LLM_MODEL); MODEL="${MODEL:-claude-haiku-4-5}"
SUPA_URL=$(val SUPABASE_URL); SUPA_ANON=$(val SUPABASE_ANON_KEY); SUPA_SR=$(val SUPABASE_SERVICE_ROLE_KEY)
[ -z "$ANTH" ] && { echo "Thiếu LLM_API_KEY trong .env"; exit 1; }

echo "▶ project=$PROJECT  region=$REGION"
gcloud config set project "$PROJECT" >/dev/null
echo "▶ Bật API cần thiết…"
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com >/dev/null

echo "▶ Deploy ggb-service (2Gi, scale-to-zero, CPU không throttle để giữ Chromium ấm)…"
gcloud run deploy ggb-service \
  --source ./ggb-service --region "$REGION" \
  --memory 2Gi --cpu 1 --no-cpu-throttling \
  --concurrency 1 --timeout 300 --max-instances 5 --min-instances 0 \
  --allow-unauthenticated --quiet
GGB_URL=$(gcloud run services describe ggb-service --region "$REGION" --format 'value(status.url)')
echo "  ✓ ggb-service: $GGB_URL"

echo "▶ Deploy orchestrator (512Mi, scale-to-zero)…"
# Dùng delimiter ^@^ để giá trị an toàn (không phụ thuộc dấu phẩy).
ENV="^@^LLM_PROVIDER=anthropic@LLM_MODEL=$MODEL@LLM_API_KEY=$ANTH"
ENV="$ENV@GENERATOR_PROVIDER=anthropic@GENERATOR_MODEL=$MODEL@GENERATOR_API_KEY=$ANTH"
ENV="$ENV@REVIEWER_PROVIDER=anthropic@REVIEWER_MODEL=$MODEL@REVIEWER_API_KEY=$ANTH"
ENV="$ENV@ENABLE_REVIEW=true@MAX_FIX_ROUNDS=2@MAX_LLM_CALLS_PER_REQUEST=8@USE_PLANNER=true"
ENV="$ENV@DEMO_LIMIT_PER_IP=2@GGB_SERVICE_URL=$GGB_URL"
ENV="$ENV@SUPABASE_URL=$SUPA_URL@SUPABASE_ANON_KEY=$SUPA_ANON@SUPABASE_SERVICE_ROLE_KEY=$SUPA_SR"
gcloud run deploy orchestrator \
  --source ./orchestrator --region "$REGION" \
  --memory 512Mi --cpu 1 --timeout 300 --max-instances 5 --min-instances 0 \
  --allow-unauthenticated --quiet \
  --set-env-vars "$ENV"
ORCH_URL=$(gcloud run services describe orchestrator --region "$REGION" --format 'value(status.url)')

echo ""
echo "✅ XONG."
echo "   ggb-service : $GGB_URL"
echo "   orchestrator: $ORCH_URL"
echo ""
echo "→ Cloudflare Pages (build env):  VITE_API_URL=$ORCH_URL"
echo "→ Smoke test:                    curl $ORCH_URL/health"
