# **Mission Veteran AI** *by G3*

#### watsonx.ai

##### The two distinct roles watsonx.ai plays

watsonx.ai appears in this solution in two separate capacities: as the inference engine powering every LLM call in the pipeline (via the REST API + IBM Granite), and as the notebook runtime where seven Jupyter notebooks run for standalone testing of each pipeline step. These are architecturally independent — the REST API is used by the production bridge server; the notebooks run in watsonx.ai Studio and are for development, exploration, and validation.

##### Role 1 — LLM Inference Engine

###### The API layer

Every LLM call across all four toolkits goes through llm_generate() in toolkits/shared/_common.py. This function calls the watsonx.ai text generation REST endpoint directly — no SDK, by deliberate design:

```
  url = f"{creds['url'].rstrip('/')}/ml/v1/text/generation?version=2025-02-11"
  payload = {
    "model_id": model_id,       # "ibm/granite-4-h-small"
    "input": prompt,
    "parameters": {
        "max_new_tokens": max_tokens,
        "temperature": temperature,
        "decoding_method": "greedy",
    },
    "project_id": creds["project_id"],
  }
```

The comment in Dockerfile explains the choice: "ibm-watsonx-ai SDK is NOT used — toolkits call the REST API directly via llm_generate() in shared/_common.py to avoid SDK version instability." Using the versioned REST API (version=2025-02-11) means the toolkit won't break silently due to SDK dependency conflicts in the container.

Authentication is IBM IAM-based: _get_iam_token() exchanges the IBM Cloud API key for a short-lived bearer token before each request. This is the correct enterprise pattern — no long-lived credentials in HTTP headers.

###### Quota resilience

The llm_generate() function handles 403 token_quota_reached errors with an automatic exponential back-off retry:

```
MAX_QUOTA_RETRIES   = 1
QUOTA_RETRY_DELAY_S = 90   # generous buffer above the ~60 s per-minute quota window
```

One retry after 90 seconds keeps the total well within Railway's 300-second request timeout. The error message surfaced to the caller is human-readable: "Token quota reached. Please wait 1–2 minutes and try again — quota resets automatically."

###### What the model is asked to do — by step

| Toolkit | Function | watsonx.ai task | Model params |
| :---:   | :---:    | :---:           | :---:        | 
| AccomplishmentTranslator | translate_accomplishment() | Military bullet → one ATS-ready civilian sentence, strict no-fabrication rules | max_tokens=80, temperature=0.3 |
| SkillMapper | map_military_skills() |	Service summary → structured JSON skill inventory (≤12 skills, each with verbatim evidence quote) | max_tokens=400, temperature=0.2 |
| GapAnalyzer | analyze_skills_gap() | Skill inventory × job description → covered/gap skills + coverage percentage | max_tokens=600, temperature=0.2 |
| PlanBuilder | analyze_job_description() | Job posting → required/preferred/optional skills + ATS keywords + industry | max_tokens=800, temperature=0.2 |
| PlanBuilder | build_resume_draft() | All assembled inputs → tagged résumé (EVIDENCED/INFERRED/MISSING per sentence) | max_tokens=1200, temperature=0.2 |
| PlanBuilder | build_resume_draft() | EVIDENCED items → grounding check (CONFIRMED vs DOWNGRADE per item) | max_tokens=800, temperature=0.2 |

The grounding check is a second, back-to-back watsonx.ai call within build_resume_draft() — the model reviews its own EVIDENCED-tagged output against the original source material and can downgrade items to INFERRED if the claim cannot be directly confirmed. This self-verification pass is what gives the EVIDENCED tag meaningful weight.

llm_with_fallback() — Granite-first with Groq safety net

All six call sites go through llm_with_fallback() rather than calling llm_generate() directly:

```
  def llm_with_fallback(prompt, max_tokens=500, json_object=False, temperature=0.2):
    try:
        text = llm_generate(prompt, "ibm/granite-4-h-small", ...)
        return text, "granite"
    except Exception:
        text = groq_generate(prompt, ...)
        return text, "groq"
```

Granite is always tried first. Groq only activates if watsonx.ai fails. The model_used field is returned and logged in every Governance inference record — so the audit trail shows whether any given résumé sentence came from Granite or the fallback, which matters for bias monitoring and explainability.

##### Role 2 — Jupyter Notebook Runtime (watsonx.ai Studio)

Seven notebooks in notebooks/ run directly in watsonx.ai Studio:

| Notebook | Tests | Key scope |
| :---:    | :---: | :---:     |
| NB 01 | translate_accomplishment() | Bullet translation in isolation |
| NB 02 | map_military_skills() + analyze_skills_gap() | O*NET crosswalk + SkillsBuild recommendations |
| NB 03 | analyze_job_description() | JD parsing: required/preferred/ATS keywords |
| NB 04 | build_resume_draft() raw path | Resume tagging in isolation, grounding check |
| NB 05 | build_resume_draft() + cover letter |	Full materials package + gate evaluation |
| NB 06 | evaluate_export_gate() | Gate logic with simulated holds and hold resolution |
| NB 07 | All toolkit functions, Steps 1→7 | Authoritative end-to-end integration test |

NB 07 is the most important: it imports the real toolkit functions and runs the complete pipeline in the correct web UI order, making it the single test that validates the whole system works together — independent of the watsonx Orchestrate agent layer, the bridge server, and the front-end. If NB 07 passes, the pipeline logic is sound.

The notebooks also serve as a development accelerator — the tight feedback loop of iterating on a prompt directly in Studio and immediately seeing the structured JSON output is how the prompts for all six inference steps were written and tuned before being promoted into the toolkit Python files.

##### Why using watsonx.ai is exactly the right choice

1. IBM Granite is the right model for this workload. ibm/granite-4-h-small is a small, instruction-tuned model optimized for structured output tasks — exactly what this pipeline requires. All six inference calls expect JSON: arrays of skills, tagged résumé sections, skill gap lists, grounding verdicts. A model that reliably produces well-formed JSON without preamble or markdown fences is worth more than a larger model that occasionally wraps output in explanation text. The prompts are written around Granite's strengths: short, unambiguous instructions, explicit output format constraints, and strict no-fabrication rules.

2. The direct REST API + IAM pattern is production-safe. Using the versioned REST endpoint directly rather than the SDK eliminates an entire class of dependency-conflict failures. The IAM token exchange means the IBM Cloud API key never appears in an HTTP Authorization header as a long-lived credential. Both choices reflect production engineering discipline, not hackathon shortcuts.

3. watsonx.ai Governance integration is native. Every llm_generate() call is wrapped in log_inference() from toolkits/shared/governance.py, which logs to watsonx Governance Factsheets. The model_used field in the return value means the Governance audit trail distinguishes Granite inferences from Groq fallback inferences — which matters when bias/fairness monitors are comparing outputs across service branches and career paths.

4. The notebooks provide verifiable depth. A solution with seven working Jupyter notebooks — one per pipeline step, plus one end-to-end — demonstrates that every piece of the AI logic was developed, tested, and validated independently before being integrated. For a judge assessing whether the AI components actually work, the notebooks are runnable proof.

5. The project_id boundary isolates the workload. All inferences are scoped to a specific watsonx.ai project (WATSONX_PROJECT_ID). This means the solution inherits watsonx.ai's project-level access controls, quota management, and cost attribution — appropriate for a tool handling sensitive veteran career data, and directly compatible with the watsonx Governance subscription model.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).
