# **Mission Veteran AI** *by G3*

#### Orchestrate 

##### Agents and Tools

Agents and @tool-decorated Python scripts in watsonx Orchestrate enable production integration with autonomous tasks and governance:

- Autonomous Task Execution with Agents that use LLMs, reasoning loops (like ReAct or default modes), and multi-agent coordination to dynamically decide when and how to invoke capabilities based on user prompts.
- Isolated, Reusable Python Tools with code that is wrapped using the @tool decorator, placed in standalone containers or toolkits, and exposed to the Orchestrate tool catalog for enterprise automation.
- Enterprise Governance & Guardrails with built-in credential handling, token tracking, role-based tool permissions, human-in-the-loop approval steps, and OpenTelemetry observability.
- Production Integration that directly connects business applications (e.g., Salesforce, Workday, Slack, custom APIs) so end-users can trigger live workflows via a conversational chat interface or agentic handoffs.

##### Agent Descriptions

Agent LLM (`llm:` in YAML) is `groq/openai/gpt-oss-120b` — used for agent reasoning via Orchestrate.
Toolkit inference (`_MODEL_ID` in Python) is `ibm/granite-4-h-small` — called directly via watsonx.ai `ModelInference`.

| Agent | Kind  | LLM (agent reasoning)   | Style | Role  |
| :---: | :---: | :---: | :---: | :---: |
| coordinator | native | groq/openai/gpt-oss-120b | react_core | Orchestrates the full pipeline; collects veteran profile, delegates to all four sub-agents in sequence, enforces the export gate. |
| accomplishment_translator | native | groq/openai/gpt-oss-120b | react_core | Translates one PII-free military bullet into an ATS-ready civilian resume bullet. |
| skill_mapper | native | groq/openai/gpt-oss-120b | react_core | Maps MOS/AFSC/rating + service summary to a categorised civilian skill inventory. |
| gap_analyzer | native | groq/openai/gpt-oss-120b | react_core | Compares skill inventory to a job description; produces coverage %, gap skills, and IBM SkillsBuild course recommendations. |
| plan_builder | native | groq/openai/gpt-oss-120b | react_core | Runs the 3-step gated resume pipeline: JD analysis → tagged draft → export gate. |

##### Tool Descriptions (per agent)

| Agent | Tool  | What it does |
| :---: | :---: | :---:        |
| accomplishment_translator | translate_accomplishment | Calls `ibm/granite-4-h-small` (watsonx.ai) with a PII-free military bullet; returns one civilian ATS bullet with DRAFT disclaimer |
| skill_mapper | map_military_skills | Looks up O*NET crosswalk for the specialty code, loads O*NET occupation skills for the career path, then calls `ibm/granite-4-h-small` (watsonx.ai) to produce a skill list with evidence quotes |
| gap_analyzer | analyze_skills_gap | Calls `ibm/granite-4-h-small` (watsonx.ai) to diff skill inventory vs JD; looks up matching IBM SkillsBuild courses and DoD SkillBridge programs from local KBs |
| plan_builder | analyze_job_description | Extracts required skills, preferred skills, ATS keywords, role level, and industry from a job posting |
| plan_builder | build_resume_draft | Builds a tagged resume draft (EVIDENCED / INFERRED / MISSING); runs an automated grounding check on all EVIDENCED items and downgrades any that can't be confirmed |
| plan_builder | evaluate_export_gate | Returns OPEN or BLOCKED based on unresolved INFERRED/MISSING counts and grounding downgrade count; export is blocked until all holds are resolved |

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

