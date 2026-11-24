# **Mission Veteran AI** *by G3*

#### SkillsBuild

##### What SkillsBuild is in this solution

IBM SkillsBuild is RAG-003 — one of 12 knowledge sources in the solution's grounding layer, and the most directly actionable one for the veteran using the tool. It is a free, IBM-hosted platform offering digital credentials (badges) across technology, business, and professional skills domains, specifically designed for adult learners and career changers. In this solution it fills a precise, well-defined role: when the GapAnalyzer identifies skills a veteran is missing for their target role, SkillsBuild is the first recommended path to close those gaps, because every course it offers is free, self-paced, and ends in a verifiable credential.

##### How SkillsBuild is integrated technically

The integration has four distinct layers:

1. Static knowledge base — knowledge-bases/skillsbuild_courses.json

20 curated courses are stored as a local JSON file. Each entry carries:

- course_id, title, provider, url — identity and deep link to skillsbuild.org
- skill_tags — keyword list used for fuzzy matching against gap skills
- career_paths — one of: IT/Cybersecurity, Project Management, Operations, Logistics
- credential — always "Badge" (verifiable digital credential)
- estimated_hours — ranging from 8 hours (Agile Explorer) to 30 hours (Data Science Foundations)
- description — one-sentence plain-language summary

The catalog spans: Cybersecurity, Cloud Computing, Data Science, AI, Project Management, Supply Chain, Enterprise Design Thinking, Linux, Network Security, Agile, DevOps, Python/Data Analysis, Communication, Leadership, Blockchain, Watson AI, Risk Management, Digital Transformation, SQL/Databases, and Workplace Foundations.

2. lookup_skillsbuild() — toolkits/shared/_common.py

A matching function that runs entirely in-process, with no API call and no latency:

```
  def lookup_skillsbuild(career_path: str, gap_skills: list) -> list:
    for course in load_skillsbuild_courses():
        if career_path not in course.get("career_paths", []):
            continue
        score = sum(
            1 for tag in course.get("skill_tags", [])
            if any(g in tag.lower() or tag.lower() in g for g in gap_lower)
        )
        scored.append((score, course))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:5]]
```

It filters first by career path, then scores each course by how many of its skill_tags overlap with the identified gap skills using bidirectional substring matching. The top 5 most relevant courses are returned. This is a deliberate, lightweight RAG pattern — no vector database, no embedding, no network hop — appropriate for a curated 20-entry catalog.

3. GapAnalyzer toolkit — toolkits/gap_analyzer/analyze_skills_gap.py

analyze_skills_gap() is the tool that calls lookup_skillsbuild(). After the LLM identifies gap_skills and covered_skills from the veteran's inventory vs. the job description, it immediately calls the lookup and returns skillsbuild_recommendations as part of its structured output:

```
  skillsbuild = lookup_skillsbuild(target_career_path, gap_skills)
  output = {
    "covered_skills": ...,
    "gap_skills": ...,
    "coverage_pct": ...,
    "skillsbuild_recommendations": [
        {
            "course_id": c["course_id"],
            "course_title": c["title"],
            "credential": c["credential"],
            "estimated_hours": c["estimated_hours"],
            "url": c["url"],
            "skill_tags": c["skill_tags"],
        }
        for c in skillsbuild
    ],
    ...
  }
```

The output also carries a disclaimer that explicitly says: "IBM SkillsBuild course recommendations are sourced from the local knowledge base — verify availability at skillsbuild.org." That honesty matters for responsible AI.

4. Front-end rendering — web/index.html

In Step 4 (Gap Analysis), whenever uncovered skills exist, the UI appends a direct call-to-action:

```
📚 Close skill gaps with free courses at IBM SkillsBuild — skillsbuild.org
```

In the mock data layer, the gap skill objects themselves carry course-level detail — title, credential_type, hours_estimate, and url — meaning every identified gap is paired with a specific course recommendation, not just a generic link. The step summary message (web/index.html:2687) reads: "X skill gaps were identified with free IBM SkillsBuild courses to close them."

##### Why including SkillsBuild is exactly the right choice

1. It is free for veterans. This is non-negotiable for the population being served. A transitioning service member, often in a financial gap period between military pay and their first civilian paycheck, cannot pay for training courses. SkillsBuild removes that barrier entirely — no subscription, no credit card, no employer sponsorship required.

2. The credentials are real and verifiable. Every course produces a Credly-backed digital badge that can be shared on LinkedIn or a résumé. That matters specifically for veterans whose civilian skills are, by design, unrecognizable to civilian hiring managers — a "Network Security" badge from IBM carries immediate recognition value that a DD-214 skill description does not.

3. It is IBM's own platform, which makes it appropriate in an IBM hackathon context. The solution is built on watsonx Orchestrate, watsonx Governance, and IBM Granite. Recommending IBM SkillsBuild as the upskilling pathway is coherent and mission-aligned — the entire solution sits within the IBM ecosystem and benefits veterans through it.

4. The matching is deterministic, not hallucinated. The LLM identifies gap skills; the knowledge base lookup resolves them to specific courses via keyword matching on a curated, manually verified catalog. There is no risk of the model fabricating a course name or URL. The disclaimer in the output reinforces this — veterans are told to verify at skillsbuild.org before acting on any recommendation.

5. It is paired with DoD SkillBridge (RAG-004), creating a two-track recommendation. SkillsBuild handles self-paced online learning; DoD SkillBridge handles on-the-job training with civilian employers while still on active duty. Together, they cover both the certification pathway and the work-experience pathway to closing a skills gap — a genuinely comprehensive answer to the transition problem, not just a link to a course catalog.

6. No API key, no dependency, no cost. SkillsBuild has no public API (live_api_available: false in rag_sources.json), so the entire integration is a local JSON file that ships with the repository. The solution works identically in mock mode, local mode, Railway, Code Engine, and OpenShift — with no external dependency to manage, rate-limit, or authenticate against.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

