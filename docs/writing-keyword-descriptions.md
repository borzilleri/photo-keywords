# Writing Keyword Descriptions That Classify Reliably

This guide explains how to write the keyword descriptions in `taxonomy.json` so that the
classifier (Claude, reading each photo) applies them **consistently and precisely**. The
quality of these descriptions matters more than the prompt itself — a vague description
produces inconsistent tags no matter how good the prompt is.

## The core principle: a controlled vocabulary

The classifier may use **only** the keywords you define — it never invents new ones. This is
what keeps your library searchable. Without it the model produces "city", "urban",
"cityscape", and "street" for the same scene and fragments your library into near-duplicates.

`taxonomy.json` is the single source of truth. `classify.py` builds both the prompt and the
output validation schema from it, so a keyword that isn't in the file literally cannot be
applied.

## Anatomy of a good keyword entry

Every keyword in `taxonomy.json` has five fields. Each does a specific job:

| Field | Job | Failure if missing |
|-------|-----|--------------------|
| `definition` | One sentence: what this keyword means. | Model guesses the scope. |
| `includes` | Concrete cases that DO qualify. | Model under-applies (low recall). |
| `excludes` | Cases that look close but DON'T qualify — point to the right neighbor. | Model over-applies / two keywords compete. |
| `examples` | 2–3 vivid, typical images. | Model lacks an anchor for the typical case. |
| `keyword` | The exact string written to Photos. | — |

## The seven rules

1. **One sentence for the definition.** If you need two, the keyword is probably two
   keywords. Split it.

2. **Define by the *dominant subject*, not by what merely appears.** Almost every outdoor
   photo contains some sky and some plants. State what has to *dominate the frame* for the
   keyword to apply. "Sky" means the sky is the subject — not that sky is visible.

3. **Disambiguate against the nearest neighbor explicitly.** The hardest classification
   errors are between adjacent keywords (`nature` vs `water`, `urban` vs `architecture`). In
   `excludes`, name the competing keyword and the deciding factor: *"use 'architecture' when
   ONE building is the subject; use 'urban' for wide multi-building streetscapes."* Every pair
   that can be confused should reference each other.

4. **Prefer precision over coverage.** It's better to tag less and be right. A wrong keyword
   is worse than a missing one because the user trusts search results. When the description is
   ambiguous, tighten `excludes` rather than broadening `includes`.

5. **No match is a valid answer.** The classifier may return an empty tag list when nothing
   fits. Never pressure it toward a "best guess" content keyword — a wrong keyword is worse than
   no keyword. Empty-tag photos are simply skipped at write time. (Low `confidence` is recorded
   separately and can be filtered with `apply_keywords.py --min-confidence`.)

6. **Allow multiple keywords, but only when each independently qualifies.** A sunset over the
   ocean can be both `sky` and `water` if both dominate. Don't force exclusivity — but each tag
   must stand on its own under rule 2, not be a weak "also kind of present."

7. **Use concrete examples, not categories.** "a latte with foam art" anchors better than
   "beverages." Pick the *typical* member of the category, not the edge case.

8. **Nesting: parent = theme, child = specific subject.** Children of one parent (`nature/water`,
   `nature/plants`, `nature/sky`, `nature/landscape`) are the sharpest disambiguation problem —
   each child's `excludes` should name its siblings and the deciding factor (what *dominates* the
   frame). Keep one child as the broad fallback for its theme (e.g. `nature/landscape` catches
   natural scenes that aren't specifically water/plants/sky/animals) so generic theme members
   still get tagged rather than dropped.

## How to refine after the test batch

The starter taxonomy is a hypothesis. After the test batch (see the project README), look at
where the classifier was wrong and apply the matching fix:

- **Two keywords kept competing for the same photos** → strengthen `excludes` on both, naming
  each other and the deciding factor.
- **A real category landed in empty-tags (no match) repeatedly** → either add a keyword for it,
  or widen the closest keyword's `includes`.
- **A keyword was applied to things it shouldn't be** → tighten its `definition` (rule 2) and
  add the offending case to `excludes`.
- **The model hedged with low confidence a lot** → the descriptions are ambiguous; add
  examples and sharpen the dominant-subject language.

Change `taxonomy.json` (the source of truth), then re-mirror the human doc `keywords.md`, then
re-run the test batch. Iterate until the tags look right *before* running the full library.
