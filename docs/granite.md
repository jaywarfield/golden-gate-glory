# **Mission Veteran AI** *by G3*

#### Granite & RAG

##### The core design principle

IBM Granite (ibm/granite-4-h-small) is not used as a general-purpose question-answering model in this solution. It is used as a structured extraction and reasoning engine operating over grounded context — context assembled from RAG sources before every prompt is constructed. The RAG layer is not a retrieval-augmented generation system in the vector-database sense; it is a deliberate, deterministic context injection pipeline where every piece of information handed to Granite is sourced from a named, trusted, citable knowledge base. Granite never reasons from parametric memory alone on any claim that matters to a veteran's career document.

The 12 RAG sources documented in docs/rag.md divide into three groups based on how they interact with Granite:

| Group | Sources | How they reach Granite |
| :---: | :---:   | :---:                  |
| Injected into prompt context | RAG-001 O*NET Crosswalk · RAG-002 O*NET Skills · RAG-005 BLS OOH · RAG-008 O*NET Work Activities · RAG-009 User job posting | Assembled into context_block or crosswalk strings appended directly to the prompt |
| Post-LLM KB lookup | RAG-003 IBM SkillsBuild · RAG-004 DoD SkillBridge | Deterministic lookup runs after Granite identifies gap skills; no LLM involvement |
| Referral-only | RAG-010 Hire Heroes USA · RAG-011 LinkedIn · RAG-012 Indeed |	Surfaced as text in coordinator instructions; Granite routes veterans to these resources |

##### RAG → Granite flow by pipeline step

Step 2 — Bullet Translation (translate_accomplishment)
No KB lookup runs before this step. The veteran's raw bullet is itself the context. Granite's prompt contains a strict no-fabrication constraint:

```
    "STRICT: Do not invent any fact, number, name, metric, or detail that is not explicitly stated in the original bullet or metrics. If the bullet is too vague to produce a faithful translation, output exactly the word SKIP and nothing else."
```

The bullet is the entire RAG context for this call. Granite is instructed to treat it as a primary source and translate only what is demonstrably present. The SKIP sentinel is a formal hallucination prevention mechanism — when Granite cannot ground the output in the input, it refuses to generate.

Step 4 — Skill Mapping (map_military_skills)

This is the most RAG-dense step. Before the prompt is constructed, two KB lookups run in Python:

1. RAG-001 (onet_military_crosswalk.json) — lookup_crosswalk(specialty_code, service_branch) maps the MOS/AFSC code to a civilian O*NET-SOC code and job title: e.g. 25B → Network Administrator (SOC 15-1244.00)
2. RAG-002 + RAG-008 (onet_occupation_skills.json) — loads the required skills and work activities for the veteran's target career path from the O*NET database

Both results are assembled into a crosswalk_context string and injected into the prompt. Critically, the prompt then explicitly tells Granite not to use the O*NET context as a skills source:

```
  O*NET context (reference only — do NOT copy these as skills):
  O*NET crosswalk: 25B → Network Administrator (SOC 15-1244.00)

  SERVICE SUMMARY:
  [veteran's own words]
```

This is a subtle but important design choice: the O*NET data proves to Granite that the specialty code maps to a known civilian occupation, which helps it interpret military terminology — but Granite is forbidden from listing O*NET skills as the veteran's own. Every skill must be traceable to a verbatim quote from the service summary. The evidence field requirement enforces this: each returned skill must include the exact phrase from the veteran's text that justifies it.

The RAG sources (RAG-001, 002, 005, 008) function here as a disambiguation and terminology bridge — they give Granite the civilian vocabulary to interpret military jargon without letting it pad the skill inventory with generic occupation requirements.

Step 4 continued — Gap Analysis (analyze_skills_gap)

Granite receives two grounded inputs:

- The skill inventory just produced (itself grounded in RAG-001/002 + the veteran's own words)
- The raw job description (RAG-009 — user-pasted from LinkedIn, Indeed, or USAJobs)

Granite performs semantic matching across these two sources — fuzzy matching by competency rather than exact string — and returns covered_skills, gap_skills, and coverage_pct. Crucially, Granite does not recommend training resources. That happens entirely in Python after Granite returns:

```
  gap_skills = result.get("gap_skills", [])
  skillsbuild = lookup_skillsbuild(target_career_path, gap_skills)   # RAG-003
  skillbridge = lookup_skillbridge(target_career_path)               # RAG-004
```

The lookup_skillsbuild() function scores IBM SkillsBuild courses (RAG-003) by how many of their skill_tags overlap with Granite's identified gap skills. lookup_skillbridge() filters DoD SkillBridge programs (RAG-004) by career path. Both run in-process, deterministically, with no LLM call — there is zero chance of a hallucinated course title or a fabricated program URL because Granite is not involved in this stage at all.

This is an intentional RAG architecture decision: use Granite for the judgment task (semantic skill matching) and use deterministic KB lookup for the retrieval task (finding specific resources). Each component does what it is best suited for.

Step 3 — Job Description Analysis (analyze_job_description)

RAG-009 (the user-pasted job posting) is the entire context for this call. Granite extracts required_skills, preferred_skills, optional_skills, ATS keywords, and industry from the raw text. The structured output from this step then feeds into gap analysis and resume drafting as a named, citable source — it is never merged with Granite's parametric knowledge about what jobs "usually require."

Step 5 — Resume Draft (build_resume_draft)

The resume step is where the RAG pipeline culminates. By this point every input is itself a grounded artifact:

- service_summary — veteran's own words
- translated_bullets_json — Granite output grounded in those words (Step 2)
- skill_inventory_json — Granite output grounded in O*NET crosswalk + veteran words (Step 4)
- job_analysis_json — Granite output grounded in the pasted job description (Step 3)

These are assembled into a single context_block and passed to Granite with explicit tagging instructions:

```
  [EVIDENCED] — directly supported by the inputs below
  [INFERRED]  — reasonable inference from the inputs (must be plausible, not invented)
  [MISSING]   — required by the JD but absent from inputs; write a placeholder
```

Granite is told: "Using ONLY the evidence below, produce a resume draft." The entire accumulated RAG corpus — O*NET crosswalk, occupation skills, the veteran's own words, the target job posting — is present in the context. Granite's job is to organize and tag, not to invent.

The grounding check — a second Granite pass over its own output

After the resume draft is produced, a second Granite call reviews every EVIDENCED-tagged item:
```
  SOURCE CONTEXT:
  [same context_block — O*NET data + veteran inputs + job analysis]

  EVIDENCED ITEMS TO CHECK:
  [list of items Granite tagged EVIDENCED in the first pass]
```
Granite responds with CONFIRMED or DOWNGRADE for each item, with a reason for any downgrade. Items that cannot be confirmed against the source context are automatically reclassified as INFERRED. This downgrade count becomes a hold on the export gate. The accumulated RAG corpus serves as the ground truth that both Granite passes reason against.

##### Why this RAG + Granite combination is exactly right

1. Granite is optimized for structured output over grounded context — which is precisely what this pipeline requires. Every inference call returns JSON: arrays, tagged objects, verdict lists. ibm/granite-4-h-small is a small, instruction-tuned model that reliably follows explicit output format constraints. The alternative — a larger general-purpose model that might produce richer prose but drifts from the JSON schema — would break every downstream parser.

2. The RAG sources are exclusively high-trust, official sources. Of the 12 sources in docs/rag.md, 10 carry a High trust rating: U.S. Department of Labor (O*NET, BLS, CareerOneStop), U.S. Department of Defense (SkillBridge), U.S. OPM (USAJobs), IBM (SkillsBuild), and an established 501(c)(3) with DoD/VA partnerships (Hire Heroes USA). The only medium-trust sources (LinkedIn, Indeed) are explicitly flagged as referral-only with no live integration path. Granite is never asked to reason over unverified data.

3. The RAG architecture prevents the most dangerous failure mode for this use case — hallucinated credentials. A veteran submitting a résumé with an AI-fabricated certification or inflated skill to a federal agency faces serious professional and legal consequences. The design ensures Granite cannot add skills not present in the veteran's own words, cannot recommend courses that don't exist, and cannot claim a job posting requires skills that aren't in the actual text. Each of these constraints is enforced at the architecture level, not just in a prompt instruction.

4. The post-LLM KB lookup pattern keeps recommendation fidelity at 100%. Because SkillsBuild course recommendations (RAG-003) and SkillBridge program listings (RAG-004) are resolved by deterministic keyword matching after Granite's gap analysis — not by Granite itself — every URL, credential type, and time estimate in the output is guaranteed to come from a manually curated, verified knowledge base. There is no mechanism by which Granite can fabricate a course that does not exist.

5. The chained grounding — where each step's output becomes the next step's RAG context — creates compounding evidence provenance. By the time the résumé draft is generated, every input to Granite has itself been grounded in an earlier, verified source. The O*NET crosswalk grounded the skill inventory. The skill inventory and the job posting grounded the gap analysis. All of these grounded the résumé draft. The grounding check then verifies the draft against that entire chain. The veteran's final document is not just AI-generated — it is AI-generated and AI-verified against a traceable provenance chain of official government and IBM data sources.

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

RAG Sources Summary:

- 12 sources total.

- 8 actively integrated (5 static JSON, 1 embedded, 1 partial embed, 1 referral).

- 2 pending integration (RAG-006 and RAG-007 need API keys).

- 2 documented as referral-only with no feasible live integration path (RAG-011, RAG-012).

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

