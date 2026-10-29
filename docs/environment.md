# **Mission Veteran AI** *by G3*

![Environment](images/environment.png)

<!--
<a href="environment.png" target="_blank">
   <img src="images/environment.png"
        alt="Mission Veteran AI Environment Architecture"
        style="width:100%; height:auto;">
</a>
-->

#### Environments

watsonx Orchestrate has two environments inside a single instance:

| Environment | Purpose | Who uses it |
| :---:       | :---:   | :---:       |
| Draft | Development — safe to iterate | Developer |
| Live | Test / tester-facing — immutable until promoted | Tester |

They are completely independent. Importing to Draft never touches Live, and promoting to Live never re-imports — it snapshots Draft as-is.

#### Import to Draft only (development)

```
make deploy
# or directly:
./deploy.sh
```

- Imports all tools, agents → Draft
- Runs governance registration (if GOVERNANCE_INSTANCE_GUID is set)
- Live is not touched

#### Import to Live only (test) — without re-importing to Draft

```
make promote
# or directly:
./deploy.sh --live-only
```

- Promotes the current Draft snapshot → Live
- Skips all tool/agent import steps entirely
- Draft is not touched

#### Governance — Draft vs Live

Governance (watsonx Governance / AI Factsheets) is not environment-scoped in the same way — it tracks inference facts at the tool level regardless of which Orchestrate environment called the tool. Registration is a one-time step per instance:

```
# Set the GUID first (from terraform output or IBM Cloud console)
export GOVERNANCE_INSTANCE_GUID=$(cd terraform && terraform output -raw governance_instance_guid)

# Then register
make governance
# or:
make register-governance   # same thing — it's an alias
```

This registers the AI use cases and monitor subscriptions once. After that, governance logging is automatic at inference time — every tool call logs facts regardless of whether it was called from Draft or Live. No separate governance import is needed per environment.

#### Typical workflow

```
# First time or after code changes:
make deploy          ← import to Draft, test in Draft UI

# When Draft looks good:
make promote         ← snapshot Draft → Live, notify tester

# If you need to update both at once:
make deploy-live     ← import + promote in one step

# Governance (once after provisioning, or after model/KB updates):
export GOVERNANCE_INSTANCE_GUID=<guid>
make governance
```

#### Requirements before running make deploy

1. Python virtual environment & packages

```
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Orchestrate CLI — installed and authenticated

```
pip install ibm-watsonx-orchestrate
orchestrate env add --name <your-env> --url <your-orchestrate-url>
orchestrate env activate <your-env>   # prompts for API key
```
 
3. Orchestrate connection — watsonx_credentials

The tools need a connection named watsonx_credentials in both Draft and Live with the three watsonx secrets. Create it once:

```
orchestrate connections import -f connections/watsonx_credentials.yaml
```

Then set the secret values in the Orchestrate UI (or CLI) for both Draft and Live:

| Key   | Value |
| :---: | :---: |
|WATSONX_API_KEY | Your IBM Cloud API key |
|WATSONX_URL | https://us-south.ml.cloud.ibm.com |
|WATSONX_PROJECT_ID | Your watsonx.ai project ID |

4. Environment variables — required at make deploy time

These must be set in your shell before running make (or in a .env file loaded by your shell):

Watsonx.ai (required — used by tools at inference time)

```
export WATSONX_API_KEY=<your-ibm-cloud-api-key>
export WATSONX_PROJECT_ID=<your-watsonx-project-id>
export WATSONX_URL=https://us-south.ml.cloud.ibm.com   # optional, this is the default
```

Governance (required only for make governance / Step 4 of deploy)

```
export GOVERNANCE_INSTANCE_GUID=<your-openscale-instance-guid>
export GOVERNANCE_API_KEY=<your-ibm-cloud-api-key>      # defaults to WATSONX_API_KEY if omitted
export GOVERNANCE_URL=https://aiopenscale.cloud.ibm.com  # optional, this is the default
export GOVERNANCE_ENABLED=true                            # optional, true by default
```

After running make governance for the first time, it prints four subscription IDs. Add them to your environment:

```
export GOVERNANCE_SUB_BULLET_TRANSLATOR=<id-from-script>
export GOVERNANCE_SUB_SKILL_MAPPER=<id-from-script>
export GOVERNANCE_SUB_GAP_ANALYZER=<id-from-script>
export GOVERNANCE_SUB_PLAN_BUILDER=<id-from-script>
```

5. Complete setup order (first time)

    a. Clone repo and install packages

    ```
    python3 -m venv venv && source venv/bin/activate
    pip install -r requirements.txt
    ```

    b. Authenticate Orchestrate CLI

    ``` 
    orchestrate env add --name my-env --url <url>
    orchestrate env activate my-env
    ```

-  Create the watsonx connection (set secrets in UI after this)

```
orchestrate connections import -f connections/watsonx_credentials.yaml
```

- Set environment variables

```
export WATSONX_API_KEY=...
export WATSONX_PROJECT_ID=...
export GOVERNANCE_INSTANCE_GUID=...
```

- Import everything to Draft

```
make deploy
```

- When Draft is verified, promote to Live

```
make promote
```

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

