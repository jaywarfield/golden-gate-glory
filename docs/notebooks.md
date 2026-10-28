# **Mission Veteran AI – IBM AI Lab Challenge**

#### Notebooks

Jupyter Notebooks in the broader IBM watsonx ecosystem (watsonx.ai Studio and watsonx.ai Runtime) enable an exploratory engineering purpose compared to autonomous agents and @tool-decorated Python scripts running inside watsonx Orchestrate:

- Interactive Data Exploration and Prototyping by running small blocks of code interactively, inspect intermediate dataframes, and view visualizations, charts, or mathematical outputs immediately in the browser.
- Machine Learning Lifecycle Workflows designed for data scientists to assemble, train, evaluate, and tune machine learning models (using scikit-learn, PySpark, XGBoost, etc.) and save artifacts directly to model runtimes.
- Rich Narrative and Documentation that combine live executable code with Markdown text, equations, and media to explain methodology and share insights with teams.
- Loose, Ad-Hoc Execution that is great for research, trial-and-error experimentation, and data wrangling before any logic is productionized.

| Notebook | Web UI step | Toolkit function | What it does |
| :---:    | :---:       | :---:            | :---:        | 
| NB 01 | 01_bullet_translation | Step 2 — Military Bullet Translation | translate_bullet | Translates raw military accomplishment bullets into ATS-ready civilian resume bullets |
| NB 02 | 02_skill_knowledge_base | Step 4 — Skill Mapping (first half) |  map_military_skills + analyze_skills_gap | Maps MOS/AFSC/rating to civilian skill inventory via O*NET crosswalk, then identifies gaps and recommends IBM SkillsBuild courses |
| NB 03 | 03_job_analyzer | Step 3 — Job Description Analysis | analyze_job_description | Extracts required skills, preferred skills, ATS keywords, seniority, and industry from a pasted job description |
| NB 04 | 04_resume_builder |  Step 5 — Tagged Resume Draft (first pass) | build_resume_draft (raw prompt path) | Builds the evidence-tagged resume draft; tests the raw Granite prompt directly against prompt_templates.json PT-002 |
| NB 05 | 05_materials_builder | Step 5 — Tagged Resume Draft + Cover Letter | build_resume_draft + cover letter (PT-005) | Extends NB 04 to also produce a tagged cover letter draft; both go through the grounding check |
| NB 06 | 06_gate_controller | Step 7 — Export Gate    evaluate_export_gate | Tests the gate logic with a simulated draft; generates plain-English hold explanations via PT-004; simulates hold resolution |
| NB 07 | 07_career_pipeline | All 7 steps end-to-end  All toolkit functions |  Runs the complete pipeline in sequence — imports and calls all toolkit functions directly, no raw prompt path |

Notes:

1. Step 1 (Veteran Profile) has no notebook — it's pure form input (branch, specialty code, service summary, target role). No LLM call, nothing to test in isolation.

2. Step 6 (Interview Prep) has no notebook — NB 07 marks it explicitly as # toolkit not yet implemented and stubs it with an empty result. The web UI has a Step 6 panel but it also calls a mock. This is the one pipeline step with no corresponding test notebook.

3. NB 03 and NB 04 are ordered opposite to the web UI — the web UI runs job analysis (Step 3) before skill mapping (Step 4), but NB 02 covers skill mapping and NB 03 covers job analysis. The numbering followed the order the notebooks were originally authored, not the final user flow order.

4. NB 04 vs NB 05 — both cover Step 5, but at different levels. NB 04 is a focused unit test of build_resume_draft via the raw prompt path. NB 05 is the integration test that produces both the resume and cover letter and runs the full gate evaluation against both. In practice you run NB 04 first to verify the resume draft in isolation, then NB 05 to verify the full materials package.

5. NB 07 is the authoritative end-to-end test — it imports the real toolkit functions and runs them in the correct web UI order (Steps 1→7), making it the single notebook that validates the whole pipeline works together.

Agents and Tools (watsonx Orchestrate):

- Autonomous Task Execution with Agents that use LLMs, reasoning loops (like ReAct or default modes), and multi-agent coordination to dynamically decide when and how to invoke capabilities based on user prompts.
- Isolated, Reusable Python Tools with code that is wrapped using the @tool decorator, placed in standalone containers or toolkits, and exposed to the Orchestrate tool catalog for enterprise automation.
- Enterprise Governance & Guardrails with built-in credential handling, token tracking, role-based tool permissions, human-in-the-loop approval steps, and OpenTelemetry observability.
- Production Integration that directly connects business applications (e.g., Salesforce, Workday, Slack, custom APIs) so end-users can trigger live workflows via a conversational chat interface or agentic handoffs.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

