# Makefile
# Mission Veteran AI by G3
#
# ── First-time setup ────────────────────────────────────────────────────────
#
#   OPTION A — You already have a watsonx Orchestrate instance
#   (hackathon trial, existing paid plan, or pre-provisioned):
#
#     cp .env.example .env          # fill in WATSONX_API_KEY / PROJECT_ID
#     orchestrate env activate ...  # authenticate the Orchestrate CLI
#     make setup                    # install deps + import agents + deploy bridge
#
#   OPTION B — You need to provision a new Orchestrate instance:
#
#     cp .env.example .env
#     cp terraform/terraform.tfvars.example terraform/terraform.tfvars
#     make provision                # Terraform: creates Orchestrate + Governance
#     orchestrate env activate ...
#     make setup
#
#   Terraform is OPTIONAL — skip it entirely if you already have an instance.
#   Governance (AI Factsheets) is also optional; omit GOVERNANCE_INSTANCE_GUID
#   in .env and the governance step is skipped automatically.
#
# ── Day-to-day development ──────────────────────────────────────────────────
#   make deploy           # re-import tools + agents + governance to Draft
#   make promote          # promote current Draft snapshot to Live (notify tester)
#   make deploy-live      # import + promote in one step
#   make bridge-run       # run bridge server locally (http://localhost:8080)
#   make bridge-deploy    # rebuild + push + redeploy bridge on Code Engine
#
# ── GitHub Pages ────────────────────────────────────────────────────────────
#   make pages-secret     # print instructions to set the API_BASE secret
#   git push origin main  # triggers .github/workflows/pages.yml automatically
#
# ── Teardown ────────────────────────────────────────────────────────────────
#   make destroy          # remove all agents from Orchestrate
#   make bridge-destroy   # delete Code Engine app + container image
#   cd terraform && terraform destroy   # (optional) destroy IBM Cloud instances

.PHONY: all setup provision deploy deploy-live promote destroy \
        bridge-install bridge-run bridge-build bridge-push \
        bridge-deploy bridge-destroy bridge-logs bridge-url \
        pages-secret \
        test test-unit lint register-governance governance help

DEPLOY_SCRIPT := ./deploy.sh

# ── Colours ─────────────────────────────────────────────────────────────────
BLUE   := \033[0;34m
GREEN  := \033[0;32m
YELLOW := \033[1;33m
RED    := \033[0;31m
NC     := \033[0m

# ── Bridge / Code Engine configuration ──────────────────────────────────────
# Override any of these on the command line, e.g.:
#   make bridge-deploy CE_REGION=eu-de
#
# IBM Container Registry namespace (must exist: ibmcloud cr namespace-add <NS>)
ICR_NAMESPACE    ?= mission-veteran-ai
ICR_REGION       ?= us.icr.io
IMAGE_NAME       ?= mission-veteran-ai-bridge
IMAGE_TAG        ?= latest
IMAGE            := $(ICR_REGION)/$(ICR_NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)

# IBM Code Engine — project and app
CE_REGION        ?= us-south
CE_RESOURCE_GROUP ?= Default
CE_PROJECT       ?= mission-veteran-ai
CE_APP           ?= mission-veteran-ai-bridge
CE_PORT          ?= 8080
CE_MIN_SCALE     ?= 0
CE_MAX_SCALE     ?= 3
CE_CPU           ?= 0.5
CE_MEMORY        ?= 1G

# GitHub repository (owner/repo) — used for pages-secret instructions
GITHUB_REPO      ?= $(shell git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]//' | sed 's/\.git$$//')

# ── Credentials (.env passthrough) ──────────────────────────────────────────
-include .env
export WATSONX_API_KEY
export WATSONX_URL
export WATSONX_PROJECT_ID

# ============================================================================
# Top-level targets
# ============================================================================

## all: Import tools + agents + governance to Draft
all: deploy

## setup: First-time setup — install deps, import agents to Draft, build + deploy bridge
setup: install deploy bridge-build bridge-push bridge-deploy pages-secret
	@echo ""
	@echo "$(GREEN)✓ Setup complete.$(NC)"
	@echo "  Orchestrate agents: Draft"
	@echo "  Bridge server:      $$(make -s bridge-url 2>/dev/null || echo 'see: make bridge-url')"
	@echo ""
	@echo "  Push to main to trigger GitHub Pages deployment:"
	@echo "    git push origin main"

## install: Install all Python dependencies (toolkit + bridge)
install:
	@echo "$(BLUE)▶ Installing Python dependencies...$(NC)"
	pip install -r requirements.txt -r src/requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

# ============================================================================
# Orchestrate targets (existing)
# ============================================================================

## deploy: Import tools + agents + governance to Orchestrate Draft
deploy:
	@echo "$(BLUE)▶ Importing tools, agents, and governance to Draft...$(NC)"
	$(DEPLOY_SCRIPT)

## deploy-live: Import to Draft AND immediately promote to Live
deploy-live:
	@echo "$(YELLOW)⚠ This will update the Live (test) environment.$(NC)"
	$(DEPLOY_SCRIPT) --live

## promote: Promote current Draft snapshot to Live (skip re-import)
promote:
	@echo "$(YELLOW)⚠ Promoting Draft to Live — notify tester after this completes.$(NC)"
	$(DEPLOY_SCRIPT) --live-only

## provision: (Optional) Run Terraform to provision Orchestrate + Governance instances
provision:
	@echo "$(BLUE)▶ Running Terraform (optional — skip if you already have an instance)...$(NC)"
	cd terraform && terraform init -input=false
	cd terraform && terraform apply -input=false -auto-approve
	@echo "$(GREEN)✓ IBM Cloud instances provisioned$(NC)"
	@echo "  Copy governance_instance_guid from output into your .env file."
	@echo "  Then activate the Orchestrate CLI: orchestrate env activate ..."

## destroy: Remove all agents from the Orchestrate instance
destroy:
	@echo "$(YELLOW)⚠ WARNING: This will remove all agents from the Orchestrate instance.$(NC)"
	@read -p "Type 'yes' to confirm: " CONFIRM && [ "$$CONFIRM" = "yes" ] || (echo "Aborted." && exit 1)
	orchestrate agents remove --name coordinator               --kind native
	orchestrate agents remove --name plan_builder              --kind native
	orchestrate agents remove --name gap_analyzer              --kind native
	orchestrate agents remove --name skill_mapper              --kind native
	orchestrate agents remove --name accomplishment_translator --kind native
	@echo "$(GREEN)✓ Agents removed$(NC)"

# ============================================================================
# Bridge server targets
# ============================================================================

## bridge-install: Install bridge server Python dependencies only
bridge-install:
	@echo "$(BLUE)▶ Installing bridge server dependencies...$(NC)"
	pip install -r src/requirements.txt
	@echo "$(GREEN)✓ Bridge dependencies installed$(NC)"

## bridge-run: Run bridge server locally on http://localhost:8080
bridge-run:
	@echo "$(BLUE)▶ Starting bridge server at http://localhost:8080 ...$(NC)"
	@echo "  (Ctrl-C to stop)"
	@if [ -z "$$WATSONX_API_KEY" ]; then \
	  echo "$(YELLOW)⚠ WATSONX_API_KEY not set — AI calls will fail. Check your .env file.$(NC)"; \
	fi
	uvicorn src.server:app --reload --port $(CE_PORT)

## bridge-build: Build the Docker image for the bridge server
bridge-build:
	@echo "$(BLUE)▶ Building Docker image $(IMAGE)...$(NC)"
	docker build -t $(IMAGE) .
	@echo "$(GREEN)✓ Image built: $(IMAGE)$(NC)"

## bridge-push: Push the Docker image to IBM Container Registry
bridge-push:
	@echo "$(BLUE)▶ Logging in to IBM Container Registry ($(ICR_REGION))...$(NC)"
	ibmcloud cr login
	@echo "$(BLUE)▶ Pushing $(IMAGE)...$(NC)"
	docker push $(IMAGE)
	@echo "$(GREEN)✓ Image pushed: $(IMAGE)$(NC)"

## bridge-deploy: Create or update the Code Engine application with the latest image
bridge-deploy:
	@echo "$(BLUE)▶ Targeting Code Engine project '$(CE_PROJECT)' in $(CE_REGION)...$(NC)"
	ibmcloud target -r $(CE_REGION) -g "$(CE_RESOURCE_GROUP)"
	ibmcloud ce project select --name $(CE_PROJECT) 2>/dev/null || \
	  ibmcloud ce project create --name $(CE_PROJECT)
	@echo "$(BLUE)▶ Deploying $(CE_APP)...$(NC)"
	@if ibmcloud ce app get --name $(CE_APP) > /dev/null 2>&1; then \
	  echo "  Updating existing application..."; \
	  ibmcloud ce app update --name $(CE_APP) \
	    --image $(IMAGE) \
	    --env WATSONX_API_KEY="$$WATSONX_API_KEY" \
	    --env WATSONX_PROJECT_ID="$$WATSONX_PROJECT_ID" \
	    --env WATSONX_URL="$${WATSONX_URL:-https://us-south.ml.cloud.ibm.com}" \
	    --env ALLOWED_ORIGINS="https://$(shell echo $(GITHUB_REPO) | cut -d/ -f1).github.io" \
	    --port $(CE_PORT) \
	    --min-scale $(CE_MIN_SCALE) \
	    --max-scale $(CE_MAX_SCALE) \
	    --cpu $(CE_CPU) \
	    --memory $(CE_MEMORY); \
	else \
	  echo "  Creating new application..."; \
	  ibmcloud ce app create --name $(CE_APP) \
	    --image $(IMAGE) \
	    --env WATSONX_API_KEY="$$WATSONX_API_KEY" \
	    --env WATSONX_PROJECT_ID="$$WATSONX_PROJECT_ID" \
	    --env WATSONX_URL="$${WATSONX_URL:-https://us-south.ml.cloud.ibm.com}" \
	    --env ALLOWED_ORIGINS="https://$(shell echo $(GITHUB_REPO) | cut -d/ -f1).github.io" \
	    --port $(CE_PORT) \
	    --min-scale $(CE_MIN_SCALE) \
	    --max-scale $(CE_MAX_SCALE) \
	    --cpu $(CE_CPU) \
	    --memory $(CE_MEMORY); \
	fi
	@echo "$(GREEN)✓ Bridge deployed$(NC)"
	@make -s bridge-url

## bridge-logs: Tail live logs from the Code Engine application
bridge-logs:
	@echo "$(BLUE)▶ Streaming logs for $(CE_APP) (Ctrl-C to stop)...$(NC)"
	ibmcloud target -r $(CE_REGION) -g "$(CE_RESOURCE_GROUP)"
	ibmcloud ce project select --name $(CE_PROJECT)
	ibmcloud ce app logs --name $(CE_APP) --follow

## bridge-url: Print the public URL of the deployed bridge server
bridge-url:
	@ibmcloud target -r $(CE_REGION) -g "$(CE_RESOURCE_GROUP)" > /dev/null 2>&1; \
	ibmcloud ce project select --name $(CE_PROJECT) > /dev/null 2>&1; \
	URL=$$(ibmcloud ce app get --name $(CE_APP) --output json 2>/dev/null \
	       | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status',{}).get('url','(not deployed yet)'))" 2>/dev/null); \
	echo "$$URL"

## bridge-destroy: Delete the Code Engine application and container image
bridge-destroy:
	@echo "$(YELLOW)⚠ WARNING: This will delete the Code Engine app and container image.$(NC)"
	@read -p "Type 'yes' to confirm: " CONFIRM && [ "$$CONFIRM" = "yes" ] || (echo "Aborted." && exit 1)
	ibmcloud target -r $(CE_REGION) -g "$(CE_RESOURCE_GROUP)"
	ibmcloud ce project select --name $(CE_PROJECT)
	ibmcloud ce app delete --name $(CE_APP) --force
	ibmcloud cr image-rm $(IMAGE) || true
	@echo "$(GREEN)✓ Bridge app and image deleted$(NC)"

# ============================================================================
# GitHub Pages
# ============================================================================

## pages-secret: Print instructions to set the API_BASE secret for GitHub Pages
pages-secret:
	@echo ""
	@echo "$(BLUE)GitHub Pages — set the API_BASE secret$(NC)"
	@echo ""
	@BRIDGE_URL=$$(make -s bridge-url 2>/dev/null); \
	if [ -n "$$BRIDGE_URL" ] && [ "$$BRIDGE_URL" != "(not deployed yet)" ]; then \
	  echo "  Bridge URL detected: $$BRIDGE_URL"; \
	  echo ""; \
	  echo "  Add this secret to your GitHub repository:"; \
	  echo "    Repo: https://github.com/$(GITHUB_REPO)/settings/secrets/actions/new"; \
	  echo "    Name:  API_BASE"; \
	  echo "    Value: $$BRIDGE_URL"; \
	else \
	  echo "  Bridge not deployed yet. Run 'make bridge-deploy' first,"; \
	  echo "  then re-run 'make pages-secret' to get the URL."; \
	  echo ""; \
	  echo "  Once deployed, add to:"; \
	  echo "    https://github.com/$(GITHUB_REPO)/settings/secrets/actions/new"; \
	  echo "    Name:  API_BASE"; \
	  echo "    Value: <bridge URL from 'make bridge-url'>"; \
	fi
	@echo ""
	@echo "  After setting the secret, push to main to redeploy Pages:"; \
	@echo "    git push origin main"; \
	@echo ""

# ============================================================================
# Test + Lint
# ============================================================================

## test: Run the full unit test suite
test: test-unit

## test-unit: Run unit tests (no live API calls — mocked)
test-unit:
	@echo "$(BLUE)▶ Running unit tests...$(NC)"
	WATSONX_API_KEY=ci-stub-key WATSONX_PROJECT_ID=ci-stub-project \
	  pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

## lint: Check Python files with flake8 (toolkits + src)
lint:
	@echo "$(BLUE)▶ Linting Python files...$(NC)"
	flake8 toolkits/ src/ \
	  --max-line-length=100 \
	  --extend-ignore=E501,W503 \
	  --count
	@echo "$(GREEN)✓ Lint passed$(NC)"

# ============================================================================
# Governance
# ============================================================================

## register-governance: Register AI Factsheets and monitors (alias for governance)
register-governance: governance

## governance: Verify watsonx Governance connectivity (monitors attached via UI)
governance:
	@echo "$(BLUE)▶ Verifying watsonx Governance connectivity...$(NC)"
	@if [ -z "$$GOVERNANCE_INSTANCE_GUID" ]; then \
	  echo "$(YELLOW)⚠ GOVERNANCE_INSTANCE_GUID not set.$(NC)"; \
	  echo "  IBM Cloud Resource list → AI/Machine Learning → <instance> → GUID"; \
	  echo "  export GOVERNANCE_INSTANCE_GUID=<guid>"; \
	  exit 1; \
	fi
	python governance/register_factsheets.py
	@echo "$(GREEN)✓ Governance connection verified$(NC)"

# ============================================================================
# Help
# ============================================================================

## help: Show available targets
help:
	@echo ""
	@echo "Mission Veteran AI by G3 — available make targets:"
	@echo ""
	@echo "$(BLUE)Orchestrate agents:$(NC)"
	@grep -E '^## (deploy|promote|provision|destroy):' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
	@echo "$(BLUE)Bridge server (src/server.py → IBM Code Engine):$(NC)"
	@grep -E '^## bridge-' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
	@echo "$(BLUE)GitHub Pages:$(NC)"
	@grep -E '^## pages-' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
	@echo "$(BLUE)Setup + utilities:$(NC)"
	@grep -E '^## (all|setup|install|test|test-unit|lint|governance|register-governance):' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
	@echo "$(BLUE)Configuration (override on command line):$(NC)"
	@echo "  ICR_NAMESPACE=$(ICR_NAMESPACE)   ICR_REGION=$(ICR_REGION)"
	@echo "  CE_REGION=$(CE_REGION)   CE_PROJECT=$(CE_PROJECT)   CE_APP=$(CE_APP)"
	@echo "  IMAGE=$(IMAGE)"
	@echo ""
