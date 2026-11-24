# **Mission Veteran AI** *by G3*

#### Orchestrate Webchat

##### What Ochestrate Webchat is

Option A is the primary, native deployment surface — the watsonx Orchestrate webchat interface that is exposed automatically when the five agent YAML files are imported into an Orchestrate instance. No server to run, no container to build, no front-end to serve. The Coordinator Agent and its four collaborator sub-agents run entirely within watsonx Orchestrate's managed runtime, and the webchat UI is the conversation surface that the platform provides out of the box.

It is listed first among the six deployment options for a reason: it is the most architecturally complete expression of the solution. Options B through F all exist to run src/server.py with API credentials in the environment. Option A is the solution running as it was designed — as a multi-agent pipeline on watsonx Orchestrate.

##### The agent architecture inside Orchestrate

Five YAML files define the entire agent stack:

| File  | Agent name | Role  |
| :---: | :---:      | :---: |
| coordinator_agent.yaml | coordinator | Orchestrates the pipeline; holds the PII boundary rules; manages the export gate |
| accomplishment_translator_agent.yaml | accomplishment_translator | Single-purpose: military bullet → ATS civilian bullet |
| skill_mapper_agent.yaml | skill_mapper | Single-purpose: MOS/AFSC/rating + service summary → civilian skill inventory |
| gap_analyzer_agent.yaml | gap_analyzer | Single-purpose: skill inventory × job description → gap report + SkillsBuild courses |
| plan_builder_agent.yaml | plan_builder | Single-purpose: JD analysis → tagged résumé draft → export gate evaluation |

All five use style: react_core (the most capable Orchestrate reasoning style) and llm: ibm/granite-4-h-small. The Coordinator has four collaborators: entries pointing to the sub-agents by name — Orchestrate routes delegation calls through that graph automatically.

Each sub-agent has a single-line instructions: scope boundary: "YOUR ONLY JOB: …" This is a deliberate design that prevents drift. A sub-agent asked to do something outside its role will refuse and redirect, because its instructions contain only one workflow with explicit BOUNDARIES.

##### What the Coordinator's instructions do

The coordinator_agent.yaml instructions: block is a 167-line behavioural specification that covers six distinct areas:

1. Step 1 — Welcome and pipeline disclosure. The Coordinator opens by telling the veteran exactly what will happen across all five steps, naming each sub-agent. No black box.

2. Step 2 — PII collection boundary. Before collecting any input, the Coordinator displays a mandatory PII reminder verbatim:

"All inputs must be PII-free — no full names, Social Security numbers, DoD ID numbers, phone numbers, email addresses, home addresses, birth dates, medical details, classified information, exact unit identifiers, or exact deployment locations."

This runs at the Orchestrate layer — before any toolkit function is called, before any watsonx.ai inference is made.

3. Steps 3–6 — Delegation sequence. Each delegation step names the sub-agent, the exact parameters to pass, and what to do if the sub-agent returns a pii_warning or error. The gate handling in Step 6 is explicit: if gate_status == "BLOCKED", the Coordinator relays all holds and guides the veteran through resolution — it cannot allow export to proceed.

4. Classified information detection. A hard boundary: if any input may contain sensitive operational details, the Coordinator refuses processing and says so with a specific, verbatim message.

5. BOUNDARIES block. Eight explicit prohibitions, including: do not invent facts, do not predict hiring outcomes, do not provide legal/medical/financial advice, do not allow export when gate is BLOCKED.

6. DRAFT disclaimer. Every output carries: "DRAFT – Review before use. Confirm every claim against your service record before submitting to an employer." This is mandated in the instructions — the Coordinator appends it even if the toolkit functions do not.

##### The deploy and promote lifecycle

deploy.sh manages the full import and promote sequence:

```
  ./deploy.sh           # import everything to Draft only
  ./deploy.sh --live    # import to Draft, then promote all to Live
  ./deploy.sh --live-only  # promote already-imported Draft snapshot to Live
```

The script's four import steps run in dependency order:

1. Tools — four Python toolkit files imported with --package-root toolkits --app-id watsonx_credentials. The watsonx_credentials connection (defined in connections/watsonx_credentials.yaml) is a key_value / team type connection that holds WATSONX_API_KEY, WATSONX_URL, and WATSONX_PROJECT_ID for both Draft and Live environments. The toolkit functions read these at inference time — no credentials are baked into the agent YAMLs.

2. Sub-agents — four sub-agent YAMLs imported in any order (they have no cross-dependency).

3. Coordinator — imported last, after all collaborators exist. If imported first, Orchestrate cannot resolve the collaborators: references.

4. Governance — optional; runs governance/register_factsheets.py if GOVERNANCE_INSTANCE_GUID is set.

##### Why Option A is the most important deployment option

1. It is the native expression of the multi-agent architecture. Options B–F run server.py, which implements the pipeline as Python function calls. Option A runs the same pipeline as it was designed — five collaborating agents inside watsonx Orchestrate, with Granite coordinating the reasoning at each delegation step. The agent instructions, boundaries, and PII guards all run as intended.

2. The webchat interface is zero-friction for a veteran. No app to install, no browser extension, no account creation beyond the IBM platform. A veteran who is handed the Orchestrate dashboard_url opens a browser and starts typing. The PII reminder panel appears before any input is collected. This is the interaction model that works for someone in a career transition who is not technical.

3. Session-scoped, no data persistence. The architecture diagram calls this out explicitly: "session-scoped, no data persistence." Veteran career data — service summaries, accomplishment bullets, skill inventories — exists only for the duration of the conversation. Nothing is logged to a database, nothing persists across sessions. For a tool handling sensitive career information, this is the correct data handling posture.

4. The PII boundary runs at the agent layer, not just the application layer. Options B–F enforce PII detection in the Python toolkit functions via contains_pii(). Option A enforces it additionally at the Coordinator's instruction level, before any tool call is dispatched. Two independent enforcement layers — the agent refuses to proceed if the input looks problematic, and even if it did proceed, the toolkit would catch it.

5. make deploy is the entire deployment command. A new team member who has the Orchestrate CLI authenticated and their .env populated runs one command to have a fully operational five-agent pipeline in the Orchestrate Draft environment. No Docker, no Kubernetes, no IBM Cloud CLI plugins for Code Engine. The deployment complexity is equivalent to a git push.

6. The Draft / Live separation enables safe iteration. The two-environment model — Draft for development, Live for testing — means the team can iterate on agent instructions, update toolkit functions, and re-import to Draft without touching the Live environment that testers are using. make promote / ./deploy.sh --live-only advances the confirmed Draft snapshot to Live only when the team is ready. This is production-grade deployment discipline applied to an agent pipeline.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
