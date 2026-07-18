# Target-Term Configuration Review

Source file reviewed: `c3e_audit_toolkit/configs/terms.yaml`
Review date: 2026-07-15

Scope: the five target conditions currently configured — Cardiomegaly, Edema, Pleural Effusion,
Atelectasis, Consolidation. No terms have been added or removed in this review; `terms.yaml` was left
unmodified because no obvious, linguistically-safe correction (e.g., a typo) was found. Findings below
are documentation for future manual review, not automatic edits.

---

## Cardiomegaly

- **Current direct terms:** `cardiomegaly`
- **Current synonyms:** `enlarged heart`, `cardiac enlargement`, `enlarged cardiac silhouette`,
  `enlarged cardiomediastinal silhouette`
- **Potential additional terms:** none proposed (avoid scope creep without clinical review)
- **Potential ambiguous terms:** `enlarged cardiomediastinal silhouette` — refers to the combined
  heart + mediastinum silhouette; enlargement can be driven by mediastinal widening (e.g., mass,
  vascular pathology) rather than the heart itself
- **Terms that may cause false positives:** `enlarged cardiomediastinal silhouette` (see above)
- **Terms requiring medical review:** `enlarged cardiomediastinal silhouette`
- **Negation concerns:** "no cardiomegaly", "heart size is normal", "cardiac silhouette is not
  enlarged" — negation detection must be verified against the toolkit's negation handling before
  trusting raw term counts
- **Speculation / "rule out" concerns:** "cannot exclude cardiomegaly", "borderline cardiomegaly",
  "possible mild cardiac enlargement" — these should not count as confirmed positive mentions

## Edema

- **Current direct terms:** `edema`, `pulmonary edema`
- **Current synonyms:** `vascular congestion`, `pulmonary vascular congestion`, `fluid overload`,
  `interstitial edema`
- **Potential additional terms:** none proposed
- **Potential ambiguous terms:** `vascular congestion` and `fluid overload` — both can appear in text
  describing an early/mild finding or a systemic clinical state without a confirmed radiographic
  pulmonary edema diagnosis
- **Terms that may cause false positives:** `vascular congestion`, `fluid overload` — "fluid overload"
  in particular is often a clinical/systemic term (e.g., renal or cardiac fluid status) that does not
  always correspond to a chest-X-ray finding
- **Terms requiring medical review:** `vascular congestion`, `fluid overload`
- **Negation concerns:** "no pulmonary edema", "resolved vascular congestion", "edema has improved" —
  improvement/resolution language should not be conflated with a present positive finding
- **Speculation / "rule out" concerns:** "cannot rule out edema", "question of mild interstitial
  edema", "early edema versus congestion" — differential/hedged language requires care

## Pleural Effusion

- **Current direct terms:** `pleural effusion`, `effusion`
- **Current synonyms:** `pleural fluid`, `fluid in the pleural space`, `blunting of the costophrenic
  angle`
- **Potential additional terms:** none proposed
- **Potential ambiguous terms:** the bare direct term `effusion` — without the qualifier "pleural" this
  can match unrelated findings such as pericardial effusion or joint effusion mentioned in the same
  report (e.g., in comparison to a prior study or an unrelated clinical note)
- **Terms that may cause false positives:** `effusion` (bare form), `blunting of the costophrenic
  angle` (a radiographic sign that is suggestive of but not exclusively caused by effusion — can also
  reflect scarring or volume loss)
- **Terms requiring medical review:** `effusion` (bare form) — consider whether the toolkit's matching
  logic already requires nearby context (e.g., "pleural") before counting a bare "effusion" hit
- **Negation concerns:** "no pleural effusion", "effusion has resolved", "small effusion, unchanged"
- **Speculation / "rule out" concerns:** "cannot exclude small effusion", "possible trace effusion",
  "effusion versus atelectasis" (differential language explicitly mixing two target conditions)

## Atelectasis

- **Current direct terms:** `atelectasis`
- **Current synonyms:** `subsegmental collapse`, `linear opacity`, `plate-like atelectasis`
- **Potential additional terms:** none proposed
- **Potential ambiguous terms:** `linear opacity` — this is a broad radiographic descriptor that is not
  specific to atelectasis; it can reflect scarring, prior surgical change, or other linear densities
- **Terms that may cause false positives:** `linear opacity` — this is the term most likely to
  over-match relative to the other conditions' synonyms, since it lacks a qualifier tying it
  specifically to atelectasis (unlike `plate-like atelectasis`, which is self-qualifying)
- **Terms requiring medical review:** `linear opacity` — recommend evaluating whether this should be
  narrowed (e.g., to `linear atelectasis` or `linear opacity consistent with atelectasis`) or removed;
  left unchanged here because no "obvious" correction was evident and narrowing wording is a clinical
  judgment call, not a typo fix
- **Negation concerns:** "no atelectasis", "prior atelectasis has resolved", "stable linear opacity,
  unchanged" (stability language should not be treated as a new positive finding)
- **Speculation / "rule out" concerns:** "likely subsegmental atelectasis versus scarring", "cannot
  distinguish atelectasis from early consolidation"

## Consolidation

- **Current direct terms:** `consolidation`
- **Current synonyms:** `airspace consolidation`, `focal airspace disease`, `lobar opacity`
- **Potential additional terms:** none proposed
- **Potential ambiguous terms:** `lobar opacity` — "opacity" alone is broad, though qualified here by
  "lobar"; still less specific than "consolidation" itself
- **Terms that may cause false positives:** `lobar opacity` — could, in principle, describe a mass or
  other lobar process rather than consolidation specifically, though this is a lower risk than the
  unqualified `linear opacity` under Atelectasis
- **Terms requiring medical review:** `lobar opacity`
- **Negation concerns:** "no focal consolidation", "consolidation has cleared", "no lobar opacity"
- **Speculation / "rule out" concerns:** "cannot exclude underlying consolidation", "possible early
  consolidation versus atelectasis"

---

## Cross-cutting notes

- Per the audit toolkit's safety guidance, broad unqualified words such as "fluid," "opacity," "heart,"
  or "congestion" were **not** added to any term list in this review, consistent with the instruction
  to avoid terms likely to create false matches.
- The single highest-risk existing term identified is `linear opacity` (Atelectasis synonym) and, to a
  lesser extent, `effusion` (Pleural Effusion direct term) — both are candidates for tightening in a
  future medically-reviewed pass, but were left unchanged here since no unambiguous typo/correction was
  present.
- No modification was made to `configs/terms.yaml` in this review. If a future change is made, create
  `configs/terms.original.yaml` as a backup first, per project instructions.
