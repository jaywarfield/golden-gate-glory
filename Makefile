# Makefile
# Mission Veteran AI — a Golden Gate Glory project
#
# Sequences Terraform (instance provisioning) and deploy.sh (agent deployment).
#
# ── First-time setup ────────────────────────────────────────────────────────
#   cp terraform/terraform.tfvars.example terraform/terraform.tfvars
#   # edit terraform/terraform.tfvars with your IBM Cloud credentials
#   make all
#
# ── Day-to-day development ──────────────────────────────────────────────────
#   make deploy       # re-import toolkits + agents to Draft after code changes
#   make promote      # promote current Draft snapshot to Live (notify tester)
#   make deploy-live  # import + promote in one step
#
# ── Teardown ────────────────────────────────────────────────────────────────
#   make destroy      # destroy the Orchestrate instance (removes all agents)

.PHONY: all provision init plan deploy deploy-live promote destroy \
        test test-unit lint register-governance help

TERRAFORM_DIR := terraform
DEPLOY_SCRIPT := ./deploy.sh

# ── Colours ─────────────────────────────────────────────────────────────────
BLUE  := \033[0;34m
GREEN := \033[0;32m
YELLOW:= \033[1;33m
NC    := \033[0m

## all: Provision instance (Terraform) + import toolkits/agents to Draft
all: provision deploy

## init: Initialise Terraform (download providers and modules)
init:
	@echo "$(BLUE)▶ Initialising Terraform...$(NC)"
	cd $(TERRAFORM_DIR) && terraform init
	@echo "$(GREEN)✓ Terraform initialised$(NC)"

## plan: Preview infrastructure changes without applying
plan: init
	@echo "$(BLUE)▶ Planning Terraform changes...$(NC)"
	cd $(TERRAFORM_DIR) && terraform plan

## provision: Create or update the Orchestrate service instance
provision: init
	@echo "$(BLUE)▶ Provisioning Orchestrate instance...$(NC)"
	cd $(TERRAFORM_DIR) && terraform apply -auto-approve
	@echo "$(GREEN)✓ Instance provisioned$(NC)"
	@echo ""
	@cd $(TERRAFORM_DIR) && terraform output

## deploy: Import toolkits + agents to Draft (safe — does not touch Live)
deploy:
	@echo "$(BLUE)▶ Importing toolkits and agents to Draft...$(NC)"
	$(DEPLOY_SCRIPT)

## deploy-live: Import to Draft AND immediately promote to Live
deploy-live:
	@echo "$(YELLOW)⚠ This will update the Live (test) environment.$(NC)"
	$(DEPLOY_SCRIPT) --live

## promote: Promote current Draft snapshot to Live (skip re-import)
promote:
	@echo "$(YELLOW)⚠ Promoting Draft to Live — notify tester after this completes.$(NC)"
	$(DEPLOY_SCRIPT) --live-only

## destroy: Destroy the Orchestrate service instance (removes all agents)
destroy:
	@echo "$(YELLOW)⚠ WARNING: This will destroy the Orchestrate instance and all agents inside it.$(NC)"
	@read -p "Type 'yes' to confirm: " CONFIRM && [ "$$CONFIRM" = "yes" ] || (echo "Aborted." && exit 1)
	cd $(TERRAFORM_DIR) && terraform destroy -auto-approve
	@echo "$(GREEN)✓ Instance destroyed$(NC)"

## test: Run the full unit test suite
test: test-unit

## test-unit: Run unit tests (no live API calls — mocked)
test-unit:
	@echo "$(BLUE)▶ Running unit tests...$(NC)"
	pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

## lint: Check Python toolkit files with flake8 (E/W errors only, max line 100)
lint:
	@echo "$(BLUE)▶ Linting toolkit Python files...$(NC)"
	flake8 toolkits/ --max-line-length=100 --extend-ignore=E501,W503 --count
	@echo "$(GREEN)✓ Lint passed$(NC)"

## register-governance: Register AI Factsheets and monitors (run once after terraform apply)
register-governance:
	@echo "$(BLUE)▶ Registering AI Factsheets and monitors with watsonx Governance...$(NC)"
	@if [ -z "$$GOVERNANCE_INSTANCE_GUID" ]; then \
	  echo "$(YELLOW)⚠ GOVERNANCE_INSTANCE_GUID not set. Run: terraform output governance_instance_guid$(NC)"; \
	  exit 1; \
	fi
	python governance/register_factsheets.py
	@echo "$(GREEN)✓ Governance registration complete$(NC)"

## help: Show available targets
help:
	@echo ""
	@echo "Mission Veteran AI — available make targets:"
	@echo ""
	@grep -E '^## ' Makefile | sed 's/## /  make /' | column -t -s ':'
	@echo ""
