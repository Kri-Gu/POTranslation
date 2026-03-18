# Prompt Optimisation Guide

This document covers the current prompt design, known limitations, and actionable improvements ranked by expected impact.

---

## Current prompt design

### PO format (`.po`) — `po_translate_en_to_nb.py`

**System prompt** is built by `make_system_prompt(target_lang, domain_context)`:

```
You are an expert translator specialising in {target_name} ({target_lang}).
…
=== RULES (strictly enforce) ===
1) Translate into {target_name} ONLY.
2) Preserve ALL placeholders exactly …
3) Match capitalisation style …
4) Preserve punctuation and whitespace …
5) Use natural, idiomatic {target_name} …
6) Technical/product terms with no translation → keep original
7) Return ONLY a valid JSON object: {"translations": [{"id": "…", "translation": "…"}, …]}
8) Do NOT add extra keys, markdown formatting, or commentary.

=== DOMAIN CONTEXT ===      ← injected when context.json is provided
…
```

**User prompt** (`make_user_prompt`) includes:
- 3–4 static few-shot examples in JSON
- The actual batch payload encoded as JSON

### XLIFF format (`.xlf`) — `xliff_translate.py`

Similar structure but handles markup items differently: when a `<source>` contains `<g>` elements, the prompt instructs the model to preserve the tag structure exactly.

---

## Identified weaknesses

| # | Weakness | Impact |
|---|---------|--------|
| W1 | Role is generic ("expert translator") — no cues about native level or specialisation depth | Medium |
| W2 | Register (formal/informal "you") not specified per language — Norwegian defaults vary by domain | High |
| W3 | Glossary terms not injected into the prompt — model invents its own terms | High |
| W4 | Few-shot examples are static and not domain-specific | Medium |
| W5 | `json_object` response format allows any key names — model can still hallucinate structure | Low-Medium |
| W6 | No explicit instruction to preserve UI-string length/brevity constraints | Low |
| W7 | `temperature=0.2` is reasonable but not validated against alternatives | Low |
| W8 | Markup prompt for XLIFF doesn't tell the model which `<g>` attributes to copy | Medium |
| W9 | No chain-of-thought for complex, ambiguous segments | Medium |
| W10 | Source language tagged per-item but no confidence signal when detection is uncertain | Low |

---

## Recommended improvements

### Improvement 1 — Stronger role framing (addresses W1)

**Current:**
```
You are an expert translator specialising in Norwegian Bokmål (nb).
```

**Proposed:**
```
You are a professional technical translator, native in Norwegian Bokmål, with 10+ years
of experience localising software UI, user manuals, and e-commerce content.
Your translations are used directly in production software without human review,
so precision and consistency are critical.
```

**Why it matters:** Models respond to role framing. A richer role description activates more specific translation knowledge and reduces casual/colloquial register drift.

---

### Improvement 2 — Explicit register instruction per language (addresses W2)

Add a per-language register note to the system prompt:

```python
_REGISTER_NOTES = {
    "nb": "Use informal address ('du', not 'De'). Norwegian UI text conventionally uses informal second person across all contexts.",
    "sv": "Use informal address ('du'). Avoid formal 'Ni' in UI text.",
    "da": "Use informal address ('du'). Formal 'De' is outdated in modern Danish UI text.",
    "de": "Use formal address ('Sie') unless the product is explicitly casual/youth-oriented.",
    "pl": "Use second person plural ('Państwo'-style) for formal contexts, or 'ty'-form for casual apps.",
    "cs": "Use informal second person singular ('ty'-form) for modern software UI.",
}
```

Inject this after rule 5:
```
5b) Register: {_REGISTER_NOTES.get(target_lang, "")}
```

---

### Improvement 3 — Glossary injection (addresses W3)

When the user provides a glossary (feature roadmap #3), inject it as a dedicated section:

```
=== GLOSSARY (mandatory) ===
The following terms MUST be translated exactly as shown. Do not paraphrase or transliterate.
  "lawn mower"  →  "gressklipper"
  "blade speed" →  "knivhastighet"
  "throttle"    →  "gasspedal"
Terms not in this list should follow normal translation rules.
```

Place this **before** the domain context section and **after** the rules, so it has higher recency weight.

---

### Improvement 4 — JSON schema enforcement (addresses W5)

Replace the current `{"type": "json_object"}` response format with a strict schema using `json_schema` mode (available in `gpt-4.1` and later):

```python
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "translation_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "translations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":          {"type": "string"},
                            "translation": {"type": "string"}
                        },
                        "required": ["id", "translation"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["translations"],
            "additionalProperties": False
        }
    }
}
```

This eliminates an entire class of parse errors where the model adds extra keys, wraps the array differently, or includes commentary.

**Note:** When `strict=True`, `temperature` must be ≤1.0 and the schema must match exactly. Validate that all model versions in `AVAILABLE_MODELS` support structured output before enabling.

---

### Improvement 5 — Domain-specific few-shot examples (addresses W4)

Move few-shot examples out of the hardcoded `_FEWSHOT_EXAMPLES` dict into the `context.json` file so teams can provide domain-specific examples:

```json
{
  "instructions": "This content describes outdoor power equipment…",
  "examples": [
    {
      "source": "Blade engagement speed",
      "source_lang": "en",
      "target": "Koblingshastigheit for kniv",
      "target_lang": "nb"
    }
  ]
}
```

The `load_context()` function would then return both the instructions text and the examples list, and `make_user_prompt()` would prepend them.

---

### Improvement 6 — XLIFF markup prompt hardening (addresses W8)

Current XLIFF prompt tells the model to "preserve the tag structure exactly". Strengthen this with an explicit example showing `<g>` attribute preservation:

```
=== XLIFF INLINE MARKUP RULES ===
Source segments may contain <g> tags representing inline formatting.
You MUST:
- Keep every <g> tag and its id attribute exactly: <g id="1">…</g>
- Only translate the TEXT CONTENT between and around the tags
- Never add, remove, rename, or re-order <g> tags
- Never change id="…" values

Example:
  Source:  Add <g id="1">all</g> items to cart
  Correct: Legg til <g id="1">alle</g> varer i handlekurven
  Wrong:   Legg til <g id="2">alle</g> varer i handlekurven   ← id changed
  Wrong:   Legg <g id="1">til alle varer</g> i handlekurven  ← tag scope changed
```

---

### Improvement 7 — Confidence-tagged output for ambiguous items (addresses W9)

For segments that are genuinely ambiguous (very short strings like "On", "Off", "Set"), request a confidence field:

```python
# Only for batches flagged as potentially ambiguous
schema_with_confidence = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "translation": {"type": "string"},
        "confidence": {"enum": ["high", "medium", "low"]}
    },
    "required": ["id", "translation", "confidence"]
}
```

Low-confidence items can be highlighted in the UI for human review. This feeds naturally into the Segment Review UI (roadmap #9).

---

### Improvement 8 — Per-format system prompt tuning

| Format | Add to system prompt |
|--------|---------------------|
| `.po` (UI strings) | "These are short UI labels (buttons, menus, error messages). Keep translations brief — match the original's approximate length." |
| `.po` (long strings) | "These strings may include full sentences and paragraphs. Preserve paragraph structure." |
| XLIFF (InDesign/CMS) | "This is published marketing or documentation copy. Use polished, print-ready language." |
| IDML (InDesign) | "These are typeset paragraphs from an InDesign document. Preserve hyphenation-friendly word choices." |
| DITA | "This is structured technical documentation. Use precise, consistent terminology. Prefer active voice." |

Auto-detect which variant applies based on file origin or add a "Content type" dropdown to the sidebar.

---

### Improvement 9 — Temperature tuning

Current: `temperature=0.2` (fixed).

Recommended approach — add a `temperature` parameter to `translate_*_file()` with sensible per-format defaults:

| Content type | Recommended temperature |
|---|---|
| Short UI strings (buttons, labels) | 0.1 — maximise consistency |
| Technical documentation | 0.2 — current default, works well |
| Marketing / descriptive copy | 0.4 — allow slightly more natural variation |

Expose in the sidebar as an "Advanced" expander.

---

## Implementation priority

| Priority | Improvement | Effort | Expected gain |
|---|---|---|---|
| 🔴 High | #3 — Glossary injection | Low (depends on feature #3) | Largest quality improvement |
| 🔴 High | #2 — Register per language | Very low (dict + one line) | Eliminates a common complaint |
| 🟠 Medium | #4 — JSON schema enforcement | Low-medium | Eliminates parse errors |
| 🟠 Medium | #6 — XLIFF markup hardening | Low | Reduces tag corruption |
| 🟡 Low | #1 — Role framing | Very low (string edit) | Small but free gain |
| 🟡 Low | #5 — Domain few-shot in context.json | Medium | Useful for power users |
| 🟡 Low | #8 — Per-format tuning | Low | Targeted quality lift |
| ⚪ Optional | #7 — Confidence-tagged output | Medium | Feeds review UI |
| ⚪ Optional | #9 — Temperature control | Very low | Minor for most content |
