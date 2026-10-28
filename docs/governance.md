# **Mission Veteran AI** *by G3*

#### Governance

Governance is a strong fit precisely because of what this solution does and who it serves — a vulnerable population making high-stakes career decisions based on AI-generated output.

Where Governance adds real value:

- Bias and fairness monitoring across military branches The map_military_skills and analyze_skills_gap tools both pass free-form text through ibm/granite-4-h-small to produce structured outputs. If the model systematically under-scores skills from certain branches (e.g. Coast Guard, Space Force, or enlisted vs. officer) or over-recommends certain career paths, you wouldn't know today. Governance's fairness metrics can surface disparate outputs across demographic or service-branch segments.
- Prompt injection and hallucination detection translate_bullet.py, analyze_skills_gap.py, and build_plan.py all construct prompts from user-supplied text (the job description, service summary, and bullets). Governance's input/output monitors can flag prompt injection attempts and catch cases where the model fabricates skills or credentials — directly countering the EVIDENCED / INFERRED / MISSING tagging system that is the solution's main trust mechanism.
- Explainability for the export gate The evaluate_export_gate logic blocks export when inferred_count > 0 or missing_count > 0. Governance's explainability layer can produce a human-readable rationale log for why a specific claim was tagged INFERRED vs. EVIDENCED — useful if a veteran disputes a gate hold or if the system is audited.
- Model drift detection over time The static knowledge bases (O*NET, SkillsBuild, SkillBridge) are updated quarterly or annually. If the model's interpretation of those knowledge bases drifts between Granite versions — e.g. an update causes different coverage percentages for the same inputs — Governance's drift monitors would catch it before veterans see degraded results.
- Audit trail for a high-stakes population Veterans relying on this tool for federal job applications (USAJobs, RAG-006) or civilian employment are making consequential decisions. Governance provides an immutable transaction log of every inference — what went in, what came out, which model version — which is directly relevant to VA/DoD responsible AI requirements and any future compliance reporting.
- PII detection reinforcement _common.py has a regex-based PII guard (_PII_PATTERNS) that catches SSNs, DoD IDs, emails, and phones. It does not catch names, informal location references, or novel PII patterns. Governance's content safety monitors — operating at inference time on the model I/O — provide a second, ML-based PII layer that the regex approach misses.

Where Governance would add less value:

- Model selection where all five agents are already pin to ibm/granite-4-h-small, so model governance (version locking, approval workflows) is already partially addressed by the YAML specs.
- Access control where Orchestrate handles the auth boundary; Governance would be redundant there.
- Throughput / cost where this is a low-volume, session-based tool, not a high-scale inference pipeline, so Governance's cost attribution features are lower priority.

Practical integration point:

The most targeted entry point would be attaching a Governance AI Factsheet to the gap_analyzer and bullet_translator toolkits — the two that produce the outputs veterans directly copy into job applications. That gives you bias monitoring, drift detection, and an audit trail for the highest-consequence outputs without requiring changes to any of the existing agent or toolkit code.

---

# License

This application is licensed under the Apache License, Version 2.  Separate third-party code objects invoked by this application are licensed by their respective providers pursuant to their own separate licenses.  Contributions are subject to the [Developer Certificate of Origin, Version 1.1](https://developercertificate.org/) and the [Apache License, Version 2](https://www.apache.org/licenses/LICENSE-2.0.txt).

