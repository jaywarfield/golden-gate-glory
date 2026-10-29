#!/usr/bin/env python3
# governance/register_factsheets.py
# Mission Veteran AI by Golden Gate Glory — watsonx Governance
#
# Connects to the Watson OpenScale / watsonx.governance service instance and
# prints available data marts and service providers to confirm connectivity.
#
# Full monitor subscriptions (bias, drift, content safety, explainability)
# must be attached via the watsonx.governance UI after this script confirms
# the connection works. The ibm-watson-openscale SDK's subscriptions.add()
# requires a deployed WML model asset — Granite text-generation tools are
# not deployed WML models and cannot be subscribed programmatically.
#
# Run ONCE after provisioning to verify connectivity:
#
#   source venv/bin/activate
#   export GOVERNANCE_INSTANCE_GUID=<guid-from-resource-list>
#   export GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>
#   python governance/register_factsheets.py
#
# Find the GUID:
#   IBM Cloud Resource list → AI / Machine Learning →
#   <your watsonx Governance instance> → right panel shows GUID
#
# Optional:
#   export GOVERNANCE_URL=https://aiopenscale.cloud.ibm.com   # default (Dallas)
#
# Prerequisites:
#   python -m pip install ibm-watson-openscale pyyaml

import os
import sys

try:
    from ibm_watson_openscale import APIClient
    from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
except ImportError:
    sys.exit(
        "ERROR: ibm-watson-openscale is not installed.\n"
        "Run: python -m pip install ibm-watson-openscale"
    )

# ---------------------------------------------------------------------------
# Connect
# ---------------------------------------------------------------------------

api_key       = os.environ.get("GOVERNANCE_API_KEY", os.environ.get("WATSONX_API_KEY", ""))
instance_guid = os.environ.get("GOVERNANCE_INSTANCE_GUID", "")
url           = os.environ.get("GOVERNANCE_URL", "https://aiopenscale.cloud.ibm.com")

if not api_key:
    sys.exit(
        "ERROR: GOVERNANCE_API_KEY (or WATSONX_API_KEY) must be set.\n"
        "export GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>"
    )
if not instance_guid:
    sys.exit(
        "ERROR: GOVERNANCE_INSTANCE_GUID must be set.\n"
        "IBM Cloud Resource list → AI/Machine Learning → <your governance instance> → GUID\n"
        "export GOVERNANCE_INSTANCE_GUID=<guid>"
    )

print(f"Connecting to watsonx Governance at {url} …")
authenticator = IAMAuthenticator(apikey=api_key)
client = APIClient(
    authenticator=authenticator,
    service_url=url,
    service_instance_id=instance_guid,
)
print("Connected.\n")

# ---------------------------------------------------------------------------
# List data marts — confirms the instance is reachable
# ---------------------------------------------------------------------------

print("Data marts in this instance:")
try:
    data_marts = client.data_marts.list().get_result()
    for dm in data_marts.get("data_marts", []):
        dm_id   = dm.get("metadata", {}).get("id", "?")
        dm_name = dm.get("entity", {}).get("name", "?")
        print(f"  {dm_name}  ({dm_id})")
    if not data_marts.get("data_marts"):
        print("  (none — instance may need to be initialised in the UI first)")
except Exception as exc:
    print(f"  Could not list data marts: {exc}")

# ---------------------------------------------------------------------------
# List service providers — shows any already-connected WML instances
# ---------------------------------------------------------------------------

print("\nService providers (connected WML instances):")
try:
    providers = client.service_providers.list().get_result()
    for sp in providers.get("service_providers", []):
        sp_id   = sp.get("metadata", {}).get("id", "?")
        sp_name = sp.get("entity", {}).get("name", "?")
        print(f"  {sp_name}  ({sp_id})")
    if not providers.get("service_providers"):
        print("  (none)")
except Exception as exc:
    print(f"  Could not list service providers: {exc}")

# ---------------------------------------------------------------------------
# Next steps
# ---------------------------------------------------------------------------

print("\n" + "=" * 60)
print("Connection verified.\n")
print("Next steps — attach monitors via the watsonx.governance UI:")
print("  1. Open your governance instance in IBM Cloud")
print("  2. Navigate to AI use cases")
print("  3. Create use cases for:")
print("     - Mission Veteran AI — Bullet Translator")
print("     - Mission Veteran AI — Skill Mapper")
print("     - Mission Veteran AI — Gap Analyzer")
print("     - Mission Veteran AI — Plan Builder")
print("  4. Attach monitors (bias, drift, content safety, explainability)")
print("     via the Evaluations tab on each use case.")
print("=" * 60)
