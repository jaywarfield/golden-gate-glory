# Makefile
# Mission Veteran AI by G3
#
# Imports tools, agents, and governance into watsonx Orchestrate.
#
# ── First-time setup ────────────────────────────────────────────────────────
#   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
#   # edit terraform/terraform.tfvars with your IBM Cloud credentials
#   # provision IBM Cloud instances manually or via Terraform, then:
#   make deploy
#
# ── Day-to-day development ──────────────────────────────────────────────────
#   make deploy       # re-import tools + agents + governance to Draft
#   make promote      # promote current Draft snapshot to Live (notify tester)
#   make deploy-live  # import + promote in one step
#
# ── Teardown ────────────────────────────────────────────────────────────────
#   make destroy      # remove all agents from the Orchestrate instance

.PHONY: all deploy deploy-live promote destroy \
        test test-unit lint register-governance governance help

DEPLOY_SCRIPT := ./deploy.sh

# ── Colours ─────────────────────────────────────────────────────────────────
BLUE  := \033[0;34m
GREEN := \033[0;32m
YELLOW:= \033[1;33m
NC    := \033[0m

## all: Import tools + agents + governance to Draft
all: deploy

## deploy: Import tools + agents + governance to Draft (safe — does not touch Live)
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

## destroy: Remove all agents from the Orchestrate instance
destroy:
	@echo "$(YELLOW)⚠ WARNING: This will remove all agents from the Orchestrate instance.$(NC)"
	@read -p "Type 'yes' to confirm: " CONFIRM && [ "$$CONFIRM" = "yes" ] || (echo "Aborted." && exit 1)
	orchestrate agents remove --name coordinator   --kind native
	orchestrate agents remove --name plan_builder  --kind native
	orchestrate agents remove --name gap_analyzer  --kind native
	orchestrate agents remove --name skill_mapper  --kind native
	orchestrate agents remove --name bullet_translator --kind native
	@echo "$(GREEN)✓ Agents removed$(NC)"

## test: Run the full unit test suite
test: test-unit

## test-unit: Run unit tests (no live API calls — mocked)
test-unit:
	@echo "$(BLUE)▶ Running unit tests...$(NC)"
	pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

## lint: Check Python tool files with flake8 (E/W errors only, max line 100)
lint:
	@echo "$(BLUE)▶ Linting Python tool files...$(NC)"
	flake8 toolkits/ --max-line-length=100 --extend-ignore=E501,W503 --count
	@echo "$(GREEN)✓ Lint passed$(NC)"

## register-governance: Register AI Factsheets and monitors (alias for governance)
register-governance: governance

## governance: Register AI Factsheets and monitors with watsonx Governance
governance:
	@echo "$(BLUE)▶ Registering AI Factsheets and monitors with watsonx Governance...$(NC)"
	@if [ -z "$$GOVERNANCE_INSTANCE_GUID" ]; then \
	  echo "$(YELLOW)⚠ GOVERNANCE_INSTANCE_GUID not set. Run:$(NC)"; \
	  echo "  export GOVERNANCE_INSTANCE_GUID=\$$(cd terraform && terraform output -raw governance_instance_guid)"; \
	  exit 1; \
	fi
	python governance/register_factsheets.py
	@echo "$(GREEN)✓ Governance registration complete$(NC)"

## help: Show available targets
help:
	@echo ""
	@echo "Mission Veteran AI by G3 — available make targets:"
	@echo ""
	@grep -E '^## ' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
