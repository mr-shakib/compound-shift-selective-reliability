# Revision R1 manuscript (2026-10-06)

- `main_revised.tex` / `.pdf`: full-length revised manuscript.
- `supplement_revised.tex` / `.pdf`: methods supplement.
- `sections/`: manuscript sections.
- `generated/`: **generated, do not edit.** Number macros (`numbers.tex`) and
  tables written by `python -m c3e.revision.report` from `results/c3e_revision/`.
- `figures/`: generated figures (same command).
- `references_revised.bib`: bibliography re-verified on 2026-10-06; entries
  that could not be read in full say so.

The original draft (21 Aug 2026) and the earlier venue builds carried the
superseded conclusions and were never submitted (removed from the current tree on 2026-10-15; in git history and the Zenodo v1.0.0 archive). The submission
build is `../jamia_r1/`.

Rebuild everything from the verified caches:

```bash
cd <project root>
bash scripts/run_revision.sh
```

Author-owned statements (ethics, funding, competing interests, contributions,
repository URL) are red placeholders; see
`docs/revision/SUBMISSION_CHECKLIST.md`.
