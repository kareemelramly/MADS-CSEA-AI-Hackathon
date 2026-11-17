# researcher (no model call)

Code-only agent. Routine:
1. Check the brief for excluded categories (physical goods; financial, investment or crypto; health or legal advice). Excluded: return; the gate stops the run and cannot be overridden.
2. Check required brief fields; missing fields give `repeat` with the list.
3. Log `define_research_criteria` with every threshold before the first search.
4. Search HN Algolia, Stack Exchange and GitHub issues in parallel (Wikipedia for background only). Thin coverage: one automatic retry with broader terms.
5. Drop items without a URL, register each item as a source ID (S001...), and count identical or near-identical excerpts (Jaccard >= 0.85 on word sets) once. Fetch and register founder evidence URLs; unreachable URLs are not registered.
6. Pass at most 20 excerpts (keyword pre-screen) to the Opportunity Analyst.
