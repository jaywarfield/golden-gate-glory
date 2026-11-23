# **Mission Veteran AI** *by G3*

#### Technology Used

IBM products used: 
- IBM Granite 4 (ibm/granite-4-h-small via watsonx.ai) as the primary LLM for all five inference steps, with Groq as a fallback.
- watsonx Orchestrate for agent coordination (react_core style, four registered toolkits).
- watsonx.Governance for Bias & Fairness monitoring, Model Drift detection, Content Safety on every inference, Explainability, and an immutable Audit Trail.
- watsonx.ai for model hosting and the REST inference API.
- IBM SkillsBuild as a RAG knowledge source for course recommendations.
- IBM Bob as the development assistant throughout. 
- IBM Code Engine and Red Hat OpenShift (alongside Railway and GitHub Pages) all provisioned via IBM Terraform. 

IBM Bob and watsonx Orchestrate form a single, end-to-end AI pipeline. IBM Bob was used to build every component of the system: it scaffolded the watsonx Orchestrate agent definitions (YAML specs), implemented all five Python toolkit packages, generated the FastAPI bridge server (src/server.py), and authored the seven Jupyter notebooks used for standalone step testing.

The pipeline flows through seven sequential steps coordinated by a watsonx Orchestrate native agent: 
- Step 1 (Welcome & Consent) — PII notice and storage choice gate the session. 
- Step 2 (Resume Translate) — AccomplishmentTranslator calls IBM Granite 4 to strip military jargon and return ATS-ready civilian bullets. 
- Step 3 (Job Analysis) — PlanBuilder's analyze_job_description() extracts required skills, preferred skills, and ATS keywords from a pasted job description or live USAJobs fetch. 
- Step 4 (Skill Mapping & Gap Analysis) — SkillMapper maps the MOS/AFSC against the O*NET Military Crosswalk and returns up to 12 civilian skills; GapAnalyzer returns coverage percentage, matched skills, gap skills, and free-course recommendations. 
- Step 5 (Resume Draft) — build_resume_draft() assembles a tagged résumé where every sentence is labelled EVIDENCED, INFERRED, or MISSING. 
- Step 6 (Interview Prep) — STAR-framed questions grounded by the résumé draft and job analysis. 
- Step 7 (Export Gate) — evaluate_export_gate() returns BLOCKED or OPEN; the UI physically prevents export while BLOCKED.

Error handling is consistent across all toolkit steps: LLM calls are wrapped in try/except blocks; JSON parse failures return structured error dicts to the coordinator rather than raising exceptions; rate-limit retries are bounded (one retry with parsed wait time) so the pipeline cannot hang. All step inputs, outputs, and error codes are logged to the FastAPI server console, providing a traceable audit record for every session. watsonx Governance is integrated at the model layer with Factsheets, Bias & Fairness monitors, Content Safety filters on every inference, Explainability, and an immutable Audit Trail. A two-layer PII guard runs before any LLM call: regex hard-blocks SSNs, phone numbers, and addresses; watsonx Governance ML content safety checks the sanitised input.

The RAG corpus contains 12 grounded sources: O*NET Military Crosswalk, O*NET Occupation Skills, IBM SkillsBuild, DoD SkillBridge, BLS Occupational Outlook Handbook, USAJobs (live API), LinkedIn/Indeed (paste), Hire Heroes USA, and CareerOneStop. All LLM responses referencing skills, courses, or job requirements are grounded against this corpus. Seven watsonx.ai Jupyter notebooks (NB 01–07) provide standalone testability for each pipeline step outside the orchestrated flow.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

