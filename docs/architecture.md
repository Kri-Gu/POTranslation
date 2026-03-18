# Architecture

## Overview

This tool translates localisation files (`.po`, `.xlf`) via the OpenAI API. It has two entry points:
- **Web UI** (`src/app.py`) — Streamlit browser app
- **CLI** — each translation module is directly executable

```
┌──────────────────────────────────────────────────────────┐
│  User interface                                          │
│  Streamlit (src/app.py)   or   CLI (python src/…)        │
└──────────────┬──────────────────────────┬────────────────┘
               │                          │
               ▼                          ▼
   src/po_translate_en_to_nb.py    src/xliff_translate.py
   ─────────────────────────────    ──────────────────────
   - parse .po with polib           - parse .xlf with ET
   - build_work_items()             - build_work_items_xliff()
   - make_system_prompt()           - _make_system_prompt_xliff()
   - make_user_prompt()             - _make_user_prompt_xliff()
   - _call_model_po()               - _call_model_xliff()
   - translate_po_file()            - translate_xliff_file()
               │                          │
               └──────────┬───────────────┘
                           ▼
              OpenAI Chat Completions API
              JSON mode / structured output
```

## Module responsibilities

### `src/po_translate_en_to_nb.py`

The original translation engine and the **shared library** that XLIFF re-uses.

| Export | Purpose |
|--------|---------|
| `AVAILABLE_MODELS` | Dict of `{model_id: display_name}` |
| `TARGET_LANGUAGES` | Dict of `{code: name}` for supported targets |
| `SOURCE_LANGUAGES` | Dict of `{code: name}` for source detection |
| `load_context(path)` | Load domain context from JSON or plain text |
| `get_defaults()` | Read `.env` into a dict of UI defaults |
| `looks_english(s)` | Heuristic: is this English text? |
| `looks_german(s)` | Heuristic: is this German text? |
| `extract_placeholders(s)` | Find `%s`, `{name}`, `<tag>`, URLs etc. |
| `validate_placeholders(src, tgt)` | Return placeholders dropped in translation |
| `make_system_prompt(lang, ctx)` | Build the system prompt sent to the model |
| `make_user_prompt(items, lang, ex)` | Build the batched user prompt |
| `chunked(iterable, n)` | Split list into batches of `n` |
| `build_work_items(po, force)` | Extract entries needing translation from a `.po` |
| `translate_po_file(...)` | **Main entry point** for `.po` files |
| `client` | Shared `openai.OpenAI` instance |

### `src/xliff_translate.py`

XLIFF 1.2 translation engine; imports its infrastructure from `po_translate_en_to_nb`.

| Export | Purpose |
|--------|---------|
| `build_work_items_xliff(tree, src_lang, force)` | Extract `<trans-unit>` items that need translation |
| `translate_xliff_file(...)` | **Main entry point** for `.xlf` files |

Internal helpers (not exported):

| Helper | Purpose |
|--------|---------|
| `_inner_xml(el)` | Serialise inner content of an XML element |
| `_extract_plain_text(el)` | Strip all tags, return text only |
| `_has_children(el)` | True if element contains child elements |
| `_set_target_content(unit, text, src)` | Write `<target>` back into the trans-unit |
| `_validate_placeholders(src, tgt)` | Placeholder validation for XLIFF markup |
| `_make_system_prompt_xliff(lang, ctx)` | XLIFF-specific system prompt |
| `_make_user_prompt_xliff(items, lang)` | XLIFF-specific user prompt |
| `_call_model_xliff(items, model, ...)` | API call + JSON parse for XLIFF batches |

### `src/app.py`

Streamlit UI. Contains no translation logic. Responsibilities:

1. File upload widget (accepts `.po`, `.xlf`)
2. Sidebar settings (model, language, batch size, API key, context file)
3. Pre-flight: detect format, call `build_work_items_*`, show count
4. Run translation with live progress bar via `progress_callback`
5. Show results table and warnings
6. Offer in-memory download without writing to disk (uses `tempfile`)

## Data flow — translation request lifecycle

```
1. User uploads file
2. app.py detects extension → routes to correct build_work_items_*()
3. Pre-flight count shown (entries found / to translate)
4. User clicks Translate
5. app.py calls translate_*_file(input_path, output_path, ...)
6. Inside translate_*_file:
   a. Parse file (polib / ElementTree)
   b. build_work_items → List[{id, text, lang}]
   c. chunked() → split into batches
   d. For each batch → _call_model_*() → OpenAI API → JSON response
   e. Parse JSON → map id → translated text
   f. Validate placeholders → collect warnings
   g. Write translations back into parsed structure
   h. Serialise to output file
7. app.py reads output file → show preview table + download button
```

## API call structure

Both formats use the same pattern:

```python
response = client.chat.completions.create(
    model=model,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ],
    temperature=0.2,
)
result = json.loads(response.choices[0].message.content)
# result = {"translations": [{"id": "…", "translation": "…"}, …]}
```

The `id` field is used to match translations back to source segments; it is never sent to the user.

## Retry strategy

Both modules use `tenacity` for automatic retries on API failures:

```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=30))
def _call_model_*(…):
    …
```

Additionally, if a whole batch fails its retry budget, each item in the batch is retried _individually_ before being recorded as failed.

## Namespace handling (XLIFF)

XLIFF 1.2 uses a default namespace (`xmlns="urn:oasis:names:tc:xliff:document:1.2"`). Python's `xml.etree.ElementTree` uses Clark notation internally: `{urn:oasis:names:tc:xliff:document:1.2}trans-unit`. The `_q(tag)` helper converts short tag names to Clark notation. Namespaces are registered with `ET.register_namespace()` before any parse so round-trip writing uses the original prefix (no `ns0:` pollution).

## Adding a new file format

1. Create `src/<format>_translate.py`
2. Import shared infrastructure from `po_translate_en_to_nb`: `client`, `chunked`, `load_context`, `get_defaults`
3. Implement `build_work_items_<format>(...)` → `(work_items, id_map, total_count)`
4. Implement `translate_<format>_file(input_path, output_path, *, model, target_lang, ...)` → `Dict`
5. In `src/app.py`: add extension to the uploader `type` list, add an `elif` branch in the format-detection block, call the new `_run_<format>_translation()` helper

See `docs/format-support.md` for per-format technical notes.
