#!/bin/bash
# deploy.sh
# Mission Veteran AI by G3 — Full stack import + promote to Live
#
# Usage:
#   ./deploy.sh              — import everything to Draft only
#   ./deploy.sh --live       — import to Draft, then promote all agents to Live
#   ./deploy.sh --live-only  — promote already-imported agents to Live (skip import)
#
# Prerequisites:
#   1. Orchestrate CLI installed and authenticated:
#        orchestrate env activate <your-env>
#   2. Secrets set in Orchestrate (Draft + Live):
#        WATSONX_API_KEY, WATSONX_URL, WATSONX_PROJECT_ID
#   3. Connection app_id 'watsonx_credentials' already created, or run:
#        orchestrate connections import -f connections/watsonx_credentials.yaml
#   4. For governance: GOVERNANCE_INSTANCE_GUID set in environment:
#        export GOVERNANCE_INSTANCE_GUID=<your-openscale-instance-guid>

set -euo pipefail

LIVE=false
LIVE_ONLY=false

for arg in "$@"; do
  case $arg in
    --live)      LIVE=true ;;
    --live-only) LIVE_ONLY=true ;;
    *)
      echo "Unknown argument: $arg"
      echo "Usage: ./deploy.sh [--live] [--live-only]"
      exit 1 ;;
  esac
done

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${BLUE}▶ $1${NC}"; }
ok()   { echo -e "${GREEN}✓ $1${NC}"; }
warn() { echo -e "${YELLOW}⚠ $1${NC}"; }

# ── Import phase ────────────────────────────────────────────────────────────
if [ "$LIVE_ONLY" = false ]; then

  echo ""
  log "=== Step 1: Import tools ==="

  log "  translate_bullet"
  orchestrate tools import \
    --kind python \
    --file toolkits/bullet_translator/translate_bullet.py \
    --package-root toolkits \
    --requirements-file requirements.txt \
    --app-id watsonx_credentials
  ok "  translate_bullet imported"

  log "  map_military_skills"
  orchestrate tools import \
    --kind python \
    --file toolkits/skill_mapper/map_military_skills.py \
    --package-root toolkits \
    --requirements-file requirements.txt \
    --app-id watsonx_credentials
  ok "  map_military_skills imported"

  log "  analyze_skills_gap"
  orchestrate tools import \
    --kind python \
    --file toolkits/gap_analyzer/analyze_skills_gap.py \
    --package-root toolkits \
    --requirements-file requirements.txt \
    --app-id watsonx_credentials
  ok "  analyze_skills_gap imported"

  log "  analyze_job_description + build_resume_draft + evaluate_export_gate"
  orchestrate tools import \
    --kind python \
    --file toolkits/plan_builder/build_plan.py \
    --package-root toolkits \
    --requirements-file requirements.txt \
    --app-id watsonx_credentials
  ok "  plan_builder tools imported"

  echo ""
  log "=== Step 2: Import sub-agents ==="

  log "  bullet_translator_agent"
  orchestrate agents import -f agents/bullet_translator_agent.yaml
  ok "  bullet_translator_agent imported"

  log "  skill_mapper_agent"
  orchestrate agents import -f agents/skill_mapper_agent.yaml
  ok "  skill_mapper_agent imported"

  log "  gap_analyzer_agent"
  orchestrate agents import -f agents/gap_analyzer_agent.yaml
  ok "  gap_analyzer_agent imported"

  log "  plan_builder_agent"
  orchestrate agents import -f agents/plan_builder_agent.yaml
  ok "  plan_builder_agent imported"

  echo ""
  log "=== Step 3: Import coordinator ==="
  orchestrate agents import -f agents/coordinator_agent.yaml
  ok "  coordinator_agent imported"

  echo ""
  log "=== Step 4: Register watsonx Governance ==="
  if [ -z "${GOVERNANCE_INSTANCE_GUID:-}" ]; then
    warn "GOVERNANCE_INSTANCE_GUID not set — skipping governance registration."
    warn "Set it with: export GOVERNANCE_INSTANCE_GUID=<your-openscale-instance-guid>"
  else
    python governance/register_factsheets.py
    ok "  AI Factsheets and monitors registered"
  fi

  echo ""
  ok "=== Draft import complete ==="
  echo ""
  warn "Verify agents in Draft before promoting to Live."
  warn "Run './deploy.sh --live-only' when ready to promote."

fi

# ── Promote to Live ─────────────────────────────────────────────────────────
if [ "$LIVE" = true ] || [ "$LIVE_ONLY" = true ]; then

  echo ""
  log "=== Step 5: Deploy to Live ==="
  warn "This promotes the current Draft snapshot to the Live (test) environment."
  warn "Testers will immediately see the new version."
  echo ""

  log "  deploying bullet_translator"
  orchestrate agents deploy --name bullet_translator
  ok "  bullet_translator → Live"

  log "  deploying skill_mapper"
  orchestrate agents deploy --name skill_mapper
  ok "  skill_mapper → Live"

  log "  deploying gap_analyzer"
  orchestrate agents deploy --name gap_analyzer
  ok "  gap_analyzer → Live"

  log "  deploying plan_builder"
  orchestrate agents deploy --name plan_builder
  ok "  plan_builder → Live"

  log "  deploying coordinator"
  orchestrate agents deploy --name coordinator
  ok "  coordinator → Live"

  echo ""
  ok "=== Live deployment complete ==="
  echo ""
  warn "Notify tester — Live environment has been updated."

fi
