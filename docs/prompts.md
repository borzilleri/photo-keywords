# Classification Prompts

This documents the exact prompt and invocation `classify.py` uses to classify each photo with
Claude Code headless (`claude -p`). The taxonomy portion is generated at runtime from
`taxonomy.json`, so this file shows the structure and the fixed wording.

## How `classify.py` calls Claude

```bash
claude -p "<PROMPT>" \
  --model sonnet \
  --allowed-tools Read \
  --add-dir <thumbnails-dir> \
  --output-format json \
  --json-schema '<SCHEMA>'
```

- **`--allowed-tools Read`** lets the agent open the image file non-interactively (no prompt).
- **`--add-dir`** grants Read access to the thumbnails directory.
- **`--output-format json`** wraps the run in an envelope; the model's answer is in `.result`.
- **`--json-schema`** forces `.result` to be valid JSON matching the schema below — this is what
  makes the output reliably parseable instead of prose.
- **`--model`** defaults to `sonnet` (good accuracy/cost balance for ~2k images). Use `haiku`
  for cheaper/faster runs, `opus` for the hardest cases.

## Output schema (built from `taxonomy.json`)

```json
{
  "type": "object",
  "properties": {
    "tags": {
      "type": "array",
      "items": { "type": "string", "enum": ["<all selectable child/standalone keywords>"] },
      "minItems": 0
    },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "reason": { "type": "string" }
  },
  "required": ["tags", "confidence", "reason"]
}
```

- The `enum` is the controlled vocabulary — the model physically cannot return an invented tag.
  It contains the **child** keywords (`nature/water`, `art/anime`, …) and **standalone**
  keywords (`food`, …). Bare parents (`nature`) are NOT selectable; they are added at write time
  by `apply_keywords.py --with-parents`.
- **`minItems: 0`** — an empty list is valid. When nothing fits, the model returns `[]` rather
  than forcing a guess.

## The prompt

The literal string sent as `<PROMPT>`. `{image_path}` and `{taxonomy_block}` are filled in by
`classify.py`.

```
Read the image at {image_path} and classify its CONTENT — what is in the image, not its
composition or quality.

Use ONLY the keywords below. Do not invent keywords.

{taxonomy_block}

Rules:
- Judge the DOMINANT subject(s) of the image, not incidental background details.
- Use the most SPECIFIC keyword that applies.
- You may return MULTIPLE keywords when more than one independently dominates the
  frame (e.g. a city beside a harbor -> "urban/cityscape" and "nature/water").
- Prefer precision over coverage: a wrong keyword is worse than a missing one.
- If NO keyword fits, return an empty list. Do not force a guess.
- confidence (0.0-1.0) is your certainty. reason is ONE short sentence.

Return only the structured object: tags, confidence, reason.
```

`{taxonomy_block}` is rendered from `taxonomy.json`, grouped by parent theme, then a
"Standalone keywords" section, each line as `- <keyword>: <definition> (NOT: <excludes>)`.

## Confidence handling

`confidence` is recorded on every row for auditing. It is **not** used to drop tags during
classification. If you want to write only high-confidence tags, filter at apply time:
`apply_keywords.py --min-confidence 0.7`.

## Refining after the test batch

1. Export a representative sample: `export_thumbnails.py --shuffle --limit 100`.
2. Classify: `classify.py` (writes `data/results.jsonl`).
3. Review the results — especially empty-tag rows and low-confidence rows.
4. Apply the fixes in [`writing-keyword-descriptions.md`](./writing-keyword-descriptions.md) to
   `taxonomy.json`, re-mirror `keywords.md`, clear `results.jsonl`, and re-run.
5. Repeat until the tags look right, then run the full library.
