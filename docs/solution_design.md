# **Mission Veteran AI – IBM AI Lab Challenge**

### Solution Design

## RAG Sources

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
| RAG-012 | Indeed Job Postings | :yellow_circle: Medium — aggregator, unverified | User paste via RAG-009 (API deprecated 2023) | :no_entry_sign: No live integration — API deprecated Yes (enterprise) | No | (referral only) | N/A | 

Summary: 12 sources total — 8 actively integrated (5 static JSON, 1 embedded, 1 partial embed, 1 referral), 2 pending integration (RAG-006 and RAG-007 need API keys), 2 documented as referral-only with no feasible live integration path (RAG-011, RAG-012).

### Solution Diagram

TBD

### Technology Used

TBD

### References

TBD

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

