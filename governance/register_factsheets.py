#!/usr/bin/env python3
# governance/register_factsheets.py
# Mission Veteran AI by Golden Gate Glory — watsonx Governance
#
# Registers all AI use cases and their monitor subscriptions from
# governance/factsheets.yaml and governance/monitors.yaml into the
# IBM watsonx Governance service.
#
# Run ONCE per environment (draft / live) before deploying agents:
#
#   # 1. Activate the virtual environment
#   source venv/bin/activate
#
#   # 2. Set environment variables (or load from .env)
#   export GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>
#   export GOVERNANCE_INSTANCE_GUID=<your-openscale-instance-guid>
#   export WATSONX_PROJECT_ID=<your-watsonx-project-id>
#
#   # 3. Run registration
#   python governance/register_factsheets.py
#
# After registration the script prints the subscription_id for each use case.
# Copy these values into your .env file as:
#   GOVERNANCE_SUB_BULLET_TRANSLATOR=<id>
#   GOVERNANCE_SUB_SKILL_MAPPER=<id>
#   GOVERNANCE_SUB_GAP_ANALYZER=<id>
#   GOVERNANCE_SUB_PLAN_BUILDER=<id>
#
# Prerequisites:
#   pip install ibm-aigov-facts-client pyyaml

import os
import sys
import yaml

try:
    from ibm_aigov_facts_client import AIGovFactsClient
except ImportError:
    sys.exit(
        "ERROR: ibm-aigov-facts-client is not installed.\n"
        "Run: pip install ibm-aigov-facts-client"
    )

# ---------------------------------------------------------------------------
# Load spec files
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(_HERE, "factsheets.yaml"), "r") as f:
    factsheets_spec = yaml.safe_load(f)

with open(os.path.join(_HERE, "monitors.yaml"), "r") as f:
    monitors_spec = yaml.safe_load(f)

# Build a quick lookup: monitor_id → monitor config
monitors_by_id = {m["monitor_id"]: m for m in monitors_spec["monitors"]}

# ---------------------------------------------------------------------------
# Connect to Governance
# ---------------------------------------------------------------------------

api_key = os.environ.get(
    "GOVERNANCE_API_KEY",
    os.environ.get("WATSONX_API_KEY", ""),
)
instance_guid = os.environ.get("GOVERNANCE_INSTANCE_GUID", "")
url = os.environ.get("GOVERNANCE_URL", "https://aiopenscale.cloud.ibm.com")

if not api_key or not instance_guid:
    sys.exit(
        "ERROR: GOVERNANCE_API_KEY (or WATSONX_API_KEY) and "
        "GOVERNANCE_INSTANCE_GUID must be set."
    )

print(f"Connecting to watsonx Governance at {url} …")
client = AIGovFactsClient(
    api_key=api_key,
    instance_guid=instance_guid,
    service_url=url,
)
print("Connected.\n")

# ---------------------------------------------------------------------------
# Register each use case
# ---------------------------------------------------------------------------

subscription_ids = {}

for uc in factsheets_spec["factsheets"]:
    use_case_id = uc["use_case_id"]
    print(f"Registering use case: {uc['name']} ({use_case_id})")

    # 1. Create or update the AI use case / model entry
    try:
        use_case = client.create_use_case(
            name=uc["name"],
            description=uc["description"],
            use_case_id=use_case_id,
            task_type=uc["task_type"],
            tags=uc.get("tags", []),
            metadata={
                "model_id": uc["model_id"],
                "model_provider": uc["model_provider"],
                "toolkit": uc["toolkit"],
                "data_sensitivity": uc["data_sensitivity"],
                "risk_tier": uc["risk_tier"],
                "intended_use": uc["intended_use"],
                "out_of_scope_uses": uc["out_of_scope_uses"],
                "human_oversight_required": uc["human_oversight_required"],
                "human_oversight_note": uc.get("human_oversight_note", ""),
            },
        )
        print(f"  ✓ Use case created/updated: {use_case.get('id', use_case_id)}")
    except Exception as exc:
        print(f"  ✗ Use case registration failed: {exc}")
        continue

    # 2. Create monitor subscriptions for this use case
    sub_id = None
    for monitor_id in uc.get("monitors", []):
        monitor_cfg = monitors_by_id.get(monitor_id)
        if not monitor_cfg:
            print(f"  ⚠ Monitor '{monitor_id}' not found in monitors.yaml — skipping.")
            continue

        # Only attach the monitor if it applies to this use case
        if use_case_id not in monitor_cfg.get("applies_to", []):
            continue

        try:
            subscription = client.subscriptions.create(
                use_case_id=use_case_id,
                monitor_type=monitor_cfg["monitor_type"],
                configuration=monitor_cfg,
            )
            sub_id = subscription.get("subscription_id") or subscription.get("id")
            print(f"  ✓ Monitor '{monitor_id}' subscribed: {sub_id}")
        except Exception as exc:
            print(f"  ✗ Monitor '{monitor_id}' subscription failed: {exc}")

    if sub_id:
        subscription_ids[use_case_id] = sub_id

# ---------------------------------------------------------------------------
# Print summary of subscription IDs for .env configuration
# ---------------------------------------------------------------------------

env_var_map = {
    "mvai-bullet-translator": "GOVERNANCE_SUB_BULLET_TRANSLATOR",
    "mvai-skill-mapper":      "GOVERNANCE_SUB_SKILL_MAPPER",
    "mvai-gap-analyzer":      "GOVERNANCE_SUB_GAP_ANALYZER",
    "mvai-plan-builder":      "GOVERNANCE_SUB_PLAN_BUILDER",
}

print("\n" + "=" * 60)
print("Registration complete. Add these to your .env file:\n")
for uc_id, env_var in env_var_map.items():
    sub_id = subscription_ids.get(uc_id, "<not-registered>")
    print(f"  {env_var}={sub_id}")
print("=" * 60)
