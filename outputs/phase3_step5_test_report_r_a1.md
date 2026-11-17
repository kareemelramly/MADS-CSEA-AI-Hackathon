UNVALIDATED · FOUNDER OVERRIDE

# Phase 3 test report (QA agent, no model call)

Attempt 1. Archetype A1: 14 applicable checks; QA-07 not applicable.

| Check | Name | Result | Evidence |
|---|---|---|---|
| QA-01 | Manifest complete | pass | 4 files |
| QA-02 | Size | pass | total 7715 bytes; too big: [] |
| QA-03 | Format validity | pass | CSV column counts [5]; checklist headings present: True |
| QA-04 | Journey trace | pass | 5 steps traced |
| QA-05 | Internal links | pass | all resolve |
| QA-06 | No external resources | pass | none |
| QA-07 | Script integrity | n/a | A1 has no HTML or scripts |
| QA-08 | Banned content | pass | none found |
| QA-09 | Excluded category | pass | not excluded |
| QA-10 | Claims sourced | pass | all numeric/market lines cited or ASSUMPTION |
| QA-11 | Mocks and override labelled | pass | override banner required |
| QA-12 | Docs headings | pass | Overview, Quick start, How to use, What is mocked, Troubleshooting, Limitations |
| QA-13 | Licence | pass | MIT (OSI) |
| QA-14 | Acceptance criteria | pass | 3 automated via QA-04/QA-05; MANUAL listed: 1 |
| QA-15 | Naming | pass | all match phase3_step<M>_* |

## Acceptance criteria

1. Given The user opens the Markdown checklist, when They review the wedding milestones, then They can check off completed tasks to track progress. (automated via QA-04, QA-05)
2. Given The user opens the CSV tracker, when They input vendor details like name, service, and contact info, then The data is structured for easy import into spreadsheet software. (automated via QA-04, QA-05)
3. Given The user is managing multiple vendors, when They use the tracker, then They can see a consolidated list of all service providers in one place. (automated via QA-04, QA-05)

## MANUAL (not checked, never reported as passed)

- [ ] A real target user completes the core workflow using only the docs (MANUAL, not checked)

## Known limitations

- QA-08 and QA-10 are pattern-based and can miss paraphrased violations.
