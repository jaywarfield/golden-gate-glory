# **Mission Veteran AI – IBM AI Lab Challenge**

![Architecture](images/solution_architecture.pdf)

#### RAG Sources

| ID    | Name  | Trust | Access Method | Integration Status | API Key? | Live API? | Used By | Update Cadence |
| :---: | :---: | :---: | :---:         | :---:              | :---:    | :---:     | :---:   | :---:          |
| RAG-001 | O*NET Military Occupational Crosswalk | :green_circle: High — U.S. Dept. of Labor | Static JSON (onet_military_crosswalk.json) | :white_check_mark: Integrated | No | Yes | skill_mapper | Annual |
| RAG-002 | O*NET Occupation Skills | :green_circle: High — U.S. Dept. of Labor | Static JSON (onet_occupation_skills.json) |   :white_check_mark: Integrated | No | Yes | skill_mapper | Annual |
| RAG-003 | IBM SkillsBuild Course Catalog | :green_circle: High — IBM | Static JSON (skillsbuild_courses.json) |  :white_check_mark: Integrated | No | No | gap_analyzer | Quarterly |
| RAG-004 | DoD SkillBridge Program List | :green_circle: High — U.S. Dept. of Defense | Static JSON (skillbridge_programs.json) | :white_check_mark: Integrated | No | No | gap_analyzer | Quarterly |
| RAG-005 | BLS Occupational Outlook Handbook | :green_circle: High — Bureau of Labor Statistics | Embedded in onet_occupation_skills.json | :white_check_mark: Integrated (embedded) | No | Yes | skill_mapper | Annual |
| RAG-006 | USAJobs API | :green_circle: High — U.S. OPM | Live API (data.usajobs.gov/api/search) | ⏳ Not yet integrated — needs API key | Yes | Yes | (none yet) | Real-time |
| RAG-007 | CareerOneStop Occupation Profile | :green_circle: High — U.S. Dept. of Labor | Live API (api.careeronestop.org/v1/occupation/) | :hourglass: Not yet integrated — needs API key | Yes | Yes | (none yet) | Quarterly |
| RAG-008 | O*NET Work Activities | :green_circle: High — U.S. Dept. of Labor | Partial embed in onet_occupation_skills.json |  :white_check_mark: Integrated (partial) | No | Yes | skill_mapper | Annual |
| RAG-009 | Civilian Job Postings (user-provided) | :yellow_circle: User-provided — unverified | User paste via job_description parameter |  :white_check_mark: Integrated | No | No | gap_analyzer, plan_builder | Per session |
| RAG-010 | Hire Heroes USA | :green_circle: High — 501(c)(3) w/ DoD & VA partnerships | Referral only — no API | :white_check_mark: Integrated (referral) | No | No | coordinator, gap_analyzer | N/A |
| RAG-011 | LinkedIn Jobs | :yellow_circle: Medium — employer-authored, unverified | User paste via RAG-009 (partner API not feasible) | :no_entry_sign: No live integration — ToS/API blocked | Yes (partner) | No | (referral only) | N/A |
| RAG-012 | Indeed Job Postings | :yellow_circle: Medium — aggregator, unverified | User paste via RAG-009 (API deprecated 2023) | :no_entry_sign: No live integration — API deprecated | Yes (enterprise) | No | (referral only) | N/A | 

Summary:

- 12 sources total.

- 8 actively integrated (5 static JSON, 1 embedded, 1 partial embed, 1 referral).

- 2 pending integration (RAG-006 and RAG-007 need API keys).

- 2 documented as referral-only with no feasible live integration path (RAG-011, RAG-012).

#### Notebooks

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

### Solution Diagram

TBD

### Technology Used

TBD

### References

TBD

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

